import os
import json
from threading import Thread
from queue import Queue, Empty
from redis import Redis

from contract_dialog import ContractDialog

class ConsensusNavigator(Thread):
    def __init__(self, identity, queue, redis_port, logger):
        self.identity = identity
        self.redis_port = redis_port
        self.logger = logger
        self.queue = queue
        self.pause_queue = Queue()
        self.wait_for_partner = set()
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'PUT':  {'deploy_contract': self.deploy_contract,
                                 'a2a_connect': self.a2a_connect,
                                 'a2a_consent': self.send_to_protocol},
                        'POST': {'contract_write': self.contract_write}}
        self.contracts = {}
        super().__init__()

    def __del__(self):
        for contract in self.contracts.values():
            contract.close()
        self.db.close()

    def get_contract(self, hash_code):
        if hash_code not in self.contracts:
            self.contracts[hash_code] = ContractDialog(self.identity, hash_code, self.redis_port)
        return self.contracts[hash_code]

    def deploy_contract(self, record, direct):
        hash_code = record['hash_code']
        contract : ContractDialog = self.get_contract(hash_code)
        contract.deploy(os.getenv('MY_ADDRESS'), record['message']['protocol'])
        contract.consent(record, direct)

    def a2a_connect(self, record, direct):
        if self.wait_for_partner and not direct:
            self.pause_queue.put(record)
            return None
        reply = self.send_to_protocol(record, direct)
        if reply:
            self.wait_for_partner.add(record['hash_code'])
        if not direct:
            self.db.publish(self.identity, record['contract'])
        return reply

    def contract_write(self, record, direct):
        if self.wait_for_partner and not direct:
            self.pause_queue.put(record)
            return None
        self.send_to_protocol()
        if not direct:
            self.db.publish(self.identity, record['contract'])
        return {}

    def send_to_protocol(self, record, direct):
        contract = self.get_contract(record['contract'])
        return contract.consent(record, direct)

    def run(self):
        while True:
            try:
                record, direct, release = self.queue.get(timeout=60)
            except Empty:
                break
            if release:
                pass
            else:
                action = self.actions[record['type']].get(record['action'])
                action(record, direct)

# new transaction	    me leader, if send pre prepare and connect tx – raise flag
# new transaction	    me not leader. Send request, continue normal
# new transaction	    flag raised, keep tx in queue
# consensus message	    handle in any case
# direct transaction	handle in any case. If connect tx, raise flag with counter
# release message	    update partners than lower flag
