//FIXME: put these in a single global object.

var gateways=[];
var sendReq = new XMLHttpRequest();
var receiveReq = new XMLHttpRequest();
var lastMessage = 0;
var myTimer;

function displayGatewayState(gateway) {
  var name=gateway.name;
  var num=gateway.number;
  var groupaccess=gateway.groupaccess;
  var otheraccess=gateway.otheraccess;
  var selected=gateway.selected;
  var groupcount=gateway.groupcount;
  var nongroupcount=gateway.othercount;
  var celsize=gateway.celsize;
  var waiting=gateway.waiting;
  var image=gateway.image;
  var canvasname="canvas" + num;
  var canvas=document.getElementById(canvasname);
  var context=canvas.getContext("2d");
  var outercollor="#aaaaaa";
  if (selected === true) {
     outercollor="#2e2efe";
  }
  context.fillStyle =outercollor;
  context.fillRect(0,0,celsize,celsize);
  peerscolor="#bbbbbb";
  if (groupaccess === true ) {
    if (groupcount > 0) {
       peerscolor="#ffff00";
       if (nongroupcount > 0) {
        peerscolor="#fe9a2e";
       } else {
         if ((groupcount === 1) && (selected == true)) {
          peerscolor="#58daf5";
         }
       }
    } else {
       if (nongroupcount > 0) {
         peerscolor="#ff8080";
       }
    }
  }
  context.fillStyle=peerscolor;
  context.fillRect(5,5,celsize-10,celsize-10);
  var fillcolor="#cccccc";
  if (groupaccess === true ) {
    if (otheraccess === true ) {
      fillcolor="#f6cef6";
    } else {
      fillcolor="#a9f5a9";
    }
  }
  context.fillStyle=fillcolor;
  context.fillRect(10,10,celsize-20,celsize-20);
  context.fillStyle="#aaaaaa";
  if (groupaccess === true ) {
    context.fillStyle="#000000";
  }
  context.font = "bold 16px sans-serif";
  context.fillText(name,15,26);
  context.fillStyle="#aaaaaa";
  if (groupaccess === true) {
    var img=new Image();
    img.src=image;
    context.drawImage(img,15,15,celsize -30,celsize -30);
  }
  if ((groupaccess === true)&&(groupcount > 0)) {
    context.fillStyle="green";
    context.font = "bold 70px sans-serif";
    if (groupcount > 9) {
       context.fillText(groupcount,celsize - 100,celsize-15);
    } else {
       context.fillText(groupcount,celsize - 60,celsize-15);
    }
  }

  if ((otheraccess === true)&&(nongroupcount > 0)) {
    if (groupaccess === true ) {
      context.fillStyle="red";
    }
    context.font = "bold 40px sans-serif";
    context.fillText(nongroupcount,15,celsize-15);
  }
  if (waiting === true) {
    if (groupaccess === true ) {
       var img2=new Image();
       img2.src="wait.png";
       context.drawImage(img2,celsize-50,celsize-50,30,50);
    }
  }
}

function handleUpdateDone() {
   if (receiveReq.readyState == 4) {
      myTimer = setTimeout('getGatewaysStatus();',2000);
   }   
}

function selectGateway(i) {
  clearTimeout(myTimer);
  gateways[i-1].waiting=true;
  displayGatewayState(gateways[i-1]);
  if (receiveReq.readyState == 4 || receiveReq.readyState == 0) {
                receiveReq.open("PUT", '/set?gw=' + i , true);
                receiveReq.onreadystatechange = handleUpdateDone;
                receiveReq.send(null);
  }
}

function addCanvas(x,y,s,i) {
  var newdiv = document.createElement('div');
  var style="position: absolute; top: " + y + "px; left: " + x +"px;";
  newdiv.setAttribute('style',style);
  divid="div" + i;
  newdiv.setAttribute('id',divid);
  newcanvas=document.createElement('canvas');
  canvasid="canvas" + i;
  newcanvas.setAttribute('id',canvasid);
  newcanvas.setAttribute('width',s);
  newcanvas.setAttribute('height',s);
  newdiv.appendChild(newcanvas);
  document.getElementById('docbody').appendChild(newdiv);
  newcanvas.addEventListener("click", function() {selectGateway(i);}, false);
}

function updateCanvas(x,y,s,i) {
  divid="div" + i;
  canvasdiv=document.getElementById(divid);
  var style="position: absolute; top: " + y + "px; left: " + x +"px;";
  canvasdiv.setAttribute('style',style);
  canvasid="canvas" + i;
  thecanvas=document.getElementById(canvasid);
  thecanvas.setAttribute('width',s);
  thecanvas.setAttribute('height',s);
  
}


