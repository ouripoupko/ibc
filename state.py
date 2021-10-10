from contract import Contract
from queue import Queue
from threading import Thread


def sender(queue):
    print('thread running')
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])
    print('thread stopping')


class State:

    def __init__(self, agent_doc, logger):
        self.agent = agent_doc.get_key()
        self.storage = agent_doc.get_sub_collection('contracts')
        self.storage_docs = {}
        self.contracts = {}
        self.logger = logger
        self.queue = Queue()
        Thread(target=sender, args=(self.queue,), daemon=True).start()

    def close(self):
        self.queue.put(True)
        for contract in self.contracts.values():
            contract.close()

    def add(self, name, message, my_address):
        self.storage[name] = {'pid': message['pid'], 'code': message['code']}
        self.get(name)
        self.contracts[name].connect(message['address'], message['pid'], self.agent, my_address, False)
        return f"contract {name} added"

    def welcome(self, name, msg, my_address, welcome):
        self.contracts[name].connect(msg['address'], msg['pid'], self.agent, my_address, welcome)

    def get(self, name):
        self.storage_docs[name] = self.storage[name].get_dict()
        if name not in self.contracts:
            self.contracts[name] = Contract(self.storage[name], name, self.storage_docs[name]['code'],
                                            self.agent, self.logger, self.queue)
            self.contracts[name].run(self.storage_docs[name]['pid'])
        return self.contracts[name]

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
