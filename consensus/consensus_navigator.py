import os
from collections import deque
from redis import Redis
from enum import Enum, auto

from contract_dialog import ContractDialog
from partner import Partner

class NavigatorState(Enum):
    INITIAL = auto()
    DIRECT = auto()
    STAGE = auto()
    NORMAL = auto()
    PARTNER = auto()


class ConsensusNavigator:

    def __init__(self, identity, redis_port, logger):
        self.identity = identity
        self.redis_port = redis_port
        self.logger = logger
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.contract = None
        self.delay_queue = deque()
        self.pause_queue = deque()
        self.wait_for_partner : set = set()
        self.actions = None
        self.state = None
        self.set_state(NavigatorState.INITIAL)

    def set_state(self, state):
        self.state = state
        match state:
            case NavigatorState.INITIAL:
                self.actions = {'PUT': {'deploy_contract': self.deploy_contract,
                                        'a2a_connect': self.delay,
                                        'a2a_consent': self.delay,
                                        'a2a_reply_join': self.a2a_reply_join},
                                'POST': {'contract_write': self.delay}}
            case NavigatorState.DIRECT:
                self.actions = {'PUT': {'deploy_contract': self.deploy_contract,
                                        'a2a_connect': self.process},
                                'POST': {'contract_write': self.process}}
            case NavigatorState.STAGE:
                self.actions = {'PUT': {'a2a_connect': self.delay,
                                        'a2a_consent': self.delay,
                                        'int_partner': self.int_partner},
                                'POST': {'contract_write': self.delay}}
            case NavigatorState.NORMAL:
                self.actions = {'PUT': {'a2a_connect': self.process,
                                        'a2a_consent': self.a2a_consent},
                                'POST': {'contract_write': self.process}}
                self.enter_normal()
            case NavigatorState.PARTNER:
                self.actions = {'PUT': {'a2a_connect': self.delay,
                                        'a2a_consent': self.a2a_consent,
                                        'int_partner': self.int_partner},
                                'POST': {'contract_write': self.delay}}


    def close(self):
        self.contract.close()
        self.db.close()

    def deploy_contract(self, record):
        self.logger.debug('%s: deploy contract:-: %s', self.identity, record['contract'])
        self.contract = ContractDialog(self.identity, os.getenv('MY_ADDRESS'), record['hash_code'], self.redis_port)
        self.contract.deploy(record['message']['pid'], record['message']['address'], record['message']['protocol'])
        self.contract.process(record, self.state == NavigatorState.DIRECT)
        if self.state == NavigatorState.INITIAL:
            self.set_state(NavigatorState.NORMAL)

    def a2a_reply_join(self, record):
        self.logger.debug('%s: got reply join: %s', self.identity, record['message']['msg']['pid'])
        message = record['message']
        status = message['msg']['status']
        if status:
            self.set_state(NavigatorState.DIRECT)
            partner = Partner(message['msg']['address'], message['msg']['pid'],
                              os.getenv('MY_ADDRESS'), self.identity, None)
            records = partner.get_ledger(record['contract'])
            for key in sorted(records.keys()):
                action = self.actions[records[key]['type']].get(records[key]['action'])
                action(records[key])
            self.set_state(NavigatorState.STAGE)

    def delay(self, record):
        self.delay_queue.append(record)

    def process(self, record):
        self.logger.debug('%s: initiate consensus: %s: %s', self.identity, record['action'], record['hash_code'])
        if self.contract.process(record, self.state == NavigatorState.DIRECT):
            self.wait_for_partner.add(record['hash_code'])
            if self.state == NavigatorState.NORMAL:
                self.set_state(NavigatorState.PARTNER)

    def int_partner(self, record):
        self.logger.debug('%s: update partner: %s', self.identity, record['message']['msg']['pid'])
        if record['status']:
            message = record['message']['msg']
            self.contract.partner(message['pid'], message['address'])
        self.wait_for_partner.remove(record['hash_code'])
        if not self.wait_for_partner:
            self.set_state(NavigatorState.NORMAL)

    def enter_normal(self):
        while self.delay_queue:
            self.handle_record(self.delay_queue.popleft())

    def a2a_consent(self, record):
        self.logger.debug('%s: receive consensus %s: %s: %s', self.identity, record['message']['from'],
                          record['message']['msg']['step'], record['message']['msg']['data']['d'])
        original = self.contract.protocol.get_original_record(record)
        if original and self.state == NavigatorState.PARTNER:
            self.delay(record)
        else:
            self.contract.consent(record)
            if original and original['action'] == 'a2a_connect':
                self.wait_for_partner.add(original['hash_code'])
                self.set_state(NavigatorState.PARTNER)

    def handle_record(self, record):
        action = self.actions[record['type']].get(record['action'])
        action(record)
