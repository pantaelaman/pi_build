#!/usr/bin/python3
import argparse

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-l', '--hello', action='store_true', dest='hello')
    args = argparser.parse_args()

    if args.hello:
        print("Hello, World!")
    else:
        print("Goodbye, World!")

if __name__ == "__main__":
    main()
