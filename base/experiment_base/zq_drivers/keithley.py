# -*- coding: utf-8 -*-
"""
Created on Fri Oct 02 16:49:17 2015

@author: Deepankur Thureja, Meinrad Sidler
"""

from __future__ import division, print_function

#import numpy as np
# import matplotlib.pyplot as plt
# from six.moves import cPickle as pickle
# import sys, os, glob
#import visa
import pyvisa as visa
import numpy as np
import time
import Pyro4

from DaemonDAQ.Network.nameserver_client import nameserver as ns
import DaemonDAQ.Network.nw_utils as nw_utils
import DaemonDAQ.Core.config as config


class keith2450(object):

    def __init__(self,address, volt_step_lim = 0.01, volt_high_lim = 20):
        self._address = address
        self._rm = visa.ResourceManager()
        self._inst = self._rm.open_resource(self._address,timeout=1000)
        self.volt_step_lim = volt_step_lim
        self.volt_high_lim = volt_high_lim

    @property
    def outp(self):
        ans = self._inst.query(':outp?')
        if ans[0] == '1':
            return True
        else:
            return False

    @outp.setter
    def outp(self,boolOn):
        if boolOn:
            self._inst.write(':outp on')
        else:
            self._inst.write(':outp off')

    @property
    def _volt(self):
        ans = self._inst.query(':sour:volt:lev:imm:ampl?')
        return float(ans)

    @_volt.setter
    def _volt(self,voltFloat):
        self._inst.write(':sour:volt:lev:imm:ampl ' + str(voltFloat))
        
    @property
    def ilim(self):
        ans = self._inst.query(':sour:volt:ilim?')
        return float(ans)

    @ilim.setter
    def ilim(self,ilimFloat):
        self._inst.write(':sour:volt:ilim ' + str(ilimFloat))
    
    @property
    def curr(self):
        ans = self._inst.query(':read?')
        return float(ans)
    
    def get_current(self):
        return self.curr

    def set_voltage(self, voltFloat):
        self.volt = voltFloat
        
    def get_voltage(self):
        return self.volt
           
    @property
    def volt(self):
        return self._volt

    # with safety
    @volt.setter
    def volt(self,voltFloat):
        pv = self._volt
        sv = voltFloat
        if abs(sv) > self.volt_high_lim:
            sv = pv
            print("ERROR : EXCEEDING HIGH VOLTAGE LIMIT!")
        steplim = self.volt_step_lim
        if abs(pv - sv) > steplim:
            stepnum = np.ceil(abs(pv - sv)/(1.0*steplim))
            smooth_move_vals = np.linspace(pv, sv, stepnum)
            for val in smooth_move_vals:
                self._volt = val
                time.sleep(0.05)
                print(self._volt)
                time.sleep(0.05)
        self._volt = sv
        

class keith2400(object):

    def __init__(self,address, volt_step_lim = 0.01, volt_high_lim = 20):
        self._address = address
        self._rm = visa.ResourceManager()
        self._inst = self._rm.open_resource(self._address,timeout=1000)
        self.volt_step_lim = volt_step_lim
        self.volt_high_lim = volt_high_lim

    @property
    def outp(self):
        ans = self._inst.query(':outp?')
        if ans[0] == '1':
            return True
        else:
            return False

    @outp.setter
    def outp(self,boolOn):
        if boolOn:
            self._inst.write(':outp on')
        else:
            self._inst.write(':outp off')
         
    # Enable local operation
    @property    
    def local(self):
        self._inst.write(':syst:loc')
    
    @property
    def _volt(self):
        ans = self._inst.query(':sour:volt:lev:imm:ampl?')
        return float(ans)

    @_volt.setter
    def _volt(self,voltFloat):
        self._inst.write(':sour:volt:lev:imm:ampl ' + str(voltFloat))
        
    # Get/set voltage range
    @property
    def voltrange(self):
        ans = self._inst.query(':sour:volt:rang?')
        return float(ans)
        
    @voltrange.setter
    def voltrange(self,voltFloat):
        self._inst.write(':sour:volt:rang ' + str(voltFloat))
    
    # Get/set current compliance    
    @property
    def currcomp(self):
        ans = self._inst.query(':sens:curr:prot:lev?')
        return float(ans)
        
    @currcomp.setter
    def currcomp(self,currFloat):
        self._inst.write(':sens:curr:prot:lev ' + str(currFloat))
    
    # Synchronize the measurement range with the compliance range setting,
    # default is OFF --> leave it like that    
    @property
    def currcomprsync(self):
        ans = self._inst.query(':sens:curr:prot:rsyn?')
        if ans[0] == '1':
            return True
        else:
            return False
        
    @currcomprsync.setter
    def currcomprsync(self,boolOn):
        if boolOn:
            self._inst.write(':sens:curr:prot:rsyn on')
        else:
            self._inst.write(':sens:curr:prot:rsyn off')
    
    # Set the function of the source: 'VOLT' or 'CURR'
    @property
    def source(self):
        ans = self._inst.query(':sour:func?')
        return (str(ans))
    
    @source.setter
    def source(self, func):
        self._inst.write(':sour:func ' + str(func))
    
    # Set the function of the sensing: 'VOLT' or 'CURR'
    @property
    def sense(self):
        ans = self._inst.query(':sens:func?')
        return (str(ans))
    
    @sense.setter
    def sense(self, func):
        self._inst.write(':sens:func "%s"' %(str(func)))
    
