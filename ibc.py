import sys
import os
import time
from threading import Condition, Thread
import logging

from flask import Flask, request, send_from_directory, render_template, jsonify, Response
from flask_cors import CORS
from flask_sse import sse
from state import State
from partner import Partner
from blockchain import BlockChain
from firebase_storage import StorageBridge, Storage

# Create the application instance
app = Flask(__name__, static_folder='ibc')
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix='/stream')
CORS(app)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(logging.DEBUG)
logger = app.logger

start = None


class IBC:
    def __init__(self, identity):
        self.my_address = os.getenv('MY_ADDRESS')
        self.storage_bridge = StorageBridge(logger)
        self.storage_bridge.connect()
        self.agents = self.storage_bridge.get_collection()
        self.identity = identity
        self.state = State(self.identity, self.storage_bridge) if self.identity in self.agents else None
        self.ledger = BlockChain(self.storage_bridge, self.identity) if self.state else None

    def commit(self, command, record, *args, **kwargs):
        index = self.ledger.log(record)
        last = self.agents[self.identity].get('last_executed', 0)
        if last < index-1:
            condition = Condition()
            listener = self.storage_bridge.listen(self.agents, self.identity, condition)
            while last < index-1:
                with condition:
                    condition.wait(1)
                last = self.agents[self.identity].get('last_executed', 0)
            self.storage_bridge.stop_listen(listener)
        reply = command(*args, **kwargs)
        self.agents.update(self.identity, {'last_executed': index})
        return reply

    @staticmethod
    def handle_partner(pid, record):
        IBC(pid).handle_record(record, False, True)

    def handle_record(self, record, internal, direct=False):
        global start
#        print('handle_record ' + str((time.time()-start)*1000))
        record_type = record['type']
        contract_name = record['contract']
        method = record['method']
        message = record['message']
        reply = {}
        if self.state:
            if contract_name:
                if method:
                    if record_type == 'PUT':
                        # a client is calling a method
                        contract = self.state.get(contract_name)
                        if not contract:
                            return {'reply': 'contract not found'}
                        if not direct:
                            for pid in contract.consent(record, True):
                                Thread(target=IBC.handle_partner, args=(pid, record)).start()
#                            if not contract.consent(record, True):
#                                return {'reply': 'consensus protocol failed'}
                        reply = self.commit(contract.call, record, record['caller'], method, message)
                        sse.publish('True', type='message', channel=self.identity+contract_name)
                    elif record_type == 'POST':
                        # a client calls an off chain method
                        contract = self.state.get(contract_name)
                        if not contract:
                            return {'reply': 'contract not found'}
                        reply = contract.call(record['caller'], method, message)
                else:
                    if record_type == 'GET':
                        if internal:
                            # a partner asks for a ledger history
                            reply = {'reply': 'Why do you want me ledger history?'}
                        else:
                            # a client asks for a contract state
                            reply = self.state.get_state(contract_name)
                    elif record_type == 'PUT':
                        contract = self.state.get(contract_name)
                        if not contract:
                            return {'reply': 'contract not found'}
                        if internal:
                            # a partner is reporting consensus protocol
                            if contract.consent(record, False):
                                original_record = record['message']['msg']['data']
                                self.handle_record(original_record, False, direct=True)
                            reply = {'reply': 'consensus protocol'}
                    elif record_type == 'POST':
                        if message.get('code'):
                            # a client deploys a contract
                            reply = self.commit(self.state.add, record, contract_name, message)
                        elif internal or direct:
                            # a partner requests to join
                            contract = self.state.get(contract_name)
                            if not contract:
                                return {'reply': 'contract not found'}
                            if not direct:
                                for pid in contract.consent(record, True):
                                    Thread(target=IBC.handle_partner, args=(pid, record)).start()
#                                if not contract.consent(record, True):
#                                    return {'reply': 'consensus protocol failed'}
                            self.commit(self.state.welcome, record, contract_name, message['msg'])
                            if not direct:
                                reply = self.ledger.get(contract_name)
                        else:  # this is the initiator of the join request
                            # a client requests a join
                            partner = Partner(message['address'], message['pid'], self.identity)
                            records = partner.connect(contract_name, self.my_address)
                            for record in records:
                                self.handle_record(record, False, direct=True)
                            reply = {'reply': 'joined a contract'}
            else:
                # a client asks for a list of contracts
                reply = [{'name': name} for name in self.state.get_contracts()]
        elif self.identity:
            if record_type == "POST":
                # a client adds an identity
                self.agents[self.identity] = {'public_key': ''}
                reply = [agent for agent in self.agents]
        else:
            # a client asks for a list of identities
            if record_type == 'GET':
                reply = [agent for agent in self.agents]
        return reply


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path,
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['GET'])
@app.route('/ibc/', methods=['GET'])
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
@app.route('/ibc/app/<identity>/<contract>', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'method': ''})
@app.route('/ibc/app/<identity>/<contract>/<method>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def ibc_handler(identity, contract, method):
    global start
    start = time.time()
    msg = request.get_json()
    internal = request.args.get('type') == 'internal'

    record = {'type': request.method,
              'contract': contract,
              'method': method,
              'message': msg}
    logger.debug(record)
    if not internal:
        record['caller'] = identity
    response = jsonify(IBC(identity).handle_record(record, internal))
    response.headers.add('Access-Control-Allow-Origin', '*')
#    print('before return ' + str((time.time() - start) * 1000))
    logger.debug(response.get_json())
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
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.DEBUG)
    port = sys.argv[1]
#    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    print(port)
    app.run(host='0.0.0.0', port=port, use_reloader=False)  #, threaded=False)
