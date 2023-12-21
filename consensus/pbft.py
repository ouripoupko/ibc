from enum import Enum, auto
import hashlib
from redis_json import RedisJson
from partner import Partner

class ProtocolStep(Enum):
    REQUEST = auto()
    PRE_PREPARE = auto()
    PREPARE = auto()
    COMMIT = auto()
    DONE = auto()
    CHECKPOINT = auto()


class PBFT:
    def __init__(self, contract_name, me, partners, db: RedisJson):
        self.db = db
        if 'parameters' not in self.db.object_keys(None):
            self.db.set(None, {'requests': {}, 'blocks': {}, 'preparations': {},
                               'parameters': {'view': 0,
                                              'last_index': 0,
                                              'next_index': 0,
                                              'low_mark': 0,
                                              'checkpoint': 100,
                                              'high_mark': 199,
                                              'block': [],
                                              'sent': []}})
        self.parameters = self.db.get('parameters')
        self.contract_name = contract_name
        self.me = me
        # self.logger = logger
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])
        self.switcher = {ProtocolStep.REQUEST: lambda x: self.receive_request(x),
                         ProtocolStep.PRE_PREPARE: lambda x: self.receive_pre_prepare(x),
                         ProtocolStep.PREPARE: lambda x: self.receive_prepare(x),
                         ProtocolStep.COMMIT: lambda x: self.receive_commit(x),
                         ProtocolStep.CHECKPOINT: lambda x: self.receive_checkpoint(x)}

    def leader_is_me(self):
        return self.names[self.order[self.parameters['view']]] == self.me

    def send_request(self, record):
        data = {'o': record,
                't': record['timestamp'],
                'd': record['hash_code'],
                'c': self.me}
        self.store_request(data)
        self.parameters['sent'].append(data['d'])
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
        return data['d']

    def receive_request(self, data):
        reply = self.store_request(data)
        if self.leader_is_me():
            self.send_pre_prepare(data['d'])
        return reply

    def store_request(self, data):
        print(self.me, data)
        all_exist = False
        block_code = None
        if data['d'] in self.db.object_keys('requests'):
            block_code = self.db.get(f'requests.{data["d"]}.missing')
            block = self.db.get(f'preparations.{block_code}.block')
            all_exist = True
            for key in block:
                if key == data['d']:
                    continue
                if 'missing' in self.db.object_keys(f'requests.{key}'):
                    all_exist = False
                    break
            if all_exist:
                self.db.set(f'preparations.{block_code}.step', ProtocolStep.PREPARE.name)
        self.db.set(f'requests.{data["d"]}', {'record': data['o'],
                                              'timestamp': data['t'],
                                              'client': data['c']})
        return self.send_phase(block_code, ProtocolStep.PREPARE) if all_exist else False

    def send_pre_prepare(self, hash_code):
        if hash_code:
            self.parameters['block'].append(hash_code)
        index = self.parameters['next_index']
        if index > self.parameters['last_index']:  # > 5 and len(self.parameters['block']) < 1000:
            return
        self.parameters['next_index'] = index+1
        block_code = hashlib.sha256(str(self.parameters['block']).encode('utf-8')).hexdigest()
        data = {'v': self.parameters['view'],
                'n': index,
                'd': block_code,
                'l': [self.parameters['block'].pop(0)]}
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.PRE_PREPARE.name, data)
        self.store_pre_prepare(data)

    def receive_pre_prepare(self, data):
        # I should check signatures and digest, but I am lazy
        if data['v'] != self.parameters['view']:
            return
        if str(data['n']) in self.db.object_keys('blocks'):
            return
        if data['n'] < self.parameters['low_mark'] or data['n'] > self.parameters['high_mark']:
            return
        index = self.parameters['next_index']
        if data['n'] >= index:
            self.parameters['next_index'] = data['n']+1
        return self.store_pre_prepare(data)

    def store_pre_prepare(self, data):
        self.db.set(f'blocks.{str(data["n"])}', {'hash': data['d']})
        block = data['l']
        all_exist = True
        for key in block:
            if key not in self.db.object_keys('requests'):
                all_exist = False
                self.db.set(f'requests.{key}', {'missing': data['d']})
            elif key in self.parameters['sent']:
                self.parameters['sent'].remove(key)
        step = ProtocolStep.PREPARE if all_exist else ProtocolStep.PRE_PREPARE
        self.db.merge(f'preparations.{data["d"]}', {'view': data['v'],
                                                    'index': data['n'],
                                                    'step': step.name,
                                                    'block': block})
        return self.send_phase(data['d'], ProtocolStep.PREPARE) if step is ProtocolStep.PREPARE else False

    def send_phase(self, hash_code, phase):
        preparation = self.db.get(f'preparations.{hash_code}')
        data = {'v': preparation['view'],
                'n': preparation['index'],
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
        exists = self.db.type(f'preparations.{data["d"]}.{phase.name}') is not None
        collection = self.db.get(f'preparations.{data["d"]}.{phase.name}') if exists else []
        collection.append(data)
        self.db.merge(f'preparations.{data["d"]}', {phase.name: collection})
        return self.check_phase(data['d'], phase)

    def check_phase(self, hash_code, phase):
        reply = False
        preparation = self.db.get(f'preparations.{hash_code}')
        collection = []
        if phase.name in preparation:
            collection = preparation[phase.name]
        if 'step' in preparation and preparation['step'] == phase.name and len(collection) * 3 > len(self.order) * 2:
            names = set()
            view = preparation['view']
            index = preparation['index']
            for item in collection:
                if item['v'] == view and item['n'] == index:
                    names.add(item['i'])
            if len(names) * 3 > len(self.order) * 2:
                if phase is ProtocolStep.PREPARE:
                    self.db.set(f'preparations.{hash_code}.step', ProtocolStep.COMMIT.name)
                    reply = self.send_phase(hash_code, ProtocolStep.COMMIT)
                if phase is ProtocolStep.COMMIT:
                    self.db.set(f'preparations.{hash_code}.step', ProtocolStep.DONE.name)
                    reply = True
        return reply

    def send_checkpoint(self):
        checkpoint = self.parameters['checkpoint']
        low_mark = self.parameters['low_mark']
        cumulative = ''
        for index in range(low_mark, checkpoint):
            if str(index) in self.db.object_keys('blocks'):
                hash_code = self.db.get(f'blocks.{str(index)}.hash')
                block = self.db.get(f'preparations.{hash_code}').get('block', [])
                for key in block:
                    cumulative += key
                    self.db.delete(f'requests.{key}')
                self.db.delete(f'preparations.{hash_code}')
                self.db.delete(f'blocks.{str(index)}')
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
        collection = self.db.get(f'blocks.{key}') if key in self.db.object_keys('blocks') else []
        collection.append(data)
        self.db.set(f'blocks.{key}', collection)
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
                            self.db.delete(f'blocks.{key}')
                            self.parameters['checkpoint'] += 100
                            self.parameters['low_mark'] += 100
                            self.parameters['high_mark'] += 100
                        else:
                            pass
                            # something bad happened. me differ from majority
                            # self.logger.ERROR('Holy Spirit!! I am corrupted!!')
                    else:
                        # me not yet in checkpoint
                        if data['n'] < self.parameters['last_index'] + 10:
                            # me will get there soon
                            pass
                        else:
                            # self.logger.WARNING('I think it is bad that I am here')
                            # me need to catch up
                            majority = []
                            for item in collection:
                                if item['d'] == hash_code:
                                    majority.append(item['i'])
                            self.parameters['majority'] = majority
                            self.parameters['checkpoint'] += 100
                            self.parameters['low_mark'] += 100
                            self.parameters['high_mark'] += 100

    def catchup(self):
        records = {}
        hash_count = {}
        last_index = self.parameters['last_index']
        for partner_name in self.parameters['majority']:
            if partner_name in self.names:
                partner_index = self.names.index(partner_name)
                partner_record = self.partners[partner_index].get_ledger(last_index)
                partner_hash = hashlib.sha256(str(partner_record).encode('utf-8')).hexdigest()
                if partner_hash in hash_count:
                    hash_count[partner_hash] += 1
                else:
                    hash_count[partner_hash] = 1
                    records[partner_hash] = partner_record
        for hash_code in hash_count:
            if hash_count[hash_code] * 3 > len(self.order):
                if str(last_index) in self.db.object_keys('blocks'):
                    stored_hash = self.db.get(f'blocks.{str(last_index)}.hash')
                    if stored_hash != hash_code:
                        self.db.delete(f'preparations.{stored_hash}')
                else:
                    self.db.merge(f'blocks.{str(last_index)}', {'hash': hash_code})
                self.db.merge(f'preparations.{hash_code}', {'step': ProtocolStep.DONE.name,
                                                            'request': records[hash_code]})

    def update_partners(self, partners):
        newcomers = [partner for partner in partners if partner.pid not in self.names]
        for code in self.parameters['sent']:
            request = self.db.get(f'requests.{code}')
            data = {'o': request['record'],
                    't': request['timestamp'],
                    'd': code,
                    'c': request['client']}
            for partner in newcomers:
                partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])

    def record_message(self, record):
        # it seems there is a conceptual defect here.
        # this function assumes all past requests were handled one by one
        # if requests were handled in blocks, this agent index will run faster than others
        # self.logger.debug('record: ' + str(record))
        index = self.parameters['next_index']
        hash_code = record['hash_code']
        self.db.set(f'blocks.{str(index)}', {'hash': str(index)+hash_code})
        self.db.set(f'preparations.{str(index)+hash_code}', {'block': [hash_code]})
        self.db.set(f'requests.{hash_code}', {'dummy': 'for deletion'})
        self.parameters['last_index'] += 1
        self.parameters['next_index'] += 1
        if self.parameters['last_index'] > self.parameters['checkpoint']:
            self.parameters['low_mark'] += 100
            self.parameters['checkpoint'] += 100
            self.parameters['high_mark'] += 100
        self.db.set('parameters', self.parameters)

    def handle_message(self, record, initiate, me_partner: Partner):
        # self.logger.debug(self.me + ' ' + str(record))
        reply = False
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
                last_index = self.parameters['last_index']
                while str(last_index) in self.db.object_keys('blocks'):
                    hash_code = self.db.get(f'blocks.{str(last_index)}.hash')
                    pre_prepare = self.db.get('preparations').get(hash_code)
                    if pre_prepare and 'step' in pre_prepare and pre_prepare['step'] == ProtocolStep.DONE.name:
                        for key in pre_prepare['block']:
                            request = self.db.get(f'requests.{key}')
                            stored_record = request['record']
                            stored_record['hash_code'] = key
                            me_partner.post_consent(self.contract_name, stored_record)
                            reply = True
                        last_index += 1
                        self.parameters['last_index'] = last_index
                        if self.parameters['next_index'] - last_index < 4 and self.parameters['block']:
                            self.send_pre_prepare(None)
                    else:
                        break
        self.db.set('parameters', self.parameters)
        return reply

# should wait on time out from request to change view
# can optimize by sending bulk of messages when traffic is high
# disregard requests with timestamp older than already committed timestamp
# add timestamp to hash.
# handle changes in partner list during protocol run
