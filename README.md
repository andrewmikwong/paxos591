# paxos591
paxos project for eecs591

 ./run.sh will start up the replicas. Clients can connect to them with the command:

	./client  -c0

where -c specifies the client's id.

To kill a replica, simply enter any key into the terminal from which you started run.sh.

To modify the config file, modify create_config.py, and then exectue it; this simply creates a json file.
