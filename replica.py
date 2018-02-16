#!/usr/bin/env python
import sys
import getopt
import pdb

uid=-1
f=-1

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "i:f:")
	except getopt.GetoptError as err:
		print str(err)  # will print something like "option -a not recognized"
		sys.exit(2)
	for o, a in opts:
		if o == "-i":
			uid=int(a)
		elif o == "-f":
			f=int(a)
		else:
			assert False, "unhandled option"

if __name__=='__main__':
	main()
