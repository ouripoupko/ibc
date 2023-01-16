class Ledger:

    def __init__(self):
        self.ledger = Storage('ledger')
        self.sources = Storage('sources')
        self.contacts = Storage('contacts')
        self.groups = Storage('groups')
        self.statements = Storage('statements')

    def befriend(self, address, agent, contract):
        _content = {'type': 'befriend',
                    'parameters': {'agent': agent,
                                   'address': address,
                                   'contract': contract}}
        self._construct(_content)

    def group(self, name, agents):
        _content = {'type': 'group',
                    'parameters': {'name': name,
                                   'agents': agents}}
        self._construct(_content)

    def deliberate(self, to, text):
        _content = {'type': 'deliberate',
                    'parameters': {'to': to,
                                   'text': text}}
        self._construct(_content)

    def _construct(self, content):
        _body = {'from': master(),
                 'timestamp': timestamp(),
                 'pointers': [_key for _key in self.sources],
                 'content': content}
        _message = {'hash_code': hashcode(_body),
                    'body': _body}
        self._message(_message)

    def _message(self, message):
        _body = message['body']
        self.ledger[message['hash_code']] = message
        self.sources[message['hash_code']] = message
        for _key in _body['pointers']:
            if _key in self.sources:
                del self.sources[_key]
        _content = _body['content']
        if _content['type'] == 'befriend':
            self._execute_befriend(_content['parameters'])
        if _content['type'] == 'group':
            self._execute_group(_content['parameters'])
        if _content['type'] == 'deliberate':
            self._execute_deliberate(_content['parameters'])

    def share(self, hash_code, agents, group):
        _message = self.ledger[hash_code]
        if group and not agents:
            agents = self.groups[group]['members']
        for _agent in agents:
            if _agent in self.contacts:
                _target = self.contacts[_agent].get_dict()
                Write(_target['address'], _agent, _target['contract'], '_message',
                      [], {'message': _message})

    def _execute_befriend(self, parameters):
        self.contacts[parameters['agent']] = {'address': parameters['address'],
                                             'contract': parameters['contract']}

    def _execute_group(self, parameters):
        self.groups[parameters['name']] = {'members': parameters['agents']}

    def _execute_deliberate(self, parameters):
        self.statements.append(parameters)

    def get_ledger(self):
        return {str(key): self.ledger[key].get_dict() for key in self.ledger}

    def get_friends(self):
        return {str(key): self.contacts[key].get_dict() for key in self.contacts}

    def get_groups(self):
        return {str(key): self.groups[key].get_dict() for key in self.groups}

    def get_statements(self):
        return {str(key): self.statements[key].get_dict() for key in self.statements}

