# -*- coding: utf-8 -*-
"""
Created on Fri Aug 04 11:03:03 2017

@author: Yuya Shimazaki
"""

from __future__ import division, print_function
import pyvisa as visa
import numpy as np
import time
import pandas as pd
import warnings
from builtins import input
import os,sys

sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base\zq_drivers\pyro_nw')
import nw_utils as nw_utils

import logging
logging.basicConfig(
    filename = os.path.splitext(__file__)[0] + '_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s')



import logging
logging.basicConfig(
    filename = os.path.splitext(__file__)[0] + '_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s')



'''
TODO: 
    - mark all private variables with _variable as private
    - make tests for all functions with assertions that we can run
    - make a nice tutorial
    - finish the VS and VM functions
    - make class decorators work with @classmethod or so
    - it claims that we're in ascii but it seems we're actually in binary mode
'''

def default_setting(init_func):
    def _init_func(self, *args, **kwargs):
        init_func(self, *args, **kwargs)
        
        self.set_average_num(50)
        
        for chnum in self.SMU_channels:
            ch = getattr(self,'SMU{}'.format(chnum))
            ch.set_voltage_limit(1)
            ch.set_voltage_safe_step(0.01)
            ch.set_current_compliance(1e-9)
            ch.set_voltage_output_range(10)
        
        for chnum in self.VSVM_channels:
            ch = getattr(self,'VS{}'.format(chnum))
            ch.set_voltage_limit(1)
            ch.set_voltage_safe_step(0.01)
#            ch.set_voltage_output_range(10) # TODO Alex: why does this throw an error?
        
        for chnum in self.HCU_channels:
            print('NOT IMPLEMENTED')
        
        for chnum in self.HVU_channels:
            print('NOT IMPLEMENTED')
        
    return _init_func
    

def sample_safety_warning(operation):
    def _operation(self, *args, **kwargs):
        if not self.is_warning_called:
            print('WARNING! This operation may harm your sample.\nDisconnect your sample from HP4142B!')
            ans = input('Is your sample disconnected? [y/n]\n')
            if ans in ['y', 'Y']:
                self.is_warning_called = True
                operation(self, *args, **kwargs)
                self.is_warning_called = False
            else:
                print('\nOperation Aborted!\n')
        else:
           operation(self, *args, **kwargs)
    return _operation

