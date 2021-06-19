var tempFiles = []; // create an empty array
var lastPos = []; // create an empty array
var busyFile = []; // create an empty array
var taintedFile = []; // create an empty array

var colors = [];
colors["js"]='#f0fff0';
colors["py"]='#fff0ff';
colors["html"]='#f0f0ff';
colors["css"]='#f0ffff';

var modes = [];
modes["js"]="ace/mode/javascript";
modes["py"]="ace/mode/python";
modes["html"]="ace/mode/html";
modes["css"]="ace/mode/css";

var lastFile; 
var lastColor;
var editor;

var hide_ext=[];

function reload(){
	getFile(lastFile);
}
function deleteFile(){
  if (confirm('Delete '+lastFile + "? This is cannot be undone")) {
		 console.log('Deleting...'); 
		 cmd("import os\r\nos.remove('" + lastFile +"')\r\n\r\n")
		 closeFile(lastFile)
	}else{console.log('Abort Reload');}
	
}
function cmd(wahtToRun){
   var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
      if (this.readyState == 4 && this.status == 200){
        alert("Command Sucessfully executed");
        console.log(xhr.responseText);
      }
      if (this.readyState == 4 && this.status !== 200){
        alert("Command Failed");
      }
    };

    xhr.open("CMD", '/', true);
    xhr.send(wahtToRun); 
    
} 
function runFile(){
  if (taintedFile[lastFile]){
    if (!confirm(lastFile + " has not been saved! Run existing file on disk?")) {
       return;
    }
  }
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200){
      alert("File Run Sucessfull");
      console.log(xhr.responseText);
      getLog();
      switchMain('main_term');
      
    }
    if (this.readyState == 4 && this.status == 500){
      alert("File Run Failed");
    }
    if (this.readyState == 4 && this.status == 403){
      alert("File Run Forbidden");
    }
  };
  xhr.open("CMD", lastFile, true);
  xhr.send(); 
} 
function getLog(){
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      document.getElementById("term_out").innerHTML=xhr.responseText;
    }
  };
  xhr.open("LOG", "console.log", true);
  xhr.send("\r\n");   

}  
function reset() {
	var xhr = new XMLHttpRequest();
	xhr.open("RST", '/', true);
	xhr.send("\r\n");
	//setTimeout(function(){ switchMain("main_graph"); }, 100);
}

function save(){
  if (!busyFile[lastFile]){
	  tempFiles[lastFile]=editor.getValue();
	  saveFile(lastFile);
  }
}
function addFile(){
  newFile = window.prompt("Filename","test.py");
  if (newFile!==null){
  tempFiles[newFile]="";
	makeTab(newFile);
	activeFile(newFile);}
}
function saveFile(filename){
	if (!busyFile[filename]){
		busyFile[filename]=true;//activate save lock
	    var xhr = new XMLHttpRequest();
	    xhr.onreadystatechange = function() {
	      if (this.readyState == 4 && this.status == 200){
	            alert("Save Sucessfull");
	            taintedFile[filename]=false;
	            busyFile[filename]=false;//release save lock
	            buildTree();
	        }
	      if (this.readyState == 4 && this.status !== 200){
	            alert("Save Failed");
	            busyFile[filename]=false;//release save lock
	            buildTree();
	        }
	    };
	
	    xhr.open("PUT", filename, true);
	    xhr.send(tempFiles[filename]); 
	}else{
		alert("File is busy! - Please wait");
	}
}
function closeFile(filename){
  var e = document.getElementById("div_" + filename );
  e.parentNode.removeChild(e);
  setTimeout(function(){ switchMain("main_files"); }, 100);
  resetColorTab()
}
function resetColorTab(){
  var file_div_bg = document.getElementsByClassName("file_div");
  for (var i = 0; i < file_div_bg.length; i++) {
    file_div_bg[i].style.background = "#eee";
    file_div_bg[i].style.borderBottomLeftRadius = "5px" ;
    file_div_bg[i].style.borderBottomRightRadius = "5px" ;
    file_div_bg[i].style.marginBottom="4px";
  }
}
function makeTab(filename){
  var files = document.getElementById("navbar");
	files.innerHTML+='<div class="file_div" id="div_' + filename + '"  title="' + filename + '" onclick="activeFile(\'' + filename + '\')">' + filename+'<div id="img_close" class="b64Img" style="height: 20px;width: 20px;" onClick="closeFile(\'' + filename + '\')"></div></div>';
	lastPos[filename]=0;
}

function getFile(filename){
	var e = document.getElementById("div_" + filename );
    if(typeof(e) != 'undefined' & e !== null){
    	//File exits in navbar
    	if (busyFile[filename]){
			console.log('Reload Failed - file is busy');
			return;
    	}
    	if (!confirm('Reload File from Disk?')) {
    	activeFile(filename);
		  console.log('Abort Reload');
		  return;
		} 
		console.log('Reloading');
		editor=null;
		lastFile=null;
        
    } else{
	    busyFile[filename]=false;
	    
	    makeTab(filename);
	}
	busyFile[filename]=true;
	var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
      if (this.readyState == 4 && this.status == 200) {
        tempFiles[filename]=xhr.responseText;
        busyFile[filename]=false;
        taintedFile[filename]=false;
        buildTree();
        activeFile(filename);
      }
    };
    xhr.open("GET", filename, true);
    xhr.send("\r\n"); 
}

