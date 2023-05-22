import requests


class Partner:
    def __init__(self, address, pid, my_address, me, queue):
        self.address = address
        self.pid = pid
        self.my_address = my_address
        self.me = me
        self.queue = queue

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid, 'address': self.address})

    def connect(self, contract, profile):
        return requests.put(self.address + 'ibc/app/' + self.pid + '/' + contract,
                            params={'action': 'a2a_connect'},
                            json={'from': self.me, 'to': self.pid,
                                  'msg': {'address': self.my_address, 'pid': self.me, 'profile': profile}})

    def welcome(self, contract):
        self.queue.put({'func': requests.put,
                        'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                        'params': {'action': 'a2a_welcome'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'welcome': self.my_address, 'pid': self.me}}})
        return {'reply': 'message sent to partner'}

    def get_ledger(self, contract, index = 0):
        return requests.post(self.address + 'ibc/app/' + self.pid + '/' + contract,
                             params={'action': 'a2a_get_ledger'},
                             json={'from': self.me, 'to': self.pid,
                                   'msg': {'index': index, 'pid': self.me}}).json()

    def consent(self, contract, step, data):
        self.queue.put({'func': requests.put,
                        'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                        'params': {'action': 'a2a_consent'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'step': step, 'data': data}}})
        return {'reply': 'message sent to partner'}
