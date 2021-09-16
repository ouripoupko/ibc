import sys
import os
import time
import logging

from flask import Flask, request, send_from_directory, render_template, jsonify, Response
from flask_cors import CORS
from redis import Redis
from state import State
from partner import Partner
from blockchain import BlockChain
from mongodb_storage import DBBridge

# Create the application instance
app = Flask(__name__, static_folder='ibc', instance_path=f'{os.getcwd()}/instance')
CORS(app)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(logging.ERROR)
logger = app.logger

start = None


class IBC:
    def __init__(self, identity):
        self.my_address = os.getenv('MY_ADDRESS')
        self.storage_bridge = DBBridge(logger).connect()
        self.agents = self.storage_bridge.get_root_collection()
        self.identity = identity
        identity_doc = self.agents[identity]
        self.state = State(identity_doc, logger) if identity_doc.exists() else None
        self.ledger = BlockChain(identity_doc, logger) if identity_doc.exists() else None

    def __del__(self):
        self.storage_bridge.disconnect()

    def commit(self, command, record, *args, **kwargs):
        self.ledger.log(record)
        reply = command(*args, **kwargs)
        return reply

    def handle_record(self, record, internal, direct=False):
        global start
        # print('handle_record ' + str((time.time()-start)*1000))

        db = Redis(host='localhost', port=6379, db=0)
        # mutex per identity
        if not direct:
            attempts = 0
            while not db.setnx(self.identity, 'locked'):
                time.sleep(0.01)
                attempts += 1
                if attempts > 10000:  # 100 seconds
                    return {'reply': 'timeout - could not lock mutex'}
            # print(self.identity, ' got mutex')

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
                            reply = {'reply': 'contract not found'}
                        elif not direct and not contract.consent(record, True):
                            reply = {'reply': 'consensus protocol failed'}
                        else:
                            reply = self.commit(contract.call, record, record['caller'], method, message)
                            db.publish(self.identity+contract_name, 'True')
                    elif record_type == 'POST':
                        # a client calls an off chain method
                        contract = self.state.get(contract_name)
                        if not contract:
                            reply = {'reply': 'contract not found'}
                        else:
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
                            reply = {'reply': 'contract not found'}
                        elif internal:
                            # a partner is reporting consensus protocol
                            original_records = contract.consent(record, False)
                            for original in original_records:
                                self.handle_record(original, False, direct=True)
                            reply = {'reply': 'consensus protocol'}
                    elif record_type == 'POST':
                        if message.get('code'):
                            # a client deploys a contract
                            reply = self.commit(self.state.add, record, contract_name, message)
                        elif internal or direct:
                            if 'address' in message['msg']:
                                # a partner requests to join
                                contract = self.state.get(contract_name)
                                if not contract:
                                    reply = {'reply': 'contract not found'}
                                elif not direct and \
                                        not contract.consent(record, True):
                                    reply = {'reply': 'consensus protocol failed'}
                                else:
                                    self.commit(self.state.welcome, record, contract_name, message['msg'])
                                    if not direct:
                                        reply = self.ledger.get(contract_name)
                            elif 'index' in message['msg']:
                                log = self.ledger.get(contract_name)
                                reply = log[message['msg']['index']]
                        else:  # this is the initiator of the join request
                            # a client requests a join
                            partner = Partner(message['address'], message['pid'], self.identity)
                            records = partner.connect(contract_name, self.my_address)
                            for key in sorted(records.keys()):
                                self.handle_record(records[key], False, direct=True)
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
        # print(self.identity, ' release mutex')
        if not direct:
            db.delete(self.identity)
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
    ibc = IBC(identity)
    response = jsonify(ibc.handle_record(record, internal))
    del ibc
    response.headers.add('Access-Control-Allow-Origin', '*')
    logger.debug(response.get_json())
    return response


@app.route('/stream/<identity>/<contract_name>')
def stream(identity, contract_name):

    def event_stream():
        db = Redis(host='localhost', port=6379, db=0)
        channel = db.pubsub()
        channel.subscribe(identity+contract_name)
        while True:
            message = channel.get_message(timeout=10)
            if message:
                if message.get('type') == 'message':
                    yield 'data: {}\n\n'.format('True')
            else:
                yield 'data: {}\n\n'.format('False')

    return Response(event_stream(), mimetype="text/event-stream")


class LoggingMiddleware(object):
    def __init__(self, the_app):
        self._app = the_app

    def __call__(self, env, resp):
        logger.debug('REQUEST '+env)

        def log_response(status, headers, *args):
            logger.debug('RESPONSE '+str(status)+' '+str(headers))
            return resp(status, headers, *args)

        return self._app(env, log_response)


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)
    port = sys.argv[1]
#    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    print(port)
    app.run(host='0.0.0.0', port=port, use_reloader=False)  #, threaded=False)
