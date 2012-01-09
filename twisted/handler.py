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

#Helper proxy for keeping track of dbus server invocation results and combining these.                       
class StateProxy:
    def __init__(self,routerstate,clientip,gatewaynum,httpserverip):
        self.routingcommandstate=None
        self.dnscommandstate=None
        self.routerstate=routerstate
        self.clientip=clientip
        self.gatewaynum=gatewaynum
        self.httpserverip=httpserverip
        self.routerstate.startUpdate(clientip,gatewaynum,httpserverip)
    def _partialSuccess(self):
        #If both requests completed than we need to forward something.
        if (self.dnscommandstate !=  None) and (self.routingcommandstate != None):
            #Test if both requests succeeded
            if self.dnscommandstate and self.routingcommandstate:
                self.routerstate.completeUpdate(self.clientip,self.gatewaynum,self.httpserverip)
            else:
                #If the other request failed, than we are in a bad state, one request succeeded and the other failed.
                self.routerstate.brokenUpdate(clientip,gatewaynum,httpserverip)
    def _partialFailure(self):
        #If both requests completed than we need to forward something.
        if (self.dnscommandstate != None) and (self.routingcommandstate != None ):
            #Test if the other request succeeded
            if self.dnscommandstate or self.routingcommandstate:
                #If the other request succeeded, than we are in a bad state, one request succeeded and the other failed.
                self.routerstate.brokenUpdate(clientip,gatewaynum,httpserverip)
            else:
                #If both failed than we are still in the old state and we have just a failed request.
                self.routerstate.failedUpdate(clientip,gatewaynum,httpserverip)
    def DnsSetResult(self,res):
        if res:
            #Positive DNS command result from dbus server.
            self.dnscommandstate=True
            self._partialSuccess()
        else:
            #Failure indication from dbus server.
            self.dnscommandstate=False
            self._partialFailure()
    def GatewaySetResult(self,res):
        if res:
            #Positive PBR command result from dbus server.
            self.routingcommandstate=True
            self._partialSuccess()
        else:
            #Failure indication from dbus server.
            self.routingcommandstate=False
            self._partialFailure()
    def DnsSetError(self,err):
        #Failure with the dns dbus
        self.dnscommandstate=False
        self._partialFailure()
    def GatewaySetError(self,err):
        #Failure with the PBR dbus 
        self.routingcommandstate=False
        self._partialFailure()

#Not done by far
class DynamicRouterState:
    def __init__(self,conf):
        #self.gatewayusers={}  : instead use self.gateways[gwnum]
        #self.workstationinfo={} : instead use self.networks[serverip]
        self.updatesinprogess={}
        self.gateways={}
        self.networks={}
        for gateway in conf["gateways"]:
            gwnum=gateway["tableno"]
            self.gateways[gwnum] = {}
        for clientnet in conf["devices"]["clients"]:
            serverip=clientnet["ip"]
            self.networks[serverip]={}            
    def getStateProxy(self,clientip,gatewaynum,httpserverip):
        return StateProxy(self,clientip,gatewaynum,httpserverip)
    def startUpdate(self,clientip,gatewaynum,httpserverip):
        if self.updatesinprogess.has_key(clientip):
           self.updatesinprogess[clientip] = self.updatesinprogess[clientip] + 1
        else:
           self.updatesinprogess[clientip] = 1 
        if self.workstationinfo.has_key(clientip):
            wsinfo=self.workstationinfo[clientip]
            wsinfo["waiting"]=True
        else:
            self.workstationinfo[clientip] = {}
            self.workstationinfo[clientip]["waiting"]=True
            self.workstationinfo[clientip]["valid"]=True
            self.workstationinfo[clientip]["gateway"]=0
            self.workstationinfo[clientip]["futuregw"]=[]
            self.workstationinfo[clientip]["futuregw"].push_back(gatewaynum)
        #We already let this workstation count in the newly selected gateway, but also still in the old one.
        if self.gatewayusers.has_key(gatewaynum):
            self.gatewayusers[gatewaynum] = self.gatewayusers[gatewaynum] +1
        else:
            self.gatewayusers[gatewaynum] = 1
    def failedUpdate(self,clientip,gatewaynum,httpserverip):
        self.updatesinprogess[clientip] = self.updatesinprogess[clientip] -1
        if self.updatesinprogess[clientip] == 0:
            if self.updatesinprogess[clientip] == 0:
                self.workstationinfo[clientip]["waiting"]=False
                self.workstationinfo[clientip]["futuregw"]=[]
        self.gatewayusers[gatewaynum] = self.gatewayusers[gatewaynum] -1
    def brokenUpdate(self,clientip,gatewaynum,httpserverip):
        #Roll back the startUpdate stuff
        self.updatesinprogess[clientip] = self.updatesinprogess[clientip] -1
        self.gatewayusers[gatewaynum] = self.gatewayusers[gatewaynum] -1
        #Remove this workstation from the old gateway too
        oldgw = self.workstationinfo[clientip]["gateway"]
        self.gatewayusers[oldgw] = self.gatewayusers[oldgw] -1
        #Update the workstation info
        self.workstationinfo[clientip]["gateway"] = 0
        self.workstationinfo[clientip]["valid"] = False
        self.workstationinfo[clientip]["waiting"]=False
        if self.updatesinprogess[clientip] == 0:
            self.workstationinfo[clientip]["futuregw"]=[]
    def completeUpdate(self,clientip,gatewaynum,httpserverip):
        self.updatesinprogess[clientip] = self.updatesinprogess[clientip] -1
        #Remove this workstation from the old gateway
        oldgw = self.workstationinfo[clientip]["gateway"]
        self.gatewayusers[oldgw] = self.gatewayusers[oldgw] -1
        if self.updatesinprogess[clientip] == 0:
            self.workstationinfo[clientip]["waiting"]=False
            self.workstationinfo[clientip]["futuregw"]=[]
        else:
            pass #FIXME    
        self.gatewayusers[oldgw] = self.gatewayusers[oldgw] -1
        
    def __call__(self):
        print "DynamicRouterState invoked"
        return ""

