# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 15:11:59 2018

@author: Patrick
"""
import ctypes
import os
import numpy as np
import time

class ANC350(object):
    
    def __init__(self):
#        os.environ['PATH'] = os.path.abspath(r'./devices/lib/') + ';' + os.environ['PATH']
#       self.dll = ctypes.windll.LoadLibrary('./devices/lib/anc350v2.dll')
        self.dll = ctypes.windll.LoadLibrary(r'C:/Users/QPG G8.1/Documents/Python Scripts/anc350v2.dll')
        ret = ctypes.c_int32()
        idn = ctypes.c_int32()
        ret = self.dll.PositionerCheck(ctypes.byref(idn))
        if ret != 1:
            print('ANC350: Error checking for anc350!')
        dev_no = ctypes.c_int32(0)
        self.handle = ctypes.c_int32()
        ret = self.dll.PositionerConnect(dev_no, ctypes.byref(self.handle))
        if ret != 0:
            print('ANC350: Error connecting to anc350!')
            
        # Default values
        for i in range(3):
            self.set_amplitude(i, 35)
            self.set_frequency(i, 500)
            
        # Limits (min, max) for axes (0, 1, 2)
        self.range_limits = ((100, 3900), (375, 4310), (None, None))
        
    def _parse_errorcode(self, errcode):
        switcher = {
            -1: "Unspecified error.",
            1: "Receive timed out.",
            2: "No connection was established.",
            3: "Error accessing the USB driver.",
            7: "Can't connect, device already in use.",
            8: "Unknown error.",
            9: "Invalid device number used in call.",
            10: "Invalid axis number in function call.",
            11: "Parameter in call is out of range.",   
            12: "Function not available for device type.",                 
        }
        return switcher.get(errcode,"No errorcode found.")
    
    def _print_error(self, retval):
        if retval != 0:
            print('ANC350:', self._parse_errorcode(retval))
  
    def close(self):
        self.dll.PositionerClose(self.handle)
        
    def get_status(self, axis_nr):
        axis_nr = ctypes.c_int32(axis_nr)
        status = ctypes.c_int32()
        ret = self.dll.PositionerGetStatus(self.handle, axis_nr,
                                           ctypes.byref(status))
        self._print_error(ret)
        return status.value
    
    def get_position(self, axis_nr):
        axis_nr = ctypes.c_int32(axis_nr) 
        position = ctypes.c_int32()
        ret = self.dll.PositionerGetPosition(self.handle, axis_nr,
                                             ctypes.byref(position))
        self._print_error(ret)
        return position.value
    
    def get_coordinates(self):
        xyz = [0, 0, 0]
        scaling = [1e-3,1e-3,1e-3]
        for i in range(3):
            xyz[i] = np.round(self.get_position(i)*scaling[i], 2)
        return xyz            
    
    def get_capacity(self, axis_nr):
        axis_nr = ctypes.c_int32(axis_nr) 
        capacity = ctypes.c_int32()
        ret = self.dll.PositionerCapMeasure(self.handle, axis_nr,
                                            ctypes.byref(capacity))
        self._print_error(ret)
        return capacity.value
    
    def get_amplitude(self, axis_nr):
        axis_nr = ctypes.c_int32(axis_nr) 
        amplitude = ctypes.c_int32()
        ret = self.dll.PositionerGetAmplitude(self.handle, axis_nr,
                                              ctypes.byref(amplitude))
        self._print_error(ret)
        return amplitude.value/1000
    
    def set_amplitude(self, axis_nr, voltage):
        axis_nr = ctypes.c_int32(axis_nr) 
        amplitude = ctypes.c_int32(voltage*1000)
        ret = self.dll.PositionerAmplitude(self.handle, axis_nr, amplitude)
        self._print_error(ret)
    
    def get_frequency(self, axis_nr):
        axis_nr = ctypes.c_int32(axis_nr) 
        frequency = ctypes.c_int32()
        ret = self.dll.PositionerGetFrequency(self.handle, axis_nr,
                                              ctypes.byref(frequency))
        self._print_error(ret)
        return frequency.value
    
    def set_frequency(self, axis_nr, frequency):
        axis_nr = ctypes.c_int32(axis_nr) 
        frequency = ctypes.c_int32(frequency)
        ret = self.dll.PositionerFrequency(self.handle, axis_nr, frequency)
        self._print_error(ret)

    def set_dc(self, axis_nr, dc_V):
        """
        Set DC level of the positioner.
        
        5V/s ramp with 10mV increment.
        """
        if dc_V > 100 or dc_V < 0: return False
        
        curr_val = ctypes.c_int32()
        ret = self.dll.PositionerGetDcLevel(self.handle,ctypes.c_int32(axis_nr), ctypes.byref(curr_val) )
        self._print_error(ret)
        val = int(dc_V * 1000) # V to mV
        incr = 50 # mV
        wait_time = incr / 5 / 1000 # 5 V/s == 5000 mV/s 

        curr_val = curr_val.value
        if val >= curr_val:
             valrange = range(curr_val+1, val+1, incr)
        else:
             valrange = range(curr_val-1, val-1,-incr)
             
        for next_val in valrange:
            ret = self.dll.PositionerDCLevel(self.handle,ctypes.c_int32(axis_nr),ctypes.c_int32(next_val))
            self._print_error(ret)
            time.sleep(wait_time)
        self.dll.PositionerDCLevel(self.handle,ctypes.c_int32(axis_nr),ctypes.c_int32(val))
        return True
    
    def get_dc(self,axis_nr):
        """
        Get DC level of the positioner.
        Units : V
        """
        
        curr_dc = ctypes.c_int32()
        self.dll.PositionerGetDcLevel(self.handle,ctypes.c_int32(axis_nr),  ctypes.byref(curr_dc))
        return float(curr_dc.value) / 1000
        
    def step(self, axis_nr, nr_steps):
        """Move 'nr_steps' single steps on axis 'axis_nr'.
        
        Can supply negative value for 'nr_steps' to step backwards.
        """
        
        axis_nr = ctypes.c_int32(axis_nr)
        if nr_steps > 0:
            direction = ctypes.c_int32(0)
        else:
            direction = ctypes.c_int32(1)
        steps = ctypes.c_int32(abs(nr_steps))
        ret = self.dll.PositionerStepCount(self.handle, axis_nr, steps)
        self._print_error(ret)
        ret = self.dll.PositionerMoveSingleStep(self.handle, axis_nr, direction)
        self._print_error(ret)
        
        
    def stop(self, axis_nr):
        """Stop given axis."""
        axis_nr = ctypes.c_int32(axis_nr)
        ret = self.dll.PositionerStopMoving(self.handle, axis_nr)
        self._print_error(ret)
    
    def move(self, axis_nr, direction=0):
        """Move continously; forward: 0, backward: 1"""
        #Int32 NCB_API PositionerMoveContinuous( Int32 deviceHandle, Int32 axisNo, Int32 dir );
        axis_nr = ctypes.c_int32(axis_nr)
        direction = ctypes.c_int32(direction)
        ret = self.dll.PositionerMoveContinuous(self.handle, axis_nr, direction)
        self._print_error(ret)
        
    def move_to_xy(self, target=(0, 0), timeout=90, tolerance=5):
        """Approach target (x,y) readout value up to tolerance"""
        scaling = 1e-3
        for axis in (0, 1):
            if target[axis] < self.range_limits[axis][0] or target[axis] > self.range_limits[axis][1]:
                raise ValueError('Attocube target position out of range_limits')
            starting_time = time.time()
            current_position = self.get_position(axis) * scaling
            while abs(current_position - target[axis]) > 25:
                # approach target if timeout not reached
                if time.time() - starting_time > timeout:
                    print('Warning: Attocube did not reach target before timeout!')
                    break
                # could speed up by taking more steps if further away
                if current_position < target[axis]:
                    self.move(axis, 0)
                else:
                    self.move(axis, 1)
                time.sleep(1)
                self.stop(axis)
                time.sleep(0.33)
                current_position = self.get_position(axis) * scaling
            # Fine approach
            while abs(current_position - target[axis]) > tolerance:
                # approach target if timeout not reached
                if time.time() - starting_time > timeout:
                    print('Warning: Attocube did not reach target before timeout!')
                    break
                if current_position < target[axis]:
                    for i in range(5):
                        self.step(axis, 1)
                else:
                    for i in range(5):
                        self.step(axis, -1)
                time.sleep(0.33)
                current_position = self.get_position(axis) * scaling                
                    
    def move_to(self, target_coordinates, tolerance=100, timeout=50):
        raise NotImplementedError('this function is work in progress...')
        # Coarse approach
        default_frequency = [0, 0, 0]
        for i in range(3):
            default_frequency[i] = self.get_frequency(i)
            self.set_frequency(i, 500)
        for i in range(3):
            error = target_coordinates[i] - self.get_position(i)
            if abs(error) > 10 * tolerance:
                steps = int(100 * np.sign(error))
                while np.sign(steps) == np.sign(target_coordinates[i] - self.get_position(i)):
                    atto.step(i, steps)
                    time.sleep(0.1)
        # Fine approach
        for i in range(3):
            self.set_frequency(i, 10)
        for i in range(3):
            error = target_coordinates[i] - self.get_position(i)
            steps = int(1 * np.sign(error))
            counter = 0
            while counter < timeout and tolerance < abs(error):
                atto.step(i, steps)
                time.sleep(0.1)   
                error = target_coordinates[i] - self.get_position(i)
                steps = int(1 * np.sign(error))
        for i in range(3):
            self.set_frequency(i, default_frequency[i])
    
    
if __name__ == "__main__":
    atto = ANC350()
    for i in range(0, 3):
        print('Status {0}'.format(i), atto.get_status(i))
        print('Position {0}'.format(i), atto.get_position(i))
        print('Capacity {0}'.format(i), atto.get_capacity(i))
        print('Amplitude {0}'.format(i), atto.get_amplitude(i))
        print('Frequency {0}'.format(i), atto.get_frequency(i))
    #atto.close()
    