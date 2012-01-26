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
import daemon
import syslog

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
        return gwmap    
    def getParkIp(self):
        for gateway in self.config["gateways"]:
            name=gateway["name"]
            if name == "parkip":
                return gateway["ip"]
    def __getitem__(self,key):
        return self.config[key]

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
        syslog.syslog(syslog.LOG_ERR,"DEBUG: _partialSuccess.")        
        #If both requests completed than we need to forward something.
        if (self.dnscommandstate !=  None) and (self.routingcommandstate != None):
            #Test if both requests succeeded
            if self.dnscommandstate and self.routingcommandstate:
                self.routerstate.completeUpdate(self.clientip,self.gatewaynum,self.httpserverip)
            else:
                #If the other request failed, than we are in a bad state, one request succeeded and the other failed.
                self.routerstate.brokenUpdate(self.clientip,self.gatewaynum,self.httpserverip)
    def _partialFailure(self):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: _partialFailure.")        
        #If both requests completed than we need to forward something.
        if (self.dnscommandstate != None) and (self.routingcommandstate != None ):
            #Test if the other request succeeded
            if self.dnscommandstate or self.routingcommandstate:
                #If the other request succeeded, than we are in a bad state, one request succeeded and the other failed.
                self.routerstate.brokenUpdate(self.clientip,self.gatewaynum,self.httpserverip)
            else:
                #If both failed than we are still in the old state and we have just a failed request.
                self.routerstate.failedUpdate(self.clientip,self.gatewaynum,self.httpserverip)
    def DnsSetResult(self,res):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: DnsResult.")        
        if res:
            syslog.syslog(syslog.LOG_ERR,"DEBUG: DNS=OK")        
            #Positive DNS command result from dbus server.
            self.dnscommandstate=True
            self._partialSuccess()
        else:
            syslog.syslog(syslog.LOG_ERR,"Dns set error (returned failure)")
            #Failure indication from dbus server.
            self.dnscommandstate=False
            self._partialFailure()
    def GatewaySetResult(self,res):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: GatewayResult.")        
        if res:
            syslog.syslog(syslog.LOG_ERR,"DEBUG: Gateway=OK.")        
            #Positive PBR command result from dbus server.
            self.routingcommandstate=True
            self._partialSuccess()
        else:
            syslog.syslog(syslog.LOG_ERR,"Gateway set error (returned failure)")
            #Failure indication from dbus server.
            self.routingcommandstate=False
            self._partialFailure()
    def DnsSetError(self,err):
        #Failure with the dns dbus
        syslog.syslog(syslog.LOG_ERR,"Dns set error (dbus failure)") 
        self.dnscommandstate=False
        self._partialFailure()
    def GatewaySetError(self,err):
        syslog.syslog(syslog.LOG_ERR,"Gateway set error (dbus failure)") 
        #Failure with the PBR dbus 
        self.routingcommandstate=False
        self._partialFailure()

