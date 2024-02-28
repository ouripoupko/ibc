from queue import Queue
from threading import Thread

from common.partner import Partner
from common.state import State

def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])


class ContractExecution:
    def __init__(self, contract_doc, hash_code, me, my_address, navigator, ledger):
        # the database
        self.contract_doc = contract_doc
        # the contract
        self.hash_code = hash_code
        self.me = me
        self.my_address = my_address
        self.ledger = ledger
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,), daemon=True).start()
        # the partners
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        # consensus protocols
        self.state = State(self.contract_doc, self.partners_db, navigator)

    def close(self):
        self.queue.put(True)

    def create(self, record):
        self.ledger.log(record)
        self.contract_doc['id'] = self.hash_code
        self.contract_doc['timestamp'] = record['timestamp']
        self.run()
        self.connect(self.contract_doc['address'], self.contract_doc['pid'], self.contract_doc['profile'])
        return True

    def run(self):
        self.state.run(self.contract_doc['pid'], self.contract_doc['timestamp'])

    def join(self, record):
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
        return approve

    def connect(self, address, pid, profile):
        self.partners_db[pid] = {'address': address, 'profile': profile}

    def call(self, record, should_log):
        if should_log:
            self.ledger.log(record)
        return self.state.call(record['agent'], record['method'], record['message'], record.get('timestamp', None))
