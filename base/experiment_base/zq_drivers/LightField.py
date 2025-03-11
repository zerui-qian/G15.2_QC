# -*- coding: utf-8 -*-
"""
Created on Thu June 15 ‏‎21:24:13 2017

@author: Yuya Shimazaki
"""

from __future__ import division, print_function
import sys
import clr # pythonnet
import time
import System
from System.Collections.Generic import List
import numpy as np
import xarray as xr

import DaemonDAQ.Network.nw_utils as nw_utils

automation_path = 'C:\Program Files\Princeton Instruments\LightField\PrincetonInstruments.LightField.AutomationV4.dll'
addin_path = 'C:\Program Files\Princeton Instruments\LightField\AddInViews\PrincetonInstruments.LightFieldViewV4.dll'
support_path = 'C:\Program Files\Princeton Instruments\LightField\PrincetonInstruments.LightFieldAddInSupportServices.dll'

clr.AddReference(addin_path)
from PrincetonInstruments.LightField import AddIns
clr.AddReference(automation_path)
from PrincetonInstruments.LightField import Automation
clr.AddReference(support_path)
#print(dir(AddIns.ExperimentSettings))
#print(dir(AddIns.CameraSettings))
#print(dir(AddIns.SpectrometerSettings))

class LightField(object):
    def __init__(self, GUI_visible):
        self.addinbase = AddIns.AddInBase()
        print("LightField turn ON")
        time.sleep(1.0)
        print("Loading experiment ...")
        self.automation = Automation.Automation(GUI_visible, List[System.String]())
        print("Load finished")
        self._app = self.automation.LightFieldApplication        
        self._exp = self._app.Experiment
        #print(dir(self._exp))

    def initialize(self):
        self._exp.Stop()    
        time.sleep(0.5)    #200ms -> LightField Freezed, 500ms -> OK

    def close(self):
        self.automation.Dispose()

    def set(self, setting, val):
        if self._exp.Exists(setting):
            if self._exp.IsValid(setting, val):
                self._exp.SetValue(setting, val)
                time.sleep(0.5)
                return self.get(setting)
            else:
                print("value not valid")
        else:
            print("operation not found/defined")
    
    def get(self, setting):
        if self._exp.Exists(setting):
            value = self._exp.GetValue(setting)
            time.sleep(0.5)
            return value

    def load_experiment(self, val):
        self._exp.Load(val)
    
    def get_exposure_time(self):
        return self.get(AddIns.CameraSettings.ShutterTimingExposureTime)/1000.0
        
    def set_exposure_time(self, val): # Exposure time in sec
#        print('Set ExposTime')
        return self.set(AddIns.CameraSettings.ShutterTimingExposureTime, val * 1000)/1000.0
    
    def get_num_frames(self):
        return self.get(AddIns.ExperimentSettings.FrameSettingsFramesToStore)
    
    def set_num_frames(self, val):
#        print('Set NumFrames')
        return self.set(AddIns.ExperimentSettings.FrameSettingsFramesToStore, val) 
   
    def get_file_name(self):
        return self.get(AddIns.ExperimentSettings.FileNameGenerationBaseFileName)
    
    def set_file_name(self,fname):
        return self.set(AddIns.ExperimentSettings.FileNameGenerationBaseFileName, fname)
    
    def get_wavelength(self):
        return self.get(AddIns.SpectrometerSettings.GratingCenterWavelength)

    def set_wavelength(self, val):
#        print('Set CentWavelen')
        return self.set(AddIns.SpectrometerSettings.GratingCenterWavelength, val)
    
    def get_grating(self):
        return self.get(AddIns.SpectrometerSettings.Grating)
    
    def set_grating(self, val):
        return self.set(AddIns.SpectrometerSettings.Grating, val)
            
    def get_shutter_control(self):
        """ Shutter control:

         1: Normal
         2: Always Closed
         3: Always Open
        """
        return self.get(AddIns.CameraSettings.ShutterTimingMode)
    
    def set_shutter_control(self, val):
        """ Shutter control:

         1: Normal
         2: Always Closed
         3: Always Open
        """
        assert val in [1, 2, 3]
        return self.set(AddIns.CameraSettings.ShutterTimingMode, val)
        
    def get_temperature(self):
#        print('Get CCDTemp')
        return self.get(AddIns.CameraSettings.SensorTemperatureReading)

    def get_target_temperature(self):
        return self.get(AddIns.CameraSettings.SensorTemperatureSetPoint)

    def set_target_temperature(self, val):
        return self.set(AddIns.CameraSettings.SensorTemperatureSetPoint, val)

    def get_temperature_status(self):
        status_list = ["Unlocked", "Locked"]
        return status_list[self.get(AddIns.CameraSettings.SensorTemperatureStatus) - 1]

    def get_ADC_analog_gain(self):
        gain_list = ["Low", "Medium", "High"]
        return gain_list[self.get(AddIns.CameraSettings.AdcAnalogGain) - 1]

    def get_spectrum(self):
        # Acquire -> Stop process is required before acquision, otherwise LightField freezes while acquision
        # Dummy process to reset program
        self._exp.Acquire()
        time.sleep(0.5)    #200ms -> LightField Freezed, 500ms -> OK
        self._exp.Stop()    
        time.sleep(0.5)    #200ms -> LightField Freezed, 500ms -> OK
        # Actual acquision
        self._exp.Acquire()
        accessed_wavelength = 0
        
        while self._exp.IsRunning:
            if accessed_wavelength == 0 and len(self._exp.SystemColumnCalibration) == 0:
                print('Wavelength information not available\n')
                wavelength = []
                accessed_wavelength = 1
            elif accessed_wavelength == 0:
                wavelen_len = self._exp.SystemColumnCalibration.Length
                assert(wavelen_len >= 1)
                wavelength = np.zeros(wavelen_len)
                for i in range(wavelen_len):
                    wavelength[i] = self._exp.SystemColumnCalibration.Get(i)
                accessed_wavelength = 1
        
        wavelength = () + (wavelength.tolist(),)
        
        recentfiles = self._app.FileManager.GetRecentlyAcquiredFileNames()
        lastfile = recentfiles[0]
        #print(lastfile)
        imageset = self._app.FileManager.OpenFile(lastfile, System.IO.FileAccess.Read)
        
        if imageset.Regions.Length == 1:
            spectra = []
            for i in range(imageset.Frames):
                frame = imageset.GetFrame(0,i)
                spectra.append([x for x in frame.GetData()])# concate axis = 2: need to be checked
            return (spectra,) + wavelength
    
    def get_spectrum_xr(self):
        (spectra, wavelength) = self.get_spectrum()
        frame_num = len(spectra)
        da = xr.DataArray(np.array(spectra), 
                            coords={'Frame': np.arange(frame_num), 'Wavelength': wavelength},
                            dims = ('Frame', 'Wavelength'))
        da.attrs['units'] = 'counts'
        da.attrs['long_name'] = 'Intensity'
        da.Wavelength.attrs['units'] = 'nm'
        return da

if __name__ == '__main__':
    show_GUI = True
    object_dict = {'LightField': LightField(show_GUI)}
    nw_utils.RunServer(object_dict, host = 'Pylon.dhcp.phys.ethz.ch')