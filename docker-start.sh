#!/bin/bash
# Runs the three ibc processes in one container.
# If any of them exits, the others are stopped and the container exits,
# so Docker's restart policy restarts the whole node.

trap 'kill $(jobs -p) 2>/dev/null' TERM INT

python consensus_service.py &
python execution_service.py &
gunicorn -b 0.0.0.0:2611 --workers 3 --worker-class gevent --access-logfile - wsgi:app &

wait -n
status=$?
kill $(jobs -p) 2>/dev/null
wait
exit $status
