var serverIP = "localhost";


var farben = [
	"C",
	"D",
	"H",
	"S",
];

var zahlen = [
	"2",
	"3",
	"4",
	"5",
	"6",
	"7",
	"8",
	"9",
	"10",
	"J",
	"Q",
	"K",
	"A",
];

var dran = true;
var nextCard = -1;
var hand = [];
var stapel = [];
var offen = [];
var verdeckt = [];
var username = "";
var andereSpieler = [];

var webSocket = null;



function numberToFile(nr) {
	"use strict";
	if (!nr && nr!==0) {
		return "x.png";
	}
	if (nr==="x") {
		return "00.png";
	}
	var str = zahlen[Math.floor(nr/4)];
	str += farben[nr%4];
	str+=".png";
	return str;
}


function renderCard(cardId, handNr) {
	"use strict";
	return "<img class=\"handKarte\" src=\"karten/"+numberToFile(cardId)+"\" alt=\"\" onClick=\"ausspielen("+cardId+", "+handNr+")\">";
}


function renderHand() {
	"use strict";
	var str = "";
	for(var i=0; i<hand.length; i++) {
		str += renderCard(hand[i], i);
	}
	document.getElementById("hand").innerHTML = str;
}

function renderAblage() {
	"use strict";
	document.getElementById("ablage1").src = "karten/"+numberToFile(stapel[stapel.length-4]);
	document.getElementById("ablage2").src = "karten/"+numberToFile(stapel[stapel.length-3]);
	document.getElementById("ablage3").src = "karten/"+numberToFile(stapel[stapel.length-2]);
	document.getElementById("ablage4").src = "karten/"+numberToFile(stapel[stapel.length-1]);
}

function renderOffen() {
	"use strict";
	if (offen.length === 0) {
		document.getElementById("letzteKarten1").src = "karten/"+numberToFile(verdeckt[0]);
		document.getElementById("letzteKarten2").src = "karten/"+numberToFile(verdeckt[1]);
		document.getElementById("letzteKarten3").src = "karten/"+numberToFile(verdeckt[2]);
	} else {
		document.getElementById("letzteKarten1").src = "karten/"+numberToFile(offen[0]);
		document.getElementById("letzteKarten2").src = "karten/"+numberToFile(offen[1]);
		document.getElementById("letzteKarten3").src = "karten/"+numberToFile(offen[2]);
	}
}

function renderAndereSpieler() {
	"use strict";
	for(var i = 0; i<andereSpieler.length/3; i++) {
		var str = "";
		str += andereSpieler[i*3] + " (" + andereSpieler[i*3+1] + " Karten in der Hand)<br>";
		for (var j = 0; j<andereSpieler[i*3+2].length; j++) {
			str += "<img src=\"karten/"+numberToFile(andereSpieler[i*3+2][j])+"\" alt=\"\" width=\"15%\">";
		}
		for (var j = andereSpieler[i*3+2].length; j<3; j++) {
			str += "<img src=\"karten/x.png\" alt=\"\" width=\"15%\">";
		}
		document.getElementById("spieler"+i).innerHTML = str;
	}
	
	for(i = andereSpieler.length/3; i<3; i++) {
		var str = "";
		str += "Warte auf Mitspieler...<br>";
		for (var j = 0; j<3; j++) {
			str += "<img src=\"karten/x.png\" alt=\"\" width=\"15%\">";
		}
		document.getElementById("spieler"+i).innerHTML = str;
	}
}

function render() {
	"use strict";
	renderHand();
	renderAblage();
	renderOffen();
	renderAndereSpieler();
	
	if (dran) {
		document.getElementById("hand").style.filter = "grayscale(0%)";
		document.getElementById("letzteKarten").style.filter = "grayscale(0%)";
	} else {
		document.getElementById("hand").style.filter = "grayscale(70%)";
		document.getElementById("letzteKarten").style.filter = "grayscale(70%)";
	}
	
	if (nextCard === -1) {
		document.getElementById("stapelKarte").src = "karten/x.png";
	}
}


function ausspielen(nr, handNr) {
	"use strict";
	if (dran) {
		if (handNr <= 0 && offen.length === 0) {
			webSocket.send(username+";-4"); 
		} else {
			webSocket.send(username+";"+handNr);
		}
	}
	console.log(nr);
	dran = !dran;
}

function aufnehmen() {
	"use strict";
	webSocket.send(username+";nehme"); 
}



function login() {
	"use strict";
	username = document.getElementById("nameText").value;
	document.getElementById("startSeite").style.display = "none";
	document.getElementById("spielSeite").style.display = "inline";
	//username = prompt("Wie ist denn bitte dein Name?", "");
	
	webSocket = new WebSocket('ws://'+serverIP+':8442');
	
	renderHand();
	
	webSocket.onopen = function (event) {
	  webSocket.send(username); 
	};
	
	webSocket.onmessage = function (event) {
		var msg = JSON.parse(event.data);
		
		dran = msg.Dran;
		hand = msg.Karten;
		nextCard = msg.Ziehen;
		stapel = msg.Ablage;
		offen = msg.Offen;
		verdeckt = msg.Verdeckt;
		andereSpieler = msg.Andere;
		
		render();
	};
	
}