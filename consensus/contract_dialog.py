from threading import Thread
from redis import Redis
from queue import Queue
import os
import logging

from consensus.redis_json import RedisJson
from common.partner import Partner
from consensus.pbft import PBFT

def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])

class ContractDialog:
    def __init__(self, identity, contract, contract_store, partner_store, redis_port):
        self.identity = identity
        self.contract = contract
        self.logger = logging.getLogger('Dialog')
        self.db0 = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
        self.db1 = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=1)
        self.json_db = RedisJson(self.db1, identity, contract)
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,)).start()
        self.protocol = None
        self.deployed = False
        self.my_address = contract_store['address'] if contract_store else None
        self.contract_db = {'protocol': contract_store['protocol']} if contract_store else None
        self.partners_db = partner_store if partner_store else {}
        if self.contract_db:
            self.create()

    def close(self):
        if self.protocol:
            self.protocol.close()
        self.db0.close()
        self.db1.close()

    def exists(self):
        return self.deployed

    def deploy(self, agent, address, protocol):
        self.contract_db = {'protocol': protocol}
        self.partners_db = {}
        self.partner(agent, address)

    def create(self):
        partners = []
        for key, address in self.partners_db.items():
            if key != self.identity:
                partners.append(Partner(address, key, self.my_address, self.identity, self.queue))
        if self.contract_db['protocol'] == 'BFT':
            if self.protocol:
                self.protocol.close()
            self.protocol = PBFT(self.contract, self.identity, partners, self.json_db, self.db0)
        self.deployed = True

    def process(self, record, direct):
        if direct:
            self.protocol.handle_direct(record)
        else:
            self.protocol.handle_request(record)

    def consent(self, record):
        self.protocol.handle_consent(record)

    def partner(self, agent, address, should_partner = True):
        if should_partner:
            self.partners_db[agent] = address
        self.create()
