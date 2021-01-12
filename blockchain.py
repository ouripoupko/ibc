class BlockChain:
    def __init__(self):
        self.chain = []

    def log(self, action, data):
        self.chain.append((action, data))
