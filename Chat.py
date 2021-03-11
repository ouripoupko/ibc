class Chat:

    def __init__(self):
        self.statements = {}
        self.topics = []
        self.chats = {}
        self.votes = {}
        self._counter = 0

    def _create_statement(self, parent, text, reply_type=None):
        self._counter = self._counter + 1
        record = {'parent': parent, 'me': self._counter, 'kids': [],
                  'text': text, 'reactions': {}, 'reply_type': reply_type}
        self.statements[self._counter] = record
        return self._counter

    def create_topic(self, statement):
        _counter = self._create_statement(None, statement)
        self.topics.append(_counter)
        self.chats[_counter] = []
        self.votes[_counter] = {}

    def reply(self, parent_counter, statement, reply_type):
        parent_counter = int(parent_counter)
        _parent = self.statements.get(parent_counter)
        if _parent:
            _counter = self._create_statement(parent_counter, statement, reply_type)
            _parent['kids'].append(_counter)

    def react(self, counter, pid, action):
        counter = int(counter)
        _record = self.statements.get(counter)
        if _record:
            _record['reactions'][pid] = action

    def vote(self, counter, pid, ballot):
        counter = int(counter)
        _votes = self.votes.get(counter)
        if _votes:
            _votes[pid] = ballot

    def chat(self, counter, pid, statement):
        counter = int(counter)
        _chat = self.chats.get(counter)
        if _chat:
            _chat.append((pid, statement))

    def get_page(self, counter):
        if counter == 0:
            return {'kids': [self.statements[stid] for stid in self.topics]}
        return {'parent': self.statements[counter],
                'kids': [self.statements[stid] for stid in self.statements[counter].get('kids')]}
