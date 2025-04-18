from builtins import __build_class__
from datetime import datetime
import hashlib
import random
import logging
from statistics import median

def hashcode(something):
    return hashlib.sha256(str(something).encode('utf-8')).hexdigest()

def elapsed_time(start, end):
    delta = datetime.strptime(end, '%Y%m%d%H%M%S%f') - datetime.strptime(start, '%Y%m%d%H%M%S%f')
    return delta.total_seconds()

class State:

    def __init__(self, contract_doc, partners_db, navigator):
        self.contract_doc = contract_doc
        self.partners_db = partners_db
        self.class_name = ''
        self.obj = None
        self.members = []
        self.methods = []
        self.current_timestamp = None
        self.caller = None
        self.navigator = navigator
        self.logger = logging.getLogger('State')

    def master(self):
        return self.caller

    def timestamp(self):
        return self.current_timestamp

    def get_storage(self, name):
        return self.contract_doc.get_sub_collection(f'contract_{name}')

    def get_partners(self):
        return [{key: self.partners_db[pid][key]
                 for key in self.partners_db[pid]} | {'agent': pid} for pid in self.partners_db]

    def get_partner_keys(self):
        return [pid for pid in self.partners_db]

    def random(self, seed, state, limit):
        # make sure execution is consistent for all partners
        if not seed and not state:
            return 0
        if seed:
            random.seed(seed)
        if state:
            random.setstate(state)
        return [random.randrange(limit), random.getstate()]

    def read(self, contract_id, method, arguments):
        contract = self.navigator.get_contract(contract_id)
        if not contract:
            return None
        partners = set(contract.state.get_partner_keys())
        all_exist = [partner in partners for partner in self.partners_db]
        if not all(all_exist):
            return None
        fake_record = {'agent': self.caller,
                       'method': method,
                       'message': {'values': arguments},
                       'timestamp': self.current_timestamp}
        return contract.call(fake_record, False)

    def parameters(self, parameter):
        return (self.contract_doc['medians'] or {}).get(parameter, 0)

    def run(self, caller, timestamp):
        self.caller = caller
        self.current_timestamp = timestamp
        empty_locals = {}
        exec(self.contract_doc['code'],
             {'__builtins__':
                  {'__build_class__': __build_class__, '__name__': __name__,
                   'str': str, 'int': int, 'list': list, 'range': range, 'dict': dict, 'len': len,
                   'print': print, 'type': type, 'set': set,
                   'enumerate': enumerate, 'abs': abs, 'sum': sum, 'min': min, 'round': round,
                   'master': self.master, 'timestamp': self.timestamp, 'Storage': self.get_storage,
                   'partners': self.get_partner_keys, 'elapsed_time': elapsed_time,
                   'hashcode': hashcode, 'random': self.random, 'read': self.read, 'parameters': self.parameters}},
             empty_locals)
        class_object = list(empty_locals.values())[0]
        self.class_name = class_object.__name__
        self.obj = class_object(**self.contract_doc['constructor'])
        attributes = [attribute for attribute in dir(self.obj) if not attribute.startswith('_')]
        self.members = [attribute for attribute in attributes if not callable(getattr(self.obj, attribute))]
        method_names = [attribute for attribute in attributes if callable(getattr(self.obj, attribute))]
        self.methods = [{'name': name,
                         'arguments': [arg for arg in
                                       list(getattr(self.obj, name).__code__.co_varnames)[1:]
                                       if not arg.startswith('_')]}
                        for name in method_names]
        return "ready"

    def update_parameters(self, parameters):
        before_parameters_update = getattr(self.obj, 'before_parameters_update', None)
        if before_parameters_update:
            before_parameters_update()

        all_parameters = self.contract_doc['parameters'] or {}
        medians = self.contract_doc['medians'] or {}
        for key, value in parameters.items():
            if key not in all_parameters:
                all_parameters[key] = {}
            all_parameters[key][self.caller] = value
            medians[key] = median(all_parameters[key].values())
        self.contract_doc.update({'parameters': all_parameters, 'medians': medians})

        after_parameters_update = getattr(self.obj, 'after_parameters_update', None)
        if after_parameters_update:
            after_parameters_update()

    def call(self, caller, method, msg, timestamp):
        self.caller = caller
        self.current_timestamp = timestamp
        if 'parameters' in msg:
            self.update_parameters(msg['parameters'])
        m = getattr(self.obj, method, None)
        if m:
            try:
                return m(**msg['values'])
            except (TypeError, Exception) as e:
                self.logger.exception('caught exception in contract call')
                return str(e)
        else:
            if method == 'get_partners':
                return self.get_partners()
            elif method == 'approve_partner':
                return True
            elif method == 'get_parameters':
                parameters = self.contract_doc['parameters'] or {}
                medians = self.contract_doc['medians'] or {}
                return {'parameters': {key: parameters[key].get(self.caller) for key in parameters},
                        'medians': medians}
