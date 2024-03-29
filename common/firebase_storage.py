from google.cloud import firestore
from google.oauth2 import service_account
import os
import json
import hashlib
import time


class StorageBridge:
    def __init__(self, logger):
        self.db = None
        self.ibc = None
        self.logger = logger

    def connect(self):
        self.db = firestore.Client()
        self.ibc = self.db.collection('ibc')

    def get_transaction(self):
        return self.db.transaction()

    @staticmethod
    @firestore.transactional
    def execute_transaction(transaction, method, *args):
        try:
            return method(*args)
        except Exception as err:
            return False

    def get_collection(self, doc=None, name=None, collection=None, transaction=None):
        collection = self.ibc if collection is None else collection.collection
        collection = collection if doc is None else collection.document(doc).collection(name)
        return Storage(self.db, collection, transaction)

    def get_document(self, name, parent, collection=None):
        collection = self.ibc if collection is None else collection.collection
        return Record(collection.document(parent), name)

    @staticmethod
    def listen(storage, name, condition):
        def on_snapshot(doc_snapshot, changes, read_time):
            with condition:
                condition.notify_all()

        return storage.collection.document(name).on_snapshot(on_snapshot)

    @staticmethod
    def stop_listen(listener):
        listener.unsubscribe()


class Storage:
    """Storage behaves like a list of dicts with persistence over Firebase"""

    def __init__(self, db, collection, transaction):
        self.db = db
        self.collection = collection
        self.batch = None
        self.transaction = transaction

    def __getitem__(self, key):
        return self.collection.document(key).get(transaction=self.transaction).to_dict()

    def __setitem__(self, key, value):
        if self.transaction:
            self.transaction.set(self.collection.document(key), value)
        elif self.batch:
            self.batch.set(self.collection.document(key), value)
        else:
            self.collection.document(key).set(value)

    def __delitem__(self, key):
        self.collection.document(key).delete()

    def __iter__(self):
        return iter([doc.id for doc in self.collection.stream(transaction=self.transaction)])

    def __contains__(self, item):
        return item and self.collection.document(item).get(transaction=self.transaction).exists

    def __len__(self):
        pass

    def update(self, key, dictionary):
        if self.transaction:
            self.transaction.update(self.collection.document(key), dictionary)
        elif self.batch:
            self.batch.update(self.collection.document(key), dictionary)
        else:
            self.collection.document(key).update(dictionary)

    def update_append(self, key, name, value):
        if self.batch:
            self.batch.update(self.collection.document(key), {name: firestore.ArrayUnion([value])})
        else:
            self.collection.document(key).update({name: firestore.ArrayUnion([value])})

    def get(self, field, condition, value):
        return {doc.id: doc.to_dict() for doc in self.collection.where(field, condition, value).get()}

    def append(self, record):
        key = hashlib.sha1(str(record).encode("utf-8")).hexdigest()
        self[key] = record
        return key

    def withhold(self):
        if not self.batch:
            self.batch = self.db.batch()

    def commit(self):
        self.batch.commit()
        self.batch = None


class Record:
    def __init__(self, document, name):
        self.document = document
        self.name = name

    def get_all(self):
        # return self.document.get([self.record+'.'+name]).to_dict().get(self.record)
        reply = self.document.get([self.name]).to_dict().get(self.name)
        return reply if reply else {}

    def get(self, key):
        record = self.get_all()
        return record.get(key) if record else None

    def update(self, dictionary, storage=None):
        if storage is not None and storage.batch is not None:
            storage.batch.update(self.document, {self.name+'.'+key: value for key, value in dictionary.items()})
        else:
            self.document.update({self.name+'.'+key: value for key, value in dictionary.items()})

    def increment(self, key, value, storage=None):
        if storage is not None and storage.batch is not None:
            storage.batch.update(self.document, {self.name+'.'+key: firestore.Increment(value)})
        else:
            self.document.update({self.name+'.'+key: firestore.Increment(value)})

    def append(self, key, value, storage=None):
        if storage is not None and storage.batch is not None:
            storage.batch.update(self.document, {self.name+'.'+key: firestore.ArrayUnion([value])})
        else:
            self.document.update({self.name+'.'+key: firestore.ArrayUnion([value])})