class HP4142B(object):
    @default_setting
    def __init__(self, GPIB_resource_name, initialize = True):
        self._address = GPIB_resource_name
        self._rm = visa.ResourceManager()
        self._inst = self._rm.open_resource(self._address,timeout=2000)
        self.inst = self._inst
        self.SMU = []
        self.SMU_A = []
        self.SMU_B = []
        self.HCU = []
        self.HVU = []
        self.VSVM = []
        self.AFU = []
        self.SMU_channels = []
        self.VSVM_channels = []
        self.HVU_channels = []
        self.HCU_channels = []
        self.channels = []
        self.data_format = "binary" # TODO changed from ASCII. our default is binary (see startup)
        self.is_warning_called = False
        if initialize:
            self.startup_HP4142B()
        else:
            self.identify_units()
            self.create_channels()



    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(type(self), self).__setattr__(name, value)
        else:
            internal_name = '__' + name
            super(type(self), self).__setattr__(internal_name, value)
            def fget(self): return getattr(self, internal_name)
            def fset(self, value): super(type(self), self).__setattr__(internal_name, value)
            def fdel(self): delattr(self, internal_name)
            setattr(type(self), name, property(fget, fset, fdel))

    def __rawWrite__(self, command):
        # print(command)
        logging.debug('__rawWrite__: {}'.format(command.__repr__()))
        self._inst.write(command)
    
    def __rawAsk__(self, command):
        logging.debug('__rawAsk__: {}'.format(command.__repr__()))
        ret = self._inst.query(command)
        logging.debug('ret = {}'.format(ret.__repr__()))
        return ret
    
    def __rawRead__(self):
        logging.debug('__rawRead__')
        ret = self._inst.read_raw()
        logging.debug('ret = {}'.format(ret.__repr__()))
        return ret
    
    def create_channels(self):
        self.identify_units()
        for channel in self.SMU_A:
            name = 'SMU'+str(channel) # TODO: str/bytes
            # TODO: eliminate class SMU_A and instead create an SMU here with type 'SMU_A'
            setattr(self, name, SMU_A(self, channel))
            
        for channel in self.SMU_B:
            name = 'SMU'+str(channel)
            setattr(self, name, SMU_B(self, channel))
        
        for channel in self.VSVM_channels:
            name = 'VS'+str(channel)
            setattr(self, name, VS(self, channel)) 
            name = 'VM'+str(channel)
            setattr(self, name, VM(self, channel)) 
            
    def identify_units(self):
        unt = self.__rawAsk__("UNT?") # Modified 'UNT? 0' to 'UNT?'. There was an error with new HP4142B.
        unt = unt.split(';')
        for x, xx in enumerate(unt):
            unt[x] = xx.split(',')
        units = dict(unt)
        units.pop('0', None) #delete the "0", remainder: the existing devices
        for device in units.keys():
            units[device] = [x+1 for x in range(len(unt)) if device in unt[x][0]]
        #now we have a dictionary which contains as keys the device names (e.g. "HP41421B") and as values a list with the slots in which these devices are

        self.SMU = []
        self.SMU_channels = []
        self.SMU_A = []
        self.SMU_B = []
        self.HCU = []
        self.HVU = []
        self.VSVM = []
        self.AFU = []
        
        if 'HP41421B' in units:
            self.SMU = self.SMU + units['HP41421B']
            self.SMU_B = units['HP41421B']
        if 'HP41420A' in units:
            self.SMU = self.SMU + units['HP41420A']
            self.SMU_A = units['HP41420A']
        if 'HP41422A' in units:
            self.HCU = self.HCU + units['HP41422A']
        if 'HP41423A' in units:
            self.HVU = self.HVU + units['HP41423A']
        if 'HP41424A' in units:
            self.VSVM = self.VSVM + units['HP41424A']
        if 'HP41425A' in units:
            self.AFU = self.AFU + units['HP41425A']
        self.SMU.sort()
        
        self.SMU_channels = self.SMU
        self.HCU_channels = self.HCU
        self.HVU_channels = self.HVU
        self.VSVM_channels = [item for x in self.VSVM for item in list((x+10,x+20))]
        
        self.channels = self.SMU_channels + self.HCU_channels + self.HVU_channels + self.VSVM_channels
        self.channels.sort()
        
        # print channels
        attrs = ['SMU', 'SMU_A', 'SMU_B', 'SMU_channels', 'HCU', 'HVU', 'VSVM', 'AFU', 'SMU_channels', 'VSVM_channels', 'HVU_channels', 'HCU_channels', 'channels']
        print('\nChannels: ')
        for attr in attrs:
            print( '%s: %s' %(attr, getattr(self, attr)))
        

    @sample_safety_warning
    @default_setting
    def startup_HP4142B(self):
        self.reset_HP()
        self.set_binary_output()
        self.auto_calibration_off()
        self.set_filter_on()
        self.output_on()
        self.identify_units()
        self.create_channels()
    
    @sample_safety_warning
    def output_on(self):
        self.identify_units()
        self._inst.write("CN")
    
    @sample_safety_warning        
    def output_off(self):
        self.identify_units()
        self._inst.write("CL")
        
    def set_average_num(self, average_num):
        self.__rawWrite__("AV" + str(int(average_num)))
 
    def set_filter_on(self):
        self.set_filters('on')
        
    def set_filter_off(self):
        self.set_filters('off')

    def set_filters(self, state = 'on'):
        if state == 'on':
            self.__rawWrite__("FL1")
        else:
            self.__rawWrite__("FL0")
    
    def auto_calibration_off(self):
        self.auto_calibration("off")
        
    def auto_calibration_on(self):
        self.auto_calibration("on")
        
    def auto_calibration(self, state = "off"):
        if state == 'on':
            self.__rawWrite__("CM 1")
        else:
            self.__rawWrite__("CM 0")    
            
    def reset_HP(self):
        self.__rawWrite__("AB") #abort all operations
        self.__rawWrite__("*RST") #reset device
            
    def clear_buffer(self):
        self.__rawWrite__("BC")
    
    def set_binary_output(self):
        self.set_output_data_format("binary")
        
    def set_ascii_output(self):
        self.set_output_data_format("ASCII")
        
    def set_output_data_format(self, data_format = "binary"):
        if data_format == "ASCII":
            self.__rawWrite__("FMT1,0")
            self.data_format = "ASCII"
        elif data_format == "ASCII_nohead":
            self.__rawWrite__("FMT2,0")
            self.data_format = "ASCII_nohead"
        elif data_format == "binary":
            self.__rawWrite__("FMT3,0")
            self.data_format = "binary"
        elif data_format == "binary_short":
            self.__rawWrite__("FMT4,0")
            self.data_format = "binary_short"
        elif data_format == "ASCII_comma":
            self.__rawWrite__("FMT5,0")
            self.data_format = "ASCII_comma"
    
    def get_SMU_settings(self):
        SMU_settings = pd.DataFrame()
        for channel in self.SMU_channels:
            channel_name ="SMU" + str(channel)
            ret_ser = getattr(getattr(self, channel_name), "get_unit_settings")()
            ret_df = pd.DataFrame({channel_name: ret_ser})
            if len(SMU_settings.index) == 0:
                SMU_settings = ret_df
            else:
                SMU_settings = SMU_settings.join(ret_df)
        return SMU_settings
    
    def get_SMU_output(self):
        ret_df = self.get_SMU_settings()
        return ret_df.loc['Output Value']
    
    # TODO: implement this in same function for VSVM?
    def get_VSVM_settings():
        pass # TODO: do for VS and VM!
#        SMU_settings = pd.DataFrame()
#        for channel in self.VSVM_channels:
#            channel_name ="SMU" + str(channel)
#            ret_ser = getattr(getattr(self, channel_name), "get_unit_settings")()
#            ret_df = pd.DataFrame({channel_name: ret_ser})
#            if len(SMU_settings.index) == 0:
#                SMU_settings = ret_df
#            else:
#                SMU_settings = SMU_settings.join(ret_df)
#        return SMU_settings
    
    def get_VSVM_output():
        pass
#        ret_df = self.get_SMU_settings()
#        return ret_df.loc['Output Value']
    

class Channel(object):
    def __init__(self, hp4142b, channel_type, channel):
        self.channel_type = channel_type
        self.channel = channel
        self.hp4142b = hp4142b
        #self._inst = hp4142b._inst
    
    def __rawWrite__(self, command):
        # print(command)
        self.hp4142b.__rawWrite__(command)

    def __rawAsk__(self, command):
        return self.hp4142b.__rawAsk__(command)

    def __rawRead__(self):
        return self.hp4142b.__rawRead__() 
        
       
    def _read_IV(self, command):
#        print('command: %s'%repr(command)) # debug
        self.__rawWrite__(command)
        reading = ''
        while len(reading) < 6 and int(self.__rawAsk__("NUB?")) > 0:           
            reading += self.__rawRead__().decode('latin-1')  # Python3
