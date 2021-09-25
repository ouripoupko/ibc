import requests
import time

n = 10

for index in range(n):
    requests.post(f'http://localhost:5001/ibc/app/agent_{str(index).zfill(5)}')

f = open('deliberation.py', 'r')
requests.post(f'http://localhost:5001/ibc/app/agent_{str(0).zfill(5)}/deliberation',
              json={'pid': f'agent_{str(0).zfill(5)}', 'address': 'http://localhost:5001/', 'code': f.read()})
f.close()

for index in range(1, n):
    requests.post(f'http://localhost:5001/ibc/app/agent_{str(index).zfill(5)}/deliberation',
                  json={'pid': f'agent_{str(0).zfill(5)}', 'address': 'http://localhost:5001/'})
    time.sleep(5)

# 'PUT', 'contract': 'deliberation', 'method': 'create_statement', 'message': {'name': 'create_statement', 'values': {'parents': [], 'text': 'again', 'tags': []}}, 'caller': 'agent_00000'}