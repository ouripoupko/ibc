import sys
from flask import Flask, request, Response, send_from_directory
from state import State
from blockchain import BlockChain

# Create the application instance
app = Flask(__name__)


class IBC:
    def __init__(self, pid):
        self.state = State()
        self.chain = BlockChain()
        self.me = pid

    def handle_contract(self, record):
        params = record['params']
        if record['type'] == 'GET':
            return self.chain.get(params['contract'])
        elif record['type'] == 'PUT':
            self.chain.log(record)
            return self.state.add(params['contract'], params['msg'])
        elif record['type'] == 'POST':
            self.chain.log(record)
            return self.state.call(params['msg'])

    def handle_partner(self, record):
        params = record['params']
        if record['type'] == 'PUT':
            if not params.get('from'):
                self.state.join(ibc, params['contract'], params['msg'])
            else:
                contract = self.state.get(params['contract'])
                contract.add_partner(params['msg'])
        return {'reply': 'hello world'}


ibc = None


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path,
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['GET'])
def view():  # pragma: no cover
    f = open('ui.html', 'r')
    content = f.read()
    f.close()
    return Response(content, mimetype="text/html")


# Create a URL route in our application for contracts
#  get contract    - receive the contract's transaction history
#  put contract    - create a new contract with the given code
#  post contract   - interact with a contract by executing a method
#  delete contract - mark it terminated (history cannot be deleted)
@app.route('/contract/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def contract_handler():
    params = request.get_json()
    record = {'type': request.method, 'params': params}
    return ibc.handle_contract(record)


# Create a URL route in our application for partners
#  put partner  - create a partnership by joining a contract
#  post partner - interact with a partner to reach consensus
@app.route('/partner/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def partner_handler():
    params = request.get_json()
    record = {'type': request.method, 'params': params}
    return ibc.handle_partner(record)


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    me = sys.argv[1]
    ibc = IBC(me)
    app.run(debug=True, port=me, threaded=False)
