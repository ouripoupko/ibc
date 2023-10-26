import json

from partner import Partner
from pbft import PBFT
from nakamoto import Nakamoto
from dissemination import Dissemination
from queue import Queue
from threading import Thread
from state import State


def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])


class Contract:
    def __init__(self, contract_doc, hash_code, me, my_address, navigator, ledger, logger):
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
        # the partners
        self.partners = []
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        for key in self.partners_db:
            if key != me:
                self.partners.append(Partner(self.partners_db[key]['address'], key, my_address, me, self.queue))
        # consensus protocols
        self.protocol_storage = self.contract_doc.get_sub_collection('pda_protocols')
        self.protocol = None
        protocol_name = self.contract_doc['protocol']
        if protocol_name == 'POW':
            self.protocol = Nakamoto(self.protocol_storage, self.hash_code, self.me, self.partners, self.logger)
        elif protocol_name == 'BFT':
            self.protocol = PBFT(self.protocol_storage, self.hash_code, self.me, self.partners, self.logger)
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

    def close(self):
        self.queue.put(True)
        self.protocol.close()

    def create(self, record):
        self.ledger.log(record)
        self.contract_doc['id'] = self.hash_code
        self.contract_doc['timestamp'] = record['timestamp']
        self.run()
        self.connect(self.contract_doc['address'], self.contract_doc['pid'], self.contract_doc['profile'])
        return self.hash_code

    def run(self):
        self.state.run(self.contract_doc['pid'], self.contract_doc['timestamp'])

    def join(self, record):
        self.ledger.log(record)
        message = record['message']
        msg = message['msg']
        status = self.state.call(message['to'],
                                 'approve_partner',
                                 {'values': {'partner': msg['pid']}},
                                 record.get('timestamp', None))
        if status:
            self.connect(msg['address'], msg['pid'], msg['profile'])
        if message['to'] == self.me:
            partner = Partner(msg['address'], msg['pid'], self.my_address, self.me, self.queue)
            partner.reply_join(self.hash_code, status)
        return {'reply': status}

    def connect(self, address, pid, profile):
        self.partners_db[pid] = {'address': address, 'profile': profile}
        if pid != self.me:
            partner = Partner(address, pid, self.my_address, self.me, self.queue)
            self.partners.append(partner)
            self.protocol.update_partners(self.partners)
        return {'reply': 'join success'}

    def consent(self, record, initiate, direct, executioner):
        # if initiate:
        #     return [partner.pid for partner in self.partners]
        if not self.partners or direct:
            self.protocol.record_message(record)
            reply = executioner([record], direct)
        else:
            reply = self.protocol.handle_message(record, initiate, executioner)
        return reply

    def call(self, record, should_log):
        if should_log:
            self.ledger.log(record)
        return self.state.call(record['agent'], record['method'], record['message'], record.get('timestamp', None))

    def get_ledger(self, index):
        reply = self.ledger.get(self.hash_code)
        if index > 0:
            reply = reply[index]
        return reply
