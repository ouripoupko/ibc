import json
import requests

f = open('csr.py','r')
csr = f.read()
f.close()

print(requests.put('http://localhost:5001/contract/', json = {'code':csr, 'name':'CSR'}).json())
print(requests.post('http://localhost:5001/contract/', json = {'from': '', 'to':'1', 'msg':{'name':'CSR', 'method':'addMember', 'param':{'id':'1'}}}).json())

