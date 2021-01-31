from builtins import __build_class__
from enum import Enum
import ast
import hashlib


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
        self.commit_state = {}
        self.keep = {}
        self.delayed = {}

    def __repr__(self):
        # state = ast.literal_eval(repr(self.obj))
        # return str({'class': 'Contract', 'name': self.name, 'partners': self.partners, 'state': state})
        return self.name

    def run(self):
        empty_locals = {}
        exec(self.code,
             {'__builtins__': {'__build_class__': __build_class__, '__name__': __name__, 'str': str}}, empty_locals)
        self.obj = list(empty_locals.values())[0]()
        return {'msg': 'contract {} is running!'.format(self.name)}

    def call(self, msg):
        m = getattr(self.obj, msg['method'])
        m(*msg['param'])
        return ast.literal_eval(repr(self.obj))

    def connect(self, partner):
        self.partners.append(partner)

    def get_ready(self, record):
        hash_code = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        self.prepared[hash_code] = set()
        self.committed[hash_code] = set()
        self.keep[hash_code] = record
        self.commit_state[hash_code] = False
        return hash_code

    def done(self, hash_code):
        self.prepared.pop(hash_code, None)
        self.committed.pop(hash_code, None)
        self.delayed.pop(hash_code, None)
        self.commit_state.pop(hash_code, None)
        record = self.keep[hash_code]
        self.keep[hash_code] = 'done'
        return record

    def consent(self, record, initiate):
        print(record)
        if initiate:
            if not self.partners:
                return True
            hash_code = self.get_ready(record)
            for partner in self.partners:
                partner.consent(self.name, ProtocolStep.LEADER.name, record, 0.5)
            for partner in self.partners:
                partner.consent(self.name, ProtocolStep.PREPARE.name, hash_code)
        else:
            step = ProtocolStep[record['params']['msg']['step']]
            if step == ProtocolStep.LEADER:
                original_record = record['params']['msg']['data']
                hash_code = self.get_ready(original_record)
                delayed = self.delayed.get(hash_code, [])
                for partner in self.partners:
                    partner.consent(self.name, ProtocolStep.PREPARE.name, hash_code)
                for delayed_record in delayed:
                    self.consent(delayed_record, False)
            else:
                hash_code = record['params']['msg']['data']
                from_pid = record['params']['from']
                if not self.keep.get(hash_code):
                    if not self.delayed.get(hash_code):
                        self.delayed[hash_code] = []
                    self.delayed[hash_code].append(record)
                    return False
                elif self.keep.get(hash_code) == 'done':
                    return False
                if step == ProtocolStep.PREPARE:
                    self.prepared[hash_code].add(from_pid)
                    if len(self.prepared[hash_code]) * 3 >= len(self.partners) * 2:
                        for partner in self.partners:
                            partner.consent(self.name, ProtocolStep.COMMIT.name, hash_code)
                        self.commit_state[hash_code] = True
                        if len(self.committed[hash_code]) * 3 >= len(self.partners) * 2:
                            return True
                elif step == ProtocolStep.COMMIT:
                    self.committed[hash_code].add(from_pid)
                    if len(self.committed[hash_code]) * 3 >= len(self.partners) * 2 and self.commit_state[hash_code]:
                        return True
        return False

    def get_consent_result(self, record):
        return self.done(record['params']['msg']['data'])
