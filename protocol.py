from enum import Enum, auto
from datetime import datetime
import hashlib
from threading import Thread
import time
from redis import Redis
import json


class ProtocolStep(Enum):
    REQUEST = auto()
    PRE_PREPARE = auto()
    PREPARE = auto()
    COMMIT = auto()
    DONE = auto()
    CHECKPOINT = auto()


class Protocol:
    def __init__(self, storage, contract_name, me, partners, logger):
        self.storage = storage
        if 'parameters' not in self.storage:
            self.storage['parameters'] = {'view': 0,
                                          'last_index': 0,
                                          'next_index': 0,
                                          'low_mark': 0,
                                          'checkpoint': 100,
                                          'high_mark': 199}
        self.parameters = self.storage['parameters']
        self.contract_name = contract_name
        self.me = me
        self.partners = partners
        self.logger = logger
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])

    def leader_is_me(self):
        return self.names[self.order[self.parameters['view']]] == self.me

    def send_request(self, record):
        data = {'o': record,
                't': datetime.now().strftime('%Y%m%d%H%M%S%f'),
                'd': hashlib.sha256(str(record).encode('utf-8')).hexdigest(),
                'c': self.me}
        self.store_request(data)
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
        return data['d']

    def receive_request(self, data):
        self.store_request(data)
        if self.leader_is_me():
            self.send_pre_prepare(data['d'])

    def store_request(self, data):
        record = self.storage[data['d']]
        if record.exists() and record['step'] == ProtocolStep.PRE_PREPARE.name:
            step = ProtocolStep.PREPARE
        else:
            step = ProtocolStep.REQUEST
        self.storage[data['d']] = {'record': data['o'],
                                   'timestamp': data['t'],
                                   'client': data['c'],
                                   'step': step.name}

    def send_pre_prepare(self, hash_code):
        index = self.parameters['next_index']
        self.parameters['next_index'] = index+1
        data = {'v': self.parameters['view'],
                'n': index,
                'd': hash_code}
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
        record = self.storage[data['d']]
        if record.exists() and record['step'] == ProtocolStep.REQUEST.name:
            step = ProtocolStep.PREPARE
        else:
            step = ProtocolStep.PRE_PREPARE
        self.storage[data['d']] = {'view': data['v'],
                                   'index': data['n'],
                                   'step': step.name}
        return self.send_phase(data['d'], ProtocolStep.PREPARE)

    def send_phase(self, hash_code, phase):
        record = self.storage[hash_code]
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
        record = self.storage[data['d']]
        if not record.exists() or phase.name not in record:
            collection = []
        else:
            collection = record[phase.name]
        collection.append(data)
        self.storage[data['d']] = {phase.name: collection}
        return self.check_phase(data['d'], phase)

    def check_phase(self, hash_code, phase):
        record = self.storage[hash_code]
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
                    self.storage[hash_code] = {'step': ProtocolStep.COMMIT.name}
                    return self.send_phase(hash_code, ProtocolStep.COMMIT)
                if phase is ProtocolStep.COMMIT:
                    self.storage[hash_code] = {'step': ProtocolStep.DONE.name}
                    return True
        # just for readability. I am not supposed to be here
        return False

    def send_checkpoint(self):
        checkpoint = self.parameters['checkpoint']
        low_mark = self.parameters['low_mark']
        high_mark = self.parameters['high_mark']
        index = low_mark
        cumulative = ''
        while index < checkpoint:
            if str(index) in self.storage:
                hash_code = self.storage[str(index)]['hash']
                cumulative += hash_code
                del self.storage[hash_code]
                del self.storage[str(index)]
        data = {'n': checkpoint,
                'd': hashlib.sha256(str(cumulative).encode('utf-8')).hexdigest(),
                'i': self.me}
        self.store_request(data)
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.CHECKPOINT.name, data)
        self.parameters['checkpoint'] = checkpoint + 100
        self.parameters['checkpoint_hash'] = data['d']
        self.parameters['low_mark'] = low_mark+100
        self.parameters['high_mark'] = high_mark+100

    def receive_checkpoint(self, data):
        if data['n'] < self.parameters['checkpoint']:
            return
        if data['i'] not in self.names:
            return
        self.store_checkpoint(data)
        pass

    def store_checkpoint(self, data):
        key = 'checkpoint_' + data['n']
        collection = self.storage[key]
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
                        else:
                            # something bad happened. me differ from majority
                            self.logger.ERROR('Holy Spirit!! I am corrupted!!')
                    else:
                        # me not yet in checkpoint
                        if data['n'] < self.parameters['last_index'] + 10:
                            # me will get there soon
                            pass
                        else:
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
                    self.storage[str(last_index)] = {'hash': hash_code}
                self.storage[hash_code] = {'step': ProtocolStep.DONE.name,
                                           'request': records[hash_code]}

    def record_message(self):
        params_dict = self.parameters.get_dict()
        params_dict['last_index'] += 1
        params_dict['next_index'] +=1
        if params_dict['last_index'] > params_dict['checkpoint']:
            params_dict['low_mark'] += 100
            params_dict['checkpoint'] += 100
            params_dict['high_mark'] += 100
        self.parameters.set_dict(params_dict)
        pass

    def handle_message(self, record, initiate):
        self.logger.info(self.me + ' ' + str(record))
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
            switcher = {ProtocolStep.REQUEST: self.receive_request,
                        ProtocolStep.PRE_PREPARE: self.receive_pre_prepare,
                        ProtocolStep.PREPARE: self.receive_prepare,
                        ProtocolStep.COMMIT: self.receive_commit,
                        ProtocolStep.CHECKPOINT: self.receive_checkpoint}
            receiver = switcher[step]
            if receiver(data):
                reply = []
                last_index = self.parameters['last_index']
                while str(last_index) in self.storage:
                    hash_code = self.storage[str(last_index)]['hash']
                    request = self.storage[hash_code]
                    if request.exists() and 'step' in request and request['step'] == ProtocolStep.DONE.name:
                        reply.append(request['record'])
                        last_index += 1
                        self.parameters['last_index'] = last_index
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
