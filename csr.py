

class CSR:

  def __init__(self, network):
    self.community = []
    self.edges = []
    self.network = network

  def triggerEdge(self, data):
    return self.network.partners[data['id']].call({'name':'CSR', 'method':'addEdge', 'param':{'id':self.network.me}})

  def addEdge(self, data):
    return {'reply': 'addEdge called'}
    
  def removeEdge(self, data):
    return {'reply': 'addEdge called'}
    
  def addMember(self, data):
    self.community.append(data['id'])
    return {'community': self.community}
    
  def removeMember(self, data):
    return {'reply': 'addEdge called'}

