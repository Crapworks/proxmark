import usb.core
import usb.util
import sys
import array
import time

from binascii import hexlify
from struct import pack,  unpack
from utils import CMsg,  DeviceError

# USB read size
USB_DATA_BLOCK_SIZE = 64

#ERROR CODES
ERR_NOT_FOUND = 0x1
ERR_NO_ENDPOINT = 0x2

CMD_MEASURE_ANTENNA_TUNING = 0x0400
CMD_MEASURED_ANTENNA_TUNING = 0x0401

CMD_DOWNLOAD_RAW_ADC_SAMPLES_125K = 0x0207
CMD_DOWNLOADED_RAW_ADC_SAMPLES_125K = 0x0208

CMD_READER_ISO_14443a = 0x0385

CMD_DEBUG_PRINT_STRING = 0x0100
CMD_DEBUG_PRINT_INTEGERS = 0x0101
CMD_DEVICE_INFO = 0x0000
CMD_READ_MEM = 0x0106
CMD_ACK = 0x00ff

ISO14A_CONNECT = 0x1

class UsbCommand():
    """ USB Command Structure """
    
    def __init__(self):
        self.cmd = 0x0
        self.ext1 = 0x0
        self.ext2 = 0x0
        self.ext3 = 0x0
        self.data = "\x00" * 48
        
    def get_str_data(self):
        data = pack('iiii48s',  self.cmd,  self.ext1,  self.ext2,  self.ext3,  self.data)
        return data
        
    def set_str_data(self,  bytes):
        data = bytes.tostring()
        self.cmd,  self.ext1,  self.ext2, self.ext3,  self.data = unpack('iiii48s',  data)

class Proxmark:
    """
    proxmark: main class to communicate with the proxmark (currently old firmware version)
    """
    
    def __init__(self):
        self.dev = None
        self.ep_in = None
        self.ep_out = None
        self.iface = None
        self.cc = CMsg()

    def dump_data(self,  data):
        self.cc.output("")
        for i in range(1,  len(data)+1):
            if i % 8:
                print "0x%02x" % ord(data[i-1]), 
            else:
                print "0x%02x" % ord(data[i-1]) 
                if i < len(data):
                    self.cc.output("")

    def send_data(self,  usbcmd):        
        """ sending UsbCommand structured data to proxmark """
        
        cmdstr = usbcmd.get_str_data()
        return self.dev.write(self.ep_out.bEndpointAddress, cmdstr,  self.iface.bInterfaceNumber,  1000)
        
    def read_once(self):
        """ read UsbCommand structured data from proxmark """
        
        try:
            usbcmd = UsbCommand()            
            data = self.dev.read(self.ep_in.bEndpointAddress,  USB_DATA_BLOCK_SIZE,   self.iface.bInterfaceNumber,  500)
            usbcmd.set_str_data(data)
            return usbcmd
        except usb.core.USBError:
            return None
        
    def read_loop(self,  waitforcmd = None):
        """ read thread """
        
        while True:
            data = self.read_once()
            if data:     
                # print debug string
                if data.cmd == CMD_DEBUG_PRINT_STRING:                    
                    if data.ext1 > 70 or data.ext1 < 0:
                        data.ext1 = 0 
                        
                    dbg = data.data[:data.ext1]
                    self.cc.output(dbg + "\n")
                    
                # print debug integers
                if data.cmd == CMD_DEBUG_PRINT_INTEGERS:
                    self.cc.output("%08x, %08x, %08x\n" %  (data.ext1,  data.ext2,  data.ext3))
                
                # wait for special cmd code from proxmark?
                if waitforcmd:
                    if data.cmd == waitforcmd:
                        return data
                else:
                    return data

    def hf14a_reader(self):
        """ act like a iso14443a card reader """
        
        ### act like a reader ###
        self.cc.info("reading iso14443a rfid data...\n")
        
        usbcmd = UsbCommand()
        usbcmd.cmd = CMD_READER_ISO_14443a
        usbcmd.ext1 = ISO14A_CONNECT
        
        self.__send_data__(usbcmd)
        data = self.read_loop(CMD_DEBUG_PRINT_STRING)
        
        if data.data[0] == 0x0:
            self.cc.err("iso14443a card select failed\n")
            return 

        ### hexdump the card samples ###
        self.cc.info("retrieving card data...\n")

        usbcmd = UsbCommand()
        usbcmd.cmd = CMD_DOWNLOAD_RAW_ADC_SAMPLES_125K        
        
        self.send_data(usbcmd)
        data = self.read_thread(CMD_DOWNLOADED_RAW_ADC_SAMPLES_125K)        
        
        self.dump_data(data.data)
        
        self.ok("MiFare UID: %s\n" % (hexlify(data.data[41:45],  )))        

    def tune(self):
        """ antenna tuning """

        usbcmd = UsbCommand()
        usbcmd.cmd = CMD_MEASURE_ANTENNA_TUNING
        
        self.send_data(usbcmd)
        data = self.read_loop(CMD_MEASURED_ANTENNA_TUNING)
        
        # process results
        vLf125 = data.ext1 & 0xffff
        vLf134 = data.ext1 >> 16
        vHf = data.ext2 & 0xffff
        peakf = data.ext3 & 0xffff
        peakv = data.ext3 >> 16
      
        # print result
        self.cc.ok("LF antenna: %5.2f V @   125.00 kHz\n" % (vLf125 / 1000.0))
        self.cc.ok("LF antenna: %5.2f V @   134.00 kHz\n" % (vLf134 / 1000.0))
        self.cc.ok("LF optimal: %5.2f V @%9.2f kHz\n" % ((peakv / 1000.0), (12000.0 / (peakf + 1)) ))
        self.cc.ok("HF antenna: %5.2f V @    13.56 MHz\n"% (vHf / 1000.0))
        
        # print warnings/errors
        if  peakv < 2000:
            self.cc.err("Your LF antenna is unusable.\n")
        elif peakv < 10000:
            self.cc.warn("Your LF antenna is marginal.\n")
        if vHf < 2000:
            self.cc.err("Your HF antenna is unusable.\n")
        elif vHf < 5000:
            self.cc.warn("Your HF antenna is marginal.\n")
        
    def open_proxmark(self):
        """ open proxmark3 device and get read/write endpoints """
        
        # check for connected proxmark
        self.dev = usb.core.find(idVendor=0x9ac4, idProduct=0x4b8f)    
        if not self.dev:
            raise DeviceError('Proxmark not Found',  ERR_NOT_FOUND)

        # get configuration and interface 
        self.cfg = self.dev.get_active_configuration()
        self.iface = self.cfg[(0,  0)]

        # get reading and writing endoint
        self.ep_out = usb.util.find_descriptor(self.dev.get_interface_altsetting(), custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.ep_in = usb.util.find_descriptor(self.dev.get_interface_altsetting(), custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)    
        if not self.ep_in or not self.ep_out:
            raise DeviceError("Unable to get read/write endpoints",  ERR_NO_ENDPOINT)
        
        # try to detach kernel driver
        if self.dev.is_kernel_driver_active(self.iface.bInterfaceNumber):
            self.dev.detach_kernel_driver(self.iface.bInterfaceNumber)
        
        # set configuration
        self.dev.set_configuration(self.cfg)                
        
        # set alternate setting
        self.dev.set_interface_altsetting(self.iface)
        
        return (self.ep_out.bEndpointAddress, self.ep_in.bEndpointAddress)

