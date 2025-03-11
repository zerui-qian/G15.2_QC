# -*- coding: utf-8 -*-
"""
Created on Fri Aug 04 11:03:03 2017

@author: Yuya Shimazaki, Emre Yazici 
"""

import Pyro4
import Pyro4.naming
import nw_config as config
import threading
import time


Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = "pickle"
Pyro4.config.REQUIRE_EXPOSE = False
Pyro4.config.PICKLE_PROTOCOL_VERSION = 4   #added on 24-02-2022


host = config.CONFIG['PYRO_HOST']
port = config.CONFIG['PYRO_PORT']

url, daemon, bcserver = Pyro4.naming.startNS(
    host = host,
    port = port
)

print("ready", url)
print("listening %s:%s" % (host, port))

thread = threading.Thread(target = daemon.requestLoop)
thread.setDaemon(True)
thread.start()
while True: 
    time.sleep(0.01) # this way this doesn't use as much resources as with pass

