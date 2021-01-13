class BlockChain:
    def __init__(self):
        self.chain = []

    def log(self, record):
        self.chain.append(record)

    def get(self, name):
        return [record for record in self.chain if record['params']['contract'] == name]
