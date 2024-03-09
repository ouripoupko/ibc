from collections import deque
from enum import Enum, auto
import logging
from redis import Redis
import json
import os

from consensus.contract_dialog import ContractDialog
from common.partner import Partner
from common.mongodb_storage import DBBridge


class ConsensusNavigator:

    def __init__(self, identity, hash_code, redis_port, mongo_port):
        self.identity = identity
        self.logger = logging.getLogger('Navigator')
        self.db = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
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
        self.logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'deploy contract', self.identity)
        self.contract.deploy(record['message']['pid'], record['message']['address'], record['message']['protocol'])
        self.contract.process(record, direct)
        while self.delay_queue:
            self.handle_record(self.delay_queue.popleft())

    def a2a_reply_join(self, record, _direct):
        message = record['message']
        self.logger.info('%s ~ %-20s ~ %s ~ %s', record['hash_code'][0:10], 'reply join', self.identity, message['msg']['pid'])
        status = message['msg']['status']
        if status:
            partner = Partner(message['msg']['address'], message['msg']['pid'],
                              None, self.identity, None)
            records = partner.get_ledger(record['contract'])
            for key in sorted(records.keys()):
                action = self.actions[records[key]['type']].get(records[key]['action'])
                action(records[key], True)
        else:
            self.db.publish(self.identity, json.dumps({'contract': None, 'action': 'a2a_reply_join', 'reply': status}))

    def process(self, record, direct):
        self.logger.info('%s ~ %-20s ~ %s ~ %s', record['hash_code'][0:10], 'start protocol', self.identity, record['action'])
        if not self.contract.exists():
            self.delay_queue.append(record)
        else:
            self.contract.process(record, direct)

    def int_partner(self, record, _direct):
        self.logger.info('%s ~ %-20s ~ %s ~ %s', record['hash_code'][0:10], 'update partner', self.identity, record['message']['msg']['pid'])
        if record['status']:
            message = record['message']['msg']
            self.contract.partner(message['pid'], message['address'])

    def a2a_consent(self, record, _direct):
        if not self.contract.exists():
            self.delay_queue.append(record)
        else:
            self.contract.consent(record)

    def handle_record(self, record):
        action = self.actions[record['type']].get(record['action'])
        action(record, False)
