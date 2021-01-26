import hashlib


class Chat:

    def __init__(self):
        self.statements = {}
        self.topics = []
        self.chats = {}
        self.votes = {}
        self.counter = 1

    def __repr__(self):
        return str({'statements': self.statements, 'chats': self.chats, 'votes': self.votes})

    def _create_statement(self, parent, text, reply_type=None):
        record = {'rid': self.counter, 'parent': parent, 'kids': [],
                  'text': text, 'reactions': {}, 'reply_type': reply_type}
        self.counter = self.counter + 1
        hash_code = hashlib.sha256(str(record).encode('utf-8')).hexdigest()[0:10]
        self.statements[hash_code] = record
        return hash_code

    def create_topic(self, statement):
        hash_code = self._create_statement(None, statement)
        self.topics.append(hash_code)
        self.chats[hash_code] = []
        self.votes[hash_code] = {}

    def reply(self, parent_hash, statement, reply_type):
        parent = self.statements.get(parent_hash)
        if parent:
            hash_code = self._create_statement(parent_hash, statement, reply_type)
            parent['kids'].append(hash_code)

    def react(self, hash_code, pid, action):
        record = self.statements.get(hash_code)
        if record:
            record['reactions'][pid] = action

    def vote(self, hash_code, pid, ballot):
        votes = self.votes.get(hash_code)
        if votes:
            votes[pid] = ballot

    def chat(self, hash_code, pid, statement):
        chat = self.chats.get(hash_code)
        if chat:
            chat.append((pid, statement))
