#!/usr/bin/python3
import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument('-l', '--hello', action='store', default="unknown", dest='hello')
argparser.add_argument('-p', '--primary', action='store', default="Finished target ", dest='primary')
args = argparser.parse_args()

print(args.primary + args.hello)