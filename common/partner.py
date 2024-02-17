import requests
import logging


class Partner:
    def __init__(self, address, pid, my_address, me, queue):
        self.address = address
        self.pid = pid
        self.my_address = my_address
        self.me = me
        self.queue = queue
        self.logger = logging.getLogger('Partner')

    def __repr__(self):
        return str({'class': 'Partner', 'id': self.pid, 'address': self.address})

    def connect(self, contract, profile):
        return requests.put(self.address + '/ibc/app/' + self.pid + '/' + contract,
                            params={'action': 'a2a_connect'},
                            json={'from': self.me, 'to': self.pid,
                                  'msg': {'address': self.my_address, 'pid': self.me, 'profile': profile}})

    def reply_join(self, contract, status):
        self.queue.put({'func': requests.put,
                        'url': self.address + '/ibc/app/' + self.pid + '/' + contract,
                        'params': {'action': 'a2a_reply_join'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'address': self.my_address, 'pid': self.me, 'status': status}}})
        return {'reply': 'message sent to partner'}

    def get_ledger(self, contract, index = 0):
        return requests.post(self.address + '/ibc/app/' + self.pid + '/' + contract,
                             params={'action': 'a2a_get_ledger'},
                             json={'from': self.me, 'to': self.pid,
                                   'msg': {'index': index, 'pid': self.me}}).json()

    def consent(self, contract, step, data):
        self.queue.put({'func': requests.put,
                        'url': self.address + '/ibc/app/' + self.pid + '/' + contract,
                        'params': {'action': 'a2a_consent'},
                        'json': {'from': self.me, 'to': self.pid,
                                 'msg': {'step': step, 'data': data}}})
        self.logger.info('p sent to ibc')
        return {'reply': 'message sent to partner'}
