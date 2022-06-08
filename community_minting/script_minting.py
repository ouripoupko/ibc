import requests
from sseclient import SSEClient
from threading import Thread, Semaphore
from random import choices, random, randrange
from time import sleep, time
from redis import Redis
from datetime import datetime

server = 'http://localhost:5001/'
agent = 'honest_00000'
contract = 'minting'
redis_port = 6379

lock = Semaphore(0)


def listener():
    messages = SSEClient(f'{server}stream/{agent}/{contract}')
    for msg in messages:
        if msg.data == 'True':
            lock.release()


def transact(method, params):
    requests.put(f'{server}ibc/app/{agent}/{contract}/{method}',
                 json={'name': method,
                       'values': params})


def read(method, params):
    return requests.post(f'{server}ibc/app/{agent}/{contract}/{method}',
                         json={'name': method,
                               'values': params}).json()


db = Redis(host='localhost', port=redis_port, db=1)
Thread(target=listener, daemon=True).start()

f = open(f'{contract}.py', 'r')
requests.post(f'{server}ibc/app/{agent}/{contract}',
              json={'pid': agent, 'address': server, 'code': f.read()})
f.close()

print('initializing')
transact('initialize', {'address': server, 'agent': agent, 'contract': 'community'})
lock.acquire()

print('first update')
transact('update_balances', {})
lock.acquire()
timers = read('get_timers', {})
print(datetime.strptime(timers['start'], '%Y%m%d%H%M%S%f').timestamp())

should_continue = True
delay = 30
while should_continue or delay:
    if not should_continue:
        delay = delay - 1
    elif db.setnx('community_minting_simulation', 'locked'):
        should_continue = False
    accounts = read('get_all', {})
    community = read('get_community', {})
    keys = [key for key in accounts if not accounts[key]['sybil']]
    parties = choices(population=keys, k=2)
    amount = accounts[parties[0]]['balance'] * random()
    timers = read('get_timers', {})
    print(datetime.strptime(timers['current'], '%Y%m%d%H%M%S%f').timestamp(), sum([accounts[key]['balance'] for key in accounts]) + community['balance'])
    # print(datetime.strptime(timers['current'], '%Y%m%d%H%M%S%f').timestamp(), accounts, community['balance'])
    transact('transfer', {'sender': parties[0], 'receiver': parties[1], 'amount': amount})
    lock.acquire()
    sleep(1)

db.delete('community_minting_simulation')
