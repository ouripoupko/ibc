import sys
import os
import time
from threading import Lock
import logging

from flask import Flask, request, send_from_directory, render_template, jsonify, Response
from flask_cors import CORS
from state import State
from partner import Partner
from blockchain import BlockChain
from firebase_storage import StorageBridge, Storage

# Create the application instance
app = Flask(__name__, static_folder='ibc')
CORS(app)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class IBC:
    def __init__(self, my_address):
        self.my_address = my_address
        self.storage_bridge = StorageBridge()
        self.storage_bridge.connect()
        self.agents = Storage(self.storage_bridge.db, self.storage_bridge.ibc)
        self.locks = {}
        self.waiting_room = {}
        self.state = {}
        self.chain = {}
        for agent in self.agents:
            self.locks[agent] = Lock()
            self.state[agent] = State(agent, self.storage_bridge)
            ledger = self.storage_bridge.get_collection(agent, 'ledger')
            self.chain[agent] = BlockChain(ledger)

    def commit(self, record, identity, internal):
        record_type = record['type']
        contract_name = record['contract']
        method = record['method']
        message = record['message']
        reply = {}
        self.chain[identity].log(record)
        contract = self.state[identity].get(contract_name)
        if record_type == 'POST':
            reply = self.state[identity].welcome(contract_name, message['msg'])
        elif record_type == 'PUT':
            print('commit call ' + identity)
            reply = contract.call(record['caller'], method, message)
        return reply

    def enter_waiting_room(self, code, agent):
        print('starting consensus protocol')
        room = self.waiting_room.get(agent)
        if room is None:
            self.waiting_room[agent] = {}
            room = self.waiting_room.get(agent)
        if room.get(code) is not None:
            print('oops. I did not expect this')
        room[code] = Lock()
        room[code].acquire()
        self.locks[agent].release()
        room[code].acquire()
        self.locks[agent].acquire()
        room[code].release()
        room.pop(code)

    def handle_record(self, record, identity, internal, direct=False):
        record_type = record['type']
        contract_name = record['contract']
        method = record['method']
        message = record['message']
        reply = {}
        if identity in self.agents:
            if not direct:
                self.locks[identity].acquire()
            if contract_name:
                if method:
                    if record_type == 'PUT':
                        # a client is calling a method
                        contract = self.state[identity].get(contract_name)
                        if not contract:
                            return {'reply': 'contract not found'}
                        if not direct:
                            done, hash_code = contract.consent(record, True)
                            if not done:
                                self.enter_waiting_room(hash_code, identity)
                        reply = self.commit(record, identity, internal)
                    elif record_type == 'POST':
                        # a client calls an off chain method
                        contract = self.state[identity].get(contract_name)
                        if not contract:
                            return {'reply': 'contract not found'}
                        reply = contract.call_off_chain(record['caller'], method, message)
                else:
                    if record_type == 'GET':
                        if internal:
                            # a partner asks for a ledger history
                            reply = {'reply': 'Why do you want me ledger history?'}
                        else:
                            # a client asks for a contract state
                            reply = self.state[identity].get_state(contract_name)
                    elif record_type == 'PUT':
                        contract = self.state[identity].get(contract_name)
                        if not contract:
                            return {'reply': 'contract not found'}
                        if internal:
                            # a partner is reporting consensus protocol
                            done, hash_code = contract.consent(record, False)
                            if done:
                                original_record = contract.get_consent_result(record)
                                room = self.waiting_room.get(identity)
                                lock = room.get(hash_code) if room else None
                                if lock:
                                    lock.release()
                                else:
                                    self.commit(original_record, identity, internal)
                            reply = {'reply': 'consensus protocol'}
                    elif record_type == 'POST':
                        if message.get('code'):
                            # a client deploys a contract
                            self.chain[identity].log(record)
                            reply = self.state[identity].add(contract_name, message)
                        elif internal or direct:
                            # a partner requests to join
                            contract = self.state[identity].get(contract_name)
                            if not contract:
                                return {'reply': 'contract not found'}
                            if not direct:
                                done, hash_code = contract.consent(record, True)
                                if not done:
                                    self.enter_waiting_room(hash_code, identity)
                            self.commit(record, identity, internal)
                            if not direct:
                                reply = self.chain[identity].get(contract_name)
                        else:  # this is the initiator of the join request
                            # a client requests a join
                            partner = Partner(message['address'], message['pid'], identity)
                            records = partner.connect(contract_name, self.my_address)
                            for record in records:
                                self.handle_record(record, identity, False, direct=True)
                            reply = {'reply': 'joined a contract'}
            else:
                # a client asks for a list of contracts
                reply = [{'name': name} for name in self.state[identity].get_contracts()]
            if not direct:
                self.locks[identity].release()
        elif identity:
            if record_type == "POST":
                # a client adds an identity
                self.agents[identity] = {'public_key': ''}
                self.locks[identity] = Lock()
                self.state[identity] = State(identity, self.storage_bridge)
                self.chain[identity] = BlockChain(self.storage_bridge.get_collection(identity, 'ledger'))
                reply = [agent for agent in self.agents]
        else:
            # a client asks for a list of identities
            if record_type == 'GET':
                reply = [agent for agent in self.agents]
        return reply


ibc = IBC(os.getenv('MY_ADDRESS'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path,
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['GET'])
def view():  # pragma: no cover
    return render_template('index.html')
#    f = open('ui.html', 'r')
#    f = open('ibc-client/index.html', 'r')
#    content = f.read()
#    f.close()
#    return Response(content, mimetype="text/html")


# Create a URL route in our application for contracts
@app.route('/ibc/app', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'identity': '', 'contract': '', 'method': ''})
@app.route('/ibc/app/<identity>', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'contract': '', 'method': ''})
@app.route('/ibc/app/<identity>/<contract>', methods=['GET', 'POST', 'PUT', 'DELETE'],  #, 'OPTIONS'],
           defaults={'method': ''})
@app.route('/ibc/app/<identity>/<contract>/<method>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def ibc_handler(identity, contract, method):
    msg = request.get_json()
    internal = request.args.get('type') == 'internal'

    record = {'type': request.method,
              'contract': contract,
              'method': method,
              'message': msg}
    if not internal:
        record['caller'] = identity
    response = jsonify(ibc.handle_record(record, identity, internal))
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/stream/<identity_name>/<contract_name>')
def stream(identity_name, contract_name):

    def event_stream():
        identity = ibc.state.get(identity_name)
        if identity:
            contract = identity.get(contract_name)
            if contract:
                ibc.state[identity_name].listen(contract_name)
                print("working")
                while True:
                    # wait for source data to be available, then push it
                    with contract:
                        contract.wait()
                    yield 'data: {}\n\n'.format('True')

    return Response(event_stream(), mimetype="text/event-stream")


class LoggingMiddleware(object):
    def __init__(self, the_app):
        self._app = the_app

    def __call__(self, env, resp):
        print('REQUEST', env)

        def log_response(status, headers, *args):
            print('RESPONSE', status, headers)
            return resp(status, headers, *args)

        return self._app(env, log_response)


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    port = sys.argv[1]
#    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    app.run(port=port, debug=True, use_reloader=False)  #, threaded=False)
