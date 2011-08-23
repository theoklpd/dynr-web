#!/usr/bin/python
from twisted.web import http
from twisted.internet import reactor
from twisted.web.static import File
import os
import json
import sys
import jinja2

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

class DynamicRouterState: #TODO
    def __init__(self):
        self.info={}
    def __call__(self):
        print "DynamicRouterState invoked"
        return ""

class DbusClient: #TODO
    def __init__(self):
        self.info={}
    def setGateway(self,clientip,gatewaynum,state):
        print "DbusClient::setGateway(" + str(clientip) + "," + str(gatewaynum) + ",state)  invoked"

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
                clientip=self.getClientIP()
                gatewaynum = self.args["gw"][0];
                self.dbusclient.setGateway(clientip,gatewaynum,self.state)
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
dbusclient=DbusClient()
state=DynamicRouterState()
try:
    template=jinja2.Environment(loader=jinja2.FileSystemLoader("/var/dynr-web/templates",encoding='utf-8')).get_template('index.tmpl')
except jinja2.exceptions.TemplateNotFound:
    print "ERROR: /var/dynr-web/templates/index.tmpl not found!"
    exit(1)
for clientip in conf.clientips():
    reactor.listenTCP(8765,DynamicRouterHttpFactory(conf,clientip,dbusclient,state,template),10,clientip)
reactor.run()
