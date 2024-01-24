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
    def __init__(self, identity, my_address, contract, redis_port, logger):
        self.identity = identity
        self.contract = contract
        self.logger = logger
        self.db0 = Redis(host='localhost', port=redis_port, db=0)
        self.db1 = Redis(host='localhost', port=redis_port, db=1)
        self.json_db = RedisJson(self.db1, identity, contract)
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,)).start()
        self.protocol = None
        self.my_address = my_address
        self.timer = Timers()

        if 'contract' in self.json_db.object_keys(None):
            self.create()

    def close(self):
        self.db0.close()
        self.db1.close()

    def exists(self):
        return 'contract' in self.json_db.object_keys(None)

    def deploy(self, agent, address, protocol):
        self.json_db.set('contract', {'protocol': protocol})
        self.json_db.set('partners', {})
        self.partner(agent, address)

    def create(self):
        db_contract = self.json_db.get('contract')
        db_partners = self.json_db.get('partners')
        partners = []
        for key, address in db_partners.items():
            if key != self.identity:
                partners.append(Partner(address, key, self.my_address, self.identity, self.queue))
        if db_contract['protocol'] == 'BFT':
            self.timer.start('create')
            self.protocol = PBFT(self.contract, self.identity, partners, self.json_db, self.db0, self.logger)
            self.timer.stop('create')

    def process(self, record, direct):
        if direct:
            self.timer.start('direct')
            self.protocol.handle_direct(record)
            self.timer.stop('direct')
        else:
            self.timer.start('request')
            self.protocol.handle_request(record)
            self.timer.stop('request')

    def consent(self, record):
        self.timer.start('consent')
        self.protocol.handle_consent(record)
        self.timer.stop('consent')

    def partner(self, agent, address):
        self.json_db.set(f'partners.{agent}', address)
        self.create()
