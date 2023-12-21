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

        self.me_partner = Partner(self_address, identity, self_address, identity, self.queue)
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
            channel, message = self.db.brpop(['record'+self.identity+self.contract, 'partner'+self.identity+self.contract])
            message = json.loads(message)
            channel = channel.decode("utf-8")
            print(self.identity, message)
            wait_for_reply = False

            if channel.startswith('record'):
                if not self.partners or message['direct']:
                    self.protocol.record_message(message['record'])
                    if not message['direct']:
                        self.executioners.lpush('executioners', json.dumps(self.identity))
                        self.executioners.lpush('records_' + self.identity, json.dumps(message['record']))
                        wait_for_reply = True
                else:
                    wait_for_reply = self.protocol.handle_message(message['record'], message['initiate'], self.me_partner)

            if wait_for_reply:
                message = json.loads(self.db.brpop(['partner' + self.identity + self.contract])[1])

            if channel.startswith('partner') and 'partner' in message:
                self.redis_db.set(f'partners.{message["partner"]}', message['address'])
                self.partners.append(Partner(message['address'], message['partner'],
                                             self.self_address, self.identity, self.queue))
                self.protocol.update_partners(self.partners)
