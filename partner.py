import requests


class Partner:
    def __init__(self, address, pid, me, queue):
        self.address = address
        self.pid = pid
        self.me = me
        self.queue = queue

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid, 'address': self.address})

    def connect(self, contract, my_address):
        self.queue.put({'func': requests.post,
                        'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                        'params': {'type': 'internal'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'address': my_address, 'pid': self.me}}})
        return {'reply': 'message sent to partner'}

    def welcome(self, contract, my_address):
        self.queue.put({'func': requests.post,
                        'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                        'params': {'type': 'internal'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'welcome': my_address, 'pid': self.me}}})
        return {'reply': 'message sent to partner'}

    def get_log(self, contract):
        return requests.get(self.address + 'ibc/app/' + self.pid + '/' + contract,
                            params={'type': 'internal'}).json()

    def catchup(self, contract, my_index):
        return requests.post(self.address + 'ibc/app/' + self.pid + '/' + contract,
                             params={'type': 'internal'},
                             json={'from': self.me, 'to': self.pid,
                                   'msg': {'index': my_index, 'pid': self.me}}).json()

    def consent(self, contract, step, data):
        self.queue.put({'func': requests.put,
                        'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                        'params': {'type': 'internal'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'step': step, 'data': data}}})
        return {'reply': 'message sent to partner'}

    def read(self, contract, method, arguments, values):
        return requests.post(self.address + 'ibc/app/' + self.pid + '/' + contract + '/' + method,
                             params={'type': 'agent_to_agent'},
                             json={'name': method,
                                   'arguments': arguments,
                                   'values': values}).json()
