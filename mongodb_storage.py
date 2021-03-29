from pymongo import MongoClient
from collections.abc import MutableMapping
import os


class StorageBridge:
    def __init__(self):
        self.connection = None

    def connect(self):
        user = os.getenv('PSQL_USER')
        password = os.getenv('PSQL_PASSWORD')
        self.connection = MongoClient()

    def get_collection(self, db, name):
        session = self.connection.start_session(causal_consistency=True)
        return Storage(self.connection[db][name], session)


class Storage:
    """Storage behaves like a list of dicts with persistence over MongoDB"""

    def __init__(self, collection, session):
        self.collection = collection
        self.session = session

    def __getitem__(self, key):
        return self.collection.find_one(key, projection={'_id': False})

    def __setitem__(self, key, value):
        self.collection.update_one(key, value)

    def __delitem__(self, key):
        pass

    def __iter__(self):
        return self.collection.find(projection={'_id': False}, session=self.session)

    def __contains__(self, item):
        return self.collection.count_documents(item, limit=1, session=self.session)

    def __len__(self):
        pass

    def append(self, item):
        self.collection.insert_one(item, session=self.session)
