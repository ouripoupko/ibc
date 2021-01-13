from contract import Contract


class State:

    def __init__(self):
        self.contracts = {}

    def add(self, name, code):
        contract = Contract(name)
        contract.init_from_code(code)
        self.contracts[name] = contract
        return contract.run()

    def join(self, ibc, name, msg):
        contract = Contract(name)
        contract.init_from_partner(msg['partner'])

    def get(self, name):
        return self.contracts.get(name)

    def trigger(self, msg):
        pass

    def call(self, msg):
        contract = self.contracts[msg['name']]
        return contract.call(msg['method'], msg['param'])
