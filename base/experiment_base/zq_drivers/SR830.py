# -*- coding: utf-8 -*2
'''
Python interface for the Stanford Research SR830 lock-in amplifier.
@author: Livio Ciorciaro
@author: Yuya Shimazaki
'''

import visa
import numpy as np
from DaemonDAQ.Drivers.visa_base import VISA_Instrument, ArgMap
from DaemonDAQ.Network.nameserver_client import nameserver as ns
import DaemonDAQ.Network.nw_utils as nw_utils
import time
import pandas as pd

# Create standard property for mapped parameters.
def _create_mapped_property(visastring, argmap, docstring=''):
    getter = lambda self: self._mapped_getter(visastring + '?', argmap)
    setter = lambda self, val: (self._mapped_setter(val, visastring, argmap))
    prop = property(fset = setter, fget = getter, fdel = None, doc = docstring)
    return (getter, setter, prop)

# Create property for standard parameter
def _create_property(visastring, limits=(-np.inf, np.inf),
                     type_=float, docstring=''):
    if not isinstance(type_, type):
        raise TypeError('type_ should be a type, not a function.')
    getter = lambda self: self._getter(visastring + '?', type_)
    setter = lambda self, val: self._setter(val, visastring, limits)
    prop = property(fset = setter, fget = getter, fdel = None, doc = docstring)
    return (getter, setter, prop)
#    return property(lambda self, val: self._setter(val, visastring, limits)
#        fset=lambda self, val: self._setter(val, visastring, limits),
#        fget=lambda self: self._getter(visastring + '?', type_),
#        fdel=None,
#        doc=docstring)

def step_sweep(sv_setter, pv_getter, step_getter):
        def step_sweep_wrapper(self, sv):
            pv = pv_getter(self)
            steplim = step_getter(self)
            if abs(sv - pv) > steplim:
                stepnum = int(np.ceil(abs(pv - sv)/(1.0*steplim)) + 1)
                smooth_move_vals = np.linspace(pv, sv, stepnum)
                for val in smooth_move_vals:
                    sv_setter(self, val)
                    time.sleep(0.025)
            sv_setter(self, sv)
        return step_sweep_wrapper

