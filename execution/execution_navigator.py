from threading import Thread
from datetime import datetime
import hashlib
import json
import os

from partner import Partner
from execution.blockchain import BlockChain
from mongodb_storage import DBBridge
from contract_execution import ContractExecution

import my_timer

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
                                 'join_contract': self.join_contract,
                                 'a2a_connect': self.a2a_connect,
                                 'a2a_reply_join': self.a2a_reply_join,
                                 'a2a_consent': self.a2a_consent,
                                 'a2a_disseminate': self.a2a_disseminate},
                        'POST': {'contract_read': self.contract_read,
                                 'contract_write': self.contract_write,
                                 'get_reply': self.get_reply,
                                 'a2a_get_ledger': self.a2a_get_ledger}}
        self.contracts = {}
        self.storage_bridge = DBBridge(self.logger).connect(self.mongo_port, allow_write=True)
        self.agents = self.storage_bridge.get_root_collection()
        self.identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts') if self.identity_doc.exists() else None
        self.ledger = BlockChain(self.identity_doc, self.logger) if self.identity_doc.exists() else None
        super().__init__()

    def __del__(self):
        for contract in self.contracts.values():
            contract.close()
        self.storage_bridge.disconnect()
        self.db.close()

    def get_contract(self, hash_code):
        if hash_code not in self.contracts_db:
            return None
        if hash_code not in self.contracts:
            self.contracts[hash_code] = Contract(self.contracts_db[hash_code], hash_code,
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

    def join_contract(self, record, _direct):
        if self.contracts_db is None:
            return {'reply': 'no such identity'}
        message = record['message']
        record['hash_code'] = message['contract']
        partner = Partner(message['address'], message['agent'],
                          self.identity_doc['address'], self.identity, None)
        partner.connect(message['contract'], message['profile'])
        self.db.setnx(self.identity + message['contract'], json.dumps({'message': 'no reply yet'}))
        return {'reply': message['contract']}

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

    def contract_read(self, record, _direct):
        # a client calls an off chain method
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        else:
            return contract.call(record, False)

    def contract_write(self, record, direct):
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        reply = contract.call(record, True)
        if not direct:
            self.db.publish(self.identity, record['contract'])
        return reply

    def get_reply(self, record, _direct):
        # a client request reply of a previous call
        reply = self.db.get(self.identity + record['message']['reply'])
        return json.loads(reply) if reply else {'message': 'no such record'}

    def a2a_consent(self, record, direct):
        # a partner is reporting consensus protocol
        self.communicators.lpush('record'+self.identity+record['contract'],
                          json.dumps({'initiate': False, 'direct': direct, 'record': record}))

    def a2a_get_ledger(self, record, _direct):
        # a partner asks for a ledger history
        index = record['message']['msg']['index']
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        return contract.get_ledger(index)

    def a2a_disseminate(self, record, _direct):
        original = record['message']['msg']['record']
        action = self.actions[original['type']].get(original['action'])
        action(original, True)
        return {}

    def run(self):
        db = Redis(host='localhost', port=self.redis_port, db=3)
        while True:
            record = json.loads(db.brpop(['records_'+self.identity])[1])
            action = self.actions[record['type']].get(record['action'])
            action(record, False)
