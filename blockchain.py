class BlockChain:
    def __init__(self, storage):
        self.chain = storage
        self.index = 1

    def log(self, record):
        self.chain[str(self.index).zfill(15)] = record
        self.index += 1

    def get(self, name):
        return self.chain.get('contract', '==', name)
