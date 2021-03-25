from builtins import __build_class__
from enum import Enum
from threading import Condition
import hashlib


class ProtocolStep(Enum):
    LEADER = 1
    PREPARE = 2
    COMMIT = 3
    DONE = 4


class Contract(Condition):
    def __init__(self, name, code):
        Condition.__init__(self)
        self.name = name
        self.class_name = ''
        self.code = code
        self.members = []
        self.methods = []
        self.partners = []
        self.obj = None
        self.prepared = {}
        self.committed = {}
        self.commit_state = {}
        self.keep = {}
        self.delayed = {}
        self.caller = None

    def __repr__(self):
        # state = ast.literal_eval(repr(self.obj))
        # return str({'class': 'Contract', 'name': self.name, 'partners': self.partners, 'state': state})
        return self.name

    def handle_off_chain(self, method):
        print("decorator state is running")

    def master(self):
        return self.caller

    def run(self, caller):
        self.caller = caller
        empty_locals = {}
        exec(self.code,
             {'__builtins__': {'__build_class__': __build_class__, '__name__': __name__,
                               'str': str, 'int': int, 'print': print, 'master': self.master, 'off_chain': self.handle_off_chain}}, empty_locals)
        # [f for f in dir(ClassName) if not f.startswith('_')]
        # args=method.__code__.co_varnames
        class_object = list(empty_locals.values())[0]
        self.class_name = class_object.__name__
        self.obj = class_object()
        attributes = [attribute for attribute in dir(self.obj) if not attribute.startswith('_')]
        self.members = [attribute for attribute in attributes if not callable(getattr(self.obj, attribute))]
        method_names = [attribute for attribute in attributes if callable(getattr(self.obj, attribute))]
        self.methods = [{'name': name,
                         'arguments': [arg for arg in
                                       list(getattr(self.obj, name).__code__.co_varnames)[1:]
                                       if not arg.startswith('_')]}
                        for name in method_names]
        return self.get_info()

    def get_info(self):
        values = [getattr(self.obj, attribute) for attribute in self.members]
        return {'name': self.name, 'contract': self.class_name, 'code': self.code,
                'methods': self.methods, 'members': self.members, 'values': values}

    def call(self, caller, method, msg):
        self.caller = caller
        m = getattr(self.obj, method)
        reply = m(*msg['values'])
        if not reply:
            reply = self.get_info()
        with self:
            self.notify_all()
        return reply

    def call_off_chain(self, caller, method, msg):
        self.caller = caller
        m = getattr(self.obj, method)
        reply = m(*msg['values'])
        if reply is None:
            reply = self.get_info()
        return reply

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
            step = ProtocolStep[record['message']['msg']['step']]
            if step == ProtocolStep.LEADER:
                original_record = record['message']['msg']['data']
                hash_code = self.get_ready(original_record)
                delayed = self.delayed.get(hash_code, [])
                for partner in self.partners:
                    partner.consent(self.name, ProtocolStep.PREPARE.name, hash_code)
                for delayed_record in delayed:
                    self.consent(delayed_record, False)
            else:
                hash_code = record['message']['msg']['data']
                from_pid = record['message']['from']
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
        return self.done(record['message']['msg']['data'])
