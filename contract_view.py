import json

from threading import Thread
from state import State

class ContractView(Thread):
    def __init__(self, contract_doc, hash_code, navigator, ledger, logger):
        # the database
        self.contract_doc = contract_doc
        # the contract
        self.hash_code = hash_code
        self.ledger = ledger
        self.logger = logger
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        self.state = State(self.contract_doc, self.partners_db, navigator)

    def run(self):
        self.state.run(self.contract_doc['pid'], self.contract_doc['timestamp'])

    def call(self, record):
        return self.state.call(record['agent'], record['method'], record['message'], record.get('timestamp', None))

    def get_ledger(self, index):
        reply = self.ledger.get(self.hash_code)
        if index > 0:
            reply = reply[index]
        return reply
