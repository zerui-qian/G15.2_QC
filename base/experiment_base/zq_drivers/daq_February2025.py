# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 16:14:38 2025

@author: QPG G8.1
"""

import nidaqmx
from nidaqmx.constants import AcquisitionType, Edge


def daq_set_ao0(voltage):
    """Set voltage going to nf power setpoint. Takes 3.1 ms!."""
    with nidaqmx.Task() as vTask:
        vTask.ao_channels.add_ao_voltage_chan('Dev1/ao0')
        vTask.write(voltage, auto_start=True)
        vTask.stop()


def daq_set_ao1(voltage):
    """Set voltage going to FPGA AI0. Takes 3.1 ms!."""
    with nidaqmx.Task() as vTask:
        vTask.ao_channels.add_ao_voltage_chan('Dev1/ao1')
        vTask.write(voltage, auto_start=True)
        vTask.stop()

def daq_set_ao2(voltage):
    """Set voltage going to FPGA AI0. Takes 3.1 ms!."""
    with nidaqmx.Task() as vTask:
        vTask.ao_channels.add_ao_voltage_chan('Dev1/ao2')
        vTask.write(voltage, auto_start=True)
        vTask.stop()        


def get_one_ctrs(sampling_rate=3e5, acq_time=0.05, channel='ctr0', device = 'Dev1/'):
    '''Read a single counter channel from the daq card.'''
    sampling_rate = int(sampling_rate)
    num_points = int(sampling_rate*acq_time)
    with nidaqmx.Task() as CtrTask1, nidaqmx.Task() as CtrTask2, nidaqmx.Task() as ClkTask:
        CtrTask1.ci_channels.add_ci_count_edges_chan(device+channel, edge=Edge.RISING)
        ClkTask.ai_channels.add_ai_voltage_chan(device + 'ai2')

        ClkTask.timing.cfg_samp_clk_timing(sampling_rate, samps_per_chan=num_points,
                                           sample_mode=AcquisitionType.FINITE, source='')
        CtrTask1.timing.cfg_samp_clk_timing(sampling_rate, samps_per_chan=num_points,
                                           sample_mode=AcquisitionType.FINITE, source='/'+ device +'ai/SampleClock')
        CtrTask1.start()
        ClkTask.start()
        Cntr1 = CtrTask1.read(number_of_samples_per_channel=num_points, timeout=acq_time*1.1)
        ClkTask.stop()
        CtrTask1.stop()
    return Cntr1

def get_one_ctrate(sampling_rate=3e3, acq_time=0.5, channel='ctr2', device = 'Dev1/'):
    return get_one_ctrs(sampling_rate=sampling_rate, acq_time=acq_time,
                        channel=channel, device = device)[-1] / acq_time 