class SR830(VISA_Instrument):
    '''
    Python interface for the SR830 lock-in amplifier.
    '''
    def __init__(self, address, visalib='default'):
        '''
        Args:
            address (int):
                The GPIB address that was set on the device.
            visalib (string):
                Path to the visa-backend that is used. If this is 'default'
                the PyVISA ResourceManager will attempt to locate the library.
        '''
        super().__init__(address, visalib)  # Defines self.visa_handle
        self.visa_handle.write('OUTX 1')  # Set interface to GPIB
        self.visa_handle.write('FAST 0')  # Turn off fast data transfer mode

    # PARAMETERS
    # Reference and Phase
    (get_reference_phase, set_reference_phase, reference_phase) = _create_property(
        'PHAS', (-360.0, 729.99), float,
        'Get or set the reference phase in degrees. Values are rounded to '
        '0.01 deg, can be between -360 deg and 729.99 deg, and are wrapped '
        'around at +-180 deg.')
    (get_reference_source, set_reference_source, reference_source) = _create_mapped_property(
        'FMOD', ArgMap({'external': 0, 'internal': 1}),
        'Get or set the reference source ("internal" or "external").')
    (get_reference_frequency, set_reference_frequency, reference_frequency) = _create_property(
        'FREQ', (1e-3, 102e3), float,
        'Get or set the reference frequency in Hz. The value is rounded to 5 '
        'digits or 0.1 mHz, whichever is greater. The value can be between '
        '1 mHz and 102 kHz. If the harmonic number n is > 1, the limit is '
        'n * f <= 102 kHz.')

    _REF_TRIG_MAP = ArgMap(
        {
            'zero-crossing': 0,
            'TTL rising edge': 1,
            'TTL falling edge': 2
        })
    (get_reference_trigger, set_reference_trigger, reference_trigger) = _create_mapped_property('RSLP', _REF_TRIG_MAP,
        'Get or set the reference trigger ("zero-crossing", '
        '"TTL rising edge", or "TTL falling edge").')
    (get_detection_harmonic, set_detection_harmonic, detection_harmonic) = _create_property(
        'HARM', (1, 19999), int,
        'Get or set the detection harmonic n. The value can be between 1 and '
        '19999. If n * f > 102 kHz, the harmonic will be set to the largest '
        'value such thatn n * f <= 102 kHz.')
    (get_output_amplitude, set_output_amplitude, output_amplitude) = _create_property(
        'SLVL', (4e-3, 5.0), float,
        'Get or set the amplitude of the output sine. The value is rounded to '
        '2 mV and can be between 4 mV and 5 V.')
    set_output_amplitude_sweep_step = lambda self, sweep_step: setattr(self, 'output_amplitude_sweep_step', sweep_step)
    get_output_amplitude_sweep_step = lambda self: self.output_amplitude_sweep_step
    set_output_amplitude = step_sweep(sv_setter = set_output_amplitude, pv_getter = get_output_amplitude, step_getter = get_output_amplitude_sweep_step)
    output_amplitude = property(get_output_amplitude, set_output_amplitude)
    output_amplitude_sweep_step = 0.005

    # Input and Filter

    _INP_CONF_MAP = ArgMap(
        {
            'A': 0,
            'A-B': 1,
            '1 MOhm': 2,
            '100 MOhm': 3
        })
    (get_input_configuration, set_input_configuration, input_configuration) = _create_mapped_property('ISRC', _INP_CONF_MAP,
        'Get or set the input configuration: "A", "A-B", "1 MOhm", '
        '"100 MOhm". Note: Sensitivity above 20 nA requires 1 MOhm current '
        'gain.')
    (get_input_shield, set_input_shield, input_shield) = _create_mapped_property(
        'IGND', ArgMap({'floating': 0, 'ground': 1}),
        'Get or set the input shield grounding ("ground" or "floating").')
    (get_input_coupling, set_input_coupling, input_coupling) = _create_mapped_property('ICPL',
        ArgMap({'AC': 0, 'DC': 1}),
        'Get or set the input coupling ("DC" or "AC").')

    _INP_NOTCH_FILTER_MAP = ArgMap(
        {
            'none': 0,
            '50 Hz': 1,
            '100 Hz': 2,
            'both': 3
        })
    (get_input_notch_filter, set_input_notch_filter, input_notch_filter) = _create_mapped_property('ILIN',
        _INP_NOTCH_FILTER_MAP,
        'Get or set the input line notch filter status ("none", "50 Hz", '
        '"100 Hz", or "both").')

    _SENS_MAP = ArgMap({
            2e-9: 0,        50e-6: 13,
            5e-9: 1,        100e-6: 14,
            10e-9: 2,       200e-6: 15,
            20e-9: 3,       500e-6: 16,
            50e-9: 4,       1e-3: 17,
            100e-9: 5,      2e-3: 18,
            200e-9: 6,      5e-3: 19,
            500e-9: 7,      10e-3: 20,
            1e-6: 8,        20e-3: 21,
            2e-6: 9,        50e-3: 22,
            5e-6: 10,       100e-3: 23,
            10e-6: 11,      200e-3: 24,
            20e-6: 12,      500e-3: 25,
                            1.0: 26
        })
    (get_sensitivity, set_sensitivity, sensitivity) = _create_mapped_property('SENS', _SENS_MAP,
        'Get or set the sensitivity. The unit is V or uA, depending on the '
        'input configuration. Possible values:\n{}'.format(_SENS_MAP.keys()))

    _RESERVE_MODE_MAP = ArgMap(
        {
            'high reserve': 0,
            'normal': 1,
            'low noise': 2
        })
    (get_reserve_mode, set_reserve_mode, reserve_mode) = _create_mapped_property('RMOD', _RESERVE_MODE_MAP,
        'Get or set the reserve mode ("high reserve", "normal", or "low '
        'noise").')

    _TIME_CONST_MAP = ArgMap(
        {
            10e-6: 0,       1.0: 10,
            30e-6: 1,       3.0: 11,
            100e-6: 2,      10.0: 12,
            300e-6: 3,      30.0: 13,
            1e-3: 4,        100.0: 14,
            3e-3: 5,        300.0: 15,
            10e-3: 6,       1e3: 16,
            30e-3: 7,       3e3: 17,
            100e-3: 8,      10e3: 18,
            300e-3: 9,      30e3: 19
        })
    (get_time_constant, set_time_constant, time_constant) = _create_mapped_property('OFLT', _TIME_CONST_MAP,
        'Get or set the time constant in s. '
        'Possible values:\n{}'.format(sorted(_TIME_CONST_MAP.keys())))

    _LP_SLOPE_MAP = ArgMap(
        {
            6: 0,
            12: 1,
            18: 2,
            24: 3
         })
    (get_lp_filter_slope, set_lp_filter_slope, lp_filter_slope) = _create_mapped_property('OFSL', _LP_SLOPE_MAP,
        'Get or set the low-pass filter slope in dB/oct. '
        'Possible values:\n{}'.format(_LP_SLOPE_MAP.keys()))
    (get_sync_filter, set_sync_filter, sync_filter) = _create_mapped_property('SYNC',
        ArgMap({'off': 0, 'on': 1}),
        'Get or set the status of the synchronous filter. Note: synchronous '
        'filtering is only turned on if the detection frequency (refereence '
        'frequency * harmonic number) is less than 200 Hz.')
    
    # Display and output

    _CH1_DISP_MAP = ArgMap(
        {
            'X': 0,
            'R': 1,
            'X noise': 2,
            'aux in 1': 3,
            'aux in 2': 4
        })
    _CH2_DISP_MAP = ArgMap(
        {
            'Y': 0,
            'theta': 1,
            'Y noise': 2,
            'aux in 3': 3,
            'aux in 4': 4
        })
    _CH1_DISP_RATIO_MAP = ArgMap(
        {
            'none': 0,
            'aux in 1': 1,
            'aux in 2': 2
        })
    _CH2_DISP_RATIO_MAP = ArgMap(
        {
            'none': 0,
            'aux in 3': 1,
            'aux in 4': 2
        })
    _CH1_OUTPUT_MAP = ArgMap(
        {
            'display': 0,
            'X': 1
        })
    _CH2_OUTPUT_MAP = ArgMap(
        {
            'display': 0,
            'Y': 1
        })
    
