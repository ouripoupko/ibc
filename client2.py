import json
import requests

f = open('csr.py','r')
csr = f.read()
f.close()

print(requests.put('http://localhost:5002/contract/', json = {'code':csr, 'name':'CSR'}).json())
print(requests.put('http://localhost:5002/partner/', json = {'addr':'http://localhost:5001/', 'id': '1'}).json())
print(requests.post('http://localhost:5002/contract/', json = {'from': '', 'to':'2', 'msg':{'name':'CSR', 'method':'triggerEdge', 'param':{'id':'1'}}}).json())

