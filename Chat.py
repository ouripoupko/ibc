class Chat:

    def __init__(self):
        self.statements = Storage('statements')
        self.parameters = Storage('parameters')
        if not self.parameters[{'record': 'single'}]:
            self.parameters.append({'record': 'single', 'topics': [], 'counter': 0, 'version': 0})

    def _create_statement(self, parent, text, reply_type=None):
        self.parameters[{'record': 'single'}] = {'$inc': {'counter': 1, 'version': 1}}
        record = {'parent': parent, 'me': self.parameters[{'record': 'single'}]['counter'], 'kids': [],
                  'owner': master(), 'text': text, 'reactions': {}, 'reply_type': reply_type}
        self.statements.append(record)
        return self.parameters[{'record': 'single'}]['counter']

    def _update_change(self, sid):
        self.statements[{'me': sid}] = {'$set': {'version': self.parameters[{'record': 'single'}]['version']}}
        _parent_id = self.statements[{'me': sid}]['parent']
        while _parent_id:
            self.statements[{'me': _parent_id}] = {'$set': {'kids_version': sid}}
            _parent_id = self.statements[{'me': _parent_id}]['parent']

    def create_topic(self, statement):
        _sid = self._create_statement(None, statement)
        self._update_change(_sid)
        self.parameters[{'record': 'single'}] = {'$push': {'topics': _sid}}

    def reply(self, parent_sid, statement, reply_type):
        _parent = self.statements[{'me': parent_sid}]
        if _parent:
            _sid = self._create_statement(parent_sid, statement, reply_type)
            self.statements[{'me': parent_sid}] = {'$push': {'kids': _sid}}
        self._update_change(_sid)

    def react(self, sid, action):
        pass
#        sid = int(sid)
#        _record = self.statements.get(sid)
#        if _record:
#            _record['reactions'][master()] = action
#        self._update_change(sid)

    def vote(self, counter, pid, ballot):
        pass
#        counter = int(counter)
#        _votes = self.votes.get(counter)
#        if _votes:
#            _votes[pid] = ballot

    def chat(self, counter, pid, statement):
        pass
#        counter = int(counter)
#        _chat = self.chats.get(counter)
#        if _chat:
#            _chat.append((pid, statement))

    def get_kids(self, counter):
        if counter == 0:
            return [self.statements[{'me': stid}] for stid in self.parameters[{'record': 'single'}]['topics']]
        return [self.statements[{'me': stid}] for stid in self.statements[{'me': counter}]['kids']]
