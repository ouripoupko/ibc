from enum import Enum


class ProtocolStep(Enum):
    LEADER = 1
    PREPARE = 2
    COMMIT = 3
    DONE = 4


class Contract:
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.partners = []
        self.obj = None
        self.prepared = {}
        self.committed = {}
        self.keep = {}

    def __repr__(self):
        return str({'class': 'Contract', 'name': self.name, 'partners': self.partners})

    def run(self):
        exec(self.code)
        self.obj = locals()[self.name]()
        return {'msg': 'contract {} is running!'.format(self.name)}

    def call(self, msg):
        m = getattr(self.obj, msg['method'])
        return m(msg['param'])

    def connect(self, partner):
        self.partners.append(partner)

    def get_ready(self, record):
        hash_code = hash(str(record))
        self.prepared[hash_code] = set()
        self.committed[hash_code] = set()
        self.keep[hash_code] = record
        return hash_code

    def done(self, hash_code):
        self.prepared.pop(hash_code)
        self.committed.pop(hash_code)
        return self.keep.pop(hash_code)

    def consent(self, record, initiate):
        if initiate:
            if not self.partners:
                return True
            self.get_ready(record)
            for partner in self.partners:
                partner.consent(self.name, ProtocolStep.LEADER, record)
        else:
            step = record['params']['msg']['step']
            if step == ProtocolStep.PREPARE:
                hash_code = self.get_ready(record)
                for partner in self.partners:
                    partner.consent(self.name, ProtocolStep.PREPARE, hash_code)
            elif step == ProtocolStep.COMMIT:
                if not self.keep.get(record['hash']):
                    return False
                self.prepared[record['hash']].add(record['pid'])
                if len(self.prepared[record['hash']]) * 3 >= len(self.partners):
                    for partner in self.partners:
                        partner.consent(self.name, ProtocolStep.COMMIT, record['hash'])
            elif step == ProtocolStep.DONE:
                if not self.keep.get(record['hash']):
                    return False
                self.committed[record['hash']].add(record['pid'])
                if len(self.committed[record['hash']]) * 3 >= len(self.partners):
                    return True
        return False

    def get_consent_result(self, record):
        return self.done(record['hash'])
