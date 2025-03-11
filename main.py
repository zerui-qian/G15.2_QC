import sys
# sys.path.append(r'C:\Users\QPG\Documents\eyazici_g15\drivers')
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base')
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base\zq_drivers')

from zq_experiment_base import *
from zq_utility import *
from device_manager import *
from daq_February2025 import *

import warnings
import numpy as np
import xarray as xr

### ============================= PARAMETERS ============================= ###

'''HP 4142B'''

def hp_current_getter(SMU):
    '''
    Wrapper to cirumvent HP readout buffer issue

    Parameters
    ----------
    SMU : HP4241B SMU object 
        e.g. hp.SMU1

    Returns
    -------
    float : Current in A

    '''
    with warnings.catch_warnings(action="ignore"): # ignore HP warning in _read_IV
        samples = []
        for i in range(5):
            if i > 2:
                samples.append(SMU.get_current())
            time.sleep(0.1)
        return np.mean(samples[:])

# Current in nA for the parameters 

# # SMU 1
# # Check init_settings for safety features
V1  = Param("V_SMU1", units = 'V', 
    getter = hp.SMU1.get_voltage,
    setter = lambda val: hp.SMU1.set_voltage(val)
    ) if not('hp' not in globals() or hp is None) else None

I1  = Param("I_SMU1", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU1)*1e9) if not('hp' not in globals() or hp is None) else None

# # SMU 3
# # Check init_settings for safety features
V3  = Param("V_SMU3", units = 'V', 
    getter = hp.SMU3.get_voltage,
    setter = lambda val: hp.SMU3.set_voltage(val)) if not('hp' not in globals() or hp is None) else None
            
I3  = Param("I_SMU3", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU3)*1e9) if not('hp' not in globals() or hp is None) else None

# # SMU 4
# # Check init_settings for safety features
V4  = Param("V_SMU4", units = 'V', 
    getter = hp.SMU4.get_voltage,
    setter = lambda val: hp.SMU4.set_voltage(val)) if not('hp' not in globals() or hp is None) else None
            
I4  = Param("I_SMU4", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU4)*1e9) if not('hp' not in globals() or hp is None) else None


def v_134_setter(val):
    hp.SMU1.set_voltage(val)
    time.sleep(0.05)
    hp.SMU3.set_voltage(val)
    time.sleep(0.05)
    hp.SMU4.set_voltage(val)
    time.sleep(0.05)

Vall = Param("V_134", units = 'V', 
    getter = hp.SMU3.get_voltage,
    setter = v_134_setter) if not('hp' not in globals() or hp is None) else None

''' GATE VOLTAGES '''

# These are safe with some margin.
VTG_SAFE_MIN = -15
VTG_SAFE_MAX = 15

def Vtg_setter(val):
    if val > VTG_SAFE_MAX or val < VTG_SAFE_MIN:
        raise ValueError(f"Trying to set Vtg outside safe limits : {val} V")
    else:
        hp.SMU1.set_voltage(val)

Vtg  = Param("Vtg", units = 'V', 
    getter = hp.SMU1.get_voltage,
    setter = Vtg_setter) if not('hp' not in globals() or hp is None) else None

Itg  = Param("Itg", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU1)*1e9) if not('hp' not in globals() or hp is None) else None


VL_SAFE_MIN = -14
VL_SAFE_MAX = +14

def VL_setter(val):
    if val > VL_SAFE_MAX or val < VL_SAFE_MIN:
        raise ValueError(f"Trying to set VL outside safe limits : {val} V")
    else:
        hp.SMU3.set_voltage(val)

VL  = Param("VL", units = 'V', 
    getter = hp.SMU3.get_voltage,
    setter = VL_setter) if not('hp' not in globals() or hp is None) else None

IL  = Param("IL", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU3)*1e9) if not('hp' not in globals() or hp is None) else None


VR_SAFE_MIN = -14
VR_SAFE_MAX = +14

def VR_setter(val):
    if val > VR_SAFE_MAX or val < VR_SAFE_MIN:
        raise ValueError(f"Trying to set VR outside safe limits : {val} V")
    else:
        hp.SMU4.set_voltage(val)

