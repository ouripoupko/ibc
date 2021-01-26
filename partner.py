import threading
import requests
import time


def delayed_thread(t, url, json):
    time.sleep(t)
    requests.post(url, json=json)


class Partner:
    def __init__(self, address, pid, me):
        self.address = address
        self.pid = pid
        self.me = me

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid, 'address': self.address})

    def call(self, params):
        threading.Thread(target=requests.post,
                         kwargs={'url': self.address + 'contract',
                                 'json': {'from': self.me, 'to': self.pid, 'msg': params}}).start()
        return {'reply': 'message sent to partner'}

    def get_contract(self, contract):
        reply = requests.get(self.address + 'partner',
                             json={'from': self.me, 'to': self.pid, 'contract': contract}).json()
        return reply['reply']

    def connect(self, contract, my_address):
        threading.Thread(target=requests.put,
                         kwargs={'url': self.address + 'partner',
                                 'json': {'from': self.me, 'to': self.pid, 'contract': contract,
                                          'msg': {'address': my_address, 'id': self.me}}}).start()
        return {'reply': 'message sent to partner'}

    def consent(self, contract, step, data, delay=0):
        threading.Thread(target=delayed_thread,  # requests.post,
                         args=(delay,),
                         kwargs={'url': self.address + 'partner',
                                 'json': {'from': self.me, 'to': self.pid, 'contract': contract,
                                          'msg': {'step': step, 'data': data}}}).start()
        return {'reply': 'message sent to partner'}
