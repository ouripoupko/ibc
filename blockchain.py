class BlockChain:
    def __init__(self, storage_bridge, agent):
        self.storage_bridge = storage_bridge
        self.agent = agent

    @staticmethod
    def transactional_log(ledger, record):
        stored = None
        for stored in ledger:
            pass
        index = int(stored)+1 if stored else 1
        ledger[str(index).zfill(15)] = record
        return index

    def log(self, record):
        transaction = self.storage_bridge.get_transaction()
        ledger = self.storage_bridge.get_collection(self.agent, 'ledger', transaction=transaction)
        return self.storage_bridge.execute_transaction(transaction, self.transactional_log, ledger, record)

    def get(self, name):
        ledger = self.storage_bridge.get_collection(self.agent, 'ledger')
        return ledger.get('contract', '==', name)
