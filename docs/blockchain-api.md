# Talking to the Blockchain from a Frontend App

This document describes the HTTP API a client application uses to talk to a node of this
blockchain: registering an identity, deploying and joining contracts, calling contract methods,
and listening for results over a live event stream.

It assumes you already know how contracts expose *members* and *methods* — see
[contract-api.md](contract-api.md) for that side of things. This document is about the wire
protocol a browser or mobile app uses to reach them.

## Core concepts

- **Identity.** Every request acts as some *agent* — an arbitrary string id your app chooses
  (e.g. a generated UUID, or a username). There's no signup flow: an identity simply starts
  existing the first time you register it against a node.
- **Node address.** A node is just an HTTP base URL (e.g. `https://node.example.com`). Your app
  talks to one node at a time; that node relays consensus messages to the other partners' nodes
  on your behalf.
- **Contract id.** Deploying a contract returns an id (a hash string). Every later call
  targeting that contract — reading it, writing to it, other agents joining it — uses this id.
- **One request endpoint, many actions.** Every request (except the event stream) goes to the
  same URL family, `/ibc/app/...`, and is disambiguated by an `action` query parameter combined
  with the HTTP verb. The response body is always the bare JSON result — never wrapped in an
  envelope like `{ "data": ... }`.
- **Reads are synchronous, writes are not.** A read call gets its answer directly in the HTTP
  response. A write call (or a deploy, or a join) only returns an acknowledgement id — the real
  outcome shows up shortly after on the event stream. Your app needs to be connected to that
  stream *before* it needs the result.
- **Errors aren't signaled by HTTP status.** A response is essentially always `200 OK`, even
  when something went wrong — an unknown contract id, a method that raised, a bad method name.
  These come back as ordinary JSON values (e.g. `{ "message": "no such contract" }`, or a string
  describing the exception in place of the expected result) rather than a distinct HTTP error
  status. Check the shape/content of the result itself, not just the HTTP status code.
- **No built-in authentication.** Anyone who knows an identity string and its node address can
  send requests as that identity — there's no password, signature, or token. Treat identity
  strings the way you'd treat any other bit of client-held state, and don't rely on this API
  alone to keep one user's actions safe from another.

## Request shape

```
<VERB> /ibc/app/<identity>/<contractId>/<methodName>?action=<action>
Content-Type: application/json

<JSON body, if any>
```

`<contractId>` and `<methodName>` are only needed for actions that target a specific contract or
method — omit trailing segments you don't need (e.g. `/ibc/app/<identity>?action=register_agent`).

