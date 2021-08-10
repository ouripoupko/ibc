class BlockChain:
    def __init__(self, agent_doc):
        self.agent_doc = agent_doc

    def log(self, record):
        ledger = self.agent_doc.get_sub_collection('ledger')
        stored = ledger.get_last()
        index = int(stored)+1 if stored else 1
        ledger[str(index).zfill(15)] = record
        return index

    def get(self, name):
        ledger = self.agent_doc.get_sub_collection('ledger')
        return ledger.get('contract', '==', name)
