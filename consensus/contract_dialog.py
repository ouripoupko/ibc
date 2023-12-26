from threading import Thread
from redis import Redis
import json
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
    def __init__(self, identity, contract, redis_port):
        self.identity = identity
        self.contract = contract
        self.db0 = Redis(host='localhost', port=redis_port, db=0)
        self.db1 = Redis(host='localhost', port=redis_port, db=1)
        self.json_db = RedisJson(self.db1, identity, contract)
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,)).start()
        self.partners = []
        self.protocol = None
        self.created = False
        self.self_address = None

        if 'contract' not in self.json_db.object_keys(None):
            self.json_db.set('contract', {})
            self.json_db.set('partners', {})
        elif 'protocol' in self.json_db.object_keys('contract'):
            self.create()

    def __del__(self):
        self.db0.close()
        self.db1.close()

    def deploy(self, address, protocol):
        self.json_db.set('contract', {'address': address, 'protocol': protocol})
        self.create()

    def create(self):
        db_contract = self.json_db.get('contract')
        db_partners = self.json_db.get('partners')
        for key, address in db_partners.items():
            if key != self.identity:
                self.partners.append(Partner(address, key, db_contract['address'], self.identity, self.queue))
        if db_contract['protocol'] == 'BFT':
            self.protocol = PBFT(self.contract, self.identity, self.partners, self.json_db)
        self.created = True
        self.self_address = db_contract['address']

    def consent(self, record, direct):
        if not self.partners or direct:
            self.protocol.record_message(record)
            reply = True
            self.db0.lpush('execution', json.dumps((self.identity, record)))
        else:
            reply = self.protocol.handle_message(record, self.db0)
        return reply

    def partner(self, agent, address):
        self.json_db.set(f'partners.{agent}', address)
        self.partners.append(Partner(address, agent,
                                     self.self_address, self.identity, self.queue))
        self.protocol.update_partners(self.partners)
