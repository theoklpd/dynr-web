#!/usr/bin/python
from twisted.internet import glib2reactor #We need this reactor to let dbus and twisted play nice together.
glib2reactor.install() #Turn glib2reactor into the reactor.
from twisted.internet import reactor #Now import reactor, being glib2reactor.
from twisted.web import http
from twisted.web.static import File
import os
import json
import sys
import jinja2
import dbus
import gobject
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

class DynamicRouterConfig:
    def __init__(self,conffile):
        infile=open(conffile,"r")
        self.config=json.load(infile)
        infile.close()
    def getGroupName(self,host):
        for clientnet in self.config["devices"]["clients"]:
            if clientnet["ip"] == host:
                return clientnet["groupname"]
        return None
    def clientips(self):
        for clientnet in self.config["devices"]["clients"]:
            yield clientnet["ip"]
    def getGatewayList(self,host):
        groupname=self.getGroupName(host)
        gwlist = []
        for gateway in self.config["gateways"]:
            gw={}
            gw["groupaccess"]=False
            gw["otheraccess"]=False
            groups=gateway["allowedgroups"]
            for allowed in groups:
                if groupname == allowed:
                    gw["groupaccess"]=True
                else:
                    gw["otheraccess"]=True
            gw["name"]=gateway["name"]
            gwlist.append(gw)
        return gwlist
    def getGatewaysMap(self):
        gwmap={}
        for gateway in self.config["gateways"]:
            num=gateway["tableno"]
            ip=gateway["ip"]
            gwmap[str(num)]=ip
            print str(num) + " -> " + ip
        return gwmap    
    def getParkIp(self):
        for gateway in self.config["gateways"]:
            name=gateway["name"]
            if name == "parkip":
                return gateway["ip"]
                        
class StateProxy:
    def __init__(self,routerstate,clientip,gatewaynum):
        self.startedstate=0
        self.routingcommandstate=0
        self.dnscommandstate=0
        self.routerstate=routerstate
        self.clientip=clientip
        self.gatewaynum=gatewaynum
    def _partialSuccess(self):
        if (self.dnscommandstate > 0) and (self.routingcommandstate > 0):
            if (self.dnscommandstate > 1) or (self.routingcommandstate > 1):
                print "Partial failure: ",self.startedstate,self.routingcommandstate,self.dnscommandstate 
            else:
                print "Full success"
    def _partialFailure(self):
        if (self.dnscommandstate > 0) and (self.routingcommandstate > 0):
            if (self.dnscommandstate > 1) and (self.routingcommandstate > 1):
                print "Full failure."
            else:
                print "Partial failure"
    def StartedDnsClear(self):
        self.startedstate=1
    def DnsClearResult(self,res):
        if res:
            self.dnscommandstate=1
            self._partialSuccess()
        else:
            self.dnscommandstate=2
            self._partialFailure()
    def DnsClearError(self,err):
        self.dnscommandstate=3
        self._partialFailure()
    def StartedDnsSet(self):
        self.startedstate=2
    def DnsSetResult(self,res):
        if res:
            self.dnscommandstate=1
            self._partialSuccess()
        else:
            self.dnscommandstate=2
            self._partialFailure()
    def DnsSetError(self,err):
        self.dnscommandstate=3
        self._partialFailure()
        print err
    def StartedGatewaySet(self):
        self.startedstate=1
    def GatewaySetResult(self,res):
        if res:
            self.routingcommandstate=1
            self._partialSuccess()
        else:
            self.routingcommandstate=2
            self._partialFailure()
    def GatewaySetError(self,err):
        self.routingcommandstate=3
        self._partialFailure()

class DynamicRouterState: #TODO
    def __init__(self):
        self.requeststate={}
    def getStateProxy(self,clientip,gatewaynum):
        return StateProxy(self,clientip,gatewaynum)
    def __call__(self):
        print "DynamicRouterState invoked"
        return ""

class DynRDnsDbusClient:
    def __init__(self,bus,parkip):
        self.parkip=parkip
        self.remote_object = bus.get_object("nl.dnpa.pbdns.DaemonManager","/DaemonManager")
    def setGateway(self,clientip,gatewayip,updstate):
        print "DynRDnsDbusClient::setGateway(" + clientip + "," + gatewayip + ",updstate)"
        if gatewayip ==  self.parkip:
            updstate.StartedDnsClear()
            return self.remote_object.clear(clientip,
                dbus_interface = "nl.dnpa.pbdns.DaemonManager",
                reply_handler=updstate.DnsClearResult,
                error_handler=updstate.DnsClearError)
        else :
            updstate.StartedDnsSet()
            return self.remote_object.setGateway(clientip,gatewayip,
                dbus_interface = "nl.dnpa.pbdns.DaemonManager",
                reply_handler=updstate.DnsSetResult,
                error_handler=updstate.DnsSetError)
        
