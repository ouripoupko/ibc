import requests
from time import sleep

file = open('../../temp/dispatcher.log', 'r')
lines = file.readlines()
file.close()
actions = {'register_agent', 'deploy_contract', 'contract_write', 'join_contract'}
apps = {'profile': 'http://localhost:4201', 'community': 'http://localhost:4202'}
functions = {'PUT': requests.put, 'POST': requests.post}
contracts = {}
for line in lines:
    parts = line.split(' ~ ')
    if parts[6].startswith('request'):
        request = eval(parts[-1])
        contract = '/' + request['contract'] if request['contract'] else ''
        method = '/' + request['method'] if request['method'] else ''
        if request['action'] in actions:
            if request['action'] == 'deploy_contract':
                request['message']['default_app'] = apps[request['message']['default_app'].split('/')[-1]]
                if request['message']['profile']:
                    request['message']['profile'] = contracts[request['message']['profile']]
            if request['action'] == 'join_contract':
                request['message']['contract'] = contracts[request['message']['contract']]
                if request['message']['profile']:
                    request['message']['profile'] = contracts[request['message']['profile']]
            if 'address' in request['message']:
                request['message']['address'] = 'http://localhost:5001'
            if request['contract'] and request['contract'] in contracts:
                contract = '/' + contracts[request['contract']]
            reply = functions[request['type']]('http://localhost:5001/ibc/app/' + request['agent'] + contract + method,
                                               params={'action': request['action']},
                                               json=request['message'])
            if request['action'] == 'deploy_contract':
                contracts[parts[5]] = reply.json()
            print('.', end='')
            sleep(1)
    elif parts[6].startswith('response'):
        if parts[5] in contracts:
            contracts[parts[8].split()[0]] = contracts[parts[5]]
            del contracts[parts[5]]
