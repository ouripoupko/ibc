from threading import Thread
from redis import Redis
from queue import Queue

from redis_json import RedisJson
from partner import Partner
from pbft import PBFT

def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])

class ContractDialog:
    def __init__(self, identity, my_address, contract, redis_port):
        self.identity = identity
        self.contract = contract
        self.db0 = Redis(host='localhost', port=redis_port, db=0)
        self.db1 = Redis(host='localhost', port=redis_port, db=1)
        self.json_db = RedisJson(self.db1, identity, contract)
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,)).start()
        self.partners = []
        self.protocol = None
        self.my_address = my_address

        if 'contract' not in self.json_db.object_keys(None):
            self.json_db.set('contract', {})
            self.json_db.set('partners', {})
        elif 'protocol' in self.json_db.object_keys('contract'):
            self.create()

    def close(self):
        self.db0.close()
        self.db1.close()

    def deploy(self, agent, address, protocol):
        self.json_db.set('contract', {'protocol': protocol})
        self.create()
        if agent != self.identity:
            self.partner(agent, address)

    def create(self):
        db_contract = self.json_db.get('contract')
        db_partners = self.json_db.get('partners')
        for key, address in db_partners.items():
            if key != self.identity:
                self.partners.append(Partner(address, key, self.my_address, self.identity, self.queue))
        if db_contract['protocol'] == 'BFT':
            self.protocol = PBFT(self.contract, self.identity, self.partners, self.json_db)

    def process(self, record, direct):
        if not self.partners or direct:
            self.protocol.record_message(record, self.db0)
        else:
            self.protocol.send_request(record)

    def consent(self, record):
        self.protocol.handle_consent(record, self.db0)


    def partner(self, agent, address):
        self.json_db.set(f'partners.{agent}', address)
        self.partners = []
        self.create()