#            reading += self.__rawRead__() # Python2
#        print(repr(reading)) # debug
        if len(reading) == 6:
            reading = reading[:4]
        if self.hp4142b.data_format == 'ASCII':
            conversion = self._convert_from_ascii(reading)
            if conversion[6] == 'unexpected ASCII data format':
                conversion = self._convert_from_binary(reading)
            return conversion[4]
        elif self.hp4142b.data_format == 'binary':
            conversion = self._convert_from_binary(reading)
            if conversion[6] == 'unexpected binary data format':
                conversion = self._convert_from_ascii(reading)
            # print(self.channel) # TODO debug
            if not conversion[5] == self.channel:
                warnings.warn('_read_IV: addressed channel %s but got %s instead'%(conversion[5],self.channel)) # TODO check debug
                #raise ValueError('_read_IV: addressed channel %s but got %s instead'%(conversion[5],self.channel)) # TODO check debug
            return conversion[4]
    
    def _current_range_format(self, x):
        return "{:.0E}".format(x)

    def _voltage_to_range_setting(self, voltage='Auto'):

        voltage_range_setting = {'Auto':'0','0.2':'10','2':'11','20':'12','40':'13','100':'14','200':'15','500':'16','1000':'17'}
        if voltage == 'Auto':
            return '0'
        voltage_keys_dict = {
            'SMU_A': np.array([2,20,40,100,200]),
            'SMU_B': np.array([2,20,40,100]),
            'VS': np.array([2,20,40]),
            'VM': np.array([0.2,2,20,40])
            }
        voltage_keys = voltage_keys_dict[self.channel_type]
        vk = voltage_keys - abs(float(voltage))
        #vk.clip(0)
        idx = np.where(vk>=0)[0]
        if len(idx) == 0:
            # BEFORE: if we set a source to a too high voltage limit,
            # it just goes to auto range! This is not the behaviour that we want,
            # rather for safety it should go to the highest range or throw an error
            print('invalid voltage range! setting highest range')
            idx = [len(voltage_keys)-1]
        return voltage_range_setting[str(voltage_keys[idx[0]])]

    def _range_setting_to_voltage(self,range_setting):
        voltage_range_setting = {'0':'Auto','11':'2','12':'20','13':'40','14':'100','15':'200','16':'500','17':'1000'}
        #a voltage value of 0 defined as auto_ranging
        return voltage_range_setting[range_setting]
    
    def _current_to_range_setting(self, current='Auto'):
        current_range_setting = {'Auto':'0',
                                 self._current_range_format(1e-9):'11',
                                 self._current_range_format(1e-8):'12',
                                 self._current_range_format(1e-7):'13',
                                 self._current_range_format(1e-6):'14',
                                 self._current_range_format(1e-5):'15',
                                 self._current_range_format(1e-4):'16',
                                 self._current_range_format(1e-3):'17',
                                 self._current_range_format(1e-2):'18',
                                 self._current_range_format(1e-1):'19',
                                 self._current_range_format(1):'20',
                                 self._current_range_format(10):'21'}
        if current == 'Auto':
            return '0'
        current_keys_dict = {
            'SMU_A': np.array([1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1]),
            'SMU_B': np.array([1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]),
            'VS': np.array([1e-3, 1e-2, 1e-1, 1, 10])
            }
        current_keys = current_keys_dict[self.channel_type]
        ck = current_keys - abs(float(current))
        idx = np.where(ck>=0)[0]
        if len(idx) == 0:
            return '0'
        else:
            return current_range_setting[self._current_range_format(current_keys[idx[0]])]

    def _range_setting_to_current(self,range_setting):
        current_range_setting = {'0':'Auto','11':'1E-9','12':'1E-8','13':'1E-7','14':'1E-6','15':'1E-5','16':'1E-4','17':'1E-3','18':'1E-2','19':'1E-1','20':'1'}
        #a current value of 0 defined as auto_ranging
        return current_range_setting[range_setting]    

    def _convert_from_ascii(self,ascii_data):
        #ASCII as defined below is assumed, i.e. with header: self.set_ascii_output()
        if len(ascii_data)%15 != 0:
            return([False, False, 0, 10, float('NaN'), 0, "unexpected ASCII data format"])

        ascii_error = ascii_data[0]  #status in HP docu, indicates status of measurement
        if ascii_error == 'N': #N - no error
            status = 'N: normal data, no error'
            error_code = 0
            is_measurement_data = True
        elif ascii_error == 'T': #T
            status = 'T: another channel reached compliance limit'
            error_code = 1
            is_measurement_data = True
        elif ascii_error == 'C': #C
            status = 'C: this channel reached compliance limit'
            error_code = 2
            is_measurement_data = True
        elif ascii_error == 'V': #V
            status = 'V: overflow'
            error_code = 3
            is_measurement_data = True
        elif ascii_error == 'X': #X
            status = 'X: SMU/HVU oscillating'
            error_code = 4
            is_measurement_data = True
        elif ascii_error == 'F': #F
            status = 'F: HVU output not settled'
            error_code = 5
            is_measurement_data = True
        elif ascii_error == 'G': #G
            status = 'G: check manual'
            error_code = 6
            is_measurement_data = True
        elif ascii_error == 'S': #S
            status = 'S: check manual'
            error_code = 7
            is_measurement_data = True
        elif ascii_error == 'W': #W
            status = 'W: sweep source - first or intermediate sweep step'
            error_code = 1
            is_measurement_data = False
        elif ascii_error == 'E': #E
            status = 'E: sweep source - final sweep step'
            error_code = 2
            is_measurement_data = False
                        
        channel = ascii_data[1]
        if channel == 'A':
            channel_number = 1
        elif channel == 'B':
            channel_number = 2
        elif channel == 'C':
            channel_number = 3
        elif channel == 'D':
            channel_number = 4
        elif channel == 'E':
            channel_number = 5
        elif channel == 'F':
            channel_number = 6
        elif channel == 'G':
            channel_number = 7
        elif channel == 'H':
            channel_number = 8
        elif channel == 'I':
            channel_number = 11
        elif channel == 'J':
            channel_number = 12
        elif channel == 'K':
            channel_number = 13
        elif channel == 'L':
            channel_number = 14
        elif channel == 'M':
            channel_number = 15
        elif channel == 'N':
            channel_number = 16
        elif channel == 'O':
            channel_number = 17
        elif channel == 'P':
            channel_number = 18
        elif channel == 'Q':
            channel_number = 21
        elif channel == 'R':
            channel_number = 22
        elif channel == 'S':
            channel_number = 23
        elif channel == 'T':
            channel_number = 24
        elif channel == 'U':
            channel_number = 25
        elif channel == 'V':
            channel_number = 26
        elif channel == 'W':
            channel_number = 27
        elif channel == 'X':
            channel_number = 28
        
        if ascii_data[2] == 'V':
            is_voltage_data = True #voltage data
        else: # 'I'
            is_voltage_data = False #current data
            
        value = ascii_data[3:len(ascii_data)]
        reading = float(value)
        
        #if not error_code==0: # debug
            #print('_convert_from_asci: %s'%status)
        #same output as with convert_from_binary but range_setting = 0 as it is not given in the ASCII output
        return([is_measurement_data, is_voltage_data, 0, error_code, reading, channel_number, status])        
        

    
    def _convert_from_binary(self,binary_data):
        #binary as below is assumed, with normal termination: self.set_binary_output()
        #to convert bit strings to int: int('1100101',2)
        # the other way around: bin(number)

        if len(binary_data)%4 != 0: #length of binary data is 4 byte
            return([False, False, 0, 10, float('NaN'), 0, "unexpected binary data format"]) #return dummy values and indicate error
            
        byte_1 = ord(binary_data[0])
        byte_2 = ord(binary_data[1])
        byte_3 = ord(binary_data[2])
        byte_4 = ord(binary_data[3])        
        #print bin(byte_1), "  ", bin(byte_2), "  ", bin(byte_3), "  ", bin(byte_4)

        #measurement or souce data
        A = byte_1 & 128     #A in HP documentation
        if A == 128: #bit 7 is 1
            is_measurement_data = True
        else: #bit 7 is 0
            is_measurement_data = False #sweep source data
            
        #current or voltage data 
        B = byte_1 & 64      #B in HP documentation
        
        if B == 64: #bit 6 is 1
            is_voltage_data = False #current data
        else: #bit 6 is 0
            is_voltage_data = True #voltage data
            
        #measurement / output range
        C = ((byte_1 & (2+4+8+16+32)) >> 1)    #C in HP documentation        
        if is_voltage_data:
            voltage_range = {10:0.2, 11:2, 12:20, 13:40, 14:100, 15:200, 16:500, 17:1000}
            range_setting = voltage_range[C]
        else:
            current_range = {11:1e-9, 12:1e-8, 13:1e-7, 14:1e-6, 15:1e-5, 16:1e-4, 17:1e-3, 18:1e-2, 19:1e-1, 20:1, 21:10}
            range_setting = current_range[C]

        # evaluate error code
        error_code = ((byte_4 & (32+64+128)) >> 5) #E in HP docu, indicates status of measurement
        if error_code == 0: #N - no error
            status = 'N: normal data, no error'
        elif error_code == 1 and is_measurement_data: #T
            status = 'T: another channel reached compliance limit'
        elif error_code == 1 and not is_measurement_data: #T
            status = 'W: sweep source - first or intermediate sweep step'
        elif error_code == 2 and is_measurement_data: #C
            status = 'C: this channel reached compliance limit'
        elif error_code == 2 and not is_measurement_data: #C
            status = 'E: sweep source - final sweep step'
        elif error_code == 3: #V
            status = 'V: overflow'
        elif error_code == 4: #X
            status = 'X: SMU/HVU oscillating'
        elif error_code == 5: #F
            status = 'F: HVU output not settled'
        elif error_code == 6: #G
            status = 'G: check manual'
        elif error_code == 7: #S
            status = 'S: check manual'
        
        #measurement data
        D_umb = byte_1 & 1       #highest order bit of D in documentation, sign of measurement value        
        D_value = (byte_2 << 8) | (byte_3)       
        if D_umb == 0: #positive value
            D_counts = D_value
        else: #twos complement (17bit), negative value
            D_counts = D_value - 65536
        if error_code == 3: #error V, overflow
            D_counts = 65536    #E = 3, indicating an overflow: channel output exceeds measurement range                   

        if is_measurement_data:
            reading = (D_counts*range_setting)/50000.0
        else:
            reading = (D_counts*range_setting)/20000.0
            
        channel_number = byte_4 & (1+2+4+8+16)     #F in HP documentation, channel number
         
        if not error_code==0: # debug
            print('_convert_from_binary')
            print('is_measurement_data: %s'%(is_measurement_data))
            print('is_voltage_data: %s'%(is_voltage_data))
            print('range_setting: %s'%(range_setting))
            print('error_code: %s'%(error_code))
            print('reading: %s'%(reading))
            print('channel_number: %s'%(channel_number))
            print('status: %s'%(status))
        return([is_measurement_data, is_voltage_data, range_setting, error_code, reading, channel_number, status])


    # TODO this is defined in all classes 
    # - maybe define outside as it's a common wrapper function? put it in channel? why doesn't it work then? classmethod something
    def update(operation):
        def _operation(self_obj, *args, **kwargs):
            ans = operation(self_obj, *args, **kwargs)
            self_obj._update_channel_info()
            return ans # it's ok to return None, that's the default
        return _operation
    
    # TODO this is defined in all classes 
    # - maybe define outside as it's a common function?
    # need to extract SMU from an SMU channel and VM from a VM channel etc - if and else is ugly?
    '''
    right now there's devices with channel type SMU_A and SMU_B and VM and VS
    SMU_As are called SMUX
    VMs are called VMXX - is that ok?
    hp has lists SMU_A and SMU_B, but no lists VM and VS - ok?
    or should just every object have a field where its name is stored?
    '''
    def _update_channel_info(self):
        if self.channel_type in ['SMU_A', 'SMU_B']:
            setattr(self.hp4142b, 'SMU' + str(self.channel), self)
        elif self.channel in ['VM', 'VS']:
            setattr(self.hp4142b, self.channel + str(self.channel), self)
        else:
            raise NotImplementedError('Not implemented!')
            

    #Check settings for output off, is return required?
    @update
    def get_unit_settings(self):
        logging.debug('get_unit_settings()')
        # TODO same as SMU
        channel_str = str(self.channel)
        reply = self.__rawAsk__(''.join(['*LRN? ',channel_str]))
        
        '''
        replies:
        SMU: [Device slot, output range, output value, compliance, compliance mode]
        VSVM: [Device slot, output range, output value; VM device, vm measuring mode]
        '''
        ret = {}
        if reply.startswith( ''.join(['CL',channel_str]) ): # TODO changed from reply==
            self.source_mode = None
            
            ret['Output Status']            = self.output_on                = False # TODO check and expand
            retindex = [
                 "Output Status"
                ]
        else:
            ret['Output Status']            = self.output_on                = True
            
            if self.channel in self.hp4142b.SMU_channels:
                [_, output_range, output_value, compliance, compliance_mode] = reply[2:].split(',')  
                ret['Output Value']         = self.output_value             = float( output_value )
                
                if reply[1] == 'V':
                    ret['Source Mode']      = self.source_mode              = 'Voltage'
                    ret['Output Range']     = self.voltage_output_range     = float(self._range_setting_to_voltage(output_range))
                    ret['Compliance']       = self.current_compliance       = float(compliance)
                    ret['Compliance Mode']  = self.current_compliance_mode  = float(compliance_mode)    
                    ret['Safe Step']        = self.voltage_safe_step
                    ret['High Limit']       = self.voltage_high_limit
                else: # 'C'
                    ret['Source Mode']      = self.source_mode              = 'Current'
                    ret['Output Range']     = self.current_output_range     = float(self._range_setting_to_current(output_range))
                    ret['Compliance']       = self.voltage_compliance       = float(compliance)
                    ret['Compliance Mode']  = self.voltage_compliance_mode  = float(compliance_mode)
                    ret['Safe Step']        = self.current_safe_step
                    ret['High Limit']       = self.current_high_limit
                
                retindex = [
                     "Source Mode",
                     "Output Value",
                     "Safe Step",
                     "High Limit",
                     "Output Range",
                     "Compliance",
                     "Compliance Mode",
                     "Output Status"
                    ]
            
            elif self.channel in self.hp4142b.VSVM_channels:
                [reply_VS, reply_VM] = reply.split(';')
                
                [_, output_range, output_value] = reply_VS[2:].split(',')
                ret['Output Range']         = self.voltage_output_range     = float(self._range_setting_to_voltage(output_range))
                ret['Output Value']         = self.output_value             = float(output_value)
                vm_mode = reply_VM[2:].split(',')[1][0]
                if vm_mode == '1':
                    ret['VM Mode']          = self.vm_mode                  = 'grounded'
                elif vm_mode == '2':
                    ret['VM Mode']          = self.vm_mode                  = 'differential'
                if self.channel_type == 'VS':
                    ret['Safe Step']            = self.voltage_safe_step
                    ret['High Limit']           = self.voltage_high_limit
                    
                retindex = [
                     "Output Value",
                     "Safe Step",
                     "High Limit",
                     "Output Range",
                     "VM Mode",
                     "Output Status"
                    ]
            else:
                raise NotImplementedError('Only VSVM and SMU units are implemented!')
                
        return pd.Series(ret, index=retindex)

