import time
from datetime import datetime
import hashlib
import json
import os

from partner import Partner
from execution.blockchain import BlockChain
from mongodb_storage import DBBridge
from contract_view import ContractView

import my_timer

from redis import Redis

class Navigator:
    def __init__(self, identity, one_time, mongo_port, redis_port, logger):
        self.mongo_port = mongo_port
        self.logger = logger
        self.identity = identity
        self.one_time = one_time
        self.redis_port = redis_port
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.communicators = Redis(host='localhost', port=redis_port, db=2)
        self.executioners = Redis(host='localhost', port=redis_port, db=3)
        self.actions = {'GET':  {'is_exist_agent': self.is_exist_agent,
                                 'get_contracts': self.get_contracts},
                        'PUT':  {'register_agent': self.send_to_execution,
                                 'deploy_contract': self.deploy_contract,
                                 'join_contract': self.join_contract,
                                 'a2a_connect': self.send_to_consensus,
                                 'a2a_reply_join': self.send_to_execution,
                                 'a2a_consent': self.a2a_consent,
                                 'a2a_disseminate': self.a2a_disseminate},
                        'POST': {'contract_read': self.contract_read,
                                 'contract_write': self.send_to_consensus,
                                 'get_reply': self.get_reply,
                                 'a2a_get_ledger': self.a2a_get_ledger}}
        self.storage_bridge = None
        self.agents = None
        self.identity_doc = None
        self.contracts_db = None
        self.contracts = {}
        self.ledger = None

    def open(self):
        self.storage_bridge = DBBridge(self.logger).connect(self.mongo_port)
        self.agents = self.storage_bridge.get_root_collection()
        self.identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts') if self.identity_doc.exists() else None
        self.ledger = BlockChain(self.identity_doc, self.logger) if self.identity_doc.exists() else None

    def close(self):
        if self.one_time:
            self.storage_bridge.disconnect()
            self.db.close()
            self.communicators.close()

    def get_contract(self, hash_code):
        if hash_code not in self.contracts_db:
            return None
        if hash_code not in self.contracts:
            self.contracts[hash_code] = ContractView(self.contracts_db[hash_code], hash_code,
                                                 self.identity, self.identity_doc['address'],
                                                 self, self.ledger, self.logger)
            self.contracts[hash_code].run()
        return self.contracts[hash_code]

    def is_exist_agent(self, _record, _direct):
        return self.contracts_db is not None

    def send_to_execution(self, record, _direct):
        self.executioners.lpush('executioners', json.dumps(record['agent']))
        self.executioners.lpush('records_'+record['agent'], json.dumps(record))
        return 'send to execution ' + record['action']

    def get_contracts(self, _record, _direct):
        # a client asks for a list of contracts
        return [{key: self.contracts_db[hash_code][key] for key in self.contracts_db[hash_code]
                 if key in ['id', 'name', 'contract', 'code', 'protocol', 'default_app', 'pid', 'address']}
                for hash_code in (self.contracts_db if self.contracts_db else [])]

    def deploy_contract(self, record, direct):
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
            record['contract'] = record['hash_code']
        self.communicators.lpush('communicators', json.dumps({'identity': self.identity,
                                                              'contract': record['hash_code'],
                                                              'protocol': record['message']['protocol']}))
        self.send_to_execution(record, direct)
        return record['hash_code']

    def join_contract(self, record, _direct):
        message = record['message']
        partner = Partner(message['address'], message['agent'],
                          os.getenv('MY_ADDRESS'), self.identity, None)
        partner.connect(message['contract'], message['profile'])
        self.db.setnx(self.identity + message['contract'], json.dumps({'message': 'no reply yet'}))
        return 'sent join contract request'

    def send_to_consensus(self, record, direct):
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        self.communicators.lpush('record'+self.identity+record['contract'],
                          json.dumps({'initiate': True, 'direct': direct, 'record': record}))
        return self.a2a_post_consent({'message': {'msg': record}}, direct) if direct else {'message': 'sent to consensus'}

    def contract_read(self, record, _direct):
        # a client calls an off chain method
        self.open()
        contract = self.get_contract(record['contract'])
        if not contract:
            reply = {'message': 'no such contract'}
        else:
            reply = contract.call(record, False)
        self.close()
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
        self.open()
        # a partner asks for a ledger history
        index = record['message']['msg']['index']
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        reply = contract.get_ledger(index)
        self.close()
        return reply

    def a2a_disseminate(self, record, _direct):
        original = record['message']['msg']['record']
        action = self.actions[original['type']].get(original['action'])
        action(original, True)
        return {}

    def a2a_post_consent(self, record, direct):
        record = record['message']['msg']
        action = record['action']
        reply = {}
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        if action == 'contract_write':
            reply = contract.call(record, True)
        elif action == 'a2a_connect':
            reply = contract.join(record)
        if not direct:
            self.db.publish(self.identity, record['contract'])
        return reply

    def handle_record(self, record):
        action = self.actions[record['type']].get(record['action'])
        return action(record, False)
