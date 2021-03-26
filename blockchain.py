class BlockChain:
    def __init__(self, storage):
        self.chain = storage

    def log(self, record):
        self.chain.append(record)

    def get(self, name):
        return [record for record in self.chain if record['contract'] == name]
