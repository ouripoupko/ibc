from contract import Contract


class State:

    def __init__(self, agent, storage_bridge):
        self.agent = agent
        self.storage_bridge = storage_bridge
        self.storage = storage_bridge.get_collection(agent, 'state')
        self.contracts = {}
        for key in self.storage:
            record = self.storage[key]
            self.contracts[key] = Contract(self.storage_bridge, self.storage, key, record['code'], self.agent)
            self.contracts[key].run(record['pid'])

    def add(self, name, message):
        self.storage[name] = {'pid': message['pid'], 'code': message['code']}
        contract = Contract(self.storage_bridge, self.storage, name, message['code'], self.agent)
        contract.connect(message['address'], message['pid'], self.agent)
        self.contracts[name] = contract
        return contract.run(message['pid'])

    def welcome(self, name, msg):
        contract = self.contracts.get(name)
        contract.connect(msg['address'], msg['pid'], self.agent)

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