class SMU(Channel):
    def __init__(self, hp4142b, channel_type, channel): # source_mode = 'Voltage' or 'Current'
        super(SMU, self).__init__(hp4142b, channel_type, channel)
        self.voltage_safe_step = 0.05
        self.voltage_high_limit = 100
        self.voltage_low_limit = -100
        self.current_safe_step = 1e-9
        self.current_high_limit = 10e-6
        self.get_unit_settings()
        
    
#    def initialize(self, source_mode, output_range):
#        self.set_source_mode(source_mode)
    
    # TODO this is defined in all classes 
    # - maybe define outside as it's a common wrapper function? put it in channel? why doesn't it work then? classmethod something
    def update(operation):
        def _operation(self_obj, *args, **kwargs):
            ans = operation(self_obj, *args, **kwargs)
            self_obj._update_channel_info()
            if ans is not None:
                return ans
        return _operation

    
    # TODO this is defined in all classes 
    # - maybe define outside as it's a common function?
    # need to extract SMU from an SMU channel and VM from a VM channel etc - if and else is ugly?
    def _update_channel_info(self):
        setattr(self.hp4142b, 'SMU' + str(self.channel), self)
        

    def update_hardware(operation): 
        def _operation(self_obj, *args, **kwargs):
            if self_obj.source_mode == 'Voltage':
                output_voltage = self_obj.get_voltage()                
                ans = operation(self_obj, *args, **kwargs)
                self_obj._update_channel_info()
                self_obj._set_raw_voltage(output_voltage)
                if ans is not None:
                    return ans
            elif self_obj.source_mode == 'Current':
                output_current = self_obj.get_current()                
                ans = operation(self_obj, *args, **kwargs)
                self_obj._update_channel_info()
                self_obj._set_raw_current(output_current)
                if ans is not None:
                    return ans         
        return _operation

    
    @update
    def get_voltage_safe_step(self):
        return self.voltage_safe_step
    
    @update
    def set_voltage_safe_step(self, voltage):
        self.voltage_safe_step = voltage
    
    @update
    def get_voltage_limit(self):
        return (self.voltage_high_limit, self.voltage_low_limit)
    
    @update
    def set_voltage_limit(self, *limits):
        '''
        set the limits. input either length 1 or 2
        '''
        if len(limits) == 1:
            self.voltage_high_limit = abs(limits[0])
            self.voltage_low_limit = -abs(limits[0])
        else:
            self.voltage_high_limit = np.max(limits)
            self.voltage_low_limit = np.min(limits)

        
    @update
    def get_current_safe_step(self):
        return self.current_safe_step
    
    @update
    def set_current_safe_step(self, current):
        self.current_safe_step = current
    
    @update
    def get_current_high_limit(self):
        return self.current_high_limit
    
    @update
    def set_current_high_limit(self, current):
        self.current_high_limit = current
    
    #Done
    @update
    def get_output_status(self):
        self.get_unit_settings()
        return self.output_on
        
    # Interlock required
    @update
    def set_output_status(self, output_on):
        output_on_options = [True, False]
        if output_on not in output_on_options:
            raise ValueError("SMU.set_output_status: output_on must be True or False")
        self.get_unit_settings()
        if self.output_on != output_on:
            if output_on:
                self.__rawWrite__("CN {}".format(self.channel))
                self.output_on = True
            else:
                self.__rawWrite__("CL {}".format(self.channel))
                self.output_on = False
    
    #Done
    @update
    def get_source_mode(self):
        self.get_unit_settings()
        return self.source_mode
        
    # Interlock required
    # Debug required
    @update
    def set_source_mode(self, source_mode): # source_mode = 'Voltage' or 'Current'
        source_mode_options = ['Voltage', 'Current']
        if source_mode not in source_mode_options:
            raise ValueError("SMU.set_source_mode: source_mode must be 'Voltage' or 'Current'")
        self.get_unit_settings()
        if self.source_mode != source_mode:
            if self.source_mode == "Voltage":
                self.set_voltage(0)             #Set voltage to zero before change
                self.source_mode = source_mode
                self._update_channel_info()
                self.__rawWrite__(''.join([
                    'DI',
                    '{}'.format(self.channel),',',
                    self._current_to_range_setting('Auto'),',',
                    '{}'.format(0),',',
                    '{}'.format(100),',','0']))
            elif self.source_mode == "Current":
                self.set_current(0)             #Set current to zero before change
                self.source_mode = source_mode
                self._update_channel_info()
                self.__rawWrite__(''.join([
                    'DV',
                    '{}'.format(self.channel),',',
                    self._voltage_to_range_setting('Auto'),',',
                    '{}'.format(0),',',
                    '{}'.format(1e-9),',','0']))
        print( self.get_unit_settings() )
    
    
    # Safety decorator for voltage sweeep
    def safe_voltage_sweep(set_voltage_func):
        def safe_voltage_wrapper(self, voltage):
            pv = self.get_voltage()
            sv = voltage
            steplim = self.voltage_safe_step
            if sv > self.voltage_high_limit or sv < self.voltage_low_limit:
                sv = pv
                print("ERROR : EXCEEDING VOLTAGE LIMIT")
            if abs(sv - pv) > steplim:
                stepnum = int(np.ceil(abs(pv - sv)/(1.0*steplim)) + 1)
                smooth_move_vals = np.linspace(pv, sv, stepnum)
