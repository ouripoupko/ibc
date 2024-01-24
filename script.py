import requests

server = 'http://localhost:5001'
agents = [f'agent_{str(index).zfill(5)}' for index in range(20)]
f = open('delib.py', 'r')
contract_code = f.read()
f.close()

for agent in agents:
    requests.put(f'{server}/ibc/app/{agent}',
                 params={'action': 'register_agent'},
                 json={})

reply = requests.put(f'{server}/ibc/app/{agents[0]}',
                     params={'action': 'deploy_contract'},
                     json={'address': 'http://localhost:5001/',
                           'pid': agents[0],
                           'name': 'delib',
                           'protocol': 'BFT',
                           'default_app': 'http://localhost:4201',
                           'contract': 'delib.py',
                           'profile': '',
                           'constructor': {},
                           'code': contract_code})
contract = reply.json()
print(contract)

for agent in agents[1:]:
    requests.put(f'{server}/ibc/app/{agent}',
                 params={'action': 'join_contract'},
                 json={'address': f'{server}/',
                       'agent': agents[0],
                       'contract': contract,
                       'profile': ''})


requests.post(f'{server}/ibc/app/{agents[0]}/{contract}/create_statement',
              params={'action': 'contract_write'},
              json={'name': 'create_statement',
                    'values': {'parent': None, 'text': 'Hello World'}})

wait = input()

for agent in agents:
    reply = requests.post(f'{server}/ibc/app/{agent}/{contract}/get_statements',
              params={'action': 'contract_read'},
              json={'name': 'get_statements',
                    'values': {'parent': None}})
    print(agent)
    print(reply.json())



#
# requests.post(f'{server}/ibc/app/{alice}/{me_a}/set_value',
#               params={'action': 'contract_write'},
#               json={'name': 'set_value',
#                     'values': {'key': 'last_name', 'value': 'Wonderland'}})
#
# reply = requests.put(f'{server}/ibc/app/{alice}',
#                      params={'action': 'deploy_contract'},
#                      json={'address': 'http://localhost:5001/',
#                            'pid': alice,
#                            'name': 'my_wall_a',
#                            'protocol': 'BFT',
#                            'default_app': 'http://localhost:4202',
#                            'contract': 'sn_person.py',
#                            'profile': me_a,
#                            'code': sn_person})
# my_wall_a = reply.json()
#
# requests.post(f'{server}/ibc/app/{alice}/{my_wall_a}/create_post',
#               params={'action': 'contract_write'},
#               json={'name': 'create_post',
#                     'values': {'text': 'Alice is having a wonderful day'}})
#
# requests.put(f'{server}/ibc/app/{bob}',
#               params={'action': 'register_agent'},
#               json={})
#
# reply = requests.put(f'{server}/ibc/app/{bob}',
#                      params={'action': 'deploy_contract'},
#                      json={'address': 'http://localhost:5001/',
#                            'pid': bob,
#                            'name': 'me_b',
#                            'protocol': 'BFT',
#                            'default_app': 'http://localhost:4201',
#                            'contract': 'profile.py',
#                            'profile': '',
#                            'code': profile})
# me_b = reply.json()
#
# requests.post(f'{server}/ibc/app/{bob}/{me_b}/set_value',
#               params={'action': 'contract_write'},
#               json={'name': 'set_value',
#                     'values': {'key': 'first_name', 'value': 'Bob'}})
#
# requests.post(f'{server}/ibc/app/{bob}/{me_b}/set_value',
#               params={'action': 'contract_write'},
#               json={'name': 'set_value',
#                     'values': {'key': 'last_name', 'value': 'Fisher'}})
#
# reply = requests.put(f'{server}/ibc/app/{bob}',
#                      params={'action': 'deploy_contract'},
#                      json={'address': 'http://localhost:5001/',
#                            'pid': bob,
#                            'name': 'my_wall_b',
#                            'protocol': 'BFT',
#                            'default_app': 'http://localhost:4202',
#                            'contract': 'sn_person.py',
#                            'profile': me_b,
#                            'code': sn_person})
# my_wall_b = reply.json()
#
# requests.post(f'{server}/ibc/app/{bob}/{my_wall_b}/create_post',
#               params={'action': 'contract_write'},
#               json={'name': 'create_post',
#                     'values': {'text': 'Bob is having fun tonight'}})
#
