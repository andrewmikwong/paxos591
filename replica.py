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

log_lock=Lock()
view_lock=Lock()
leader_lock=Lock()
accepted_lock=Lock()
view=0
p=-1
i_am_leader=False
accepted_vals=[]
accepted_ps=[]
#bit mask for accepted slots
accepted=[]
learn_requests=[]
tail=-1

channels=[]
stubs=[]
log=[]

_ONE_DAY_IN_SECONDS=60*60*24

def print_log():
	print 'Replica %d\'s LOG:'%uid
	for m in log:
		if m !=None:
			print m

class Chatter(paxos_pb2_grpc.ChatterServicer):
	def SendChatMessage(self, request, context):
		global tail
		global log
		slot=-1
		#don't need view lock here
		while(view%n==uid):
			with log_lock:
				tail+=1
				slot=tail
				log.append(None)
			if not i_am_leader:
				broadcast_prepare()
			if not i_am_leader:
				return paxos_pb2.ChatReply(mesg='IGNORED:I AM NO LONGER LEADER')
	
			val=int(request.mesg)
			if len(accepted)>slot:
				if accepted[slot]:
					val=accepted_vals[slot]

			accepted_as_leader=broadcast_accept(val,slot)
			if accepted_as_leader!=None:
				start_time=datetime.now()
				while (datetime.now()-start_time).total_seconds()<2:
					if log[slot]==int(request.mesg):
						return paxos_pb2.ChatReply(mesg='ack: %s placed in slot %d'%(request.mesg,slot))
					elif log[slot]!=None:
						continue
				return paxos_pb2.ChatReply(mesg='Learned some other value')
			else:
				return paxos_pb2.ChatReply(mesg='Ignored: I was not accepted: am no longer leader!')
		return paxos_pb2.ChatReply(mesg='IGNORED')

class Paxos(paxos_pb2_grpc.PaxosServicer):
	def Prepare(self, request, context):
		global view
		#should this be a LEQ?? multiple proposals??
		with view_lock:
			if request.proposal<view:
				return paxos_pb2.PromiseReply(ignored=view)
			else:
				#NEED A LOCK here!!!!!
				#all view writes need locks!!
				view=max(request.proposal,view)
				return paxos_pb2.PromiseReply(highest_proposals=accepted_ps,highest_values=accepted_vals, accepted=accepted)

	def Accept(self, request, context):
		global view
		global accepted_vals
		global accepted_ps
		global accepted
		with view_lock:
			if request.n<view:
				return paxos_pb2.AcceptReply(view=view)
			view=max(view, request.n)

			with accepted_lock:
				diff_len=max(len(accepted),request.slot+1)-min(len(accepted),request.slot+1)
				for i in range(diff_len):
					accepted.append(0)
					accepted_ps.append(None)
					accepted_vals.append(None)
				accepted_vals[request.slot]=request.val
				accepted_ps[request.slot]=view
				accepted[request.slot]=1
			print str(uid)+' Accepting leader %d:'%request.n, request.val
			t=threading.Thread(target=broadcast_learn, args=(request.val,view, request.slot))
			t.start()
			return paxos_pb2.AcceptReply(view=view)

	def Learn(self, request, context):
		global view
		global learn_requests
		global log
		with log_lock:
			#extend log
			diff_len=max(len(log),request.slot+1)-min(len(log),request.slot+1)
			for i in range(diff_len):
				log.append(None)
			if log[request.slot]!=None:
				#already learned
				return paxos_pb2.LearnReply(ack=1)

			#extend learn requests
			
			diff_len=max(len(learn_requests),request.slot+1)-min(len(learn_requests),request.slot+1)
			for i in range(diff_len):
				learn_requests.append([(None,None)]*n)
			
			if learn_requests[request.slot][request.rid][0]<=request.n:
				print "%d has request %d"%(uid,request.rid)
				learn_requests[request.slot][request.rid]=(request.n, request.val)
				c=Counter(learn_requests[request.slot])
				maj=c.most_common()[0]
				if maj[0][1]!=None and maj[1]>f:
					
					log[request.slot]=maj[0][1]
					print "%d HAS LEARNED %d!!"%(uid,request.val)
					print_log()
		with view_lock:
			view=max(view, request.n)
		return paxos_pb2.LearnReply(ack=1)

