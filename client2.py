
import requests

resp = requests.get('http://localhost:5001/')
print(resp.text)
