
from contract import Contract

class State:

  def __init__(self):
    self.contracts = {}
    
  def add(self, name, code, network):
    contract = Contract(name, code)
    self.contracts[name] = contract
    return contract.run(network)
    
  def trigger(self, msg):
    pass
    
  def call(self, msg):
    contract = self.contracts[msg['name']]
    return contract.call(msg['method'], msg['param'])
