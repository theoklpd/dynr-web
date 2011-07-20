var gateways = [];
var receiveReq = new XMLHttpRequest();
var receiveReq2 = new XMLHttpRequest();
var myTimer;
var reqseq=0;
function displayGatewayState(gateway) {
    'use strict';
    var name = gateway.name,
        num = gateway.number,
        groupaccess = gateway.groupaccess,
        otheraccess = gateway.otheraccess,
        selected = gateway.selected,
        groupcount = gateway.groupcount,
        nongroupcount = gateway.othercount,
        celsize = gateway.celsize,
        waiting = gateway.waiting,
        image = gateway.image,
        canvasname = "canvas" + num,
        canvas = document.getElementById(canvasname),
        context = canvas.getContext("2d"),
        outercollor = "#aaaaaa",
        peerscolor = "#bbbbbb",
        fillcolor = "#cccccc",
        img = new Image(),
        img2 = new Image();
    if (selected === true) {
        outercollor = "#2e2efe";
    }
    context.fillStyle = outercollor;
    context.fillRect(0, 0, celsize, celsize);
    if (groupaccess === true) {
        if (groupcount > 0) {
            peerscolor = "#ffff00";
            if (nongroupcount > 0) {
                peerscolor = "#fe9a2e";
            } else {
                if ((groupcount === 1) && (selected === true)) {
                    peerscolor = "#58daf5";
                }
            }
        } else {
            if (nongroupcount > 0) {
                peerscolor = "#ff8080";
            }
        }
    }
    context.fillStyle = peerscolor;
    context.fillRect(5, 5, celsize - 10, celsize - 10);
    if (groupaccess === true) {
        if (otheraccess === true) {
            fillcolor = "#f6cef6";
        } else {
            fillcolor = "#a9f5a9";
        }
    }
    context.fillStyle = fillcolor;
    context.fillRect(10, 10, celsize - 20, celsize - 20);
    context.fillStyle = "#aaaaaa";
    if (groupaccess === true) {
        context.fillStyle = "#000000";
    }
    context.font = "bold 16px sans-serif";
    context.fillText(name, 15, 26);
    context.fillStyle = "#aaaaaa";
    if (groupaccess === true) {
        img.src = image;
        context.drawImage(img, 15, 15, celsize - 30, celsize - 30);
    }
    if ((groupaccess === true) && (groupcount > 0)) {
        context.fillStyle = "green";
        context.font = "bold 70px sans-serif";
        if (groupcount > 9) {
            context.fillText(groupcount, celsize - 100, celsize - 15);
        } else {
            context.fillText(groupcount, celsize - 60, celsize - 15);
        }
    }
    if ((otheraccess === true)  &&  (nongroupcount > 0)) {
        if (groupaccess === true) {
            context.fillStyle = "red";
        }
        context.font = "bold 40px sans-serif";
        context.fillText(nongroupcount, 15, celsize - 15);
    }
    if (waiting === true) {
        if (groupaccess === true) {
            img2.src = "wait.png";
            context.drawImage(img2, celsize - 50, celsize -  50, 30, 50);
        }
    }
}

function handleGatewaysStatus() {
    'use strict';
    var somethingchanged = false,
        response,
        i,
        gatewaystatus,
        gatewaynum,
        gateway,
        updated = false;
    if (receiveReq.readyState === 4) { 
        response = eval("(" + receiveReq.responseText + ")");
        for (i = 0; i < response.length; i = i + 1) { 
            gatewaystatus = response[i]; 
            gatewaynum = gatewaystatus.id; 
            gateway = gateways[gatewaynum - 1];
            updated = false;
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
            if (updated === true) {
                somethingchanged = true;
                displayGatewayState(gateways[gatewaynum - 1]);
            }
        }
        myTimer = setTimeout(getGatewaysStatus, 2000);
    }
}

function getGatewaysStatus() {
    'use strict';
    if (receiveReq.readyState === 4 || receiveReq.readyState === 0) {
        reqseq = reqseq + 1;
        receiveReq.open("GET", '/status?' + reqseq , true);
        receiveReq.onreadystatechange = handleGatewaysStatus;
        receiveReq.send(null);
    }
}

function handleUpdateDone() {
    'use strict';
    if (receiveReq2.readyState === 4) {
        myTimer = setTimeout(getGatewaysStatus, 2000);
    }
}

function selectGateway(i) {
    'use strict';
    clearTimeout(myTimer);
    gateways[i - 1].waiting = true;
    displayGatewayState(gateways[i - 1]);
    if (receiveReq2.readyState === 4 || receiveReq2.readyState === 0) {
        receiveReq2.open("PUT", '/set?gw=' + i, true);
        receiveReq2.onreadystatechange = handleUpdateDone;
        receiveReq2.send(null);
    }
}