#    @property
#    def ilim(self):
#        ans = self._inst.query(':sour:volt:ilim?')
#        return float(ans)
#
#    @ilim.setter
#    def ilim(self,ilimFloat):
#        self._inst.write(':sour:volt:ilim ' + str(ilimFloat))
    
    @property
    def curr(self):
        ans = self._inst.query(':meas:curr?')
        return float(ans.split(',')[1])
    
    def get_current(self):
        return self.curr
    
    def set_voltage(self, voltFloat):
        self.volt = voltFloat
        
    def get_voltage(self):
        return self.volt
    
    @property
    def volt(self):
        return self._volt

    # with safety
    @volt.setter
    def volt(self,voltFloat):
        pv = self._volt
        sv = voltFloat
        if abs(sv) > self.volt_high_lim:
            sv = pv
            print("ERROR : EXCEEDING HIGH VOLTAGE LIMIT!")
        steplim = self.volt_step_lim
        if abs(pv - sv) > steplim:
            stepnum = np.ceil(abs(pv - sv)/(1.0*steplim))
            smooth_move_vals = np.linspace(pv, sv, int(stepnum))
            for val in smooth_move_vals:
                self._volt = val
                time.sleep(0.05)
                print(self._volt)
                time.sleep(0.05)
        self._volt = sv 

    #def volt_sweep(self, init, fin, step):
    #    kt.sweep_range = np.linspace(init, fin, step)

#def RunServer(host = 'Pylon.dhcp.phys.ethz.ch'):
#    
#    Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
#    Pyro4.config.SERIALIZER = "pickle"
#    Pyro4.config.REQUIRE_EXPOSE = False
#        
#    daemon = Pyro4.Daemon(host = host)
##    daemon._pyroHmacKey = "9tzuWZ!hkKR$xM?@E5gDpLQ8d7T45>~e"
#
#    kt2450 = keith2450(address = 'GPIB0::18::INSTR', volt_step_lim = 0.01, volt_high_lim = 10)
#    uri_2450 = daemon.register(kt2450, objectId = "Keithley2450")
#    ns.register("Keithley2450", uri_2450)
#    print("Ready. Object uri = ", uri_2450)
#
##    kt2400 = keith2400(address = 'GPIB0::12::INSTR', volt_step_lim = 0.01, volt_high_lim = 16)
##    uri_2400 = daemon.register(kt2400, objectId = "Keithley2400")
##     ns.register("Keithley2400", uri_2400)    
##     print("Ready. Object uri = ", uri_2400)
    
#    daemon.requestLoop()
    
#if __name__ == '__main__':
##    RunServer()
#    RunServer(host = "localhost")
    
if __name__ == '__main__':
    object_dict = {
            'Keithley2400': keith2400('GPIB0::29::INSTR', volt_step_lim = 0.05, volt_high_lim = 8),           
    }
#    nw_utils.RunServer(object_dict, host = 'localhost')
    nw_utils.RunServer(object_dict, host = config.HOSTNAME + '.dhcp-int.phys.ethz.ch')
    