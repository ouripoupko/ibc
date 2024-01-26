import os
from collections import deque
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

    def __init__(self, identity, contract_code, redis_port, logger, timer):
        self.identity = identity
        self.logger = logger
        self.timer = timer
        self.contract = ContractDialog(self.identity, os.getenv('MY_ADDRESS'), contract_code, redis_port, logger, timer)
        self.delay_queue = deque()
        self.actions = {'PUT': {'deploy_contract': self.deploy_contract,
                                'a2a_connect': self.process,
                                'a2a_reply_join': self.a2a_reply_join,
                                'a2a_consent': self.a2a_consent,
                                'int_partner': self.int_partner},
                        'POST': {'contract_write': self.process}}

    def close(self):
        self.contract.close()

    def deploy_contract(self, record, direct):
        self.logger.debug('%s: deploy contract:-: %s', self.identity, record['contract'])
        self.contract.deploy(record['message']['pid'], record['message']['address'], record['message']['protocol'])
        self.contract.process(record, direct)
        while self.delay_queue:
            self.handle_record(self.delay_queue.popleft())

    def a2a_reply_join(self, record, _direct):
        self.logger.debug('%s: got reply join: %s', self.identity, record)
        message = record['message']
        status = message['msg']['status']
        if status:
            partner = Partner(message['msg']['address'], message['msg']['pid'],
                              os.getenv('MY_ADDRESS'), self.identity, None, self.logger)
            records = partner.get_ledger(record['contract'])
            for key in sorted(records.keys()):
                action = self.actions[records[key]['type']].get(records[key]['action'])
                action(records[key], True)

    def process(self, record, direct):
        self.logger.debug('%s: initiate consensus: %s: %s', self.identity, record['action'], record)
        if not self.contract.exists():
            self.delay_queue.append(record)
        else:
            self.contract.process(record, direct)

    def int_partner(self, record, _direct):
        self.timer.start(self.identity + '_partner')
        if self.identity == 'agent_00000':
            self.logger.info('%s: update partner: %s', self.identity, record['message']['msg']['pid'])
        if record['status']:
            message = record['message']['msg']
            self.contract.partner(message['pid'], message['address'])
        self.timer.stop(self.identity + '_partner')

    def a2a_consent(self, record, _direct):
        self.logger.debug('%s: receive consensus %s: %s: %s', self.identity, record['message']['from'],
                          record['message']['msg']['step'], record['message']['msg']['data']['d'])
        if not self.contract.exists():
            self.timer.start(self.identity + '_consent1')
            self.delay_queue.append(record)
            self.timer.stop(self.identity + '_consent1')
        else:
            self.timer.start(self.identity + '_consent2')
            self.contract.consent(record)
            self.timer.stop(self.identity + '_consent2')

    def handle_record(self, record):
        action = self.actions[record['type']].get(record['action'])
        action(record, False)

# initializing this process from redis creates synchronization issue between redis and mongo. not good.