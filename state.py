from contract import Contract
from partner import Partner


class State:

    def __init__(self):
        self.contracts = {}

    def add(self, name, code):
        contract = Contract(name)
        contract.init_from_code(code)
        self.contracts[name] = contract
        return contract.run()

    def join(self, ibc, name, msg):
        partner = Partner(msg['address'], msg['id'], ibc.me)
        records = partner.get_contract(name)
        for record in records:
            ibc.handle_contract(record)
        partner.connect(name)

    def get(self, name):
        return self.contracts.get(name)

    def trigger(self, msg):
        pass

    def call(self, msg):
        contract = self.contracts[msg['name']]
        return contract.call(msg['method'], msg['param'])