class DynRPbrDbusClient:
    def __init__(self,bus):
        self.remote_object = bus.get_object("nl.dnpa.pbr.GatewayManager","/GatewayManager")
    def setGateway(self,clientip,gatewayip,updstate):
        updstate.StartedGatewaySet()
        print "DynRPbrDbusClient::setGateway(" + clientip + "," + gatewayip + ",updstate)"
        return self.remote_object.setGateway(clientip,gatewayip,
            dbus_interface = "nl.dnpa.pbr.GatewayManager",
            reply_handler=updstate.GatewaySetResult,
            error_handler=updstate.GatewaySetError)

class DbusClient: 
    def __init__(self,gateways,parkip):
        self.gateways = gateways
        bus = dbus.SystemBus()
        self.routing = DynRDnsDbusClient(bus,parkip)
        self.dns = DynRPbrDbusClient(bus)
    def setGateway(self,clientip,gatewaynum,state):
        if self.gateways.has_key(str(gatewaynum)):
            updstate=state.getStateProxy(clientip,gatewaynum)
            gwip=self.gateways[gatewaynum]
            self.routing.setGateway(clientip,gwip,updstate)
            self.dns.setGateway(clientip,gwip,updstate)
        else:
            print gatewaynum + " not part of self.gateways in DbusClient::setGateway"

class DynamicRouterRequestHandler(http.Request):
    def __init__(self,conf,html,state,dbusclient, *args):
        self.conf=conf
        self.html=html
        self.state=state
        self.dbusclient=dbusclient
        self.files = { "/gridview2.js" : "ecmascript",
            "/wait.png" : "images",
            "/router.png" : "images",
            "/parkip.png" : "images",
            "/favicon.ico" : "images"}
        http.Request.__init__(self,*args)
    def process(self):
        needredirect=False
        print self.path
        if self.getRequestHostname() == self.getHost().host:
            #Our main application page generated at startup time.
            if self.path == "/gatewaylist":
                self.setHeader('Content-Type', 'text/html')
                self.write(self.html)
            #The dynamic status stuff.
            elif self.path == "/routerstatus":
                self.setHeader('Content-Type', 'application/json')
                self.write(self.state())
            #Changing the current gateway for a given client ip.
            elif self.path == "/setgateway":
                self.setHeader('Content-Type', 'text/html')
                clientip=self.getClientIP()
                print "clientip=" + clientip
                gatewaynum = self.args["gw"][0]
                print "gatewaynum=" + gatewaynum
                self.dbusclient.setGateway(clientip,gatewaynum,self.state)
                print "request made"
                self.write("<h1>Request made</h1>")
            #Our static files (images and javascript.
            elif self.files.has_key(self.path):
                realfile="/var/dynr-web/" + self.files[self.path] + self.path
                rfile=File(realfile)
                rfile.render_GET(self)
                self.unregisterProducer()
            #Anything else we redirect to our main application page.
            else:
                needredirect=True
        #If directed at a host name, redirect to the main application page using the IP address.
        else:
            needredirect=True
        if needredirect:
            host=self.getHost().host
            port=self.getHost().port
            self.redirect("http://" + str(host) + ":" + str(port) + "/gatewaylist")
        self.finish()
        self.unregisterProducer()

class DynamicRouterHttp(http.HTTPChannel):
    requestFactory = DynamicRouterRequestHandler
    def __init__(self,conf,html,state,dbusclient):
        http.HTTPChannel.__init__(self)
        self.conf=conf
        self.html=html
        self.state=state
        self.dbusclient=dbusclient
        http.HTTPChannel.__init__(self)
    def requestFactory(self, *args):
        return DynamicRouterRequestHandler(self.conf,self.html,self.state,self.dbusclient, *args)
    
        

class DynamicRouterHttpFactory(http.HTTPFactory):
    protocol = DynamicRouterHttp
    def __init__(self,conf,ip,dbusclient,state,template):
        self.conf=conf
        self.ip=ip
        self.state=state
        self.dbusclient=dbusclient
        gwlist=conf.getGatewayList(ip)
        self.html=str(template.render({"gateway_list" : gwlist}))
        http.HTTPFactory.__init__(self)
    def buildProtocol(self, addr):
        return DynamicRouterHttp(self.conf,self.html,self.state,self.dbusclient)
        

if os.system("/usr/bin/pbr-checkconfig.py"):
    sys.exit(1)
conf=DynamicRouterConfig("/etc/pbrouting.json")
dbusclient=DbusClient(conf.getGatewaysMap(),conf.getParkIp())
state=DynamicRouterState()
try:
    template=jinja2.Environment(loader=jinja2.FileSystemLoader("/var/dynr-web/templates",encoding='utf-8')).get_template('index.tmpl')
except jinja2.exceptions.TemplateNotFound:
    print "ERROR: /var/dynr-web/templates/index.tmpl not found!"
    exit(1)
for clientip in conf.clientips():
    reactor.listenTCP(8765,DynamicRouterHttpFactory(conf,clientip,dbusclient,state,template),10,clientip)
reactor.run()
