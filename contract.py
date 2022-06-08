from builtins import __build_class__
from partner import Partner
from protocol import Protocol
import numpy as np
from numpy.linalg import eig
from datetime import datetime


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
        self.current_timestamp = None
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

    def eig(self, array):
        npa = np.array(array)
        npa = npa/npa.sum(axis=0)
        w, v = eig(npa)
        w.sort()
        return w.tolist()

    def master(self):
        return self.caller

    def timestamp(self):
        return self.current_timestamp

    def elapsed_time(self, start, end):
        delta = datetime.strptime(end, '%Y%m%d%H%M%S%f') - datetime.strptime(start, '%Y%m%d%H%M%S%f')
        return delta.total_seconds()

    def get_storage(self, name):
        return self.contract_doc.get_sub_collection(f'contract_{name}')

    def read(self, address, agent, contract, method, arguments, values):
        partner = Partner(address, agent, self.me, None)
        return partner.read(contract, method, arguments, values)

    def run(self, caller, timestamp):
        self.caller = caller
        self.current_timestamp = timestamp
        empty_locals = {}
        exec(self.code,
             {'__builtins__':
              {'__build_class__': __build_class__, '__name__': __name__,
               'str': str, 'int': int, 'list': list, 'range': range, 'dict': dict, 'len': len, 'master': self.master,
               'timestamp': self.timestamp, 'Storage': self.get_storage, 'off_chain': self.handle_off_chain,
               'eig': self.eig, 'print': print, 'set': set, 'enumerate': enumerate, 'abs': abs, 'sum': sum,
               'min': min, 'Read': self.read, 'elapsed_time': self.elapsed_time}},
             empty_locals)
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

    def call(self, caller, method, msg, timestamp):
        self.caller = caller
        self.current_timestamp = timestamp
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
            self.protocol.record_message(record)
            reply = True
        else:
            reply = self.protocol.handle_message(record, initiate)
        return reply

    def get_info(self):
        values = [list(iter(getattr(self.obj, attribute))) for attribute in self.members]
        values = [[str(val) for val in row] for row in values]
        return {'name': self.name, 'contract': self.class_name, 'code': self.code,
                'methods': self.methods, 'members': self.members, 'values': values}
