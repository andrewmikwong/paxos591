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

	channel=grpc.insecure_channel('0.0.0.0:8000')
	stub=paxos_pb2_grpc.ChatterStub(channel)
	while(s!='quit'):
		s=raw_input()
		response=stub.SendChatLine(paxos_pb2.ChatRequest(line=s))
		print response.line	
		

if __name__=='__main__':
	main()
