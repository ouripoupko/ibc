import threading
import requests


def delayed_thread(func, url, params, json):
    func(url, params=params, json=json)


class Partner:
    def __init__(self, address, pid, me):
        self.address = address
        self.pid = pid
        self.me = me

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid, 'address': self.address})

    def connect(self, contract, my_address):
        threading.Thread(target=delayed_thread,
                         args=(requests.post,),
                         kwargs={'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                                 'params': {'type': 'internal'},
                                 'json': {'from': self.me, 'to': self.pid,
                                          'msg': {'address': my_address, 'pid': self.me}}}).start()
        return {'reply': 'message sent to partner'}

    def welcome(self, contract, my_address):
        threading.Thread(target=delayed_thread,
                         args=(requests.post,),
                         kwargs={'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                                 'params': {'type': 'internal'},
                                 'json': {'from': self.me, 'to': self.pid,
                                          'msg': {'welcome': my_address, 'pid': self.me}}}).start()
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
        threading.Thread(target=delayed_thread,
                         args=(requests.put,),
                         kwargs={'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                                 'params': {'type': 'internal'},
                                 'json': {'from': self.me, 'to': self.pid,
                                          'msg': {'step': step, 'data': data}}}).start()
        return {'reply': 'message sent to partner'}
