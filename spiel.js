var serverIP = "localhost";
var secure = true;

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
var dranName = "";
var ausgetauscht = false;
var nextCard = -1;
var hand = [];
var stapel = [];
var offen = [];
var verdeckt = [];
var username = "";
var andereSpieler = [];

var webSocket = null;
var timer = null;

// Wandelt die KartenID in den Namen der Bilddatei einer Karte um
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

// Rendert eine Karte aus der Kartenhand
function renderCard(cardId, handNr) {
	"use strict";
	return "<img class=\"handKarte\" src=\"karten/"+numberToFile(cardId)+"\" alt=\"\" onClick=\"ausspielen("+cardId+", "+handNr+")\">";
}

// Rendert die komplette Kartenhand
function renderHand() {
	"use strict";
	var str = "";
	for(var i=0; i<hand.length; i++) {
		str += renderCard(hand[i], i);
	}
	document.getElementById("hand").innerHTML = str;
}

// Rendert die letzten vier Karten des Ablagestapels
function renderAblage() {
	"use strict";
	document.getElementById("ablage1").src = "karten/"+numberToFile(stapel[stapel.length-4]);
	document.getElementById("ablage2").src = "karten/"+numberToFile(stapel[stapel.length-3]);
	document.getElementById("ablage3").src = "karten/"+numberToFile(stapel[stapel.length-2]);
	document.getElementById("ablage4").src = "karten/"+numberToFile(stapel[stapel.length-1]);
}

// Rendert die offenen (bzw. geschlossenen) Karten des Spielers
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

// Rendert die Namen und Karten der Mitspieler
function renderAndereSpieler() {
	"use strict";
	for(var i = 0; i<andereSpieler.length/3; i++) {
		var str = (andereSpieler[i*3] === dranName?"<b>":"");
		str += andereSpieler[i*3] + (andereSpieler[i*3].toLowerCase().includes("hann")?" (hacker)":"");
		str += (andereSpieler[i*3] === dranName?"</b>":"");
		str += " <b>" + andereSpieler[i*3+1] + "</b><br>";
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

// Ruft sämtliche Render Funktionen auf
function render() {
	"use strict";
	renderHand();
	renderAblage();
	renderOffen();
	renderAndereSpieler();
	
	if (dran || !ausgetauscht) {
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

// Startet den Timer um nach einer 3 noch eine weitere Karte auszuspielen
function startAusspielTimer() {
	"use strict";
	var secs = 5;
	document.getElementById("weiterInDiv").style.display = "block";
	stopAusspielTimer();
	timer = setInterval(function() {
		document.getElementById("weiterInDiv").innerHTML = "Weiter in "+secs+"s ...";
		secs--;
		if (secs < 0) {
			stopAusspielTimer();
		}
	}, 1000);
}

// Stoppt den Ausspieltimer
function stopAusspielTimer() {
    if (timer === null) {
        return;
    }
    document.getElementById("weiterInDiv").style.display = "none";
	webSocket.send(username+";weiter");
	timer.clearInterval(x);
}


// Wird durch Klick auf eine eigene Karte ausgelöst
// Tauscht entweder die eigenen Karten durch oder spielt die Karte aus
function ausspielen(nr, handNr) {
	"use strict";
	if (!ausgetauscht) {
		if (handNr >= 0) {
			var k = offen[0];
			offen[0] = offen[1];
			offen[1] = offen[2];
			offen[2] = hand[handNr];
			hand[handNr] = k;
		}
		render();
		return;
	}
	
	if (dran) {
		if (handNr < 0 && offen.length === 0) {
			webSocket.send(username+";-4"); 
		} else {
			webSocket.send(username+";"+handNr);
		}
	}
	
	// Drei gleichzeitig ausspielbar mit anderen Karten
	if (nr<4 || nr>7) {
			dran = !dran;
	} else {
		startAusspielTimer();
	}
}

// Durch Klick auf Ablagestapel wird dieser Aufgenommen
function aufnehmen() {
	"use strict";
	webSocket.send(username+";nehme"); 
}


function austauschen() {
	"use strict";
	var str = "";
	for (var i = 0;i<3;i++) {
		str += offen[i] + ",";
	}
	for (var i = 0;i<3;i++) {
		str += hand[i] + ",";
	}
	str = str.substring(0,str.length-1);
	webSocket.send(username+";kartenTausch;"+str); 
	ausgetauscht = true;
	document.getElementById("austauschDiv").style.display = "none";
}

// Einloggen beim Server und sämtliche Netzwerkangelegenheiten aufsetzen
function login() {
	"use strict";
	username = document.getElementById("nameText").value.replace(/[^a-zA-Z]+/g, '');

	username = username.substring(0,20);

	document.getElementById("startSeite").style.display = "none";
	document.getElementById("spielSeite").style.display = "inline";
	
	webSocket = new WebSocket('ws'+(secure?'s':'')+'://'+serverIP+':8442');
	
	renderHand();
	
	webSocket.onopen = function (event) {
	  webSocket.send(username); 
	};
	
	webSocket.onmessage = function (event) {
		var msg = JSON.parse(event.data);

		if (msg.Message !== undefined) {
		    var gifDiv = document.getElementByIs("gifDiv");

		    //gifDiv.addChild(); //!!!

			alert(msg.Message);
			return;
		}


		// Eigene Variablen vom Server aktualisieren
		dran = (msg.Dran === username);
		dranName = msg.Dran;
		nextCard = msg.Ziehen;
		stapel = msg.Ablage;
		verdeckt = msg.Verdeckt;
		andereSpieler = msg.Andere;

		// Wenn noch nicht ausgetauscht: Eigene Karten nicht andauernd zurücksetzen
		if (ausgetauscht || hand.length === 0 ) {
			hand = msg.Karten;
			offen = msg.Offen;
		}

		// Spiel rendern
		render();
	};
	
}