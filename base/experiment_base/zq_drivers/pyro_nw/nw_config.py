# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 17:45:51 2024

@author: QPG
"""
import socket
HOSTNAME = socket.gethostname()

CONFIG = dict(
    PYRO_HOST = 'localhost',
    PYRO_PORT =  9090,
)

G15_2_CONFIG = dict(
    HP4142B_ADDR = 'GPIB0::17::INSTR',
    PYRO_HOST = 'G15-OT.dhcp-int.phys.ethz.ch',
    PYRO_PORT =  9090,
    ANC300_ADDR = 'COM3',
    ANC150_ADDR = 'COM11'
)

if HOSTNAME == 'G15_2' or HOSTNAME == 'G15-OT': 
    CONFIG.update(G15_2_CONFIG)