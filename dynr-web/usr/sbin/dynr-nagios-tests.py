#!/usr/bin/python
import json
import os

def processRunning(cmd):
    return os.system(cmd + ">/dev/null") == 0

def routingDbusDaemonRunning():
    return processRunning("ps -C pbr-dbus.py h")

def dnsServerRunning(ip):
    return processRunning("ps -C pbdnsd h|grep "+ ip)

def dnsDbusDaemonRunning():
    return processRunning("ps -C pbdns-dbus.py h")

def webServerRunning():
    return processRunning("ps -C dynr-web.py")

def getIpList():
    configpath="/etc/pbrouting.json"
    if (not os.path.isfile(configpath)):
        print "CRITICAL: No configuration file installed."
        exit(2)
    try:
        infile=open(configpath,"r")
    except:
        print "CRITICAL: Unable to open config file."
        exit(2)
    try:
        conf=json.load(infile)
    except:
        print "CRITICAL: Config file isn't valid JSON."
        exit(2)
    if not conf.has_key("devices"):
        print "CRITICAL: Config file has no 'devices' section"
        exit(2)
    if not conf["devices"].has_key("clients"):
        print "CRITICAL: Config file has no 'devices::clients' section"
        exit(2)
    for device in conf["devices"]["clients"]:
        if not device.has_key("ip"):
            print "CRITICAL: Config file has a 'devices::clients[]' withou the mandatory 'ip' defined for it."
            exit(2) 
        yield device["ip"]

everytingirie = True
completelydown=True
notrunning = []
running=[]
if not routingDbusDaemonRunning():
    notrunning.append("pbdns_dbus")
    everytingirie = False
else:
    running.append("pbdns_dbus")
    completelydown=False
for ip in getIpList():
    if not dnsServerRunning(ip):
        notrunning.append("pbdnsd[" + ip + "]")
        everytingirie = False
    else:
        running.append("pbdnsd[" + ip + "]")
        completelydown=False
if not dnsDbusDaemonRunning():
    notrunning.append("pbr_dbus")
    everytingirie = False
else:
    running.append("pbr_dbus")
    completelydown=False
if not webServerRunning():
    notrunning.append("dynr_web")
    everytingirie = False
else:
    running.append("dynr_web")
    completelydown=False
if everytingirie:
    print "OK: everything is running just fine"
    exit(0)
else:
    if completelydown:
        print "WARNING: Dynamic router is completely down. Probably disabled."
        exit(1)
    else:
        print "CRITICAL: Dynamic router is partialy down. Active sub-systems : " , running , " ; Inactive subsystems : " , notrunning