#Not done by far
class DynamicRouterState:
    def __init__(self,conf):
        self.updatesinprogess={}
        self.gateways={}
        self.networks={}
        for gateway in conf["gateways"]:
            gwnum=gateway["tableno"]
            self.gateways[gwnum] = {}
            for clientnet in conf["devices"]["clients"]:
                serverip=clientnet["ip"]
                self.gateways[gwnum][serverip] = 0
        for clientnet in conf["devices"]["clients"]:
            serverip=clientnet["ip"]
            self.networks[serverip]={}            
    def getStateProxy(self,clientip,gatewaynum,httpserverip):
        return StateProxy(self,clientip,gatewaynum,httpserverip)
    def startUpdate(self,clientip,gatewaynum,httpserverip):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: startUpdate.")        
        #There can be more than one update in progress, lets count them.
        if self.updatesinprogess.has_key(clientip):
           self.updatesinprogess[clientip] = self.updatesinprogess[clientip] + 1
        else:
           self.updatesinprogess[clientip] = 1 
        #Fetch the relevant network with client IPs.
        network=self.networks[httpserverip]
        #Check if the client IP is known (since system startup)
        if network.has_key(clientip):
            #Client is known, update the record.
            wsinfo=network[clientip]
            #Indicate that this workstation is waiting for the operation to complete.
            wsinfo["waiting"]=True
            #Mark the new gateway number as a potential new gateway.
            network[clientip]["futuregw"][gatewaynum]=True
        else: 
            #For an unknown client create a brand new clean record.
            network[clientip] = {}
            network[clientip]["waiting"]=True
            network[clientip]["valid"]=True
            network[clientip]["gateway"]=None
            network[clientip]["futuregw"]={}
            network[clientip]["futuregw"][gatewaynum]=True
        #We already let this workstation count in the newly selected gateway, but also still in the old one.
        if self.gateways.has_key(gatewaynum):
            if self.gateways[gatewaynum].has_key(httpserverip):
                self.gateways[gatewaynum][httpserverip] = self.gateways[gatewaynum][httpserverip] + 1
            else:
                syslog.syslog(syslog.LOG_ERR,str(httpserverip) + " not defined in gateways. This should not happen.")
        else:
            syslog.syslog(syslog.LOG_ERR,str(gatewaynum)+" "+str(type(gatewaynum)) + "not in gateways. This should not happen.")
    def failedUpdate(self,clientip,gatewaynum,httpserverip):
        syslog.syslog(syslog.LOG_ERR,"Update error (full failure: results in valid state)")
        #The update failed completely (both dns and routing).
        #First decrement the number of updates in progress.
        self.updatesinprogess[clientip] = self.updatesinprogess[clientip] -1
        #Fetch the relevant network with client IPs.
        network=self.networks[httpserverip]
        #unmark the gateway number as a future one.
        network[clientip]["futuregw"][gatewaynum]=False
        #If there are no other updates in progress we are no longer waiting.
        if self.updatesinprogess[clientip] == 0:
            network[clientip]["waiting"]=False
        #Decrement the count for the failed prospective new gateway.
        self.gateways[gatewaynum][httpserverip] = self.gateways[gatewaynum][httpserverip] - 1
    def brokenUpdate(self,clientip,gatewaynum,httpserverip):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: brokenUpdate.")        
        syslog.syslog(syslog.LOG_ERR,"Update error (partial failure: results in invalid state)")
        #The update failed partially, this is bad.
        #First decrement the number of updates in progress.
        self.updatesinprogess[clientip] = self.updatesinprogess[clientip] -1
        #Fetch the relevant network with client IPs.
        network=self.networks[httpserverip]
        #Let it be known that we are in an invalid state
        network[clientip]["valid"]=False
        #unmark the gateway number as a future one.
        network[clientip]["futuregw"][gatewaynum]=False
        #If there are no other updates in progress we are no longer waiting.
        if self.updatesinprogess[clientip] == 0:
            network[clientip]["waiting"]=False
        #Decrement the count for the original IP.
        if network[clientip]["gateway"] != None:
            originalgateway=network[clientip]["gateway"]
            self.gateways[originalgateway][httpserverip] = self.gateways[originalgateway][httpserverip] -1
        #There now is no original gateway left
        network[clientip]["gateway"]=None
        #Decrement the count for the failed prospective new gateway.
        self.gateways[gatewaynum][httpserverip] = self.gateways[gatewaynum][httpserverip] - 1
    def completeUpdate(self,clientip,gatewaynum,httpserverip):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: completeUpdate.")        
        #The update completed succesfully.
        #First decrement the number of updates in progress.
        self.updatesinprogess[clientip] = self.updatesinprogess[clientip] -1
        #Fetch the relevant network with client IPs.
        network=self.networks[httpserverip]
        #Let it be known that we are now in a valid state.
        network[clientip]["valid"]=True
        #unmark the gateway number as a future one.
        network[clientip]["futuregw"][gatewaynum]=False
        #If there are no other updates in progress we are no longer waiting.
        if self.updatesinprogess[clientip] == 0:
            network[clientip]["waiting"]=False
        #Decrement the count for the original IP.
        if network[clientip]["gateway"] != None:
            originalgateway=network[clientip]["gateway"]
            self.gateways[originalgateway][httpserverip] = self.gateways[originalgateway][httpserverip] -1
        #Set the current gateway
        network[clientip]["gateway"] = gatewaynum
    def __call__(self,httpserverip,clientip):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: Fetching router state as json")        
        network=self.networks[httpserverip]
        if network.has_key(clientip):
            wsinfo=network[clientip]
        else:
            wsinfo = {}
            wsinfo["waiting"]=False
            wsinfo["valid"]=True
            wsinfo["gateway"]=None
            wsinfo["futuregw"]={}
        gateways=[]
        for gwid in self.gateways:
            gwnew=dict()
            gwnew["id"]=gwid
            gwnew["groupcount"]=0
            gwnew["othercount"]=0
            gwnew["selected"]=False
            gwnew["specialstate"]=""
            gateway=self.gateways[gwid]
            for serverip in gateway:
                count=gateway[serverip]
                if serverip == httpserverip:
                    gwnew["groupcount"] = gwnew["groupcount"] + count
                else:
                    gwnew["othercount"] = gwnew["othercount"] + count
            if wsinfo["gateway"] == gwid:
                if wsinfo["valid"]:
                    if wsinfo["waiting"]:
                        gwnew["specialstate"] = "waiting"
                    else:
                        gwnew["selected"]=True
                else:
                    gwnew["specialstate"] = "invalid"
            if wsinfo["futuregw"].has_key(gwid) and wsinfo["futuregw"]:
                if not wsinfo["valid"]:
                    gwnew["specialstate"] = "invalid"
            else:
                if wsinfo["waiting"]:
                    gwnew["specialstate"] = "waiting"
            gateways.append(gwnew)    
        return json.dumps(gateways, indent=4)

