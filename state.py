from contract import Contract
from queue import Queue
from threading import Thread


def sender(queue):
    while True:
        item = queue.get()
        if isinstance(item, bool):
            break
        item['func'](item['url'], params=item['params'], json=item['json'])


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

    def add(self, message, my_address, timestamp):
        name = message.get('name')
        if name:
            self.storage[name] = message
            self.storage[name]['timestamp'] = timestamp
            self.get(name)
            self.contracts[name].connect(message['address'], message['pid'], self.agent, my_address, False)
            return True
        else:
            return False

    def welcome(self, name, msg, my_address, welcome):
        self.contracts[name].connect(msg['address'], msg['pid'], self.agent, my_address, welcome)

    def get(self, name):
        if name not in self.storage:
            return None
        self.storage_docs[name] = self.storage[name].get_dict()
        if name not in self.contracts:
            self.contracts[name] = Contract(self.storage[name], name, self.storage_docs[name]['code'],
                                            self.agent, self.logger, self.queue)
            self.contracts[name].run(self.storage_docs[name]['pid'], self.storage_docs[name]['timestamp'])
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
        reply =  [{key: self.storage[name][key] for key in self.storage[name]
                   if key in ['name', 'contract', 'code', 'protocol', 'default_app', 'pid', 'address']}
                  for name in self.storage]
        return reply
