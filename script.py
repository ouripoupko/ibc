import requests
import time
from os import listdir

servers = ['http://' + f + '/' for f in listdir('../var/')]

for index, address in enumerate(servers):
    requests.post(f'{address}ibc/app/agent_{str(index).zfill(5)}')

f = open('deliberation.py', 'r')
requests.post(f'{servers[0]}ibc/app/agent_00000/deliberation',
              json={'pid': 'agent_00000', 'address': servers[0], 'code': f.read()})
f.close()

for index in range(1,len(servers)):
    address = servers[index]
    url = f'{address}ibc/app/agent_{str(index).zfill(5)}/deliberation'
    json = {'pid': 'agent_00000', 'address': servers[0]}
    requests.post(url, json=json)
    time.sleep(2+index/3)

for index in range(50):
    agent = index % len(servers)
    requests.put(f'{servers[agent]}ibc/app/agent_{str(agent).zfill(5)}/deliberation/create_statement',
                 json={'name': 'create_statement',
                       'values': {'parents': [],
                                  'text': f'statement_{str(index).zfill(3)}',
                                  'tags': []}})

# requests.post(f'http://localhost:5001/ibc/app/agent_{str(666).zfill(5)}')
