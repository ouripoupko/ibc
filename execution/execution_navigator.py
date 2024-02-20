from threading import Thread
import json
import os
import logging
from redis import Redis

from common.blockchain import BlockChain
from common.mongodb_storage import DBBridge
from execution.contract_execution import ContractExecution

class ExecutionNavigator(Thread):
    def __init__(self, identity, mongo_port, redis_port):
        self.identity = identity
        self.mongo_port = mongo_port
        self.redis_port = redis_port
        self.logger = logging.getLogger('Navigator')
        self.db = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
        self.actions = {'PUT':  {'register_agent': self.register_agent,
                                 'deploy_contract': self.deploy_contract,
                                 'a2a_connect': self.a2a_connect},
                        'POST': {'contract_write': self.contract_write}}
        self.contracts = {}
        self.storage_bridge = DBBridge().connect(self.mongo_port, allow_write=True)
        self.agents = self.storage_bridge.get_root_collection()
        self.identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts') if self.identity_doc.exists() else None
        self.ledger = BlockChain(self.identity_doc) if self.identity_doc.exists() else None
        super().__init__()

    def close(self):
        for contract in self.contracts.values():
            contract.close()
        self.storage_bridge.disconnect()
        self.db.close()

    def get_contract(self, hash_code):
        if hash_code not in self.contracts_db:
            return None
        if hash_code not in self.contracts:
            self.contracts[hash_code] = ContractExecution(self.contracts_db[hash_code], hash_code,
                                                 self.identity, self.identity_doc['address'],
                                                 self, self.ledger)
            self.contracts[hash_code].run()
        return self.contracts[hash_code]

    def register_agent(self, record):
        # a client adds an identity
        self.logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'register agent', self.identity)
        self.identity_doc['address'] = record['message']['address']
        self.contracts_db = self.identity_doc.get_sub_collection('contracts')
        self.ledger = BlockChain(self.identity_doc)

    def deploy_contract(self, record):
        if self.contracts_db is None:
            self.logger.warning('unregistered agent tried to deploy contract')
            return
        self.logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'deploy contract', self.identity)
        hash_code = record['hash_code']
        self.contracts_db[hash_code] = record['message']
        contract = ContractExecution(self.contracts_db[hash_code], hash_code,
                                     self.identity, self.identity_doc['address'],
                                     self, self.ledger)
        self.contracts[hash_code] = contract
        contract.create(record)
        self.db.publish(self.identity, record['contract'])

    def a2a_connect(self, record):
        self.logger.info('%s ~ %-20s ~ %s ~ %s', record['hash_code'][0:10], 'a2a connect', self.identity, record['message']['msg']['pid'])
        contract = self.get_contract(record['contract'])
        record['status'] = contract.join(record)
        record['action'] = 'int_partner'
        self.db.lpush('consensus', json.dumps((self.identity, record)))
        self.db.publish(self.identity, record['contract'])

    def contract_write(self, record):
        self.logger.info('%s ~ %-20s ~ %s ~ %s', record['hash_code'][0:10], 'contract write', self.identity, record['method'])
        contract = self.get_contract(record['contract'])
        contract.call(record, True)
        self.db.publish(self.identity, record['contract'])

    def run(self):
        try:
            self.logger.info('%s ~ %-20s ~ %s', '----------', 'thread start', self.identity)
            while True:
                message = self.db.brpop(['execution:'+self.identity], 60)
                if not message:
                    break
                record = json.loads(message[1])
                action = self.actions[record['type']].get(record['action'])
                action(record)
            self.logger.info('%s ~ %-20s ~ %s', '----------', 'exit thread',self.identity)
            self.close()
        except Exception as e:
            self.logger.exception('Unhandled exception caught')

# BlockChain and ContractExecution are generated in two places. looks like a bug