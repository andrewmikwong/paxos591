#!/usr/bin/env python
import sys
import getopt
import json

import grpc
import paxos_pb2
import paxos_pb2_grpc

f=-1

def main():
	fd=open("config.txt","r")
	configs=json.loads(fd.read())
	fd.close()
	f=configs['f']
	s=''

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

	channel=grpc.insecure_channel('localhost:'+str(8000+uid))
	stub=paxos_pb2_grpc.ChatterStub(channel)
	while(s!='quit'):
		s=raw_input()
		response=stub.SendChatMessage.future(paxos_pb2.ChatRequest(mesg=s))
		print response.result().mesg	
		

if __name__=='__main__':
	main()
