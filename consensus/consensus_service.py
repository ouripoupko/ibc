from redis import Redis
import json
from queue import Queue

from consensus_navigator import ConsensusNavigator

redis_port = 6379

if __name__ == '__main__':
    db = Redis(host='localhost', port=redis_port, db=0)
    queues = {}
    navigators = {}
    while True:
        agent, record = json.loads(db.brpop(['consensus'])[1])
        print(agent, record)
        if agent not in queues:
            queues[agent] = Queue()
        queues[agent].put(record)
        if agent not in navigators or not navigators[agent].is_alive():
            navigators[agent] = ConsensusNavigator(agent, queues[agent], redis_port, None)
            navigators[agent].start()
