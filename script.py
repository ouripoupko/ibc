import requests
import time

n = 10
one_server = False

for index in range(n):
    requests.post(f'http://localhost:{5001+(0 if one_server else index)}/ibc/app/agent_{str(index).zfill(5)}')

f = open('deliberation.py', 'r')
requests.post(f'http://localhost:5001/ibc/app/agent_{str(0).zfill(5)}/deliberation',
              json={'pid': f'agent_{str(0).zfill(5)}', 'address': 'http://localhost:5001/', 'code': f.read()})
f.close()

for index in range(1, n):
    url = f'http://localhost:{5001+(0 if one_server else index)}/ibc/app/agent_{str(index).zfill(5)}/deliberation'
    json = {'pid': f'agent_{str(0).zfill(5)}', 'address': f'http://localhost:5001/'}
    requests.post(url, json=json)
    time.sleep(2+index/3)

for index in range(50):
    agent = index % 10
    requests.put(f'http://localhost:{5001+(0 if one_server else agent)}/ibc/app/agent_{str(agent).zfill(5)}/deliberation/create_statement',
                 json={'name': 'create_statement',
                       'values': {'parents': [],
                                  'text': f'statement_{str(index).zfill(3)}',
                                  'tags': []}})

# requests.post(f'http://localhost:5001/ibc/app/agent_{str(666).zfill(5)}')
