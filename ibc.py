import sys
from flask import Flask, request, send_from_directory, render_template, jsonify
from state import State
from blockchain import BlockChain

# Create the application instance
app = Flask(__name__, static_folder='ibc')


class IBC:
    def __init__(self, my_address):
        self.my_address = my_address
        self.agents = []
        self.state = {}
        self.chain = {}
        for agent in self.agents:
            self.state[agent] = State()
            self.chain[agent] = BlockChain()

    def commit(self, record, identity, internal):
        record_type = record['type']
        contract_name = record['contract']
        message = record['message']
        reply = {}
        self.chain[identity].log(record)
        contract = self.state[identity].get(contract_name)
        if internal and record_type == 'POST':
            reply = self.state[identity].join(ibc, identity, contract_name, message['msg'], None)
        elif record_type == 'PUT':
            reply = contract.call(message)
        return reply

    def handle_record(self, record, identity, internal, direct=False):
        record_type = record['type']
        contract_name = record['contract']
        message = record['message']
        reply = {}
        if identity in self.agents:
            if record_type == 'GET':
                if contract_name:
                    if internal:
                        reply = self.chain[identity].get(contract_name)
                    else:
                        reply = self.state[identity].get_state(contract_name)
                else:
                    reply = [{'name': name} for name in self.state[identity].get_contracts()]
            elif record_type == 'POST' and contract_name:
                if message.get('code'):
                    self.chain[identity].log(record)
                    reply = self.state[identity].add(identity, contract_name, message)
                elif internal or direct:
                    contract = self.state[identity].get(contract_name)
                    if direct or contract.consent(record, True):
                        reply = self.commit(record, identity, internal)
                    else:
                        reply = {'reply': 'starting consensus protocol'}
                else:  # this is the initiator of the join request
                    reply = self.state[identity].join(ibc, identity, contract_name, message, self.my_address)

            elif record_type == 'PUT':
                contract = self.state[identity].get(contract_name)
                if internal:
                    if direct or contract.consent(record, False):
                        original_record = contract.get_consent_result(record)
                        reply = self.commit(original_record, identity, internal)
                else:
                    if direct or contract.consent(record, True):
                        reply = self.commit(record, identity, internal)
                    else:
                        reply = {'reply': 'starting consensus protocol'}

        elif identity:
            if record_type == "POST":
                self.agents.append(identity)
                self.state[identity] = State()
                self.chain[identity] = BlockChain()
                reply = self.agents
        else:
            if record_type == 'GET':
                reply = self.agents
        return reply


ibc = None


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
@app.route('/ibc/app/<identity>/<contract>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
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
    response = jsonify(ibc.handle_record(record, identity, internal))
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


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
    app.run(debug=True, port=port)  #, threaded=False)