function maxCells(xrange,yrange,celsize) {
  xcels=Math.floor(xrange/celsize);
  ycels=Math.floor(yrange/celsize);
  var rval= xcels * ycels;
  return rval;
}

function getCellSize(cels) {
  var xrange=window.innerWidth;
  var yrange=window.innerHeight;
  var celsize=Math.floor(Math.sqrt(xrange*yrange/cels));
  while (celsize > 80) {
     if (maxCells(xrange,yrange,celsize) >= cels) {
       return celsize - 4;
     }
     celsize = celsize -1;
  }
  return 80;
}

function getColCount(celsize) {
  var xrange=window.innerWidth;
  return Math.floor(xrange / celsize);
}

function getRowCount(cels,colcount) {
  return Math.ceil(cels/colcount);
}

function initScreen(gateways) {
  var cels=gateways.length;
  var celsize=getCellSize(cels);
  var colcount = getColCount(celsize);
  var rowcount = getRowCount(cels,colcount);
  var xoffset = Math.floor((window.innerWidth - (celsize * colcount))/2);
  var yoffset = Math.floor((window.innerHeight - (celsize * rowcount))/2);
  var row=0; 
  var canvasno=0;
  for (row=0;row<rowcount;row++) { 
    var col=0;
    for (col=0;col<colcount;col++) {
      canvasno++;
      if (canvasno <= cels) {
        addCanvas(col*celsize+xoffset,row*celsize+yoffset,celsize,canvasno);
        displayGatewayState(gateways[canvasno-1]);
      }
    }
  } 
  return celsize; 
}

function updateScreen(gateways) {
  var cels=gateways.length;
  var celsize=getCellSize(cels);
  var colcount = getColCount(celsize);
  var rowcount = getRowCount(cels,colcount);
  var xoffset = Math.floor((window.innerWidth - (celsize * colcount))/2);
  var yoffset = Math.floor((window.innerHeight - (celsize * rowcount))/2);
  var row=0;
  var canvasno=0;
  for (row=0;row<rowcount;row++) {
    var col=0;
    for (col=0;col<colcount;col++) {
      canvasno++;
      if (canvasno <= cels) {
        gateways[canvasno-1].celsize=celsize;
        updateCanvas(col*celsize+xoffset,row*celsize+yoffset,celsize,canvasno);
        displayGatewayState(gateways[canvasno-1]);
      }
    }
  }
  return celsize;
}

function parseNoJsSection(nojsdiv) {
  var gateways = [];
  var images = nojsdiv.getElementsByTagName('img');
  var celsize=getCellSize(images.length-1);
  var gatewayno=0;
  for (var i = 1; i < images.length; i++){
    gatewayno++;
    var image=images[i];
    var gatewayobj = {
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
    }
    gatewayobj.name=images[i].getAttribute('name'),
    gatewayobj.image=images[i].getAttribute('src');
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

function handleGatewaysStatus() {
	if (receiveReq.readyState == 4) {
		var response = eval("(" + receiveReq.responseText + ")");
                var somethingchanged=false;
		for(i=0;i < response.length; i++) {
                  gatewaystatus=response[i];
                  gatewaynum=gatewaystatus.id;
                  gateway=gateways[gatewaynum-1];
                  var updated=false;
                  if (gatewaystatus.selected != gateway.selected) {
                     gateway.selected = gatewaystatus.selected;
                     updated=true;
                  }
                  if (gatewaystatus.groupcount != gateway.groupcount) {
                     gateway.groupcount=gatewaystatus.groupcount;
                     updated=true;
                  }
                  if (gatewaystatus.othercount != gateway.othercount) {
                     gateway.othercount = gatewaystatus.othercount;
                     updated=true;
                  }
                  if (gateway.waiting == true) {
                     gateway.waiting = false;
                     updated=true;
                  }
                  if (updated == true) {
                    somethingchanged=true;
                    displayGatewayState(gateways[gatewaynum-1]);
                  }
		}
		myTimer = setTimeout('getGatewaysStatus();',2000);
	}
}

function getGatewaysStatus() {
	if (receiveReq.readyState == 4 || receiveReq.readyState == 0) {
		receiveReq.open("GET", '/status', true);
		receiveReq.onreadystatechange = handleGatewaysStatus; 
		receiveReq.send(null);
	}			
} 

window.onload = function() {
  var nojsdiv=document.getElementById('nojs');
  gateways=parseNoJsSection(nojsdiv);
  initScreen(gateways);
  document.getElementById('docbody').removeChild(nojsdiv);
  clearTimeout(myTimer);
  getGatewaysStatus();
}

window.onresize = function() {
    updateScreen(gateways);
}

