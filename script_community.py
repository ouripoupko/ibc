import requests
from time import sleep
from sseclient import SSEClient
from threading import Thread, Semaphore
from random import choice

server = 'http://localhost:5001/'
agents = [f'agent_{str(i).zfill(5)}' for i in range(200)]
contract = 'community'

locks = [Semaphore(0) for s in agents]
started = False


def listener(local_index):
    counter = 0
    messages = SSEClient(f'{server}stream/{agents[local_index]}/{contract}')
    for msg in messages:
        if msg.data == 'True':
            # if not started or local_index == 0:
            #     print(f'a message received from the server {local_index} {counter}')
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

# for index in range(1, len(agents)):
#     url = f'{server}ibc/app/{agents[index]}/{contract}'
#     json = {'pid': agents[0], 'address': server}
#     requests.post(url, json=json)
#     locks[index].acquire()
#     sleep(2+index/100)

print(f'starting to send transactions')
started = True
deg = 10

for index in range(deg+1):
    print('transact', index)
    # transact(agents[0], 'register', {'name': agents[index]})
    # locks[0].acquire()
    # for second in range(index) if index < 13 else sample(range(index), 12):
    #     transact(agents[0], 'add_friend', {'name': agents[index], 'friend': agents[second]})
    #     locks[0].acquire()
    transact(agents[0], 'join', {'name': agents[index], 'friends': []})
    locks[0].acquire()

for index in range(deg+1, len(agents)):
    community = read(agents[0], 'get_community', {})
    friends = []
    for i in range(int(deg/2+0.1)):
        first = choice(list(community.keys()))
        second = None
        while not second or second not in community:
            second = choice(community[first]['friends'])
        friends.append([community[first]['name'], community[second]['name']])
        del community[first]
        del community[second]
    print(friends)
    transact(agents[0], 'join', {'name': agents[index], 'friends': friends})
    locks[0].acquire()
