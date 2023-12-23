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
        channel, record = db.brpop(['consensus', 'consensus_direct', 'consensus_release'])
        channel = channel.decode("utf-8")
        record = json.loads(record)
        agent = record['agent']
        if agent not in queues:
            queues[agent] = (Queue(), Queue())
        if channel == 'consensus_release':
            queues[agent][1].put(record)
        else:
            queues[agent][0].put((record, channel == 'consensus_direct'))
        if agent not in navigators or not navigators[agent].is_alive():
            navigators[agent] = ConsensusNavigator(agent, queues[agent], redis_port, None)
            navigators[agent].start()
