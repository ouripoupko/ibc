import requests
from time import sleep, time
from os import listdir
from sseclient import SSEClient
from threading import Thread, Semaphore

import numpy

# servers = ['http://' + f + '/' for f in listdir('../var/')]
servers = [f'http://localhost:{str(i)}/' for i in range(5001, 5011)]
contract = 'currency'
transaction = 'create_statement'

agents_count = len(servers)
degree = 4
random = numpy.random.rand(agents_count, agents_count)
adjacency = random < (degree + 1) / agents_count
numpy.fill_diagonal(adjacency, False)
print(min(sum(adjacency)), max(sum(adjacency)), sum(sum(adjacency))/100)

locks = [Semaphore(0) for s in servers]
start = time()
started = False


def listen(owner, partner):
    messages = SSEClient(f'{servers[partner]}stream/agent_{str(partner).zfill(5)}/{contract}_{str(owner).zfill(5)}')
    for msg in messages:
        if msg.data == 'True':
            locks[partner].release()
            break


f = open(f'{contract}.py', 'r')
contract_content = f.read()
f.close()

for index, address in enumerate(servers):
    print('installing agent', index)
    # define the agent
    requests.post(f'{address}ibc/app/agent_{str(index).zfill(5)}')
    # deploy the contract
    requests.post(f'{address}ibc/app/agent_{str(index).zfill(5)}/{contract}_{str(index).zfill(5)}',
                  json={'pid': 'agent_{str(index).zfill(5)}', 'address': address, 'code': contract_content})
    # connect with neighbours
    neighbours = numpy.nonzero(adjacency[index, :])
    for neighbour in neighbours[0]:
        print('connecting to neighbour', neighbour)
        Thread(target=listen, args=(index, neighbour)).start()
        address = servers[neighbour]
        url = f'{address}ibc/app/agent_{str(neighbour).zfill(5)}/{contract}_{str(index).zfill(5)}'
        json = {'pid': 'agent_{str(index).zfill(5)}', 'address': servers[index]}
        requests.post(url, json=json)
        locks[neighbour].acquire()
        sleep(2)

print('starting to send transactions', time()-start)
#
# for index in range(1500):
#     agent = index % len(servers)
#     requests.put(f'{servers[agent]}ibc/app/agent_{str(agent).zfill(5)}/{contract}/{transaction}',
#                  json={'name': transaction,
#                        'values': {'parents': [],
#                                   'text': f'statement_{str(index).zfill(3)}',
#                                   'tags': []}})
#
# # requests.post(f'http://localhost:5001/ibc/app/agent_{str(666).zfill(5)}')
