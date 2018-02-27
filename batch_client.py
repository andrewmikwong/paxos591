#!/usr/bin/env python
import sys
import getopt
import json
from datetime import datetime
import time

import grpc
import paxos_pb2
import paxos_pb2_grpc

stubs=[]
view=0
views=[]
n=-1
hashes=[]

def query_replicas():
	global hashes
	global view
	global views
	rview=-1
	while rview ==-1:
		future_to_uid={}
		for i in range(n):
			try:
				future_to_uid[stubs[i].GetData.future(paxos_pb2.Empty())]=i
			except:
				pass
		time.sleep(1)
		for future in future_to_uid.keys():
			if(future.done()):
				try:
					res=future.result()
					rid=future_to_uid[future]
					rview=max(rview, res.view)
					hashes[rid]= res.hash
					views[rid]=res.view
				except:
					pass
				del future_to_uid[future]
	view=rview
	return

def main():
	global n
	global view
	global stubs
	global hashes
	global views
	fd=open("config.txt","r")
	configs=json.loads(fd.read())
	fd.close()
	f=configs['f']
	n=2*f+1
	s=''
	hashes=[None]*n
	views=[None]*n

	#get options
        #i=uid
        try:
                opts, args = getopt.getopt(sys.argv[1:], "i:c:")
        except getopt.GetoptError as err:
                print str(err)  # will print something like "option -a not recognized"
                sys.exit(2)
        for o, a in opts:
                if o == "-i":
                        uid=int(a)
		elif o =="-c":
			client=int(a)
                else:
                        assert False, "unhandled option"

	
	#initialize grpc channels and stubs with other replicas
        channels=[None]*n
        stubs=[None]*n
        for i in range(n):
                channels[i]=grpc.insecure_channel('localhost:'+str(8000+i))
                stubs[i]=paxos_pb2_grpc.ChatterStub(channels[i])

#        channel=grpc.insecure_channel('localhost:'+str(8000+uid))
#	stub=paxos_pb2_grpc.ChatterStub(channel)
	seq=0
	s='0'
	while(True):
		try:
			response=stubs[view%n].SendChatMessage.future(paxos_pb2.ChatRequest(mesg=s,seq_num=seq, rid=client))
			start_time=datetime.now()
			while (datetime.now()-start_time).total_seconds()<3:
				if response.done():
					try:
						if response.result().success:
							seq+=1
							s=str(seq)
							break
						query_replicas()
						break
					except:
						query_replicas()
						break
			
		except:
			query_replicas()
		

if __name__=='__main__':
	main()
