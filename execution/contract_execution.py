from partner import Partner
from queue import Queue
from threading import Thread
from state import State

import my_timer

def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])


class ContractExecution:
    def __init__(self, contract_doc, hash_code, me, my_address, navigator, ledger, logger):
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
        Thread(target=sender, args=(self.queue,), daemon=True).start()
        my_timer.stop(self.me + '_init1', previous)
        # the partners
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        my_timer.stop(self.me + '_init2', previous)
        # consensus protocols
        my_timer.stop(self.me + '_init3', previous)
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
        reply = False
        previous = my_timer.start()
        self.ledger.log(record)
        message = record['message']
        msg = message['msg']
        approve = self.state.call(message['to'],
                                 'approve_partner',
                                 {'values': {'partner': msg['pid']}},
                                 record.get('timestamp', None))
        if approve:
            reply = self.connect(msg['address'], msg['pid'], msg['profile'])
        if message['to'] == self.me:
            partner = Partner(msg['address'], msg['pid'], self.my_address, self.me, self.queue)
            partner.reply_join(self.hash_code, approve)
            print(self.me, 'reply on join request', approve)
        my_timer.stop(self.me + '_join', previous)
        return reply

    def connect(self, address, pid, profile):
        reply = False
        self.partners_db[pid] = {'address': address, 'profile': profile}
        if pid != self.me:
            reply = True
            print(self.me, 'adding new partner', pid)
        return reply

    def call(self, record, should_log):
        previous = my_timer.start()
        if should_log:
            self.ledger.log(record)
        my_timer.stop(self.me + '_call', previous)
        return self.state.call(record['agent'], record['method'], record['message'], record.get('timestamp', None))