#    def set_output_amplitude_sweep_step(self, sweep_step):
#        self.output_amplitude_sweep_step = sweep_step
#        
#    def get_output_amplitude_sweep_step(self):
#        return self.output_amplitude_sweep_step
    
    def ch1_summary(self):
        '''Returns a summary of ch1 (display and output).'''
        mode = self.visa_handle.query('DDEF? 1')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]
        output_mode = int(self.visa_handle.query('FPOP? 1'))

        summary_string = (
            'CH1 summary:\n'
            '    Display mode: {}\n'
            '    Ratio mode: {}\n'
            '    Output mode: {}\n').format(
                self._CH1_DISP_MAP.get_readable(disp_mode),
                self._CH1_DISP_RATIO_MAP.get_readable(ratio_mode),
                self._CH1_OUTPUT_MAP.get_readable(output_mode))
        
    def ch2_summary(self):
        '''Returns a summary of ch1 (display and output).'''
        mode = self.visa_handle.query('DDEF? 2')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]
        output_mode = int(self.visa_handle.query('FPOP? 2'))

        summary_string = (
            'CH2 summary:\n'
            '    Display mode: {}\n'
            '    Ratio mode: {}\n'
            '    Output mode: {}\n').format(
                self._CH2_DISP_MAP.get_readable(disp_mode),
                self._CH2_DISP_RATIO_MAP.get_readable(ratio_mode),
                self._CH2_OUTPUT_MAP.get_readable(output_mode))

    # Display mode and ratio mode require special treatment because both are
    # set with the same command.
    
    def get_ch1_display_mode(self):
        '''
        Get or set what the CH1 display shows ('X', 'R', 'X noise', 'aux in 1'
        or 'aux in 2').
        '''
        mode = self.visa_handle.query('DDEF? 1')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]
        return self._CH1_DISP_MAP.get_readable(disp_mode)

    def set_ch1_display_mode(self, val):
        mode = self.visa_handle.query('DDEF? 1')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]

        if val in range(len(self._CH1_DISP_MAP)):
            self.visa_handle.write('DDEF 1, {}, {}'.format(val, ratio_mode))
        elif val in self._CH1_DISP_MAP.keys():
            self.visa_handle.write(
                'DDEF 1, {}, {}'.format(self._CH1_DISP_MAP.get_int(val), ratio_mode))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._CH1_DISP_MAP.keys(), val))

    ch1_display_mode = property(get_ch1_display_mode, set_ch1_display_mode)

    def get_ch1_display_ratio_mode(self):
        '''
        Get or set the ratio mode of the CH1 display. The denominator can be
        'none', 'aux in 1', or 'aux in 2').
        '''
        mode = self.visa_handle.query('DDEF? 1')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]
        return self._CH1_DISP_RATIO_MAP.get_readable(ratio_mode)

    def set_ch1_display_ratio_mode(self, val):
        mode = self.visa_handle.query('DDEF? 1')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]

        if val in range(len(self._CH1_DISP_RATIO_MAP)):
            self.visa_handle.write('DDEF 1, {}, {}'.format(disp_mode, val))
        elif val in self._CH1_DISP_RATIO_MAP.keys():
            self.visa_handle.write(
                'DDEF 1, {}, {}'
                .format(disp_mode, self._CH1_DISP_RATIO_MAP.get_int(val)))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._CH1_DISP_RATIO_MAP.keys(), val))

    ch1_display_ratio_mode = property(get_ch1_display_ratio_mode, set_ch1_display_ratio_mode)

    def get_ch2_display_mode(self):
        '''   
        Get o r set what the CH2 display shows ('Y', 'theta', 'Y noise',
        'aux  in 3' or 'aux in 4').
        '''   
        mode  = self.visa_handle.query('DDEF? 2')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]
        return self._CH2_DISP_MAP.get_readable(disp_mode)
              
    def set_ch2_display_mode(self, val):
        mode = self.visa_handle.query('DDEF? 2')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]

        if val in range(len(self._CH2_DISP_MAP)):
            self.visa_handle.write('DDEF 2, {}, {}'.format(val, ratio_mode))
        elif val in self._CH2_DISP_MAP.keys():
            self.visa_handle.write(
                'DDEF 2, {}, {}'.format(self._CH2_DISP_MAP.get_int(val), ratio_mode))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._CH2_DISP_MAP.keys(), val))

    ch2_display_mode = property(get_ch2_display_mode, set_ch2_display_mode)

    def get_ch2_display_ratio_mode(self):
        '''
        Get or set the ratio mode of the CH2 display. The denominator can be
        'none', 'aux in 3', or 'aux in 4').
        '''
        mode = self.visa_handle.query('DDEF? 2')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]
        return self._CH2_DISP_RATIO_MAP.get_readable(ratio_mode)

    def set_ch2_display_ratio_mode(self, val):
        mode = self.visa_handle.query('DDEF? 2')
        disp_mode, ratio_mode = [int(x) for x in mode.strip().split(',')]

        if val in range(len(self._CH2_DISP_RATIO_MAP)):
            self.visa_handle.write('DDEF 2, {}, {}'.format(disp_mode, val))
        elif val in self._CH2_DISP_RATIO_MAP.keys():
            self.visa_handle.write(
                'DDEF 2, {}, {}'
                .format(disp_mode, self._CH2_DISP_RATIO_MAP.get_int(val)))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._CH2_DISP_RATIO_MAP.keys(), val))
    
    ch2_display_ratio_mode = property(get_ch2_display_ratio_mode, set_ch2_display_ratio_mode)
    
    ch1_output_mode = property(
        fset=lambda self, val: (
            self._mapped_setter(val, 'FPOP 1', self._CH1_OUTPUT_MAP)),
        fget=lambda self: self._mapped_getter('FPOP? 1', self._CH1_OUTPUT_MAP),
        fdel=None,
        doc="Get or set the CH1 output mode ('display' or 'X')")
    ch2_output_mode = property(
        fset=lambda self, val: (
            self._mapped_setter(val, 'FPOP 2', self._CH2_OUTPUT_MAP)),
        fget=lambda self: self._mapped_getter('FPOP? 2', self._CH2_OUTPUT_MAP),
        fdel=None,
        doc="Get or set the CH2 output mode ('display' or 'Y')")
    
    # Offset and expand require special treatment because both are set with the
    # same command.
    _EXPAND_MAP = ArgMap(
        {
            1: 0,
            10: 1,
            100: 2
        })

    def get_X_offset(self):
        '''
        Get or set the X-offset in percent.
        '''
        res = self.visa_handle.query('OEXP? 1')
        offs, exp = res.strip().split(',')
        return float(offs)

    def set_X_offset(self, val):
        if not isinstance(val, (float, np.floating)):
            raise TypeError('Value must be float.')

        res = self.visa_handle.query('OEXP? 1')
        offs, exp = res.strip().split(',')
        if -105.0 <= val <= 105.0:
            self.visa_handle.write('OEXP 1, {}, {}'.format(val, exp))
        else:
            raise ValueError(
                'Value must be between -105 % and 105 % (got {}).'.format(val))

    X_offset = property(get_X_offset, set_X_offset)

    def get_X_expand(self):
        '''
        Get or set the X-expand factor.
        '''
        res = self.visa_handle.query('OEXP? 1')
        offs, exp = res.strip().split(',')
        return self._EXPAND_MAP.get_readable(int(exp))

    def set_X_expand(self, val):
        res = self.visa_handle.query('OEXP? 1')
        offs, exp = res.strip().split(',')

        if val in range(len(self._EXPAND_MAP)):
            self.visa_handle.write('OEXP 1, {}, {}'.format(offs, val))
        elif val in self._EXPAND_MAP.keys():
            self.visa_handle.write(
            'OEXP 1, {}, {}'.format(offs, _EXPAND_MAP.get_int(val)))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._EXPAND_MAP.keys(), val))

    X_expand = property(get_X_expand, set_X_expand)
    
    def get_Y_offset(self):
        '''
        Get or set the Y-offset in percent.
        '''
        res = self.visa_handle.query('OEXP? 2')
        offs, exp = res.strip().split(',')
        return float(offs)

    def set_Y_offset(self, val):
        if not isinstance(val, (float, np.floating)):
            raise TypeError('Value must be float.')

        res = self.visa_handle.query('OEXP? 2')
        offs, exp = res.strip().split(',')
        if -105.0 <= val <= 105.0:
            self.visa_handle.write('OEXP 2, {}, {}'.format(val, exp))
        else:
            raise ValueError(
                'Value must be between -105 % and 105 % (got {}).'.format(val))

    Y_offset = property(get_Y_offset, set_Y_offset)

    def get_Y_expand(self):
        '''
        Get or set the Y-expand factor.
        '''
        res = self.visa_handle.query('OEXP? 2')
        offs, exp = res.strip().split(',')
        return self._EXPAND_MAP.get_readable(int(exp))

    def set_Y_expand(self, val):
        res = self.visa_handle.query('OEXP? 2')
        offs, exp = res.strip().split(',')

        if val in range(len(self._EXPAND_MAP)):
            self.visa_handle.write('OEXP 2, {}, {}'.format(offs, val))
        elif val in self._EXPAND_MAP.keys():
            self.visa_handle.write(
            'OEXP 2, {}, {}'.format(offs, self._EXPAND_MAP.get_int(val)))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._EXPAND_MAP.keys(), val))

    Y_expand = property(get_Y_expand, set_Y_expand)

    def get_R_offset(self):
        '''
        Get or set the R-offset in percent.
        '''
        res = self.visa_handle.query('OEXP? 3')
        offs, exp = res.strip().split(',')
        return float(offs)

    def set_R_offset(self, val):
        if not isinstance(val, (float, np.floating)):
            raise TypeError('Value must be float.')

        res = self.visa_handle.query('OEXP? 3')
        offs, exp = res.strip().split(',')
        if -105.0 <= val <= 105.0:
            self.visa_handle.write('OEXP 3, {}, {}'.format(val, exp))
        else:
            raise ValueError(
                'Value must be between -105 % and 105 % (got {}).'.format(val))

    R_offset = property(get_R_offset, set_R_offset)

    def get_R_expand(self):
        '''
        Get or set the R-expand factor.
        '''
        res = self.visa_handle.query('OEXP? 3')
        offs, exp = res.strip().split(',')
        return self._EXPAND_MAP.get_readable(int(exp))

    def set_R_expand(self, val):
        res = self.visa_handle.query('OEXP? 3')
        offs, exp = res.strip().split(',')

        if val in range(len(self._EXPAND_MAP)):
            self.visa_handle.write('OEXP 3, {}, {}'.format(offs, val))
        elif val in self._EXPAND_MAP.keys():
            self.visa_handle.write(
            'OEXP 3, {}, {}'.format(offs, self._EXPAND_MAP.get_int(val)))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(self._EXPAND_MAP.keys(), val))

    R_expand = property(get_R_expand, set_R_expand)

    # Aux Out
    aux_out_1 = property(
        fset=lambda self, val: (
            self._setter(val, 'AUXV 1,', (-10.5, 10.5), float)),
        fget=lambda self: self._getter('AUXV? 1', float),
        fdel=None,
        doc='Get or set the voltage on aux out channel 1 in V. The value will '
            'be rounded to the nearest mV.')
    aux_out_2 = property(
        fset=lambda self, val: (
            self._setter(val, 'AUXV 2,', (-10.5, 10.5), float)),
        fget=lambda self: self._getter('AUXV? 2', float),
        fdel=None,
        doc='Get or set the voltage on aux out channel 2 in V. The value will '
            'be rounded to the nearest mV.')
    aux_out_3 = property(
        fset=lambda self, val: (
            self._setter(val, 'AUXV 3,', (-10.5, 10.5), float)),
        fget=lambda self: self._getter('AUXV? 3', float),
        fdel=None,
        doc='Get or set the voltage on aux out channel 3 in V. The value will '
            'be rounded to the nearest mV.')
    aux_out_4 = property(
        fset=lambda self, val: (
            self._setter(val, 'AUXV 4,', (-10.5, 10.5), float)),
        fget=lambda self: self._getter('AUXV? 4', float),
        fdel=None,
        doc='Get or set the voltage on aux out channel 4 in V. The value will '
            'be rounded to the nearest mV.')

    # Setup parameters

    (get_key_click, set_key_click, key_click) = _create_mapped_property('KCLK', ArgMap({'on': 1, 'off': 0}),
        'Get or set the key click state.')
    (get_alarm, set_alarm, alarm) = _create_mapped_property('ALRM', ArgMap({'on': 1, 'off': 0}),
        'Get or set the alarm state.')

    # Data storage

    _SRATE_MAP = ArgMap(
        {
            62.5e-3: 0,     8: 7,
            125e-3: 1,      16: 8,
            250e-3: 2,      32: 9,
            500e-3: 3,      64: 10,
            1: 4,           128: 11,
            2: 5,           256: 12,
            4: 6,           512: 13,
                            'trigger': 14})
    (get_samplingrate, set_samplingrate, samplingrate) = _create_mapped_property('SRAT', _SRATE_MAP,
        'Get or set the sampling rate in Hz. '
        'Possible values:\n{}'.format(_SRATE_MAP.keys()))
    (get_buffer_mode, set_buffer_mode, buffer_mode) = _create_mapped_property(
        'SEND', ArgMap({'single shot': 0, 'loop': 1}),
        "Get or set the end-of-buffer mode ('single shot' or 'loop').")
    (get_trigger_mode, set_trigger_mode, trigger_mode) = _create_mapped_property(
        'TSTR', ArgMap({'on': 1, 'off': 0}),
        "Get or set the trigger mode ('on' -> trigger starts data storage, "
        "or 'off' -> trigger has no effect).")

    # Setup commands
    def disable_offset(self, output):
        '''Turn off the offset on a given output ('X', 'Y', or 'R').'''
        output_map = {'X': 1, 'Y': 2, 'R': 3}
        if output in [1, 2, 3]:
            self.visa_handle.write('AOFF {}'.format(output))
        elif output in output_map.keys():
            self.visa_handle.write('AOFF {}'.format(output_map[output]))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'
                .format(output_map.keys()), val)

    def get_aux_in(self, channel):
        '''Get the input value of a given aux in channel (1, 2, 3, or 4) in
        units of V.'''
        if channel not in [1, 2, 3, 4]:
            raise ValueError(
                'Channel must be 1, 2, 3, or 4 (got {}).'.format(channel))
        return self.visa_handle.query('OAUX? {}'.format(channel))
    
    def set_output_interface(self, interface):
        ArgMap({6: 0,
                12: 1,
                18: 2,
                24: 3}),
        '''Set the output interface that is used for communication ('GPIB' or
        'RS232'). The device always accepts commands from both interfaces, but
        only sends responses to one.
        WARNING: this driver was only tested with GPIB.'''
        if interface not in [1, 'GPIB']:
            print('WARNING: driver was only tested with GPIB.')

        map_ = {'GPIB': 1, 'RS232': 0}
        if interface in [0, 1]:
            self.visa_handle.write('OUTX {}'.format(interface))
        elif interface in map_.keys():
            self.visa_handle.write('OUTX {}'.format(map_[interface]))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'.format(map_.keys(), interface))

    (get_override_remote, set_override_remote, override_remote) = _create_mapped_property(
        'OVRM', ArgMap({'on': 1, 'off': 0}),
        "Get or set the override remote mode. 'on' means that the front panel "
        "is active even in the 'remote' interface mode.")

    def save_setup(self, buf):
        '''Save the lock-in setup to a given buffer (1--9). The buffers are
        retained when the power is turned off.'''
        if buf not in range(1, 10):
            raise ValueError(
                'Value must be between 1 and 9 (got {}).'.format(buf))
        self.visa_handle.write('SSET {}'.format(buf))

    def load_setup(self, buf):
        '''Load the lock-in setup to a given buffer (1--9). The buffers are
        retained when the power is turned off.'''
        if buf not in range(1, 10):
            raise ValueError(
                'Value must be between 1 and 9 (got {}).'.format(buf))
        # Clear event status byte 4 to be able to detect errors
        self.visa_handle.query('*ESR? 4')
        self.visa_handle.write('RSET {}'.format(buf))
        ArgMap({6: 0,
                12: 1,
                18: 2,
                24: 3}),
        res = int(self.visa_handle.query('*ESR? 4'))
        if res == 1:
            raise RuntimeError(
                'Error while loading setup from buffer {}. '
                'Make sure a setup was previously stored in that buffer.'
                .format(buf))

    def auto_gain(self):
        '''Perform the auto gain function (same as pressing the Auto Gain key
        on the front panel). This may take some time for large time constants.
        This does nothing if the time constant is greater than 1 s.'''
        self.visa_handle.write('AGAN')
