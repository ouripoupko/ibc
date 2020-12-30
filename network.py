
from partner import Partner

class Network:
  def __init__(self, me):
    self.me = me
    self.partners = {}
    
  def addPartner(self, addr, pid, contract):
    if pid not in self.partners:
      self.partners[pid] = Partner(addr, pid, self.me)
    self.partners[pid].addContract(contract)
