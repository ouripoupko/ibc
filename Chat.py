class Chat:

    def __init__(self):
        self.statements = Storage('statements')
        if parameters.get('topics') is None:
            parameters.set({'topics': [], 'version': 1})

    def _create_statement(self, parent, text, reply_type=None):
        parameters.increment('version', 1, self.statements)
        record = {'parent': parent, 'kids': [],
                  'owner': master(), 'text': text, 'reactions': {}, 'reply_type': reply_type}
        return self.statements.append(record)

    def _update_change(self, sid, _parent_id):
        version = parameters.get('version')
        self.statements.update(sid, 'version', version)
        while _parent_id:
            self.statements.update(_parent_id, 'kids_version', version)
            _parent_id = self.statements[_parent_id]['parent']

    def create_topic(self, statement):
        self.statements.withhold()
        _sid = self._create_statement(None, statement)
        self._update_change(_sid, None)
        parameters.append('topics', _sid, self.statements)
        self.statements.commit()

    def reply(self, parent_sid, statement, reply_type):
        _parent = self.statements[parent_sid]
        if _parent:
            self.statements.withhold()
            _sid = self._create_statement(parent_sid, statement, reply_type)
            self.statements.update_append(parent_sid, 'kids', _sid)
            self._update_change(_sid, parent_sid)
            self.statements.commit()

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

    def get_kids(self, sid):
        _kids = self.statements[sid]['kids'] if sid else parameters.get('topics')
        return {kid: self.statements[kid] for kid in _kids}