# TODO: wait for command completion 
# -> Can't find correct byte. Does not behave accoridng to manual.
#        while self.serial_poll_status[-2] == '0':
#            # Command execution not finished
#            time.sleep(100e-3)

    def auto_reserve(self):
        '''Perform the auto reserve function (same as pressing the Auto Reserve
        key on the front panel). This may take some time.'''
        self.visa_handle.write('ARSV')
# TODO: wait for command completion
# -> Can't find correct byte. Does not behave accoridng to manual.
#        while self.serial_poll_status[-2] == '0':
#            # Command execution not finished
#            time.sleep(100e-3)

    def auto_phase(self):
        '''Perform the auto phase function (same as pressing the Auto Phase
        key on the front panel). It takes many time constants for the outputs
        to reach their new values. This will do nothing if the phase is
        unstable.'''
        self.visa_handle.write('APHS')
# TODO: wait for command completion
# -> Can't find correct byte. Does not behave accoridng to manual.
#        while self.serial_poll_status[-2] == '0':
#            # Command execution not finished
#            time.sleep(100e-3)

    def auto_offset(self):
        '''Perform the auto offset function (same as pressing the Auto Offset
        key on the front panel).'''
        self.visa_handle.write('AOFF')


    # Data storage commands

    def send_trigger(self):
        '''Send a software trigger for data storage. This has the same effect
        as a trigger at the rear panel trigger input.'''
        self.visa_handle.write('TRIG')

    def start(self):
        '''Start data storage. This has no effect if data storage is already in
        progress.'''
        self.visa_handle.write('STRT')

    def pause(self):
        '''Pause data storage.'''
        self.visa_handle.write('PAUS')

    def reset_data_buffer(self):
        '''Reset the data buffer.'''
        self.visa_handle.write('REST')

    # Data transfer commands

