from redis import Redis

class RedisJson:
    def __init__(self, port, db, agent, contract):
        self.db = Redis(host='localhost', port=port, db=db)
        self.agent = agent
        self.contract = contract

    def init(self, value):
        if not self.db.exists(self.agent) or self.contract not in self.db.json().objkeys(self.agent, '.'):
            self.db.json().set(self.agent, f'.', {self.contract: value})

    def set(self, path, value):
        self.db.json().set(self.agent, f'.{self.contract}.{path}', value)

    def merge(self, path, value):
        self.db.json().merge(self.agent, f'.{self.contract}.{path}', value)

    def get(self, path):
        return self.db.json().get(self.agent, f'.{self.contract}.{path}')

    def type(self, path):
        return self.db.json().type(self.agent, f'.{self.contract}.{path}')

    def delete(self, path):
        return self.db.json().delete(self.agent, f'.{self.contract}.{path}')

    def array_append(self, path, value):
        return self.db.json().arrappend(self.agent, f'.{self.contract}.{path}', value)

    def array_pop(self, path, index):
        return self.db.json().arrpop(self.agent, f'.{self.contract}.{path}', index)

    def array_index(self, path, value):
        return self.db.json().arrpop(self.agent, f'.{self.contract}.{path}', value)

    def object_keys(self, path):
        return self.db.json().objkeys(self.agent, f'.{self.contract}.{path}')

