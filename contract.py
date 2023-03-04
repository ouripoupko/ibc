from builtins import __build_class__
from partner import Partner
from pbft import PBFT
from nakamoto import Nakamoto
import numpy as np
from numpy.linalg import eig
from datetime import datetime
import hashlib


class Contract:
    def __init__(self, contract_doc, hash_code, code, me, my_address, logger, queue):
        # the database
        self.contract_doc = contract_doc
        # the contract
        self.hash_code = hash_code
        self.class_name = ''
        self.code = code
        self.me = me
        self.my_address = my_address
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
            if key != me:
                self.partners.append(Partner(self.partners_db[key]['address'], key, my_address, me, self.queue))
        # consensus protocols
        self.protocol_storage = self.contract_doc.get_sub_collection('pda_protocols')
        self.protocol = None
        if self.contract_doc['protocol'] == 'POW':
            self.protocol = Nakamoto(self.protocol_storage, self.hash_code, self.me, self.partners, self.logger)
        elif self.contract_doc['protocol'] == 'BFT':
            self.protocol = PBFT(self.protocol_storage, self.hash_code, self.me, self.partners, self.logger)

    def __repr__(self):
        return self.hash_code

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

    def hashcode(self, object):
        return hashlib.sha256(str(object).encode('utf-8')).hexdigest()

    def elapsed_time(self, start, end):
        delta = datetime.strptime(end, '%Y%m%d%H%M%S%f') - datetime.strptime(start, '%Y%m%d%H%M%S%f')
        return delta.total_seconds()

    def get_storage(self, name):
        return self.contract_doc.get_sub_collection(f'contract_{name}')

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
               'min': min, 'elapsed_time': self.elapsed_time,
               'hashcode': self.hashcode}},
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
        m = getattr(self.obj, method, None)
        if m:
            try:
                return m(**msg['values'])
            except (TypeError, Exception) as e:
                return str(e)
        else:
            if method == 'get_partners':
                return [{('agent' if key == '_id' else key): self.partners_db[pid][key]
                          for key in self.partners_db[pid]} for pid in self.partners_db]

    def connect(self, address, pid, profile, welcome):
        self.partners_db[pid] = {'address': address, 'profile': profile}
        if pid != self.me:
            partner = Partner(address, pid, self.my_address, self.me, self.queue)
            self.partners.append(partner)
            self.protocol.update_partners(self.partners)
            if welcome:
                partner.welcome(self.hash_code)
        return {'reply': 'join success'}

    def consent(self, record, initiate, direct):
        # if initiate:
        #     return [partner.pid for partner in self.partners]
        if not self.partners or direct:
            self.protocol.record_message(record)
            reply = [record]
        else:
            reply = self.protocol.handle_message(record, initiate)
        return reply

    def get_info(self):
        values = [list(iter(getattr(self.obj, attribute))) for attribute in self.members]
        values = [[str(val) for val in row] for row in values]
        return {'name': self.hash_code, 'contract': self.class_name, 'code': self.code,
                'methods': self.methods, 'members': self.members, 'values': values}


