from builtins import __build_class__
from partner import Partner
from protocol import Protocol


class Contract:
    def __init__(self, contract_doc, name, code, me, logger, queue):
        # the database
        self.contract_doc = contract_doc
        # the contract
        self.name = name
        self.class_name = ''
        self.code = code
        self.me = me
        self.logger = logger
        self.queue = queue
        self.members = []
        self.methods = []
        self.obj = None
        self.caller = None
        # the partners
        self.partners = []
        self.partners_db = self.contract_doc.get_sub_collection('pda_partners')
        for key in self.partners_db:
            self.partners.append(Partner(self.partners_db[key]['address'], key, me, self.queue))
        # consensus protocols
        self.protocol_storage = self.contract_doc.get_sub_collection('pda_protocols')
        self.protocol = Protocol(self.protocol_storage, self.name, self.me, self.partners, self.logger)

    def __repr__(self):
        return self.name

    def close(self):
        self.protocol.close()

    def handle_off_chain(self, method):
        print("decorator state is running")

    def master(self):
        return self.caller

    def get_storage(self, name):
        return self.contract_doc.get_sub_collection(f'contract_{name}')

    def run(self, caller):
        self.caller = caller
        empty_locals = {}
        exec(self.code,
             {'__builtins__':
              {'__build_class__': __build_class__, '__name__': __name__,
               'str': str, 'int': int, 'list': list, 'range': range, 'dict': dict, 'len': len, 'master': self.master,
               'Storage': self.get_storage, 'off_chain': self.handle_off_chain}}, empty_locals)
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
        return "ready"

    def call(self, caller, method, msg):
        self.caller = caller
        m = getattr(self.obj, method)
        try:
            reply = m(**msg['values'])
        except (TypeError, Exception) as e:
            return str(e)
        return reply

    def connect(self, address, pid, me, my_address, welcome):
        if pid != me:
            partner = Partner(address, pid, me, self.queue)
            self.partners.append(partner)
            self.partners_db[pid] = {'address': address}
            self.protocol.update_partners(self.partners)
            if welcome:
                partner.welcome(self.name, my_address)

    def consent(self, record, initiate, direct):
        # if initiate:
        #     return [partner.pid for partner in self.partners]
        if not self.partners or direct:
            self.protocol.record_message(record, direct)
            reply = True
        else:
            reply = self.protocol.handle_message(record, initiate)
        return reply

    def get_info(self):
        values = [list(iter(getattr(self.obj, attribute))) for attribute in self.members]
        return {'name': self.name, 'contract': self.class_name, 'code': self.code,
                'methods': self.methods, 'members': self.members, 'values': values}
