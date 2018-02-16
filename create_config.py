#!/usr/bin/env python
import json

def main():
	fd=open("config.txt","w")
	fd.write(json.dumps({'f':2,}))
	fd.close()


if __name__=='__main__':
	main()
