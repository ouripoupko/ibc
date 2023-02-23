import hashlib


class Nakamoto:
    def __init__(self, storage, contract_name, me, partners, logger):
        self.db_storage = storage
        self.storage = {}
        for key in storage:
            self.storage[key] = storage[key].get_dict()
        if 'parameters' in self.storage:
            self.parameters = self.storage['parameters']
        else:
            self.parameters = {}
        self.contract_name = contract_name
        self.me = me
        self.logger = logger
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])

    def close(self):
        self.storage['parameters'] = self.parameters
        self.db_storage.store(self.storage)

    def update_partners(self, partners):
        self.partners = partners
        self.names = [partner.pid for partner in self.partners]
        self.names.append(self.me)
        self.order = sorted(range(len(self.names)), key=lambda k: self.names[k])

    def record_message(self, record):
        pass

    def handle_message(self, record, initiate):
        # Each node queries the current state of the ledger for a list of permitted nodes.
        # New transactions are broadcast to all nodes.
        # Each node collects new transactions into a block.
        # Each node calculates its own difficulty level.
        # Each node works on finding a difficult proof-of-work for its block.
        # When a node finds a proof-of-work, it broadcasts the block to all nodes.
        if initiate:
            self.logger.error(record)

        # Nodes accept the block only if all transactions in it are valid and not already spent.
        #   and only if the difficulty level of the block fits the required level for the node that signed it.
        else:
            pass

        # Nodes express their acceptance of the block by working on creating the next block in the chain,
        #   using the hash of the accepted block as the previous hash.
