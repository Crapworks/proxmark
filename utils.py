#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys

class DeviceError(Exception):
    def __init__(self, value,  error):
        self.value = value
        self.error = error

class Colors:
    """ provide some fancy colors on the commandline """
    
    def __init__(self):
        self.colors = {}
        self.colors['green'] = '\033[92m'
        self.colors['yellow'] = '\033[93m'
        self.colors['red'] = '\033[91m'
        self.colors['blue']='\033[94m'      
        self.colors['end'] = '\033[0m'

    def cc_text(self, color, text):
        if not color in self.colors:
            print "color " + color + " not defined"
        return self.colors[color] + text + self.colors['end'] 

class CMsg(Colors):
    """ prints some beautiful colored messages """
    
    def err(self, msg):
        sys.stdout.write("[" + self.cc_text('red', '-') + "] " + msg)
        
    def warn(self, msg):
        sys.stdout.write("[" + self.cc_text('yellow', '+') + "] " + msg)
        
    def ok(self, msg):
        sys.stdout.write("[" + self.cc_text('green', '+') + "] " + msg)
        
    def info(self,  msg):
        sys.stdout.write("[" + self.cc_text('green', '*') + "] " + msg)
        
    def output(self, msg):
        sys.stdout.write("[" + self.cc_text('blue', '>') + "] " + msg)

