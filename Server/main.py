#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import pathlib
import random
import asyncio
# import ssl

import websockets
from math import floor

serverIP = "localhost"

farben = {
    0: "Herz",
    1: "Kreuz",
    2: "Karo",
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
            for i in range(-2, -4, -1):
                if k.zahl != self.karten[i].zahl:
                    return False
            return True
        return False


class Spieler:
    verdeckt, offen, karten = [], [], []
    name, ip, websocket = "", None, None

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
            return False

        # Spieler besitzt Karte und darf sie ausspielen
        if karte.spielbar(ablage.oben()):
            ablage.ablegen(karte)
            karten.remove(karte)

            # mehrere Karten ablegen
            for k in karten:
                if k.zahl == karte.zahl:
                    ablage.ablegen(k)
                    karten.remove(k)

            # Nachziehen
            while len(self.karten) < 3:
                k = stapel.zieheKarte()
                if k is not None and k.id != -1:
                    self.karten.append(k)
                else:
                    break

            # Verbrennen
            if karte.zahl == 10 or ablage.verbrennbar():
                ablage.karten = []
                return False

            return True
        return False


class Spiel:
    st = Stapel()
    ablage = Ablage()
    dran = 0
    spieler = []

    # Bots (entfernen !!!)
    # for i in range(3):
    #     spieler.append(Spieler("bot" + str(i), st.verteileKarten(), None))
    # dran = 3
    # st.karten = st.karten[0:10]

    # Bots Ende

    # Neuen Spieler hinzufügen
    def addSpieler(self, name, socket):
        for spieler in self.spieler:
            if spieler.name == name:
                return
        self.spieler.append(Spieler(name, self.st.verteileKarten(), socket))

    # Spieler Objekt finden über Spieler-Name
    def getSpielerByName(self, name):
        for spieler in self.spieler:
            if spieler.name == name:
                return spieler
        return None

    # Alle Spieler benachrichtigen
    async def benachrichtige(self):
        for i in range(len(self.spieler)):
            if self.spieler[i].websocket:
                try:
                    await self.spieler[i].websocket.send(self.socketNachricht(i))
                except websockets.ConnectionClosed as exc:
                    print("Verbindung zu " + self.spieler[i].name + " geschlossen!")
                    self.spieler[i].websocket = None

    # Nächster Spieler dran (incl. Aussetzen)
    def naechster(self):
        aussetzen = 0
        for i in range(min(len(self.ablage.karten), 3)):
            if self.ablage.karten[i].zahl == 4:
                aussetzen += 1
        self.dran = (self.dran + 1 + aussetzen) % 4

    # Führe Spielzug aus
    def spielzug(self, karteId):
        # Karte überhaupt vorhanden in Hand?
        if karteId >= len(self.spieler[self.dran].karten):
            return False

        spielzugErfolgreich = False

        # Normale Hand-Karten: ID >= 0
        if karteId >= 0:
            k = self.spieler[self.dran].karten[karteId]
            spielzugErfolgreich = self.spieler[self.dran].spielzug(k, self.ablage, self.st,
                                                                   self.spieler[self.dran].karten)
        # Offene (und verdeckte) Karten: ID < 0
        else:
            if karteId == -4:
                if len(self.spieler[self.dran].karten) == 0:
                    if not self.spieler[self.dran].spielzug(self.spieler[self.dran].verdeckt[-1], self.ablage, self.st,
                                                            self.spieler[self.dran].verdeckt):
                        self.nehme()
                        self.spieler[self.dran].karten.append(self.spieler[self.dran].verdeckt.pop())
                    spielzugErfolgreich = True
            elif (-1 - karteId) < len(self.spieler[self.dran].offen):
                k = self.spieler[self.dran].offen[-1 - karteId]
                spielzugErfolgreich = self.spieler[self.dran].spielzug(k, self.ablage, self.st,
                                                                       self.spieler[self.dran].offen)
            else:
                return
        # Wenn Spielzug valide: nächster Spieler dran
        if spielzugErfolgreich:
            self.naechster()

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
        msg = addJson(msg, "Dran", str(self.istdran(self.spieler[nr].name)).lower())
        msg = addJson(msg, "Namen", str(self.spieler).replace("[", "[\"").replace("]", "\"]")).replace(", ", "\", \"")
        msg = addJson(msg, "Karten", str(self.spieler[nr].karten))
        msg = addJson(msg, "Offen", str(self.spieler[nr].offen))
        verdecktArr = []
        for x in self.spieler[self.dran].verdeckt:
            verdecktArr.append("x")
        msg = addJson(msg, "Verdeckt", str(verdecktArr).replace("'", "\""))
        msg = addJson(msg, "Ablage", str(self.ablage.karten))
        msg = addJson(msg, "Andere", self.getAndereKarten(nr))
        msg = addJson(msg, "Ziehen", str(self.st.oben()))[:-2] + "\n"
        msg += "}"
        print(msg)
        return msg

    # Offene Karten der anderen Spieler
    def getAndereKarten(self, nr):
        k = "["
        for i in range(len(self.spieler)):
            if i != nr:
                if len(self.spieler[i].offen) == 0:
                    offeneKarten = str(self.spieler[i].verdeckt)
                else:
                    offeneKarten = str(self.spieler[i].offen)
                k += "\"" + self.spieler[i].name + "\", "
                k += str(len(self.spieler[i].karten)) + ", " + offeneKarten + ", "
        if len(k) < 2:
            return "[]"
        return k[:-2] + "]"

    # Gibt es bereits einen Sieger?
    def laeuft(self):
        a = 1
        for s in self.spieler:
            a *= (len(s.karten) + len(s.offen) + len(s.verdeckt))
        return a > 0


def ladeSpiel(spielListe):
    for sp in spielListe:
        if sp.getSpielerByName:
            pass
    pass


if __name__ == '__main__':
    sp = Spiel()


    # ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # zertifikat = pathlib.Path(__file__).with_name("priesterCert.pem")
    # ssl_context.load_cert_chain(zertifikat)

    async def socketLoop(websocket, path):
        print("Neue Verbindung")
        spieler = None

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
                # Spielzug nur ausführen wenn alle Spieler da und Spieler dran
                if len(sp.spieler) == 4 and sp.istdran(msg[0]):
                    # Karten aufnehmen weil anderer Zug nicht möglich
                    if msg[1] == "nehme":
                        sp.nehme()
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
                # Wenn Spieler neu --> zum letzten Spiel hinzufügen
                elif len(sp.spieler) < 4:
                    sp.addSpieler(msg[0], websocket)

            spieler = sp.getSpielerByName(msg[0])
            # Alle Spieler benachrichtigen
            await sp.benachrichtige()


    # Starte den Server
    start_server = websockets.serve(socketLoop, serverIP, 8442)  # , ssl=ssl_context)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
