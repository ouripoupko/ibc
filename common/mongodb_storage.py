from pymongo import MongoClient
from bson.objectid import ObjectId
import uuid
import os


class WritePermissionException(Exception):
    pass

class DBBridge:
    def __init__(self):
        self.connection = None
        self.allow_write = False

    def connect(self, port, allow_write = False):
        self.connection = MongoClient(host=os.getenv('MONGODB_GATEWAY'), port=int(port))
        self.allow_write = allow_write
        return self

    def disconnect(self):
        self.connection.close()

    def get_root_collection(self):
        db = self.connection['ibc']
        return Collection(db, db['agents'], self.allow_write)


class Collection:
    """Storage behaves like a list of dicts with persistence over MongoDB"""

    def __init__(self, db, collection, allow_write):
        self.db = db
        self.collection = collection
        self.allow_write = allow_write

    def __getitem__(self, key):
        return Document(self, key)

    def __setitem__(self, key, value):
        if not self.allow_write:
            raise WritePermissionException()
        value['_id'] = key
        self.collection.update_one({'_id': key}, {'$set': value}, upsert=True)

    def __delitem__(self, key):
        if not self.allow_write:
            raise WritePermissionException()
        if self.collection.find_one({'_id': key}):
            self.collection.delete_one({'_id': key})
        else:
            self.collection.delete_one({'_id': ObjectId(key)})

    def __iter__(self):
        for doc in self.collection.find():
            yield doc['_id']

    def __contains__(self, item):
        return self.collection.find_one({'_id': item}) is not None

    def __len__(self):
        return self.collection.count_documents({})

    def store(self, collection):
        if not self.allow_write:
            raise WritePermissionException()
        for key in collection:
            collection[key]['_id'] = key
        self.collection.delete_many({})
        if collection:
            self.collection.insert_many(collection.values())

    def append(self, item):
        if not self.allow_write:
            raise WritePermissionException()
        result = self.collection.insert_one(item)
        return str(result.inserted_id)

    def get_last(self, field=None, value=None):
        if field:
            result = list(self.collection.find({field: value}).sort('_id', -1).limit(1))
        else:
            result = list(self.collection.find().sort('_id', -1).limit(1))
        return result[0]['_id'] if result else None

    def get(self, field=None, operator=None, value=None):
        if operator == '>':
            return {item['_id']: item for item in list(self.collection.find({field: {'$gt': value}}))}
        elif operator == '==':
            # return {item['_id']: item for item in list(self.collection.find({field: value}))}
            return {str(item['_id']):
                    {key: (str(value) if key == '_id' else value) for key, value in item.items()}
                    for item in list(self.collection.find({field: value}))}
        elif operator is None:
            if field is None:
                return {str(item['_id']):
                        {key: (str(value) if key == '_id' else value) for key, value in item.items()}
                        for item in list(self.collection.find())}
            else:
                return self[field] if field in self else None


class Document:

    def __init__(self, storage, key, parent=None):
        self.storage = storage
        real_key = ObjectId(key) if ObjectId.is_valid(key) else key
        self.key = real_key if real_key in self.storage else key
        self.parent = parent

    def __getitem__(self, key):
        document = self.storage.collection.find_one({'_id': self.key})
        return document.get(key)

    def __setitem__(self, key, value):
        if not self.storage.allow_write:
            raise WritePermissionException()
        self.storage[self.key] = {key: value}

    def __delitem__(self, key):
        if not self.storage.allow_write:
            raise WritePermissionException()
        self.storage.collection.update_one({'_id': self.key}, {'$unset': {key: ''}})

    def __contains__(self, item):
        return item in self.storage.collection.find_one({'_id': self.key})

    def __iter__(self):
        return iter(self.get_dict())

    def create_sub_collection(self, name):
        if not self.storage.allow_write:
            raise WritePermissionException()
        uid = str(uuid.uuid4())
        self.storage[self.key] = {name: uid}

    def get_sub_collection(self, name):
        document = self.storage.collection.find_one({'_id': self.key})
        if not document or name not in document:
            self.create_sub_collection(name)
            document = self.storage.collection.find_one({'_id': self.key})
        db = self.storage.db
        uid = document[name]
        return Collection(self.storage.db, db[uid], self.storage.allow_write)

    def get_key(self):
        return self.key

    def get_dict(self):
        reply = self.storage.collection.find_one({'_id': self.key})
        if reply:
            del reply['_id']
        return reply or {}

    def update(self, value):
        if not self.storage.allow_write:
            raise WritePermissionException()
        self.storage.collection.update_one({'_id': self.key}, {'$set': value}, upsert=True)

    def exists(self):
        return self.key in self.storage

