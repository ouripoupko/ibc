import requests
from time import sleep, time
from os import listdir
from sseclient import SSEClient
from threading import Thread, Semaphore

# servers = ['http://' + f + '/' for f in listdir('../var/')]
servers = [f'http://localhost:{str(i)}/' for i in range(5001,5011)]
contract = 'deliberation'
transaction = 'create_statement'

locks = [Semaphore(0) for s in servers]
start = time()
started = False


def listener(local_index):
    messages = SSEClient(f'{servers[local_index]}stream/agent_{str(local_index).zfill(5)}/{contract}')
    for msg in messages:
        if msg.data == 'True':
            if not started or local_index == 0:
                print('a message received from the server', local_index, time()-start)
            locks[local_index].release()


for index in range(len(servers)):
    Thread(target=listener, args=(index,)).start()

for index, address in enumerate(servers):
    requests.post(f'{address}ibc/app/agent_{str(index).zfill(5)}')

f = open(f'{contract}.py', 'r')
requests.post(f'{servers[0]}ibc/app/agent_00000/{contract}',
              json={'pid': 'agent_00000', 'address': servers[0], 'code': f.read()})
f.close()

for index in range(1, len(servers)):
    address = servers[index]
    url = f'{address}ibc/app/agent_{str(index).zfill(5)}/{contract}'
    json = {'pid': 'agent_00000', 'address': servers[0]}
    requests.post(url, json=json)
    locks[index].acquire()
    sleep(2)

print('starting to send transactions', time()-start)
started = True

for index in range(1500):
    agent = index % len(servers)
    requests.put(f'{servers[agent]}ibc/app/agent_{str(agent).zfill(5)}/{contract}/{transaction}',
                 json={'name': transaction,
                       'values': {'parents': [],
                                  'text': f'statement_{str(index).zfill(3)}',
                                  'tags': []}})

# requests.post(f'http://localhost:5001/ibc/app/agent_{str(666).zfill(5)}')
