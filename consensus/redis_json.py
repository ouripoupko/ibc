from redis import Redis

class RedisJson:
    def __init__(self, db: Redis, agent, contract):
        self.db = db
        self.agent = agent
        self.contract = contract
        if not self.db.exists(self.agent):
            self.db.json().set(self.agent, f'.', {})
        if self.contract not in self.db.json().objkeys(self.agent, '.'):
            self.db.json().set(self.agent, f'.{self.contract}', {})

    def set(self, path, value, nx = False):
        self.db.json().set(self.agent, f'.{self.contract}{"."+path if path else ""}', value, nx)

    def merge(self, path, value):
        self.db.json().merge(self.agent, f'.{self.contract}{"."+path if path else ""}', value)

    def get(self, path):
        return self.db.json().get(self.agent, f'.{self.contract}{"."+path if path else ""}')

    def type(self, path):
        return self.db.json().type(self.agent, f'.{self.contract}{"."+path if path else ""}')

    def delete(self, path):
        return self.db.json().delete(self.agent, f'.{self.contract}{"."+path if path else ""}')

    def array_append(self, path, value):
        return self.db.json().arrappend(self.agent, f'.{self.contract}{"."+path if path else ""}', value)

    def array_pop(self, path, index):
        return self.db.json().arrpop(self.agent, f'.{self.contract}{"."+path if path else ""}', index)

    def array_index(self, path, value):
        return self.db.json().arrpop(self.agent, f'.{self.contract}{"."+path if path else ""}', value)

    def object_keys(self, path):
        return self.db.json().objkeys(self.agent, f'.{self.contract}{"."+path if path else ""}')
