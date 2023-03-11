import sys
import os
import time
import logging

from datetime import datetime
import hashlib
import json

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
port = None
mongo_port = 27017
redis_port = 6379


class Waiter:
    pass


class IBC:
    def __init__(self, identity):
        self.storage_bridge = DBBridge(logger).connect(mongo_port)
        self.agents = self.storage_bridge.get_root_collection()
        self.identity = identity
        self.identity_doc = self.agents[identity]
        self.state = State(self.identity_doc, logger) if self.identity_doc.exists() else None
        self.ledger = BlockChain(self.identity_doc, logger) if self.identity_doc.exists() else None
        self.db = Redis(host='localhost', port=redis_port, db=0)
        self.actions = {'GET':  {'is_exist_agent': self.is_exist_agent,
                                 'get_contracts': self.get_contracts},
                        'PUT':  {'register_agent': self.register_agent,
                                 'deploy_contract': self.deploy_contract,
                                 'join_contract': self.join_contract,
                                 'a2a_connect': self.a2a_connect,
                                 'a2a_welcome': self.a2a_welcome,
                                 'a2a_consent': self.a2a_consent},
                        'POST': {'contract_read': self.contract_read,
                                 'contract_write': self.contract_write,
                                 'a2a_get_ledger': self.a2a_get_ledger}}

    def close(self):
        if self.state:
            self.state.close()
        self.storage_bridge.disconnect()

    def commit(self, command, record, *args, **kwargs):
        self.ledger.log(record)
        reply = command(*args, **kwargs)
        self.db.publish(self.identity, record['contract'])
        return reply

    def is_exist_agent(self, record, direct):
        return self.state is not None

    def register_agent(self, record, direct):
        # a client adds an identity
        self.agents[self.identity] = {'address': os.getenv('MY_ADDRESS')}
        identity_doc = self.agents[self.identity]
        self.state = State(identity_doc, logger)
        self.ledger = BlockChain(identity_doc, logger)
        return True

    def get_contracts(self, record, direct):
        # a client asks for a list of contracts
        return self.state.get_contracts()

    def deploy_contract(self, record, direct):
        # a client deploys a contract
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
            record['contract'] = record['hash_code']
        return self.commit(self.state.add, record,
                           record['message'], record['timestamp'], record['hash_code'])

    def join_contract(self, record, direct):
        message = record['message']
        record['hash_code'] = message['contract']
        partner = Partner(message['address'], message['agent'],
                          self.identity_doc['address'], self.identity, self.state.queue)
        partner.connect(message['contract'], message['profile'])
        return Waiter()

    def a2a_connect(self, record, direct):
        # a partner requests to join
        contract = self.state.get(record['contract'])
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        if not contract:
            return {'reply': 'contract not found'}
        return self.handle_consent_records(contract.consent(record, True, direct), True)

    def a2a_welcome(self, record, direct):
        # a partner notifies success on join request
        message = record['message']
        partner = Partner(message['msg']['welcome'], message['msg']['pid'],
                          self.identity_doc['address'], self.identity, self.state.queue)
        records = partner.get_ledger(record['contract'])
        for key in sorted(records.keys()):
            self.handle_record(records[key], True)
        self.db.publish(self.identity, record['contract'])
        self.db.publish(record['contract'], json.dumps({'reply': 'join success'}))
        return {}

    def contract_read(self, record, direct):
        # a client calls an off chain method
        contract = self.state.get(record['contract'])
        if not contract:
            return {'reply': 'contract not found'}
        else:
            return contract.call(record['agent'], record['method'], record['message'], None)

    def contract_write(self, record, direct):
        # a client is calling a method
        contract = self.state.get(record['contract'])
        if not direct:
            record['timestamp'] = datetime.now().strftime('%Y%m%d%H%M%S%f')
            record['hash_code'] = hashlib.sha256(str(record).encode('utf-8')).hexdigest()
        if not contract:
            return {'reply': 'contract not found'}
        return self.handle_consent_records(contract.consent(record, True, direct), True)

    def a2a_consent(self, record, direct):
        # a partner is reporting consensus protocol
        contract = self.state.get(record['contract'])
        return self.handle_consent_records(contract.consent(record, False, False), False)

    def a2a_get_ledger(self, record, direct):
        # a partner asks for a ledger history
        index = record['message']['msg']['index']
        reply = self.ledger.get(record['contract'])
        if index > 0:
            reply = reply[index]
        return reply

    def handle_consent_records(self, records, immediate):
        reply = Waiter()
        for record in records:
            action = record['action']
            contract = self.state.get(record['contract'])
            if action == 'contract_write':
                reply = self.commit(contract.call, record,
                                   record['agent'], record['method'], record['message'], record['timestamp'])
            if action == 'a2a_connect':
                message = record['message']
                reply = self.commit(self.state.join, record,
                                   record['contract'], message['msg'], message['to'] == self.identity)
            if not immediate:
                self.db.publish(record['hash_code'], json.dumps(reply))
        return reply if immediate else {}

    def handle_record(self, record, direct=False):
        # mutex per identity
        if not direct:
            attempts = 0
            while not self.db.setnx(self.identity, 'locked'):
                time.sleep(0.01)
                attempts += 1
                if attempts > 10000:  # 100 seconds
                    return {'reply': 'timeout - could not lock mutex'}

        action = self.actions[record['type']].get(record['action'])
        reply = action(record, direct)
        if not direct:
            self.db.delete(self.identity)
        if isinstance(reply, Waiter):
            channel = self.db.pubsub()
            channel.subscribe(record['hash_code'])
            while True:
                message = channel.get_message(timeout=10)
                if message:
                    if message.get('type') == 'message':
                        reply = json.loads(message.get('data'))
                        break
                else:
                    reply = {'reply': 'Waited too long for consensus'}
                    break
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


