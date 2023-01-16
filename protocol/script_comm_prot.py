import requests
from sseclient import SSEClient
from threading import Thread, Semaphore
from random import choice, choices, randrange
from time import sleep, time
from redis import Redis
from datetime import datetime


server = 'http://localhost:5001/'
deg = 10
agents = [f'honest_{str(i).zfill(5)}' for i in range(deg+1)]
contract = 'community'
redis_port = 6379

locks = [Semaphore(0) for s in agents]


def listener(local_index):
    messages = SSEClient(f'{server}stream/{agents[local_index]}/{contract}')
    for msg in messages:
        if msg.data == 'True':
            locks[local_index].release()


def transact(agent, method, params):
    requests.put(f'{server}ibc/app/{agent}/{contract}/{method}',
                 json={'name': method,
                       'values': params})


def read(agent, method, params):
    return requests.post(f'{server}ibc/app/{agent}/{contract}/{method}',
                         json={'name': method,
                               'values': params}).json()


db = Redis(host='localhost', port=redis_port, db=1)
db.setnx('community_minting_simulation', 'locked')
for index in range(deg+1):
    Thread(target=listener, args=(index,), daemon=True).start()
    requests.post(f'{server}ibc/app/{agents[index]}')

f = open(f'{contract}.py', 'r')
requests.post(f'{server}ibc/app/{agents[0]}/{contract}',
              json={'pid': agents[0], 'address': server, 'code': f.read()})
f.close()

for index in range(1, deg+1):
    url = f'{server}ibc/app/{agents[index]}/{contract}'
    json = {'pid': agents[index-1], 'address': server}
    requests.post(url, json=json)
    locks[index].acquire()
    sleep(2+index/100)

print(f'starting to send transactions')

for index in range(deg+1):
    print('transact', index)
    transact(agents[0], 'join', {'name': agents[index], 'friends': []})
    locks[0].acquire()

sleep(4)
keys = []
terminating = False
weights = [0.1, 0.3, 0.58, 0.02]
while True:
    community = read(agents[0], 'get_community', {})
    keys = list(community.keys())
    # check the community structure
    for key in keys:
        friends = community[key]['friends'][-1]
        if community[key]['sybil_exposed']:
            if friends:
                print('a sybil should not have friends')
        else:
            if len(set(friends)) != deg or len(friends) != deg:
                print('each agent should have 10 distinct friends')
            else:
                for friend_key in friends:
                    if key == friend_key:
                        print('an agent should not befriend itself')
                    if key not in community[friend_key]['friends'][-1]:
                        print('agent should be a friend of its friends')
    sleep(1)
    names = [community[key]['name'] for key in keys]
    honests = [key for index, key in enumerate(keys) if names[index].startswith('honest')]
    corrupts = [key for index, key in enumerate(keys) if names[index].startswith('corrupt')]
    sybils = [key for index, key in enumerate(keys) if names[index].startswith('sybil') and not community[key]['sybil_exposed']]
    live_count = len(honests) + len(corrupts) + len(sybils)
    last_time = max([community[key]['timestamps'][-1] for key in community])
    print(datetime.strptime(last_time, '%Y%m%d%H%M%S%f').timestamp(), len(honests), len(corrupts), len(sybils), len(names) - live_count)
    if not terminating and live_count == 300:
        terminating = True
        weights = [0, 0, 0.9, 0.1]
    if terminating and not sybils:
        break
    candidate = choices(
        population=['honest', 'corrupt', 'sybil', 'X'],
        weights=weights,
        k=1)[0]
    if candidate == 'X':
        if sybils:
            key = choice(sybils)
            transact(agents[0], 'report_sybil', {'name': community[key]['name']})
            locks[0].acquire()
        continue
    if candidate == 'corrupt':
        if len(corrupts) / live_count > 0.3:
            continue
    else:
        if candidate == 'honest':
            keys = honests + corrupts
        else:
            keys = corrupts + sybils
    friends = []
    while len(friends) * 2 < deg:
        if len(keys) < 2:
            break
        first = choice(keys)
        tmp_friends = community[first]['friends'][-1][:]
        while tmp_friends:
            second = choice(tmp_friends)
            if second in keys:
                break
            tmp_friends.remove(second)
        if not tmp_friends:
            keys.remove(first)
            continue
        friends.append([community[first]['name'], community[second]['name']])
        if first not in keys or second not in keys or first == second:
            print('oops!!!')
        keys.remove(first)
        keys.remove(second)
    if len(friends) * 2 == deg:
        transact(agents[0], 'join', {'name': f'{candidate}_{str(len(names)).zfill(5)}', 'friends': friends})
        locks[0].acquire()

db.delete('community_minting_simulation')
