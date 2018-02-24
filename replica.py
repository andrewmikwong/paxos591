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

uid=-1
f=-1
n=-1

proposal_num=0
p=-1
highest_val=-1

channels=[]
stubs=[]
view=0

_ONE_DAY_IN_SECONDS=60*60*24

def print_state():
	print 'uid=%d'%uid
	print 'f=%d'%f
	print 'n=%d'%n

class Chatter(paxos_pb2_grpc.ChatterServicer):
	def SendChatMessage(self, request, context):
		if(view%n==uid):
			broadcast_prepare()
			return paxos_pb2.ChatReply(mesg='ack: %s'%request.mesg)
		else:
			return paxos_pb2.ChatReply(mesg='IGNORED')

class Paxos(paxos_pb2_grpc.PaxosServicer):
	def Prepare(self, request, context):
		if request.proposal<proposal_num:
			return
		else:
			highest_seen_p=proposal_num
			if request.proposal>proposal_num:
				proposal_num=request.proposal
			return paxos_pb2.PromiseReply(highest_proposal=highest_seen_p,highest_value=highest_val)

def broadcast_prepare():
	received=0
	future_to_uid= {stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=proposal_num)):i for i in range(n) if i!=uid}
	while received<f+1:
		for future in future_to_uid.keys():
			if(future.done()):
				received+=1
				print future.result().highest_proposal, future.result().highest_value
				del future_to_uid[future]

def main():
	global f
	global n
	global uid
	global proposal_num
	global channels
	global stubs

	#read config file
	fd=open('config.txt',"r")
	configs=json.loads(fd.read())
        fd.close()
        f=configs['f']
	n=2*f+1

	#get options
	#i=uid
	try:
		opts, args = getopt.getopt(sys.argv[1:], "i:")
	except getopt.GetoptError as err:
		print str(err)  # will print something like "option -a not recognized"
		sys.exit(2)
	for o, a in opts:
		if o == "-i":
			uid=int(a)
			proposal_num=uid
		else:
			assert False, "unhandled option"

	#start grpc server
	server=grpc.server(futures.ThreadPoolExecutor(max_workers=40))
	paxos_pb2_grpc.add_ChatterServicer_to_server(Chatter(), server)
	paxos_pb2_grpc.add_PaxosServicer_to_server(Paxos(), server)
	server.add_insecure_port('localhost:'+str(8000+uid))
	server.start()

	#let other replicas start up
	time.sleep(1)

	#initialize grpc channels and stubs with other replicas
	channels=[None]*n
	stubs=[None]*n
	for i in range(n):
		if i != uid:
			channels[i]=grpc.insecure_channel('localhost:'+str(8000+i))
			stubs[i]=paxos_pb2_grpc.PaxosStub(channels[i])

	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		server.stop(0)


if __name__=='__main__':
	main()
