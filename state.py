from contract import Contract
from partner import Partner


class State:

    def __init__(self, agent, storage_bridge):
        self.agent = agent
        self.storage_bridge = storage_bridge
        self.contract_names = storage_bridge.get_collection(agent, agent+'_state')
        self.contracts = {}
        for record in self.contract_names:
            self.contracts[record['name']] = Contract(self.storage_bridge, self.agent, record['name'], record['code'])
            self.contracts[record['name']].run(record['caller'])

    def add(self, caller, name, message):
        self.contract_names.append({'caller': caller, 'name': name, 'code': message['code']})
        contract = Contract(self.storage_bridge, self.agent, name, message['code'])
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
