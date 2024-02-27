from enum import Enum, auto
import hashlib
import json
from redis import Redis
import logging

from consensus.redis_json import RedisJson

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
        self.logger = logging.getLogger('PBFT')
        if 'state' not in self.db.object_keys(None):
            self.db.merge(None, {'requests': {}, 'receipts': {},
                               'state': {'view': 0,
                                         'index': 0,
                                         'step': ProtocolStep.REQUEST.name,
                                         'requests': [],
                                         'sent': {},
                                         'pre_prepare': [],
                                         'hash_code': None,
                                         'block': [],
                                         'direct': []}})
        self.state = self.db.get('state')
        self.requests = self.db.get('requests')
        self.receipts = self.db.get('receipts')
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
        self.run_protocol()

    def close(self):
        self.db.set('state', self.state)
        self.db.set('receipts', self.receipts)
        self.db.set('requests', self.requests)

    def leader_is_me(self):
        return self.names[self.order[self.state['view']]] == self.me

    def check_terminate(self, record, enforce = True):
        should_terminate = record['action'] == 'a2a_connect'
        if should_terminate and enforce:
            self.terminate = True
        return should_terminate

    def up_to_a2a_connect(self, records):
        block = []
        for code in records:
            block.append(code)
            request = self.requests[code]
            if self.check_terminate(request['record'], False):
                break
        return block

    def check_request(self):
        directs = self.up_to_a2a_connect(self.state['direct'])
        while directs and not self.terminate:
            request = self.requests[directs.pop(0)]
            self.execute_direct(request['record'], True)
        for sent, checked in self.state['sent'].items():
            request = self.requests[sent]
            self.resend_request(request['record'], checked)
        if not self.terminate:
            if self.state['pre_prepare']:
                self.receive_pre_prepare(self.state['pre_prepare'].pop(0))
            elif self.state['requests'] and self.leader_is_me():
                self.send_pre_prepare()

    def resend_request(self, record, checked):
        data = {'o': record,
                't': record['timestamp'],
                'd': record['hash_code'],
                'c': self.me}
        for partner in self.partners:
            if partner.pid not in checked:
                partner.consent(self.contract_name, ProtocolStep.REQUEST.name, data)
                self.state['sent'][data['d']].append(partner.pid)

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
        self.requests[data['d']] = {'record': data['o'],
                                    'timestamp': data['t'],
                                    'client': data['c']}

    def send_pre_prepare(self):
        index = self.state['index']
        # need to pause after connect request, as it might lead to change in partners
        block = self.up_to_a2a_connect(self.state['requests'])
        data = {'v': self.state['view'],
                'n': index,
                'd': hashlib.sha256(str(block).encode('utf-8')).hexdigest(),
                'l': block}
        self.logger.info('%s ~ %-20s ~ %s ~ %s', data['d'][0:10], 'send pre prepare', self.me, block)
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.PRE_PREPARE.name, data)
        self.store_pre_prepare(data)

    def receive_pre_prepare(self, data):
        if self.terminate or self.state['step'] != ProtocolStep.REQUEST.name:
            self.state['pre_prepare'].append(data)
            return
        for request in data['l']:
            if request not in self.state['requests']:
                self.state['pre_prepare'].append(data)
                return
        # I should check signatures and digest, but I am lazy
        if data['v'] != self.state['view']:
            return
        if data['n'] < self.state['index']:
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
        stored = self.requests.keys()
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
        if data['n'] < self.state['index']:
            return
        # I should check signatures, but I am lazy
        self.store_phase(data, ProtocolStep.PREPARE)

    def receive_commit(self, data):
        if data['n'] < self.state['index']:
            return
        # I should check signatures, but I am lazy
        self.store_phase(data, ProtocolStep.COMMIT)

    def make_sure_array_exists(self, record, phase):
        if record not in self.receipts:
            self.receipts[record] = {phase: []}
        if phase not in self.receipts[record]:
            self.receipts[record][phase] = []

    def store_phase(self, data, phase):
        self.make_sure_array_exists(data['d'], phase.name)
        self.receipts[data['d']][phase.name].append(data)

    def check_phase(self):
        hash_code = self.state['hash_code']
        self.make_sure_array_exists(hash_code, self.state['step'])
        receipts = self.receipts[hash_code][self.state["step"]]
        if len(receipts) * 3 > len(self.order) * 2:
            names = set()
            for item in receipts:
                if item['v'] == self.state['view'] and item['n'] == self.state['index']:
                    names.add(item['i'])
            if len(names) * 3 > len(self.order) * 2:
                new_step = ProtocolStep(ProtocolStep[self.state['step']].value + 1)
                self.state['step'] = new_step.name
                self.logger.info('%s ~ %-20s ~ %s ~ %s', hash_code[0:10], 'set step', self.me, new_step.name)
                if new_step is ProtocolStep.COMMIT:
                    self.send_phase(ProtocolStep.COMMIT)

    def execute_direct(self, record, clean_up = False):
        self.state['index'] += 1
        self.executioner.lpush('execution', json.dumps((self.me, record)))
        self.logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'execute direct', self.me)
        self.check_terminate(record)
        if clean_up:
            self.requests.pop(record["hash_code"])
            self.state['direct'].remove(record['hash_code'])

    def handle_direct(self, record):
        if self.terminate:
            self.requests[record["hash_code"]] = {'record': record}
            self.state['direct'].append(record['hash_code'])
        else:
            self.execute_direct(record)

    def handle_request(self, record):
        self.send_request(record)
        self.run_protocol()

    def handle_consent(self, record):
        message = record['message']['msg']
        step = ProtocolStep[message['step']]
        data = message['data']
        self.switcher[step](data)
        self.run_protocol()

    def run_protocol(self):
        while True:
            if self.state['step'] == ProtocolStep.REQUEST.name:
                self.check_request()
            if self.state['step'] == ProtocolStep.PRE_PREPARE.name:
                self.check_pre_prepare()
            if self.state['step'] == ProtocolStep.PREPARE.name:
                self.check_phase()
            if self.state['step'] == ProtocolStep.COMMIT.name:
                self.check_phase()
            if self.state['step'] == ProtocolStep.DONE.name:
                self.execute()
                self.state['step'] = ProtocolStep.REQUEST.name
            no_pre_prepare = not self.state['pre_prepare']
            no_requests = not self.state['requests'] or not self.leader_is_me()
            in_the_middle = self.state['step'] != ProtocolStep.REQUEST.name
            if (no_pre_prepare and no_requests) or in_the_middle or self.terminate:
                break

    def execute(self):
        for key in self.state['block']:
            request = self.requests[key]
            stored_record = request['record']
            stored_record['index'] = self.state['index']
            self.state['index'] += 1
            self.executioner.lpush('execution', json.dumps((self.me, stored_record)))
            self.logger.info('%s ~ %-20s ~ %s', stored_record['hash_code'][0:10], 'execute', self.me)
            self.requests.pop(stored_record['hash_code'])
            self.check_terminate(stored_record)
        self.state['block'] = []
        self.receipts.pop(self.state["hash_code"])
        self.state["hash_code"] = None



# should wait on time out from request to change view
# disregard requests with timestamp older than already committed timestamp
