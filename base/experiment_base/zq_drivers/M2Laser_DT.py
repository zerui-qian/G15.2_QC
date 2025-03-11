# -*- coding: utf-8 -*-
"""
Created on Tue Sep 29 14:32:20 2015

@author: Thomas Fink, Quantum Photonics Group, ETH Zurich
"""

from __future__ import division, print_function
import socket
import json
import time

import Pyro4
from DaemonDAQ.Network.nameserver_client import nameserver as ns
import DaemonDAQ.Network.nw_utils as nw_utils


class M2Laser(object):
    
    
    # def __init__(self, address='172.31.88.105', port=39933): # G17 M2
    # def __init__(self, address='172.31.88.153', port=39933): # G15 M2
    #     self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     self.ip = address
    #     self.port = port
    #     for ownip in socket.gethostbyname_ex(socket.gethostname())[2]:
    #         if '192.33' in ownip:
    #             self.ownip = ownip
    #     if not hasattr(self, 'ownip'):
    #         raise RuntimeError("No internet connection for the client")
    #     self.connect()
        
    def __init__(self, address='172.31.88.153', port=39933): # G15 M2
        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = address
        self.port = port
        for ownip in socket.gethostbyname_ex(socket.gethostname())[2]:
            self.ownip = ownip
        if not hasattr(self, 'ownip'):
            raise RuntimeError("No internet connection for the client")
        self.connect()
        
        
    def connect(self):
        try:
            self._s.connect((self.ip, self.port))
            self.startmsg = {"transmission_id": [1], "op":"start_link", "parameters":{"ip_address":self.ownip}}
            self._sendObj(self.startmsg)         
            self.retmsg = self._readObj()
            if self.retmsg['parameters']['status'] == 'ok':
                print ('Start Link Reply ok')
            else:
                print('Start Link Reply Error')
        except socket.error as msg:
            print("Could not connect to ICE-BLOC at %s:%s\nSocket Error: %s" %( self.ip, self.port, msg))       
            

    def close(self):
        self._s.close()
        print("M2 connection closed.")
        
        
    def _get_timeout(self):
        return self._timeout
        
        
    def _set_timeout(self, timeout):
        self._timeout = timeout
        self.socket.settimeout(timeout)
        

    def _sendObj(self, obj):
        msg = json.dumps({"message": obj})
        if self._s:
            self._send(msg)


    def _send(self, msg):
#        self._s.send(msg) # Python2
        self._s.send(msg.encode()) # Python3
        
        
    def _read(self):
#        data = self._s.recv(1024) # Python2
        data = self._s.recv(1024).decode()
        if data == '':
            raise RuntimeError("Socket connection broken")
        return data

 
    def _readObj(self):
        data = json.loads(self._read())
        if data['message']['op'] == 'parse_fail':
            raise RuntimeError(self.parse_errorcode(data['message']['parameters']['protocol_error'][0]))
        else:
            return data['message']
        
        
    def parse_errorcode(self,errcode):
        switcher = {
            1: "JSON parsing error, invalid start command, wrong IP address.",
            2: "'message' string missing.",
            3: "'transmission_id' string missing.",
            4: "No transmission id value.",
            5: "'op' string missing.",
            6: "No operation name.",
            7: "Operation not recognised.",
            8: "'parameters' string missing.",
            9: "Invalid parameter tag or value.",        
        }
        return switcher.get(errcode,"nothing")
        
                
    def _ping(self):
        text_in = "PiNgTeSt"
        msg = {"transmission_id": [99], "op":"ping", "parameters":{"text_in":text_in}}
        self._sendObj(msg)
        ret = self._readObj()
        if ret['parameters']['text_out'] == text_in.swapcase():
            return True
        else:
            raise RuntimeError("Ping failed")
            
            
    def _status(self):
        msg = {"transmission_id": [99], "op":"get_status"}
        self._sendObj(msg)
        return self._readObj()
        
        
    def _alignment_status(self):
        msg = {"transmission_id": [99], "op":"get_alignment_status"}
        self._sendObj(msg)
        return self._readObj()        
        
    @property
    def wavelength_m(self):
        self._sendObj({"transmission_id": [1], "op":"poll_wave_m"})
        ret = self._readObj()
#        if ret['parameters']['status'][0] == 0:
#            raise RuntimeError("Tuning software not active.")
        if ret['parameters']['status'][0] == 1:
            raise RuntimeError("No link to wavelength meter or no meter configured.")
        return ret['parameters']['current_wavelength'][0], ret['parameters']['status'][0], ret['parameters']['lock_status'][0]
    @wavelength_m.setter
    def wavelength_m(self,wl):
        self._sendObj({"transmission_id": [1], "op":"set_wave_m", "parameters":{"wavelength":[wl]}})
        ret = self._readObj()
        if ret['parameters']['status'][0] == 0:
            return ret['parameters']['wavelength'][0]
        if ret['parameters']['status'][0] == 1:
            raise RuntimeError("No link to wavelength meter or no meter configured.")
        if ret['parameters']['status'][0] == 2:
            raise ValueError("Wavelength out of range.")
            
        
    def wl_lock(self,state):
        if state:
            lock = "on"
        else:
            lock = "off"
        self._sendObj({"transmission_id": [1], "op":"lock_wave_m", "parameters":{"operation":lock}})
        ret = self._readObj()
        if ret['parameters']['status'][0] == 0:
            return True
        if ret['parameters']['status'][0] == 1:
            raise RuntimeError("No link to wavelength meter or no meter configured.")
        
        
    @property
    def wavelength_t(self):
        self._sendObj({"transmission_id": [1], "op":"poll_move_wave_t"})
        ret = self._readObj()
        if ret['parameters']['status'][0] == 2:
            raise RuntimeError("Tuning operation failed.")
        else:
            return ret['parameters']['current_wavelength'][0], ret['parameters']['status'][0]
    @wavelength_t.setter
    def wavelength_t(self,wl):
        self._sendObj({"transmission_id": [1], "op":"move_wave_t", "parameters":{"wavelength":[wl]}})
        ret = self._readObj()
        if ret['parameters']['status'][0] == 0:
            return True
        if ret['parameters']['status'][0] == 1:
            raise RuntimeError("Command failed.")
        if ret['parameters']['status'][0] == 2:
            raise ValueError("Wavelength out of range.")
            
    def set_wavelength_t(self,wl):
        self.wavelength_t = wl
        if wl >= 807 and wl <= 810:
            time.sleep(10)
    
    def get_wavelength_t(self):
        return self.wavelength_t[0]
    
    def set_wavelength_m(self,wl):
        self.wavelength_m = wl
        
    def get_wavelength_m(self):
        return self.wavelength_m[0]


if __name__ == '__main__':
    G15_Laser_address = {'address': '172.31.88.153', 'port': 39933}
    G17_Laser_address = {'address': '172.31.88.105', 'port': 39933}

    args = G15_Laser_address
    # args = G17_Laser_address
    
    object_dict = {'M2Laser': M2Laser(**args)}
    nw_utils.RunServer(object_dict)

#from m2laser import *
#
#m2 = m2laser()
#m2.connect()
#print m2._status()
#print m2._alignment_status()
#print m2._ping()
##print m2.wavelength_m
##m2.wavelength_m = 800
#m2.wl_lock(True)
#m2.wavelength_t = 855
#wl,_,_ = m2.wavelength_m
#m2.close()