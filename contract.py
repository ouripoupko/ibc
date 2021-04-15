from builtins import __build_class__
from threading import Condition
from partner import Partner
from protocol import Protocol


class Contract(Condition):
    def __init__(self, storage_bridge, storage, name, code, me):
        Condition.__init__(self)
        # the database
        self.storage_bridge = storage_bridge
        self.storage = storage
        # the contract
        self.name = name
        self.class_name = ''
        self.code = code
        self.members = []
        self.methods = []
        self.obj = None
        self.caller = None
        # the partners
        self.partners = []
        self.partners_db = self.storage_bridge.get_document('partners', self.name, self.storage)
        for key, value in self.partners_db.get_all().items():
            self.partners.append(Partner(value, key, me))
        # consensus protocols
        self.protocol_storage = self.storage_bridge.get_collection(me, 'protocols')

    def __repr__(self):
        return self.name

    def handle_off_chain(self, method):
        print("decorator state is running")

    def master(self):
        return self.caller

    def get_storage(self, name):
        return self.storage_bridge.get_collection(self.name, name, self.storage)

    def run(self, caller):
        self.caller = caller
        empty_locals = {}
        exec(self.code,
             {'__builtins__':
              {'__build_class__': __build_class__, '__name__': __name__,
               'str': str, 'int': int, 'master': self.master, 'Storage': self.get_storage,
               'parameters': self.storage_bridge.get_document('parameters', self.name, self.storage),
               'off_chain': self.handle_off_chain}}, empty_locals)
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
        values = [list(iter(getattr(self.obj, attribute))) for attribute in self.members]
        return {'name': self.name, 'contract': self.class_name, 'code': self.code,
                'methods': self.methods, 'members': self.members, 'values': values}

    def call(self, caller, method, msg):
        self.caller = caller
        m = getattr(self.obj, method)
        reply = m(*msg['values'])
        if not reply:
            reply = self.get_info()
        return reply

    def call_off_chain(self, caller, method, msg):
        self.caller = caller
        m = getattr(self.obj, method)
        reply = m(*msg['values'])
        if reply is None:
            reply = self.get_info()
        return reply

    def connect(self, address, pid, me):
        if pid != me:
            self.partners.append(Partner(address, pid, me))
            self.partners_db.update({pid: address})

    def consent(self, record, initiate):
        if initiate:
            return [partner.pid for partner in self.partners]
        if initiate and not self.partners:
            return True
        protocol = Protocol(self.storage_bridge, self.protocol_storage, self.name, self.partners)
        return protocol.handle_message(record, initiate)
