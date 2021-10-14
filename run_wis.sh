#!/bin/tcsh
#$ -S /bin/tcsh
setenv PATH ${PATH}:${HOME}"/data/mongodb/bin":${HOME}"/data/redis/bin"
setenv MY_ADDRESS "http://"${HOST}":$SGE_TASK_ID/"
mkdir -p /mnt/ramdisk/poupko/$SGE_TASK_ID/lib/mongo
mkdir -p /mnt/ramdisk/poupko/$SGE_TASK_ID/log/mongodb
mkdir -p /mnt/ramdisk/poupko/$SGE_TASK_ID/log/ibc
cd ~/data/ibc
redis-server --port 3$SGE_TASK_ID --daemonize yes
mongod --dbpath /mnt/ramdisk/poupko/$SGE_TASK_ID/lib/mongo --logpath /mnt/ramdisk/poupko/$SGE_TASK_ID/log/mongodb/mongod.log --port 2$SGE_TASK_ID --fork
source /home/poupko/data/ibc/.venv/bin/activate.csh
python ibc.py $SGE_TASK_ID 2$SGE_TASK_ID 3$SGE_TASK_ID &
touch /home/poupko/data/var/${HOST}:$SGE_TASK_ID
while ( `ls /home/poupko/data/var/ | grep ${HOST}:$SGE_TASK_ID | wc -l` > 0 )
  sleep 10
end
ps -ef | grep ibc.py | grep -v grep | awk '{print $2}' | xargs kill
redis-cli -p 3$SGE_TASK_ID shutdown
mongod --dbpath /mnt/ramdisk/poupko/$SGE_TASK_ID/lib/mongo --logpath /mnt/ramdisk/poupko/$SGE_TASK_ID/log/mongodb/mongod.log --port 2$SGE_TASK_ID --shutdown
rm -r -f /mnt/ramdisk/poupko/$SGE_TASK_ID