#Client for the DNS service.
class DynRDnsDbusClient:
    def __init__(self,bus,parkip):
        self.parkip=parkip
        self.remote_object = bus.get_object("nl.dnpa.pbdns.DaemonManager","/DaemonManager")
    def setGateway(self,clientip,gatewayip,updstate):
        if gatewayip ==  self.parkip:
            #Invoke clear asynchonously, letting the proxy state object handle the result.
            return self.remote_object.clear(clientip,
                dbus_interface = "nl.dnpa.pbdns.DaemonManager",
                reply_handler=updstate.DnsSetResult,
                error_handler=updstate.DnsSetError)
        else :
            #Invoke clear asynchonously, letting the proxy state object handle the result.
            return self.remote_object.setGateway(clientip,gatewayip,
                dbus_interface = "nl.dnpa.pbdns.DaemonManager",
                reply_handler=updstate.DnsSetResult,
                error_handler=updstate.DnsSetError)

#Client for the routing service.
class DynRPbrDbusClient:
    def __init__(self,bus):
        self.remote_object = bus.get_object("nl.dnpa.pbr.GatewayManager","/GatewayManager")
    def setGateway(self,clientip,gatewayip,updstate):
        #Invoke setGateway asynchonously, letting the proxy state object handle the result.
        return self.remote_object.setGateway(clientip,gatewayip,
            dbus_interface = "nl.dnpa.pbr.GatewayManager",
            reply_handler=updstate.GatewaySetResult,
            error_handler=updstate.GatewaySetError)

#The DbusClient combines a client for both dbus services.
class DbusClient: 
    def __init__(self,gateways,parkip):
        self.gateways = gateways
        bus = dbus.SystemBus()
        self.routing = DynRDnsDbusClient(bus,parkip)
        self.dns = DynRPbrDbusClient(bus)
    def setGateway(self,clientip,gatewaynum,state,httpserverip):
        #Only allow setGateway to work on allowed gateways as defined in the config.
        if self.gateways.has_key(str(gatewaynum)):
            #Get a proxy object for updating the state based on the progresso of both active dbus calls.
            updstate=state.getStateProxy(clientip,gatewaynum,httpserverip)
            #Look ip the gateway IP by number.
            gwip=self.gateways[gatewaynum]
            #Start the asynchonous call to the routing dbus service.
            self.routing.setGateway(clientip,gwip,updstate)
            #Start the asynchonous call to the dns dbus service.
            self.dns.setGateway(clientip,gwip,updstate)

class DynamicRouterRequestHandler(http.Request):
    def __init__(self,conf,html,state,dbusclient, *args):
        self.conf=conf
        self.html=html
        self.state=state
        self.dbusclient=dbusclient
        #Where to find what static file.
        self.files = { "/gridview2.js" : "ecmascript",
            "/wait.png" : "images",
            "/router.png" : "images",
            "/parkip.png" : "images",
            "/favicon.ico" : "images"}
        http.Request.__init__(self,*args)
    def process(self):
        needredirect=False
        #Normaly the client should be addressed by its IP.
        if self.getRequestHostname() == self.getHost().host:
            #Our main application page generated at startup time.
            if self.path == "/gatewaylist":
                self.setHeader('Content-Type', 'text/html')
                self.write(self.html)
            #The dynamic ajaxy status stuff.
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
                self.dbusclient.setGateway(clientip,gatewaynum,self.state,self.getHost().host)
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
        #If directed at a host name, the client will likely be 'parked'.
        else:
            #If the client uses a hostname, redirect to the main url.
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
state=DynamicRouterState(conf)
try:
    template=jinja2.Environment(loader=jinja2.FileSystemLoader("/var/dynr-web/templates",encoding='utf-8')).get_template('index.tmpl')
except jinja2.exceptions.TemplateNotFound:
    print "ERROR: /var/dynr-web/templates/index.tmpl not found!"
    exit(1)
for clientip in conf.clientips():
    reactor.listenTCP(8765,DynamicRouterHttpFactory(conf,clientip,dbusclient,state,template),10,clientip)
reactor.run()
