import requests


class Partner:
    def __init__(self, address, pid, me):
        self.address = address
        self.pid = pid
        self.me = me

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid})

    def call(self, params):
        return requests.post(self.address + 'contract/', json={'from': self.me, 'to': self.pid, 'msg': params}).json()

    def get_contract(self, contract):
        reply = requests.get(self.address + 'partner/',
                             json={'from': self.me, 'to': self.pid, 'contract': contract}).json()
        return reply['reply']

    def connect(self, contract, my_address):
        return requests.put(self.address + 'partner/',
                            json={'from': self.me, 'to': self.pid, 'contract': contract,
                                  'msg': {'address': my_address, 'id': self.me}}).json()
