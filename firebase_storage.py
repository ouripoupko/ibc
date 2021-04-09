from google.cloud import firestore
from google.oauth2 import service_account
import os
import json
import hashlib
import time


class StorageBridge:
    def __init__(self):
        self.db = None
        self.ibc = None

    def connect(self):
        credentials = service_account.Credentials.from_service_account_info(json.loads(os.getenv("CREDENTIALS")))
        self.db = firestore.Client(credentials=credentials)
        self.ibc = self.db.collection('ibc')

    def get_collection(self, doc, name, collection=None):
        collection = self.ibc if collection is None else collection.collection
        return Storage(self.db, collection.document(doc).collection(name))

    def get_document(self, name, parent, collection=None):
        collection = self.ibc if collection is None else collection.collection
        return Record(collection.document(parent), name)

    @staticmethod
    def listen(storage, name, condition):
        def on_snapshot(doc_snapshot, changes, read_time):
            print('Received update from db')
            with condition:
                condition.notify_all()

        storage.collection.document(name).on_snapshot(on_snapshot)


class Storage:
    """Storage behaves like a list of dicts with persistence over Firebase"""

    def __init__(self, db, collection):
        self.db = db
        self.collection = collection
        self.batch = None

    def __getitem__(self, key):
        return self.collection.document(key).get().to_dict()

    def __setitem__(self, key, value):
        if self.batch:
            self.batch.set(self.collection.document(key), value)
        else:
            self.collection.document(key).set(value)

    def __delitem__(self, key):
        pass

    def __iter__(self):
        return iter([doc.id for doc in self.collection.stream()])

    def __contains__(self, item):
        return item and self.collection.document(item).get().exists

    def __len__(self):
        pass

    def update(self, key, name, value):
        if self.batch:
            self.batch.update(self.collection.document(key), {name: value})
        else:
            self.collection.document(key).update({name: value})

    def update_append(self, key, name, value):
        if self.batch:
            self.batch.update(self.collection.document(key), {name: firestore.ArrayUnion([value])})
        else:
            self.collection.document(key).update({name: firestore.ArrayUnion([value])})

    def get(self, field, condition, value):
        return [doc.to_dict() for doc in self.collection.where(field, condition, value).get()]

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

    def set(self, dictionary, storage=None):
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