#returns highest value(what will be written to log) if successfully get majority of promises, None otherwise. Repeatedly attempts to do so until view is changed. 
#returns true if i am now leader, false otherwise
def broadcast_prepare():
	global view
	global accepted_ps
	global accepted_vals
	global accepted
	global i_am_leader
	received=0

	view_lock.acquire()
	while view%n==uid:
		future_to_uid= {stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=view)):i for i in range(n) }
		view_lock.release()
		start_time=datetime.now()
		while received<f+1 and (datetime.now()-start_time).total_seconds<1:
			for future in future_to_uid.keys():
				if(future.done()):
					res=future.result()

					#i am no longer leader
					if res.ignored:
						with leader_lock:
							i_am_leader=False
						with view_lock:
							view=max(view,res.ignored)
						return False

					received+=1
					rid=future_to_uid[future]
					del future_to_uid[future] 

					accepted_lock.acquire()

					#merge with my own accepts
					m=min(len(accepted), len(res.accepted))
					temp_ps=[None]*m
					temp_vals=[None]*m
					temp_accepts=[None]*m
					for i in range(m):
						temp_accepts[i]=res.accepted[i] or accepted[i]
						if res.accepted[i]:
							if res.highest_proposals[i]>=accepted_ps[i]:
								temp_ps[i]=res.highest_proposals[i]
								temp_vals[i]=res.highest_values[i]
							else:
								temp_ps[i]=accepted_ps[i]
								temp_vals[i]=accepted_vals[i]
					if len(accepted)>len(res.accepted):
						accepted_ps=temp_ps+accepted_ps[m:]
						accepted_vals=temp_vals+accepted_vals[m:]
						accepted=temp_accepts+accepted[m:]
					elif len(res.accepted)>len(accepted):
						accepted_ps=temp_ps+res.highest_proposals[m:]
						accepted_vals=temp_vals+res.highest_values[m:]
						accepted=temp_accepts+res.accepted[m:]
					else:
						accepted_ps=temp_ps
						accepted_vals=temp_vals
						accepted=temp_accepts
					accepted_lock.release()
		with leader_lock:
			i_am_leader=True
		return True
	with leader_lock:
		i_am_leader=False
	return False

#now that we have majority, we can just keep broadcasting accept until either we lose leadership or the value is learned.
#returns None if we lose leadership before learning log value
def broadcast_accept(value, slot):
	global view
	global i_am_leader
	received=[False]*n
	recv_num=0

	#need a lock here
	while log[slot]==None:
		print "Broadcasting Accept "+str(uid)
		view_lock.acquire()
		cur_view=view
		if view%n==uid:
			#if I return before futures fire off, they just die
			future_to_uid= {stubs[i].Accept.future(paxos_pb2.AcceptSend(n=view,val=value, slot=slot)):i for i in range(n) if received[i]==False}
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
							with leader_lock():
								i_am_leader=False
							with view_lock:
								view=max(res.view, view)
							return None
						received[rid]=True
						recv_num+=1
						if recv_num==f+1:
							return True
		else:
			view_lock.release()
			with leader_lock():
				i_am_leader=False
			return None
	#if we get here the value has been learned or majority has accepted
	return True

#broadcasts learn requests from proposer p_num for value value
def broadcast_learn(value, p_num, slot):
	global view
	received=[False]*n
	recv_num=0

	outer_time=datetime.now()
	while (datetime.now()-outer_time).total_seconds()<5:
		view_lock.acquire()
		#if I return before futures fire off, they just die
		future_to_uid= {stubs[i].Learn.future(paxos_pb2.LearnSend(n=p_num,val=value, rid=uid, slot=slot)):i for i in range(n) if received[i]==False}
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
#	global learn_requests

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
#	learn_requests=[(None,None)]*n

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
