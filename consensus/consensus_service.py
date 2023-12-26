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
        channel, payload = db.brpop(['consensus', 'consensus_direct', 'consensus_release'])
        channel = channel.decode("utf-8")
        agent, record = json.loads(payload)
        print(channel.ljust(17), agent, record)
        if agent not in queues:
            queues[agent] = Queue()
        queues[agent].put((record, channel == 'consensus_direct', channel == 'consensus_release'))
        if agent not in navigators or not navigators[agent].is_alive():
            navigators[agent] = ConsensusNavigator(agent, queues[agent], redis_port, None)
            navigators[agent].start()
