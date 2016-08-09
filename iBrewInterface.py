#!/usr/bin/python
# -*- coding: utf8 -*-

import socket
import sys
import struct
import string
import random
import select

from iBrewProtocol import *
from iBrewSettings import *

#------------------------------------------------------
# iBrew CLIENT
#
# Client to iKettle 2.0 or Smarter Coffee Devices
#------------------------------------------------------

class iBrewClient:

    """
    dump = False
    device = ""
    version = 0
    statusCommand = 0
    
    isSmarterCoffee = False
    statusCoffee = 0
    cups = 0
    strength = 0
    waterLevel = 0
    WiFiStrenght = 0
    
    isKettle2 = False
    statusKettle = 0
    temperature = 0
    waterSensorBase = 0
    waterSensor
    onBase = False
    WiFi = []
    WiFiFirmware = ""
    
    sendMessage = ""
    readMessage = ""
    """
    
    #------------------------------------------------------
    # NETWORK CONNECTION: iKettle 2.0 & Smarter Coffee
    #------------------------------------------------------

    def connect(self, host):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            print 'iBrew: Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
            return False
        try:
            self.socket.connect((host, iBrewPort))
        except socket.error, msg:
            print 'iBrew: Failed to connect to host (' + host + ') Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
            return False
            
        #default values
        self.dump = False
        self.isKettle2 = False
        self.isSmarterCoffee = False
        
        self.read()
        self.info()
        if self.isKettle2:
            self.calibrate_base()
        self.host = host
        return True

    def __init__(self,host, auto_connect = "True"):
        if auto_connect:
            if not self.connect(host):
                sys.exit()

    def __del__(self):
        self.socket.close()

    #------------------------------------------------------
    #  NETWORK PROTOCOL: iKettle 2.0 & Smarter Coffee
    #------------------------------------------------------

    # read a protocol message
    def read_message(self):
        try:
            message = ""
            i = 0
            # let the buffer of the os handle this
            
            # error check here...
            
            
            data = self.socket.recv(1)
            #if not data: return
            while data != iBrewTail:
                message += data
                data = self.socket.recv(1)
                #if not data: break
                i += 1
            message += data
            return message
        except socket.error, msg:
            print 'iBrew: Failed to read message. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]

    # read a protocol message and decode it to internal variables
    def read(self):
     
        message = self.read_message()
     
        # Command Status
        if message[0] == iBrewResponseStatus:
            self.statusCommand = struct.unpack('B',message[1])[0]
            if not iBrewStatusCommand.has_key(self.statusCommand):
                self.statusCommand = 0xff
    
        # Calibration
        elif message[0] == iBrewResponseCalibrationBase:
            self.waterSensorBase = struct.unpack('B',message[2])[0] + 256 * struct.unpack('B',message[1])[0]
        
        # Device Info
        elif message[0] == iBrewResponseDeviceInfo:
            self.isSmarterCoffee = False
            self.isKettle2 = False
            if struct.unpack('B',message[1])[0] == 1:
                self.isKettle2 = True
                self.device = "iKettle 2.0"
            if struct.unpack('B',message[1])[0] == 2:
                self.isSmarterCoffee = True
                self.device = "SmarterCoffee"
            self.version = struct.unpack('B',message[2])[0]

        # WiFi Firmware
        elif message[0] == iBrewResponseWifiFirmware:
            s = ""
            for i in range(1,len(message)-1):
                x = str(message[i])
                if x in string.printable:
                    s += x
            self.WiFiFirmware = s
 
        # WiFi List
        elif message[0] == iBrewResponseWifiList:
            a = ""
            w = []
            db = False
            for i in range(1,len(message)-1):
                x = str(message[i])
                if x == ',':
                   db = True
                   d = ""
                   continue
                elif x == '}':
                   db = False
                   w += [(a,d)]
                   a = ""
                   continue
                elif not db and x in string.printable:
                    a += x
                elif db and x in string.printable:
                    d += x
            from operator import itemgetter
            
            # most powerfull wifi on top
            self.WiFi = sorted(w,key=itemgetter(1))
            # alphabetically
            #self.WiFiSorted = sorted(w,key=itemgetter(0))

        # Device Status
        elif message[0] == iBrewResponseStatusDevice:
            if self.isKettle2:
                #self.unknown      = struct.unpack('B',message[5])[0]
                self.statusKettle = struct.unpack('B',message[1])[0]
                self.temperature  = struct.unpack('B',message[2])[0]
                self.waterSensor  = struct.unpack('B',message[4])[0] + 256 * struct.unpack('B',message[3])[0]
                if self.temperature == iBrewOffBase:
                    self.onBase = False
                else:
                    self.onBase = True
            elif self.isSmarterCoffee:
                self.statusSmarterCoffee = struct.unpack('B',message[1])[0]
                self.waterLevel          = struct.unpack('B',message[2])[0]
                # ???
                self.WiFiStrenght        = struct.unpack('B',message[3])[0]
                self.strength            = struct.unpack('B',message[4])[0]
                self.cups                = struct.unpack('B',message[5])[0]
        self.print_message_received(message)
     
        self.readMessage = message
        return message

    # send a protocol message and wait's for response...
    def send(self,message):
        try:
            if len(message) > 0 and message[len(message)-1] == iBrewTail:
                self.socket.send(message)
                self.sendMessage = message
                self.print_message_send(message)
            elif len(message) > 0:
                self.socket.send(message+iBrewTail)
                self.sendMessage = message
                self.print_message_send(message+iBrewTail)
            else:
                return
    
        except socket.error, msg:
            print 'iBrew: Failed to send message. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]

        # keep reading until we got the response message
        # if a message does not generate a response... we're in deep shit...
        m = self.read()
        while m[0] == iBrewResponseStatusDevice:
            m = self.read()
            # FIX TIMEOUT 10 tries???

        # store reply message
        r = m

        # keep reading until we got the device status message
        m = self.read()
        while m[0] != iBrewResponseStatusDevice:
            m = self.read()
        return r

    #------------------------------------------------------
    #  NETWORK CONVERTERS: iKettle 2.0 & Smarter Coffee
    #------------------------------------------------------

    # Convert raw data to hex string without 0x seperated by spaces
    def message_to_string(self,message):
        raw = ""
        for x in range(0,len(message)):
            y = struct.unpack('B',message[x])[0]
            if y < 0x10:
               raw += "0"
            raw += hex(y)[2:4] + " "
        return raw

    # Convert hex string without 0x input maybe seperated by spaces or not
    def string_to_message(self,code):
        message = ""
        
        if len(code) > 2 and code[2] != " ":
            if len(code) % 2 == 0:
                try:
                    message = code.decode("hex")
                except:
                    print "iBrew: Invalid Input: Error encoding hex \'" + code + "\'"
            else:
                print "iBrew: Invalid Input: Missing character on position: " + str(len(code)+1)
        elif len(code) % 3 == 2:
            for x in range(0,(len(code) / 3)+1):
                if x > 0:
                    if code[x*3-1] != ' ':
                        print "iBrew: Invalid Input: Expected space character on position: " + str(x*3)
                        break
                s = code[x*3]+code[x*3+1]
                try:
                    message +=  s.decode("hex")
                except:
                    print "iBrew: Invalid Input: Error encoding hex \'" + s + "\' on position: " + str(x*3+1)
        else:
            print "iBrew: Invalid Input: Missing character on position: " + str(len(code)+1)
        return message


    #------------------------------------------------------
    # CONVERTERS: iKettle 2.0
    #------------------------------------------------------

    # Fix Check value's

