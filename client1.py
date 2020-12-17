import json
import requests

f = open('csr.py','r')
csr = f.read()
f.close()

resp = requests.post('http://localhost:5000/contract/', json = {"code":csr, "name":"CSR"})
print(resp.text)
