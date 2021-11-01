import requests
from time import sleep, time
from os import listdir
from sseclient import SSEClient
from threading import Thread, Semaphore
from random import randrange

# servers = ['http://' + f + '/' for f in listdir('../var/')]
# servers = [f'http://localhost:{str(i)}/' for i in range(5001, 5005)]
servers = ['http://localhost:5001/' for i in range(20)]
contract = 'deliberation'
transaction = 'create_statement'

locks = [Semaphore(0) for s in servers]
start = time()
started = False
counter = 0


def listener(agent_index, contract_index):
    global counter
    agent_address = f'{servers[agent_index]}stream/agent_{str(agent_index).zfill(5)}'
    contract_url = f'{agent_address}/{contract}_{str(contract_index).zfill(5)}'
    messages = SSEClient(contract_url)
    locks[agent_index].release()
    for msg in messages:
        if msg.data == 'True':
            print('a message received from the server', agent_index, counter, time()-start)
            locks[agent_index].release()
            if started:
                counter += 1
            else:
                break


community = []
for index in range(11):
    community.append([i for i in range(11) if not i == index])
for index in range(11, len(servers)):
    community.append([])
    while len(community[index]) < 10:
        left = randrange(0, index)
        right = community[left][randrange(0, 10)]
        if left not in community[index] and right not in community[index]:
            community[index].extend([left, right])
            community[left].remove(right)
            community[left].append(index)
            community[right].remove(left)
            community[right].append(index)


for index, address in enumerate(servers):
    requests.post(f'{address}ibc/app/agent_{str(index).zfill(5)}')

f = open(f'{contract}.py', 'r')
code = f.read()
f.close()

for index, address in enumerate(servers):
    requests.post(f'{address}ibc/app/agent_{str(index).zfill(5)}/{contract}_{str(index).zfill(5)}',
                  json={'pid': f'agent_{str(index).zfill(5)}', 'address': address, 'code': code})

for my_index, my_address in enumerate(servers):
    for partner in range(10):
        his_index = community[my_index][partner]
        Thread(target=listener, args=(my_index, his_index)).start()
        locks[my_index].acquire()
        his_address = servers[his_index]
        url = f'{my_address}ibc/app/agent_{str(my_index).zfill(5)}/{contract}_{str(his_index).zfill(5)}'
        json = {'pid': f'agent_{str(his_index).zfill(5)}', 'address': his_address}
        requests.post(url, json=json)
        locks[my_index].acquire()
    sleep(2)

for index in range(len(servers)):
    Thread(target=listener, args=(index, index)).start()
    locks[index].acquire()

print('starting to send transactions', time()-start)
started = True

for marker in range(100):
    my_index = marker % len(servers)
    his_index = community[my_index][randrange(0, 10)]
    my_address = f'{servers[my_index]}ibc/app/agent_{str(my_index).zfill(5)}'
    requests.put(f'{my_address}/{contract}_{str(his_index).zfill(5)}/{transaction}',
                 json={'name': transaction,
                       'values': {'parents': [],
                                  'text': f'statement_{str(marker).zfill(3)}',
                                  'tags': []}})

# requests.post(f'http://localhost:5001/ibc/app/agent_{str(666).zfill(5)}')
