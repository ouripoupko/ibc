import json
import requests

class Partner:
  def __init__(self, addr, pid, me):
    self.addr = addr
    self.pid = pid
    self.me = me
    
    
  def __repr__(self):
    return str({'class': 'Partner', 'id': self.pid})
    
    
  def call(self, params):
    return requests.post(self.addr + 'contract/', json = {'from': self.me, 'to': self.pid, 'msg': params}).json()

