from collections import deque
from enum import Enum, auto
import logging

from consensus.contract_dialog import ContractDialog
from common.partner import Partner
from common.mongodb_storage import DBBridge

class NavigatorState(Enum):
    INITIAL = auto()
    DIRECT = auto()
    STAGE = auto()
    NORMAL = auto()
    PARTNER = auto()


class ConsensusNavigator:

    def __init__(self, identity, hash_code, redis_port, mongo_port):
        self.identity = identity
        self.logger = logging.getLogger('Navigator')
        contract, partners = self.read_from_storage(mongo_port, hash_code)
        self.contract = ContractDialog(self.identity, hash_code, contract, partners, redis_port)
        self.delay_queue = deque()
        self.actions = {'PUT': {'deploy_contract': self.deploy_contract,
                                'a2a_connect': self.process,
                                'a2a_reply_join': self.a2a_reply_join,
                                'a2a_consent': self.a2a_consent,
                                'int_partner': self.int_partner},
                        'POST': {'contract_write': self.process}}

    def read_from_storage(self, mongo_port, hash_code):
        db_bridge = DBBridge().connect(mongo_port)
        agents = db_bridge.get_root_collection()
        identity_doc = agents[self.identity]
        contract = None
        partners = None
        if identity_doc.exists() and 'contracts' in identity_doc:
            contracts_db = identity_doc.get_sub_collection('contracts')
            contract_doc = contracts_db[hash_code]
            contract = contract_doc.get_dict()
            if contract_doc.exists() and 'pda_partners' in contract_doc:
                partners_db = contract_doc.get_sub_collection('pda_partners')
                partners = {key: partners_db[key]['address'] for key in partners_db}
        db_bridge.disconnect()
        return contract, partners

    def close(self):
        self.contract.close()

    def deploy_contract(self, record, direct):
        self.logger.info('%-15s%s %s', 'deploy', self.identity, record['contract'])
        self.contract.deploy(record['message']['pid'], record['message']['address'], record['message']['protocol'])
        self.contract.process(record, direct)
        while self.delay_queue:
            self.handle_record(self.delay_queue.popleft())

    def a2a_reply_join(self, record, _direct):
        message = record['message']
        self.logger.info('%-15s%s %s', 'reply join', self.identity, message['msg']['pid'])
        status = message['msg']['status']
        if status:
            partner = Partner(message['msg']['address'], message['msg']['pid'],
                              None, self.identity, None)
            records = partner.get_ledger(record['contract'])
            for key in sorted(records.keys()):
                action = self.actions[records[key]['type']].get(records[key]['action'])
                action(records[key], True)

    def process(self, record, direct):
        self.logger.info('%-15s%s %s', 'start protocol', self.identity, record['action'])
        if not self.contract.exists():
            self.delay_queue.append(record)
        else:
            self.contract.process(record, direct)

    def int_partner(self, record, _direct):
        self.logger.info('%-15s%s %s', 'update partner', self.identity, record['message']['msg']['pid'])
        if record['status']:
            message = record['message']['msg']
            self.contract.partner(message['pid'], message['address'])

    def a2a_consent(self, record, _direct):
        self.logger.debug('%s receive consensus from %s step %s hash %s', self.identity, record['message']['from'],
                          record['message']['msg']['step'], record['message']['msg']['data']['d'])
        if not self.contract.exists():
            self.delay_queue.append(record)
        else:
            self.contract.consent(record)

    def handle_record(self, record):
        action = self.actions[record['type']].get(record['action'])
        action(record, False)
