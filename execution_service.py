from redis import Redis
import logging
import os
import json

from execution.execution_navigator import ExecutionNavigator

mongo_port = 27017
redis_port = 6379

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s.%(msecs)03d ~ execution  ~ %(name)-10s ~ %(levelname)-8s ~ %(message)s',
                        filename='execution.log',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d ~ %H:%M:%S')
    logger = logging.getLogger('Main')
    db = Redis(host=os.getenv('REDIS_GATEWAY'), port=redis_port, db=0)
    navigators = {}
    logger.info('%s ~ %-20s', '----------', 'start process')
    while True:
        message = db.brpop(['execution'])[1]
        agent, record = json.loads(message)
        logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'send to agent', agent)
        db.lpush('execution:'+agent, json.dumps(record))
        if agent not in navigators or not navigators[agent].is_alive():
            logger.info('%s ~ %-20s ~ %s', record['hash_code'][0:10], 'wake up', agent)
            navigators[agent] = ExecutionNavigator(agent, mongo_port, redis_port)
            navigators[agent].start()
