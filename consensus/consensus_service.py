from redis import Redis
import json
import os

from contract_dialog import ContractDialog

redis_port = 6379

if __name__ == '__main__':
    db = Redis(host='localhost', port=redis_port, db=2)
    while True:
        message = json.loads(db.brpop(['communicators'])[1])
        ContractDialog(message['identity'], os.getenv('MY_ADDRESS'),
                       message['contract'], message['protocol'], redis_port).start()
