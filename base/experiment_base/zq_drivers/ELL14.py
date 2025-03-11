# -*- coding: utf-8 -*-
"""
Created on Mon Nov 12 20:57:42 2018

@author: Gian-Marco, based on elloController.py by Li Bing for linear stage, Alex

Communication class with Thorlabs ELL8K/M rotation stage, communication protocol under:
    https://www.thorlabs.com/Software/Elliptec/Communications_Protocol/ELLx%20modules%20protocol%20manual.pdf
"""

from __future__ import division,print_function,unicode_literals,absolute_import

import serial, sys

sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\base\experiment_base\fey_drivers\pyro_nw')
import nw_utils as nw_utils
import time

VERBOSE = False

'''
2019-10 debugging
Old board was not responding!
Need to plug them in one after another?
Need to wait some time until board appears in device manager!
Couldn't find motor address...
manually started ser, asked for 'in' and '0in', and the device responded
! They work mutually exclusive ! (was because didn't get enough current from usb)
! Sometimes they need more than 1 attempt to respond, especially when the device
is busy, it can take longer for it to respond, that's why we need many attempts in read()

okay, we get a mechanical timeout when the device is not connected to 5V, so 
they're sensitive to getting enough current


TODO: make driver compatible with daisy-chained devices

'''


def hexify(decimal,n=8):
#    try:
    decimal = int(decimal)
    hexStr="{0:0{1}x}".format(decimal,n).upper()
#    except Exception as e:
#        print(decimal)
#        raise(e)
    
    return hexStr


class ELL14():
    
    def __init__(self, comstr='COM4'):
        self._ser=serial.Serial(port=comstr,timeout=1,interCharTimeout=5)
        # empty output storage of serialport 
        for ii in range(50):
            reply = self._ser.read(10)
            if len(reply) == 0:
                break
        
        # initiate values 
        self._angle=0. # absolute angle relative to home
        self._posError = 0.
        self._zeroangle = 0. # angle offset relative to home
        
        self._move_timeout = 5 # throw error if movement not finished after this. especially old boards are slow
        
        # find the address of the motor motAdd in (0,F)
        for n in ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']:
            reply = self._query(n+'in')
            if reply.startswith(n): 
                print(reply)
                self._pPdeg=int(reply[25:],16)/360
                #print (self._pPdeg)
                print('Motor Address:'+n)
                self._motAdd = n            
                break
            if n=='F':
                raise ValueError('no address found for {}'.format(comstr))
            
        # check status of the device
        print(self.status)
            
        # Initialize velocity to 100%
        reply = self._query(self._motAdd+'gv')
        self._vel = int(reply[3:5],16)
        if self._vel != 100:
            reply = self._query(self._motAdd+'sv'+hexify(100,2))
            self._vel = int(reply[3:-2],16)
    
    def __del__(self):
        if VERBOSE:
            print('destructing object')
        self.close()
            
    def _write(self, cmd):
        b_cmd = bytes(cmd,'utf-8')
        self._ser.write(b_cmd)
        if VERBOSE:
            print('wrote: {}'.format(b_cmd.__repr__()))
    
    def _read(self,nbytes=None):
#        ret = self._ser.readline() # ends with \r\n
#        if VERBOSE:
#            print('read: {}'.format(ret.__repr__()))
#            print('ret length: {}'.format(len(ret)))
        tstart = time.time()
        while time.time() - tstart < self._move_timeout:
            ret = self._ser.readline() # ends with \r\n
            if VERBOSE:
                print('read: {}'.format(ret.__repr__()))
                print('ret length: {}'.format(len(ret)))
            if len(ret) > 2: # not just empty line
                break
        ret = ret[:-2] # cut off ending
        if ret[1:3] == 'GS': # error
            if ret[3:5] == '00':
                print('no error')
            else:
                raise ValueError('error {}'.format(int(ret[3:5],16)))
        return ret.decode()
    
    def _query(self, cmd):
        self._write(cmd)
        ret = self._read()
        return ret

    def _calc_angle(self, reply):
        # https://stackoverflow.com/questions/11826054/valueerror-invalid-literal-for-int-with-base-16-x0e-xa3-python
