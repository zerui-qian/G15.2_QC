# -*- coding: utf-8 -*-
"""
Class for National Instruments DAQ Device unsing PyDAQmx wrapper for c dll.

NI-DAQmx C Reference Help
http://zone.ni.com/reference/en-XX/help/370471AA-01/

Synchronization Concept
http://www.ni.com/product-documentation/4322/en/#toc3

PyDAQmx Doc (very limited)
https://pythonhosted.org/PyDAQmx/index.html

Header file of dll and c examples are valuable to understand DAQmx.

TODO:
There are still exceptions (KeyBoardInterrupt during measurement or 
data reading?) that leave the daq card in a weird
state after exiting this code. Some buffer stays non-empty and screws
up the following measurements...

@author: Patrick Knüppel
@author: Yuya Shimazaki
@author: eyazici
"""

""" 
Specifications USB-6366
input ranges 10, 5, 2, 1V

"""

import numpy as np
import PyDAQmx
from PyDAQmx import *
import sys
import DaemonDAQ.Network.nw_utils as nw_utils
import time

class NIDAQ_Channel(object):
    def __init__(self, nidaq, channel_name):
        self.nidaq = nidaq
        self.channel_name = channel_name
    
class NIDAQ_AI_Channel(NIDAQ_Channel):
    def __init__(self, nidaq, channel_name, low_limit = -10, high_limit = 10):
        super(NIDAQ_AI_Channel, self).__init__(nidaq, channel_name)
        self.task = PyDAQmx.Task()
        self.task.CreateAIVoltageChan(nidaq.device_name + "/" + self.channel_name, "",
                                 PyDAQmx.DAQmx_Val_Diff, low_limit, high_limit,
                                 PyDAQmx.DAQmx_Val_Volts, None)
        self.rate = 1000
        self.nr_samples = 100
    
    def update(operation):
        def _operation(self_obj, *args, **kwargs):
            ans = operation(self_obj, *args, **kwargs)
            self_obj._update_channel_info()
            if ans is not None:
                return ans
        return _operation
    
    def _update_channel_info(self):
        setattr(self.nidaq, self.channel_name, self)
    
    @update
    def get(self):
        read = PyDAQmx.int32()
        data = np.zeros((self.nr_samples, ), dtype=np.float64)
        self.task.CfgSampClkTiming("", self.rate, PyDAQmx.DAQmx_Val_Rising,
                                      PyDAQmx.DAQmx_Val_FiniteSamps, self.nr_samples)
    
        self.task.StartTask()
        self.task.ReadAnalogF64(self.nr_samples, self.nr_samples / self.rate + 2,
                                   PyDAQmx.DAQmx_Val_GroupByChannel,
                                   data, self.nr_samples,
                                   PyDAQmx.byref(PyDAQmx.int32()), None)

        self.task.WaitUntilTaskDone(self.nr_samples / self.rate + 2)
        self.task.StopTask()
        
        return np.mean(data)

class NIDAQ_dm(object):
    """"""
    
    def __init__(self, device_name='Dev_dm', mod1_amp_max = 1, mod2_amp_max = 1, mod3_amp_max = 5):
        self.device_name = device_name
        self._ao0 = None
        self._ao1 = None
        self.output_handle = sys.stdout
        self.create_ai('ai0')
        
        self.mod_active = False
        
        self._mod1_amp = 0
        self._mod1_amp_max = mod1_amp_max
        self._mod2_amp = 0
        self._mod2_amp_max = mod2_amp_max
        self._mod3_amp = 0
        self._mod3_amp_max = mod3_amp_max
        self._mod1_freq = 20e3
        self._mod2_freq = 30e3
        self._mod3_freq = 50e3        
        self._mod_sample_freq = 600e3
#        self._mod_sum_freq = None
        
        self._mod_task = None
#        self._sum_freq_task = None
        self._mod_timebase = None
                
    """
    from PyDAQmx import Task
    import numpy as np
    data = np.array([0,1,1,0,1,0,1,0], dtype=np.uint8)
    task = Task()
    task.CreateDOChan("/TestDevice/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    task.StopTask()
    """

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

    def create_ai(self, channel_name):
        setattr(self, channel_name, NIDAQ_AI_Channel(self, channel_name))

    @property
    def ao0(self):
        return self._ao0

    @property
    def ao1(self):
        return self._ao1