#   calibrate nokettlebase:       1120     measure: kettle off: 2010 kettle empty: 2070 kettle full: 2140  (div 890 950 1020)
#   calibrate emptykettlebase: 1070     measure: kettle off: 1975 kettle empty: 2020 kettle full: 2085  (div 905 950 1015)
#   calibrate fullkettlebase:      1010    measure: kettle off: 1875 kettle empty: 1950 kettle full: 2015  (div 865 940 1005)
# div = measure - base
# need temperature in calclation...
#   1.8l
    def water_sensor(self):
        # is this accurate??? nope...
        # sometimes if placed on base it gives wrong levels

        x = (1.800/72) * (self.waterSensor - self.waterSensorBase - 1000)
        if x < 0:
            return 0.0
        if x > 2:
            return 2.0
        else:
            return x

    #------------------------------------------------------
    # PRINT: iKettle 2.0 & Smarter Coffee
    #------------------------------------------------------

    def print_message_send(self,message):
        if self.dump:
            print "iBrew: Message Send: " + self.message_to_string(message)
            s = iBrew_message_description(iBrew_raw_to_hex(struct.unpack('B',message[0])[0]))
            if s != "":
                print "       " + s

    def print_message_received(self,message):
        if self.dump: # and message[0] != iBrewResponseStatusDevice:
            print "iBrew: Message Received: " + self.message_to_string(message)
        s = iBrew_message_description(iBrew_raw_to_hex(struct.unpack('B',message[0])[0]))
        l = "       "
        
        if message[0] == iBrewResponseStatus:
            if self.dump:
                print l + s + ": " + iBrewStatusCommand[self.statusCommand]
            if not self.dump and self.statusCommand != 0:
                print "iBrew: " + s + ": " + iBrewStatusCommand[self.statusCommand]
                
   
        elif message[0] == iBrewResponseWifiList:
            if self.dump:
                print l + s
            print
            print "           Signal   Wireless Network"
            for i in range(0,len(self.WiFi)):
                
                dBm = int(self.WiFi[i][1])
                
                # quality = 2 * (dBm + 100)  where dBm: [-100 to -50]
                # dBm = (quality / 2) - 100  where quality: [0 to 100]
                
                if dBm <= -100:
                    quality = 0;
                elif dBm >= -50:
                    quality = 100;
                else:
                    quality = 2 * (dBm + 100);
    
                s = ""
                for x in range(quality / 10,10):
                    s += " "
                for x in range(0,quality / 10):
                    s += "█"

                print "       " + s + "   " + self.WiFi[i][0]
            print

        elif message[0] == iBrewResponseWifiFirmware:
            if self.dump:
                print l + s
            print
            print self.WiFiFirmware
            print
            
        elif message[0] == iBrewResponseUnknown:
            print l + s + " Not Implemented"

        elif message[0] == iBrewResponseZero:
            print l + s + " Not Implemented"

        elif message[0] == iBrewResponseSettings:
            print l + s + " Not Implemented"

        elif message[0] == iBrewResponseDeviceInfo:
            if self.dump:
                print l + s + " " + self.device + " Firmware v" + str(self.version)

        elif message[0] == iBrewResponseCalibrationBase:
            if self.dump:
                print l + s + " " +  str(self.waterSensorBase)

        elif message[0] == iBrewResponseStatusDevice:
            if self.dump:
                #FIX HERE
                pass
        
        else:
            if self.dump:
                if s != "":
                    print l + s
                else:
                    print "       Unknown Reply Message"

    def print_info(self):
        print "iBrew: " + self.device + " v" + str(self.version)

    def print_watersensor_base(self):
        print "iBrew: Watersensor base value " + str(self.waterSensorBase)
    
    def print_status(self):
        if self.dump:
            m = self.read()
            print "iBrew: Message Received: " + self.message_to_string(m)
        print
        if self.isKettle2 == True:
            if self.onBase:
                print "Status        " + iBrewStatusKettle[self.statusKettle]
                print "Kettle        On Base"
                print "Temperature   " + str(self.temperature) +  "ºC"
                print "Water level   " + "%.1f" % self.water_sensor() + "l (raw: " + str(self.waterSensor) + ":" + str(self.waterSensorBase) + ")"
            else:
                print "Status        " + iBrewStatusKettle[self.statusKettle]
                print "Kettle        Not On Base"
        if self.isSmarterCoffee == True:
            print "Status        " + iBrewStatusCoffee[self.statusCoffee]
            w = "Unknown"
            if iBrewWaterLevelStatus.has_key(self.waterLevel):
                w = iBrewWaterLevelStatus[self.waterLevel]
            print "Water level   " + w
            s = ""
            if iBrewStrength.has_key(self.strength):
                s = iBrewStrength.has_key[self.strength]
            print "Setting       " + str(self.cups) + " " + s + " cups"
            #print "WiFi Strenght " + str(self.WiFiStrenght)
        # FIX add the rest
        print

    def print_short_status(self):
        if self.dump:
            m = self.read()
            print "iBrew: Message Received: " + self.message_to_string(m)
        if self.isKettle2 == True:
            if self.onBase:
                print "iBrew: " + iBrewStatusKettle[self.statusKettle] + " On Base (" + str(self.temperature) + "ºC, " + str(self.waterSensor) + ")"
            else:
                print "iBrew: " + iBrewStatusKettle[self.statusKettle] + " Not On Base"
        if self.isSmarterCoffee == True:
            s = "Unknown"
            if iBrewStrength.has_key(self.strength):
                s = iBrewStrength.has_key[self.strength]
            w = "Unknown"
            if iBrewWaterLevelStatus.has_key(self.waterLevel):
                w = iBrewWaterLevelStatus[self.waterLevel]
            print "Status       " + iBrewStatusCoffee[self.statusCoffee] + " (Water level: " + w + ", Setting: " + str(self.cups) + " " + s + "cups)"
            # FIX add the rest

    def print_connect_status(self):
        print "iBrew: Connected to " + self.device + " Firmware v" + str(self.version) + " (" + self.host + ")"

    #------------------------------------------------------
    # COMMANDS: iKettle 2.0 & Smarter Coffee
    #------------------------------------------------------

    def info(self):
        self.send(iBrewCommandInfo)
   
    def raw(self,code):
        self.send(self.string_to_message(code))

    #------------------------------------------------------
    # COMMANDS: WiFi
    #------------------------------------------------------

    def wifi_firmware(self):
        self.send(iBrewCommandWiFiFirmware)

    def wifi_scan(self):
        self.send(iBrewCommandWiFiScan)
    
    def wifi_reset(self):
        self.send(iBrewCommandWiFiReset)
    
    def wifi_connect(self):
        self.send(iBrewCommandWiFiConnect)

    def wifi_password(self,password=""):
        # add "}" ?
        self.send(iBrewCommandWiFiPassword+password)

    def wifi_name(self,name=""):
        self.send(iBrewCommandWiFiName+name)
    
    #------------------------------------------------------
    # COMMANDS: iKettle 2.0
    #------------------------------------------------------

    def calibrate(self):
        if self.isKettle2 == True:
            self.send(iBrewCommandCalibrate)
        else:
            print 'iBrew: You need a kettle to calibrate its water sensor'

    def calibrate_base(self):
        if self.isKettle2 == True:
            self.send(iBrewCommandWaterSensorBase)
        else:
            print 'iBrew: You need a kettle to read its water sensor base value'

    def store_calibrate_base(self,base = 0):
        if self.isKettle2 == True:
            high = base / 256
            low =  base % 256
            print high
            print low
            self.send(iBrewCommandWaterSensorBase+struct.pack('B',high)+struct.pack('B',low))
        else:
            print 'iBrew: You need a kettle to store its water sensor base value'

    def store_settings(self,temperature = 100, keepwarmtime = 0, formulaOn = False, formulaTemperature = 75):
        if self.isKettle2 == True:
            # FIX THIS timer
            self.send(iBrewCommandStoreSettings+struct.pack('B',temperature)+struct.pack('B',keepwarmtime)+struct.pack('B',formulaOn)+struct.pack('B',formulaTemperature))
        else:
            print 'iBrew: You need a kettle to store its user settings'

    def heat(self):
        if self.isKettle2 == True:
            self.send(iBrewCommandHeat)
        else:
            print 'iBrew: You need a kettle to heat water'

    def formula(self):
        if self.isKettle2 == True:
            self.send(iBrewCommandFormula)
        else:
            print 'iBrew: You need a kettle to heat water in formula mode'

    # does this work on coffee? (that's why no check)
    def stop(self):
        self.send(iBrewCommandStop)

    #------------------------------------------------------
    # COMMANDS: Smarter Coffee
    #------------------------------------------------------

    def brew(self):
        if self.isSmarterCoffee == True:
            self.send(iBrewCommandBrew)
        else:
            print 'iBrew: The device does not brew coffee'

    def hotplate_off(self):
        if self.isSmarterCoffee == True:
            self.send(iBrewCommandHotplateOff)
        else:
            print 'iBrew: The device does not have a hotplate'

    def hotplate_on(self, timer=5):
        if self.isSmarterCoffee == True:
            if timer >= 5 and timer <= 30:
                self.send(iBrewCommandHotplateOn+struct.pack('B',number))
            else:
                print "iBrew: Invalid hotplate timer, range is between 5 and 30 minutes, not " +str(timer) + " minutes"
        else:
            print 'iBrew: The device does not have a hotplate'

    def grinder(self):
        if self.isSmarterCoffee == True:
            self.send(iBrewCommandGrinder)
        else:
            print 'iBrew: The device does not have a grinder'

    def coffee_cups(self,number=1):
        if self.isSmarterCoffee == True:
            if number < 1 or number > 12:
                print "iBrew: Invalid number of cups, range is between 1 and 12 cups, not  " + str(number) + " cups"
            self.send(iBrewCommandCups+struct.pack('B',number))
        else:
            print 'iBrew: The device does not let you choose the number of cups to brew'

    def coffee_strength(self,strength="medium"):
        if self.isSmarterCoffee == True:
            if strength.lower == "weak":
                number = 0
            elif strength.lower == "medium":
                number = 1
            elif strength.lower == "strong":
                number = 2
            else:
                print "iBrew: Invalid coffee strength, options are weak, medium, strong, not " + strength
            if number:
                self.send(iBrewCommandStrenght+struct.pack('B',number))
        else:
            print 'iBrew: The device does not let you choose the coffee strength'