#                pbar = tqdm.tqdm(smooth_move_vals)
#                for val in pbar:
                for val in smooth_move_vals:
                    set_voltage_func(self, val)
                    time.sleep(0.025)
#                    pbar.set_description("{:6.2f} V".format(self.get_voltage()))
                    time.sleep(0.025)
            set_voltage_func(self, sv)             
        return safe_voltage_wrapper
    
    #Done
    @update
    def get_voltage(self):
        logging.debug('get_voltage()')
        if self.source_mode == 'Voltage':
            self.get_unit_settings()
            return self.output_value
        elif self.source_mode == 'Current':
            command = ''.join([
                    'TV',
                    '{}'.format(self.channel),', 0']) # TODO: added ,', 0' - necessary?
            return self._read_IV(command)

    @safe_voltage_sweep
    def set_voltage(self, voltage):
        logging.debug('set_voltage(): {}'.format(voltage))
        if self.source_mode == 'Voltage':
            self.__rawWrite__(''.join([
                'DV',
                '{}'.format(self.channel),',',
                self._voltage_to_range_setting(self.voltage_output_range),',',
                '{}'.format(voltage),',',
                '{}'.format(self.current_compliance),',','0']))
        else:
            raise RuntimeError("SMU.set_voltage: source_mode is not 'Voltage'")

    def _set_raw_voltage(self, voltage):
        if self.source_mode == 'Voltage':
            self.__rawWrite__(''.join([
                'DV','{}'.format(self.channel),',',
                self._voltage_to_range_setting(self.voltage_output_range),',',
                '{}'.format(voltage),',',
                '{}'.format(self.current_compliance),',','0']))
        else:
            raise RuntimeError("SMU.set_voltage: source_mode is not 'Voltage'")
           
    #Done
    @update
    def get_voltage_output_range(self):
        if self.source_mode == 'Voltage':
            self.get_unit_settings()
            return self.voltage_output_range
        else:
            raise RuntimeError("SMU.get_voltage_output_range: source_mode is not 'Voltage'")
    
    #Done
    @update_hardware
    def set_voltage_output_range(self, voltage_output_range):
        if self.source_mode == 'Voltage':
            self.voltage_output_range = voltage_output_range
        else:
            raise RuntimeError("SMU.set_voltage_output_range: source_mode is not 'Voltage'")

    #Done         
    @update
    def get_current_compliance(self):
        if self.source_mode == 'Voltage':
            self.get_unit_settings()
            return self.current_compliance
        else:
            raise RuntimeError("SMU.get_current_compliance: source_mode is not 'Voltage'")

    #Done
    @update_hardware
    def set_current_compliance(self, current_compliance):
        if self.source_mode == 'Voltage':
            self.current_compliance = current_compliance
        else:
            raise RuntimeError("SMU.set_current_compliance: source_mode is not 'Voltage'")


    # Safety decorator for curent sweeep
    def safe_current_sweep(set_current_func):
        def safe_current_wrapper(self, current):
            pv = self.get_current()
            sv = current
            steplim = self.current_safe_step
            if abs(sv) > self.current_high_limit:
                sv = pv
                print("ERROR : EXCEEDING HIGH CURRENT LIMIT " + str(self.current_high_limit) + "A!")
            if abs(sv - pv) > steplim:
                stepnum = int(np.ceil(abs(pv - sv)/(1.0*steplim)) + 1)
                smooth_move_vals = np.linspace(pv, sv, stepnum)