#
#    def set_do(self, value, channel='PFI7'):
#        task = PyDAQmx.Task()
#        task.CreateDOChan('Dev1/'+channel, '',
#                          PyDAQmx.DAQmx_Val_ChanForAllLines)
#        data = np.array(value, dtype=np.uint8)
#        task.StartTask()
#        # int32 DAQmxWriteDigitalLines (TaskHandle taskHandle,
#        # int32 numSampsPerChan, bool32 autoStart, float64 timeout, 
#        # bool32 dataLayout, uInt8 writeArray[], int32 *sampsPerChanWritten,
#        # bool32 *reserved);
#        task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel,
#                               data, None, None)
#        task.StopTask()
#            
    def set_ao0(self, value, ao_range=10, rate=0):
        """Set analog output voltage to value at ao0.
        Args:
            value (float): value that the output is set to.
            ao_range (float): maximum expected value for the channel.
            rate (float): rate at which the voltage is changed in V/s.
                If this is zero or negative, the voltage is set instantly."""
        task = PyDAQmx.Task()
        task.CreateAOVoltageChan(self.device_name + '/ao0', '',
                                -ao_range, ao_range,
                                PyDAQmx.DAQmx_Val_Volts, None)

        if rate <= 0 or self._ao0 == None:
            task.StartTask()
            task.WriteAnalogScalarF64(1, 10.0, value, None)
            task.StopTask()
        else:
            cv = self._ao0
            nsamples = int(np.ceil(1000 * np.abs(value - cv) / rate))
            voltages = np.linspace(self.ao0, value, nsamples, dtype=np.float64)
            task.CfgSampClkTiming(None, 1000, PyDAQmx.DAQmx_Val_Rising,
                                PyDAQmx.DAQmx_Val_FiniteSamps, nsamples)
            # set timeout to expected time the ramp takes, + 2 seconds.
            task.WriteAnalogF64(nsamples, True, 0,
                                    PyDAQmx.DAQmx_Val_GroupByChannel,
                                    voltages, None, None)
    
            task.WaitUntilTaskDone(nsamples / 1000 + 2)
            task.StopTask()
        self._ao0 = value
        #print(self.ao0)
            
    def set_ao1(self, value, ao_range=10, rate=0):
        """Set analog output voltage to value at ao1.
        Args:
            value (float): value that the output is set to.
            ao_range (float): maximum expected value for the channel.
            rate (float): rate at which the voltage is changed in V/s.
                If this is zero or negative, the voltage is set instantly."""
        task = PyDAQmx.Task()
        task.CreateAOVoltageChan(self.device_name + '/ao1', '',
                                -ao_range, ao_range,
                                PyDAQmx.DAQmx_Val_Volts, None)

        if rate <= 0 or self._ao1 == None:
            task.StartTask()
            task.WriteAnalogScalarF64(1, 10.0, value, None)
            task.StopTask()  
        else:
            cv = self._ao1
            nsamples = int(np.ceil(1000 * np.abs(value - cv) / rate))
            voltages = np.linspace(self.ao1, value, nsamples, dtype=np.float64)
            task.CfgSampClkTiming(None, 1000, PyDAQmx.DAQmx_Val_Rising,
                                PyDAQmx.DAQmx_Val_FiniteSamps, nsamples)
            # set timeout to expected time the ramp takes, + 2 seconds.
            task.WriteAnalogF64(nsamples, True, 0,
                                    PyDAQmx.DAQmx_Val_GroupByChannel,
                                    voltages, None, None)
    
            task.WaitUntilTaskDone(nsamples / 1000 + 2)
            task.StopTask()
        self._ao1 = value
        #print(self.ao1)
