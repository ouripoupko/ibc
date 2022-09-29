class Ledger:

    def __init__(self):
        self.ledger = Storage('ledger')
        self.roots = Storage('roots')
        self.friends = Storage('friends')
        self.statements = Storage('statements')

    def befriend(self, address, agent, contract):
        _content = {'type': 'befriend',
                    'parameters': {'agent': agent,
                                   'address': address,
                                   'contract': contract}}
        self._construct([], _content)

    def deliberate(self, to, text):
        _content = {'type': 'deliberate',
                    'parameters': {'text': text}}
        self._construct(to, _content)

    def _construct(self, to, content):
        _body = {'from': master(),
                 'to': to,
                 'timestamp': timestamp(),
                 'pointers': [_key for _key in self.roots],
                 'content': content}
        _message = {'hash_code': hashcode(_body),
                    'body': _body}
        self._message(_message)

    def _message(self, message):
        _body = message['body']
        _agents = _body['to']
        self.ledger[message['hash_code']] = message
        self.roots[message['hash_code']] = message
        for _key in _body['pointers']:
            if _key in self.roots:
                del self.roots[_key]
        if _body['from'] == master():
            for _agent in _agents:
                if _agent in self.friends:
                    _target = self.friends[_agent].get_dict()
                    Write(_target['address'], _agent, _target['contract'], '_message',
                          [], {'message': message})
        _content = _body['content']
        if _content['type'] == 'befriend':
            self._execute_befriend(_content['parameters'])
        if _content['type'] == 'deliberate':
            self._execute_deliberate(_content['parameters'])

    def _execute_befriend(self, parameters):
        self.friends[parameters['agent']] = {'address': parameters['address'],
                                             'contract': parameters['contract']}

    def _execute_deliberate(self, parameters):
        self.statements.append(parameters)

    def get(self):
        return {str(key): self.ledger[key].get_dict() for key in self.ledger}

    def get_statements(self):
        return {str(key): self.statements[key].get_dict() for key in self.statements}

