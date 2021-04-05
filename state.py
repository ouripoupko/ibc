from contract import Contract
from partner import Partner


class State:

    def __init__(self, agent, storage_bridge):
        self.agent = agent
        self.storage_bridge = storage_bridge
        self.storage = storage_bridge.get_collection(agent, 'state')
        self.contracts = {}
        for key in self.storage:
            record = self.storage[key]
            self.contracts[key] = Contract(self.storage_bridge, self.storage, key, record['code'])
            self.contracts[key].run(record['caller'])

    def add(self, caller, name, message):
        self.storage[name] = {'caller': caller, 'code': message['code']}
        contract = Contract(self.storage_bridge, self.storage, name, message['code'])
        self.contracts[name] = contract
        return contract.run(caller)

    def join(self, ibc, me, name, msg, my_address):
        partner = Partner(msg['address'], msg['pid'], me)
        if my_address:  # my_address is supplied when initiator calls this method
            records = partner.get_contract(name)
            for record in records:
                ibc.handle_record(record, me, False, direct=True)
            partner.connect(name, my_address)
        contract = self.contracts.get(name)
        contract.connect(partner)
        return contract.get_info()

    def get(self, name):
        return self.contracts.get(name)

    def trigger(self, msg):
        pass

    def get_state(self, name):
        contract = self.contracts.get(name)
        if contract:
            return contract.get_info()
        else:
            return {'reply': 'no such contract'}

    def get_contracts(self):
        return [contract.name for contract in self.contracts.values()]

    def listen(self, name):
        self.storage_bridge.listen(self.storage, name, self.contracts[name])
