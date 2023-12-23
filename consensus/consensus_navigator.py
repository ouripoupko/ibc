from threading import Thread
from queue import Queue, Empty
import json
import os

from partner import Partner
from execution.blockchain import BlockChain

import my_timer

from redis import Redis

class ConsensusNavigator(Thread):
    def __init__(self, identity, queue, redis_port, logger):
        self.identity = identity
        self.redis_port = redis_port
        self.logger = logger
        self.main_queue = queue[0]
        self.release_queue = queue[1]
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'PUT':  {'register_agent': self.register_agent,
                                 'deploy_contract': self.deploy_contract,
                                 'a2a_connect': self.a2a_connect,
                                 'a2a_reply_join': self.a2a_reply_join,
                                 'a2a_disseminate': self.a2a_disseminate},
                        'POST': {'contract_write': self.contract_write}}
        self.contracts = {}
        super().__init__()

    def __del__(self):
        for contract in self.contracts.values():
            contract.close()
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

    def register_agent(self, _record, _direct):
        # a client adds an identity
        self.agents[self.identity] = {'address': os.getenv('MY_ADDRESS')}
        identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts')
        self.ledger = BlockChain(identity_doc, self.logger)
        print('registered agent', self.identity)

    def deploy_contract(self, record, direct):
        if self.contracts_db is None:
            return
        hash_code = record['hash_code']
        self.contracts_db[hash_code] = record['message']
        contract = ContractExecution(self.contracts_db[hash_code], hash_code,
                                     self.identity, self.identity_doc['address'],
                                     self, self.ledger, self.logger, self.redis_port)
        self.contracts[hash_code] = contract
        if not direct:
            self.db.publish(self.identity, record['contract'])
        contract.create(record)
        print(self.identity, 'execution notifies communicator on deploy contract', record['hash_code'])
        self.communicators.lpush('communicators', json.dumps({'identity': self.identity,
                                                              'contract': record['hash_code'],
                                                              'protocol': record['message']['protocol']}))

    def a2a_reply_join(self, record, _direct):
        # a partner notifies success on join request
        message = record['message']
        status = message['msg']['status']
        if status:
            partner = Partner(message['msg']['address'], message['msg']['pid'],
                              self.identity_doc['address'], self.identity, None)
            records = partner.get_ledger(record['contract'])
            for key in sorted(records.keys()):
                action = self.actions[records[key]['type']].get(records[key]['action'])
                action(records[key], True)
        self.db.publish(self.identity, record['contract'])
        return {}

    def a2a_connect(self, record, direct):
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        reply = contract.join(record)
        if not direct:
            self.db.publish(self.identity, record['contract'])
        return reply

    def contract_write(self, record, direct):
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        contract.call(record, True)
        if not direct:
            self.db.publish(self.identity, record['contract'])
        return {}

    def a2a_disseminate(self, record, _direct):
        original = record['message']['msg']['record']
        action = self.actions[original['type']].get(original['action'])
        action(original, True)
        return {}

    def run(self):
        while True:
            try:
                record, direct = self.main_queue.get(timeout=60)
            except Empty:
                break
            action = self.actions[record['type']].get(record['action'])
            action(record, direct)
            if record['action'] == 'a2a_connect':
                record = self.release_queue.get()
