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
    def __init__(self, contract_name, me, partners, db: RedisJson, executioner: Redis):
        self.db = db
        self.executioner = executioner
        if 'state' not in self.db.object_keys(None):
            self.db.merge(None, {'requests': {}, 'receipts': {},
                               'state': {'view': 0,
                                         'index': 0,
                                         'step': ProtocolStep.REQUEST.name,
                                         'requests': [],
                                         'sent': {},
                                         'hash_code': None,
                                         'block': [],
                                         'direct': []}})
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
        self.handle_cache()

    def leader_is_me(self):
        return self.names[self.order[self.state['view']]] == self.me

    def check_terminate(self, record):
        if record['action'] == 'a2a_connect':
            self.terminate = True
        return self.terminate

    def up_to_a2a_connect(self, records):
        block = []
        for code in records:
            block.append(code)
            request = self.db.get(f'requests.{code}')
            if self.check_terminate(request['record']):
                break
        return block

    def handle_cache(self):
        directs = self.up_to_a2a_connect(self.state['direct'])
        while directs:
            request = self.db.get(f'requests.{directs.pop(0)}')
            self.execute_direct(request['record'])
        if self.state['direct']:
            self.terminate = True
        for sent, checked in self.state['sent'].items():
            request = self.db.get(f'requests.{sent}')
            self.resend_request(request['record'], checked)
        if not self.terminate and self.state['requests'] and self.leader_is_me():
            self.send_pre_prepare()
        self.db.set('state', self.state)

    def resend_request(self, record, checked):
        data = {'o': record,
                't': record['timestamp'],
                'd': record['hash_code'],
                'c': self.me}
        for partner in self.partners:
            if partner.pid not in checked:
                partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
                self.state['sent'][data['d']].append(partner.pid)
        self.store_request(data)

    def send_request(self, record):
        data = {'o': record,
                't': record['timestamp'],
                'd': record['hash_code'],
                'c': self.me}
        self.state['sent'][data['d']] = []
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
            self.state['sent'][data['d']].append(partner.pid)
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
        block = self.up_to_a2a_connect(self.state['requests'])
        data = {'v': self.state['view'],
                'n': index,
                'd': hashlib.sha256(str(block).encode('utf-8')).hexdigest(),
                'l': block}
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.PRE_PREPARE.name, data)
        self.store_pre_prepare(data)
        self.check_progress()

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
        for request in data['l']:
            self.state['requests'].remove(request)
            self.state['sent'].pop(request, None)

    def check_pre_prepare(self):
        all_exist = True
        stored = self.db.object_keys('requests')
        for key in self.state['block']:
            if key not in stored:
                all_exist = False
                break
        if all_exist:
            self.state['step'] = ProtocolStep.PREPARE.name
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

    def make_sure_array_exists(self, record, phase):
        if record not in self.db.object_keys('receipts'):
            self.db.set(f'receipts.{record}', {phase: []})
        if phase not in self.db.object_keys(f'receipts.{record}'):
            self.db.set(f'receipts.{record}.{phase}', [])

    def store_phase(self, data, phase):
        self.make_sure_array_exists(data['d'], phase.name)
        self.db.array_append(f'receipts.{data["d"]}.{phase.name}', data)

    def check_phase(self):
        hash_code = self.state['hash_code']
        self.make_sure_array_exists(hash_code, self.state['step'])
        receipts = self.db.get(f'receipts.{hash_code}.{self.state["step"]}')
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

    def execute_direct(self, record, clean_up = False):
        self.state['index'] += 1
        self.executioner.lpush('execution', json.dumps((self.me, record)))
        if clean_up:
            self.db.delete(f'requests.{record["hash_code"]}')

    def handle_direct(self, record):
        if self.terminate:
            self.db.set(f'requests.{record["hash_code"]}', {'record': record})
            self.state['direct'].append(record['hash_code'])
        else:
            self.execute_direct(record)
            self.check_terminate(record)
        self.db.set('state', self.state)

    def handle_request(self, record):
        self.send_request(record)
        if self.state['step'] == ProtocolStep.REQUEST.name and not self.terminate and self.leader_is_me():
            self.send_pre_prepare()
        self.db.set('state', self.state)

    def handle_consent(self, record):
        # self.logger.debug(self.me + ' ' + str(record))
        message = record['message']['msg']
        step = ProtocolStep[message['step']]
        data = message['data']
        self.switcher[step](data)
        self.check_progress()
        self.db.set('state', self.state)

    def check_progress(self):
        if self.state['step'] == ProtocolStep.PRE_PREPARE.name:
            self.check_pre_prepare()
        if self.state['step'] == ProtocolStep.PREPARE.name:
            self.check_phase()
        if self.state['step'] == ProtocolStep.COMMIT.name:
            self.check_phase()
        if self.state['step'] == ProtocolStep.DONE.name:
            self.execute()
            self.state['step'] = ProtocolStep.REQUEST.name
            if self.state['requests'] and not self.terminate and self.leader_is_me():
                self.send_pre_prepare()

    def execute(self):
        for key in self.state['block']:
            request = self.db.get(f'requests.{key}')
            stored_record = request['record']
            stored_record['index'] = self.state['index']
            self.state['index'] += 1
            self.executioner.lpush('execution', json.dumps((self.me, stored_record)))
        self.state['block'] = []
        self.db.delete(f'requests.{self.state["hash_code"]}')
        self.db.delete(f'receipts.{self.state["hash_code"]}')



# should wait on time out from request to change view
# disregard requests with timestamp older than already committed timestamp