VR  = Param("VR", units = 'V', 
    getter = hp.SMU4.get_voltage,
    setter = VR_setter) if not('hp' not in globals() or hp is None) else None

IR  = Param("IR", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU4)*1e9) if not('hp' not in globals() or hp is None) else None


''' Vdiff , Vsum Basis  '''
''' Vdiff = VL - VR     '''
''' Vsum =  VL + VR     '''

# if VL is not None and VR is not None:
#     def Vdiff_getter():
#         return VL.getter() - VR.getter()
#     def Vsum_getter():
#         return VL.getter() + VR.getter()

#     VLR_INCR_STEP = 1
#     def Vdiff_setter(Vdiff_new):
#         '''
#         Symetrically increments Vdiff to a new value. This is to make sure
#         we don't introduce large asymmetry on the gated region while
#         ramping Vdiff.
        
#         Parameters
#         ----------
#         Vdiff_new : Desired value of Vdiff.

#         Returns
#         -------
#         None.

#         '''
        
#         VL_act = VL.getter()
#         VR_act = VR.getter()
#         Vdiff_act = VL_act - VR_act
#         Vsum_act = VL_act + VR_act
#         incr_direction = np.sign(Vdiff_new - Vdiff_act)
        
#         VL_new = 0.5*(Vdiff_new + Vsum_act)
#         VR_new = 0.5*(-Vdiff_new + Vsum_act)
        
#         if VL_new > VL_SAFE_MAX or VL_new < VL_SAFE_MIN:
#             raise ValueError(f"Trying to set VL outside safe limits : {VL_new} V")

#         if VR_new > VR_SAFE_MAX or VR_new < VR_SAFE_MIN:
#             raise ValueError(f"Trying to set VR outside safe limits : {VR_new} V")

#         # Increment VL and VR until Vdiff is within one increment step
#         while (np.abs(Vdiff_new - Vdiff_act) > 2 * VLR_INCR_STEP):
#             VL_next = VL_act + incr_direction*VLR_INCR_STEP
#             VR_next = VR_act - incr_direction*VLR_INCR_STEP
            
#             VL.setter(VL_next)
#             VL_act = VL_next
#             VR.setter(VR_next)
#             VR_act = VR_next

#             Vdiff_act = VL_act - VR_act
    
#         # Set the exact values
#         VL.setter(VL_new)
#         VR.setter(VR_new)

#     def Vsum_setter(Vsum_new):
#         '''
#         Symetrically increments Vsum to a new value. This is to make sure
#         we don't introduce large asymmetry on the gated region while
#         ramping Vsum.
        
#         Parameters
#         ----------
#         Vsum_new : Desired value of Vsum

#         Returns
#         -------
#         None.

#         '''
        
#         VL_act = VL.getter()
#         VR_act = VR.getter()
#         Vdiff_act = VL_act - VR_act
#         Vsum_act = VL_act + VR_act
#         incr_direction = np.sign(Vsum_new - Vsum_act)
        
#         VL_new = 0.5*(Vdiff_act + Vsum_new)
#         VR_new = 0.5*(-Vdiff_act + Vsum_new)
        
#         if VL_new > VL_SAFE_MAX or VL_new < VL_SAFE_MIN:
#             raise ValueError(f"Trying to set VL outside safe limits : {VL_new} V")

#         if VR_new > VR_SAFE_MAX or VR_new < VR_SAFE_MIN:
#             raise ValueError(f"Trying to set VR outside safe limits : {VR_new} V")

#         # Increment VL and VR until Vdiff is within one increment step
#         while (np.abs(Vsum_new - Vsum_act) > 2 * VLR_INCR_STEP):
#             VL_next = VL_act + incr_direction*VLR_INCR_STEP
#             VR_next = VR_act + incr_direction*VLR_INCR_STEP
            
#             VL.setter(VL_next)
#             VL_act = VL_next
#             VR.setter(VR_next)
#             VR_act = VR_next

#             Vsum_act = VL_act + VR_act
    
#         # Set the exact values
#         VL.setter(VL_new)
#         VR.setter(VR_new)

#     Vdiff = Param('Vdiff', units = 'V', long_name = 'VL - VR',
#                   getter = Vdiff_getter, setter = Vdiff_setter)        
    
