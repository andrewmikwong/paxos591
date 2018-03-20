#!/bin/bash
#runs paxos in script mode:
#starts up replicas and then clients in batch mode

for i in `seq 0 2`;
do
	./bclient.py -c $i & 
done
read var1
while [ "$var1" != "quit" ]
do
	kill `pgrep -o python`
	read var1
done

killall python
