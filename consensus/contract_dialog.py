from threading import Thread
from redis import Redis
from queue import Queue

from redis_json import RedisJson
from partner import Partner
from pbft import PBFT

from my_timer import Timers

def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])

class ContractDialog:
    def __init__(self, identity, my_address, contract, redis_port, logger, timer):
        self.identity = identity
        self.contract = contract
        self.logger = logger
        self.timer = timer
        self.db0 = Redis(host='localhost', port=redis_port, db=0)
        self.db1 = Redis(host='localhost', port=redis_port, db=1)
        self.json_db = RedisJson(self.db1, identity, contract)
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,)).start()
        self.protocol = None
        self.my_address = my_address
        self.deployed = False
        self.contract_db = None
        self.partners_db = None

        if 'contract' in self.json_db.object_keys(None):
            self.contract_db = self.json_db.get('contract')
            self.partners_db = self.json_db.get('partners')
            self.create()

    def close(self):
        self.json_db.set('contract', self.contract_db)
        self.json_db.set('partners', self.partners_db)
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
                partners.append(Partner(address, key, self.my_address, self.identity, self.queue, self.logger))
        if self.contract_db['protocol'] == 'BFT':
            if self.protocol:
                self.timer.start(self.identity + '_pbft_close')
                self.protocol.close()
                self.timer.stop(self.identity+'_pbft_close')
            self.timer.start(self.identity+'_pbft_open')
            self.protocol = PBFT(self.contract, self.identity, partners, self.json_db, self.db0, self.logger, self.timer)
            self.timer.stop(self.identity + '_pbft_open')
        self.deployed = True

    def process(self, record, direct):
        if direct:
            self.protocol.handle_direct(record)
        else:
            self.protocol.handle_request(record)

    def consent(self, record):
        self.protocol.handle_consent(record)

    def partner(self, agent, address):
        self.partners_db[agent] = address
        self.create()
