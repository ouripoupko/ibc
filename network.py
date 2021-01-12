from partner import Partner


class Network:
    def __init__(self, me):
        self.me = me
        self.partners = {}

    def add_partner(self, address, pid, contract):
        if pid not in self.partners:
            self.partners[pid] = Partner(address, pid, self.me)
        self.partners[pid].add_contract(contract)
