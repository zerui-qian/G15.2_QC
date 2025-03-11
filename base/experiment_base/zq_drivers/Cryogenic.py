# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 19:33:48 2017

@author: Patrick Knüppel, modified by Alex Popert
"""

import time
import re
import numpy as np

import visa, serial
import warnings, traceback




class MagnetController():
    """
    Use the function set_Bfield to ramp the magnetic field.
    To access the controller manually in local mode, use unlock.
    It is important to lock it in remote operation, since we have 
    not implemented handling the message buffer in a failsafe way.
    
    * By default, the ramp rate should be chosen suitable for:
      high magnetic fields & millikelvin temperatures & heater on!
    
    TO DO:
    Enable reversing the field polarity: Negative Bfields
    Possibilty for bugs when sending commands while ramping,
    e.g. set_Bfield inside tolarance while ramping across.
    """
    
    def __init__(self, address = 'COM5', field_limits = [-6, 6]):
        self.loop_sleep = 0.5 # (s)
        self.tol = 0.001 # (Tesla)
        self.sleep = 10 # (seconds)
        self.ramp_rate = 0.02 # (A/s?)
        self.ramp_rate_leads = 1
        self.message_log = []
        
        self.field_limits = field_limits # [T]
        self.address = address
        
#        self._rm = visa.ResourceManager()
#        self._inst = self._rm.open_resource(
#            self.address,
#            timeout=1000, # ms
#            write_termination = '\r\n',
#            read_termination = '\r\n',
#        )
        self._ser=serial.Serial(port=address,timeout=1)
        
        self.tesla(True)
        self.output_filter(True)
        self.set_ramp_rate(self.ramp_rate)
        self.set_max(np.max(field_limits)) # the maximum should always be the maximum allowed field
        self.lock()

        
    def _query(self, message):
        try:
            self._write(message)
            m = self._read()
#            m = self._inst.query(message)
        except visa.VisaIOError:
            self.flush_buffer()
            print('MagnetController: Caught IO Error!')
            traceback.print_exc()
            time.sleep(2)
            try:
                m = self._inst.query(message)
            except:
                raise
        except:
            raise
        self.message_log.append(m)
        return m
    
    
    def _write(self, message):
        print('writing: {}'.format(message))
        self._ser.write(message.encode('utf-8') + b'\n\r')
#        self._inst.write(message)
    
    
    def _read(self):
        print('reading')
        ''' TODO: does this work like that?'''
        ret = self._ser.read(100).decode()
        print(ret)
        return ret
#        self._inst.read()
    
    
    def print_status(self):
        self._write('UPDATE')
        print('MagnetController Status:')
        try:
            while True:
                print(self.read())
        except visa.VisaIOError:
            traceback.print_exc()
    
    
    def flush_buffer(self):
        pass # TODO debug
#        try:
#            while True:
#                self._read()
#        except visa.VisaIOError:
#            traceback.print_exc()
    
    
    def _extract_float(self, string):
        f = re.findall("\d+\.\d+", string)[0]
        return float(f)
    
    def extract_on_off(self, string):
        if string.lower().find('on') != -1:
            return 1
        elif string.lower().find('off') != -1:
            return 0
        else:
            return -1
    
    def lock(self):
        """Blocks local operation!"""
        ret = self._query('LOCK ON')
        self.flush_buffer()
        return ret
        
    def unlock(self):
        """Enables local operation"""
        return self._query('LOCK OFF')
    
    def close(self):
        self.unlock()
        self._inst.close()
    
    def tesla(self, on=True):
        """Turn on Tesla mode if on == True."""
        if on:
            return self._query('TESLA ON')
        else:
            return self._query('TESLA OFF')
            
    def output_filter(self, on=True):
        """Turn on mysterious filter option if on == True"""
        if on:
            return self._query('FILTER ON')
        else:
            return self._query('FILTER OFF')
    
    
    def pause(self):
        return self._query('PAUSE ON')
    
    
    def unpause(self):
        return self._query('PAUSE OFF')
        
    
    def is_ramping(self):
        status = self.get_ramp_status()
        return status == 'ramping'     
    
    
    def set_mid(self, value):
        if value < np.min(self.field_limits) or value > np.max(self.field_limits):
            warnings.warn('value: {} exceed limits! aborted'.format(value))
            return 0
        if value < 0:
            print('Negative fields not implemented, will go to absolute value')
            value = -value
        self._query('SET MID ' + str(value))
        if abs(value - self.get_mid()) > self.tol:
            # Setting did not work, probably because MAX point lies below
            self.set_max(value)
            self._query('SET MID ' + str(value))
        
    def get_mid(self):
        return self._extract_float(self._query('GET MID'))
        
    def set_max(self, value):
        if value < np.min(self.field_limits) or value > np.max(self.field_limits):
            warnings.warn('value: {} exceed limits! aborted'.format(value))
            return 0
        if value < 0:
            print('Negative fields not implemented, will go to absolute value') # TODO: implement
            value = -value    
        ret = self._query('SET MAX ' + str(value))
        if abs(value - self.get_max()) > self.tol:
            # Setting did not work, probably because MID point lies above
            self.set_mid(value)
            ret = self._query('SET MAX ' + str(value))
        return ret
        
    def get_max(self):
        return self._extract_float(self._query('GET MAX'))
    
    def set_ramp_rate(self, ramp_rate):
        return self._query('SET RAMP ' + str(ramp_rate))

    def get_ramp_rate(self):
        return self._extract_float(self._query('GET RAMP'))
    
    def get_output(self):
        return self._extract_float(self._query('GET OUTPUT'))
    
    def get_persistent(self):
        """Returns on: 1, off: 0, error: None"""
        s = self._query('GET PER').upper()
        if 'OFF' in s:
            # Persistent mode is off
            return 0
        elif 'STATUS' in s:
            # persistent mode on
            return 1
    
    def get_ramp_status(self): # TODO: check
        s = self._query('RAMP STATUS').upper()
        if 'RAMPING' in s:
            return 'ramping'
        elif 'HOLDING' in s:
            return 'holding'
        elif 'QUENCH' in s:
            print('MAGNET QUENCH DETECTED!')
        elif 'EXTERNAL' in s:
            print('MAGNET EXTERNAL TRIP!')
            
    def get_field(self): # TODO: check
        """
        Read field as indicated in ramp status. 
        
        Warning: Does not correspond to the magnetic field in the coil!!!
        """
        ramp_status = self.get_ramp_status()
        if ramp_status == 'ramping':
            self.pause()
            time.sleep(0.1)
            f = self._extract_float(self._query('RAMP STATUS'))
            self.unpause()
        elif ramp_status == 'holding':
            f = self._extract_float(self._query('RAMP STATUS'))
        else:
            f = None
            print('MagnetController: Cannot read magnetic field!')
        return f
    
    def get_physical_field(self): # TODO: read / write value into some file?
        """Try to figure out the field that is actually in the magnet."""
        persistent = self.get_persistent()
        if  persistent == 1:
            # We are in persistent mode, GET PER gives the field
            f = self._extract_float(self._query('GET PER'))
        elif persistent == 0:
            # We are not persistent, so either the field is zero,
            # or the heater is on and the field is given by RAMP STATUS
            heater = self.check_heater_on()
            if  heater == 0:
                f = 0
            elif heater == 1.:
                f = self.get_field()
        return float(f)
    
    def check_heater_on(self):
        """Switch heater on: 1 , off: 0, error: -1"""
        return self.extract_on_off(self._query('HEATER'))
    
    def switch_heater_on(self):
        if self.check_heater_on() == 1:
            # heater already on
            return 1
        elif self.check_heater_on() == 0:
            # Check if leads match persistent current!!!
            if abs(self.get_field() - self.get_physical_field()) <= self.tol:
                self._query('HEATER ON')
                time.sleep(self.sleep)
                return 1
            else:
                print('MagnetController: Tried to switch heater on',
                      'without having current match physical field!')
                return 0
        else:
            print('MagnetController: Cannot turn heater on.')
            return 0
        
    def switch_heater_off(self):
        if self.check_heater_on() == 0:
            # heater already off
            return 1
        else:
            self._query('HEATER OFF')
            time.sleep(self.sleep)
            return 1

    def ramp_to_zero(self):
        self._write('RAMP ZERO')

    def ramp_to_mid(self):
        self._write('RAMP MID')

    def ramp_to_max(self):
        self._write('RAMP MAX')
        
    def raise_field(self, target_field, persistent=False): # TODO: check
        # Check if we need to ramp the leads
        heater = self.check_heater_on()
        if not heater:  # which is only the case if the heater is off
            current_field = self.get_physical_field()
            current_leads = self.get_field()
            if abs(current_field - current_leads) <= self.tol:
                pass  # we are good to go
            else:  # energize current leads
                self.set_mid(current_field)
                self.set_ramp_rate(self.ramp_rate_leads)
                self.ramp_to_mid()
                while self.is_ramping():
                    time.sleep(self.loop_sleep)
                self.set_ramp_rate(self.ramp_rate)
                time.sleep(self.loop_sleep)
            time.sleep(self.loop_sleep)
            self.switch_heater_on()
        else:
            pass  # heater is already on and nothing to do
        # Set limits and ramp up, wait to reach target
        self.set_max(target_field)
        self.ramp_to_max()
        while self.is_ramping():
            time.sleep(self.loop_sleep)
        # Now we are done, except we somehow ended up in pause mode
        # (which should not be possible)
        # Ramp down the leads if persistent == True
        if persistent:
            time.sleep(self.sleep) # wait for field to settle at setpoint
            self.switch_heater_off()
            self.set_ramp_rate(self.ramp_rate_leads)
            self.ramp_to_zero()
            while self.is_ramping():
                time.sleep(self.loop_sleep)
            self.set_ramp_rate(self.ramp_rate)
            self.switch_heater_off()
    
    def lower_field(self, target_field, persistent=False): # TODO: check. and why raise and lower differently?
        # Check if we need to ramp the leads
        heater = self.check_heater_on()
        if not heater:  # which is only the case if the heater is off
            current_field = self.get_physical_field()
            current_leads = self.get_field()
            if abs(current_field - current_leads) <= self.tol:
                pass  # we are good to go
            else:  # energize current leads
                self.set_max(current_field)
                self.set_ramp_rate(self.ramp_rate_leads)
                self.ramp_to_max()
                while self.is_ramping():
                    time.sleep(self.loop_sleep)
                self.set_ramp_rate(self.ramp_rate)
                time.sleep(self.loop_sleep)
            time.sleep(self.loop_sleep)
            self.switch_heater_on()
        else:
            pass  # heater is already on and nothing to do
        # Set limits and ramp down, wait to reach target
        self.set_mid(target_field)
        self.ramp_to_mid()
        while self.is_ramping():
            time.sleep(self.loop_sleep)
        # Now we are done, except we somehow ended up in pause mode
        # (which should not be possible)
        # Ramp down the leads if persistent == True
        if persistent:
            time.sleep(self.sleep) # wait for field to settle at setpoint
            self.switch_heater_off()
            self.set_ramp_rate(self.ramp_rate_leads)
            self.ramp_to_zero()
            while self.is_ramping():
                time.sleep(self.loop_sleep)
            self.set_ramp_rate(self.ramp_rate)
            self.switch_heater_off()
        
    def set_Bfield(self, target_field, persistent=False):
        """
        Set the magnetic field to target_field in Tesla
        
        If persistent == True, ramp the leads down to zero.
        """
        # Find out if the current field is higher, equal or lower
        # then the target field and ramp if necessary
        current_field = self.get_physical_field()
        if abs(current_field - target_field) <= self.tol:
            print('MagnetController: Magnetic field already set to',
                  target_field, 'Tesla.')
            if persistent and self.check_heater_on():  
                print('MagnetController: Removing current from leads.')
                self.switch_heater_off()
                self.set_ramp_rate(self.ramp_rate_leads)
                self.ramp_to_zero()
                while self.is_ramping():
                    time.sleep(self.loop_sleep)
                self.set_ramp_rate(self.ramp_rate)
        elif current_field < target_field:
            print('MagnetController: Raising magnetic field to',
                  target_field, 'Tesla.')
            self.raise_field(target_field, persistent=persistent)
        elif current_field > target_field:
            print('MagnetController: Lowering magnetic field to',
                  target_field, 'Tesla.')     
            self.lower_field(target_field, persistent=persistent)

            
            
if __name__ == "__main__":
    # Example to initialize
    try:
        magnet._inst.close()
    except:
        pass
    magnet = MagnetController()
    # magnet.set_Bfield(0, persistent=False)
    
    # magnet._query('HEATER ON')

