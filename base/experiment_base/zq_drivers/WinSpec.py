# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 23:50:29 2018

@author: G13-WinSpec
"""

# winspec.py, COM wrapper for use with Roper Scientific's Winspec
# Reinier Heeres <reinier@heeres.eu>, 2009
# Yves Delley
# Meinrad Sidler
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from comtypes.client import CreateObject, Constants
import numpy as np
import time, sys
import logging
import threading
import Pyro4
import Pyro4.naming
import xarray as xr
Pyro4.config.SERIALIZERS_ACCEPTED = set(['pickle',
                                         'json',
                                         'marshal',
                                         'serpent',
                                         ])
Pyro4.config.SERIALIZER = 'pickle'
sys.path.append(r'C:\Users\QPG\Documents\eyazici_g15\base\experiment_base\fey_drivers\pyro_nw')
import nw_utils as nw_utils
import nw_config as config



@Pyro4.expose
class wsSrv(object):

    _exp = None
    _app = None
    _const = None
    _spec_mgr = None
    _spec = None
    _is_initialised = False

    _logger = logging.getLogger('WinSpec')

    # actually: the thread first importing comtypes would be the one being
    # CoInitialised already. Let's hope this is the same thread as the one
    # importing us here.
    _thread_info = threading.local()
    #_thread_info._is_CoInitialised = True

    #print('********** WinSpec is beeing imported')


    def _ensure_CoInit(self):
        try:
            if self._thread_info._is_CoInitialised:
                return
        except AttributeError:
            # '_thread_info' has no '_is_CoInitialised'?
            # => so it's certainly not True!
            pass
        from comtypes import CoInitialize
    #    print('*********** CoInitialize a second thread')
        CoInitialize()
        self._thread_info._is_CoInitialised = True
        self._thread_info._is_initialised = False
        self._initialise_this_thread()

    def _initialize(self):
        '''
        Create objects. Associated constants will be available in the _const
        object. Note that it's not possible to request the contents of that;
        one has to look in the Python file generated with gen_py.
        '''
        # MS global _exp, _app, _const, _spec_mgr, _spec, _is_initialized

        self._ensure_CoInit()
        self._logger.info(
            "WinSpec._initialize called",
        )

    def _initialise_this_thread(self):
        if self._thread_info._is_initialised:
            import traceback
            self._logger.warning(
                "_initialize called a second time:\n%s",
                ''.join(traceback.format_stack())
            )
            return
        self._logger.info(
            "WinSpec._initialise_this_thread called",
        )
        self._thread_info._exp = CreateObject('WinX32.ExpSetup.2')
        self._thread_info._app = CreateObject('WinX32.Winx32App.2')
        self._thread_info._const = Constants(self._thread_info._exp)
        self._thread_info._spec_mgr = CreateObject('WinX32.SpectroObjMgr')
        self._thread_info._spec = self._thread_info._spec_mgr.Current

        # no idea where this command loads the configuration from:
        # we seem to be unable to store the configuration anywhere
    #    _spec.Process(_const.SPTP_INST_LOADCONFIGURATION)

        self._thread_info._is_initialised = True
        
    def initialize(self):
        self._ensure_CoInit()
        self._thread_info._exp.Stop()  
        time.sleep(0.5) 
    
    @property  
    def exposure_time(self):
        self._ensure_CoInit()
        return self._thread_info._exp.SGetParam(self._thread_info._const.EXP_EXPOSURE)[1]
    @exposure_time.setter
    def exposure_time(self,val):
        self._ensure_CoInit()
        return self._thread_info._exp.SetParam(self._thread_info._const.EXP_EXPOSURE, float(val))

    def get_exposure_time(self):
        return self.exposure_time
    
    def set_exposure_time(self, val):
        self.exposure_time = val
        
    @property
    def grating(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_CUR_GRATING)[1]
    @grating.setter
    def grating(self,val):
#        val = int(self,val)
        val = int(val)        
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_NEW_GRATING, val)
        self._thread_info._spec.Move()
        return self.grating
    
    def get_grating(self):
        return self.grating
    
    def set_grating(self, val):
        self.grating = val

    def get_current_grating_grooves(self):
        return self.get_grating_grooves(self.grating)
        
    def get_grating_grooves(self,gr):
        '''gr is the absolute grating number.'''
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_GRAT_GROOVES, gr)[1]

    def get_grating_name(self,gr):
        '''gr is the absolute grating number.'''
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_GRAT_USERNAME, gr)[1]

    @property
    def ngratings(self):
        '''Get number of gratings per turret.'''
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_GRATINGSPERTURRET)[1]

    @property
    def current_turret(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_ACTIVE_TURRET_NUM)[1]

    @property
    def forcemove(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_FORCEMOVE)[1]

    @property
    def active_mirror_loc(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_ACTIVE_MIRROR_LOC)[1]
    @active_mirror_loc.setter
    def active_mirror_loc(self,val):
        """ Mirror control:
         1: Front
         2: Side
        """
#        val = int(val)        
#        assert val in [1,2]
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_ACTIVE_MIRROR_LOC, val)
        self._thread_info._spec.Move()
        return self.active_mirror_loc         
       
    @property
    def active_mirror_pos(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_ACTIVE_MIRROR_POS)[1]
    @active_mirror_pos.setter
    def active_mirror_pos(self,val):
        """ Mirror control:
         1: Front
         2: Side
        """
#        val = int(val)        
#        assert val in [1,2]
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_ACTIVE_MIRROR_POS, val)
        self._thread_info._spec.Move()
        return self.active_mirror_pos         
              
    @property
    def mirror_curposition(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_MIRROR_CURPOSITION)[1]
    @mirror_curposition.setter
    def mirror_curposition(self,val):
        """ Mirror control:
         1: Front
         2: Side
        """
#        val = int(val)        
#        assert val in [1,2]
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_MIRROR_CURPOSITION, val)
        self._thread_info._spec.Move()
        return self.mirror_curposition         
        
    @property
    def mirror_newposition(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_MIRROR_NEWPOSITION)[1]
    @mirror_newposition.setter
    def mirror_newposition(self,val):
        """ Mirror control:
         1: Front
         2: Side
        """
#        val = int(val)        
#        assert val in [1,2]
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_MIRROR_NEWPOSITION, val)
        self._thread_info._spec.Move()
        return self.mirror_newposition         
    
    @property
    def mirror_location(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_MIRROR_LOCATION)[1]
    @mirror_location.setter
    def mirror_location(self,val):
        """ Mirror control:
         1: Entrance
         2: Exit
         The current mirror_location is the one affected by mirror_newposition commands
         With mirror_location=2, the entrance mirror option disapears from the Winspec program
        """
#        val = int(val)        
#        assert val in [1,2]
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_MIRROR_LOCATION, val)
        self._thread_info._spec.Move()
        return self.mirror_location             
        
    @property
    def shutter_control(self):
        """ Shutter control:

         1: Normal
         2: Disabled closed
         3: Disabled opened
        """
        self._ensure_CoInit()
        return self._thread_info._exp.SGetParam(self._thread_info._const.EXP_SHUTTER_CONTROL)[1]
    @shutter_control.setter
    def shutter_control(self,val):
        """ Shutter control:

         1: Normal
         2: Disabled closed
         3: Disabled opened
        """
        assert val in [1,2,3]
        self._ensure_CoInit()
        return self._thread_info._exp.SetParam(self._thread_info._const.EXP_SHUTTER_CONTROL,val)

    @property
    def temperature(self):
        self._ensure_CoInit()
        return self._thread_info._exp.SGetParam(self._thread_info._const.EXP_ACTUAL_TEMP)[1]
    
    def get_temperature(self):
        return self.temperature
    
    @property
    def target_temperature(self):
        self._ensure_CoInit()
        return self._thread_info._exp.SGetParam(self._thread_info._const.EXP_TEMPERATURE)[1]
    @target_temperature.setter
    def target_temperature(self,val):
        self._ensure_CoInit()
        return self._thread_info._exp.SetParam(self._thread_info._const.EXP_TEMPERATURE, float(val))
        
    @property
    def wavelength(self):
        self._ensure_CoInit()
        return self._thread_info._spec.GetParam(self._thread_info._const.SPT_CUR_POSITION)[1]
    @wavelength.setter
    def wavelength(self,val):
        self._ensure_CoInit()
        self._thread_info._spec.SetParam(self._thread_info._const.SPT_NEW_POSITION, float(val))
        self._thread_info._spec.Move()
        return self.wavelength
    
    def get_wavelength(self):
        return self.wavelength
    
    def set_wavelength(self, val):
        self.wavelength = val

    @property
    def num_frames(self):
        self._ensure_CoInit()
        return self._thread_info._exp.SGetParam(self._thread_info._const.EXP_SEQUENTS)[1]
    @num_frames.setter
    def num_frames(self,val):
        self._ensure_CoInit()
        return self._thread_info._exp.SetParam(self._thread_info._const.EXP_SEQUENTS,int(val))
        
    def get_num_frames(self):
        return self.num_frames
    
    def set_num_frames(self, val):
        self.num_frames = val
    
    @property
    def file_name(self):
        self._ensure_CoInit()
        return self._thread_info._exp.SGetParam(self._thread_info._const.EXP_DATFILENAME)[1]
    @file_name.setter
    def file_name(self,fname):
        self._ensure_CoInit()
        return self._thread_info._exp.SetParam(self._thread_info._const.EXP_DATFILENAME,fname)

    def get_calibration_poly(self,doc=None):
        self._ensure_CoInit()
        try:
            if doc is None:
                _doc = CreateObject('WinX32.DocFile.3')
            else:
                _doc = doc
            self._thread_info._exp.Start(doc)
            calib = _doc.GetCalibration()
            order = calib.Order
            return np.polynomial.Polynomial(
                [calib.PolyCoeffs(i) for i in range(order + 1)]
            )(np.polynomial.Polynomial([1,1]))
        finally:
            if doc is None:
                _doc.Close()

    def get_calibration(self,doc=None):
        self._ensure_CoInit()
        try:
            if doc is None:
                _doc = CreateObject('WinX32.DocFile.3')
            else:
                _doc = doc
            ### self._thread_info._exp.Start(doc)            
            calib = _doc.GetCalibration()
            xdim = _doc.SGetParam(self._thread_info._const.DM_XDIM)[1]
            return np.array([calib.Lambda(i + 1) for i in range(xdim)])
        finally:
            if doc is None:
                _doc.Close()

    @property
    def specdict(self):
        dic = {}
        dic['exposure_time']        = self.exposure_time
        dic['num_frames']           = self.num_frames
        dic['wavelength']           = self.wavelength
        dic['grating_name']         = self.get_grating_name(self.grating)
        dic['grating_grooves']      = self.get_grating_grooves(self.grating)
        dic['shutter_control']      = self.shutter_control
        dic['temperature']          = self.temperature
        dic['target_temperature']   = self.target_temperature
        return dic
    
    
#    def get_const(self):
#        print('test')
#        self._ensure_CoInit()
#        doc = CreateObject('WinX32.DocFile.3')
#        _exp = self._thread_info._exp
#        _const = self._thread_info._const
#        dic = None
#        try:
#            print('test2')
#            print(_const)
##            dic = dict(_const)
#        finally:
#            doc.Close()
#        return dic

    def get_spectrum(self,wlenpoly=False, wlen=False, dt_loop=0.01,test=False):
        '''
        Get a spectrum using winspec.

        If wlen is True it returns a 2D numpy array with wavelength and counts
        as the columns. If wlen is False it returns a 1D array with counts.
        If wlenpoly is True the polynomial approximation for determining the
        wavelength will be used, which is quite a bit faster than querying winspec
        for the individual pixels (takes 0.5 sec in 100kHz ADC mode). 
        It can be off by ~0.3nm.
        '''
        self._ensure_CoInit()
        doc = CreateObject('WinX32.DocFile.3')
        _exp = self._thread_info._exp
        _const = self._thread_info._const
        try:
            nframes = _exp.SGetParam(_const.EXP_SEQUENTS)[1]
            t_exp = _exp.SGetParam(_const.EXP_EXPOSURE)[1]
            self._thread_info._exp.Start(doc)
            try:
                tstart = time.time()
                texpend = tstart + nframes*t_exp*1.0
#                tstop = texpend + 2*t_exp + nframes*0.1
#                print('nframes: {}'.format(nframes))
#                print('experiment runtime: {}'.format(texpend-tstart))
                while _exp.SGetParam(_const.EXP_RUNNING)[1] != 0:
                    cur_t = time.time()
                    tsleep = max(texpend - cur_t, dt_loop)
#                    print('exp_running X: {}, tsleep: {}'.format(
#                            _exp.SGetParam(_const.EXP_RUNNING)[1], tsleep))
#                    print('expected duration: {} s'.format(texpend - cur_t))
#                    print('sleeping 1 for {} s'.format(tsleep))
                    time.sleep(tsleep)
                    
                

                
#                while time.time() < tstop and _exp.SGetParam(_const.EXP_RUNNING)[1] != 0:
#                    print('sleeping 2 for {} s!'.format(dt_final))
#                    time.sleep(dt_final)
            except:
                _exp.Stop()
                raise

            if _exp.SGetParam(_const.EXP_RUNNING)[1] != 0:
                _exp.Stop()
                raise RuntimeError('Exposure kept running after expected end. Aborted!')

#            xdim = doc.SGetParam(_const.DM_XDIM)[1]
#            ydim = doc.SGetParam(_const.DM_YDIM)[1]
            nf_real = doc.SGetParam(_const.DM_NUMFRAMES)[1]
#
#            if nframes != nf_real:
#                print('Number of frames doesnt match ',nframes,nf_real,xdim,ydim)

#            if ydim != 1:
#                raise ValueError('Can only get 1D spectra')
            
#            tstart = time.time()
#            print('dtype: {}'.format(type(doc.GetFrame(1))))
#            print(doc.GetFrame(1)[0].__repr__())
            spectra = [doc.GetFrame(k+1) for k in range(nf_real)]
#            print('readout time: {}'.format(time.time()-tstart))
            spectra = np.array(spectra, dtype=np.uint16)
            
            
            # if False:
            #     allzero = ~np.any(spectra,-1)
            #     if np.any(allzero):
            #         print('WARNING: Allzero data received, re-trying in 0.1s ...')
            #         print(' (though, apparently it does not help...)')
            #         time.sleep(0.1)
            #         retry = np.array([doc.GetFrame(k+1) for k in np.flatnonzero(allzero)],dtype='u2')
            #         assert retry.shape[2] == 1
            #         spectra[allzero] = retry[:,:,0]
            if wlen or wlenpoly:
                if wlenpoly:
                    wlens = self.get_calibration_poly(doc).tolist()
                if wlen:
                    wlens = self.get_calibration(doc).tolist()
                wlens = np.array(wlens)
#                print('took {} s'.format(time.time()-tstart))
                if test: 
                    return time.time()-tstart
                return spectra, wlens
            return spectra
        finally:
            doc.Close()

    def get_spectrum_xr(self, wlen=True): 
        ''' record a spectrum in the Xarray format
        returns: da[Frame, Wavelength, ROI]
        '''
        if wlen:
            spectra, wl = self.get_spectrum(wlen=True)
        else:
            spectra = self.get_spectrum(wlen=False)
            wl = np.arange(0,len(spectra[0]))
        spectra = np.array(spectra,dtype=np.float)
        frame_num = spectra.shape[0]
        roi_num = spectra.shape[-1]
        da = xr.DataArray(spectra, 
            coords={'Frame': np.arange(frame_num), 'Wavelength': wl, 
                    'ROI': np.arange(roi_num)},
            dims = ('Frame', 'Wavelength', 'ROI'))
        da.attrs['units'] = 'counts'
        da.attrs['long_name'] = 'Intensity'
        da.Wavelength.attrs['units'] = 'nm'
        return da


if __name__ == "__main__":
    IS_EXILE = True    
    
    if IS_EXILE: # EXILE winspec 
        # don't register the daemon 
        daemon = Pyro4.Daemon(host = config.CONFIG['PYRO_HOST'], port=config.CONFIG['PYRO_PORT'], nathost='phd-exile-phys.ethz.ch', natport=9090)
        uri = daemon.register(wsSrv, objectId = 'WinSpec')
        print('WinSpec in exile')
    else: # normal winspec
        daemon = Pyro4.Daemon(host = config.HOSTNAME + '.dhcp.phys.ethz.ch')
        uri = daemon.register(wsSrv, objectId = 'WinSpec')
        ns = Pyro4.naming.locateNS(host=config.CONFIG['PYRO_HOST'], port=config.CONFIG['PYRO_PORT'])
        ns.register('WinSpec',uri)
    
#    ns = Pyro4.naming.locateNS(host=config.CONFIG['PYRO_HOST'], port=9900)
#    ns.register('WinSpec',uri)
    print("Ready. Object uri = ", uri)
    daemon.requestLoop()
    
#    ws = wsSrv()
    
#    resource_name = config.CONFIG['HP4142B_ADDR']
#    object_dict = {'HP4142B': HP4142B(resource_name)}
#    nw_utils.RunServer(object_dict, host = config.HOSTNAME + '.dhcp.phys.ethz.ch')

    

### Client commands
#import Pyro4
#ns = Pyro4.naming.locateNS(host='g13-winspec-pc.dhcp.phys.ethz.ch',hmac_key='G13_WinSpec')
#ws = Pyro4.Proxy(ns.lookup('G13_Winspec'))
#ws.set_exposure_time(1)
#ws.set_num_frames(1)