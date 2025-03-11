# -*- coding: utf-8 -*-
'''
Base class and other general visa-related utilites.
@author: Livio Ciorciaro
'''

import visa
import numpy as np
import types
import pandas as pd


class VISA_Instrument(object):
    '''
    Base class for VISA instrument.
    '''
    def __init__(self, address, visalib='default'):
        '''
        Args:
            name (string):
                Human-readable name for the device.
            address (int):
                The GPIB address that was set on the device.
            visalib (string):
                Path to the visa-backend that is used. If this is 'default'
                the PyVISA ResourceManager will attempt to locate the library.
        '''
        if visalib == 'default':
            self.visa_handle = visa.ResourceManager().open_resource(address)
        else:
            self.visa_handle = (
                visa.ResourceManager(visalib).open_resource(address))
    
    # Setter and getter for parameters that are mapped from human-readable form
    # to integer setting value.
    def _mapped_getter(self, visastring, argmap):
        '''VISA getter for a parameter which is mapped from a human-readable
        form to an integer-valued device setting.'''
        return argmap.get_readable(int(self.visa_handle.query(visastring)))

    def _mapped_setter(self, val, visastring, argmap):
        '''VISA setter for a parameter that is mapped from a human-readable
        form to an integer-valued device setting.'''
        if val in argmap.keys():
            self.visa_handle.write('{} {}'.format(visastring, argmap.get_int(val)))
        else:
            raise ValueError(
                'Value must be in {} (got {}).'.format(sorted(argmap.keys()), val))

    # Getter and setter for a paramter that is directly set and has some
    # limits.
    def _getter(self, visastring, type_=float):
        '''VISA setter for a generic parameter of type <type_>.'''
        if not isinstance(type_, type):
            raise TypeError('type_ should be a type.')
        return type_(self.visa_handle.query(visastring))

    def _setter(self, val, visastring, limits=(-np.inf, np.inf), type_=float):
        '''VISA setter for a generic parameter, with optional limits.'''
        if not isinstance(type_, type):
            raise TypeError('type_ should be a type.')
        if not isinstance(val, type_):
            if type_ == float and type(val) == int:
                val = float(val)
            else:
                raise TypeError(
                    'Value should be of type {} (got {}).'
                    .format(type_, type(val)))
        if limits[0] <= val <= limits[1]:
            self.visa_handle.write('{} {}'.format(visastring, val))
        else:
            raise ValueError(
                'Value must be between {} and {} (got {}).'
                .format(*limits, val))

    # Some commands for user-friendliness
    def print_parameters(self):
        '''Print all available parameters. Some might not be settable.'''
        attrs = [x for x in dir(self) if
                 not x.startswith('_') and
                 not isinstance(getattr(self, x), types.MethodType)]
#        ret = {}
        for x in attrs:
#            ret[x] = getattr(self, x)
#        print(pd.Series(ret))
#        return pd.Series(ret)
#        print(ret)
            print('{:<25}:  {}'.format(x, getattr(self, x)))

    def print_commands(self):
        '''Print all available methods.'''
        attrs = [x for x in dir(self) if
                 not x.startswith('_') and
                 isinstance(getattr(self, x), types.MethodType)]
        for x in attrs:
            print(x)
    
    def close(self):
        self.visa_handle.close()


class ArgMap():
    '''Small wrapper class that saves an immutable two-way dictionary. The
    descriptive keys can be listed with the keys() method.'''
    def __init__(self, arg_dict):
        '''
        arg_dict is a dictionary with the descriptive argument names as keys, and
        the actual arguments that are passed to the visa_handle as values.
        '''
        self._readable_to_int = dict()
        self._int_to_readable = dict()
        self._keys = []
        for k, v in arg_dict.items():
            self._readable_to_int[k] = v
            self._int_to_readable[v] = k

    def __getitem__(self, key):
        raise NotImplementedError(
            'Use the methods get_readable and get_int to access items.')

    def __setitem__(self, key, val):
        raise ValueError('Setting items not allowed!')

    def __len__(self):
        return len(self._readable_to_int)

    def get_readable(self, key, default=None):
        if key in self._int_to_readable.keys():
            return self._int_to_readable[key]
        else:
            return default

    def get_int(self, key, default=None):
        if key in self._readable_to_int.keys():
            return self._readable_to_int[key]
        else:
            return default

    def keys(self):
        '''List the descriptive keys.'''
        return self._readable_to_int.keys()

