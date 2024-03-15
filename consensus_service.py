from redis import Redis
import json
import logging
from threading import Thread
import os

from consensus.consensus_navigator import ConsensusNavigator

mongo_port = 27017
redis_port = 6379

class AgentThread(Thread):

    def __init__(self, identity):
        self.identity = identity
        self.navigators : dict[str, ConsensusNavigator] = {}
        super().__init__()

    def close(self):
        for navigator in self.navigators.values():
            navigator.close()
    def run(self):
        try:
            logger.info('%s ~ %-20s ~ %s', '----------', 'start thread', self.identity)
            while True:
                payload = db.blmpop(60, 1, 'consensus:'+self.identity, direction='RIGHT', count=100)
                if not payload:
                    break
                message_list = payload[1]
                for message in message_list:
                    record = json.loads(message)
                    contract = record['contract']
                    if contract not in self.navigators:
                        self.navigators[contract] = ConsensusNavigator(self.identity, contract, redis_port, mongo_port)
                    self.navigators[contract].handle_record(record)
            logger.info('%s ~ %-20s ~ %s', '----------', 'exit thread', self.identity)
            self.close()
        except Exception as e:
            logger.exception('Unhandled exception caught %s', self.identity)


def main_loop():
    agents = {}
    logger.info('%s ~ %-20s', '----------', 'start process')
    while True:
        message = db.brpop(['consensus'])[1]
        agent, record = json.loads(message)
        db.lpush('consensus:'+agent, json.dumps(record))
        if agent not in agents or not agents[agent].is_alive():
            logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'wake up', agent)
            agents[agent] = AgentThread(agent)
            agents[agent].start()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s.%(msecs)03d ~ consensus  ~ %(name)-10s ~ %(levelname)-8s ~ %(message)s',
                        filename='consensus.log',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d ~ %H:%M:%S')
    logger = logging.getLogger('Main')
    db = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
    main_loop()