#        w = struct.unpack("h", x)[0]
        if VERBOSE:
            print('converting: {}'.format(reply[3:]))
        reply = int(reply[3:],16)
        if reply > 2**31:
            reply -= 2**32
        return reply / self._pPdeg
        
        
    @property # get absolute angle (relative to home position)
    def angle(self):
        reply = self._query(self._motAdd+'gp')
        self._angle = self._calc_angle(reply) - self._zeroangle
        return self._angle
        
    @angle.setter # set angle (relative to zero)
    def angle(self,targetAngle):
        targetAngle = (targetAngle + self._zeroangle) % 360 # values >= 360 give an error
        targetPulse = round(targetAngle*self._pPdeg)
#        targetPulse = int(round(targetAngle*self._pPdeg))
        reply = self._query(self._motAdd+'ma'+hexify(targetPulse))
        self._angle = self._calc_angle(reply)
        self._posError = targetAngle - self._angle
        if VERBOSE:
            print('targetangle: {}'.format(targetAngle))
            print('error: {}'.format(self._posError))
        return self._angle
    
    
    def home(self,direction = 0): # move to home posittion :=0° with 0=cw, 1=ccw
        reply = self._query(self._motAdd +'ho'+ "%s" %direction)
        self._angle = int(reply[3:],16)/self._pPdeg
        return self._angle
    
    def set_zero(self, zeroangle=None): # set current position to zero
        ''' set zero angle relative to home position
        set it somewhere between 0 and 180 deg, such that angle can be 
        between 0 and 180 deg without having any jumps with a full rotation
        '''
        if zeroangle is None:
            self._zeroangle = self._angle
        else:
            self._zeroangle = zeroangle
            
    def set_angle(self,targetAngle):
        self.angle = targetAngle
        
    def get_angle(self):
        return self.angle
        
        
        
#    # move relative to current position
#    def rotate(self,relAngle):
#        ''' negative rotations? not implemented'''
#        initialPosition = self._angle
#        relPulse = round(relAngle*self._pPdeg)
#        reply = self._query(self._motAdd+'mr'+hexify(relPulse))
#        self._angle = int(reply[3:],16)/self._pPdeg
#        self._posError = initialPosition + relAngle - self._angle
#        return self._angle
    
#    @property # get the velocity in % of the maximal velocity
#    def vel(self):
#        reply = self._query(self._motAdd+'gv')
#        self._vel = int(reply[3:],16)
#        return self._vel
    
#    @vel.setter # set the velocity in % of the maximal velocity !!!NOT IMPLEMENTED YET!!!!
#    def vel(self,percentageOfMaxVel):
#        if percentageOfMaxVel < 45:
#            print('Warning: low velocity might cause device to stall')
#        reply = self._query(self._motAdd+'sv'+hexify(percentageOfMaxVel,2))
#        self._vel = int(reply[3:],16)
#        return self._vel
    
    @property # get status of device, see error codes in pdf
    def status(self):
        reply = self._query(self._motAdd+'gs')
        self._status = int(reply[3:],16)
        return self._status
    
    @property
    def posError(self):
        return self._posError
    
    
    def close(self):
        self._ser.close()


if __name__ == '__main__':
    
    ell = ELL14('COM6')
    ell.set_zero(0)
    ell.angle = ell.angle
    
    ell2 = ELL14('COM7')
    ell2.set_zero(0)
    ell2.angle = ell2.angle
    
    ell3 = ELL14('COM12')
    ell3.set_zero(0)
    ell3.angle = ell3.angle
    
    object_dict = {
        'ELL14': ell,
        'ELL14_2': ell2,
        'ELL14_3': ell3,
        }
    nw_utils.RunServer(object_dict)

    
    # ========= DEBUGGING =========
#    ser=serial.Serial(port='COM4',timeout=0.1,interCharTimeout=5)
#    ser.write(bytes('0in','utf-8'))
#    print(ser.readline())
#    
##    ser.write(bytes('0ca1','utf-8'))
##    print(ser.readline())
#    
#    ser.write(bytes('1in','utf-8'))
#    print(ser.readline())
#    
#    ser2=serial.Serial(port='COM6',timeout=0.1,interCharTimeout=5)
#    
#    ser2.write(bytes('0in','utf-8'))
#    print(ser2.readline())
#    
#    ser2.write(bytes('1in','utf-8'))
#    print(ser2.readline())
    
#    for n in ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F']:
#        ser2.write(bytes(n+'in','utf-8'))
#        print(ser.readline())

#    targetAngle = 360
#    ret = ell._query(ell._motAdd+'ma'+hexify(round(targetAngle*ell._pPdeg)))
#    print(ret)
    
    
#    for ii in range(10):
#        ell.angle = ii*20
#        time.sleep(1)
    

    
    
    
    
    
    
        