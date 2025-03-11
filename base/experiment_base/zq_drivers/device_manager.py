# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 17:20:06 2024

@author: eyazici
Based on DeviceManager of the DaemonDAQ module
"""
import sys
import Pyro4
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base\zq_drivers\pyro_nw')
from nameserver_client import nameserver as ns
from colorama import Fore, Back, Style
from HP4142B import *
from NIDAQ import *
from ELL14 import *


Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = "pickle"
Pyro4.config.REQUIRE_EXPOSE = False
Pyro4.config.PICKLE_PROTOCOL_VERSION = 4   #added on 24-02-2022


def connect(objectId, nameserver = ns, exile_id=None, uri = None):
    try:
        if exile_id is not None:
            # uri = 'PYRO:' + exile_id + '@phd-exile-phys.ethz.ch:' + str(9090)
            uri = 'PYRO:' + exile_id + '@phd-exile-phys.ethz.ch:' + str(9091)
        elif uri is None:
            uri = nameserver.lookup(objectId)
        
        proxy = Pyro4.Proxy(uri)
        proxy._pyroBind()
        print(Fore.GREEN + Style.BRIGHT + "Connection success: " + objectId + Fore.RESET)
        return proxy
    except:
        print(Fore.RED + Style.BRIGHT + "Connection failure: " + objectId + Fore.RESET)
        return None

HP4142B_c       = connect('HP4142B_r')
WinSpec_c       = connect('WinSpec', exile_id = 'WinSpec')
# LightField_c    = connect('LightField', uri = 'PYRO:LightField@G15-Pylon.dhcp-int.phys.ethz.ch:63899')        
NIDAQ_c = connect("NIDAQ")
ELL1_c = connect("ELL14")
ELL2_c = connect("ELL14_2")
ELL3_c = connect("ELL14_3")


hp = HP4142B_c
ws = WinSpec_c
daq = NIDAQ_c
# lf = LightField_c
ell1 = ELL1_c
ell2 = ELL2_c
ell3 = ELL3_c