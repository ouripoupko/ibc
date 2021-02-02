import sys
from flask import Flask, request, send_from_directory, render_template, jsonify
from state import State
from blockchain import BlockChain

# Create the application instance
app = Flask(__name__, static_folder='ibc')


class IBC:
    def __init__(self, pid):
        self.state = State()
        self.chain = BlockChain()
        self.me = pid

    def commit(self, record):
        self.chain.log(record)
        params = record['params']
        contract = self.state.get(record['path'])
        reply = {'reply': 'hello world'}
        if record['owner'] == 'partner' and record['type'] == 'POST':
            reply = self.state.join(ibc, params['contract'], params['msg'], None)
        elif record['owner'] == 'contract' and record['type'] == 'PUT':
            reply = contract.call(params)
        return reply

    def handle_contract(self, record):
        params = record['params']
        path = record['path']
        print(params)
        print(path)
        if record['type'] == 'GET':
            if path:
                return self.state.get_state(path)
            else:
                reply = jsonify([{'name': name} for name in self.state.get_contracts()])
                print(reply.get_json())
                return reply
        elif record['type'] == 'POST':
            self.chain.log(record)
            return self.state.add(params['name'], params['code'])
        elif record['type'] == 'PUT':
            contract = self.state.get(path)
            if contract.consent(record, True):
                return self.commit(record)
            else:
                return {'reply': 'starting consensus protocol'}

    def handle_partner(self, record, my_address):
        params = record['params']
        reply = {'reply': 'hello world'}
        if record['type'] == 'GET':
            reply = self.chain.get(params['contract'])
        elif record['type'] == 'PUT':
            if not params.get('from'):  # this is the initiator of the join request
                reply = self.state.join(ibc, params['contract'], params['msg'], my_address)
            else:
                contract = self.state.get(params['contract'])
                if contract.consent(record, True):
                    return self.commit(record)
                else:
                    return {'reply': 'starting consensus protocol'}
        elif record['type'] == 'POST':
            contract = self.state.get(params['contract'])
            if contract.consent(record, False):
                original_record = contract.get_consent_result(record)
                reply = self.commit(original_record)

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
#  get contract    - receive the contract's state
#  put contract    - create a new contract with the given code
#  post contract   - interact with a contract by executing a method
#  delete contract - mark it terminated (history cannot be deleted)
@app.route('/ibc/contract', methods=['GET', 'POST', 'PUT', 'DELETE'], defaults={'path': ''})
@app.route('/ibc/contract/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def contract_handler(path):
    params = request.get_json()

    record = {'owner': 'contract', 'type': request.method, 'params': params, 'path': path}
    return ibc.handle_contract(record)


# Create a URL route in our application for partners
#  get contract    - receive the contract's transaction history
#  put partner  - create a partnership by joining a contract
#  post partner - interact with a partner to reach consensus
@app.route('/partner', methods=['GET', 'POST', 'PUT', 'DELETE'])
def partner_handler():
    params = request.get_json()
    record = {'owner': 'partner', 'type': request.method, 'params': params}
    return ibc.handle_partner(record, request.url_root)


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    me = sys.argv[1]
    ibc = IBC(me)
    app.run(debug=True, port=me, threaded=False)
