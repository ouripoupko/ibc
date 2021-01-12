import sys
from flask import Flask, request, Response, send_from_directory
from state import State
from blockchain import BlockChain
from network import Network

# Create the application instance
app = Flask(__name__)
state = State()
chain = BlockChain()
network = None


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
#  get contract    - receive its state? not sure yet
#  put contract    - create a new contract with the given code
#  post contract   - interact with a contract by executing a method
#  delete contract - mark it terminated (history cannot be deleted)
@app.route('/contract/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def contract_handler():
    if request.method == 'GET':
        print(request.get_json())
        return "hello world"
    params = request.get_json()
    if request.method == 'PUT':
        chain.log('CREATE', params)
        return state.add(params['name'], params['code'], network)
    elif request.method == 'POST':
        if not params.get('from'):
            print(params)
            chain.log('TRIGGER', params)
        else:
            chain.log('INPUT', params)
        return state.call(params['msg'])


# Create a URL route in our application for partners
#  put partner  - create a partnership by joining a contract
#  post partner - interact with a partner to reach consensus
@app.route('/partner/', methods=['GET', 'POST', 'PUT', 'DELETE'])
def partner_handler():
    params = request.get_json()
    if request.method == 'PUT':
        contract = state.get(params['contract'])
        network.add_partner(params['address'], params['id'], contract)
        if params.get('from'):
            return chain.getHistory(contract)
    return {'partners': str(network.partners)}


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    me = sys.argv[1]
    network = Network(me)
    app.run(debug=True, port=me, threaded=False)
