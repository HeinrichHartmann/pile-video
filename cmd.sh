#!/bin/bash

python -u /usr/src/app/upd_schedule.py &
while true;
do
      echo "STARTING"
      python -u /usr/src/app/youtube-dl-server.py
done
