from redis import Redis
import logging
import os

from execution_navigator import ExecutionNavigator

mongo_port = 27017
redis_port = 6379

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(name)-10s %(levelname)-8s %(message)s',
                        filename='execution.log',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger('Main')
    db = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
    navigators = {}
    while True:
        agent = db.brpop(['execution'])[1].decode()
        if agent not in navigators or not navigators[agent].is_alive():
            navigators[agent] = ExecutionNavigator(agent, mongo_port, redis_port)
            navigators[agent].start()
