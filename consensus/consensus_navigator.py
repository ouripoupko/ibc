import os
from threading import Thread
from queue import Empty
from collections import deque
from redis import Redis

from contract_dialog import ContractDialog
from partner import Partner

class ConsensusNavigator(Thread):
    def __init__(self, identity, queue, redis_port, logger):
        self.identity = identity
        self.redis_port = redis_port
        self.logger = logger
        self.queue = queue
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'PUT':  {'deploy_contract': self.deploy_contract,
                                 'a2a_connect': self.process,
                                 'a2a_consent': self.a2a_consent,
                                 'a2a_reply_join': self.a2a_reply_join,
                                 'int_partner': self.int_partner},
                        'POST': {'contract_write': self.process}}
        self.packages = {}
        super().__init__()

    class Package:
        def __init__(self):
            self.contract = None
            self.delay_queue = deque()
            self.pause_queue = deque()
            self.wait_for_partner : set = set()

    def close(self):
        for package in self.packages.values():
            package.contract.close()
        self.db.close()

    def get_contract(self, hash_code):
        if hash_code not in self.packages:
            self.packages[hash_code] = self.Package()
        return self.packages[hash_code]

    def deploy_contract(self, record, direct):
        package = self.get_contract(record['hash_code'])
        package.contract = ContractDialog(self.identity, os.getenv('MY_ADDRESS'), record['hash_code'], self.redis_port)
        package.contract.deploy(record['message']['pid'], record['message']['address'], record['message']['protocol'])
        package.contract.consent(record, direct)

    def get_verify_contract(self, record):
        package = self.get_contract(record['contract'])
        if not package.contract:
            package.delay_queue.append(record)
            return None
        return package

    def process(self, record, direct):
        package = self.get_verify_contract(record)
        if not package:
            return
        if package.wait_for_partner and not direct:
            package.pause_queue.append(record)
            return
        # if protocol returns True, the record initiated consensus protocol
        package.contract.consent(record, direct)
        if record['action'] == 'a2a_connect':
            package.wait_for_partner.add(record['hash_code'])
            print(self.identity, 'wait for', record['message']['msg']['pid'], record['hash_code'])
        if not direct:
            self.db.publish(self.identity, record['contract'])

    def a2a_consent(self, record, direct):
        package = self.get_verify_contract(record)
        if package:
            package.contract.consent(record, direct)
            original = package.contract.protocol.get_original_record(record)
            if original and original['action'] == 'a2a_connect':
                package.wait_for_partner.add(original['hash_code'])
                print(self.identity, 'wait for', original['message']['msg']['pid'], original['hash_code'])

    def a2a_reply_join(self, record, _direct):
        message = record['message']
        status = message['msg']['status']
        if status:
            partner = Partner(message['msg']['address'], message['msg']['pid'],
                              os.getenv('MY_ADDRESS'), self.identity, None)
            records = partner.get_ledger(record['contract'])
            for key in sorted(records.keys()):
                action = self.actions[records[key]['type']].get(records[key]['action'])
                action(records[key], True)
            package = self.get_contract(record['contract'])
            while package and package.delay_queue:
                self.handle_record(package.delay_queue.popleft(), False)
        return {}

    def handle_record(self, record, direct):
        action = self.actions[record['type']].get(record['action'])
        action(record, direct)

    def int_partner(self, record, _direct):
        package : ConsensusNavigator.Package = self.get_contract(record['contract'])
        if record['status']:
            message = record['message']['msg']
            package.contract.partner(message['pid'], message['address'])
        print(self.identity, 'partner came back', record['hash_code'])
        package.wait_for_partner.remove(record['hash_code'])
        while not package.wait_for_partner and package.pause_queue:
            self.handle_record(package.pause_queue.popleft(), False)

    def run(self):
        while True:
            try:
                record = self.queue.get(timeout=60)
                self.handle_record(record, False)
            except Empty:
                break
        self.close()
