#!/usr/bin/python3
from typing import *
from collections import deque
from os import PathLike
import subprocess
import toml
import threading
import argparse
import numpy as np

class Target:
    def __init__(self, name, data, config=None):
        self.name = name
        self.config = config
        if isinstance(data, str):
            self.fpath = data
            self.args = []
        else:
            self.fpath = data['path']
            args = data.get('args')
            if args is not None:
                self.args = list(args)
            else:
                self.args = []


    
    def run_sync(self, args: List[str] = []):
        self.config.signal("target_started", {'name': self.name})
        subprocess.run([self.fpath] + self.args + args)
        self.config.signal("target_terminated", {'name': self.name})
    
    def run(self, special_args: List[str] = []):
        execution = threading.Thread(target=self.run_sync, args=(special_args,))
        execution.start()

class Event:
    def __init__(self, targets: List[Target], args: List[Dict[str, Any]]):
        self.targets = targets
        self.args = args

    def run(self, signal_environment: Dict[str, Any] = {}, environment: Dict[str, Any] = {}):
        for target in self.targets:
            args = []
            for arg in self.args:
                argtype = arg.get('type')
                if argtype is None: continue
                if argtype == 'dynamic':
                    relation = arg.get('relation')
                    if relation is None: continue
                    optional = arg.get('optional')
                    if optional is None: optional = False
                    signal_value = signal_environment.get(relation)
                    if signal_value is None:
                        if optional:
                            continue
                        else:
                            return
                    else:
                        args.append(str(signal_value))
                elif argtype == 'environment':
                    relation = arg.get('relation')
                    if relation is None: continue
                    optional = arg.get('optional')
                    if optional is None: optional = False
                    environment_value = environment.get(relation)
                    if environment_value is None:
                        if optional:
                            continue
                        else:
                            return
                    else:
                        args.append(str(environment_value))
                elif argtype == 'literal':
                    value = arg.get('value')
                    if value is not None: args.append(str(value))
                else:
                    continue
            target.run(args)

class DataStore:
    def __init__(self, file: PathLike, data=None, config=None):
        self.fpath = file
        self.config = config
        if data is not None:
            self.data = data
        else:
            with toml.load(file).get("Environment") as environ:
                if environ is not None:
                    self.data = environ
                else:
                    self.data = {}
    
    def put_value(self, key: str, value):
        self.data[key] = value
        if self.config is not None:
            self.config.signal('updated_value', {'value': key, 'to': value})

    def get_value(self, key: str):
        if self.config is not None:
            self.config.signal('retrieved_value', {'value': key})
        return self.data.get(key)

    def update(self):
        if self.config is None: return
        self.data = self.config.update()
    
    def post(self):
        if self.config is None: return
        self.config.post()

class Signal:
    def __init__(self, event: Event, conditions: Dict[str, str] = None):
        self.event = event
        if conditions is not None:
            self.conditions = conditions
        else:
            self.conditions = {}
    
    def run(self, args: Dict[str, Any], environment: Dict[str, Any]):
        run = True
        if args is None:
            args = {}
        for arg in args:
            condition = self.conditions.get(arg)
            if condition is not None:
                if condition[0] == '!':
                    if args[arg] == condition[1:]:
                        run = False
                        break
                else:
                    if args[arg] != condition:
                        run = False
                        break
        if run:
            self.event.run(args, environment)

class Config:
    def __init__(self, file: PathLike):
        self.fpath = file
        self.full_data = toml.load(self.fpath)
        
        if self.full_data.get("Environment") is not None:
            self.data = DataStore(file, self.full_data.get("Environment"), self)
        else:
            self.data = DataStore(file, {}, self)
        
        if self.full_data.get("Register") is not None:
            self.register = self.full_data["Register"]

            self.targets = {}
            for target_name in self.register.keys():
                self.targets[target_name] = Target(target_name, self.register[target_name], self)
        else:
            self.register = {}

        if self.full_data.get("Events") is not None:
            events = self.full_data.get("Events")
            self.events: Dict[str, Event] = {}
            for event in events.keys():
                targets = events[event].get("targets")
                if targets is not None:
                    attached_targets: List[Target] = []
                    for target in targets:
                        cur_target = self.targets.get(target)
                        if cur_target is not None:
                            attached_targets.append(cur_target)
                    args = events[event].get("args")
                    if args is None: args = []
                    self.events[event] = Event(attached_targets, args)
            
            if self.full_data.get("Signals") is not None:
                signals = self.full_data.get("Signals")
                self.signals: Dict[str, List[Signal]] = {}
                for signal in signals:
                    attached_events: List[Event] = []
                    for event in signals[signal]:
                        attachee = None
                        if isinstance(event, dict):
                            possible = self.events.get(event['event'])
                            if possible is not None:
                                attachee = Signal(possible, event.get('conditions'))
                        else:
                            possible = self.events.get(event)
                            attachee = Signal(possible)
                        if possible is not None:
                            attached_events.append(attachee)
                    self.signals[signal] = attached_events
                
        self.signal('init') # Start initial processes

    def run_all_targets(self):
        for target in self.targets.values():
            target.run()

    def signal(self, signal: str, args: Dict[str, str] = None):
        events = self.signals.get(signal)
        if events is not None:
            for event in events:
                event.run(args, self.data.data)
    
    def update(self):
        self.full_data = toml.load(self.fpath)
        loaded_data = self.full_data.get['Environment']
        if loaded_data is not None:
            self.data.data = loaded_data
        else:
            self.data.data = {}

    def post(self):
        self.full_data['Environment'] = self.data.data
        with open(self.fpath, 'w') as f:
            toml.dump(self.full_data, f)

config = None

def init(path):
    global config
    config = Config(path)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(prog="Pi Configuration Manager", usage="Starts the configuration server.")
    argparser.add_argument('-p', '--path', default="/home/pi/vision/configs/config.json", dest="path", help="Path to the configuration file to be loaded.")
    args = argparser.parse_args()
    try:
        init(args.path)
    except KeyboardInterrupt:
        pass