function activeFile(filename){
	//save the last file to temporary buffer

	if (typeof(editor) != 'undefined' && editor !== null && lastFile != filename){
    if (editor.getValue().localeCompare(tempFiles[lastFile])!=0){
      taintedFile[lastFile]=true;
    }
    tempFiles[lastFile]=editor.getValue();
		lastPos[lastFile]=editor.selection.getCursor().row;
	}
	
	//wipe ace editor
	switchMain("main_editor");
	if (lastFile != filename){
		editor = ace.edit("id_editor");
		editor.session.setOptions({ tabSize: 2, useSoftTabs: true });
		
		//load the new file from temporary buffer
		editor.setValue(tempFiles[filename]);
		lastFile=filename;
		
		
		//display/hide the Run button
		if (filename.split('.').pop()=="py"){
		  document.getElementById("button_run").style.display = "block";
		}else{
      document.getElementById("button_run").style.display = "none";
    }
		
		//color code the editor
		lastColor='#ffffff'
		
		editor.getSession().setMode("ace/mode/text");
		if (colors[filename.split('.').pop()]!==null){
		  editor.getSession().setMode(modes[filename.split('.').pop()]);
		  lastColor=colors[filename.split('.').pop()]
		}
    //change color to default of all tabs
    resetColorTab();
    //chage the currentyl active one to the editor color
    document.getElementById("div_"+filename).style.background=lastColor;
    document.getElementById("div_"+filename).style.borderBottomLeftRadius= "0px" ;
    document.getElementById("div_"+filename).style.borderBottomRightRadius= "0px" ;
    document.getElementById("div_"+filename).style.marginBottom="0px"
		editor.container.style.background=lastColor;
		
		editor.commands.addCommand({
		    name: "myCommand",
		    bindKey: { win: "Ctrl-S", mac: "Command-S" },                
		    exec: function() {        save();    }
		});   
		editor.getSession().on('change', function() {
      taintedFile[lastFile]=true;
    });
		editor.focus();

		editor.gotoLine(lastPos[filename]); 

	}else{
		if (typeof(editor) != 'undefined' && editor !== null){
		  editor.focus();
		}
	}

}
function buildNavbar(){
  var navbar = document.getElementById("navbar")
  //https://www.iconfinder.com/iconsets/gnomeicontheme
  navbar.innerHTML += '<button title="Reset" onclick="reset()"><div id="img_reset" class="b64Img"></div>'
  navbar.innerHTML += '<button title="Directory" onclick="switchMain(\'main_files\');buildTree();"><div id="img_dir" class="b64Img"></div>'
  navbar.innerHTML += '<button title="Info" onclick="switchMain(\'main_info\')"><div id="img_info" class="b64Img"></div>'
  navbar.innerHTML += '<button title="Graph" onclick="switchMain(\'main_graph\')"><div id="img_graph" class="b64Img"></div>'
  
  navbar.innerHTML += '<button title="Term" onclick="switchMain(\'main_term\');getLog()"><div id="img_term" class="b64Img"></div>'
  navbar.innerHTML += '<button title="New File" onclick="addFile()"><div id="img_add" class="b64Img"></div>'
  "https://icons8.com/icon/pack/user-interface/color"
}

function buildEditor(){
	var e = document.getElementById("main_editor");	
	e.innerHTML +='<div class="menu">\
<button title="Save"  onclick="save()"><div id="img_save" class="b64Img"></div></button>\
<button title="Reload"   onclick="reload()"><div id="img_reload" class="b64Img"></div></button>\
<button title="Save & Run File" id="button_run"  onclick="runFile()"><div id="img_run" class="b64Img"></div></button>\
<button title="Delete" onclick="deleteFile()"><div id="img_delete" class="b64Img"></div></button>\
</div>'

}



function buildTree(){
	var xhr = new XMLHttpRequest();
	xhr.onreadystatechange = function() {
	  if (this.readyState == 4 && this.status == 200) {
	    var htmltext= '<table>';
	    htmltext+="<tr><th>Open</th><th>Edit</th><th>Filename</th><th>Size</th></tr>"
	    var res = xhr.responseText.split(";\r\n");
	    for (var x in res){
	      if (x===0){
	      	//parameters
	    	 console.log(res[0]);
	      }
	      if (x>0){ //ignore zero (perameters 
	        if (res[x].length >5){
  		      y=res[x].split(",");
            if (hide_ext[y[0].split('.').pop()]==null){
              htmltext+="<tr>"
              htmltext +="<td><a href='" + y[0] + "' target='_blank'><div id='img_file' class='b64Img'></div></a> </td>"
              
              if (y[0].split('.').pop()=="gz")
                htmltext +="<td></td>"
              else
                htmltext +="<td><a onclick=\"getFile('" + y[0] + "')\"><div id='img_pencil' class='b64Img'></div></a> </td>"
              htmltext +="<td>"+ y[0] + "</td>"
              htmltext +="<td>" + y[1] + "</td>"
    	        htmltext+="</tr>"
            }
  		    }
	      }
	    }
	    htmltext+="</table>"
	    document.getElementById("container_files").innerHTML = htmltext;
	  }
	};
	xhr.open("DIR", 'tree', true);
	xhr.setRequestHeader("Time", new Date().getTime());
	xhr.send("\r\n");
}

function switchMain(mainDivID){
  var i, mains_display;
  mains_display = document.getElementsByClassName("main");
  for (i = 0; i < mains_display.length; i++) {
    mains_display[i].style.display = "none";
  }
  resetColorTab();
  document.getElementById(mainDivID).style.display = "block";
}