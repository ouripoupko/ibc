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

    def add_contract(self, contract):
        return requests.get(self.address + 'partner/',
                            json={'from': self.me, 'to': self.pid, 'msg': {'contract': contract}}).json()
