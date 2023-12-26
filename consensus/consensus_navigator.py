import os
from threading import Thread
from queue import Empty
from collections import deque
from redis import Redis

from contract_dialog import ContractDialog

class ConsensusNavigator(Thread):
    def __init__(self, identity, queue, redis_port, logger):
        self.identity = identity
        self.redis_port = redis_port
        self.logger = logger
        self.queue = queue
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'PUT':  {'deploy_contract': self.deploy_contract,
                                 'a2a_connect': self.process,
                                 'a2a_consent': self.a2a_consent},
                        'POST': {'contract_write': self.process}}
        self.contracts = {}
        super().__init__()

    class Package:
        def __init__(self):
            self.contract = None
            self.delay_queue = deque()
            self.pause_queue = deque()
            self.wait_for_partner : set = set()

    def __del__(self):
        for contract in self.contracts.values():
            contract.close()
        self.db.close()

    def get_contract(self, hash_code):
        if hash_code not in self.contracts:
            self.contracts[hash_code] = self.Package()
        return self.contracts[hash_code]

    def deploy_contract(self, record, direct):
        package = self.get_contract(record['hash_code'])
        package.contract = ContractDialog(self.identity, record['hash_code'], self.redis_port)
        package.contract.deploy(os.getenv('MY_ADDRESS'), record['message']['protocol'])
        package.contract.consent(record, direct)
        for delayed_record in package.delay_queue:
            self.handle_record(delayed_record, False)

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
        processed = package.contract.consent(record, direct)
        if processed and record['action'] == 'a2a_connect':
            package.wait_for_partner.add(record['hash_code'])
        if not direct:
            self.db.publish(self.identity, record['contract'])

    def a2a_consent(self, record, direct):
        package = self.get_verify_contract(record)
        if not package:
            return
        return package.contract.consent(record, direct)

    def handle_record(self, record, direct):
        action = self.actions[record['type']].get(record['action'])
        action(record, direct)

    def a2a_post_connect(self, record):
        package : ConsensusNavigator.Package = self.get_contract(record['contract'])
        if record['status']:
            message = record['message']['msg']
            package.contract.partner(message['pid'], message['address'])
        package.wait_for_partner.remove(record['hash_code'])
        while not package.wait_for_partner and package.pause_queue:
            self.handle_record(package.pause_queue.popleft(), False)

    def run(self):
        while True:
            try:
                record, direct, release = self.queue.get(timeout=60)
            except Empty:
                break
            if release:
                self.a2a_post_connect(record)
            else:
                self.handle_record(record, direct)
