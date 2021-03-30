from tinydb import TinyDB, Query
from tinydb.table import Table

import string
import random
import operator
import os
from typing import Optional, Mapping, Iterable, List, Union, Callable, Dict


class StringTable(Table):

    def __init__(self, *args, **kwargs):
        Table.__init__(self, *args, **kwargs)
        self.document_id_class = str
        self.document_class = dict

    def __iter__(self):
        # Iterate all documents and their IDs
        return iter(self._read_table())

    def _get_next_id(self):
        next_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

        # Read the table documents
        table = self._read_table()

        # verify uniqueness
        while next_id in table:
            next_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

        return next_id

    def _read_table(self) -> dict:
        # Retrieve the tables from the storage
        tables = self._storage.read()

        if tables is None:
            # The database is empty
            return {}

        # Retrieve the current table's data
        return tables.get(self.name, {})

    def get(
        self,
        cond: Optional[Query] = None,
        doc_id: Optional[str] = None,
    ):
        if doc_id is not None:
            # Retrieve a document specified by its ID
            table = self._read_table()
            return table.get(doc_id, None)

        elif cond is not None:
            # Find a document specified by a query
            for doc in self:
                if cond(doc):
                    return doc

            return None

        raise RuntimeError('You have to pass either cond or doc_id')

    def set(self, doc_id, document):
        # Make sure the document implements the ``Mapping`` interface
        if not isinstance(document, Mapping):
            raise ValueError('Document is not a Mapping')

        # Now, we update the table and add the document
        def updater(table: dict):
            table[doc_id] = document

        # See below for details on ``Table._update``
        self._update_table(updater)

        return doc_id

    def update(
        self,
        fields: Union[Mapping, Callable[[Mapping], None]],
        cond: Optional[Query] = None,
        doc_ids: Optional[Iterable[str]] = None,
    ) -> List[str]:
        # Define the function that will perform the update
        if callable(fields):
            def perform_update(table, doc_id):
                # Update documents by calling the update function provided by
                # the user
                fields(table[doc_id])
        else:
            def perform_update(table, doc_id):
                # Update documents by setting all fields from the provided data
                table[doc_id].update(fields)

        if doc_ids is not None:
            # Perform the update operation for documents specified by a list
            # of document IDs

            updated_ids = list(doc_ids)

            def updater(table: dict):
                # Call the processing callback with all document IDs
                for doc_id in updated_ids:
                    perform_update(table, doc_id)

            # Perform the update operation (see _update_table for details)
            self._update_table(updater)

            return updated_ids

        elif cond is not None:
            pass
        else:
            pass

    def contains(
        self,
        cond: Optional[Query] = None,
        doc_id: Optional[str] = None
    ) -> bool:
        if doc_id is not None:
            # Documents specified by ID
            return self.get(doc_id=doc_id) is not None

        elif cond is not None:
            # Document specified by condition
            return self.get(cond) is not None

        raise RuntimeError('You have to pass either cond or doc_id')


class StringTinyDB(TinyDB):

    def __init__(self, *args, **kwargs):
        TinyDB.__init__(self, *args, **kwargs)
        self.table_class = StringTable
        self._tables = {}  # type: Dict[str, StringTable]

    def table(self, name: str, **kwargs) -> StringTable:
        if name in self._tables:
            return self._tables[name]

        table = self.table_class(self.storage, name, **kwargs)
        self._tables[name] = table

        return table


class StorageBridge:
    def __init__(self):
        self.ibc = None

    def connect(self):
        path = './database/'
        os.makedirs(path, exist_ok=True)
        self.ibc = StringTinyDB(path+'ibc.json')

    def get_collection(self, agent, db, name=None):
        name = name if name else db
        if agent:
            path = './database/{}/'.format(agent)
            os.makedirs(path, exist_ok=True)
            db = StringTinyDB(path+db+'.json')
        else:
            db = self.ibc
        return Storage(db.table(name))

    @staticmethod
    def get_document(agent, db):
        path = './database/{}/'.format(agent)
        os.makedirs(path, exist_ok=True)
        db = StringTinyDB(path+db+'.json')
        table = db.table('parameters')
        if not table.contains(doc_id='parameters'):
            table.set('parameters', {})
        return Parameters(table)


class Storage:
    """Storage behaves like a list of dicts with persistence over Firebase"""

    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, key):
        return self.collection.get(doc_id=key)

    def __setitem__(self, key, value):
        self.collection.set(key, value)

    def __delitem__(self, key):
        pass

    def __iter__(self):
        return iter(self.collection)

    def __contains__(self, item):
        return item and self.collection.contains(doc_id=item)

    def __len__(self):
        pass

    def update(self, key, name, value):
        self.collection.update({name: value}, doc_ids=[key])

    def update_append(self, key, name, value):
        def updater(document):
            document[name].append(value)
        self.collection.update(updater, doc_ids=[key])

    def get(self, field, condition, value):
        condition_list = {'==': operator.eq}
        self.collection.search(condition_list[condition](Query()[field], value))

    def append(self, record):
        return self.collection.insert(record)


class Parameters:
    def __init__(self, collection):
        self.collection = collection
        self.parameters = self.collection.get(doc_id='parameters')

    def get(self, name):
        return self.parameters.get(name)

    def set(self, name, value):
        self.parameters[name] = value
        self.collection.set('parameters', self.parameters)

    def increment(self, name, value):
        old_value = self.parameters.get(name, 0)
        self.parameters[name] = old_value + value
        self.collection.set('parameters', self.parameters)

    def append(self, name, value):
        self.parameters[name].append(value)
        self.collection.set('parameters', self.parameters)
