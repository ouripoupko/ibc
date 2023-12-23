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

class ContractDialog(Thread):
    def __init__(self, identity, self_address, contract, protocol, redis_port):
        self.identity = identity
        self.self_address = self_address
        self.contract = contract
        self.db = Redis(host='localhost', port=redis_port, db=2)
        self.executioners = Redis(host='localhost', port=redis_port, db=3)
        self.redis_db = RedisJson(self.db, identity, contract)
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,)).start()

        if 'partners' not in self.redis_db.object_keys(None):
            self.redis_db.set('partners', {})
        self.partners = []
        db_partners = self.redis_db.get('partners')
        for key, address in db_partners.items():
            if key != identity:
                self.partners.append(Partner(address, key, self_address, identity, self.queue))

        self.protocol = None
        if protocol == 'BFT':
            self.protocol = PBFT(contract, identity, self.partners, self.redis_db)

        super().__init__()

    def run(self):
        while True:
            message = self.db.brpop(['record'+self.identity+self.contract])[1]
            message = json.loads(message)
            print('entry point', message)
            wait_for_reply = False

            if not self.partners or message['direct']:
                self.protocol.record_message(message['record'])
                if not message['direct']:
                    self.executioners.lpush('executioners', json.dumps(self.identity))
                    self.executioners.lpush('records_' + self.identity, json.dumps(message['record']))
                    wait_for_reply = True
                    print(self.identity, 'from consensus to execution', message['record']['action'])
            else:
                wait_for_reply = self.protocol.handle_message(message['record'], message['initiate'], self.executioners)

            if wait_for_reply:
                message = json.loads(self.db.brpop(['reply_' + self.identity + self.contract])[1])
                print(self.identity, 'received on wait', message)

                if 'partner' in message:
                    print(self.identity, 'consensus adding partner', message['partner'])
                    self.redis_db.set(f'partners.{message["partner"]}', message['address'])
                    self.partners.append(Partner(message['address'], message['partner'],
                                                 self.self_address, self.identity, self.queue))
                    self.protocol.update_partners(self.partners)