#                pbar = tqdm.tqdm(smooth_move_vals)
#                for val in pbar:
                for val in smooth_move_vals:
                    set_current_func(self, val)
                    time.sleep(0.025)
#                    pbar.set_description("{:6.2f} A".format(self.get_current()))
                    time.sleep(0.025)
            set_current_func(self, sv)             
        return safe_current_wrapper


    #Done
    # TODO that's the same as get_voltage!? ah no, there's a 0?... 
    @update
    def get_current(self):
        if self.source_mode == 'Current':
            self.get_unit_settings() 
            return self.output_value
        elif self.source_mode == 'Voltage':
            command = ''.join([
                    'TI ',
                    '{}'.format(self.channel),', 0'])
            return self._read_IV(command)

    #Done
    @safe_current_sweep
    def set_current(self, current):
        if self.source_mode == 'Current':
            self.__rawWrite__(''.join([
                'DI',
                '{}'.format(self.channel),',',
                self._current_to_range_setting(self.current_output_range),',',
                '{}'.format(current),',',
                '{}'.format(self.voltage_compliance),',','0']))
        else:
            raise RuntimeError("SMU.set_current: source_mode is not 'Current'")
            
    def _set_raw_current(self, current):
        if self.source_mode == 'Current':
            self.__rawWrite__(''.join([
                'DI',
                '{}'.format(self.channel),',',
                self._current_to_range_setting(self.current_output_range),',',
                '{}'.format(current),',',
                '{}'.format(self.voltage_compliance),',','0']))
        else:
            raise RuntimeError("SMU.set_current: source_mode is not 'Current'")

    #Done
    @update
    def get_current_output_range(self):
        if self.source_mode == 'Current':
            self.get_unit_settings()
            return self.current_output_range
        else:
            raise RuntimeError("SMU.get_current_output_range: source_mode is not 'Current'")
    
    #Done
    @update_hardware
    def set_current_output_range(self, current_output_range):
        if self.source_mode == 'Current':
            self.current_output_range = current_output_range
        else:
            raise RuntimeError("SMU.set_current_output_range: source_mode is not 'Current'")

    #Done       
    @update
    def get_voltage_compliance(self):
        if self.source_mode == 'Current':
            self.get_unit_settings()
            return self.voltage_compliance
        else:
            raise RuntimeError("SMU.get_voltage_compliance: source_mode is not 'Current'")

    #Done
    @update
    def set_voltage_compliance(self, voltage_compliance):
        if self.source_mode == 'Current':
            output_current = self.get_current()
            self.voltage_compliance = voltage_compliance
            self.set_current(output_current)
        else:
            raise RuntimeError("SMU.set_voltage_compliance: source_mode is not 'Current'")   
        

            

