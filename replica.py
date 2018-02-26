#!/usr/bin/env python
#Andrew Kwong's PAXOS project
from concurrent import futures
import grpc
import paxos_pb2
import paxos_pb2_grpc
import threading
from threading import Lock

import sys
import time
from datetime import datetime
import getopt
import json
from collections import Counter
import pdb

uid=-1
f=-1
n=-1

view_lock=Lock()
view=0
p=-1
accepted_val=None
accepted_p=None
learn_requests=None

channels=[]
stubs=[]
log=None

_ONE_DAY_IN_SECONDS=60*60*24

def print_state():
	print 'uid=%d'%uid
	print 'f=%d'%f
	print 'n=%d'%n

class Chatter(paxos_pb2_grpc.ChatterServicer):
	def SendChatMessage(self, request, context):
		if(view%n==uid):
			val= broadcast_prepare(int(request.mesg))
			if val==None:
				return paxos_pb2.ChatReply(mesg='IGNORED:I AM NO LONGER LEADER')
			learned=broadcast_accept(val)
			if learned!=None:
				start_time=datetime.now()
				while (datetime.now()-start_time).total_seconds()<2:
					if log==int(request.mesg):
						return paxos_pb2.ChatReply(mesg='ack: %s'%request.mesg)
				print log
				return paxos_pb2.ChatReply(mesg='Learned some other value')
			else:
				return paxos_pb2.ChatReply(mesg='Ignored: I am no longer leader!')
		else:
			return paxos_pb2.ChatReply(mesg='IGNORED')

class Paxos(paxos_pb2_grpc.PaxosServicer):
	def Prepare(self, request, context):
		global view
		#should this be a LEQ?? multiple proposals??
		if request.proposal<view:
			return paxos_pb2.PromiseReply(ignored=view)
		else:
			#NEED A LOCK here!!!!!
			#all view writes need locks!!
			view=max(request.proposal,view)
			if accepted_val==None:
				accepted=0
			else:
				accepted=1
			return paxos_pb2.PromiseReply(highest_proposal=accepted_p,highest_value=accepted_val, accepted=accepted)

	def Accept(self, request, context):
		global view
		global accepted_val
		global accepted_p
		with view_lock:
			if request.n<view:
				return paxos_pb2.AcceptReply(view=view)
			view=max(view, request.n)
			accepted_val=request.val
			acceped_p=view
			print str(uid)+' Accepting leader %d:'%request.n, request.val
			t=threading.Thread(target=broadcast_learn, args=(request.val,view))
			t.start()
			return paxos_pb2.AcceptReply(view=view)

	def Learn(self, request, context):
		global view
		global learn_requests
		global log
		if log!=None:
			#already learned
			return paxos_pb2.LearnReply(ack=1)
		with view_lock:
			view=max(view, request.n)
			if learn_requests[request.rid][0]<=request.n:
				print "%d has request %d"%(uid,request.rid)
				learn_requests[request.rid]=(request.n, request.val)
				c=Counter(learn_requests)
				maj=c.most_common()[0]
				if maj[0][1]!=None and maj[1]>f:
					log=maj[0][1]
					print "%d HAS LEARNED %d!!"%(uid,request.val)
		return paxos_pb2.LearnReply(ack=1)

#returns highest value(what will be written to log) if successfully get majority of promises, None otherwise. Repeatedly attempts to do so until view is changed. 
# returns the high value
def broadcast_prepare(value):
	global view
	received=0

	#highest proposals and values returned on promises
	hv=None
	hp=None

	while view%n==uid:
		future_to_uid= {stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=view)):i for i in range(n) }
		while received<f+1:
			for future in future_to_uid.keys():
				if(future.done()):
					res=future.result()

					#i am no longer leader
					if res.ignored:
						view=max(view,res.ignored)
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

#now that we have majority, we can just keep broadcasting accept until either we lose leadership or the value is learned.
#returns None if we lose leadership before learning log value
def broadcast_accept(value):
	global view
	received=[False]*n
	recv_num=0

	#need a lock here
	while log==None:
		print "Broadcasting Accept "+str(uid)
		view_lock.acquire()
		cur_view=view
		if view%n==uid:
			#if I return before futures fire off, they just die
			future_to_uid= {stubs[i].Accept.future(paxos_pb2.AcceptSend(n=view,val=value)):i for i in range(n) if received[i]==False}
			view_lock.release()
			start_time=datetime.now()
			while (datetime.now()-start_time).total_seconds()<1:
				for future in future_to_uid.keys():
					if(future.done()):
						res=future.result()
						rid=future_to_uid[future]
						del future_to_uid[future]
						#no risk of data race here
						if res.view>cur_view:
							view=max(res.view, view)
							return None
						received[rid]=True
						recv_num+=1
						if recv_num==f+1:
							return True
		else:
			view_lock.release()
			return None
	#if we get here the value has been learned or majority has accepted
	return True

#broadcasts learn requests from proposer p_num for value value
def broadcast_learn(value, p_num):
	global view
	received=[False]*n
	recv_num=0

	outer_time=datetime.now()
	while (datetime.now()-outer_time).total_seconds()<5:
		view_lock.acquire()
		#if I return before futures fire off, they just die
		future_to_uid= {stubs[i].Learn.future(paxos_pb2.LearnSend(n=p_num,val=value, rid=uid)):i for i in range(n) if received[i]==False}
		view_lock.release()
		start_time=datetime.now()
		while (datetime.now()-start_time).total_seconds()<1:
			for future in future_to_uid.keys():
				if(future.done()):
					res=future.result()
					rid=future_to_uid[future]
					del future_to_uid[future]
					if res.ack==1:
						received[rid]=True
						recv_num+=1
					if recv_num==n:
						return 
	return 

def main():
	global f
	global n
	global uid
	global channels
	global stubs
	global learn_requests

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

	#init learn_requests
	learn_requests=[(None,None)]*n

	#initialize grpc channels and stubs with other replicas
	channels=[None]*n
	stubs=[None]*n
	for i in range(n):
		channels[i]=grpc.insecure_channel('localhost:'+str(8000+i))
		stubs[i]=paxos_pb2_grpc.PaxosStub(channels[i])

	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		server.stop(0)


if __name__=='__main__':
	main()
