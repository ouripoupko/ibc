import ast
from contract import Contract
from partner import Partner


class State:

    def __init__(self):
        self.contracts = {}

    def add(self, name, code):
        contract = Contract(name, code)
        self.contracts[name] = contract
        return contract.run()

    def join(self, ibc, name, msg, my_address):
        partner = Partner(msg['address'], msg['id'], ibc.me)
        if my_address:  # my_address is supplied when initiator calls this method
            records = partner.get_contract(name)
            for record in records:
                ibc.handle_contract(record)
            partner.connect(name, my_address)
        contract = self.contracts.get(name)
        contract.connect(partner)
        return ast.literal_eval(repr(contract))

    def get(self, name):
        return self.contracts.get(name)

    def trigger(self, msg):
        pass

    def get_state(self, name):
        contract = self.contracts.get(name)
        if contract:
            return ast.literal_eval(repr(contract))
        else:
            return {'reply': 'no such contract'}

    def get_contracts(self):
        return [contract.name for contract in self.contracts.values()]
