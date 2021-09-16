from contract import Contract


class State:

    def __init__(self, agent_doc, logger):
        self.agent = agent_doc.get_key()
        self.storage = agent_doc.get_sub_collection('contracts')
        self.logger = logger

    def add(self, name, message):
        self.storage[name] = {'pid': message['pid'], 'code': message['code']}
        contract = Contract(self.storage[name], name, message['code'], self.agent, self.logger)
        contract.connect(message['address'], message['pid'], self.agent)
        return f"contract {name} added"

    def welcome(self, name, msg):
        contract = self.get(name)
        contract.connect(msg['address'], msg['pid'], self.agent)

    def get(self, name):
        item = self.storage[name]
        contract = Contract(item, name, item['code'], self.agent, self.logger)
        contract.run(item['pid'])
        return contract

    def trigger(self, msg):
        pass

    def get_state(self, name):
        contract = self.get(name)
        if contract:
            return contract.get_info()
        else:
            return {'reply': 'no such contract'}

    def get_contracts(self):
        return [key for key in self.storage]
