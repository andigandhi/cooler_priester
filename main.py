#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import asyncio
import ssl

import websockets
from math import floor

# ###### CONFIG ######

serverIP = "localhost"
debug = False

secure = True
SSLchain = "/home/pi/ssl/fullchain.pem"
SSLkey = "/home/pi/ssl/key.pem"

# ###### ###### ######


farben = {
    0: "Kreuz",
    1: "Karo",
    2: "Herz",
    3: "Pik",
}

werte = {
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "B",
    12: "D",
    13: "K",
    14: "A",
}


# Eine Zeile JSON hinzufügen
def addJson(msg, key, val):
    return msg + "\t\"" + key + "\": " + val + ",\n"


# Klasse für das Objekt "Karte"
class Karte:
    farbe, zahl = -1, -1
    id = -1

    # Initialisierung über die ID (0-51)
    def __init__(self, kartenId):
        if id == -1:
            return

        self.zahl = floor(kartenId / 4) + 2
        self.farbe = kartenId % 4
        self.id = kartenId

    def getID(self):
        return self.id

    def __str__(self):
        return farben[self.farbe] + werte[self.zahl]

    def __repr__(self):
        return str(self.id)

    # Test ob eine Karte spielbar ist
    def spielbar(self, k):
        # 2 oder 3 immer spielbar
        b = (self.zahl == 2 or self.zahl == 3)

        # Bei 7 drunter legen
        if k.zahl == 7:
            if self.zahl < 7:
                b = True

        # Sonst gleich oder drueber (Ausnahme 10)
        else:
            if self.zahl >= k.zahl or self.zahl == 10:
                b = True

        return b


# Nachziehestapel
class Stapel:
    karten = []

    # Mische den Kartenstapel
    def __init__(self):
        for i in range(52):
            self.karten.append(Karte(i))
        random.shuffle(self.karten)

    # Ziehe oberste Karte des Nachziehstapels
    def zieheKarte(self):
        if len(self.karten) > 0:
            return self.karten.pop()
        return Karte(-1)

    # VERALTET!!! Gib die oberste Karte der Ablage ohne sie zu nehmen
    def oben(self):
        if len(self.karten) > 0:
            return self.karten[-1].id
        return -1

    # Verteile die Karten an einen Spieler (3 verdeckt, 3 offen, 3 Handkarten)
    def verteileKarten(self):
        ret = []
        for i in range(9):
            ret.append(self.zieheKarte())
        return ret


# Ablegestapel
class Ablage:
    karten = []

    # Nehme alle Karten der Ablage und setze Ablage zurück
    def kartenAufnehmen(self):
        k = self.karten
        self.karten = []
        return k

    # Gib die oberste Karte der Ablage zurück (3 ist unsichtbar!)
    def oben(self):
        if len(self.karten) == 0:
            return Karte(-1)
        for i in range(len(self.karten)):
            if self.karten[-1 - i].zahl != 3:
                return self.karten[-1 - i]
        return Karte(-1)

    # Füge Karte der Ablage hinzu
    def ablegen(self, karte):
        self.karten.append(karte)

    # Ist Stapel verbrennbar (weil 4 gleiche Zahlen)?
    def verbrennbar(self):
        if len(self.karten) >= 4:
            k = self.karten[-1]
            for i in range(-2, -5, -1):
                if k.zahl != self.karten[i].zahl:
                    return False
            return True
        return False


class Spieler:
    verdeckt, offen, karten = [], [], []
    name, ip, websocket = "", None, None
    fertig, kartenGetauscht = False, debug

    def __init__(self, name, karten, socket):
        self.verdeckt = karten[0:3]
        self.offen = karten[3:6]
        self.karten = karten[6:9]
        self.websocket = socket
        if socket:
            self.ip = socket.remote_address[0]
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def spielzug(self, karte, ablage, stapel, karten):

        if karte not in self.karten and len(self.karten) != 0:
            return 0

        # Spieler besitzt Karte und darf sie ausspielen
        if karte.spielbar(ablage.oben()):
            ablage.ablegen(karte)
            karten.remove(karte)

            anzahlGespielteKarten = 1

            # Drei ist unsichtbar und kann mehrfach gelegt werden
            if karte.zahl == 3:
                return 0

            # mehrere Karten ablegen
            for k in list(karten):
                if k.zahl == karte.zahl:
                    ablage.ablegen(k)
                    karten.remove(k)

                    anzahlGespielteKarten += 1

            # Nachziehen
            self.nachziehen(stapel)

            # Verbrennen
            if karte.zahl == 10 or ablage.verbrennbar():
                ablage.karten = []
                return 0

            return anzahlGespielteKarten
        return 0

    def nachziehen(self, stapel):
        while len(self.karten) < 3:
            k = stapel.zieheKarte()
            if k is not None and k.id != -1:
                self.karten.append(k)
            else:
                break

    # Am Anfang Karten austauschbar machen
    def kartenAustauschen(self, neueKarten):
        if self.kartenGetauscht:
            return

        kartenArray = list(map(int, neueKarten.split(",")))

        # Teste ob Karten nur vertauscht wurden oder ob gecheatet wurde
        kartenArray2 = []
        kartenArray3 = kartenArray.copy()
        for k1 in self.offen+self.karten:
            kartenArray2.append(k1.getID())
        kartenArray2.sort()
        kartenArray3.sort()
        if kartenArray2 != kartenArray3:
            return

        # Tausche die Karten
        for i in range(3):
            self.offen[i] = Karte(kartenArray[i])
        for i in range(3):
            self.karten[i] = Karte(kartenArray[i+3])

        self.kartenGetauscht = True


