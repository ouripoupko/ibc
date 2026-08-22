# Writing Contracts

A contract on this blockchain is a single Python file containing exactly **one class**. That
class is instantiated once per contract instance, and from then on every call into the contract
invokes a method on that instance.

This document describes the sandbox the contract code runs in, and the storage API available
to it.

## The contract file

- The file must define exactly one top-level class — nothing else at module scope.
- The class is instantiated as `ClassName(**constructor_args)`, where `constructor_args` is the
  dict of arguments the contract was created with. Your `__init__` parameters must match those
  keys.
- Every public attribute (not starting with `_`) that is **not callable** is exposed as a
  contract *member* (readable state).
- Every public attribute that **is callable** is exposed as a contract *method* that partners can
  invoke. Its arguments are auto-discovered from the method's signature (`self` and any argument
  starting with `_` are excluded), so keep method signatures explicit — no `*args` / `**kwargs`
  magic if you want the arguments to be discoverable.
- A method's return value becomes the call's result. If a method raises, the exception is caught
  and its string representation is returned as the result instead of propagating.

### Reserved / auto-handled method names

If the class does **not** define these methods itself, calling them is handled automatically
instead of hitting your code:

| Method | Behavior |
|---|---|
| `get_partners` | Returns the list of connected partners (address, profile, agent id). |
| `approve_partner` | Returns `True` unconditionally (default join policy). |
| `get_parameters` | Returns this caller's submitted parameter values plus the current consensus medians. |

Define any of these yourself on your class to override the default behavior.

### Optional lifecycle hooks

If present on the class, these are called automatically around `parameters` updates (see
`parameters()` below):

- `before_parameters_update(self)` — called before new parameter values are merged in.
- `after_parameters_update(self)` — called after the medians have been recomputed and persisted.

## The sandbox: what's available inside a contract

The contract code does **not** run with normal Python builtins. Only the following names are
available:

**Builtins:** `str`, `int`, `list`, `range`, `dict`, `len`, `print`, `type`, `set`, `enumerate`,
`abs`, `sum`, `min`, `round`.

Note what's *missing*: no file/network/OS access, no `import`, no `open`, no `eval`, no `max`
(!), no `float`. Anything not in this list simply isn't defined — using it raises `NameError`.
Standard library modules cannot be imported from within a contract.

**Injected functions**, callable directly by name from anywhere in the contract:

