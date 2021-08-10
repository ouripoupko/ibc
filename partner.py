import threading
import requests
import time
import sys


def delayed_thread(t, url, params, json):
    time.sleep(t)
    requests.put(url, params=params, json=json)


class Partner:
    def __init__(self, address, pid, me):
        self.address = address
        self.pid = pid
        self.me = me

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid, 'address': self.address})

    def connect(self, contract, my_address):
        return requests.post(self.address + 'ibc/app/' + self.pid + '/' + contract,
                             params={'type': 'internal'},
                             json={'from': self.me, 'to': self.pid,
                                   'msg': {'address': my_address, 'pid': self.me}}).json()

    def consent(self, contract, step, data, delay=0):
        threading.Thread(target=delayed_thread,  # requests.post,
                         args=(delay,),
                         kwargs={'url': self.address + 'ibc/app/' + self.pid + '/' + contract,
                                 'params': {'type': 'internal'},
                                 'json': {'from': self.me, 'to': self.pid,
                                          'msg': {'step': step, 'data': data}}}).start()
        return {'reply': 'message sent to partner'}