class Spiel:
    st = Stapel()
    ablage = Ablage()
    dran = 0
    spieler = []

    # Neuen Spieler hinzufügen
    def addSpieler(self, name, socket):
        for spieler in self.spieler:
            if spieler.name == name and not debug:
                return

        self.spieler.append(Spieler(name, self.st.verteileKarten(), socket))

        if debug and len(self.spieler) == 1:
            for i in range(3):
                self.addSpieler(name, socket)

    # Spieler Objekt finden über Spieler-Name
    def getSpielerByName(self, name):
        for spieler in self.spieler:
            if spieler.name == name:
                return spieler
        return None

    # Alle Spieler benachrichtigen
    async def benachrichtige(self, spielerFertig = -1):
        for i in range(len(self.spieler)):
            if debug and self.dran != i:
                pass
            elif self.spieler[i].websocket:
                try:
                    if spielerFertig == -1:
                        await self.spieler[i].websocket.send(self.socketNachricht(i))
                    else:
                        await self.spieler[i].websocket.send("{\n\tMessage: \""+self.spieler[self.dran].name +
                                                             " ist fertig!\"\n}")
                except websockets.ConnectionClosed as exc:
                    print("Verbindung zu " + self.spieler[i].name + " geschlossen!")
                    self.spieler[i].websocket = None

    # Nächster Spieler dran (incl. Aussetzen)
    def naechster(self, kartenZahl):
        aussetzen = 1

        # Aussetzen durch 4er
        for i in range(min(kartenZahl, len(self.ablage.karten))):
            if self.ablage.karten[-1-i].zahl == 4:
                aussetzen += 1
            else:
                break

        # Fertige Spieler überspringen
        for i in range(aussetzen):
            self.dran = (self.dran + 1) % 4
            while self.spieler[self.dran].fertig:
                self.dran = (self.dran + 1) % 4


    # Führe Spielzug aus
    def spielzug(self, karteId):

        spielerdran = self.spieler[self.dran]

        # Karte überhaupt vorhanden in Hand?
        if karteId >= len(spielerdran.karten):
            return False

        spielzugErfolgreich = False

        # Normale Hand-Karten: ID >= 0
        if karteId >= 0:
            k = spielerdran.karten[karteId]
            spielzugErfolgreich = spielerdran.spielzug(k, self.ablage, self.st, spielerdran.karten)
        # Offene (und verdeckte) Karten: ID < 0
        else:
            if karteId == -4:
                if len(spielerdran.karten) == 0:
                    if not spielerdran.spielzug(spielerdran.verdeckt[-1], self.ablage, self.st, spielerdran.verdeckt):
                        self.nehme()
                        if len(spielerdran.verdeckt) > 0:
                            spielerdran.karten.append(spielerdran.verdeckt.pop())
                    spielzugErfolgreich = True
            elif (-1 - karteId) < len(spielerdran.offen):
                k = spielerdran.offen[-1 - karteId]
                spielzugErfolgreich = spielerdran.spielzug(k, self.ablage, self.st, spielerdran.offen)
            else:
                return

        spielerdran.fertig = (len(spielerdran.karten) + len(spielerdran.offen) + len(spielerdran.verdeckt)) == 0

        # Wenn Spielzug valide: nächster Spieler dran
        if spielzugErfolgreich:
            self.naechster(spielzugErfolgreich)

    # Nehme alle Karten von der Ablage
    def nehme(self):
        karten = self.ablage.kartenAufnehmen()
        self.spieler[self.dran].karten += karten

    # Ist Spieler dran?
    def istdran(self, name):
        return self.spieler[self.dran].name == name

    # Erstelle JSON Text für Socket Nachricht
    def socketNachricht(self, nr):
        msg = "{\n"
        msg = addJson(msg, "Dran", "\"" + self.spieler[self.dran].name + "\"")
        msg = addJson(msg, "Namen", str(self.spieler).replace("[", "[\"").replace("]", "\"]")).replace(", ", "\", \"")
        msg = addJson(msg, "Karten", str(self.spieler[nr].karten))
        msg = addJson(msg, "Offen", str(self.spieler[nr].offen))
        verdecktArr = []
        for x in self.spieler[nr].verdeckt:
            verdecktArr.append("x")
        msg = addJson(msg, "Verdeckt", str(verdecktArr).replace("'", "\""))
        msg = addJson(msg, "Ablage", str(self.ablage.karten))
        msg = addJson(msg, "Andere", self.getAndereKarten(nr))
        msg = addJson(msg, "Ziehen", str(self.st.oben()))[:-2] + "\n"
        msg += "}"

        print(msg)

        print(self.spieler[nr].name, self.spieler[nr].karten[0])

        return msg

    # Offene Karten der anderen Spieler
    def getAndereKarten(self, nr):
        k = "["
        for i in range(len(self.spieler)):
            if i != nr:
                if len(self.spieler[i].offen) == 0:
                    verdecktArr = []
                    for x in self.spieler[nr].verdeckt:
                        verdecktArr.append("x")
                    offeneKarten = str(verdecktArr).replace("'", "\"")
                else:
                    offeneKarten = str(self.spieler[i].offen)
                k += "\"" + self.spieler[i].name + "\", "
                k += str(len(self.spieler[i].karten)) + ", " + offeneKarten + ", "
        if len(k) < 2:
            return "[]"
        return k[:-2] + "]"

    # Gibt es bereits einen Sieger?
    def laeuft(self):
        for s in self.spieler:
            if not s.fertig:
                return True
        return False


