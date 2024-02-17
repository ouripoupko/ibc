class BlockChain:
    def __init__(self, agent_doc):
        self.ledger = agent_doc.get_sub_collection('ledger')

    def log(self, record):
        stored = self.ledger.get_last()
        index = int(stored)+1 if stored else 1
        self.ledger[str(index).zfill(15)] = record
        return index

    def get(self, name):
        return self.ledger.get('contract', '==', name)