#    @property
#    def X(self):
#        '''Get the value of X in volts.'''
#        return float(self.visa_handle.query('OUTP? 1'))

    def get_X(self):
        '''Get the value of X in volts.'''
        return float(self.visa_handle.query('OUTP? 1'))
    
    X = property(get_X)    
    
    def get_Y(self):
        '''Get the value of Y in volts.'''
        return float(self.visa_handle.query('OUTP? 2'))

    Y = property(get_Y)

    def get_R(self):
        '''Get the value of R in volts.'''
        return float(self.visa_handle.query('OUTP? 3'))

    R = property(get_R)

    def get_theta(self):
        '''Get the value of theta in degrees.'''
        return float(self.visa_handle.query('OUTP? 4'))

    theta = property(get_theta)

    def get_ch1_display(self):
        '''Get the current value of the CH1 display in the units of the
        display.'''
        return float(self.visa_handle.query('OUTR? 1'))

    ch1_display = property(get_ch1_display)

    def get_ch2_display(self):
        '''Get the current value of the CH2 display in the units of the
        display.'''
        return float(self.visa_handle.query('OUTR? 2'))
    
    ch2_display = property(get_ch2_display)
    
    def snapshot(self, *args):
        '''Get a snapshot of 2 to 6 values at the same time. Values are
        returned in the order that they were requested. Arguments can be 'X',
        'Y', 'R', 'theta', 'aux in 1', 'aux in 2', 'aux in 3', 'aux in 4',
        'reference frequency', 'ch1 display', and 'ch2 display'.
        See manual for more information on timings of the snapshot.'''
        map_ = {
            'X': 1,         'aux in 3': 7,
            'Y': 2,         'aux in 4': 8,
            'R': 3,         'reference frequency': 9,
            'theta': 4,     'ch1 display': 10,
            'aux in 1': 5,  'ch2 display': 11,
            'aux in 2': 6
        }
        if not (2 <= len(args) <= 6):
            raise ValueError(
                'Number of arguments must be between 2 and 6 (got {}).'
                .format(len(args)))
        for a in args:
            if a not in map_.keys():
                raise ValueError(
                    'Values must be in {} (got {}).'.format(map_.keys(), a))

        res = self.visa_handle.query(
            'SNAP? ' + ','.join([str(map_[x]) for x in args]))
        return [float(x) for x in res.strip().split(',')]

    def get_aux_in_1(self):
        '''Read the input on the aux in channel 1 in volts. The resolution is
        1/3 mV.'''
        return float(self.visa_handle.query('OAUX? 1'))

    aux_in_1 = property(get_aux_in_1)

    def get_aux_in_2(self):
        '''Read the input on the aux in channel 2 in volts. The resolution is
        1/3 mV.'''
        return float(self.visa_handle.query('OAUX? 2'))

    aux_in_2 = property(get_aux_in_2)

    def get_aux_in_3(self):
        '''Read the input on the aux in channel 3 in volts. The resolution is
        1/3 mV.'''
        return float(self.visa_handle.query('OAUX? 3'))

    aux_in_3 = property(get_aux_in_3)

    def get_aux_in_4(self):
        '''Read the input on the aux in channel 4 in volts. The resolution is
        1/3 mV.'''
        return float(self.visa_handle.query('OAUX? 4'))

    aux_in_4 = property(get_aux_in_4)

    def get_nr_stored_points(self):
        '''Get the number of point currently stored in the data buffer.'''
        return int(self.visa_handle.query('SPTS?'))

    nr_stored_points = property(get_nr_stored_points)

    def get_points(self, channel, index=0, nr=1, container=np.array):
        '''
        Read points from a given channel buffer.
        Limits:
            0 <= index < self.nr_stored_points
            1 <= nr
            index + nr <= self.nr_stored_points
        
        Args:
            channel (int):
                Channel number from which to read (1 or 2).
            index (int):
                Index of the first bin in the buffer that is read.
            nr (int):
                Total number of point to read.
            container (type):
                Type of container to store return. Usually 'list' or
                'numpy.array'.
        '''
        if not (isinstance(channel, int) and isinstance(index, int)
                and isinstance(nr, int)):
            raise TypeError('All arguments must be integers.')
        if (index + nr > self.nr_stored_points or index < 0 or nr < 1):
            raise ValueError(
                'Requested points {} through {} out of range. '
                'Total stored ponits: {}.'
                .format(index, index + nr, self.nr_stored_points))

        def sep(x):
            return x.strip(', \n').split(',')

        return self.visa_handle.query_ascii_values(
            'TRCA? {}, {}, {}'.format(channel, index, nr),
            container=container, separator=sep)

    # Interface commands

    def reset_all(self):
        '''Reset the device do default settings. Communications setup is not
        affected. This may take some time.'''
        ans = input('Reset ALL settings (data in buffer will be lost)? '
                    '(y/[n]): ')
        if ans.lower() == 'y':
            self.visa_handle.write('*RST')


    def get_IDN(self):
        '''Get the device's identification string.'''
        return self.visa_handle.query('*IDN?')

    IDN = property(get_IDN)


    (get_interface_mode, set_interface_mode, interface_mode) = _create_mapped_property(
        'LOCL', ArgMap({'local': 0, 'remote': 1, 'local lockout': 2}),
        'Get or set the interface mode.\n'
        "    'local': command execution and front panel input possible.\n"
        "    'remote': command execution possible. The [LOCAL] key is the\n"
        "              only active key on the front panel.\n"
        "    'local lockout': only command execution possible.\n"
        "Note that this mode can be overridden by self.remote_override.")

    # Status reporting commands

    def clear_status(self):
        '''Clear all status registers (except status enable registers).'''
        self.visa_handle.write('*CLS')

    _BYTE_MAP = ArgMap({'{:0>8b}'.format(x): x for x in range(256)})
    (get_event_enable, set_event_enable, event_enable) = _create_mapped_property('*ESE', _BYTE_MAP,
        'Get or set the standard event enable byte. This can be set to to '
        'a string representation (e.g. "1001011", left is MSB, right is LSB), '
        'or the corresponding integer representation (0--255, e.g. 75). Each '
        'bit of the event enable byte enables a bit in the event status '
        'byte. Bit 5 of the serial poll status byte will be 1 if any enabled '
        'bit in the event status byte is one.')
    (get_serial_poll_enable, set_serial_poll_enable, serial_poll_enable) = _create_mapped_property('*SRE', _BYTE_MAP,
        'Get or set the serial poll enable byte. This can be set to to '
        'a string representation (e.g. "1001011", left is MSB, right is LSB), '
        'or the corresponding integer representation (0--255, e.g. 75). Each '
        'bit of the enable byte enables a bit in the status byte. If an '
        'enabled bit is 1 in the status byte, bit 7 (the service request bit) '
        'is set to one, until the serial poll status byte is polled.')
    (get_error_enable, set_error_enable, error_enable) = _create_mapped_property('ERRE', _BYTE_MAP,
        'Get or set the error status enable byte. This can be set to to '
        'a string representation (e.g. "1001011", left is MSB, right is LSB), '
        'or the corresponding integer representation (0--255, e.g. 75). Each '
        'bit of the enable byte enables a bit in the status '
        'byte. Bit 2 of the serial poll status byte will be 1 if any enabled '
        'bit in the status byte is one.')
    (get_lockin_enable, set_lockin_enable, lockin_enable) = _create_mapped_property('LIAE', _BYTE_MAP,
        'Get or set the lock-in enable byte. This can be set to to '
        'a string representation (e.g. "1001011", left is MSB, right is LSB), '
        'or the corresponding integer representation (0--255, e.g. 75). Each '
        'bit of the enable byte enables a bit in the status '
        'byte. Bit 3 of the serial poll status byte will be 1 if any enabled '
        'bit in the status byte is one.')

    event_status = property(
        fget=lambda self: self._mapped_getter('*ESR?', self._BYTE_MAP),
        doc='Read and clear the event status byte. Returns a string '
            'representation (e.g. "1001011", left is MSB, right is LSB).')
    serial_poll_status = property(
        fget=lambda self: self._mapped_getter('*STB?', self._BYTE_MAP),
        doc='Read and clear the serial poll status byte. Returns a string '
            'representation (e.g. "1001011", left is MSB, right is LSB). '
            "Note: Results don't seem to agree with manual.")
    error_status = property(
        fget=lambda self: self._mapped_getter('ERRS?', self._BYTE_MAP),
        doc='Read and clear the error status byte. Returns a string '
            'representation (e.g. "1001011", left is MSB, right is LSB).')
    lockin_status = property(
        fget=lambda self: self._mapped_getter('LIAS?', self._BYTE_MAP),
        doc='Read and clear the lock-in status byte. Returns a string '
            'representation (e.g. "1001011", left is MSB, right is LSB).')

    (get_clear_status_on_power_up, set_clear_status_on_power_up, clear_status_on_power_up) = _create_mapped_property(
        '*PSC', ArgMap({'on': 1, 'off': 0}),
        'Sets the power-on status clear bit. If this is on, all status and '
        'enable bytes are cleared at power up, otherwise they are retained.')

    def clear_output_buffer(self):
        '''Reads from the output buffer until it is empty.
        Any values that were read are returnd as a list.'''
        res = []
        while (self.visa_handle.stb >> 4) % 2 == 1:
            res.append(self.visa_handle.read())
        return res

if __name__ == '__main__':
    object_dict = {
            # 'LIA1': SR830('GPIB0::8::INSTR'),
            # 'LIA2': SR830('GPIB0::9::INSTR'),
            'LIA3': SR830('GPIB0::10::INSTR'),            
    }
    nw_utils.RunServer(object_dict, host = 'localhost')