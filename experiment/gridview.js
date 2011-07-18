function showCell(num,color,s) {
  var canvasname="canvas" + num;
  var canvas=document.getElementById(canvasname);
  var context=canvas.getContext("2d");
  context.fillStyle = "#aaaaaa";
  context.fillRect(0,0,s,s);
  context.fillStyle = color;
  context.fillRect(5,5,s-10,s-10);
  context.fillStyle = "#cccccc";
  context.fillRect(10,10,s-20,s-20);
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
        showCell(canvasno,"#bbbbbb",celsize);
      }
    }
  } 
  return celsize; 
}

window.onload = function() {
  var canvascount=document.getElementById('docbody').getAttribute('canvascount')
  var celsize=initScreen(canvascount);
  showCell(7,"#a06060",celsize);
  drawScreen();
}
