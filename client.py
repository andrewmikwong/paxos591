#!/usr/bin/env python
import sys
import getopt
import json
from datetime import datetime

import grpc
import paxos_pb2
import paxos_pb2_grpc

stubs=[]
view=0

def main():
	global view
	global stubs
	fd=open("config.txt","r")
	configs=json.loads(fd.read())
	fd.close()
	f=configs['f']
	n=2*f+1
	s=''

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
	s=raw_input()
	while(True):
		if s=='quit':
			break
		try:
			response=stubs[view].SendChatMessage.future(paxos_pb2.ChatRequest(mesg=s,seq_num=seq, rid=client))
			start_time=datetime.now()
			while (datetime.now()-start_time).total_seconds()<3:
				if response.done():
					print response.result().mesg	
					seq+=1
					s=raw_input()
					break
		except:
			view+=1
		

if __name__=='__main__':
	main()
