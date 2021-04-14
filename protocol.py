from enum import Enum
import hashlib
from threading import Thread, Condition
import time


class ProtocolStep(Enum):
    LEADER = 1
    PREPARE = 2
    COMMIT = 3
    DONE = 4


def cleanup(storage, hash_code):
    time.sleep(30)
    del storage[hash_code]


class Protocol:
    def __init__(self, storage_bridge, storage, contract_name, partners):
        self.storage_bridge = storage_bridge
        self.storage = storage
        self.contract_name = contract_name
        self.partners = partners

    @staticmethod
    def execute_sync(storage, hash_code):
        if hash_code not in storage:
            storage[hash_code] = {'locked': True}
            return True
        if not storage[hash_code].get('locked'):
            storage.update(hash_code, {'locked': True})
            return True
        return False

    def synchronize(self, hash_code):
        while True:
            transaction = self.storage_bridge.get_transaction()
            transactional = self.storage_bridge.get_collection(collection=self.storage, transaction=transaction)
            if self.storage_bridge.execute_transaction(transaction, self.execute_sync, transactional, hash_code):
                break
            else:
                condition = Condition()
                listener = self.storage_bridge.listen(self.storage, hash_code, condition)
                with condition:
                    condition.wait(2)
                self.storage_bridge.stop_listen(listener)

    def release(self, hash_code):
        self.storage.update(hash_code, {'locked': False})

    def start_protocol(self, record, is_leader):
        hash_code = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        self.synchronize(hash_code)
        self.storage.update(hash_code, {'prepared': [],
                                        'committed': [],
                                        'keep': record,
                                        'commit_state': ProtocolStep.PREPARE.value})
        # a leader sends leader messages
        if is_leader:
            for partner in self.partners:
                partner.consent(self.contract_name, ProtocolStep.LEADER.name, record)
        # all send prepare messages
        for partner in self.partners:
            partner.consent(self.contract_name, ProtocolStep.PREPARE.name, hash_code)
        # a non leader sends delayed messages
        if not is_leader:
            delayed = self.storage[hash_code].get('delayed', [])
            for delayed_record in delayed:
                self.handle_message(delayed_record, False, True)
            self.storage.update(hash_code, {'delayed': []})
        # release and wait till protocol ends
        self.release(hash_code)
        condition = Condition()
        listener = self.storage_bridge.listen(self.storage, hash_code, condition)
        while True:
            with condition:
                condition.wait(2)
            if self.storage[hash_code].get('commit_state', ProtocolStep.PREPARE.value) == ProtocolStep.DONE.value:
                break
        self.storage_bridge.stop_listen(listener)
        # raise a thread to sleep for late messages, then clean up
        Thread(target=cleanup, args=(self.storage, hash_code)).start()
        return True

    def handle_message(self, record, initiate, direct=False):
        if initiate:
            # the leader starts a new session
            return self.start_protocol(record, True)
        else:
            step = ProtocolStep[record['message']['msg']['step']]
            if step == ProtocolStep.LEADER:
                # a follower received original record
                original_record = record['message']['msg']['data']
                return self.start_protocol(original_record, False)
            else:
                hash_code = record['message']['msg']['data']
                if not direct:
                    self.synchronize(hash_code)
                from_pid = record['message']['from']
                # a protocol message arrived before the original record
                if not self.storage[hash_code].get('keep'):
                    self.storage.update_append(hash_code, 'delayed', record)
                # a protocol message arrived after protocol completed
                elif self.storage[hash_code].get('commit_state') == ProtocolStep.DONE.value:
                    pass
                # a prepare message arrived
                elif step == ProtocolStep.PREPARE:
                    self.storage.update_append(hash_code, 'prepared', from_pid)
                    if len(self.storage[hash_code].get('prepared', [])) * 3 >= len(self.partners) * 2:
                        for partner in self.partners:
                            partner.consent(self.contract_name, ProtocolStep.COMMIT.name, hash_code)
                        self.storage.update(hash_code, {'commit_state': ProtocolStep.COMMIT.value})
                        if len(self.storage[hash_code].get('committed', [])) * 3 >= len(self.partners) * 2:
                            self.storage.update(hash_code, {'commit_state': ProtocolStep.DONE.value})
                elif step == ProtocolStep.COMMIT:
                    self.storage.update_append(hash_code, 'committed', from_pid)
                    if len(self.storage[hash_code].get('committed', [])) * 3 >= len(self.partners) * 2 and \
                            self.storage[hash_code].get('commit_state') == ProtocolStep.COMMIT.value:
                        self.storage.update(hash_code, {'commit_state': ProtocolStep.DONE.value})
                if not direct:
                    self.release(hash_code)
        return False
