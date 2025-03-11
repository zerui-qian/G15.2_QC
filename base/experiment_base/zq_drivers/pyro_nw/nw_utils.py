# -*- coding: utf-8 -*-
"""
Created on Mon Jun 04 14:15:01 2018

@author: Yuya Shimazaki
"""

from nameserver_client import *
import nw_config as config

import Pyro4
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
Pyro4.config.SERIALIZER = "pickle"
Pyro4.config.REQUIRE_EXPOSE = False
Pyro4.config.PICKLE_PROTOCOL_VERSION = 4   #added on 24-02-2022


def connect(objectId):
    try:
        uri = ns.lookup(objectId)
        proxy = Pyro4.Proxy(uri)
        proxy._pyroBind()
        return (proxy, "Connection success: " + objectId)
    except:
        return (None, "Connection failure: " + objectId)

def RunServer(object_dict, host = 'localhost'):
    
    Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')
    Pyro4.config.SERIALIZER = "pickle"
    Pyro4.config.REQUIRE_EXPOSE = False
    
    daemon = Pyro4.Daemon(host = host)
    objectIds = object_dict.keys()
    for objectId in objectIds:
        uri = daemon.register(object_dict[objectId], objectId = objectId)
        nameserver.register(objectId, uri)
        print("Ready. Object uri = ", uri)
        
    print('name server: %s'%nameserver)
    
    daemon.requestLoop()
    
