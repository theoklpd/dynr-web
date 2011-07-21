//The gridViewApp function takes browser globals as invocation dependencies so we can
//have accidental globals stick out in jslint.
function gridViewApp(doc, win, settimeout, cleartimeout, newimg, newreq) {
    'use strict';
    //The gridview object makes up most of our simple application.
    var gridview = {
        "gateways" : [],
        "receiveReq" : newreq(),
        "receiveReq2" : newreq(),
        "myTimer" : "",
        "reqseq" : 0,
        //This method draws a canvas according to its current gateway state.
        "displayGatewayState" : function (gateway) {
            var canvasname = "canvas" + gateway.number,
                canvas = doc.getElementById(canvasname),
                context = canvas.getContext("2d"),
                outercollor = "#aaaaaa",
                peerscolor = "#bbbbbb",
                fillcolor = "#cccccc",
                img = newimg(),
                img2 = newimg();
            //The selected gateway gets a blue outer border rather than the default grey (window collor) outer border.
            if (gateway.selected === true) {
                outercollor = "#2e2efe";
            }
            context.fillStyle = outercollor;
            context.fillRect(0, 0, gateway.celsize, gateway.celsize);
            //The inner border color is determined by the types of people that are using the gateway, and by
            //the fact that we may use this gateway. Gateways we can't select will have a light gray outer border.
            //Gateways that we can use that have no active users also have a light gray outer border.
            if (gateway.groupaccess === true) {
                if (gateway.groupcount > 0) {
                    //If there are only users of our group that currently use this gateway, the inner border is yellow.
                    peerscolor = "#ffff00";
                    if (gateway.othercount > 0) {
                        //If currenly this gateway has users of both our group and of other groups, the inner border is orange (yellow + redish)
                        peerscolor = "#fe9a2e";
                    } else {
                        if ((gateway.groupcount === 1) && (gateway.selected === true)) {
                            //If we are the only one who selected this gateway, the inner border is light blue.
                            peerscolor = "#58daf5";
                        }
                    }
                } else {
                    if (gateway.othercount > 0) {
                        //If the gateway currenly has only users from other groups, the inner border is redish.
                        peerscolor = "#ff8080";
                    }
                }
            }
            context.fillStyle = peerscolor;
            context.fillRect(5, 5, gateway.celsize - 10, gateway.celsize - 10);
            //Any gateway that can't be selected has a grey fill collor.
            if (gateway.groupaccess === true) {
                if (gateway.otheraccess === true) {
                    //If we share access to this gateway with other groups, than the fill collor is pink.
                    fillcolor = "#f6cef6";
                } else {
                    //If this gateway is for our group exclusively, the fill collor id green.
                    fillcolor = "#a9f5a9";
                }
            }
            context.fillStyle = fillcolor;
            context.fillRect(10, 10, gateway.celsize - 20, gateway.celsize - 20);
            //Gateway names are written in black for gateways we can pick, and in grey for gateways we can't pick.
            context.fillStyle = "#aaaaaa";
            if (gateway.groupaccess === true) {
                context.fillStyle = "#000000";
            }
            context.font = "bold 16px sans-serif";
            context.fillText(gateway.name, 15, 26);
            //Only for gateways we can pick will we show the icon.
            if (gateway.groupaccess === true) {
                img.src = gateway.image;
                context.drawImage(img, 15, 15, gateway.celsize - 30, gateway.celsize - 30);
            }
            //For gateways with people from our group on it, display the number of users from our group in large green numbers.
            if (gateway.groupcount > 0) {
                context.fillStyle = "green";
                context.font = "bold 70px sans-serif";
                if (gateway.groupcount > 9) {
                    context.fillText(gateway.groupcount, gateway.celsize - 100, gateway.celsize - 15);
                } else {
                    context.fillText(gateway.groupcount, gateway.celsize - 60, gateway.celsize - 15);
                }
            }
            //For gateways with people from other groups on it, display the number of users from this group that are currently on it.
            //If we are allowed to pick this line, using red numbers, otherwise in grey numbers. These numbers are a bit smaller than
            //those for indicating people from our own group.
            context.fillStyle = "#aaaaaa";
            if (gateway.othercount > 0) {
                if (gateway.groupaccess === true) {
                    context.fillStyle = "red";
                }
                context.font = "bold 40px sans-serif";
                context.fillText(gateway.othercount, 15, gateway.celsize - 15);
            }
            //If the state of the gateway has been marked as waiting for a new status, display an hourglass with this gateway.
            if (gateway.waiting === true) {
                if (gateway.groupaccess === true) {
                    img2.src = "wait.png";
                    context.drawImage(img2, gateway.celsize - 50, gateway.celsize -  50, 30, 50);
                }
            }
        },
        //This is the AJAJ response handler for the status info request.
        "handleGatewaysStatus" : function () {
            var response,
                i,
                gatewaystatus,
                gatewaynum,
                gateway,
                updated = false,
                gv = this;
            if (this.receiveReq.readyState === 4) {
                response = JSON.parse(this.receiveReq.responseText); //Our response should be a json doc containing an array of gateway statusses.
                //Loop over the statusses for all gateways.
                for (i = 0; i < response.length; i = i + 1) {
                    gatewaystatus = response[i]; //The most recent gateway state
                    gatewaynum = gatewaystatus.id;
                    gateway = this.gateways[gatewaynum - 1]; //The remembered state
                    updated = false;
                    //Update our remembered status, setting the 'updated' flag if appropriate.
                    if (gatewaystatus.selected !== gateway.selected) {
                        gateway.selected = gatewaystatus.selected;
                        updated = true;
                    }
                    if (gatewaystatus.groupcount !== gateway.groupcount) {
                        gateway.groupcount = gatewaystatus.groupcount;
                        updated = true;
                    }
                    if (gatewaystatus.othercount !== gateway.othercount) {
                        gateway.othercount = gatewaystatus.othercount;
                        updated = true;
                    }
                    if (gateway.waiting === true) {
                        gateway.waiting = false;
                        updated = true;
                    }
                    //If anything has changed for this gateway, than we should redraw it appropriately. 
                    if (updated === true) {
                        this.displayGatewayState(this.gateways[gatewaynum - 1]);
                    }
                }
                this.myTimer = settimeout(function () {gv.getGatewaysStatus(); }, 2000);
            }
        },
        //Ask the server for its status using an AJAJ request.
        "getGatewaysStatus" : function () {
            var gv = this;
            if (this.receiveReq.readyState === 4 || this.receiveReq.readyState === 0) {
                this.reqseq = this.reqseq + 1; //Add a sequence number to avoid caching. This is lame, whats up with this?
                this.receiveReq.open("GET", '/status?' + this.reqseq, true);
                this.receiveReq.onreadystatechange = function () {gv.handleGatewaysStatus(); }; //Set a callback for the response.
                this.receiveReq.send(null);
            }
        },
        //Gets invoked once our request for updating has been transfered to the server.
        "handleUpdateDone" : function () {
            var gv = this;
            if (this.receiveReq2.readyState === 4) {
                //In two seconds we shall ask the server for its status, update should be done by than.
                this.myTimer = settimeout(function () {gv.getGatewaysStatus(); }, 2000);
            }
        },
        //This method gets called when a canvas is pressed. It will ask the dynamic router
        //to change its gateway to that with the given gateway number.
        "selectGateway" : function (i) {
            var gv = this;
            //Wait with new timer events untill we did our request to the server.
            cleartimeout(this.myTimer);
            this.gateways[i - 1].waiting = true; //Set the status of this gateway to 'waiting' untill our next update of the status.
            this.displayGatewayState(this.gateways[i - 1]); //Display our gateway as waiting (with the litle ourglass).
            if (this.receiveReq2.readyState === 4 || this.receiveReq2.readyState === 0) {
                this.receiveReq2.open("PUT", '/set?gw=' + i, true); //Create a new AJAJ request for updating our gateway on the server.
                this.receiveReq2.onreadystatechange = function () { gv.handleUpdateDone(); }; //Bind receiving the response ti our handleUpdateDone method.
                this.receiveReq2.send(null);
            }
        },
        //Append a new canvas with id i of a given size s and place it at the coordinates x,y.
        "addCanvas" : function (x, y, s, i) {
            var newdiv = doc.createElement('div'),
                style = "position: absolute; top: " + y + "px; left: " + x + "px;",
                divid = "div" + i,
                newcanvas = doc.createElement('canvas'),
                canvasid = "canvas" + i,
                gv = this;
            newdiv.setAttribute('style', style);
            newdiv.setAttribute('id', divid);
            canvasid = "canvas" + i;
            newcanvas.setAttribute('id', canvasid);
            newcanvas.setAttribute('width', s);
            newcanvas.setAttribute('height', s);
            newdiv.appendChild(newcanvas);
            doc.getElementById('docbody').appendChild(newdiv);
            newcanvas.addEventListener("click", function () {gv.selectGateway(i); }, false);
        },
        //Update the location and size of a given canvas at index i.
        "updateCanvas" : function (x, y, s, i) {
            var divid = "div" + i,
                style = "position: absolute; top: " + y + "px; left: " + x + "px;", //The position.
                canvasdiv = doc.getElementById(divid),
                canvasid = "canvas" + i,
                thecanvas = doc.getElementById(canvasid);
            canvasdiv.setAttribute('style', style);
            thecanvas.setAttribute('width', s); 
            thecanvas.setAttribute('height', s);
        },
        //This method returns the maximum number of cells of a given size into our browser window.
        "maxCells" : function (xrange, yrange, celsize) {
            var xcels = Math.floor(xrange / celsize),
                ycels = Math.floor(yrange / celsize),
                rval =  xcels * ycels;
            return rval;
        },
        //The celsize is the maximum square size that allows us to fit 'cels' cels into our browser window.
        "getCellSize" : function (cels) {
            var xrange = win.innerWidth,
                yrange = win.innerHeight,
                celsize = Math.floor(Math.sqrt(xrange * yrange / cels)); //Upper bound for the celsize, this is unlikely to fit.
            while (celsize > 84) { //If things get to small we won't be able to display all info, lets set a lower bound for celsize.
                //Test if the proposed celsize will allow us to fit all cels into our browser window.
                if (this.maxCells(xrange, yrange, celsize) >= cels) {
                    return celsize - 4; //If it does, lets give back something a bit smaller so we get nice margins.
                }
                //decrement the proposed celsize and try again if it fits.
                celsize = celsize - 1;
            }
            return 80;
        },
        //The number of columns is detemined by the number of cells of celsize that fit into our browswe windows horizontally.
        "getColCount" : function (celsize) {
            var xrange = win.innerWidth;
            return Math.floor(xrange / celsize);
        },
        //The number of rows is determined from the total number of cells and the number of columns.
        "getRowCount" : function (cels, colcount) {
            return Math.ceil(cels / colcount);
        },
        //Initialize our browser windof for the first time.
        "initScreen" : function () {
            var cels = this.gateways.length,
                celsize = this.getCellSize(cels), //Get the max celsize that fits our window.
                colcount = this.getColCount(celsize), //Get the number of columns we should use.
                rowcount = this.getRowCount(cels, colcount), //Get the number of rows we should use.
                //Try to somewhat center our matrix on our page
                xoffset = Math.floor((win.innerWidth - (celsize * colcount)) / 2),
                yoffset = Math.floor((win.innerHeight - (celsize * rowcount)) / 2),
                row = 0,
                canvasno = 0,
                col = 0;
            //Determine the proper cell for each existing canvas.
            for (row = 0; row < rowcount; row = row + 1) {
                for (col = 0; col < colcount; col = col + 1) {
                    canvasno = canvasno + 1;
                    if (canvasno <= cels) {
                        //Create a new canvas of the proper size and place it at the right location on the screen.
                        this.addCanvas(col * celsize + xoffset, row * celsize + yoffset, celsize, canvasno);
                        //Display the proper info in our new canvas.
                        this.displayGatewayState(this.gateways[canvasno - 1]);
                    }
                }
            }
            return celsize;
        },
        //This method parses the 'nojs' div section in the original dom tree.
        "parseNoJsSection" : function (nojsdiv) {
            var images = nojsdiv.getElementsByTagName('img'), //get all image tags, each image represents a single gateway.
                celsize = this.getCellSize(images.length - 1), //Get the max celsize that fits our window.
                gatewayno = 0,
                image,
                gatewayobj,
                i;
            //Fill our gateways array with initial data from the 'nojs' image tags.
            for (i = 1; i < images.length; i = i + 1) {
                gatewayno = gatewayno + 1;
                image = images[i];
                //create a gateway object.
                gatewayobj = {
                    "number" : gatewayno,
                    "selected" : false,
                    "name" : "Uninitialized",
                    "groupaccess" : false,
                    "otheraccess" : false,
                    "groupcount" : 0,
                    "othercount" : 0,
                    "celsize" : celsize,
                    "waiting" : true,
                    "image"  : "bogus.png"
                };
                //Copy the piggybacked gateway info from the image tag.
                gatewayobj.name = images[i].getAttribute('name');
                gatewayobj.image = images[i].getAttribute('src');
                if (images[i].getAttribute('groupaccess') === 'true') {
                    gatewayobj.groupaccess = true;
                }
                if (images[i].getAttribute('otheraccess') === 'true') {
                    gatewayobj.otheraccess = true;
                }
                //Add the new gateway to our gateways array.
                this.gateways.push(gatewayobj);
            }
            return;
        },
        //This method gets called when the browser window gets resized by the user.
        //Its a lot like initScreen, but the difs and canvasses already exist, we only need to rescale and reposition them.
        "updateScreen" : function () {
            var cels = this.gateways.length,
                celsize = this.getCellSize(cels), //Get the max celsize that fits our window.
                colcount = this.getColCount(celsize), //Get the number of columns we should use.
                rowcount = this.getRowCount(cels, colcount), //Get the number of rows we should use.
                //Try to somewhat center our matrix on our page.
                xoffset = Math.floor((win.innerWidth - (celsize * colcount)) / 2),
                yoffset = Math.floor((win.innerHeight - (celsize * rowcount)) / 2),
                row = 0,
                col = 0,
                canvasno = 0;
            //Determine the proper cell for each existing canvas.
            for (row = 0; row < rowcount; row = row + 1) {
                for (col = 0; col < colcount; col = col + 1) {
                    canvasno = canvasno + 1;
                    if (canvasno <= cels) {
                        //Update our canvas celsize in our gateways array.
                        this.gateways[canvasno - 1].celsize = celsize;
                        //Move our canvas to the right place.
                        this.updateCanvas(col * celsize + xoffset, row * celsize + yoffset, celsize, canvasno);
                        //Redraw everything on our moved and resized canvas.
                        this.displayGatewayState(this.gateways[canvasno - 1]);
                    }
                }
            }
            return;
        },
        //Method called once at the start of the application.
        "onload" : function () {
            //The initial html has a 'nojs' div (filled with img tags) that we should replace.
            var nojsdiv = doc.getElementById('nojs');
            //Parse the 'nojs' section and its img tags to initialize the gateways array.
            this.parseNoJsSection(nojsdiv);
            //Initialize our browser window for the first time creating and scaling divs and canvasses to fit all our gateways.
            this.initScreen();
            //Remove the parsed 'nojs' from the dom tree.
            doc.getElementById('docbody').removeChild(nojsdiv);
            //Start off with an unset timer.
            cleartimeout(this.myTimer);
            //Go and do an AJAJ request to the server for our gateways status.
            this.getGatewaysStatus();
        }
    };
    //gridview created, now lets bind it to the proper window events.
    win.onload = function () {
        gridview.onload();
    };
    win.onresize = function () {
        gridview.updateScreen();
    };
}

gridViewApp(document, window, setTimeout, clearTimeout, function () {return new Image();}, function () {return new XMLHttpRequest();}  );

