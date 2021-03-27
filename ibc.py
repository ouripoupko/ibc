import sys
import time
from flask import Flask, request, send_from_directory, render_template, jsonify, Response
from flask_cors import CORS
from state import State
from blockchain import BlockChain
from storage import StorageBridge

# Create the application instance
app = Flask(__name__, static_folder='ibc')
CORS(app)


class IBC:
    def __init__(self, my_address):
        self.my_address = my_address
        self.storage_bridge = StorageBridge()
        self.storage_bridge.connect()
        self.agents = self.storage_bridge.get_collection('ibc', 'agents')
        self.state = {}
        self.chain = {}
        for agent in self.agents:
            self.state[agent['name']] = State(agent['name'], self.storage_bridge)
            ledger = self.storage_bridge.get_collection(agent['name'], agent['name']+'_ledger')
            self.chain[agent['name']] = BlockChain(ledger)

    def commit(self, record, identity, internal):
        record_type = record['type']
        contract_name = record['contract']
        method = record['method']
        message = record['message']
        reply = {}
        self.chain[identity].log(record)
        contract = self.state[identity].get(contract_name)
        if internal and record_type == 'POST':
            reply = self.state[identity].join(ibc, identity, contract_name, message['msg'], None)
        elif record_type == 'PUT':
            reply = contract.call(record['caller'], method, message)
        return reply

    def handle_record(self, record, identity, internal, direct=False):
        record_type = record['type']
        contract_name = record['contract']
        method = record['method']
        message = record['message']
        reply = {}
        if {'name': identity} in self.agents:
            if contract_name:
                if method:
                    if record_type == 'PUT':
                        # a client is calling a method
                        contract = self.state[identity].get(contract_name)
                        if direct or contract.consent(record, True):
                            reply = self.commit(record, identity, internal)
                        else:
                            reply = {'reply': 'starting consensus protocol'}
                    elif record_type == 'POST':
                        # a client calls an off chain method
                        contract = self.state[identity].get(contract_name)
                        reply = contract.call_off_chain(record['caller'], method, message)
                else:
                    if record_type == 'GET':
                        if internal:
                            # a partner asks for a ledger history
                            reply = self.chain[identity].get(contract_name)
                        else:
                            # a client asks for a contract state
                            reply = self.state[identity].get_state(contract_name)
                    elif record_type == 'PUT':
                        contract = self.state[identity].get(contract_name)
                        if internal:
                            # a partner is calling a method
                            if direct or contract.consent(record, False):
                                original_record = contract.get_consent_result(record)
                                reply = self.commit(original_record, identity, internal)
                    elif record_type == 'POST':
                        if message.get('code'):
                            # a client deploys a contract
                            self.chain[identity].log(record)
                            reply = self.state[identity].add(identity, contract_name, message)
                        elif internal or direct:
                            # a partner requests to join
                            contract = self.state[identity].get(contract_name)
                            if direct or contract.consent(record, True):
                                reply = self.commit(record, identity, internal)
                            else:
                                reply = {'reply': 'starting consensus protocol'}
                        else:  # this is the initiator of the join request
                            # a client requests a join
                            reply = self.state[identity].join(ibc, identity, contract_name, message,
                                                              self.my_address)
            else:
                # a client asks for a list of contracts
                reply = [{'name': name} for name in self.state[identity].get_contracts()]
        elif identity:
            if record_type == "POST":
                # a client adds an identity
                self.agents.append({'name': identity})
                self.state[identity] = State(identity, self.storage_bridge)
                self.chain[identity] = BlockChain(self.storage_bridge.get_collection(identity, identity+'_ledger'))
                reply = [agent['name'] for agent in self.agents]
        else:
            # a client asks for a list of identities
            if record_type == 'GET':
                reply = [agent['name'] for agent in self.agents]
        return reply


ibc = IBC('https://dashboard.heroku.com/')


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
    if request.method == 'OPTIONS':
        response = jsonify()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'PUT')
        response.headers.add('Access-Control-Allow-Headers', 'content-type')
        return response
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
                yield 'data: \n\n'
                while True:
                    print("working")
                    # wait for source data to be available, then push it
                    with contract:
                        contract.wait()
                    yield 'data: \n\n'
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
    address = sys.argv[1]
    port = sys.argv[2]
    ibc = IBC(address)
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    app.run(port=port, debug=True, use_reloader=False)  #, threaded=False)
