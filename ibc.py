import sys
import os
import logging
import random

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from redis import Redis

from navigator import Navigator

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


# Create a URL route in our application for contracts
@app.route('/ibc/app', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'identity': '', 'contract': '', 'method': ''})
@app.route('/ibc/app/<identity>', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'contract': '', 'method': ''})
@app.route('/ibc/app/<identity>/<contract>', methods=['GET', 'POST', 'PUT', 'DELETE'],
           defaults={'method': ''})
@app.route('/ibc/app/<identity>/<contract>/<method>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def ibc_handler(identity, contract, method):
    logger.info('i get %s', identity)
    msg = request.get_json() if request.is_json else None
    action = request.args.get('action')
    record = {'type': request.method,
              'action': action,
              'contract': contract,
              'method': method,
              'message': msg,
              'agent': identity}
    log_id = str(random.random())[2:8]
    logger.info('record ' + log_id+ ': ' + str(record))
    navigator = Navigator(identity, mongo_port, redis_port, logger)
    response = jsonify(navigator.handle_record(record))
    response.headers.add('Access-Control-Allow-Origin', '*')
    logger.info('response ' + log_id+ ': ' + str(response.get_json()))
    logger.info('i out %s', identity)
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
                        logger.info('found a match ' + contracts[index][0:4] + ' ' + modified_contract[0:4])
                        yield f'data: {{"agent": "{identity}", "contract": "{modified_contract}"}}\n\n'
            else:
                yield "data: \n\n"

    return Response(event_stream(), mimetype="text/event-stream")


class LoggingMiddleware(object):
    def __init__(self, the_app):
        self._app = the_app

    def __call__(self, env, resp):
        logger.debug('REQUEST ')

        def log_response(status, headers, *args):
            logger.debug('RESPONSE '+str(status)+' '+str(headers))
            return resp(status, headers, *args)

        return self._app(env, log_response)


# If we're running in stand-alone mode, run the application
if __name__ == '__main__':
    port = int(sys.argv[1])
    if len(sys.argv) > 3:
        mongo_port = sys.argv[2]
        redis_port = sys.argv[3]
    conf_kwargs = {'format': '%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
                   'datefmt': '%Y-%m-%d %H:%M:%S'}
    if len(sys.argv) > 4:
        conf_kwargs['filename'] = sys.argv[4]
    logging.basicConfig(**conf_kwargs)

    # logger = logging.getLogger('werkzeug')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logger = logging.getLogger('ibc')
    logger.setLevel(logging.ERROR)
    # app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    app.run(host='0.0.0.0', port=port, use_reloader=False)  # , threaded=False)