#     Vsum = Param('Vsum', units = 'V', long_name = 'VL + VR',
#                   getter = Vsum_getter, setter = Vsum_setter)

''' LightField '''

# if lf is not None:
   
#     def spec_getter():
#         '''get spectrum function to read wavelengths only once per measurement'''
#         ''' record a spectrum in the Xarray format
#         returns: da[Frame, Wavelength]
#         '''        
#         spectra, wl = lf.get_spectrum()
#         spectra = np.array(spectra,dtype=float)
#         wl = np.array(wl,dtype=float)
#         frame_num = spectra.shape[0]
#         roi_num = spectra.shape[-1]
#         da = xr.DataArray(spectra, 
#             coords={'Frame': np.arange(frame_num), 'Wavelength': wl},
#             dims = ('Frame', 'Wavelength'))
#         da.attrs['units'] = 'counts'
#         da.attrs['long_name'] = 'Intensity'
#         da.Wavelength.attrs['units'] = 'nm'
#         return da
    
#     def wlen_getter():
#         curr_exp = ExposTime.getter()
#         curr_frames = NumFrames.getter()
#         ExposTime.setter(0.01)
#         NumFrames.setter(1)
#         spectra, wl = lf.get_spectrum()
#         ExposTime.setter(curr_exp)
#         NumFrames.setter(curr_frames)
#         return wl
    
        
#     Spec = Param("Spec", units = 'counts', long_name = 'Intensity', 
#         getter = spec_getter) if not('lf' not in globals() or lf is None) else None
#     Wlen = Param("Wlen", units = 'nm', long_name = 'Wavelengths', 
#         getter = wlen_getter) if not('lf' not in globals() or lf is None ) else None
    
#     ExposTime = Param("ExposTime", units = 's', long_name = 'Exposure time', 
#         getter = lf.get_exposure_time, 
#         setter = lf.set_exposure_time) if not('lf' not in globals() or lf is None ) else None
#     CentWavelen = Param("CentWavelen", units = 'nm', long_name = 'Center wavelength', 
#         getter = lf.get_wavelength, 
#         setter = lf.set_wavelength) if not('lf' not in globals() or lf is None ) else None
#     CCD_Temp = Param("CCD_Temperature", units = 'deg', long_name = 'CCD temperature', 
#         getter = lf.get_temperature ) if not('lf' not in globals() or lf is None ) else None
#     Spec_Inten_sum = Param("Intensity_sum", 
#         getter = (lambda : np.sum(Spec.pv.data)) if ('Spec' in locals()) else None )
    
#     NumFrames = Param("NumFrames", long_name = 'Frame numbers', 
#         getter = lf.get_num_frames,
#         setter = lf.set_num_frames) if not('lf' not in globals() or lf is None ) else None    

''' WinSpec '''

if ws is not None:
   
    def spec_getter():
        '''get spectrum function to read wavelengths only once per measurement'''
        ''' record a spectrum in the Xarray format
        returns: da[Frame, Wavelength]
        '''        
        if not hasattr(Wlen,'pv') or Wlen.pv is None:
            Wlen.meas()
        
        spectra = ws.get_spectrum(wlen=False, dt_loop = 0.1)
        spectra = np.array(spectra).astype('uint16')[:,:,0]
        wl = Wlen.pv
        frame_num = spectra.shape[0]
        # roi_num = spectra.shape[-1]
        da = xr.DataArray(spectra, 
            coords={'Frame': np.arange(frame_num).astype('uint16'), 'Wavelength': Wlen.pv},
            dims = ('Frame', 'Wavelength'))        
        da.attrs['units'] = 'counts'
        da.attrs['long_name'] = 'Intensity'
        da.Wavelength.attrs['units'] = 'nm'
        return da
    
    def wlen_getter():
        curr_exp = ExposTime.getter()
        curr_frames = NumFrames.getter()
        ExposTime.setter(0.01)
        NumFrames.setter(1)
        spectra, wl = ws.get_spectrum(wlen = True)
        ExposTime.setter(curr_exp)
        NumFrames.setter(curr_frames)
        return np.array(wl,dtype = float)
    
        
    Spec = Param("Spec", units = 'counts', long_name = 'Intensity', 
        getter = spec_getter) if not('ws' not in globals() or ws is None) else None
    Wlen = Param("Wlen", units = 'nm', long_name = 'Wavelengths', 
        getter = wlen_getter) if not('ws' not in globals() or ws is None ) else None
    
    ExposTime = Param("ExposTime", units = 's', long_name = 'Exposure time', 
        getter = lambda: ws.exposure_time, 
        setter = (lambda x: setattr(ws,'exposure_time',x))) if not('ws' not in globals() or ws is None ) else None
    CentWavelen = Param("CentWavelen", units = 'nm', long_name = 'Center wavelength', 
        getter = lambda: ws.wavelength, 
        setter = lambda x: setattr(ws,'wavelength',x)) if not('ws' not in globals() or ws is None ) else None
    CCD_Temp = Param("CCD_Temperature", units = 'deg', long_name = 'CCD temperature', 
        getter = lambda: ws.temperature ) if not('ws' not in globals() or ws is None ) else None
    Spec_Inten_sum = Param("Intensity_sum", 
        getter = (lambda : np.sum(Spec.pv.data)) if ('Spec' in locals()) else None )
    
    NumFrames = Param("NumFrames", long_name = 'Frame numbers', 
        getter = lambda: ws.num_frames,
        setter = (lambda x: setattr(ws,'num_frames',x))) if not('ws' not in globals() or ws is None ) else None    


