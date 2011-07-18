function displayGatewayState(name,num,groupaccess,otheraccess,selected,groupcount,nongroupcount,celsize) {
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
    img.src="router.png";
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

function getRowCount(celsize) {
  var yrange=window.innerHeight;
  return Math.floor(yrange/celsize);
}

function getColCount(celsize) {
  var xrange=window.innerWidth;
  return Math.floor(xrange / celsize);
}

function initScreen(cels) {
  var celsize=getCellSize(cels);
  var rowcount = getRowCount(celsize);
  var colcount = getColCount(celsize);
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
        displayGatewayState(name="undef",num=canvasno,groupaccess=false,otheraccess=false,selected=false,groupcount=0,othercount=0,celsize);
      }
    }
  } 
  return celsize; 
}

window.onload = function() {
  var canvascount=document.getElementById('docbody').getAttribute('canvascount')
  var celsize=initScreen(canvascount);
  displayGatewayState(name="team1:isdn 1",num=1,groupaccess=true,otheraccess=false,selected=false,groupcount=3,othercount=0,celsize);
  displayGatewayState(name="team1:isdn 2",num=2,groupaccess=true,otheraccess=false,selected=false,groupcount=1,othercount=0,celsize);
  displayGatewayState(name="team1:isdn 3",num=3,groupaccess=true,otheraccess=false,selected=false,groupcount=0,othercount=0,celsize);
  displayGatewayState(name="team1:isdn 4",num=4,groupaccess=true,otheraccess=false,selected=false,groupcount=0,othercount=0,celsize);
  displayGatewayState(name="shared leased line",num=5,groupaccess=true,otheraccess=true,selected=false,groupcount=32,othercount=2,celsize);
  displayGatewayState(name="shared adsl 1",num=6,groupaccess=true,otheraccess=true,selected=false,groupcount=0,othercount=2,celsize);
  displayGatewayState(name="shared adsl 2",num=7,groupaccess=true,otheraccess=true,selected=true,groupcount=1,othercount=0,celsize);
  displayGatewayState(name="shared adsl 3",num=8,groupaccess=true,otheraccess=true,selected=false,groupcount=0,othercount=0,celsize);
  displayGatewayState(name="team2: leased line",num=9,groupaccess=false,otheraccess=true,selected=false,groupcount=0,othercount=2,celsize);
  displayGatewayState(name="team2: vpn gateway",num=10,groupaccess=false,otheraccess=true,selected=false,groupcount=0,othercount=0,celsize);
  displayGatewayState(name="team2: 3g line",num=11,groupaccess=false,otheraccess=true,selected=false,groupcount=0,othercount=0,celsize);
  routerimg=document.getElementById('routerimg'); 
  document.getElementById('docbody').removeChild(routerimg);
  drawScreen();
}
