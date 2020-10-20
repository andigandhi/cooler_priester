// JavaScript Document

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
var name = "";
var andereSpieler = [];

var exampleSocket = null;



function numberToFile(nr) {
	if (!nr && nr!==0) {
		return "x.png";
	}
	var str = zahlen[Math.floor(nr/4)];
	str += farben[nr%4];
	str+=".png";
	return str;
}


function renderCard(cardId, handNr) {
	return "<img class=\"handKarte\" src=\"karten/"+numberToFile(cardId)+"\" alt=\"\" onClick=\"ausspielen("+cardId+", "+handNr+")\">";
}


function renderHand() {
	var str = "";
	for(var i=0; i<hand.length; i++) {
		str += renderCard(hand[i], i);
	}
	document.getElementById("hand").innerHTML = str;
}

function renderAblage() {
	document.getElementById("ablage1").src = "karten/"+numberToFile(stapel[stapel.length-4]);
	document.getElementById("ablage2").src = "karten/"+numberToFile(stapel[stapel.length-3]);
	document.getElementById("ablage3").src = "karten/"+numberToFile(stapel[stapel.length-2]);
	document.getElementById("ablage4").src = "karten/"+numberToFile(stapel[stapel.length-1]);
}

function renderOffen() {
	document.getElementById("letzteKarten1").src = "karten/"+numberToFile(offen[0]);
	document.getElementById("letzteKarten2").src = "karten/"+numberToFile(offen[1]);
	document.getElementById("letzteKarten3").src = "karten/"+numberToFile(offen[2]);
}

function renderAndereSpieler() {
	for(var i = 0; i<andereSpieler.length/3; i++) {
		str = "";
		str += andereSpieler[i*3] + " (" + andereSpieler[i*3+1] + " Karten in der Hand)<br>";
		for (var j = 0; j<andereSpieler[i*3+2].length; j++) {
			str += "<img src=\"karten/"+numberToFile(andereSpieler[i*3+2][j])+"\" alt=\"\" width=\"2%\">";
		}
		document.getElementById("spieler"+i).innerHTML = str;
	}
}

function render() {
	renderHand();
	renderAblage();
	renderOffen();
	renderAndereSpieler()
}


function ausspielen(nr, handNr) {
	if (dran) {
		exampleSocket.send(name+";"+handNr); 
	}
	console.log(nr);
	dran = !dran;
}

function aufnehmen() {
	exampleSocket.send(name+";nehme"); 
}



function login() {
	name = document.getElementById("nameText").text;
	document.getElementById("startSeite").style.display = "none";
	document.getElementById("spielSeite").style.display = "inline";
	//name = prompt("Wie ist denn bitte dein Name?", "");
	
	exampleSocket = new WebSocket("ws://localhost:8442");
	
	renderHand();
	
	exampleSocket.onopen = function (event) {
	  exampleSocket.send(name); 
	};
	
	exampleSocket.onmessage = function (event) {
		var msg = JSON.parse(event.data);
		
		dran = msg.Dran;
		hand = msg.Karten;
		nextCard = msg.Ziehen;
		stapel = msg.Ablage;
		offen = msg.Offen;
		andereSpieler = msg.Andere
		
		render();
	};
	
}