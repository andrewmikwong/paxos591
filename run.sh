#!/bin/bash
#runs paxos in script mode:
#starts up replicas and then clients in batch mode

for i in `seq 0 4`;
do
	./replica.py -i $i & 
done
read var1
killall python