#TODO: eliminate class SMU_A and instead create an SMU with type 'SMU_A' above
class SMU_A(SMU):
    def __init__(self, hp4142b, channel):
        super(SMU_A, self).__init__(hp4142b, 'SMU_A', channel)

#TODO: eliminate class SMU_A and instead create an SMU with type 'SMU_A' above  
class SMU_B(SMU):
    def __init__(self, hp4142b, channel):
        super(SMU_B, self).__init__(hp4142b, 'SMU_B', channel)

    
class VM(Channel):
    '''
    NO: have a common get_unit_settings()
    but have different class variables per class
    
    
    Driver philosophy: Have the same parameters for all VSVM and SMU
    But set the parameters in the init function such that the functions perform correctly
    All functions check which unit it is and then adjust their behaviour
    This is consistent with the manual that for all functions explains the different behaviour
    THUS: program all functions in a way that they can be copied to CHANNEL class!
    
    VS: no current source mode, no current compliance
    '''
    def __init__(self, hp4142b, channel):
        super(VM, self).__init__(hp4142b, 'VM', channel)
        
        self.voltage_measurement_range = None
        self.vm_mode = None # VM specific: differential or grounded measurement
        self.output_on = None
                
        self.get_unit_settings()
        
        # TODO: put this in init decorator
        self.set_vm_mode('grounded')
        self.set_voltage_measurement_range('Auto')
    
    
        # TODO this is defined in all classes 
    # - maybe define outside as it's a common function?
    # need to extract SMU from an SMU channel and VM from a VM channel etc - if and else is ugly?
    def _update_channel_info(self):
        setattr(self.hp4142b, 'VM' + str(self.channel), self)
        
    # TODO this is defined in all classes 
    # - maybe define outside as it's a common wrapper function? put it in channel? why doesn't it work then? classmethod something
    def update(operation):
        def _operation(self_obj, *args, **kwargs):
            ans = operation(self_obj, *args, **kwargs)
            self_obj._update_channel_info()
            if ans is not None:
                return ans
        return _operation
    
    # NOT same as SMU!
    @update
    def get_voltage(self):
        command = ''.join(['TV',
                           '{}'.format(self.channel),', 0']) # TODO: added ,', 0' - necessary?
        return self._read_IV(command)
    
    
    # NOT the same as SMU, we need to use the RV command because there's no VS avaliable?
    # We NEED to use @update because update_hardware uses setting a voltage in SMU, which we don't want
    @update
    def set_voltage_measurement_range(self, voltage_measurement_range):
        self.voltage_measurement_range = voltage_measurement_range
        self.__rawWrite__(''.join([
            'RV',
            '{}'.format(self.channel),',',
            self._voltage_to_range_setting(self.voltage_measurement_range) ]))
        # self.get_unit_settings() # TODO: necessary?
    
    # works
    @update
    def set_vm_mode(self, vm_mode):
        if vm_mode == 'grounded':
            self.__rawWrite__(''.join(['VM','{}'.format(self.channel),',','1']))
        elif vm_mode == 'differential':
            self.__rawWrite__(''.join(['VM','{}'.format(self.channel),',','2']))
        # self.get_unit_settings() # TODO: necessary?

