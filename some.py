#!/usr/bin/python3
import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument('-l', '--hello', action='store', default="nuts, balls even", dest='hello')
args = argparser.parse_args()

print("Finished target " + args.hello)