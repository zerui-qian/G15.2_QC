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
"""

""" 
Specifications USB-6366
input ranges 10, 5, 2, 1V

"""

import numpy as np
import time
import PyDAQmx
import sys
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base\zq_drivers\pyro_nw')
import nw_utils as nw_utils

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

class NIDAQ(object):
    """"""
    
    def __init__(self, device_name='Dev1'):
        self.device_name = device_name
        self._ao0 = None
        self._ao1 = None
        self._ao2 = None
        self.output_handle = sys.stdout
        self.create_ai('ai0')
        
        
        try:
            self._ao0 = self.get_ao0()
            self._ao1 = self.get_ao1()
            self._ao2 = self.get_ao2()
            
        except Exception:
            print("Warning: could not initialize AO channel values")
    
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

    @property
    def ao2(self):
        return self._ao2

    def set_do(self, value, channel='PFI7'):
        task = PyDAQmx.Task()
        task.CreateDOChan('Dev1/'+channel, '',
                          PyDAQmx.DAQmx_Val_ChanForAllLines)
        data = np.array(value, dtype=np.uint8)
        task.StartTask()
        # int32 DAQmxWriteDigitalLines (TaskHandle taskHandle,
        # int32 numSampsPerChan, bool32 autoStart, float64 timeout, 
        # bool32 dataLayout, uInt8 writeArray[], int32 *sampsPerChanWritten,
        # bool32 *reserved);
        task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel,
                              data, None, None)
        task.StopTask()
            
    def set_ao0(self, value, ao_range=10, rate=1):
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
            cv = self.get_ao0()
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
    
    def set_ao1(self, value, ao_range=10, rate=1, verbose=False):
        """Set analog output voltage to value at ao1.
        Args:
            value (float): value that the output is set to.
            ao_range (float): maximum expected value for the channel.
            rate (float): rate at which the voltage is changed in V/s.
                If this is zero or negative (default), the voltage is
                set instantly.
            verbose (bool): print verbose output during voltage sweep."""
        
        if rate > 0 and self._ao1 is None:
            print('WARNING: Cannot ramp to target voltage because current '
                'voltage is unknown.')
            ans = input('Set voltage to {:.2f} V instantly? y/[n]: '
                        .format(value))
            if ans.lower() != 'y':
                return
            else:
                rate = -1

        if self.ao1 is not None and np.isclose(value, self.ao1):
            if verbose is True:
                self.output_handle.write(
                    'Voltage already at {} V.\n'.format(value))
                self.output_handle.flush()
            return

        task = PyDAQmx.Task()
        task.CreateAOVoltageChan(self.device_name + '/ao1', '',
                                -ao_range, ao_range,
                                PyDAQmx.DAQmx_Val_Volts, None)

        if rate <= 0:
            if verbose is True:
                self.output_handle.write(
                    'Setting voltage to {} V.\n'.format(value))
                self.output_handle.flush()
    
            task.StartTask()
            task.WriteAnalogScalarF64(1, 10.0, value, None)
            task.StopTask()
        else:
            if verbose is True:
                self.output_handle.write('Sweeping voltage... ')
                self.output_handle.flush()

            nsamples = int(np.ceil(1000 * np.abs(value - self.ao1) / rate))
            voltages = np.linspace(self.ao1, value, nsamples, dtype=np.float64)
            task.CfgSampClkTiming(None, 1000, PyDAQmx.DAQmx_Val_Rising,
                                PyDAQmx.DAQmx_Val_FiniteSamps, nsamples)

            try:
                task.WriteAnalogF64(nsamples, True, 0,
                                    PyDAQmx.DAQmx_Val_GroupByChannel,
                                    voltages, None, None)
                # set timeout to expected time the ramp takes, + 2 seconds.
                task.WaitUntilTaskDone(nsamples / 1000 + 2)  
                if verbose is True:
                    self.output_handle.write('Done.\n')
                    self.output_handle.flush()
            except (Exception, KeyboardInterrupt) as e:
                task.ClearTask()
                self._ao1 = None
                raise e
            task.StopTask() 
        self._ao1 = value

    def set_ao2(self, value, ao_range=10, rate=1, verbose=False):
        """Set analog output voltage to value at ao2.
        Args:
            value (float): value that the output is set to.
            ao_range (float): maximum expected value for the channel.
            rate (float): rate at which the voltage is changed in V/s.
                If this is zero or negative (default), the voltage is
                set instantly.
            verbose (bool): print verbose output during voltage sweep."""
        
        if rate > 0 and self._ao2 is None:
            print('WARNING: Cannot ramp to target voltage because current '
                'voltage is unknown.')
            ans = input('Set voltage to {:.2f} V instantly? y/[n]: '
                        .format(value))
            if ans.lower() != 'y':
                return
            else:
                rate = -1

        if self.ao2 is not None and np.isclose(value, self.ao2):
            if verbose is True:
                self.output_handle.write(
                    'Voltage already at {} V.\n'.format(value))
                self.output_handle.flush()
            return

        task = PyDAQmx.Task()
        task.CreateAOVoltageChan(self.device_name + '/ao2', '',
                                -ao_range, ao_range,
                                PyDAQmx.DAQmx_Val_Volts, None)

        if rate <= 0:
            if verbose is True:
                self.output_handle.write(
                    'Setting voltage to {} V.\n'.format(value))
                self.output_handle.flush()
    
            task.StartTask()
            task.WriteAnalogScalarF64(1, 10.0, value, None)
            task.StopTask()
        else:
            if verbose is True:
                self.output_handle.write('Sweeping voltage... ')
                self.output_handle.flush()

            nsamples = int(np.ceil(1000 * np.abs(value - self.ao2) / rate))
            voltages = np.linspace(self.ao2, value, nsamples, dtype=np.float64)
            task.CfgSampClkTiming(None, 1000, PyDAQmx.DAQmx_Val_Rising,
                                PyDAQmx.DAQmx_Val_FiniteSamps, nsamples)

            try:
                task.WriteAnalogF64(nsamples, True, 0,
                                    PyDAQmx.DAQmx_Val_GroupByChannel,
                                    voltages, None, None)
                # set timeout to expected time the ramp takes, + 2 seconds.
                task.WaitUntilTaskDone(nsamples / 1000 + 2)  
                if verbose is True:
                    self.output_handle.write('Done.\n')
                    self.output_handle.flush()
            except (Exception, KeyboardInterrupt) as e:
                task.ClearTask()
                self._ao2 = None
                raise e
            task.StopTask() 
        self._ao2 = value
    
    def smooth_set_ao1(self, target_value, step_size=0.01, delay=0.05):
        """
        Written by Johannes on December 15, 2024
        Smoothly sets ao1 from its current value to the target value.
        Parameters:
            target_value (float): The value to set ao1 to.
            step_size (float): The increment size for each step.
            delay (float): The time (in seconds) to wait between each step.
        """
        current_value = self.ao1
        direction = 1 if target_value > current_value else -1
        total_steps = int(abs(target_value - current_value) / step_size)
        
        for _ in range(total_steps):
            current_value += direction * step_size
            self.set_ao1(current_value, rate=0)
            time.sleep(delay)

        self.set_ao1(target_value)  # Ensure the final value is set accurately
    
    def smooth_set_ao2(self, target_value, step_size=0.01, delay=0.05):
        """
        Written by Johannes on December 15, 2024
        Smoothly sets ao2 from its current value to the target value.
        Parameters:
            target_value (float): The value to set ao2 to.
            step_size (float): The increment size for each step.
            delay (float): The time (in seconds) to wait between each step.
        """
        current_value = self.ao2
        direction = 1 if target_value > current_value else -1
        total_steps = int(abs(target_value - current_value) / step_size)
        
        for _ in range(total_steps):
            current_value += direction * step_size
            self.set_ao2(current_value, rate=0)
            time.sleep(delay)

        self.set_ao2(target_value)  # Ensure the final value is set accurately
    
    # def main_set_ao1(self, target_value, step_thr=2):
    #     # if self.ao1 is None: 
    #     #     self.set_ao1(target_value)
    #     if abs(target_value - self.ao1) > step_thr:
    #         self.smooth_set_ao1(target_value)
    #     else:
    #         self.set_ao1(target_value)
    
    # def main_set_ao2(self, target_value, step_thr=2):
    #     # if self.ao2 is None: 
    #     #     self.set_ao2(target_value)
    #     if abs(target_value - self.ao2) > step_thr:
    #         self.smooth_set_ao2(target_value)
    #     else:
    #         self.set_ao2(target_value)
    
    
    
    def get_ao0(self):
        ai_task = PyDAQmx.Task()
        ai_task.CreateAIVoltageChan(self.device_name + "/_ao0_vs_aognd", "",
                                PyDAQmx.DAQmx_Val_Diff, -10, 10,
                                PyDAQmx.DAQmx_Val_Volts, None)
        read = PyDAQmx.int32()
        nr_samples = 100
        data = np.zeros((nr_samples, ), dtype=np.float64)
        ai_task.CfgSampClkTiming("", 1000, PyDAQmx.DAQmx_Val_Rising,
                                      PyDAQmx.DAQmx_Val_FiniteSamps, nr_samples)
    
        ai_task.StartTask()
        ai_task.ReadAnalogF64(nr_samples, nr_samples / 1000 + 2,
                                  PyDAQmx.DAQmx_Val_GroupByChannel,
                                  data, nr_samples,
                                  PyDAQmx.byref(read), None)

        ai_task.WaitUntilTaskDone(nr_samples / 1000 + 2)
        ai_task.StopTask()
        
        return np.mean(data)

    def get_ao1(self):
        ai_task = PyDAQmx.Task()
        ai_task.CreateAIVoltageChan(self.device_name + "/_ao1_vs_aognd", "",
                                PyDAQmx.DAQmx_Val_Diff, -10, 10,
                                PyDAQmx.DAQmx_Val_Volts, None)
        read = PyDAQmx.int32()
        nr_samples = 100
        data = np.zeros((nr_samples, ), dtype=np.float64)
        ai_task.CfgSampClkTiming("", 1000, PyDAQmx.DAQmx_Val_Rising,
                                      PyDAQmx.DAQmx_Val_FiniteSamps, nr_samples)
    
        ai_task.StartTask()
        ai_task.ReadAnalogF64(nr_samples, nr_samples / 1000 + 2,
                                  PyDAQmx.DAQmx_Val_GroupByChannel,
                                  data, nr_samples,
                                  PyDAQmx.byref(read), None)

        ai_task.WaitUntilTaskDone(nr_samples / 1000 + 2)
        ai_task.StopTask()
        
        return np.mean(data)

    def get_ao2(self):
        ai_task = PyDAQmx.Task()
        ai_task.CreateAIVoltageChan(self.device_name + "/_ao2_vs_aognd", "",
                                PyDAQmx.DAQmx_Val_Diff, -10, 10,
                                PyDAQmx.DAQmx_Val_Volts, None)
        read = PyDAQmx.int32()
        nr_samples = 100
        data = np.zeros((nr_samples, ), dtype=np.float64)
        ai_task.CfgSampClkTiming("", 1000, PyDAQmx.DAQmx_Val_Rising,
                                      PyDAQmx.DAQmx_Val_FiniteSamps, nr_samples)
    
        ai_task.StartTask()
        ai_task.ReadAnalogF64(nr_samples, nr_samples / 1000 + 2,
                                  PyDAQmx.DAQmx_Val_GroupByChannel,
                                  data, nr_samples,
                                  PyDAQmx.byref(read), None)

        ai_task.WaitUntilTaskDone(nr_samples / 1000 + 2)
        ai_task.StopTask()
        
        return np.mean(data)

    
    


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
            
    def set_ao0_measure_ctr1(self, n_samples, sampling_rate, ao_setpoints):
        """Collect n_samples while setting ao_setpoints at sampling_rate.
        
        The number of samples must be the length of ao_setpoints.
        The setpoints are voltages withing [-4V, 4V] and the sampling
        rate cannot exceed 2MHz.
        """
        
        assert len(ao_setpoints) == n_samples
                  
        # Declaration of variables 
        ctr_taskHandle = PyDAQmx.TaskHandle()
        ao_taskHandle = PyDAQmx.TaskHandle()
        read = PyDAQmx.int32()
        written = PyDAQmx.int32()
        arraysize = PyDAQmx.uInt32(n_samples)
        n_samples_int32 = PyDAQmx.int32(-1)
        data = np.zeros((n_samples,), dtype=np.uint32)
        timeout = PyDAQmx.float64(20)
        # valid terminal identifying source clock
        clock_src = '/' + self.device_name + '/ao/SampleClock'  
    
        try:
            # Create Analog Out Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ao_taskHandle))
            # It is routed to channel ao0 with range [-4, 4] Volts
            PyDAQmx.DAQmxCreateAOVoltageChan(ao_taskHandle,
                                            self.device_name + '/ao0', '',
                                            -4, 4, PyDAQmx.DAQmx_Val_Volts, '') 
            # Default clock should be ao sample clock
            PyDAQmx.DAQmxCfgSampClkTiming(ao_taskHandle, '', sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
            
            # Create Counter Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ctr_taskHandle))
            PyDAQmx.DAQmxCreateCICountEdgesChan(ctr_taskHandle,
                                                self.device_name + '/Ctr1',
                                                '', PyDAQmx.DAQmx_Val_Rising, 0,
                                                PyDAQmx.DAQmx_Val_CountUp)
            PyDAQmx.DAQmxCfgSampClkTiming(ctr_taskHandle, clock_src, sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
            
            
            PyDAQmx.DAQmxWriteAnalogF64(ao_taskHandle, n_samples, 0, 10.0, 
                                        PyDAQmx.DAQmx_Val_GroupByChannel,
                                        ao_setpoints, PyDAQmx.byref(written), None)
        
            #source = '/' + self.device_name + '/Ctr1Source'
            #destination = '/' + self.device_name + '/PFI0'
            #PyDAQmx.DAQmxConnectTerms(source,
            #                          destination,
            #                          PyDAQmx.DAQmx_Val_DoNotInvertPolarity);
                                      
            # DAQmx Start Code
            PyDAQmx.DAQmxStartTask(ctr_taskHandle)
            PyDAQmx.DAQmxStartTask(ao_taskHandle)    
            
            # DAQmx Read Code (n_samples_int32)
            PyDAQmx.DAQmxReadCounterU32(ctr_taskHandle, n_samples_int32, 10.0,
                                        data, arraysize, PyDAQmx.byref(read),
                                        None)
            
            PyDAQmx.DAQmxWaitUntilTaskDone(ao_taskHandle, timeout)
            PyDAQmx.DAQmxWaitUntilTaskDone(ctr_taskHandle, timeout)

#            print('Acquired {0} points'.format(read.value))
            
        except PyDAQmx.DAQError as err:
            print('DAQmx Error: {0}'.format(err))
            
        finally:
            if ao_taskHandle:
                try:
                    PyDAQmx.DAQmxStopTask(ao_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ao_taskHandle)
            if ctr_taskHandle:
                try: 
                    PyDAQmx.DAQmxStopTask(ctr_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ctr_taskHandle)
                
        return data
    
    
    def set_ao0_measure_ai0(self, n_samples, sampling_rate, ao_setpoints):
        """Collect n_samples while setting ao_setpoints at sampling_rate.
        
        The number of samples must be the length of ao_setpoints.
        The setpoints are voltages withing [-4V, 4V] and the sampling
        rate cannot exceed 2MHz. Input signal in [-1V, 1V].
        """
    
        # Declaration of variables 
        ai_taskHandle = PyDAQmx.TaskHandle()
        ao_taskHandle = PyDAQmx.TaskHandle()
        read = PyDAQmx.int32()
        written = PyDAQmx.int32()
        data = np.zeros(n_samples, dtype=np.float64)
        clock_src = '/Dev1/ai/SampleClock'  # valid terminal identifying source clock
        
        try:
            # Create Analog In Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ai_taskHandle))
            PyDAQmx.DAQmxCreateAIVoltageChan(ai_taskHandle, 'Dev1/ai0', '',
                                    PyDAQmx.DAQmx_Val_Diff, -1, 1,
                                    PyDAQmx.DAQmx_Val_Volts, None)
            PyDAQmx.DAQmxCfgSampClkTiming(ai_taskHandle, '', sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps,
                                          n_samples)
            
            # Create Analog Out Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ao_taskHandle))
            PyDAQmx.DAQmxCreateAOVoltageChan(ao_taskHandle, 'Dev1/ao0', '',
                                            -4, 4, PyDAQmx.DAQmx_Val_Volts, '') 
            PyDAQmx.DAQmxCfgSampClkTiming(ao_taskHandle, clock_src, sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_ContSamps, n_samples)
            
            PyDAQmx.DAQmxWriteAnalogF64(ao_taskHandle, n_samples, 0, 10.0, 
                                        PyDAQmx.DAQmx_Val_GroupByChannel,
                                        ao_setpoints, PyDAQmx.byref(written), None)
        
            # DAQmx Start Code
            PyDAQmx.DAQmxStartTask(ao_taskHandle)
            PyDAQmx.DAQmxTaskControl(ai_taskHandle,
                                    PyDAQmx.DAQmx_Val_Task_Commit)
            PyDAQmx.DAQmxStartTask(ai_taskHandle)
        
            # DAQmx Read Code
            PyDAQmx.DAQmxReadAnalogF64(ai_taskHandle, n_samples, 10.0,
                                      PyDAQmx.DAQmx_Val_GroupByChannel,
                                      data, n_samples, PyDAQmx.byref(read),
                                      None)
        
            print('Acquired {0} points'.format(read.value))
        
        
        except PyDAQmx.DAQError as err:
            print('DAQmx Error: {0}'.format(err))
            
        finally:
            if ao_taskHandle:
                try:
                    PyDAQmx.DAQmxStopTask(ao_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ao_taskHandle)
            if ai_taskHandle:
                try: 
                    PyDAQmx.DAQmxStopTask(ai_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ai_taskHandle)
                
        return data
    
    def set_ao0_measure_ctr1_ai0(self, n_samples, sampling_rate, ao_setpoints):
        """Collect n_samples while setting ao_setpoints at sampling_rate.
        
        The number of samples must be the length of ao_setpoints.
        The setpoints are voltages withing [-4V, 4V] and the sampling
        rate cannot exceed 2MHz.
        """
        
        # Declaration of variables 
        n_samples = int(n_samples)
        ctr_taskHandle = PyDAQmx.TaskHandle()
        ao_taskHandle = PyDAQmx.TaskHandle()
        ai_taskHandle = PyDAQmx.TaskHandle()
        read = PyDAQmx.int32()
        written = PyDAQmx.int32()
        arraysize = PyDAQmx.uInt32(n_samples)
        n_samples_int32 = PyDAQmx.int32(n_samples)
        counts = np.zeros(n_samples, dtype=np.uint32)
        voltages = np.zeros(n_samples, dtype=np.float64)
        # valid terminal identifying source clock
        clock_src = '/Dev1/ao/SampleClock'  
    
        try:
            # Create Analog Out Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ao_taskHandle))
            # It is routed to channel ao0 with range [-4, 4] Volts
            PyDAQmx.DAQmxCreateAOVoltageChan(ao_taskHandle, 'Dev1/ao0', '',
                                            -4, 4, PyDAQmx.DAQmx_Val_Volts, '') 
            # Default clock should be ao sample clock
            PyDAQmx.DAQmxCfgSampClkTiming(ao_taskHandle, '', sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
            
            # Create Analog In Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ai_taskHandle))
            PyDAQmx.DAQmxCreateAIVoltageChan(ai_taskHandle, 'Dev1/ai0', '',
                                    PyDAQmx.DAQmx_Val_Diff, -10, 10,
                                    PyDAQmx.DAQmx_Val_Volts, None)
            PyDAQmx.DAQmxCfgSampClkTiming(ai_taskHandle, clock_src,
                                          sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps,
                                          n_samples)
            # Create Counter Task
            PyDAQmx.DAQmxCreateTask('', PyDAQmx.byref(ctr_taskHandle))
            PyDAQmx.DAQmxCreateCICountEdgesChan(ctr_taskHandle, 'Dev1/Ctr1',
                                                '', PyDAQmx.DAQmx_Val_Rising, 0,
                                                PyDAQmx.DAQmx_Val_CountUp)
            PyDAQmx.DAQmxCfgSampClkTiming(ctr_taskHandle, clock_src, sampling_rate,
                                          PyDAQmx.DAQmx_Val_Rising,
                                          PyDAQmx.DAQmx_Val_FiniteSamps, n_samples)
            
            
            PyDAQmx.DAQmxWriteAnalogF64(ao_taskHandle, n_samples, 0, 10.0, 
                                        PyDAQmx.DAQmx_Val_GroupByChannel,
                                        ao_setpoints, PyDAQmx.byref(written), None)
        
            # DAQmx Start Code
            PyDAQmx.DAQmxStartTask(ctr_taskHandle)
            PyDAQmx.DAQmxStartTask(ai_taskHandle)
            PyDAQmx.DAQmxStartTask(ao_taskHandle)    
        
            # DAQmx Read Code
            PyDAQmx.DAQmxReadCounterU32(ctr_taskHandle, n_samples_int32, 10.0,
                                        counts, arraysize, PyDAQmx.byref(read),
                                        None)
            
            PyDAQmx.DAQmxReadAnalogF64(ai_taskHandle, n_samples, 10.0,
                                      PyDAQmx.DAQmx_Val_GroupByChannel,
                                      voltages, n_samples, PyDAQmx.byref(read),
                                      None)
        
            print('Acquired {0} points'.format(read.value))
            
        except PyDAQmx.DAQError as err:
            print('DAQmx Error: {0}'.format(err))
            
        finally:
            if ao_taskHandle:
                try:
                    PyDAQmx.DAQmxStopTask(ao_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ao_taskHandle)
            if ctr_taskHandle:
                try: 
                    PyDAQmx.DAQmxStopTask(ctr_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ctr_taskHandle)
            if ai_taskHandle:
                try:
                    PyDAQmx.DAQmxStopTask(ai_taskHandle)
                finally:
                    PyDAQmx.DAQmxClearTask(ai_taskHandle)
                
        return counts, voltages


if __name__ == '__main__':
    object_dict = {
        'NIDAQ': NIDAQ()
        }
    nw_utils.RunServer(object_dict)