| Verb | `action` | Path | Body | Result |
|---|---|---|---|---|
| PUT | `register_agent` | `/ibc/app/<identity>` | `{ "address": "<this app's own callback URL>" }` | ack id (see [The event stream](#the-event-stream)) |
| PUT | `deploy_contract` | `/ibc/app/<identity>` | contract definition (below) | ack id **and** the new contract's id |
| PUT | `join_contract` | `/ibc/app/<identity>` | `{ "contract", "address", "agent", "profile" }` | ack id, or `null` if already joined |
| GET | `is_exist_agent` | `/ibc/app/<identity>` | — | `true` / `false` |
| GET | `get_contracts` | `/ibc/app/<identity>` | — | array of contract summaries |
| GET | `get_contract` | `/ibc/app/<identity>/<contractId>` | — | one contract summary |
| POST | `contract_read` | `/ibc/app/<identity>/<contractId>/<methodName>` | `{ "values": {...} }` | the method's return value, **directly** |
| POST | `contract_write` | `/ibc/app/<identity>/<contractId>/<methodName>` | `{ "values": {...} }` | ack id only — real result arrives via the event stream |

A small JS helper used by every example below:

```js
async function ibc(baseUrl, verb, identity, action, { contractId = '', method = '', body } = {}) {
  const path = [identity, contractId, method].filter(Boolean).join('/');
  const res = await fetch(`${baseUrl}/ibc/app/${path}?action=${action}`, {
    method: verb,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}
```

## Registering an identity

Before doing anything else, an identity must register the address of the node it will be
reached at for incoming (agent-to-agent) traffic — normally the same node it's talking to.

```js
await ibc(baseUrl, 'PUT', myId, 'register_agent', {
  body: { address: baseUrl },
});
```

Since registering the same identity twice is unnecessary, you can check first whether it's
already registered on this node — useful when an app reuses a persisted identity across
sessions rather than generating a fresh one each time:

```js
const registered = await ibc(baseUrl, 'GET', myId, 'is_exist_agent');
// true / false — call register_agent only if this comes back false
```

## Deploying a contract

```js
const contractId = await ibc(baseUrl, 'PUT', myId, 'deploy_contract', {
  body: {
    name: 'my-counter',        // human-readable label, your choice
    contract: 'counter.py',    // a label for the contract "type" / source file, your choice
    code: contractSourceCode,  // the contract's Python source, see contract-api.md
    constructor: { start: 0 }, // arguments passed to the contract's constructor
    protocol: 'BFT',
    default_app: 'https://my-app.example.com', // where other partners should be sent to interact with it
    pid: myId,
    address: baseUrl,
    profile: '',
  },
});
// contractId is this new contract's permanent id, used in every call below
```

The PUT response is only an *acknowledgement id* — while it happens to equal the new contract's
id, deployment itself completes asynchronously (see [The event stream](#the-event-stream)) and
you should wait for the corresponding `deploy_contract` event before assuming the contract is
live and callable.

## Joining a contract someone else deployed

A second agent joins by pointing at the node and identity of a partner already on the contract
(typically the deployer):

```js
await ibc(baseUrl, 'PUT', myId, 'join_contract', {
  body: {
    contract: contractId,           // the contract id shared with you out-of-band
    address: ownerBaseUrl,          // the existing partner's node URL
    agent: ownerId,                 // the existing partner's identity
    profile: '',
  },
});
```

## Listing and inspecting contracts

```js
const contracts = await ibc(baseUrl, 'GET', myId, 'get_contracts');
// [{ id, name, contract, code, protocol, default_app, pid, address, profile }, ...]

const one = await ibc(baseUrl, 'GET', myId, 'get_contract', { contractId });
// same shape as a single entry above, or {} if not found
```

## Calling a contract method

Use `contract_read` for a method whose result you need right away and that doesn't need to be
agreed on by every partner (e.g. a getter). Use `contract_write` for anything that changes
contract state — it goes through consensus with the other partners, so its result isn't ready
by the time the HTTP call returns.

```js
// Read — result comes back directly.
const value = await ibc(baseUrl, 'POST', myId, 'contract_read', {
  contractId, method: 'get_value',
  body: { values: {} },
});

// Write — this only confirms the request was accepted; see the event stream for the outcome.
const requestId = await ibc(baseUrl, 'POST', myId, 'contract_write', {
  contractId, method: 'increment',
  body: { values: { amount: 1 } },
});
```

`values` must have one key per argument the target method declares (see
[contract-api.md](contract-api.md#the-contract-file) for how a contract's methods and their
arguments are defined).

### Governance parameters

Alongside `values`, a call may also include a `parameters` object to submit this agent's vote for
one or more governance parameter values:

```js
await ibc(baseUrl, 'POST', myId, 'contract_write', {
  contractId, method: 'increment',
  body: { values: { amount: 1 }, parameters: { fee: 10 } },
});
```

### Built-in methods

Every contract answers these without you having to define them yourself, using the same
`contract_read` / `contract_write` calling convention with `values: {}`:

| Method | Returns |
|---|---|
| `get_partners` | The contract's connected partners (address, profile, agent id). |
| `get_parameters` | This caller's submitted governance parameter values plus the current consensus values. |

## The event stream

Because `deploy_contract`, `join_contract`, and `contract_write` only hand back an
acknowledgement, your app needs a live channel to learn what actually happened. That's what
`/stream` is for — a standard [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
endpoint.

```
GET /stream?agent=<identity1>&contract=<contractId1|''>&agent=<identity2>&contract=<contractId2|''>...
```

- `agent` and `contract` are repeated query parameters, paired up by position: the *n*-th
  `agent` value is scoped to the *n*-th `contract` value.
- Pass an empty string for a given `contract` to subscribe to **all** events for that identity
  (across every contract it's involved in). Pass an actual contract id to scope that
  subscription to just that one contract.
- You can mix identities and scopes freely in one connection — e.g. subscribe broadly to your
  own identity while narrowly watching one specific contract for a different identity.

```js
const params = new URLSearchParams();
params.append('agent', myId);
params.append('contract', ''); // '' = everything for myId

const events = new EventSource(`${baseUrl}/stream?${params}`);

events.onmessage = (evt) => {
  if (!evt.data) return; // periodic empty keep-alive pings — safe to ignore
  const update = JSON.parse(evt.data);
  console.log(update);
  // { request: "<ack id from the original PUT/POST>",
  //   contract: "<contract id, or null>",
  //   action: "deploy_contract" | "contract_write" | "register_agent" | "a2a_connect" | "a2a_reply_join",
  //   reply: <the actual result — a method's return value for contract_write, a boolean for the others>,
  //   agent: "<which of your subscribed identities this event belongs to>" }
};
```

Match `update.request` against the ack id you got back from the original `fetch()` call to know
which pending action this event resolves:

```js
function waitForResult(events, requestId) {
  return new Promise((resolve) => {
    const handler = (evt) => {
      if (!evt.data) return;
      const update = JSON.parse(evt.data);
      if (update.request === requestId) {
        events.removeEventListener('message', handler);
        resolve(update.reply);
      }
    };
    events.addEventListener('message', handler);
  });
}

const requestId = await ibc(baseUrl, 'POST', myId, 'contract_write', {
  contractId, method: 'increment', body: { values: { amount: 1 } },
});
const result = await waitForResult(events, requestId);
```

Keep a single `EventSource` connection open for the lifetime of your session rather than
reconnecting per request — reconnecting per call defeats the purpose and can cause you to miss
events that fire in between.

## Putting it together

```js
const baseUrl = 'https://node.example.com';
const myId = crypto.randomUUID();

await ibc(baseUrl, 'PUT', myId, 'register_agent', { body: { address: baseUrl } });

const events = new EventSource(
  `${baseUrl}/stream?agent=${myId}&contract=`
);

const deployAck = await ibc(baseUrl, 'PUT', myId, 'deploy_contract', {
  body: {
    name: 'my-counter', contract: 'counter.py', code: contractSourceCode,
    constructor: { start: 0 }, protocol: 'BFT',
    default_app: 'https://my-app.example.com',
    pid: myId, address: baseUrl, profile: '',
  },
});
const contractId = deployAck; // deploy's ack id doubles as the new contract's id
await waitForResult(events, deployAck); // wait for deployment to actually finish before using it

const requestId = await ibc(baseUrl, 'POST', myId, 'contract_write', {
  contractId, method: 'increment', body: { values: { amount: 1 } },
});

const result = await waitForResult(events, requestId);
console.log('new counter value:', result);
```
