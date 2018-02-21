#!/usr/bin/env python
#Andrew Kwong's PAXOS project
from concurrent import futures
import grpc
import paxos_pb2
import paxos_pb2_grpc

import sys
import time
import getopt
import json
import pdb

_ONE_DAY_IN_SECONDS=60*60*24
uid=-1
f=-1

class Chatter(paxos_pb2_grpc.ChatterServicer):
	def SendChatMessage(self, request, context):
		return paxos_pb2.ChatReply(mesg='ack: %s'%request.mesg)

def main():
	#read config file
	fd=open('config.txt',"r")
	configs=json.loads(fd.read())
        fd.close()
        f=configs['f']

	#i=uid
	try:
		opts, args = getopt.getopt(sys.argv[1:], "i:")
	except getopt.GetoptError as err:
		print str(err)  # will print something like "option -a not recognized"
		sys.exit(2)
	for o, a in opts:
		if o == "-i":
			uid=int(a)
		else:
			assert False, "unhandled option"

	#start grpc server
	server=grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	paxos_pb2_grpc.add_ChatterServicer_to_server(Chatter(), server)
	server.add_insecure_port('localhost:'+str(8000+uid))
	server.start()
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		server.stop(0)


if __name__=='__main__':
	main()
