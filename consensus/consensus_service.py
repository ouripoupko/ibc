from redis import Redis
import json
from queue import Queue
import logging
import sys
from threading import Thread
from queue import Empty

from consensus_navigator import ConsensusNavigator

redis_port = 6379

class AgentThread(Thread):

    def __init__(self, identity, queue, a_logger):
        self.identity = identity
        self.logger = a_logger
        self.queue = queue
        self.navigators = {}
        super().__init__()

    def close(self):
        for navigator in self.navigators.values():
            navigator.close()
    def run(self):
        while True:
            try:
                a_record = self.queue.get(timeout=60)
                self.logger.debug('%s: take record from queue: %s', self.identity, a_record['action'])
                contract = a_record['contract']
                if contract not in self.navigators:
                    self.navigators[contract] = ConsensusNavigator(self.identity, contract, redis_port, logger)
                self.navigators[contract].handle_record(a_record)
            except Empty:
                break
        self.close()


if __name__ == '__main__':
    logger = logging.getLogger('ibc2')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    db = Redis(host='localhost', port=redis_port, db=0)
    queues = {}
    agents = {}
    while True:
        agent, record = json.loads(db.brpop(['consensus'])[1])
        logger.debug('%s: take record from redis: %s', agent, record['action'])
        if agent not in queues:
            queues[agent] = Queue()
        queues[agent].put(record)
        if agent not in agents or not agents[agent].is_alive():
            agents[agent] = AgentThread(agent, queues[agent], logger)
            agents[agent].start()
