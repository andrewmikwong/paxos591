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

view=0
p=-1
accepted_val=None
accepted_p=None

channels=[]
stubs=[]

_ONE_DAY_IN_SECONDS=60*60*24

def print_state():
	print 'uid=%d'%uid
	print 'f=%d'%f
	print 'n=%d'%n

class Chatter(paxos_pb2_grpc.ChatterServicer):
	def SendChatMessage(self, request, context):
		if(view%n==uid):
			val= broadcast_prepare(request.mesg)
			if val==None:
				print "faild"
				return paxos_pb2.ChatReply(mesg='IGNORED')
			print val
			broadcast_accept(val)
			return paxos_pb2.ChatReply(mesg='ack: %s'%request.mesg)
		else:
			return paxos_pb2.ChatReply(mesg='IGNORED')

class Paxos(paxos_pb2_grpc.PaxosServicer):
	def Prepare(self, request, context):
		global view
		if request.proposal<view:
			return paxos_pb2.PromiseReply(ignored=1)
		else:
			#NEED A LOCK here!!!!!
			#all view writes need locks!!
			view=max(request.proposal,view)
			if accepted_val==None:
				accepted=0
			else:
				accepted=1
			return paxos_pb2.PromiseReply(highest_proposal=accepted_p,highest_value=accepted_val, accepted=accepted)

#returns highest value(what will be writtein to log) if successfully get majority of promises, None otherwise. Repeatedly attempts to do so until view is changed. 
def broadcast_prepare(value):
	received=0

	#highest proposals and values returned on promises
	hv=None
	hp=None

	while view%n==uid:
		future_to_uid= {stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=view)):i for i in range(n) if i!=uid}
		while received<f+1:
			for future in future_to_uid.keys():
				if(future.done()):
					res=future.result()

					#i am no longer leader
					if res.ignored:
						return None

					received+=1
					rid=future_to_uid[future]
					del future_to_uid[future] 
					if res.accepted:
						if res.highest_proposal>=hp:
							hp=res.highest_proposal
							hv=res.highest_value
		if hv==None:
			hv=value
		return hv
	return None

def broadcast_accept():
	received=0
	future_to_uid= {stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=view)):i for i in range(n) if i!=uid}
	while received<f+1:
		for future in future_to_uid.keys():
			if(future.done()):
				res=future.result()
				rid=future_to_uid[future]
				del future_to_uid[future]
				if res.ignored:
					continue
				received+=1
				print res.highest_proposal, res.highest_value, res.ignored, rid



def main():
	global f
	global n
	global uid
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