#        
#    def get_ao0(self):
#        ai_task = PyDAQmx.Task()
#        ai_task.CreateAIVoltageChan(self.device_name + "/_ao0_vs_aognd", "",
#                                 PyDAQmx.DAQmx_Val_Diff, -10, 10,
#                                 PyDAQmx.DAQmx_Val_Volts, None)
#        read = PyDAQmx.int32()
#        nr_samples = 100
#        data = np.zeros((nr_samples, ), dtype=np.float64)
#        ai_task.CfgSampClkTiming("", 1000, PyDAQmx.DAQmx_Val_Rising,
#                                      PyDAQmx.DAQmx_Val_FiniteSamps, nr_samples)
#    
#        ai_task.StartTask()
#        ai_task.ReadAnalogF64(nr_samples, nr_samples / 1000 + 2,
#                                   PyDAQmx.DAQmx_Val_GroupByChannel,
#                                   data, nr_samples,
#                                   PyDAQmx.byref(read), None)
#
#        ai_task.WaitUntilTaskDone(nr_samples / 1000 + 2)
#        ai_task.StopTask()
#        
#        return np.mean(data)
#
#    
#    def set_ao1(self, value, ao_range=10, rate=1, verbose=False):
#        """Set analog output voltage to value at ao1.
#        Args:
#            value (float): value that the output is set to.
#            ao_range (float): maximum expected value for the channel.
#            rate (float): rate at which the voltage is changed in V/s.
#                If this is zero or negative (default), the voltage is
#                set instantly.
#            verbose (bool): print verbose output during voltage sweep."""
#        
#        if rate > 0 and self._ao1 is None:
#            print('WARNING: Cannot ramp to target voltage because current '
#                 'voltage is unknown.')
#            ans = input('Set voltage to {:.2f} V instantly? y/[n]: '
#                        .format(value))
#            if ans.lower() != 'y':
#                return
#            else:
#                rate = -1
#
#        if self.ao1 is not None and np.isclose(value, self.ao1):
#            if verbose is True:
#                self.output_handle.write(
#                    'Voltage already at {} V.\n'.format(value))
#                self.output_handle.flush()
#            return
#
#        task = PyDAQmx.Task()
#        task.CreateAOVoltageChan(self.device_name + '/ao1', '',
#                                 -ao_range, ao_range,
#                                 PyDAQmx.DAQmx_Val_Volts, None)
#
#        if rate <= 0:
#            if verbose is True:
#                self.output_handle.write(
#                    'Setting voltage to {} V.\n'.format(value))
#                self.output_handle.flush()
#    
#            task.StartTask()
#            task.WriteAnalogScalarF64(1, 10.0, value, None)
#            task.StopTask()
#        else:
#            if verbose is True:
#                self.output_handle.write('Sweeping voltage... ')
#                self.output_handle.flush()
#
#            nsamples = int(np.ceil(1000 * np.abs(value - self.ao1) / rate))
#            voltages = np.linspace(self.ao1, value, nsamples, dtype=np.float64)
#            task.CfgSampClkTiming(None, 1000, PyDAQmx.DAQmx_Val_Rising,
#                                 PyDAQmx.DAQmx_Val_FiniteSamps, nsamples)
#
#            try:
#                task.WriteAnalogF64(nsamples, True, 0,
#                                    PyDAQmx.DAQmx_Val_GroupByChannel,
#                                    voltages, None, None)
#                # set timeout to expected time the ramp takes, + 2 seconds.
#                task.WaitUntilTaskDone(nsamples / 1000 + 2)  
#                if verbose is True:
#                    self.output_handle.write('Done.\n')
#                    self.output_handle.flush()
#            except (Exception, KeyboardInterrupt) as e:
#                task.ClearTask()
#                self._ao1 = None
#                raise e
#            task.StopTask() 
#        self._ao1 = value
#        
    def measure_ai(self, ai_channel=0, rate=1000.0, nr_samples=100,
                   average=True, limit=10.0, mode='diff', return_std=False):
        """Measure analog input voltage on one or multiple ai_channels.
        
        Args:
            ai_channel (int or list):
                Channel(s) on which the input is measured.
            rate (float):
                Sampling rate of the measurement in Hz.
            nr_samples (int):
                Number of measured samples per channel.
            average (bool):
                Whether to average the measured samples on each channel.
            limit (float):
                Maximum expected value.
            mode ("diff", "RSE", "NRSE", "pseudodiff"):
                Input mode. See DAQmx documentation for details.
            return_std (bool):
                Also return the standard deviations if average==True.

        Returns:
            data (np.ndarray):
                Array of measured values, one row per channel
                (shape: (len(ai_channel), nr_samples)). If average is True, data
                is an array of length len(ai_channel).
            std (np.ndarray, optional):
                Array of length len(ai_channel) containing the standard
                deviations. This is only returned if average==True and
                return_std==True."""
        
        analog_input = PyDAQmx.Task()
        read = PyDAQmx.int32()
    
        # Configure channel(s)
        if (not isinstance(ai_channel, list) and
            not isinstance(ai_channel, np.ndarray)):
            ai_channel = [ai_channel]

        ch_list = [self.device_name + '/ai' + str(c)
                   for c in ai_channel]
        channel = ', '.join(ch_list)

        # Input mode, determines the reference for the measured voltage.
        # See DAQmx documentation for details
        if mode.lower() == 'diff':
            ch_mode = PyDAQmx.DAQmx_Val_Diff
        elif mode.lower() == 'rse':
            ch_mode = PyDAQmx.DAQmx_Val_RSE
        elif mode.lower() == 'nrse':
            ch_mode = PyDAQmx.DAQmx_Val_NRSE
        elif mode.lower() == 'pseudodiff':
            ch_mode = PyDAQmx.DAQmx_Val_PseudoDiff
        else:
            raise ValueError('Unknown input mode "' + mode + '".\n' +
                             'Choose from "diff" (default), "RSE", "NRSE", ' +
                             '"pseudodiff".')

        analog_input.CreateAIVoltageChan(channel, "",
                                         ch_mode, -limit, limit,
                                         PyDAQmx.DAQmx_Val_Volts, None)

        # Measure one more sample and then throw away first sample -> sometimes
        # first sample is an outlier for some reason.
        nr_samples += 1
        data = np.zeros((nr_samples * len(ai_channel), ), dtype=np.float64)
        
        # int32 DAQmxCfgSampClkTiming (TaskHandle taskHandle, const char source[],
        # float64 rate, int32 activeEdge, int32 sampleMode,
        # uInt64 sampsPerChanToAcquire);
        analog_input.CfgSampClkTiming("", rate, PyDAQmx.DAQmx_Val_Rising,
                                      PyDAQmx.DAQmx_Val_FiniteSamps, nr_samples)
    
        # DAQmx Start Code
    
        analog_input.StartTask()
    
        # DAQmx Read Code
        # int32 DAQmxReadAnalogF64 (TaskHandle taskHandle, int32 numSampsPerChan,
        # float64 timeout, bool32 fillMode, float64 readArray[],
        # uInt32 arraySizeInSamps, int32 *sampsPerChanRead, bool32 *reserved);
        try:
            analog_input.ReadAnalogF64(nr_samples, nr_samples / rate + 2,
                                       PyDAQmx.DAQmx_Val_GroupByChannel,
                                       data, nr_samples * len(ai_channel),
                                       PyDAQmx.byref(read), None)

            analog_input.WaitUntilTaskDone(nr_samples / rate + 2)
        except (Exception, KeyboardInterrupt) as e:
            analog_input.ClearTask()
            raise e

        data = data.reshape(len(ai_channel), nr_samples)
        data = data[:, 1:]  # Throw away first sample for each channel
    
        if average is True:
            avg = np.array([np.mean(x) for x in data])
            std = np.array([np.std(x) for x in data])
            if return_std is True:
                return avg, std
            else:
                return avg
        else:
            return data


    def measure_single_voltage(self, ai_channel=0, rate=1000.0, nr_samples=100,
                   average=True, ai_limit=10.0, mode='diff', return_std=False):
        """Measure analog input voltage on one or multiple ai_channels.
        
        Args:
            ai_channel (int or list):
                Channel(s) on which the input is measured.
            rate (float):
                Sampling rate of the measurement in Hz.
            nr_samples (int):
                Number of measured samples per channel.
            average (bool):
                Whether to average the measured samples on each channel.
            ai_limit (float):
                Maximum expected value.
            mode ("diff", "RSE", "NRSE", "pseudodiff"):
                Input mode. See DAQmx documentation for details.
            return_std (bool):
                Also return the standard deviations if average==True.

        Returns:
            data (np.ndarray):
                Array of measured values, one row per channel
                (shape: (len(ai_channel), nr_samples)). If average is True, data
                is an array of length len(ai_channel).
            std (np.ndarray, optional):
                Array of length len(ai_channel) containing the standard
                deviations. This is only returned if average==True and
                return_std==True."""
        
        analog_input = PyDAQmx.Task()
        read = PyDAQmx.int32()
    
        # Configure channel(s)
        if (not isinstance(ai_channel, list) and
            not isinstance(ai_channel, np.ndarray)):
            ai_channel = [ai_channel]

        ch_list = [self.device_name + '/ai' + str(c)
                   for c in ai_channel]
        channel = ', '.join(ch_list)

        # Input mode, determines the reference for the measured voltage. See DAQmx documentation for details
        if mode.lower() == 'diff':
            ch_mode = PyDAQmx.DAQmx_Val_Diff
        elif mode.lower() == 'rse':
            ch_mode = PyDAQmx.DAQmx_Val_RSE
        elif mode.lower() == 'nrse':
            ch_mode = PyDAQmx.DAQmx_Val_NRSE
        elif mode.lower() == 'pseudodiff':
            ch_mode = PyDAQmx.DAQmx_Val_PseudoDiff
        else:
            raise ValueError('Unknown input mode "' + mode + '".\n' +
                             'Choose from "diff" (default), "RSE", "NRSE", ' +
                             '"pseudodiff".')

        analog_input.CreateAIVoltageChan(channel, "", ch_mode, -ai_limit, ai_limit, PyDAQmx.DAQmx_Val_Volts, None)
        # Measure one more sample and then throw away first sample -> sometimes
        # first sample is an outlier for some reason.
        nr_samples += 1
        data = np.zeros((nr_samples * len(ai_channel), ), dtype=np.float64)
        
        # int32 DAQmxCfgSampClkTiming (TaskHandle taskHandle, const char source[],
        # float64 rate, int32 activeEdge, int32 sampleMode,
        # uInt64 sampsPerChanToAcquire);
        analog_input.CfgSampClkTiming("", rate, PyDAQmx.DAQmx_Val_Rising, PyDAQmx.DAQmx_Val_FiniteSamps, nr_samples)
    
        # DAQmx Start Code
    
        analog_input.StartTask()
    
        # DAQmx Read Code
        # int32 DAQmxReadAnalogF64 (TaskHandle taskHandle, int32 numSampsPerChan,
        # float64 timeout, bool32 fillMode, float64 readArray[],
        # uInt32 arraySizeInSamps, int32 *sampsPerChanRead, bool32 *reserved);
        try:
            DEFAULT_TIMEOUT = 1e-2
            analog_input.ReadAnalogF64(nr_samples, nr_samples / rate + DEFAULT_TIMEOUT,
                                       PyDAQmx.DAQmx_Val_GroupByChannel,
                                       data, nr_samples * len(ai_channel),
                                       PyDAQmx.byref(read), None)

            analog_input.WaitUntilTaskDone(nr_samples / rate + DEFAULT_TIMEOUT)
        except (Exception, KeyboardInterrupt) as e:
            analog_input.ClearTask()
            raise e

        data = data.reshape(len(ai_channel), nr_samples)
        data = data[:, 1:]  # Throw away first sample for each channel
    
        if average is True:
            avg = np.array([np.mean(x) for x in data])
            std = np.array([np.std(x) for x in data])
            if return_std is True:
                return avg, std
            else:
                return avg
        else:
            return data



    def measure_ctr1(self, n_samples=1000, sampling_rate=1000):
        """not tested"""
        
        # Declaration of variables 
        ctr_taskHandle = PyDAQmx.TaskHandle()
        ai_taskHandle = PyDAQmx.TaskHandle()
        read = PyDAQmx.int32()
        arraysize = PyDAQmx.uInt32(n_samples)
        n_samples_int32 = PyDAQmx.int32(n_samples)
        data = np.zeros((n_samples,), dtype=np.uint32)
        timeout = PyDAQmx.float64(20)
        clock_src = '/' + self.device_name + '/ai/SampleClock'  

        try:
            # Route signal ## Does not work yet
            #destination = '/' + self.device_name + '/Ctr1Source'
            #source = '/' + self.device_name + '/PFI0'
            #PyDAQmx.DAQmxConnectTerms(source,
            #                          destination,
            #                          PyDAQmx.DAQmx_Val_DoNotInvertPolarity)
            
            # Create Counter Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ctr_taskHandle))
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ai_taskHandle))
            
            PyDAQmx.DAQmxCreateAIVoltageChan(ai_taskHandle,
                                             self.device_name+'/ai10',
                                             '',
                                             PyDAQmx.DAQmx_Val_Cfg_Default,
                                             0, 1, PyDAQmx.DAQmx_Val_Volts,
                                             None)
            
            PyDAQmx.DAQmxCfgSampClkTiming(ai_taskHandle, '',
                                          sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps,
                                          n_samples)
            
            PyDAQmx.DAQmxCreateCICountEdgesChan(ctr_taskHandle,
                                                self.device_name+'/Ctr1',
                                                None, PyDAQmx.DAQmx_Val_Rising,
                                                0, PyDAQmx.DAQmx_Val_CountUp)
            
            PyDAQmx.DAQmxCfgSampClkTiming(ctr_taskHandle, clock_src,
                                          sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps,
                                          n_samples)
    
            # DAQmx Start Code
            PyDAQmx.DAQmxStartTask(ctr_taskHandle)
            PyDAQmx.DAQmxStartTask(ai_taskHandle)
            
            PyDAQmx.DAQmxWaitUntilTaskDone(ctr_taskHandle, timeout)
            PyDAQmx.DAQmxWaitUntilTaskDone(ai_taskHandle, timeout)
            # DAQmx Read Code (n_samples_int32)
            PyDAQmx.DAQmxReadCounterU32(ctr_taskHandle, n_samples_int32,
                                        timeout, data, arraysize, 
                                        PyDAQmx.byref(read),
                                        None)
            #PyDAQmx.DAQmxRead
            

        
        except PyDAQmx.DAQError as err:
            print('DAQmx Error: {0}'.format(err))
        
        finally:
            if ctr_taskHandle:
                try: 
                    PyDAQmx.DAQmxStopTask(ctr_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ctr_taskHandle)
            if ctr_taskHandle:
                try: 
                    PyDAQmx.DAQmxStopTask(ai_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ai_taskHandle)
            
        return data
