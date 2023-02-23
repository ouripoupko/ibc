from enum import Enum, auto
import hashlib


class ProtocolStep(Enum):
    REQUEST = auto()
    PRE_PREPARE = auto()
    PREPARE = auto()
    COMMIT = auto()
    DONE = auto()
    CHECKPOINT = auto()


class PBFT:
    def __init__(self, storage, contract_name, me, partners, logger):
        self.db_storage = storage
        self.storage = {}
        for key in storage:
            self.storage[key] = storage[key].get_dict()
        if 'parameters' in self.storage:
            self.parameters = self.storage['parameters']
        else:
            self.parameters = {'view': 0,
                               'last_index': 0,
                               'next_index': 0,
                               'low_mark': 0,
                               'checkpoint': 100,
                               'high_mark': 199,
                               'block': []}
        self.contract_name = contract_name
        self.me = me
        self.logger = logger
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])
        self.switcher = {ProtocolStep.REQUEST: self.receive_request,
                         ProtocolStep.PRE_PREPARE: self.receive_pre_prepare,
                         ProtocolStep.PREPARE: self.receive_prepare,
                         ProtocolStep.COMMIT: self.receive_commit,
                         ProtocolStep.CHECKPOINT: self.receive_checkpoint}

    def update_partners(self, partners):
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])

    def close(self):
        self.storage['parameters'] = self.parameters
        self.db_storage.store(self.storage)

    def leader_is_me(self):
        return self.names[self.order[self.parameters['view']]] == self.me

    def send_request(self, record):
        data = {'o': record,
                't': record['timestamp'],
                'd': record['hash_code'],
                'c': self.me}
        self.store_request(data)
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
        return data['d']

    def receive_request(self, data):
        reply = self.store_request(data)
        if self.leader_is_me():
            self.send_pre_prepare(data['d'])
        return reply

    def store_request(self, data):
        all_exist = False
        if data['d'] in self.storage:
            block_code = self.storage[data['d']]
            block = self.storage[block_code]['block']
            all_exist = True
            for key in block:
                if key == data['d']:
                    continue
                if isinstance(self.storage[key], str):
                    all_exist = False
                    break
            if all_exist:
                self.storage[block_code]['step'] = ProtocolStep.PREPARE.name
        self.storage[data['d']] = {'record': data['o'],
                                   'timestamp': data['t'],
                                   'client': data['c']}
        return self.send_phase(block_code, ProtocolStep.PREPARE) if all_exist else False

    def send_pre_prepare(self, hash_code):
        if hash_code:
            self.parameters['block'].append(hash_code)
        index = self.parameters['next_index']
        if index - self.parameters['last_index'] > 5 and len(self.parameters['block']) < 1000:
            return
        self.parameters['next_index'] = index+1
        block_code = hashlib.sha256(str(self.parameters['block']).encode('utf-8')).hexdigest()
        data = {'v': self.parameters['view'],
                'n': index,
                'd': block_code,
                'l': self.parameters['block']}
        self.parameters['block'] = []
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.PRE_PREPARE.name, data)
        self.store_pre_prepare(data)

    def receive_pre_prepare(self, data):
        # I should check signatures and digest, but I am lazy
        if data['v'] != self.parameters['view']:
            return
        if str(data['n']) in self.storage:
            return
        if data['n'] < self.parameters['low_mark'] or data['n'] > self.parameters['high_mark']:
            return
        index = self.parameters['next_index']
        if data['n'] >= index:
            self.parameters['next_index'] = data['n']+1
        return self.store_pre_prepare(data)

    def store_pre_prepare(self, data):
        self.storage[str(data['n'])] = {'hash': data['d']}
        block = data['l']
        all_exist = True
        for key in block:
            if key not in self.storage:
                all_exist = False
                self.storage[key] = data['d']
        step = ProtocolStep.PREPARE if all_exist else ProtocolStep.PRE_PREPARE
        if data['d'] not in self.storage:
            self.storage[data['d']] = {}
        self.storage[data['d']].update({'view': data['v'],
                                        'index': data['n'],
                                        'step': step.name,
                                        'block': block})
        return self.send_phase(data['d'], ProtocolStep.PREPARE) if step is ProtocolStep.PREPARE else False

    def send_phase(self, hash_code, phase):
        record = self.storage.get(hash_code)
        data = {'v': record['view'],
                'n': record['index'],
                'd': hash_code,
                'i': self.me}
        for partner in self.partners:
            partner.consent(self.contract_name, phase.name, data)
        return self.store_phase(data, phase)

    def receive_prepare(self, data):
        # I should check signatures, but I am lazy
        if data['v'] != self.parameters['view']:
            return
        if data['n'] < self.parameters['low_mark'] or data['n'] > self.parameters['high_mark']:
            return
        if data['i'] not in self.names:
            return
        return self.store_phase(data, ProtocolStep.PREPARE)

    def receive_commit(self, data):
        # I should check signatures, but I am lazy
        if data['v'] != self.parameters['view']:
            return
        if data['n'] < self.parameters['low_mark'] or data['n'] > self.parameters['high_mark']:
            return
        if data['i'] not in self.names:
            return
        return self.store_phase(data, ProtocolStep.COMMIT)

    def store_phase(self, data, phase):
        record = self.storage.get(data['d'])
        if not record or phase.name not in record:
            collection = []
        else:
            collection = record[phase.name]
        collection.append(data)
        if not record:
            self.storage[data['d']] = {}
        self.storage[data['d']].update({phase.name: collection})
        return self.check_phase(data['d'], phase)

    def check_phase(self, hash_code, phase):
        reply = False
        record = self.storage.get(hash_code)
        collection = []
        if phase.name in record:
            collection = record[phase.name]
        if 'step' in record and record['step'] == phase.name and len(collection) * 3 > len(self.order) * 2:
            names = set()
            view = record['view']
            index = record['index']
            for item in collection:
                if item['v'] == view and item['n'] == index:
                    names.add(item['i'])
            if len(names) * 3 > len(self.order) * 2:
                if phase is ProtocolStep.PREPARE:
                    self.storage[hash_code]['step'] = ProtocolStep.COMMIT.name
                    reply = self.send_phase(hash_code, ProtocolStep.COMMIT)
                if phase is ProtocolStep.COMMIT:
                    self.storage[hash_code]['step'] = ProtocolStep.DONE.name
                    reply = True
        return reply

    def send_checkpoint(self):
        checkpoint = self.parameters['checkpoint']
        low_mark = self.parameters['low_mark']
        high_mark = self.parameters['high_mark']
        cumulative = ''
        for index in range(low_mark, checkpoint):
            if str(index) in self.storage:
                hash_code = self.storage[str(index)]['hash']
                block = self.storage[hash_code].get('block', [])
                for key in block:
                    cumulative += key
                    del self.storage[key]
                del self.storage[hash_code]
                del self.storage[str(index)]
        data = {'n': checkpoint,
                'd': hashlib.sha256(str(cumulative).encode('utf-8')).hexdigest(),
                'i': self.me}
        self.store_checkpoint(data)
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.CHECKPOINT.name, data)
        self.parameters['checkpoint_hash'] = data['d']

    def receive_checkpoint(self, data):
        if data['n'] < self.parameters['checkpoint']:
            return
        if data['i'] not in self.names:
            return
        self.store_checkpoint(data)
        pass

    def store_checkpoint(self, data):
        key = f'checkpoint_{str(data["n"])}'
        collection = self.storage.get(key)
        if not collection:
            collection = []
        collection.append(data)
        self.storage[key] = collection
        if data['n'] == self.parameters['checkpoint'] and len(collection) * 3 > len(self.order) * 2:
            hash_count = {}
            for item in collection:
                hash_count[item['d']] = hash_count[item['d']]+1 if item['d'] in hash_count else 1
            for hash_code in hash_count:
                if hash_count[hash_code] * 3 > len(self.order) * 2:
                    if 'checkpoint_hash' in self.parameters:
                        # me also passed checkpoint
                        if self.parameters['checkpoint_hash'] == hash_code:
                            # me on track. can clean up checkpoint
                            del self.parameters['checkpoint_hash']
                            del self.storage[key]
                            self.parameters['checkpoint'] += 100
                            self.parameters['low_mark'] += 100
                            self.parameters['high_mark'] += 100
                        else:
                            # something bad happened. me differ from majority
                            self.logger.ERROR('Holy Spirit!! I am corrupted!!')
                    else:
                        # me not yet in checkpoint
                        if data['n'] < self.parameters['last_index'] + 10:
                            # me will get there soon
                            pass
                        else:
                            self.logger.WARNING('I think it is bad that I am here')
                            # me need to catch up
                            majority = []
                            for item in collection:
                                if item['d'] == hash_code:
                                    majority.append(item['i'])
                            self.parameters['majority'] = majority
                            self.parameters['checkpoint'] = self.parameters['checkpoint'] + 100
                            self.parameters['low_mark'] = self.parameters['low_mark'] + 100
                            self.parameters['high_mark'] = self.parameters['high_mark'] + 100

    def catchup(self):
        records = {}
        hash_count = {}
        last_index = self.parameters['last_index']
        for partner_name in self.parameters['majority']:
            if partner_name in self.names:
                partner_index = self.names.index(partner_name)
                partner_record = self.partners[partner_index].catchup(last_index)
                partner_hash = hashlib.sha256(str(partner_record).encode('utf-8')).hexdigest()
                if partner_hash in hash_count:
                    hash_count[partner_hash] += 1
                else:
                    hash_count[partner_hash] = 1
                    records[partner_hash] = partner_record
        for hash_code in hash_count:
            if hash_count[hash_code] * 3 > len(self.order):
                if str(last_index) in self.storage:
                    stored_hash = self.storage[str(last_index)]['hash']
                    if stored_hash != hash_code:
                        del self.storage[stored_hash]
                else:
                    self.storage[str(last_index)].update({'hash': hash_code})
                self.storage[hash_code].update({'step': ProtocolStep.DONE.name,
                                                'request': records[hash_code]})

    def record_message(self, record):
        if self.me[0] == 'z':
            self.logger.warning('record: ' + str(record))
        index = self.parameters['next_index']
        hash_code = record['hash_code']
        self.storage[str(index)] = {'hash': str(index)+hash_code}
        self.storage[str(index)+hash_code] = {'block': [hash_code]}
        self.storage[hash_code] = {'dummy': 'for deletion'}
        self.parameters['last_index'] += 1
        self.parameters['next_index'] += 1
        if self.parameters['last_index'] > self.parameters['checkpoint']:
            self.parameters['low_mark'] += 100
            self.parameters['checkpoint'] += 100
            self.parameters['high_mark'] += 100

    def handle_message(self, record, initiate):
        self.logger.debug(self.me + ' ' + str(record))
        if 'message' in record and 'msg' in record['message'] and record['message']['msg']['step'] == 'COMMIT' and record['message']['msg']['data']['n'] == 2:
            pass
        if self.me[0] == 'z':
            self.logger.warning('handle: ' + str(record))
        # check if checkpoint was crossed
        if self.parameters['last_index'] > self.parameters['checkpoint'] and \
                'checkpoint_hash' not in self.parameters:
            self.send_checkpoint()
        # check if me am behind
        if self.parameters['last_index'] < self.parameters['low_mark']:
            self.catchup()
        if initiate:
            hash_code = self.send_request(record)
            if self.leader_is_me():
                self.send_pre_prepare(hash_code)
        else:
            message = record['message']['msg']
            step = ProtocolStep[message['step']]
            data = message['data']
            receiver = self.switcher[step]
            if receiver(data):
                reply = []
                last_index = self.parameters['last_index']
                while str(last_index) in self.storage:
                    hash_code = self.storage[str(last_index)]['hash']
                    pre_prepare = self.storage.get(hash_code)
                    if pre_prepare and 'step' in pre_prepare and pre_prepare['step'] == ProtocolStep.DONE.name:
                        for key in pre_prepare['block']:
                            request = self.storage[key]
                            stored_record = request['record']
                            stored_record['hash_code'] = key
                            reply.append(stored_record)
                        last_index += 1
                        self.parameters['last_index'] = last_index
                        if self.parameters['next_index'] - last_index < 4 and self.parameters['block']:
                            self.send_pre_prepare(None)
                    else:
                        break
                self.logger.info(self.me + ' leaving')
                return reply
        self.logger.info(self.me + ' leaving')
        return []

# should wait on time out from request to change view
# can optimize by sending bulk of messages when traffic is high
# disregard requests with timestamp older than already committed timestamp
# add timestamp to hash.
# handle changes in partner list during protocol run
