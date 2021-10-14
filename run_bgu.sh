#!/bin/bash
if [ $# -eq 0 ]
  then
    echo "you forgot the port base number, dummy"
    exit 1
fi

HOST="talmonlab.bgu.ac.il"
PORT=$1
export MY_ADDRESS="http://${HOST}:1${PORT}/"
mkdir -p ${HOME}/var/${PORT}/lib/mongo
mkdir -p ${HOME}/var/${PORT}/log/mongodb
mkdir -p ${HOME}/var/${PORT}/log/ibc
cd ~/ibc
redis-server --port 3$PORT --daemonize yes
mongod --dbpath ${HOME}/var/${PORT}/lib/mongo --logpath ${HOME}/var/${PORT}/log/mongodb/mongod.log --port 2$PORT --fork
source ${HOME}/ibc/.venv/bin/activate
python ibc.py 1$PORT 2$PORT 3$PORT /home/poupko/var/${PORT}/log/ibc/ibc.log &
touch ${HOME}/var/instances/${HOST}:1${PORT}
while [ $(ls ${HOME}/var/instances/ | grep ${HOST}:1${PORT} | wc -l) -gt 0 ]
do
  sleep 10
done
ps -ef | grep "ibc.py 1${PORT}" | grep -v grep | awk '{print $2}' | xargs kill
redis-cli -p 3$PORT flushall
redis-cli -p 3$PORT shutdown
mongod --dbpath ${HOME}/var/${PORT}/lib/mongo --logpath ${HOME}/var/${PORT}/log/mongodb/mongod.log --port 2$PORT --shutdown
rm -r -f ${HOME}/var/${PORT}