# from eth.vm.forks.paris import ParisVM
# from eth.db.atomic import AtomicDB
# from eth.rlp.headers import BlockHeader
# from eth.vm.chain_context import ChainContext
# state = ParisVM.build_state(AtomicDB(), BlockHeader(difficulty=0, block_number=-1, gas_limit=0), ChainContext(None))
# contract = {
# 	"functionDebugData": {},
# 	"generatedSources": [],
# 	"linkReferences": {},
# 	"object": "608060405234801561001057600080fd5b50610150806100206000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c80632e64cec11461003b5780636057361d14610059575b600080fd5b610043610075565b60405161005091906100d9565b60405180910390f35b610073600480360381019061006e919061009d565b61007e565b005b60008054905090565b8060008190555050565b60008135905061009781610103565b92915050565b6000602082840312156100b3576100b26100fe565b5b60006100c184828501610088565b91505092915050565b6100d3816100f4565b82525050565b60006020820190506100ee60008301846100ca565b92915050565b6000819050919050565b600080fd5b61010c816100f4565b811461011757600080fd5b5056fea26469706673582212209a159a4f3847890f10bfb87871a61eba91c5dbf5ee3cf6398207e292eee22a1664736f6c63430008070033",
# 	"opcodes": "PUSH1 0x80 PUSH1 0x40 MSTORE CALLVALUE DUP1 ISZERO PUSH2 0x10 JUMPI PUSH1 0x0 DUP1 REVERT JUMPDEST POP PUSH2 0x150 DUP1 PUSH2 0x20 PUSH1 0x0 CODECOPY PUSH1 0x0 RETURN INVALID PUSH1 0x80 PUSH1 0x40 MSTORE CALLVALUE DUP1 ISZERO PUSH2 0x10 JUMPI PUSH1 0x0 DUP1 REVERT JUMPDEST POP PUSH1 0x4 CALLDATASIZE LT PUSH2 0x36 JUMPI PUSH1 0x0 CALLDATALOAD PUSH1 0xE0 SHR DUP1 PUSH4 0x2E64CEC1 EQ PUSH2 0x3B JUMPI DUP1 PUSH4 0x6057361D EQ PUSH2 0x59 JUMPI JUMPDEST PUSH1 0x0 DUP1 REVERT JUMPDEST PUSH2 0x43 PUSH2 0x75 JUMP JUMPDEST PUSH1 0x40 MLOAD PUSH2 0x50 SWAP2 SWAP1 PUSH2 0xD9 JUMP JUMPDEST PUSH1 0x40 MLOAD DUP1 SWAP2 SUB SWAP1 RETURN JUMPDEST PUSH2 0x73 PUSH1 0x4 DUP1 CALLDATASIZE SUB DUP2 ADD SWAP1 PUSH2 0x6E SWAP2 SWAP1 PUSH2 0x9D JUMP JUMPDEST PUSH2 0x7E JUMP JUMPDEST STOP JUMPDEST PUSH1 0x0 DUP1 SLOAD SWAP1 POP SWAP1 JUMP JUMPDEST DUP1 PUSH1 0x0 DUP2 SWAP1 SSTORE POP POP JUMP JUMPDEST PUSH1 0x0 DUP2 CALLDATALOAD SWAP1 POP PUSH2 0x97 DUP2 PUSH2 0x103 JUMP JUMPDEST SWAP3 SWAP2 POP POP JUMP JUMPDEST PUSH1 0x0 PUSH1 0x20 DUP3 DUP5 SUB SLT ISZERO PUSH2 0xB3 JUMPI PUSH2 0xB2 PUSH2 0xFE JUMP JUMPDEST JUMPDEST PUSH1 0x0 PUSH2 0xC1 DUP5 DUP3 DUP6 ADD PUSH2 0x88 JUMP JUMPDEST SWAP2 POP POP SWAP3 SWAP2 POP POP JUMP JUMPDEST PUSH2 0xD3 DUP2 PUSH2 0xF4 JUMP JUMPDEST DUP3 MSTORE POP POP JUMP JUMPDEST PUSH1 0x0 PUSH1 0x20 DUP3 ADD SWAP1 POP PUSH2 0xEE PUSH1 0x0 DUP4 ADD DUP5 PUSH2 0xCA JUMP JUMPDEST SWAP3 SWAP2 POP POP JUMP JUMPDEST PUSH1 0x0 DUP2 SWAP1 POP SWAP2 SWAP1 POP JUMP JUMPDEST PUSH1 0x0 DUP1 REVERT JUMPDEST PUSH2 0x10C DUP2 PUSH2 0xF4 JUMP JUMPDEST DUP2 EQ PUSH2 0x117 JUMPI PUSH1 0x0 DUP1 REVERT JUMPDEST POP JUMP INVALID LOG2 PUSH5 0x6970667358 0x22 SLT KECCAK256 SWAP11 ISZERO SWAP11 0x4F CODESIZE SELFBALANCE DUP10 0xF LT 0xBF 0xB8 PUSH25 0x71A61EBA91C5DBF5EE3CF6398207E292EEE22A1664736F6C63 NUMBER STOP ADDMOD SMOD STOP CALLER ",
# 	"sourceMap": "199:356:0:-:0;;;;;;;;;;;;;;;;;;;"
# }