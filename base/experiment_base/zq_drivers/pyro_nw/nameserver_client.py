# -*- coding: utf-8 -*-
"""
Created on Fri Jul 28 08:05:14 2017

@author: Yuya Shimazaki
"""

import Pyro4
import subprocess
import os, sys
import time
import nw_config as config

NS_host = config.CONFIG['PYRO_HOST']
NS_port = config.CONFIG['PYRO_PORT']

def remove_unreachable_proxy(ns):
    for (objectId, proxy) in ns.list().items():
        with Pyro4.Proxy(proxy) as p:
            try:
                p._pyroBind()
            except Pyro4.errors.CommunicationError:
                print('removing unreachable pyro proxy: {}'.format(objectId))
                ns.remove(objectId)
                
def start_nameserver():
    print('starting new Pyro4 nameserver')
    PythonwEXE = os.path.join(sys.exec_prefix, 'pythonw.exe')
    client_path = os.path.realpath(__file__)
    host_path = client_path.replace('client', 'host')
    subprocess.Popen([PythonwEXE, host_path], creationflags = subprocess.CREATE_NEW_CONSOLE)
    time.sleep(1)

def locate_nameserver(host, port):
    return Pyro4.locateNS(
        host = host,
        port = port
    #    hmac_key = "9tzuWZ!hkKR$xM?@E5gDpLQ8d7T45>~e"
    )

try:
    nameserver = locate_nameserver(NS_host, NS_port)
except:
    start_nameserver()
    nameserver = locate_nameserver(NS_host, NS_port)

remove_unreachable_proxy(nameserver)