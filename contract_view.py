import json

from threading import Thread
from state import State

import my_timer

class ContractView(Thread):
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
        my_timer.stop(self.me + '_init1', previous)
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        self.state = State(self.contract_doc, self.partners_db, navigator)
        my_timer.stop(self.me + '_init6', previous)

    def run(self, m = True):
        previous = my_timer.start()
        self.state.run(self.contract_doc['pid'], self.contract_doc['timestamp'])
        if m:
            my_timer.stop(self.me + '_run', previous)

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
