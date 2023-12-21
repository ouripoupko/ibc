from redis import Redis
import json

from execution_navigator import ExecutionNavigator

mongo_port = 27017
redis_port = 6379

if __name__ == '__main__':
    logger = None
    db = Redis(host='localhost', port=redis_port, db=3)
    navigator = {}
    while True:
        message = db.brpop(['executioners'])[1]
        print('message', message)
        agent = json.loads(message)
        print('agent', agent)
        if agent not in navigator:
            navigator[agent] = ExecutionNavigator(agent, mongo_port, redis_port, logger)
            navigator[agent].start()
