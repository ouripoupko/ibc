

class Contract:
  def __init__(self, name, code):
    self.name = name
    self.code = code
    self.partners = []
    
  def run(self, network):
    exec(self.code)
    self.obj = locals()[self.name](network)
    return {'msg': 'contract {} is running!'.format(self.name)}
    
  def call(self, method, param):
    return getattr(self.obj, method)(param)
    
  def connect(self, address, partner_id):
    self.partners.append((partner_id, address))
