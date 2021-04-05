from google.cloud import firestore
from google.oauth2 import service_account
import os
import json


class StorageBridge:
    def __init__(self):
        self.ibc = None

    def connect(self):
        credentials = service_account.Credentials.from_service_account_info(json.loads(os.getenv("CREDENTIALS")))
        self.ibc = firestore.Client(credentials=credentials).collection('ibc')

    def get_collection(self, doc, name, collection=None):
        collection = self.ibc if collection is None else collection.collection
        return Storage(collection.document(doc).collection(name))

    def get_document(self, doc, collection=None):
        collection = self.ibc if collection is None else collection.collection
        return Parameters(collection.document(doc))

    @staticmethod
    def listen(storage, name, condition):
        def on_snapshot(doc_snapshot, changes, read_time):
            print('Received update from db')
            with condition:
                condition.notify_all()

        storage.collection.document(name).on_snapshot(on_snapshot)


class Storage:
    """Storage behaves like a list of dicts with persistence over Firebase"""

    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, key):
        return self.collection.document(key).get().to_dict()

    def __setitem__(self, key, value):
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
        self.collection.document(key).update({name: value})

    def update_append(self, key, name, value):
        self.collection.document(key).update({name: firestore.ArrayUnion([value])})

    def get(self, field, condition, value):
        self.collection.where(field, condition, value).get()

    def append(self, record):
        doc_ref = self.collection.document()
        doc_ref.set(record)
        return doc_ref.id

    def listen(self, name, notify):
        def on_snapshot(document_snapshot, changes, read_time):
            print('db change detected')
            notify()
        self.collection.document(name).on_snapshot(on_snapshot)



class Parameters:
    def __init__(self, document):
        self.document = document

    def get(self, name):
        parameters = self.document.get(['parameters.'+name]).to_dict().get('parameters')
        return parameters.get(name) if parameters is not None else None

    def set(self, name, value):
        self.document.update({'parameters.'+name: value})

    def increment(self, name, value):
        self.document.update({'parameters.'+name: firestore.Increment(value)})

    def append(self, name, value):
        self.document.update({'parameters.'+name: firestore.ArrayUnion([value])})
