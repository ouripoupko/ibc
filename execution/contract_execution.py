import json

from partner import Partner
from nakamoto import Nakamoto
from dissemination import Dissemination
from queue import Queue
from threading import Thread
from state import State
from redis import Redis

import my_timer

def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])


class ContractExecution:
    def __init__(self, contract_doc, hash_code, me, my_address, navigator, ledger, logger, redis_port):
        previous = my_timer.start()
        # the database
        self.contract_doc = contract_doc
        # the contract
        self.hash_code = hash_code
        self.me = me
        self.my_address = my_address
        self.ledger = ledger
        self.logger = logger
        self.queue = Queue()
        self.redis = Redis(host='localhost', port=redis_port, db=2)
        Thread(target=sender, args=(self.queue,), daemon=True).start()
        my_timer.stop(self.me + '_init1', previous)
        # the partners
        self.partners = []
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        my_timer.stop(self.me + '_init2', previous)
        for key in self.partners_db:
            if key != me:
                self.partners.append(Partner(self.partners_db[key]['address'], key, my_address, me, self.queue))
        # consensus protocols
        my_timer.stop(self.me + '_init3', previous)
        self.protocol_storage = self.contract_doc.get_sub_collection('pda_protocols')
        self.protocol = None
        my_timer.stop(self.me + '_init4', previous)
        protocol_name = self.contract_doc['protocol']
        if protocol_name == 'POW':
            self.protocol = Nakamoto(self.protocol_storage, self.hash_code, self.me, self.partners, self.logger)
        elif protocol_name == 'BFT':
            my_timer.stop(self.me + '_init5', previous)
        elif protocol_name == 'Dissemination':
            self.partners = []
            group = self.contract_doc['group']
            if isinstance(group, list):
                for member in group:
                    member_dict = None
                    try:
                        member_dict = json.loads(member)
                    except (Exception,):
                        continue
                    if member_dict and 'address' in member_dict and 'agent' in member_dict:
                        self.partners.append(Partner(member_dict['address'], member_dict['agent'],
                                                     my_address, me, self.queue))
            self.protocol = Dissemination(self.protocol_storage, self.hash_code, self.me,
                                          self.partners, self.contract_doc['threshold'], self.logger)
        self.state = State(self.contract_doc, self.partners_db, navigator)
        my_timer.stop(self.me + '_init6', previous)

    def close(self):
        previous = my_timer.start()
        self.queue.put(True)
        my_timer.stop(self.me + '_close', previous)

    def create(self, record):
        previous = my_timer.start()
        self.ledger.log(record)
        self.contract_doc['id'] = self.hash_code
        self.contract_doc['timestamp'] = record['timestamp']
        self.run(False)
        self.connect(self.contract_doc['address'], self.contract_doc['pid'], self.contract_doc['profile'])
        my_timer.stop(self.me + '_create', previous)
        return self.hash_code

    def run(self, m = True):
        previous = my_timer.start()
        self.state.run(self.contract_doc['pid'], self.contract_doc['timestamp'])
        if m:
            my_timer.stop(self.me + '_run', previous)

    def join(self, record):
        previous = my_timer.start()
        self.ledger.log(record)
        message = record['message']
        msg = message['msg']
        approve = self.state.call(message['to'],
                                 'approve_partner',
                                 {'values': {'partner': msg['pid']}},
                                 record.get('timestamp', None))
        if approve:
            self.connect(msg['address'], msg['pid'], msg['profile'])
        if message['to'] == self.me:
            partner = Partner(msg['address'], msg['pid'], self.my_address, self.me, self.queue)
            partner.reply_join(self.hash_code, approve)
        my_timer.stop(self.me + '_join', previous)
        return {'reply': approve}

    def connect(self, address, pid, profile):
        self.partners_db[pid] = {'address': address, 'profile': profile}
        if pid != self.me:
            partner = Partner(address, pid, self.my_address, self.me, self.queue)
            self.redis.lpush('partner' + self.me + self.hash_code,
                             json.dumps({'partner': pid, 'address': address}))
            self.partners.append(partner)
        return {'reply': 'join success'}

    def call(self, record, should_log):
        previous = my_timer.start()
        if should_log:
            self.ledger.log(record)
        my_timer.stop(self.me + '_call', previous)
        return self.state.call(record['agent'], record['method'], record['message'], record.get('timestamp', None))

    def get_ledger(self, index):
        previous = my_timer.start()
        reply = self.ledger.get(self.hash_code)
        if index > 0:
            reply = reply[index]
        my_timer.stop(self.me + '_get_ledger', previous)
        return reply

