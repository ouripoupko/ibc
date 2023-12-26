from redis import Redis
import json
from queue import Queue

from execution_navigator import ExecutionNavigator

mongo_port = 27017
redis_port = 6379

if __name__ == '__main__':
    logger = None
    db = Redis(host='localhost', port=redis_port, db=0)
    navigators = {}
    queues = {}
    while True:
        agent, record = json.loads(db.brpop(['execution'])[1])
        print(agent, record['action'])
        if agent not in queues:
            queues[agent] = Queue()
        queues[agent].put(record)
        if agent not in navigators or not navigators[agent].is_alive():
            if agent in navigators:
                raise Exception('I need to check if need to call delete')
            navigators[agent] = ExecutionNavigator(agent, queues[agent], mongo_port, redis_port, None)
            navigators[agent].start()