function addCanvas(x, y, s, i) { 
    'use strict';
    var newdiv = document.createElement('div'),
        style = "position: absolute; top: " + y + "px; left: " + x + "px;",
        divid = "div" + i,
        newcanvas = document.createElement('canvas'),
        canvasid = "canvas" + i;
    newdiv.setAttribute('style', style);
    newdiv.setAttribute('id', divid);
    canvasid = "canvas" + i;
    newcanvas.setAttribute('id', canvasid);
    newcanvas.setAttribute('width', s);
    newcanvas.setAttribute('height', s);
    newdiv.appendChild(newcanvas);
    document.getElementById('docbody').appendChild(newdiv);
    newcanvas.addEventListener("click", function () {selectGateway(i); }, false);
}

function updateCanvas(x, y, s, i) {
    'use strict';
    var divid = "div" + i, 
        style = "position: absolute; top: " + y + "px; left: " + x + "px;",
        canvasdiv = document.getElementById(divid),
        canvasid = "canvas" + i,
        thecanvas = document.getElementById(canvasid);
    canvasdiv.setAttribute('style', style);
    thecanvas.setAttribute('width', s);
    thecanvas.setAttribute('height', s);
}


function maxCells(xrange, yrange, celsize) {
    'use strict';
    var xcels = Math.floor(xrange / celsize),
        ycels = Math.floor(yrange / celsize),
        rval =  xcels * ycels;
    return rval;
}

function getCellSize(cels) {
    'use strict'; //200
    var xrange = window.innerWidth,
        yrange = window.innerHeight,
        celsize = Math.floor(Math.sqrt(xrange * yrange / cels));
    while (celsize > 80) {
        if (maxCells(xrange, yrange, celsize) >= cels) {
            return celsize - 4;
        }
        celsize = celsize - 1;
    }
    return 80;
}

function getColCount(celsize) {
    'use strict';
    var xrange = window.innerWidth;
    return Math.floor(xrange / celsize);
}

function getRowCount(cels, colcount) {
    'use strict';
    return Math.ceil(cels / colcount);
}


function initScreen(gateways) {
    'use strict';
    var cels = gateways.length,
        celsize = getCellSize(cels),
        colcount = getColCount(celsize),
        rowcount = getRowCount(cels, colcount),
        xoffset = Math.floor((window.innerWidth - (celsize * colcount)) / 2),
        yoffset = Math.floor((window.innerHeight - (celsize * rowcount)) / 2),
        row = 0,
        canvasno = 0,
        col = 0;
    for (row = 0; row < rowcount; row = row + 1) {
        for (col = 0; col < colcount; col = col + 1) {
            canvasno = canvasno + 1;
            if (canvasno <= cels) {
                addCanvas(col * celsize + xoffset, row * celsize + yoffset, celsize, canvasno);
                displayGatewayState(gateways[canvasno - 1]);
            }
        }
    }
    return celsize;
}

function updateScreen(gateways) {
    'use strict';
    var cels = gateways.length,
        celsize = getCellSize(cels),
        colcount = getColCount(celsize),
        rowcount = getRowCount(cels, colcount),
        xoffset = Math.floor((window.innerWidth - (celsize * colcount)) / 2),
        yoffset = Math.floor((window.innerHeight - (celsize * rowcount)) / 2),
        row = 0,
        col = 0,
        canvasno = 0;
    for (row = 0; row < rowcount; row = row + 1) {
        for (col = 0; col < colcount; col = col + 1) {
            canvasno = canvasno + 1;
            if (canvasno <= cels) {
                gateways[canvasno - 1].celsize = celsize;
                updateCanvas(col * celsize + xoffset, row * celsize + yoffset, celsize, canvasno);
                displayGatewayState(gateways[canvasno - 1]);
            }
        }
    }
    return celsize;
}

function parseNoJsSection(nojsdiv) {
    'use strict';
    var images = nojsdiv.getElementsByTagName('img'),
        celsize = getCellSize(images.length - 1),
        gatewayno = 0,
        image,
        gatewayobj,
        i;
    for (i = 1; i < images.length; i = i + 1) {
        gatewayno = gatewayno + 1;
        image = images[i];
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
        gatewayobj.name = images[i].getAttribute('name');
        gatewayobj.image = images[i].getAttribute('src');
        if (images[i].getAttribute('groupaccess') === 'true') {
            gatewayobj.groupaccess = true;
        }
        if (images[i].getAttribute('otheraccess') === 'true') {
            gatewayobj.otheraccess = true;
        }
        gateways.push(gatewayobj);
    }
    return gateways;
}

window.onload = function () {
    'use strict';
    var nojsdiv = document.getElementById('nojs');
    gateways = parseNoJsSection(nojsdiv);
    initScreen(gateways);
    document.getElementById('docbody').removeChild(nojsdiv);
    clearTimeout(myTimer);
    getGatewaysStatus();
};

window.onresize = function () {
    'use strict';
    updateScreen(gateways);
};