ibc = None


# Create a URL route in our application for contracts
@app.route('/ibc/app', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'identity': '', 'contract': '', 'method': ''})
@app.route('/ibc/app/<identity>', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'contract': '', 'method': ''})
@app.route('/ibc/app/<identity>/<contract>', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'method': ''})
@app.route('/ibc/app/<identity>/<contract>/<method>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def ibc_handler(identity, contract, method):
    msg = request.get_json() if request.is_json else None
    action = request.args.get('action')
    record = {'type': request.method,
              'action': action,
              'contract': contract,
              'method': method,
              'message': msg,
              'agent': identity}
    logger.info('-------------------------------------------------------')
    logger.warning(record)
    if isinstance(ibc, dict):
        if identity in ibc:
            this_ibc = ibc[identity]
        else:
            this_ibc = IBC(identity)
            ibc[identity] = this_ibc
    else:
        this_ibc = IBC(identity)
    response = jsonify(this_ibc.handle_record(record))
    if not isinstance(ibc, dict):
        this_ibc.close()
    response.headers.add('Access-Control-Allow-Origin', '*')
    logger.warning(response.get_json())
    return response


@app.route('/stream')
def stream():
    identities = request.args.getlist('agent')
    contracts = request.args.getlist('contract')
    generals = [identities[index] for index in range(len(identities)) if not contracts[index]]

    def event_stream():
        db = Redis(host='localhost', port=redis_port, db=0)
        channel = db.pubsub()
        channel.subscribe(*identities)
        while True:
            message = channel.get_message(timeout=10)
            if message:
                if message.get('type') == 'message':
                    modified_contract = message.get('data').decode()
                    identity = message.get('channel').decode()
                    index = contracts.index(modified_contract) if modified_contract in contracts else -1
                    if identity in generals or (index >= 0 and identities[index] == identity):
                        logger.warning('found a match ' + contracts[index][0:4] + ' ' + modified_contract[0:4])
                        yield f'data: {{"agent": "{identity}", "contract": "{modified_contract}"}}\n\n'
            else:
                yield "data: \n\n"

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
    port = int(sys.argv[1])
    if len(sys.argv) > 3:
        mongo_port = sys.argv[2]
        redis_port = sys.argv[3]
    conf_kwargs = {'format': '%(asctime)s %(levelname)-8s %(message)s',
                   'datefmt': '%Y-%m-%d %H:%M:%S'}
    if len(sys.argv) > 4:
        conf_kwargs['filename'] = sys.argv[4]
    logging.basicConfig(**conf_kwargs)

    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.WARNING)
#    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # turning ibc from None to empty dict triggers memory cache when using flask directly, without gunicorn
    ibc = {}
    app.run(host='0.0.0.0', port=port, use_reloader=False)  # , threaded=False)