| Function | Signature | Description |
|---|---|---|
| `master()` | `() -> agent_id` | Returns the id of the agent (partner) who initiated the current call. |
| `timestamp()` | `() -> str` | Returns the timestamp of the current call, format `YYYYMMDDHHMMSSffffff`. |
| `Storage(name)` | `(str) -> collection` | Returns a persistent, named storage collection scoped to this contract. See [Storage API](#storage-api) below. |
| `partners()` | `() -> [agent_id, ...]` | Returns the ids of all connected partners. |
| `elapsed_time(start, end)` | `(str, str) -> float` | Seconds between two `timestamp()`-formatted strings. |
| `hashcode(x)` | `(Any) -> str` | SHA-256 hex digest of `str(x)`. |
| `random(seed, state, limit)` | `(Any, Any, int) -> [int, state]` | Deterministic PRNG: pass `None`/falsy `seed` and `state` on the first call, then thread the returned `state` back in on subsequent calls so every partner computes the same sequence. Returns `[value_in_range(limit), new_state]`, or plain `0` if both `seed` and `state` are falsy. |
| `read(contract_id, method, arguments)` | `(str, str, dict) -> Any` | Read-only call into **another** contract's method, without going through consensus. Only succeeds if every one of *this* contract's partners is also a partner of the target contract (`arguments` is a plain dict of keyword args). |
| `parameters(name)` | `(str) -> Any` | Returns the current consensus (median) value for a governance parameter previously submitted via a call's `parameters` field; `0` if unset. |

There is no access to anything beyond what's listed above — everything the contract needs comes
through these functions.

### Governance parameters

A call into the contract may carry a `parameters` dict alongside its normal arguments, handled
before your method runs. Each partner's submitted value for a given key is recorded, and the
**median** across all partners becomes that parameter's consensus value, readable from anywhere
in your contract via `parameters(name)`. Use the `before_parameters_update` /
`after_parameters_update` hooks if your contract needs to react when this happens.

## Storage API

`Storage(name)` gives a contract a persistent, dict-like *collection*. Nesting is supported: a
stored value can itself hold a sub-collection, accessed as a *document*.

### Collection

Behaves like a mapping from key → document (a dict).

| Operation | Effect |
|---|---|
| `collection[key]` | Returns a document view over `key` (does not itself read the data — see Document below). |
| `collection[key] = value` | Upserts `value` (a dict) as the document stored at `key`. |
| `del collection[key]` | Deletes the document at `key`. |
| `for key in collection: ...` | Iterates all keys (document ids) in the collection. |
| `key in collection` | `True` if a document exists at `key`. |
| `len(collection)` | Number of documents in the collection. |
| `collection.store(other_dict)` | Replaces the **entire** collection's contents with `other_dict` (a `{key: value_dict}` mapping). Destructive — clears existing data first. |
| `collection.append(item)` | Inserts `item` (a dict) as a new document with an auto-generated id; returns the new id as a string. |
| `collection.get_last(field=None, value=None)` | Returns the id of the most-recently-inserted document, optionally filtered to documents where `field == value`. `None` if empty. |
| `collection.get(field=None, operator=None, value=None)` | Flexible read (see below). |

`get()` behavior depends on which arguments are passed:

- `get(field, '>', value)` — documents where `field > value`, as `{id: document}`.
- `get(field, '==', value)` — documents where `field == value`, as `{id: document}` (ids are
  stringified).
- `get()` (no args) — **every** document in the collection, as `{id: document}`.
- `get(field)` (no operator) — treats `field` as a document key/id: returns that single
  document if it exists, else `None`. (Note the inconsistent return shape vs. the other three
  forms — this one returns a single document, not a dict of documents.)

### Document

A single document (dict-like) inside a collection, obtained via `collection[key]`.

| Operation | Effect |
|---|---|
| `document[field]` | Returns the value of `field`, or `None` if absent. |
| `document[field] = value` | Sets `field` to `value` on this document (upserts the document if it doesn't exist yet). |
| `del document[field]` | Removes `field` from the document. |
| `field in document` | `True` if the document has `field` set. |
| `for field in document: ...` | Iterates the document's field names. |
| `len(document)` | Number of fields on the document. |
| `document.exists()` | `True` if the underlying document exists in storage. |
| `document.get_key()` | Returns this document's id/key. |
| `document.get_dict()` | Returns the full document as a plain `dict`. |
| `document.update(value)` | Merges `value` (a dict of `{field: val}`) into the document, upserting if needed. Prefer this over setting fields one at a time when updating several fields at once. |
| `document.create_sub_collection(name)` | Attaches a fresh, empty nested collection to this document under `name`. |
| `document.get_sub_collection(name)` | Returns the nested collection at `name`, creating it first if it doesn't exist yet. |

## Minimal example

```python
class Counter:
    def __init__(self, start=0):
        self._counter = Storage('state')['counter']
        if not self._counter['owner']:
            self._counter.update({'value': start, 'owner': master()})

    def increment(self, amount):
        current = self._counter['value'] or 0
        self._counter.update({'value': current + amount, 'last_caller': master(), 'at': timestamp()})
        return current + amount

    def get_value(self):
        return self._counter['value']
```

- `increment` and `get_value` are exposed as callable *methods*, with `amount` auto-discovered
  as `increment`'s argument.
- State that needs to be durable and consistent across nodes must go through `Storage(...)`.
  Plain attributes on `self` only live in memory: whenever the contract is reloaded — for
  example when a new partner joins — the class is re-instantiated from scratch using just the
  original constructor arguments, and any state kept only as `self.xxx` is lost and rebuilt from
  `__init__`. Only what you write to `Storage(...)` is guaranteed to survive and stay consistent
  across partners.
- `Storage('state')['counter']` is fetched once in `__init__` and kept as `self._counter` so the
  other methods can reuse it — it's just a handle to the underlying storage, cheap to hold in
  memory. The leading underscore matters: it's what keeps `self._counter` out of the contract's
  publicly readable members (see [above](#the-contract-file)), since it's an internal handle,
  not data meant to be read directly by callers.

### The constructor runs more than once

`__init__` is **not** a one-time setup step — it runs every time the contract is reloaded (e.g.
whenever a new partner joins), using the same original constructor arguments each time. Never
assume it runs exactly once. Anything that should only happen on the *first* run — like seeding
initial values into storage — must be guarded by checking whether that data already exists, as
`Counter` does above with `if not self._counter['owner']`. Without that guard, every reload would
silently reset `value` back to `start`, wiping out everything `increment` had done since.