#Client for the DNS service.
class DynRDnsDbusClient:
    def __init__(self,bus,parkip):
        self.parkip=parkip
        self.remote_object = bus.get_object("nl.dnpa.pbdns.DaemonManager","/DaemonManager")
    def setGateway(self,clientip,gatewayip,updstate):
        syslog.syslog(syslog.LOG_ERR,"DEBUG: setGateway called for dns.")        
        if gatewayip ==  self.parkip:
            syslog.syslog(syslog.LOG_ERR,"DEBUG: setGateway called for parkip.")        
            #Invoke clear asynchonously, letting the proxy state object handle the result.
            return self.remote_object.clear(clientip,
                dbus_interface = "nl.dnpa.pbdns.DaemonManager",
                reply_handler=updstate.DnsSetResult,
                error_handler=updstate.DnsSetError)
        else :
            syslog.syslog(syslog.LOG_ERR,"DEBUG: setGateway called for normal gateway")        
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
        syslog.syslog(syslog.LOG_ERR,"DEBUG: setGateway called for pbr.")        
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
        syslog.syslog(syslog.LOG_ERR,"DEBUG: setGateway called.")        
        #Only allow setGateway to work on allowed gateways as defined in the config.
        if self.gateways.has_key(str(gatewaynum)):
            syslog.syslog(syslog.LOG_ERR,"DEBUG:   On valid gateway number.")
            #Get a proxy object for updating the state based on the progresso of both active dbus calls.
            updstate=state.getStateProxy(clientip,gatewaynum,httpserverip)
            #Look ip the gateway IP by number.
            gwip=self.gateways[str(gatewaynum)]
            #Start the asynchonous call to the routing dbus service.
            self.routing.setGateway(clientip,gwip,updstate)
            #Start the asynchonous call to the dns dbus service.
            self.dns.setGateway(clientip,gwip,updstate)