def ladeSpiel(spielListe):
    for sp in spielListe:
        if sp.getSpielerByName:
            pass
    pass


if __name__ == '__main__':
    sp = Spiel()

    if debug:
        sp.st.karten = sp.st.karten[0:36]

    async def socketLoop(websocket, path):
        global sp
        print("Neue Verbindung")
        spieler = None
        # sp = Spiel()

        # Führe Schleife aus bis Spieler die Verbindung trennt
        while True:
            # Empfange Nachricht
            try:
                msg = await websocket.recv()
            except websockets.ConnectionClosed as exc:
                print("Verbindung geschlossen!")
                if spieler:
                    spieler.websocket = None
                return

            # Trenne Nachricht in verschiedene Teile
            msg = str(msg).split(";")
            print(msg)

            # Spielzüge bestehen aus Name + Spielzug
            if len(msg) > 1:
                if msg[1] == "kartenTausch":
                    for spieler in sp.spieler:
                        if spieler.name == msg[0]:
                            spieler.kartenAustauschen(msg[2])
                            break
                # Spielzug nur ausführen wenn alle Spieler da und Spieler dran
                elif len(sp.spieler) == 4 and sp.istdran(msg[0]):
                    # Karten aufnehmen weil anderer Zug nicht möglich
                    if msg[1] == "nehme":
                        sp.nehme()
                    # Spieler kann nach einer ausgespielten 3 auch weiter sagen
                    elif msg[1] == "weiter":
                        sp.naechster(0)
                    # bestimmte Karte ausspielen
                    else:
                        sp.spielzug(int(msg[1]))

            # Login Nachricht besteht nur aus einem "Teil"
            else:
                spieler = sp.getSpielerByName(msg[0])
                # Wenn Spieler bereits existiert --> Reconnect
                if spieler:
                    # Teste auf IP des Spielers
                    if spieler.ip is None or spieler.ip == websocket.remote_address[0]:
                        spieler.websocket = websocket
                        spieler.ip = websocket.remote_address[0]
                    else:
                        return
                # Wenn Spieler neu --> zum letzten Spiel hinzufügen
                elif len(sp.spieler) < 4:
                    sp.addSpieler(msg[0], websocket)

            spieler = sp.getSpielerByName(msg[0])
            # Alle Spieler benachrichtigen
            await sp.benachrichtige()
            if not sp.laeuft():
                sp = Spiel()


    # Starte den Server

    # Mit SSL Verschlüsselung
    if secure:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(SSLchain, keyfile=SSLkey)
        start_server = websockets.serve(socketLoop, serverIP, 8442, ssl=ssl_context)

    # Ohne SSL Verschlüsselung
    else:
        start_server = websockets.serve(socketLoop, serverIP, 8442)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