#            
#    def set_ao0_measure_ctr1(self, n_samples, sampling_rate, ao_setpoints):
#        """Collect n_samples while setting ao_setpoints at sampling_rate.
#        
#        The number of samples must be the length of ao_setpoints.
#        The setpoints are voltages withing [-4V, 4V] and the sampling
#        rate cannot exceed 2MHz.
#        """
#        
#        assert len(ao_setpoints) == n_samples
#                  
#        # Declaration of variables 
#        ctr_taskHandle = PyDAQmx.TaskHandle()
#        ao_taskHandle = PyDAQmx.TaskHandle()
#        read = PyDAQmx.int32()
#        written = PyDAQmx.int32()
#        arraysize = PyDAQmx.uInt32(n_samples)
#        n_samples_int32 = PyDAQmx.int32(-1)
#        data = np.zeros((n_samples,), dtype=np.uint32)
#        timeout = PyDAQmx.float64(20)
#        # valid terminal identifying source clock
#        clock_src = '/' + self.device_name + '/ao/SampleClock'  
#    
#        try:
#            # Create Analog Out Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ao_taskHandle))
#            # It is routed to channel ao0 with range [-4, 4] Volts
#            PyDAQmx.DAQmxCreateAOVoltageChan(ao_taskHandle,
#                                             self.device_name + '/ao0', '',
#                                             -4, 4, PyDAQmx.DAQmx_Val_Volts, '') 
#            # Default clock should be ao sample clock
#            PyDAQmx.DAQmxCfgSampClkTiming(ao_taskHandle, '', sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
#            
#            # Create Counter Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ctr_taskHandle))
#            PyDAQmx.DAQmxCreateCICountEdgesChan(ctr_taskHandle,
#                                                self.device_name + '/Ctr1',
#                                                '', PyDAQmx.DAQmx_Val_Rising, 0,
#                                                PyDAQmx.DAQmx_Val_CountUp)
#            PyDAQmx.DAQmxCfgSampClkTiming(ctr_taskHandle, clock_src, sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
#            
#            
#            PyDAQmx.DAQmxWriteAnalogF64(ao_taskHandle, n_samples, 0, 10.0, 
#                                        PyDAQmx.DAQmx_Val_GroupByChannel,
#                                        ao_setpoints, PyDAQmx.byref(written), None)
#        
#            #source = '/' + self.device_name + '/Ctr1Source'
#            #destination = '/' + self.device_name + '/PFI0'
#            #PyDAQmx.DAQmxConnectTerms(source,
#            #                          destination,
#            #                          PyDAQmx.DAQmx_Val_DoNotInvertPolarity);
#                                       
#            # DAQmx Start Code
#            PyDAQmx.DAQmxStartTask(ctr_taskHandle)
#            PyDAQmx.DAQmxStartTask(ao_taskHandle)    
#            
#            # DAQmx Read Code (n_samples_int32)
#            PyDAQmx.DAQmxReadCounterU32(ctr_taskHandle, n_samples_int32, 10.0,
#                                        data, arraysize, PyDAQmx.byref(read),
#                                        None)
#            
#            PyDAQmx.DAQmxWaitUntilTaskDone(ao_taskHandle, timeout)
#            PyDAQmx.DAQmxWaitUntilTaskDone(ctr_taskHandle, timeout)
#
##            print('Acquired {0} points'.format(read.value))
#            
#        except PyDAQmx.DAQError as err:
#            print('DAQmx Error: {0}'.format(err))
#            
#        finally:
#            if ao_taskHandle:
#                try:
#                    PyDAQmx.DAQmxStopTask(ao_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ao_taskHandle)
#            if ctr_taskHandle:
#                try: 
#                    PyDAQmx.DAQmxStopTask(ctr_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ctr_taskHandle)
#                
#        return data
#    
#    
#    def set_ao0_measure_ai0(self, n_samples, sampling_rate, ao_setpoints):
#        """Collect n_samples while setting ao_setpoints at sampling_rate.
#        
#        The number of samples must be the length of ao_setpoints.
#        The setpoints are voltages withing [-4V, 4V] and the sampling
#        rate cannot exceed 2MHz. Input signal in [-1V, 1V].
#        """
#    
#        # Declaration of variables 
#        ai_taskHandle = PyDAQmx.TaskHandle()
#        ao_taskHandle = PyDAQmx.TaskHandle()
#        read = PyDAQmx.int32()
#        written = PyDAQmx.int32()
#        data = np.zeros(n_samples, dtype=np.float64)
#        clock_src = '/Dev1/ai/SampleClock'  # valid terminal identifying source clock
#        
#        try:
#            # Create Analog In Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ai_taskHandle))
#            PyDAQmx.DAQmxCreateAIVoltageChan(ai_taskHandle, 'Dev1/ai0', '',
#                                     PyDAQmx.DAQmx_Val_Diff, -1, 1,
#                                     PyDAQmx.DAQmx_Val_Volts, None)
#            PyDAQmx.DAQmxCfgSampClkTiming(ai_taskHandle, '', sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_FiniteSamps,
#                                          n_samples)
#            
#            # Create Analog Out Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ao_taskHandle))
#            PyDAQmx.DAQmxCreateAOVoltageChan(ao_taskHandle, 'Dev1/ao0', '',
#                                             -4, 4, PyDAQmx.DAQmx_Val_Volts, '') 
#            PyDAQmx.DAQmxCfgSampClkTiming(ao_taskHandle, clock_src, sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_ContSamps, n_samples)
#            
#            PyDAQmx.DAQmxWriteAnalogF64(ao_taskHandle, n_samples, 0, 10.0, 
#                                        PyDAQmx.DAQmx_Val_GroupByChannel,
#                                        ao_setpoints, PyDAQmx.byref(written), None)
#        
#            # DAQmx Start Code
#            PyDAQmx.DAQmxStartTask(ao_taskHandle)
#            PyDAQmx.DAQmxTaskControl(ai_taskHandle,
#                                     PyDAQmx.DAQmx_Val_Task_Commit)
#            PyDAQmx.DAQmxStartTask(ai_taskHandle)
#        
#            # DAQmx Read Code
#            PyDAQmx.DAQmxReadAnalogF64(ai_taskHandle, n_samples, 10.0,
#                                       PyDAQmx.DAQmx_Val_GroupByChannel,
#                                       data, n_samples, PyDAQmx.byref(read),
#                                       None)
#        
#            print('Acquired {0} points'.format(read.value))
#        
#        
#        except PyDAQmx.DAQError as err:
#            print('DAQmx Error: {0}'.format(err))
#            
#        finally:
#            if ao_taskHandle:
#                try:
#                    PyDAQmx.DAQmxStopTask(ao_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ao_taskHandle)
#            if ai_taskHandle:
#                try: 
#                    PyDAQmx.DAQmxStopTask(ai_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ai_taskHandle)
#                
#        return data
#    
#    def set_ao0_measure_ctr1_ai0(self, n_samples, sampling_rate, ao_setpoints):
#        """Collect n_samples while setting ao_setpoints at sampling_rate.
#        
#        The number of samples must be the length of ao_setpoints.
#        The setpoints are voltages withing [-4V, 4V] and the sampling
#        rate cannot exceed 2MHz.
#        """
#        
#        # Declaration of variables 
#        n_samples = int(n_samples)
#        ctr_taskHandle = PyDAQmx.TaskHandle()
#        ao_taskHandle = PyDAQmx.TaskHandle()
#        ai_taskHandle = PyDAQmx.TaskHandle()
#        read = PyDAQmx.int32()
#        written = PyDAQmx.int32()
#        arraysize = PyDAQmx.uInt32(n_samples)
#        n_samples_int32 = PyDAQmx.int32(n_samples)
#        counts = np.zeros(n_samples, dtype=np.uint32)
#        voltages = np.zeros(n_samples, dtype=np.float64)
#        # valid terminal identifying source clock
#        clock_src = '/Dev1/ao/SampleClock'  
#    
#        try:
#            # Create Analog Out Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ao_taskHandle))
#            # It is routed to channel ao0 with range [-4, 4] Volts
#            PyDAQmx.DAQmxCreateAOVoltageChan(ao_taskHandle, 'Dev1/ao0', '',
#                                             -4, 4, PyDAQmx.DAQmx_Val_Volts, '') 
#            # Default clock should be ao sample clock
#            PyDAQmx.DAQmxCfgSampClkTiming(ao_taskHandle, '', sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
#            
#            # Create Analog In Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ai_taskHandle))
#            PyDAQmx.DAQmxCreateAIVoltageChan(ai_taskHandle, 'Dev1/ai0', '',
#                                     PyDAQmx.DAQmx_Val_Diff, -10, 10,
#                                     PyDAQmx.DAQmx_Val_Volts, None)
#            PyDAQmx.DAQmxCfgSampClkTiming(ai_taskHandle, clock_src,
#                                          sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_FiniteSamps,
#                                          n_samples)
#            # Create Counter Task
#            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ctr_taskHandle))
#            PyDAQmx.DAQmxCreateCICountEdgesChan(ctr_taskHandle, 'Dev1/Ctr1',
#                                                '', PyDAQmx.DAQmx_Val_Rising, 0,
#                                                PyDAQmx.DAQmx_Val_CountUp)
#            PyDAQmx.DAQmxCfgSampClkTiming(ctr_taskHandle, clock_src, sampling_rate,
#                                          PyDAQmx.DAQmx_Val_Rising,
#                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
#            
#            
#            PyDAQmx.DAQmxWriteAnalogF64(ao_taskHandle, n_samples, 0, 10.0, 
#                                        PyDAQmx.DAQmx_Val_GroupByChannel,
#                                        ao_setpoints, PyDAQmx.byref(written), None)
#        
#            # DAQmx Start Code
#            PyDAQmx.DAQmxStartTask(ctr_taskHandle)
#            PyDAQmx.DAQmxStartTask(ai_taskHandle)
#            PyDAQmx.DAQmxStartTask(ao_taskHandle)    
#        
#            # DAQmx Read Code
#            PyDAQmx.DAQmxReadCounterU32(ctr_taskHandle, n_samples_int32, 10.0,
#                                        counts, arraysize, PyDAQmx.byref(read),
#                                        None)
#            
#            PyDAQmx.DAQmxReadAnalogF64(ai_taskHandle, n_samples, 10.0,
#                                       PyDAQmx.DAQmx_Val_GroupByChannel,
#                                       voltages, n_samples, PyDAQmx.byref(read),
#                                       None)
#        
#            print('Acquired {0} points'.format(read.value))
#            
#        except PyDAQmx.DAQError as err:
#            print('DAQmx Error: {0}'.format(err))
#            
#        finally:
#            if ao_taskHandle:
#                try:
#                    PyDAQmx.DAQmxStopTask(ao_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ao_taskHandle)
#            if ctr_taskHandle:
#                try: 
#                    PyDAQmx.DAQmxStopTask(ctr_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ctr_taskHandle)
#            if ai_taskHandle:
#                try:
#                    PyDAQmx.DAQmxStopTask(ai_taskHandle)
#                finally:
#                    PyDAQmx.DAQmxClearTask(ai_taskHandle)
#                
#        return counts, voltages



    def init_mod_tasks(self, ch_mod1 = '/ao1', ch_mod2 = '/ao2', ch_mod3 = "/ao3", mod_timebase = ""):
        self.mod_task = PyDAQmx.Task()
        self.mod_task.CreateAOVoltageChan(self.device_name + ch_mod1, 'ch_mod1',
                        -self._mod1_amp_max, self._mod1_amp_max,
                        PyDAQmx.DAQmx_Val_Volts, None)
        self.mod_task.CreateAOVoltageChan(self.device_name + ch_mod2, 'ch_mod2',
                       -self._mod2_amp_max, self._mod2_amp_max,
                        PyDAQmx.DAQmx_Val_Volts, None)
        self.mod_task.CreateAOVoltageChan(self.device_name + ch_mod3, 'ch_mod3',
                       -self._mod3_amp_max, self._mod3_amp_max,
                        PyDAQmx.DAQmx_Val_Volts, None)
        
        self.mod_timebase = mod_timebase
        self.mod_write_buffer()

    def stop_mod_task(self):
        if self.mod_task is None: return
        self.mod_task.StopTask()
        self.mod_task.ClearTask()
        self.mod_task = None
    def start_mod_task(self):
        if self.mod_task is None: self.init_mod_tasks()
        self.mod_task.StartTask()        
                
    def mod_write_buffer(self, generate_sum_freq = True):

        was_active = False
        if (self.mod_active):   # stop modulation to modify buffer
            self.stop_dual_mod()
            was_active = True
            self.init_mod_tasks()
            
        sample_rate = self._mod_sample_freq
        t_sample = 1. / sample_rate
        
        t_low_1 = int(0.5 * (1./self.mod1_freq) / t_sample) # in units of sample time
        t_low_2 = int(0.5 * (1./self.mod2_freq) / t_sample)
        t_low_3 = int(0.5 * (1./self.mod3_freq) / t_sample)
        t_high_1 = t_low_1
        t_high_2 = t_low_2
        t_high_3 = t_low_3
        
        print(f"T1: {t_low_1*2}")
        print(f"T2: {t_low_2*2}")
        print(f"T3: {t_low_3*2}")
        
