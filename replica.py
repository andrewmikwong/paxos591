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
learn_lock=Lock()
view=0
lead=1
p=-1
i_am_leader=False
accepted_vals=[]
accepted_ps=[]
#bit mask for accepted slots
accepted=[]
learn_requests=[]
tail=-1
skip=None

channels=[]
stubs=[]
log=[]

_ONE_DAY_IN_SECONDS=60*60*24

#returns true if primary is alive
def heart_beat(rep):
	try:
		fut=stubs[rep%n].HeartBeat.future(paxos_pb2.Empty())
		start_time=datetime.now()
		while (datetime.now()-start_time).total_seconds()<0.5:
			if fut.done():
				try:
					if fut.result().ack==1:
						return True
				except:
					break
	except:
		return False
	return False

def view_switch():
	global view
	global lead
	with view_lock:
		#if uid==((view+lead)%n):
		while view%n!=uid:
			view+=1
		lead=1
		print "%d is LEADER!"%(uid)

	broadcast_prepare()
		#else:
		#	lead+=1

def print_log():
	print 'Replica %d\'s LOG:'%uid
	for m in log:
		if m !=None:
			print m

class Chatter(paxos_pb2_grpc.ChatterServicer):
	def SendChatMessage(self, request, context):
		s='Client %d: '%(request.rid)+ request.mesg
		global tail
		global log
		slot=-1
		#don't need view lock here
 
		with log_lock:
			tail=len(log)
			if tail ==skip:
				tail=tail+1
			slot=tail
			log.append(None)
		print '%d is handling:'%(uid) +s

		while(view%n==uid):
			if not i_am_leader:
				broadcast_prepare()
			if not i_am_leader:
				return paxos_pb2.ChatReply(mesg='IGNORED:I AM NO LONGER LEADER', success=0)
	
			val=s
			with accepted_lock:
				if len(accepted)>slot:
					if accepted[slot]:
						val=accepted_vals[slot]

			accepted_as_leader=broadcast_accept(val,slot)
			if accepted_as_leader!=None:
				start_time=datetime.now()
				while (datetime.now()-start_time).total_seconds()<2:
					with log_lock:
						if log[slot]==s:
							return paxos_pb2.ChatReply(mesg='ack: %s placed in slot %d'%(request.mesg,slot), success=1)
						elif log[slot]!=None:
							#some other value is in this slot, try next one
							tail=len(log)
							if skip==tail:
								tail=tail+1
							slot=tail
							log.append(None)
							break
				print "Trying again same slot!!"
			else:
				return paxos_pb2.ChatReply(mesg='Ignored: I was not accepted: am no longer leader!', success=0)
		return paxos_pb2.ChatReply(mesg='IGNORED', success=0)

	def GetData(self, request, context):
		h=hash(str(log))%(2**30)
		return paxos_pb2.DataReply(view=view,hash=h)

class Paxos(paxos_pb2_grpc.PaxosServicer):
	def Prepare(self, request, context):
		global lead
		global view
		#should this be a LEQ?? multiple proposals??
		with view_lock and accepted_lock:
			if request.proposal<view:
				return paxos_pb2.PromiseReply(ignored=1,view=view)
			else:
				#NEED A LOCK here!!!!!
				#all view writes need locks!!
				lead=1
				view=max(request.proposal,view)
				print "%d: %d is my leader!"%(uid, view)
				return paxos_pb2.PromiseReply(highest_proposals=accepted_ps,highest_values=accepted_vals, accepted=accepted,ignored=0)

	def Accept(self, request, context):
		global view
		global accepted_vals
		global accepted_ps
		global accepted
		global lead
		lead=1
		with view_lock:
			if request.n<view:
				return paxos_pb2.AcceptReply(view=view)
			view=max(view, request.n)

			with accepted_lock:
				diff_len=max(len(accepted),request.slot+1)-min(len(accepted),request.slot+1)
				for i in range(diff_len):
					accepted.append(0)
					accepted_ps.append(0)
					accepted_vals.append("")
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
			with learn_lock:
				diff_len=max(len(learn_requests),request.slot+1)-min(len(learn_requests),request.slot+1)
				for i in range(diff_len):
					learn_requests.append([(None,None)]*n)
				
				if learn_requests[request.slot][request.rid][0]<request.n:
					print "%d has request %d"%(uid,request.rid)
					learn_requests[request.slot][request.rid]=(request.n, request.val)
					c=Counter(learn_requests[request.slot])
					maj=c.most_common()[0]
					if maj[0][1]!=None and maj[1]>f:
						
						log[request.slot]=maj[0][1]
						print "%d HAS LEARNED %s!!"%(uid,request.val)
						#print_log()
		with view_lock:
			view=max(view, request.n)
		return paxos_pb2.LearnReply(ack=1)
		
	def HeartBeat(self, request, context):
		return paxos_pb2.HBReply(ack=1)

