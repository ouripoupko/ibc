class Chat:

    def __init__(self):
        self.statements = {}
        self.topics = []
        self.chats = {}
        self.votes = {}
        self._counter = 0
        self._version = 0

    def _create_statement(self, parent, text, reply_type=None):
        self._counter = self._counter + 1
        self._version = self._version + 1
        record = {'parent': parent, 'me': self._counter, 'kids': [], 'owner': master(),
                  'text': text, 'reactions': {}, 'reply_type': reply_type}
        self.statements[self._counter] = record
        return self._counter

    def _update_change(self, sid):
        _statement = self.statements[sid]
        _statement['version'] = self._version
        _parent_id = _statement['parent']
        while _parent_id:
            _parent = self.statements[_parent_id]
            _parent['kids_version'] = sid
            _parent_id = _parent['parent']

    def create_topic(self, statement):
        _sid = self._create_statement(None, statement)
        self._update_change(_sid)
        self.topics.append(_sid)
        self.chats[_sid] = []
        self.votes[_sid] = {}

    def reply(self, parent_sid, statement, reply_type):
        parent_counter = int(parent_sid)
        _parent = self.statements.get(parent_sid)
        if _parent:
            _sid = self._create_statement(parent_sid, statement, reply_type)
            _parent['kids'].append(_sid)
        self._update_change(_sid)

    def react(self, sid, action):
        sid = int(sid)
        _record = self.statements.get(sid)
        if _record:
            _record['reactions'][master()] = action
        self._update_change(sid)

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

    def get_kids(self, counter):
        if counter == 0:
            return [self.statements[stid] for stid in self.topics]
        return [self.statements[stid] for stid in self.statements[counter].get('kids')]