class DynamicRouterRequestHandler(http.Request):
    def __init__(self,html,state,dbusclient, *args):
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
        syslog.syslog(syslog.LOG_ERR,"DEBUG: http request received.")        
        needredirect=False
        #Normaly the client should be addressed by its IP.
        if self.getRequestHostname() == self.getHost().host:
            syslog.syslog(syslog.LOG_ERR,"DEBUG: by ip")
            #Our main application page generated at startup time.
            if self.path == "/gatewaylist":
                self.setHeader('Content-Type', 'text/html')
                self.write(self.html)
            #The dynamic ajaxy status stuff.
            elif self.path == "/routerstatus":
                clientip=self.getClientIP()
                serverip=self.getHost().host
                self.setHeader('Content-Type', 'application/json')
                self.write(self.state(serverip,clientip))
            #Changing the current gateway for a given client ip.
            elif self.path == "/setgateway":
                self.setHeader('Content-Type', 'text/html')
                clientip=self.getClientIP()
                gatewaynum = int(self.args["gw"][0])
                self.dbusclient.setGateway(clientip,gatewaynum,self.state,self.getHost().host)
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
        syslog.syslog(syslog.LOG_ERR,"DEBUG: http request handled.")        


class DynamicRouterHttp(http.HTTPChannel):
    requestFactory = DynamicRouterRequestHandler
    def __init__(self,html,state,dbusclient):
        http.HTTPChannel.__init__(self)
        self.html=html
        self.state=state
        self.dbusclient=dbusclient
        http.HTTPChannel.__init__(self)
    def requestFactory(self, *args):
        return DynamicRouterRequestHandler(self.html,self.state,self.dbusclient, *args)
    
        

class DynamicRouterHttpFactory(http.HTTPFactory):
    protocol = DynamicRouterHttp
    def __init__(self,conf,ip,dbusclient,state,htmltemplate):
        self.ip=ip
        self.state=state
        self.dbusclient=dbusclient
        gwlist=conf.getGatewayList(ip)
        self.html=str(htmltemplate.render({"gateway_list" : gwlist}))
        http.HTTPFactory.__init__(self)
    def buildProtocol(self, addr):
        return DynamicRouterHttp(self.html,self.state,self.dbusclient)
        
if os.system("/usr/bin/pbr-checkconfig.py"):
    exit(1)
syslog.openlog("dynr-web.py")
syslog.syslog(syslog.LOG_NOTICE,"pbdns-web started")
#with daemon.DaemonContext():
if True:
    DBusGMainLoop(set_as_default=True)
    syslog.openlog("dynr-web.py")
    syslog.syslog(syslog.LOG_NOTICE,'Running as daemon')
    try:
        conf=DynamicRouterConfig("/etc/pbrouting.json")
    except:
        syslog.syslog(syslog.LOG_CRIT,"Problem loading config /etc/pbrouting.json: aborting.")
        exit(1)
    try:
        dbusclient=DbusClient(conf.getGatewaysMap(),conf.getParkIp())
    except:
        syslog.syslog(syslog.LOG_CRIT,"Problem binding to dbus: aborting.")
        exit(1)
    try:
        state=DynamicRouterState(conf)
    except:
        syslog.syslog(syslog.LOG_CRIT,"Problem constructing DynamicRouterState. Aborting.")
        exit(1)
    try:
        htmltemplate=jinja2.Environment(loader=jinja2.FileSystemLoader("/var/dynr-web/templates",encoding='utf-8')).get_template('index.tmpl')
    except jinja2.exceptions.TemplateNotFound:
        syslog.syslog(syslog.LOG_CRIT,"/var/dynr-web/templates/index.tmpl not found! : Aborting.")
        exit(1)
    for clientip in conf.clientips():
        try:
            reactor.listenTCP(80,DynamicRouterHttpFactory(conf,clientip,dbusclient,state,htmltemplate),10,clientip)
        except:
            syslog.syslog(syslog.LOG_CRIT,"Unable to bind to webserver port 80 on "+str(clientip))
            exit(1)
        syslog.syslog(syslog.LOG_CRIT,"Starting to listen on IP "+str(clientip))
    try:
        syslog.syslog(syslog.LOG_CRIT,"Starting twisted reactor.")
        reactor.run()
    except:
        syslog.syslog(syslog.LOG_CRIT,"Problem running twisted reactor. Aborting.")
        exit(1)
