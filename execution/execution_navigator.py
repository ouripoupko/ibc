from threading import Thread
import json
import os

from execution.blockchain import BlockChain
from mongodb_storage import DBBridge
from contract_execution import ContractExecution

from redis import Redis

class ExecutionNavigator(Thread):
    def __init__(self, identity, mongo_port, redis_port, logger):
        self.identity = identity
        self.mongo_port = mongo_port
        self.redis_port = redis_port
        self.logger = logger
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'PUT':  {'register_agent': self.register_agent,
                                 'deploy_contract': self.deploy_contract,
                                 'a2a_connect': self.a2a_connect},
                        'POST': {'contract_write': self.contract_write}}
        self.contracts = {}
        self.storage_bridge = DBBridge(self.logger).connect(self.mongo_port, allow_write=True)
        self.agents = self.storage_bridge.get_root_collection()
        self.identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts') if self.identity_doc.exists() else None
        self.ledger = BlockChain(self.identity_doc, self.logger) if self.identity_doc.exists() else None
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
                                                 self, self.ledger, self.logger)
            self.contracts[hash_code].run()
        return self.contracts[hash_code]

    def register_agent(self, _record):
        # a client adds an identity
        self.agents[self.identity] = {'address': os.getenv('MY_ADDRESS')}
        identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts')
        self.ledger = BlockChain(identity_doc, self.logger)

    def deploy_contract(self, record):
        if self.contracts_db is None:
            return
        hash_code = record['hash_code']
        self.contracts_db[hash_code] = record['message']
        contract = ContractExecution(self.contracts_db[hash_code], hash_code,
                                     self.identity, self.identity_doc['address'],
                                     self, self.ledger, self.logger)
        self.contracts[hash_code] = contract
        contract.create(record)
        self.db.publish(self.identity, record['contract'])

    def a2a_connect(self, record):
        contract = self.get_contract(record['contract'])
        record['status'] = contract.join(record)
        record['action'] = 'int_partner'
        self.db.lpush('consensus', self.identity)
        self.db.lpush('consensus:'+self.identity, json.dumps(record))
        self.logger.warning('e sent to consensus')
        self.db.publish(self.identity, record['contract'])

    def contract_write(self, record):
        contract = self.get_contract(record['contract'])
        contract.call(record, True)
        self.db.publish(self.identity, record['contract'])

    def run(self):
        while True:
            message = self.db.brpop(['execution:'+self.identity], 60)
            self.logger.warning('e get %s', self.identity)
            if not message:
                break
            record = json.loads(message[1])
            action = self.actions[record['type']].get(record['action'])
            action(record)
            self.logger.warning('e out %s', self.identity)
        self.close()