#returns highest value(what will be written to log) if successfully get majority of promises, None otherwise. Repeatedly attempts to do so until view is changed. 
#returns true if i am now leader, false otherwise
def broadcast_prepare():
	global view
	global accepted_ps
	global accepted_vals
	global accepted
	global i_am_leader
	received=[False]*n
	recv_num=0

	while True:
		view_lock.acquire()
		if view%n!=uid:
			break

		future_to_uid={}
                for i in range(n):
			if received[i]==False:
				try:
					future_to_uid[stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=view))]=i
				except:
					pass

		#no chance of getting quorum
		if len(future_to_uid)<f+1:
			continue
	#	future_to_uid= {stubs[i].Prepare.future(paxos_pb2.PrepareSend(proposal=view)):i for i in range(n) }
		view_lock.release()
		start_time=datetime.now()
		while recv_num<f+1 and (datetime.now()-start_time).total_seconds()<1:
			for future in future_to_uid.keys():
				if(future.done()):
					rid=future_to_uid[future]
					del future_to_uid[future] 
					try:
						res=future.result()

					#i am no longer leader
						if res.ignored:
							with leader_lock:
								i_am_leader=False
							with view_lock:
								view=max(view,res.view)
							return False
						received[i]=True
						recv_num+=1
					except:
						continue

					accepted_lock.acquire()

					#merge with my own accepts
					m=min(len(accepted), len(res.accepted))
					temp_ps=[0]*m
					temp_vals=[""]*m
					temp_accepts=[0]*m
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
		if recv_num>f:
			with leader_lock:
				i_am_leader=True
			return True
		else:
			 continue
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
			future_to_uid={}
                	for i in range(n):
				if received[i]==False:
					try:
						future_to_uid[stubs[i].Accept.future(paxos_pb2.AcceptSend(n=view,val=value,slot=slot))]=i
					except:
						pass

			#future_to_uid= {stubs[i].Accept.future(paxos_pb2.AcceptSend(n=view,val=value, slot=slot)):i for i in range(n) if received[i]==False}
			view_lock.release()
			start_time=datetime.now()
			while (datetime.now()-start_time).total_seconds()<1:
				for future in future_to_uid.keys():
					if(future.done()):
						try:
							res=future.result()
							recv_num+=1
							#no risk of data race here
							if res.view>cur_view:
								with leader_lock:
									i_am_leader=False
								with view_lock:
									view=max(res.view, view)
								return None
						except:
							pass

						rid=future_to_uid[future]
						del future_to_uid[future]
						received[rid]=True
						if recv_num==f+1:
							return True
		else:
			view_lock.release()
			with leader_lock:
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

		future_to_uid={}
		for i in range(n):
			if received[i]==False:
				try:
					future_to_uid[stubs[i].Learn.future(paxos_pb2.LearnSend(n=p_num,val=value, rid=uid, slot=slot))]=i
				except:
					pass
#		future_to_uid= {stubs[i].Learn.future(paxos_pb2.LearnSend(n=p_num,val=value, rid=uid, slot=slot)):i for i in range(n) if received[i]==False}
		view_lock.release()
		start_time=datetime.now()
		while (datetime.now()-start_time).total_seconds()<1:
			for future in future_to_uid.keys():
				if(future.done()):
					try:
						res=future.result()
						rid=future_to_uid[future]
						if res.ack==1:
							received[rid]=True
							recv_num+=1
					except:
						pass
					del future_to_uid[future]
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
		opts, args = getopt.getopt(sys.argv[1:], "i:s:")
	except getopt.GetoptError as err:
		print str(err)  # will print something like "option -a not recognized"
		sys.exit(2)
	for o, a in opts:
		if o == "-i":
			uid=int(a)
		elif o == "-s":
			skip=int(a)
		else:
			assert False, "unhandled option"

	#start grpc server
	server=grpc.server(futures.ThreadPoolExecutor(max_workers=6000))
	paxos_pb2_grpc.add_ChatterServicer_to_server(Chatter(), server)
	paxos_pb2_grpc.add_PaxosServicer_to_server(Paxos(), server)
	server.add_insecure_port('0.0.0.0:'+str(8000+uid))
	server.start()

	#let other replicas start up
	time.sleep(1)

	#init learn_requests
#	learn_requests=[(None,None)]*n

	#initialize grpc channels and stubs with other replicas
	channels=[None]*n
	stubs=[None]*n
	for i in range(n):
		channels[i]=grpc.insecure_channel('0.0.0.0:'+str(8000+i))
		stubs[i]=paxos_pb2_grpc.PaxosStub(channels[i])

	global lead
	#heartbeats
	while True:
		try:
			leader_alive=False
			for i in range(5):
				life=heart_beat(view)#+lead-1)
				if life:
					leader_alive=True
				else:
					print "%d thinks "%(view)+str(view)+": dead: "+str(i)
			if not leader_alive:
				view_switch()
		except KeyboardInterrupt:
			server.stop(0)


if __name__=='__main__':
	main()
