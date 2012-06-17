#!/usr/bin/env python

VERSION="0.1"

import sys

from proxmark import Proxmark
from utils import CMsg,  DeviceError
            
def main():
    cc = CMsg()
    
    # hail to the chief
    cc.info("RFIDLE V%s - RFID Exploitation Framework\n" % (VERSION,  ))
    cc.info("(c) 2010 - Christian Eichelmann\n\n")

    # create new proxmark instance
    prox = Proxmark()    

    # open proxmark device
    try:    
        endpoints = prox.open_proxmark()
    except DeviceError as e:
        cc.err(e.value + "\n")
        sys.exit(e.error)
    else:
        cc.ok("Connected to Proxmark3 at [0x%x/0x%x]\n" % (endpoints[0],  endpoints[1]))
        
    #prox.hf14a_reader()
    prox.tune()
    
if __name__ == '__main__':
    main()