#        if (generate_sum_freq):
#            if self._mod_sum_freq == None: self._mod_sum_freq = self._mod1_freq + self._mod2_freq
#            nsamples = int(np.lcm(t_low_1+t_high_1,t_low_2+t_high_2))
#            t_sum = int((1./self._mod_sum_freq) / t_sample) //2 * 2 # must be multiple of 2
#            print(f"Tsum: {t_sum}")
#            nsamples = int(np.lcm(nsamples,t_sum)) * 2 # one buffer for each channel
#            
#        else:
        lcm1 = np.lcm(t_low_1+t_high_1,t_low_2+t_high_2)
        lcm2 = np.lcm(lcm1, t_low_3 + t_high_3)
        nsample_per_chan = int(lcm2)
        nsamples = int(nsample_per_chan * 3) # one buffer for each channel

        print(f"Nsamples: {nsamples}")

        samples = np.zeros(nsamples)        
        mod1_samples = np.concatenate((-self._mod1_amp*np.ones(t_low_1), self._mod1_amp*np.ones(t_high_1)))
        mod2_samples = np.concatenate((-self._mod2_amp*np.ones(t_low_2), self._mod2_amp*np.ones(t_high_2)))
        mod3_samples = np.concatenate((0* np.ones(t_low_3), self._mod3_amp*np.ones(t_high_3)))
        samples[:nsample_per_chan] = np.tile(mod1_samples, nsamples//len(mod1_samples)//3)
        samples[nsample_per_chan:2*nsample_per_chan] = np.tile(mod2_samples, nsamples//len(mod2_samples)//3)
        samples[2*nsample_per_chan:] = np.tile(mod3_samples, nsamples//len(mod3_samples)//3)
        
#        task.WriteAnalogF64(len(samples), True, 0,
#                                PyDAQmx.DAQmx_Val_GroupByChannel,
#                                samples, None, None)
#        task.CfgSampClkTiming(source = "80MHzTimebase",
#                                rate= sample_rate,
#                                activeEdge = PyDAQmx.DAQmx_Val_Rising,
#                                sampleMode= PyDAQmx.DAQmx_Val_FiniteSamps, 
#                                sampsPerChan= nsamples )
        self.mod_task.CfgSampClkTiming(self.mod_timebase,
                                       sample_rate,
                                       DAQmx_Val_Rising,
                                       DAQmx_Val_ContSamps,
                                       nsamples//3)
        self.mod_task.WriteAnalogF64(nsamples//3, False, 0,
                                PyDAQmx.DAQmx_Val_GroupByChannel,
                                samples, None, None)

#        if (generate_sum_freq):
#            sum_freq_samples = np.concatenate((np.zeros(t_sum//2), np.ones(t_sum//2)))
#            sum_freq_samples = np.tile(sum_freq_samples, (nsamples//2)//len(sum_freq_samples))
#            print(f"Nsamples (sumfreq): {len(sum_freq_samples)}")
#            self.sum_freq_task.CfgSampClkTiming(self.mod_timebase,
#                                       sample_rate,
#                                       DAQmx_Val_Rising,
#                                       DAQmx_Val_ContSamps,
#                                       nsamples//2)
#            self.sum_freq_task.WriteDigitalLines(nsamples//2,False,0,DAQmx_Val_GroupByChannel,np.array(sum_freq_samples, dtype = 'uint8')[:nsamples//2],None,None)

        if (was_active):
            self.start_dual_mod()
        

    def start_dual_mod(self):
        self.start_mod_task()
        self.mod_active = True
    def stop_dual_mod(self):
        self.stop_mod_task()
        self.mod_active = False

    @property
    def mod1_amp(self):
        return self._mod1_amp
    @mod1_amp.setter
    def mod1_amp(self, val):
        self._mod1_amp = val
        self.stop_dual_mod()
        self.start_dual_mod()
    @property
    def mod1_freq(self):
        return self._mod1_freq
    @mod1_freq.setter
    def mod1_freq(self, val):
        self._mod1_freq = val
        self.stop_dual_mod()
        self.start_dual_mod()
    @property
    def mod2_amp(self):
        return self._mod2_amp
    @mod2_amp.setter
    def mod2_amp(self, val):
        self._mod2_amp = val
        self.stop_dual_mod()
        self.start_dual_mod()
    @property
    def mod2_freq(self):
        return self._mod2_freq
    @mod2_freq.setter
    def mod2_freq(self, val):
        self._mod2_freq = val
        self.stop_dual_mod()
        self.start_dual_mod()

    @property
    def mod3_amp(self):
        return self._mod3_amp
    @mod3_amp.setter
    def mod3_amp(self, val):
        self._mod3_amp = val
        self.stop_dual_mod()
        self.start_dual_mod()
    @property
    def mod3_freq(self):
        return self._mod3_freq
    @mod3_freq.setter
    def mod3_freq(self, val):
        self._mod3_freq = val
        self.stop_dual_mod()
        self.start_dual_mod()


    @property
    def mod_sample_freq(self):
        return self._mod_sample_freq
    @mod_sample_freq.setter
    def mod_sample_freq(self, val):
        self._mod_sample_freq = val
        self.stop_dual_mod()
        self.start_dual_mod()


if __name__ == '__main__':
    daq_dm = NIDAQ_dm()
    daq_dm.init_mod_tasks()
    object_dict = {
        'NIDAQ_dual_mod': daq_dm
        }    
    nw_utils.RunServer(object_dict, host = 'localhost')
