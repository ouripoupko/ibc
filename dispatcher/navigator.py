from datetime import datetime
import hashlib
import json
import os

from common.partner import Partner
from common.blockchain import BlockChain
from common.mongodb_storage import DBBridge
from dispatcher.contract_view import ContractView

from redis import Redis

class Navigator:
    def __init__(self, identity, mongo_port, redis_port, logger):
        self.mongo_port = mongo_port
        self.logger = logger
        self.identity = identity
        self.redis_port = redis_port
        self.db = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
        self.actions = {'GET':  {'is_exist_agent': self.is_exist_agent,
                                 'get_contracts': self.get_contracts},
                        'PUT':  {'register_agent': self.register_agent,
                                 'deploy_contract': self.deploy_contract,
                                 'join_contract': self.join_contract,
                                 'a2a_connect': self.stamp_to_consensus,
                                 'a2a_reply_join': self.send_to_consensus,
                                 'a2a_consent': self.send_to_consensus},
                        'POST': {'contract_read': self.contract_read,
                                 'contract_write': self.stamp_to_consensus,
                                 'a2a_get_ledger': self.a2a_get_ledger}}
        self.storage_bridge = None
        self.agents = None
        self.identity_doc = None
        self.contracts_db = None
        self.ledger = None

    def __del__(self):
        self.db.close()

    def open(self):
        self.storage_bridge = DBBridge().connect(self.mongo_port)
        self.agents = self.storage_bridge.get_root_collection()
        self.identity_doc = self.agents[self.identity]
        if self.identity_doc.exists() and 'contracts' in self.identity_doc and 'ledger' in self.identity_doc:
            self.contracts_db = self.identity_doc.get_sub_collection('contracts')
            self.ledger = BlockChain(self.identity_doc)

    def close(self):
        self.storage_bridge.disconnect()

    def get_contract(self, hash_code):
        if not self.contracts_db or hash_code not in self.contracts_db:
            return None
        contract = ContractView(self.contracts_db[hash_code], hash_code, self, self.ledger, self.logger)
        contract.run()
        return contract

    def is_exist_agent(self, _record):
        self.open()
        reply = self.contracts_db is not None
        self.close()
        return reply

    def register_agent(self, record):
        self.db.lpush('execution', self.identity)
        self.db.lpush('execution:'+self.identity, json.dumps(record))
        self.logger.info('register_agent sent to execution')
        return None

    def get_contracts(self, _record):
        self.open()
        reply = [{key: self.contracts_db[hash_code][key] for key in self.contracts_db[hash_code]
                  if key in ['id', 'name', 'contract', 'code', 'protocol', 'default_app', 'pid', 'address']}
                 for hash_code in (self.contracts_db if self.contracts_db else [])]
        self.close()
        return reply

    def deploy_contract(self, record):
        record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
        record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        record['contract'] = record['hash_code']
        self.send_to_consensus(record)
        return record['hash_code']

    def join_contract(self, record):
        self.open()
        message = record['message']
        partner = Partner(message['address'], message['agent'],
                          self.identity_doc['address'], self.identity, None)
        partner.connect(message['contract'], message['profile'])
        self.close()
        return None

    def stamp_to_consensus(self, record):
        record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
        record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        self.send_to_consensus(record)

    def send_to_consensus(self, record):
        self.db.lpush('consensus', self.identity)
        self.db.lpush('consensus:'+self.identity, json.dumps(record))
        self.logger.warning('i sent consensus')
        return None

    def contract_read(self, record):
        self.open()
        contract = self.get_contract(record['contract'])
        if not contract:
            reply = {'message': 'no such contract'}
        else:
            reply = contract.call(record)
        self.close()
        return reply

    def a2a_get_ledger(self, record):
        self.open()
        index = record['message']['msg']['index']
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'message': 'no such contract'}
        reply = contract.get_ledger(index)
        self.close()
        return reply

    def handle_record(self, record):
        action = self.actions[record['type']].get(record['action'])
        return action(record)
