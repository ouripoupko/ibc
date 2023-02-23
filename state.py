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

    def add(self, message, my_address, timestamp, hash_code):
        message['id'] = hash_code
        self.storage[hash_code] = message
        self.storage[hash_code]['timestamp'] = timestamp
        self.get(hash_code)
        self.contracts[hash_code].connect(message['address'], message['pid'], self.agent, my_address, False)
        return True

    def welcome(self, hash_code, msg, my_address, welcome):
        self.contracts[hash_code].connect(msg['address'], msg['pid'], self.agent, my_address, welcome)

    def get(self, hash_code):
        if hash_code not in self.storage:
            return None
        self.storage_docs[hash_code] = self.storage[hash_code].get_dict()
        if hash_code not in self.contracts:
            self.contracts[hash_code] = Contract(self.storage[hash_code], hash_code,
                                                 self.storage_docs[hash_code]['code'],
                                                 self.agent, self.logger, self.queue)
            self.contracts[hash_code].run(self.storage_docs[hash_code]['pid'],
                                          self.storage_docs[hash_code]['timestamp'])
        return self.contracts[hash_code]

    def trigger(self, msg):
        pass

    def get_state(self, hash_code):
        contract = self.get(hash_code)
        if contract:
            return contract.get_info()
        else:
            return {'reply': 'no such contract'}

    def get_contracts(self):
        reply =  [{key: self.storage[hash_code][key] for key in self.storage[hash_code]
                   if key in ['id', 'name', 'contract', 'code', 'protocol', 'default_app', 'pid', 'address']}
                  for hash_code in self.storage]
        return reply
