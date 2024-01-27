from redis import Redis
import json
import logging
from threading import Thread

from consensus_navigator import ConsensusNavigator

from my_timer import Timers

redis_port = 6379
timer = Timers()

class AgentThread(Thread):

    def __init__(self, identity, a_logger):
        self.identity = identity
        self.logger = a_logger
        self.navigators : dict[str, ConsensusNavigator] = {}
        super().__init__()

    def close(self):
        for navigator in self.navigators.values():
            navigator.close()
    def run(self):
        count = 0
        loops = 0
        self.logger.info('starting')
        while True:
            payload = db.blmpop(20, 1, 'consensus:'+self.identity, direction='RIGHT', count=100)
            timer.start(self.identity + '_all')
            self.logger.info('c get %s', self.identity)
            if not payload:
                break
            message_list = payload[1]
            loops += 1
            count += len(message_list)
            for message in message_list:
                a_record = json.loads(message)
                self.logger.debug('%s: take record from queue: %s', self.identity, a_record['action'])
                contract = a_record['contract']
                if contract not in self.navigators:
                    self.navigators[contract] = ConsensusNavigator(self.identity, contract, redis_port, logger, timer)
                self.navigators[contract].handle_record(a_record)
            self.logger.warning('c out %s', self.identity)
            timer.stop(self.identity + '_all')
        self.logger.info('stopping')
        if self.identity == 'agent_00000':
            timer.report()

        print(count, loops)
        self.close()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger('ibc2')
    logger.setLevel(logging.ERROR)
#    logger.addHandler(logging.StreamHandler(sys.stdout))
    db = Redis(host='localhost', port=redis_port, db=0)
    agents = {}
    while True:
        agent = db.brpop(['consensus'])[1].decode()
        logger.debug('%s: take agent from redis: %s', agent)
        if agent not in agents or not agents[agent].is_alive():
            agents[agent] = AgentThread(agent, logger)
            agents[agent].start()
