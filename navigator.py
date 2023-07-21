import time
from datetime import datetime
import hashlib
import json
import os

from partner import Partner
from blockchain import BlockChain
from mongodb_storage import DBBridge
from contract import Contract

from redis import Redis

class Waiter:
    pass

class Navigator:
    def __init__(self, identity, one_time, mongo_port, redis_port, logger):
        self.mongo_port = mongo_port
        self.logger = logger
        self.identity = identity
        self.one_time = one_time
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'GET':  {'is_exist_agent': self.is_exist_agent,
                                 'get_contracts': self.get_contracts},
                        'PUT':  {'register_agent': self.register_agent,
                                 'deploy_contract': self.deploy_contract,
                                 'join_contract': self.join_contract,
                                 'a2a_connect': self.a2a_connect,
                                 'a2a_welcome': self.a2a_welcome,
                                 'a2a_consent': self.a2a_consent,
                                 'a2a_disseminate': self.a2a_disseminate},
                        'POST': {'contract_read': self.contract_read,
                                 'contract_write': self.contract_write,
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
            if self.contracts:
                for contract in self.contracts.values():
                    contract.close()
            self.storage_bridge.disconnect()

    def get_contract(self, hash_code):
        if hash_code not in self.contracts_db:
            return None
        if hash_code not in self.contracts:
            self.contracts[hash_code] = Contract(self.contracts_db[hash_code], hash_code,
                                                 self.identity, self.identity_doc['address'],
                                                 self.ledger, self.logger)
            self.contracts[hash_code].run()
        return self.contracts[hash_code]

    def is_exist_agent(self, _record, _direct):
        return self.contracts_db is not None

    def register_agent(self, _record, _direct):
        # a client adds an identity
        self.agents[self.identity] = {'address': os.getenv('MY_ADDRESS')}
        identity_doc = self.agents[self.identity]
        self.contracts_db = self.identity_doc.get_sub_collection('contracts')
        self.ledger = BlockChain(identity_doc, self.logger)
        return True

    def get_contracts(self, _record, _direct):
        # a client asks for a list of contracts
        return [{key: self.contracts_db[hash_code][key] for key in self.contracts_db[hash_code]
                 if key in ['id', 'name', 'contract', 'code', 'protocol', 'default_app', 'pid', 'address']}
                for hash_code in self.contracts_db]

    def deploy_contract(self, record, direct):
        # a client deploys a contract
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
            record['contract'] = record['hash_code']
        hash_code = record['hash_code']
        self.contracts_db[hash_code] = record['message']
        self.contracts[hash_code] = Contract(self.contracts_db[hash_code], hash_code,
                                             self.identity, self.identity_doc['address'],
                                             self.ledger, self.logger)
        return self.handle_consent_records(self.contracts[hash_code].consent(record, True, direct), True)

    def join_contract(self, record, _direct):
        message = record['message']
        record['hash_code'] = message['contract']
        partner = Partner(message['address'], message['agent'],
                          self.identity_doc['address'], self.identity, None)
        partner.connect(message['contract'], message['profile'])
        return Waiter()

    def a2a_connect(self, record, direct):
        # a partner requests to join
        contract = self.get_contract(record['contract'])
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        if not contract:
            return {'reply': 'contract not found'}
        return self.handle_consent_records(contract.consent(record, True, direct), True)

    def a2a_welcome(self, record, _direct):
        # a partner notifies success on join request
        message = record['message']
        partner = Partner(message['msg']['welcome'], message['msg']['pid'],
                          self.identity_doc['address'], self.identity, None)
        records = partner.get_ledger(record['contract'])
        for key in sorted(records.keys()):
            self.handle_record(records[key], True)
        self.db.publish('stream' + self.identity, record['contract'])
        self.db.publish('wait' + self.identity, json.dumps({'key': record['contract'],
                                                            'record': {'reply': 'join success'}}))
        return {}

    def contract_read(self, record, _direct):
        # a client calls an off chain method
        contract = self.get_contract(record['contract'])
        if not contract:
            return {'reply': 'contract not found'}
        else:
            return contract.call(record, False)

    def contract_write(self, record, direct):
        # a client is calling a method
        contract = self.get_contract(record['contract'])
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        if not contract:
            return {'reply': 'contract not found'}
        return self.handle_consent_records(contract.consent(record, True, direct), True)

    def a2a_consent(self, record, _direct):
        # a partner is reporting consensus protocol
        contract = self.get_contract(record['contract'])
        return self.handle_consent_records(contract.consent(record, False, False), False)

    def a2a_get_ledger(self, record, _direct):
        # a partner asks for a ledger history
        index = record['message']['msg']['index']
        contract = self.get_contract(record['contract'])
        return contract.get_ledger(index)

    def a2a_disseminate(self, record, _direct):
        original = record['message']['msg']['record']
        self.handle_record(original, True)
        return {}

    def handle_consent_records(self, records, immediate):
        reply = Waiter()
        for record in records:
            action = record['action']
            contract = self.get_contract(record['contract'])
            if action == 'contract_write':
                reply = contract.call(record, True)
            elif action == 'a2a_connect':
                reply = contract.join(record)
            elif action == 'deploy_contract':
                reply = contract.create(record)
            self.db.publish('stream' + self.identity, record['contract'])
            if not immediate:
                self.db.publish('wait' + self.identity, json.dumps({'key': record['hash_code'],
                                                                    'record': reply}))
        return reply if immediate else {}

    def handle_record(self, record, direct=False):
        # mutex per identity
        if not direct:
            attempts = 0
            while not self.db.setnx(self.identity, 'locked'):
                time.sleep(0.01)
                attempts += 1
                if attempts > 10000:  # 100 seconds
                    return {'reply': 'timeout - could not lock mutex'}
            self.open()

        action = self.actions[record['type']].get(record['action'])
        reply = action(record, direct)
        if not direct:
            self.close()
            self.db.delete(self.identity)
        if isinstance(reply, Waiter):
            channel = self.db.pubsub()
            channel.subscribe('wait' + self.identity)
            while True:
                message = channel.get_message(timeout=180)
                if message:
                    if message.get('type') == 'message':
                        data = json.loads(message.get('data'))
                        if data['key'] == record['hash_code']:
                            reply = data['record']
                            break
                else:
                    reply = {'reply': 'Waited too long for consensus'}
                    break
        return reply
