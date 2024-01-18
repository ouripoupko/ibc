from enum import Enum, auto
import hashlib
import json
from redis_json import RedisJson
from redis import Redis

class ProtocolStep(Enum):
    REQUEST = auto()
    PRE_PREPARE = auto()
    PREPARE = auto()
    COMMIT = auto()
    DONE = auto()


class PBFT:
    def __init__(self, contract_name, me, partners, db: RedisJson):
        self.db = db
        if 'state' not in self.db.object_keys(None):
            self.db.set(None, {'requests': {}, 'receipts': {},
                               'state': {'view': 0,
                                         'index': 0,
                                         'step': ProtocolStep.REQUEST.name,
                                         'requests': [],
                                         'hash_code': None,
                                         'block': []}})
        self.state = self.db.get('state')
        self.contract_name = contract_name
        self.me = me
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])
        self.terminate = False
        self.switcher = {ProtocolStep.REQUEST: lambda x: self.receive_request(x),
                         ProtocolStep.PRE_PREPARE: lambda x: self.receive_pre_prepare(x),
                         ProtocolStep.PREPARE: lambda x: self.receive_prepare(x),
                         ProtocolStep.COMMIT: lambda x: self.receive_commit(x)}

    def leader_is_me(self):
        return self.names[self.order[self.state['view']]] == self.me

    def send_request(self, record):
        data = {'o': record,
                't': record['timestamp'],
                'd': record['hash_code'],
                'c': self.me}
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
        self.store_request(data)

    def receive_request(self, data):
        self.store_request(data)

    def store_request(self, data):
        self.state['requests'].append(data['d'])
        self.db.set(f'requests.{data["d"]}', {'record': data['o'],
                                              'timestamp': data['t'],
                                              'client': data['c']})

    def send_pre_prepare(self):
        index = self.state['index']
        # need to pause after connect request, as it might lead to change in partners
        block = []
        while self.state['requests']:
            code = self.state['requests'].pop(0)
            block.append(code)
            request = self.db.get(f'requests.{code}')
            if request['record']['action'] == 'a2a_connect':
                self.terminate = True
                break
        data = {'v': self.state['view'],
                'n': index,
                'd': hashlib.sha256(str(block).encode('utf-8')).hexdigest(),
                'l': block}
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.PRE_PREPARE.name, data)
        self.store_pre_prepare(data)

    def receive_pre_prepare(self, data):
        # I should check signatures and digest, but I am lazy
        if data['v'] != self.state['view']:
            return
        if data['n'] != self.state['index']:
            return
        self.store_pre_prepare(data)

    def store_pre_prepare(self, data):
        self.state['step'] = ProtocolStep.PRE_PREPARE.name
        self.state['hash_code'] = data['d']
        self.state['block'] = data['l']

    def check_pre_prepare(self):
        all_exist = True
        stored = self.db.object_keys('requests')
        for key in self.state['block']:
            if key not in stored:
                all_exist = False
                break
        if all_exist:
            self.state['step'] = ProtocolStep.PREPARE
            self.send_phase(ProtocolStep.PREPARE)

    def send_phase(self, phase):
        data = {'v': self.state['view'],
                'n': self.state['index'],
                'd': self.state['hash_code'],
                'i': self.me}
        for partner in self.partners:
            partner.consent(self.contract_name, phase.name, data)
        self.store_phase(data, phase)

    def receive_prepare(self, data):
        # I should check signatures, but I am lazy
        self.store_phase(data, ProtocolStep.PREPARE)

    def receive_commit(self, data):
        # I should check signatures, but I am lazy
        self.store_phase(data, ProtocolStep.COMMIT)

    def store_phase(self, data, phase):
        # set to empty array if path not yet exists
        self.db.set(f'receipts.{data["d"]}.{phase.name}', [], True)
        self.db.array_append(f'receipts.{data["d"]}.{phase.name}', data)

    def check_phase(self):
        hash_code = self.state['hash_code']
        # set to empty array if path not yet exists
        self.db.set(f'receipts.{hash_code}.{self.state['step']}', [], True)
        receipts = self.db.get(f'receipts.{hash_code}.{self.state['step']}')
        if len(receipts) * 3 > len(self.order) * 2:
            names = set()
            for item in receipts:
                if item['v'] == self.state['view'] and item['n'] == self.state['index']:
                    names.add(item['i'])
            if len(names) * 3 > len(self.order) * 2:
                new_step = ProtocolStep(ProtocolStep[self.state['step']].value + 1)
                self.state['step'] = new_step.name
                if new_step is ProtocolStep.COMMIT:
                    self.send_phase(ProtocolStep.COMMIT)

    def record_message(self, record, executioner: Redis):
        self.state['index'] += 1
        executioner.lpush('execution', json.dumps((self.me, record)))
        self.db.set('state', self.state)

    def handle_request(self, record):
        self.send_request(record)
        if self.state['step'] == ProtocolStep.REQUEST and not self.terminate and self.leader_is_me():
            self.send_pre_prepare()
        self.db.set('state', self.state)

    def handle_consent(self, record, executioner: Redis):
        # self.logger.debug(self.me + ' ' + str(record))
        message = record['message']['msg']
        step = ProtocolStep[message['step']]
        data = message['data']
        self.switcher[step](data)

        if self.state['step'] == ProtocolStep.PRE_PREPARE:
            self.check_pre_prepare()
        if self.state['step'] == ProtocolStep.PREPARE:
            self.check_phase()
        if self.state['step'] == ProtocolStep.COMMIT:
            self.check_phase()
        if self.state['step'] == ProtocolStep.DONE:
            self.execute(executioner)
            self.state['step'] = ProtocolStep.REQUEST
            if self.state['requests'] and not self.terminate and self.leader_is_me():
                self.send_pre_prepare()

        self.db.set('state', self.state)

    def execute(self, executioner):
        for key in self.state['block']:
            request = self.db.get(f'requests.{key}')
            stored_record = request['record']
            stored_record['index'] = self.state['index']
            self.state['index'] += 1
            executioner.lpush('execution', json.dumps((self.me, stored_record)))
        self.state['block'] = []
        self.db.delete(f'requests.{self.state['hash_code']}')
        self.db.delete(f'receipts.{self.state['hash_code']}')

    @staticmethod
    def get_original_record(record):
        message = record['message']['msg']
        step = ProtocolStep[message['step']]
        data = message['data']
        return data['o'] if step == ProtocolStep.REQUEST else None


# should wait on time out from request to change view
# disregard requests with timestamp older than already committed timestamp