''' DAQ Card '''

SCx = Param("ScannerX", units = 'V',
            getter = lambda: daq.ao1 * 15,
            setter = lambda val: daq.set_ao1(val/15))
SCy = Param("ScannerY", units = 'V',
            getter = lambda: daq.ao2 * 15,
            setter = lambda val: daq.set_ao2(val/15))

P_det = Param("Power", units = 'muW',
            getter = lambda: daq.measure_ai(ai_channel=1)[0])
P_in = Param("Power", units = 'mW',
            getter = lambda: -1.0281913515947234 * np.tanh(1.85999284283525 * (daq.ao0 - 1.7360840044990562)) + 1.0031464148496454,
            setter = lambda val: daq.set_ao0(0.49528206859044854 * np.arctanh(-0.9949420499964587 * (val - 0.9933539705788575)) + 1.7458937905819318))

c_APD = Param("Counts", units = 'counts',
            getter = lambda: get_one_ctrate(sampling_rate=3e4, acq_time=0.05, channel='ctr2', device = 'Dev1/'))

''' ELL Angle '''
ell1_angle = Param("ELL1 Angle", units = 'deg',
            getter = lambda: ell1.angle,
            setter = lambda val: setattr(ell1, 'angle', val))
ell2_angle = Param("ELL2 Angle", units = 'deg',
            getter = lambda: ell2.angle,
            setter = lambda val: setattr(ell2, 'angle', val))
ell3_angle = Param("ELL3 Angle", units = 'deg',
            getter = lambda: ell3.angle,
            setter = lambda val: setattr(ell3, 'angle', val))



### ============================== ROUTINES ============================== ###

def set_hp_V_defaults(SMU):
    SMU.set_source_mode('Voltage')
    SMU.set_voltage_output_range(40)
    SMU.set_voltage_limit(20)
    SMU.set_voltage_safe_step(0.025)
    SMU.set_current_compliance(0.1e-6)
    print('SMU at {}'.format(SMU))
    print( SMU.get_unit_settings() )

def init_settings():
    print("Initializing measurement settings")
    if hp is not None:
        #    SMU1 init
        set_hp_V_defaults(hp.SMU1)
        #    SMU3 init
        set_hp_V_defaults(hp.SMU3)
        #    SMU4 init
        set_hp_V_defaults(hp.SMU4)
    time.sleep(0.1)

def set_zero():
    print("Setting to zero...")
    hp.SMU1.set_voltage(0)
    hp.SMU3.set_voltage(0)
    hp.SMU4.set_voltage(0)




### ================================ MAIN ================================ ###

# if __name__ == "__main__":