class VS(Channel):
    # just a thinned down version of SMU class - how about incorporating it in SMU class instead of keeping it here separately?
    def __init__(self, hp4142b, channel):
        Channel.__init__(self, hp4142b, 'VS', channel)
        
        self.voltage_safe_step = 0.05
        self.voltage_high_limit = 40
        self.voltage_low_limit = 40
        self.get_unit_settings()

    def update(operation):
        def _operation(self_obj, *args, **kwargs):
            ans = operation(self_obj, *args, **kwargs)
            self_obj._update_channel_info()
            if ans is not None:
                return ans
        return _operation
        
    
    # TODO this is defined in all classes 
    # - maybe define outside as it's a common function?
    # need to extract SMU from an SMU channel and VM from a VM channel etc - if and else is ugly?
    def _update_channel_info(self):
        setattr(self.hp4142b, 'VS' + str(self.channel), self)
        

    def update_hardware(operation):  # TODO: removed source_mode
        def _operation(self_obj, *args, **kwargs):
                output_voltage = self_obj.get_voltage()                
                ans = operation(self_obj, *args, **kwargs)
                self_obj._update_channel_info()
                self_obj._set_raw_voltage(output_voltage)
                if ans is not None:
                    return ans     
        return _operation

    
    @update
    def get_voltage_safe_step(self):
        return self.voltage_safe_step
    
    @update
    def set_voltage_safe_step(self, voltage):
        self.voltage_safe_step = voltage
    
    @update
    def get_voltage_limit(self):
        return (self.voltage_high_limit, self.voltage_low_limit)
    
    @update
    def set_voltage_limit(self, *limits):
        '''
        set the limits. input either length 1 or 2
        '''
        if len(limits) == 1:
            self.voltage_high_limit = abs(limits[0])
            self.voltage_low_limit = -abs(limits[0])
        else:
            self.voltage_high_limit = np.max(limits)
            self.voltage_low_limit = np.min(limits)
    
    #Done
    @update
    def get_output_status(self):
        self.get_unit_settings()
        return self.output_on
        
    # Interlock required
    @update
    def set_output_status(self, output_on):
        output_on_options = [True, False]
        if output_on not in output_on_options:
            raise ValueError("SMU.set_output_status: output_on must be True or False")
        self.get_unit_settings()
        if self.output_on != output_on:
            if output_on:
                self.__rawWrite__("CN {}".format(self.channel))
                self.output_on = True
            else:
                self.__rawWrite__("CL {}".format(self.channel))
                self.output_on = False
    
    # TODO: Removed source mode settings, it's always a voltage source!
    
    
    # Safety decorator for voltage sweeep
    def safe_voltage_sweep(set_voltage_func):
        def safe_voltage_wrapper(self, voltage):
            pv = self.get_voltage()
            sv = voltage
            steplim = self.voltage_safe_step
            if sv > self.voltage_high_limit or sv < self.voltage_low_limit:
                sv = pv
                print("ERROR : EXCEEDING VOLTAGE LIMIT")
            if abs(sv - pv) > steplim:
                stepnum = np.int(np.ceil(abs(pv - sv)/(1.0*steplim)) + 1) # TODO deprecation warning for int
                smooth_move_vals = np.linspace(pv, sv, stepnum)
#                pbar = tqdm.tqdm(smooth_move_vals)
#                for val in pbar:
                for val in smooth_move_vals:
                    set_voltage_func(self, val)
                    time.sleep(0.025)
#                    pbar.set_description("{:6.2f} V".format(self.get_voltage()))
                    time.sleep(0.025)
            set_voltage_func(self, sv)             
        return safe_voltage_wrapper
    
    #Done
    @update
    def get_voltage(self):
        self.get_unit_settings()
        return self.output_value


    @safe_voltage_sweep
    def set_voltage(self, voltage):
        self.__rawWrite__(''.join([
            'DV',
            '{}'.format(self.channel),',',
            self._voltage_to_range_setting(self.voltage_output_range),',y',
            '{}'.format(voltage),',','0'])) # TODO took out current_compliance
                    

    def _set_raw_voltage(self, voltage):
        self.__rawWrite__(''.join([
            'DV','{}'.format(self.channel),',',
            self._voltage_to_range_setting(self.voltage_output_range),',',
            '{}'.format(voltage),',','0']))
    
    @update
    def get_current(self):
        # current measurement range is current output range 100mA so very 
        # rough measurement!
        command = ''.join([
                'TI',
                '{}'.format(self.channel),', 0'])
        return self._read_IV(command)
    
    #Done
    @update
    def get_voltage_output_range(self):
        self.get_unit_settings()
        return self.voltage_output_range
    
    #Done
    @update_hardware
    def set_voltage_output_range(self, voltage_output_range):
        self.voltage_output_range = voltage_output_range
    
    
if __name__ == '__main__':
    resource_name = 'GPIB0::17::INSTR'
    object_dict = {'HP4142B_r': HP4142B(resource_name)}
    nw_utils.RunServer(object_dict)