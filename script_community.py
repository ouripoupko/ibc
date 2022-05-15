import requests
from sseclient import SSEClient
from threading import Thread, Semaphore
from random import choice, choices

server = 'http://localhost:5001/'
size = 3000
agents = [f'agent_{str(i).zfill(5)}' for i in range(size)]
deg = 10
character = ['H' for i in range(deg+1)] + choices(
    population=['H', 'C', 'S'],
    weights=[0.1, 0.3, 0.6],
    k=size-deg-1)
contract = 'community'

locks = [Semaphore(0) for s in agents]
started = False


def listener(local_index):
    counter = 0
    messages = SSEClient(f'{server}stream/{agents[local_index]}/{contract}')
    for msg in messages:
        if msg.data == 'True':
            if started:
                counter += 1
            locks[local_index].release()


def transact(agent, method, params):
    requests.put(f'{server}ibc/app/{agent}/{contract}/{method}',
                 json={'name': method,
                       'values': params})


def read(agent, method, params):
    return requests.post(f'{server}ibc/app/{agent}/{contract}/{method}',
                         json={'name': method,
                               'values': params}).json()


Thread(target=listener, args=(0,)).start()
requests.post(f'{server}ibc/app/{agents[0]}')

f = open(f'{contract}.py', 'r')
requests.post(f'{server}ibc/app/{agents[0]}/{contract}',
              json={'pid': agents[0], 'address': server, 'code': f.read()})
f.close()

print(f'starting to send transactions')
started = True

for index in range(deg+1):
    print('transact', index)
    transact(agents[0], 'join', {'name': agents[index], 'friends': []})
    locks[0].acquire()

for index in range(deg+1, len(agents)):
    community = read(agents[0], 'get_community', {})
    friends = []
    keys = list(community.keys())
    names = [community[key]['name'] for key in keys]
    types = [character[agents.index(name)] for name in names]
    print(index, len(keys))
    if character[index] == 'C':
        if (types.count('C') + 1)/len(types) > 0.3:
            continue
    else:
        if character[index] == 'H':
            indices = [i for i, x in enumerate(types) if x != 'S']
        else:
            indices = [i for i, x in enumerate(types) if x != 'H']
        keys = [keys[i] for i in indices]
        names = [names[i] for i in indices]
        types = [types[i] for i in indices]
    tmp_keys = keys[:]
    while len(friends) * 2 < deg:
        if len(tmp_keys) < 2:
            break
        first = choice(tmp_keys)
        tmp_friends = community[first]['friends'][:]
        while tmp_friends:
            second = choice(tmp_friends)
            if second in tmp_keys:
                break
            tmp_friends.remove(second)
        if not tmp_friends:
            tmp_keys.remove(first)
            continue
        friends.append([community[first]['name'], community[second]['name']])
        if first not in keys or second not in keys:
            print('oops!')
        tmp = keys.index(first)
        del keys[tmp]
        del names[tmp]
        del types[tmp]
        tmp_keys.remove(first)
        tmp = keys.index(second)
        del keys[tmp]
        del names[tmp]
        del types[tmp]
        tmp_keys.remove(second)
    if len(friends) * 2 == deg:
        transact(agents[0], 'join', {'name': agents[index], 'friends': friends})
        locks[0].acquire()

community = read(agents[0], 'get_community', {})
keys = list(community.keys())
names = [community[key]['name'] for key in keys]
types = [character[agents.index(name)] for name in names]
print(types)
print(len(types), types.count('H'), types.count('C'), types.count('S'))