#     # DATAPATH = r'C:\Users\QPG\Documents\eyazici_g15\data\leakage_test'
#     DATAPATH = r'C:\Users\QPG\Documents\zerui_g15\C-hBN\data\PL'
#     # DATAPATH = r'C:\Users\QPG\Documents\eyazici_g15\data\white_light'
#     # REMOTEPATH = r'Z:\Users\eyazici\_Data_0D\data_g15_2\white_light'
#     COMMENT = 'f18'
    
    
#     # init_settings()
    
    
#     param_plots = [
#                     # ('Plot1', Vdiff, Itg),
#                     # ('Plot2', Vdiff, IL),
#                     # ('Plot3', Vdiff, IR),
#                     # ('Plot2', VL, Itg),
#                     # ('Plot3', VL, IR),
#                     # ('Plot1', V1, I1),
#                     # ('Plot5', Vdiff, IR),
#                     ]
#     # For now we have to measure parameters that are live plotted
#     for p1,p2,p3 in param_plots:
#         p2.meas();p3.meas();
    
#     sweep_params = [
#                     # (V1, np.linspace(0, 20, 21)),
#                     # (Vdiff, np.linspace(0, 28, 281)),
#                     (SCx, np.arange(0, 100, 1)),
#                     (SCy, np.arange(0, 100, 1)),
#                     # (Vdiff, np.linspace(0,24,241)),
                    
#                     # (ell3_angle, np.array([73.5, 73.5+45])),
#                     #(Vtg, np.linspace(-3.4, -3, 2))
#                     ]
    
#     meas_scan(sweep_params,
#                 constant_params = [
#                                     # (Vtg, -1.8),
#                                     # (Vdiff, 0),
#                                     # (Vsum, 0),
#                                     # (VL, -12),
#                                     # (VR, -12),
#                                     # (SCx, 59.5),
#                                     # (SCy, 8.5),
#                                     # (ell1_angle, 7.7),
#                                     # (ell2_angle, 81.6),
                                    
#                                     # (NumFrames, 1),
#                                     # (ExposTime, 10),
#                                     ],
#               meas_params =     [
#                                     # IR,
#                                     # IL,
#                                     P_det,
#                                     c_APD,
#                                     # Spec,
#                                     # I1,
#                                   ],
#               measdatapath=DATAPATH,
#               file_comment= COMMENT,
#               const_wait_time = 0, wait_before = 0.05, wait_after = 0.05,
#               wait_scan_line = 0,
#               wait_btw_measurements = 0.02,
#               script_path = __file__,
#               param_plot_specifiers = param_plots,
#               # remote_path = REMOTEPATH,
#               )
    
    # set_zero()
    
    
    # COMMENT_REF = 'D3_REF'
    
    # sweep_params_ref = [
    #                 (Vtg, np.linspace(6,6,1)),
    #                 # (Vtg, np.linspace(0,5,51)),
    #                 # (VR, np.linspace(0,-5,51)),
    #                 # (SCx, np.linspace(52,62,21)),
    #                 # (SCy, np.linspace(5,15,21)),
    #                 # (Vdiff, np.linspace(0,16,81)),
    #                 (ell1_angle, np.array([7.7, 52])),
    #                 # (Dummy, np.arange(1))
    #                 # (Vdiff, np.linspace(12.5,15,2)),
    #                 # (Vdiff, np.linspace(11,15,5)),
    #                 ]
    
    # meas_scan(sweep_params_ref,
    #             constant_params = [
    #                                 # (Vtg,6),
    #                                 (VL, 0),
    #                                 (VR, 0),
    #                                 (ell2_angle, 81.6),
    #                                 # (SCx, 59.5),
    #                                 # (SCy, 8.5),
                                    
    #                                 (NumFrames, 100),
    #                                 (ExposTime, 1),
    #                                 ],
    #           meas_params =     [
    #                                 # IR,
    #                                 # Itg,
    #                                 # IL,
                                    
    #                                 Spec,
    #                                 Itg,
    #                               ],
    #           measdatapath=DATAPATH,
    #           file_comment= COMMENT_REF,
    #           const_wait_time = 1, wait_before = 0.05, wait_after = 0.05,
    #           wait_scan_line = 0,
    #           wait_btw_measurements = 0.02,
    #           script_path = __file__,
    #           # param_plot_specifiers = param_plots,
    #           # remote_path = REMOTEPATH,
    #           )
    
    # set_zero()