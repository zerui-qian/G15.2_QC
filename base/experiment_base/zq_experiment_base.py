# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 19:17:18 2024

@author: eyazici

Designed to reproduce DaemonDAQ features with less clutter.
"""

import time, os, sys
import numpy as np 
from zq_utility import *
from live_plot import PlotWindow,MultiPlotter
import threading
import netCDF4 as nc4
import xarray as xr
from tqdm import tqdm
import shutil


class Param(object):
    def __init__(self, label, units = "", long_name = "", getter = None, setter = None):
        self.label = label
        self._ext_setter = setter
        self.getter = getter
        self.pv = None
        self.ConstantValue = None

        if units != "":
            self.units = units
        if long_name != "":
            self.long_name = long_name
        
        if self._ext_setter is not None:
            self.setter = self._tracking_setter
        
    def _tracking_setter(self, val):
        self._ext_setter(val)
        self.pv = val
                 
    def constant(self, ConstantValue=None):
        # there are cases where it has a constant value but no setter
        # e.g. CCD temperature if we're running two measurements in one script
        # thus check
        if ConstantValue is not None: # input value provided
            self.ConstantValue = ConstantValue
            if hasattr(self,'setter') and self.setter:
                self.setter(self.ConstantValue)
        elif hasattr(self, "ConstantValue") and self.setter: 
            self.setter(self.ConstantValue)
        elif self.getter:
            self.ConstantValue = self.getter()
        else:
            raise ValueError('{}: need to set ConstantValue or give input value'.format(self.label))
        self.pv = self.ConstantValue
        
    def meas(self):
        self.pv = self.getter()
                    
    def get_units(self):
        if hasattr(self, 'units'):
            return self.units
        else:
            return ''

    def get_long_name(self):
        if hasattr(self, 'long_name'):
            return self.long_name
        else:
            return ''
        
def init_ncfile(filename, sweep_params, meas_params, measured_data):
    sweep_lens = [len(sweep_param[1]) for sweep_param in sweep_params]

    with nc4.Dataset(filename, 'w', format = 'NETCDF4') as ncfile:
        
        md = ncfile.createGroup('main_data')

        # Define dimensions and create variables for the sweep parameters
        for sweep_param in sweep_params:
            md.createDimension(sweep_param[0].label, len(sweep_param[1]))
            var = md.createVariable(sweep_param[0].label, sweep_param[1].dtype, (sweep_param[0].label,), zlib=True)
            if hasattr(sweep_param[0], 'units'):
                var.units = sweep_param[0].units
            if hasattr(sweep_param[0], 'long_name'):
                var.long_name = sweep_param[0].long_name
            var[:] = sweep_param[1]
        # sweep_dims = md.dimensions.values()
        sweep_dims = list(md.dimensions.keys())
        
        # Create variables for measured parameters
        for imeas_param, meas_param in enumerate(meas_params):
            param_label = meas_param.label
            if type(meas_param.pv) == xr.core.dataarray.DataArray:
                for dim in meas_param.pv.coords.dims:
                    if dim not in md.dimensions.keys():
                        md.createDimension(dim, len(meas_param.pv[dim] ) )
                    coord = md.createVariable(dim, np.array(meas_param.pv[dim]).dtype, 
                                            dim, zlib=True)
                    coord[:] = meas_param.pv[dim]
                    if hasattr(meas_param.pv[dim], 'units'):
                        coord.units = meas_param.units
                    if hasattr(meas_param.pv[dim], 'long_name'):
                        coord.long_name = meas_param.long_name
                var = md.createVariable(param_label, np.array(meas_param.pv).dtype, 
                                        sweep_dims + list(meas_param.pv.dims), zlib=True)
            else:
                var = md.createVariable(param_label, np.array(meas_param.pv).dtype, 
                                        sweep_dims, zlib=True)
            if hasattr(meas_param, 'units'):
                var.units = meas_param.units
            if hasattr(meas_param, 'long_name'):
                var.long_name = meas_param.long_name
        
            new_data = measured_data[imeas_param]            
            md[param_label][:] = new_data
    

def save_to_disk(filename, meas_params, sweep_lens, measured_data, save_index):
    with nc4.Dataset(filename, 'r+', clobber = True) as ncfile:
        md = ncfile.groups['main_data'] 
        index = np.unravel_index(save_index, sweep_lens)
        for imeas_param, meas_param in enumerate(meas_params):
            param_label = meas_param.label
            new_data = measured_data[imeas_param]
          
            old_data = md[param_label][:]
            old_data[index] = new_data
            md[param_label][:] = old_data

Dummy = Param(
    label = 'Dummy', 
    long_name = 'Dummy parameter for testing purposes',
    getter = (lambda: 0),
    setter = (lambda x: x),
    )


def make_default_params():
    time0 = time.time()
    Time = Param("Time (s)", long_name = "Time since the start of the experiment (seconds)",
                 getter = lambda: time.time() - time0)
    
    return [Time]


class ParamPlot(PlotWindow):
    def __init__(self, plot_label: str, x_param : Param, y_param : Param):
        self.title = f"{y_param.label} vs. {x_param.label}"
        self.plot_label = plot_label
        
        self.xlabel = x_param.label
        if hasattr(x_param, 'units'):
            self.xlabel += f" ({x_param.units})"
        self.ylabel = y_param.label
        if hasattr(y_param, 'units'):
            self.ylabel += f" ({y_param.units})"

        super().__init__(self.title, self.xlabel, self.ylabel)

        # Don't remeasure, always use last measured value
        self.x_getter = lambda : x_param.pv
        self.y_getter = lambda : y_param.pv
    
    def update_xy(self):
        super().update_xy(self.x_getter(), self.y_getter())
        # super().update_plot()

def proc_live_plots(mp, param_plot_specifiers):
    mp.initialize()
    for plot_label, x_param, y_param in param_plot_specifiers:
        mp.add_plot(plot_label, ParamPlot(plot_label, x_param, y_param))
    mp.main_loop()


def meas_scan(sweep_params, constant_params = None, meas_params = None, 
              file_comment = '', measdatapath = '',
              const_wait_time = 1, wait_before = 0.05, wait_after = 0.05,
              wait_scan_line = 1,
              wait_btw_measurements = 0.01,
              script_path = __file__,
              param_plot_specifiers = None,
              remote_path = None,
              ):
    """


    Parameters
    ----------
    sweep_params : [(Param, sweep_values)]
        Parameters that will be sweeped over during the experiment.
        The sweeping is done in sawtooth direction and last to first
        entry in the list.
    constant_params : [(Param,constant_value)], optional
        Parameters that will be set to a constant value at the start of the
        experiment 
        The default is None.
    meas_params : [Param], optional
        Parameters that will be measured at each sweep instance. 
        The default is None.
    file_comment : string, optional
        Comment that will be added to the measurement file name. 
        The default is ''.
    measdatapath : string, optional
        Path where the data will be stored. The default is ''.
    const_wait_time : float, optional
        Wait time (in s) after setting the constants. The default is 1.
    wait_before : float, optional
        Wait time (in s) before measuring for each sweep. The default is 0.05.
    wait_after : float, optional
        Wait time (in s) after measuring for each sweep. The default is 0.05.
    wait_scan_line : float, optional
        Wait time (in s) after each return to first value of a parameter
        in a multidimensional sweep. This is useful when sweeping over gate 
        voltages when waiting for the voltage to settle after a large swing
        is necessary.
        The default is 1.
    wait_btw_measurements : float, optional
        Wait time (in s) after each parameter measurements. 
        This solves device communication issues when two successive 
        measurements are made on the same device.
        The default is 0.01.
    script_path : string, optional
        Specify the path to the file that will be copied alongside the data.
        Passing __file__ explicitly will copy the script that the funciton is
        called from.
    param_plot_specifiers: [(string, Param, Param)]
        Give a list of 3-tuples that specify parameters to be plotted.
        For each tuple (label, Param1, Param2), a plot is generated with 
        Param1 on x axis and Param2 on y axis.
        For addional info on plotting algorithm check live_plot.py

    Returns
    -------
    None.

    """    

    if sweep_params is None:
        sweep_params = [(Dummy, [0,1])]
    else:
        sweep_dim = len(sweep_params)
    
    # Set constant parameters to their starting value
    if constant_params is not None:
        print("Setting constants.")
        for par, val in constant_params:
            par.constant(val) 
            if hasattr(par, 'units'): 
                print (f"{par.label} set to constant: {val} {par.units}")
            else:   
                print (f"{par.label} set to constant: {val}")
                
    print("Wait after setting constants")
    time.sleep(const_wait_time)
    print("Constants set to starting value")

    default_params = make_default_params()
    meas_params.extend(default_params)
    
    measname = ''
    for sweep_dim, scan_range in sweep_params:
        measname = measname + f"_scan{sweep_dim.label}_{scan_range[0]}_{scan_range[-1]}"
    if constant_params:
        for const_var, const_val in constant_params:
            measname = measname + f"_{const_var.label}_{const_val}"
#     print('measname: %s'%measname)
    measname = measname + f"_{file_comment}"
    filedir = generate_filedir(suffix = measname, base_dir = measdatapath)
    filename = os.path.join(filedir, "Measdata.nc")

    # Copy the running script to where data will be stored
    shutil.copyfile(script_path, os.path.join(filedir, "Experiment.py"))
    
    tQt = None
    mp = None
    # Create param plots if any
    HAS_PLOTS = param_plot_specifiers is not None
    if HAS_PLOTS:
        # redefine time string to time parameter
        param_plot_specifiers = [ (label, default_params[0], p2) if p1 == 'Time' or p1 == 'time' 
                                 else (label,p1,p2) for label, p1, p2 in param_plot_specifiers]
        
        mp = MultiPlotter()
        try:
            tQt = threading.Thread(target=proc_live_plots, args=([mp, param_plot_specifiers]), daemon = True)
            tQt.start()
        except e:
            print(f"Plotter thread failed: \n{e}")
        time.sleep(1)

    # Create necessary variables to loop over the sweep parameters
    sweep_lens = [len(sweep_param[1]) for sweep_param in sweep_params]
    total_len = np.prod(sweep_lens) # total length of sweep
    param_ctr = np.array(total_len/np.cumprod(sweep_lens),dtype = int) # counter that shows index at which each parameter should be changed
    
    measured_data = []
    
    # print(f"Sweep lens =  {sweep_lens}")    
    for sweep_index in tqdm(range(total_len)):
    # for sweep_index in (range(total_len)):
        # Set the sweep parameters to their next value using some algebra for indices
        for param_index, param_ct in enumerate(param_ctr):
            if sweep_index%param_ct == 0:
                sweep_params[param_index][0].setter(sweep_params[param_index][1][sweep_index//param_ct % sweep_lens[param_index]])
        
        time.sleep(wait_before)
        # Store the value of measured parameters in memory
        for i_param, param in enumerate(meas_params):
            param.meas()
            if sweep_index == 0:
                measured_data.append(np.empty((sweep_lens[-1],) + np.array(param.pv).shape))
            measured_data[i_param][sweep_index % sweep_lens[-1]] = param.pv
            time.sleep(wait_btw_measurements)
        time.sleep(wait_after)
        
        # Plot data if necessary
        if HAS_PLOTS:
            try:
                for param_plot in mp._plot_windows.values():
                    param_plot.update_xy()
            except:
                return -1
            
        # I initialize the data file here so we know the dataype of the 
        # measured variables.
        if sweep_index == 0:
            init_ncfile(filename, sweep_params,meas_params,measured_data)
        # Line end opreations
        elif (sweep_index+1) % sweep_lens[-1] == 0:
            time.sleep(wait_scan_line)
            # Save data after each line
            last_line_idx = np.arange((sweep_index+1) - sweep_lens[-1], (sweep_index+1))
            save_to_disk(filename, meas_params, sweep_lens, measured_data, last_line_idx)

    if HAS_PLOTS:
        # print("Closing plots")
        mp.close()
    
    if remote_path is not None:
        remote_filedir = generate_filedir(suffix = measname, base_dir = remote_path)
        remote_filename = os.path.join(remote_filedir, "Measdata.nc")
        try:
            shutil.copyfile(os.path.join(filedir, "Experiment.py"), os.path.join(remote_filedir, "Experiment.py"))
            shutil.copyfile(filename, remote_filename)
        except:
            print("COULD NOT UPLOAD TO REMOTE!")    

if __name__ == "__main__":
    
    Dummy_val = 0.
    
    def Dummy_setter(x):
        global Dummy_val
        Dummy_val += 1
        # print(f"Called setter with argument {x}, dummy_val = {Dummy_val}")
        # Dummy_val = Dummy_val**2/(Dummy_val + 3)
    
    def Dummy_getter():
        global Dummy_val
        return Dummy_val
    
    Dummy1 = Param(
        label = 'Dummy1', 
        long_name = 'Dummy parameter for testing purposes',
        getter = Dummy_getter,
        setter = Dummy_setter,
        units = 'au'
        )

    Dummy2 = Param(
        label = 'Dummy2', 
        long_name = 'Dummy parameter for testing purposes',
        # getter = (lambda: print("Dummy2 getter")),
        setter = Dummy_setter,
        )
    
    Dummy_meas = Param(
        label = 'Dummy_meas',
        long_name = 'Dummy parameter for testing purposes',
        getter = Dummy_getter,
        setter = Dummy_setter,
        )

    plot1 = ("TEST", Dummy2, Dummy_meas)
    plot2 = ("TEST 2", Dummy1, Dummy2)

    Dummy1.meas()
    Dummy_meas.meas()

    measured = meas_scan([
        (Dummy1, np.linspace(0,1,2)),
        (Dummy2, np.linspace(2,3,30)),
        ],
        meas_params = [Dummy_meas],
        const_wait_time = 0,
        wait_scan_line=0.5,
        wait_before=0.01,
        wait_after = 1,
        wait_btw_measurements = 0.01,
        file_comment='comment',
        measdatapath = r'C:\Users\QPG G8.1\Documents\Python Scripts\QOTSM\data\test_data\script',
        param_plot_specifiers=[plot1, plot2]
        )