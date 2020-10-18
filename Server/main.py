import pathlib
import random
import asyncio
import ssl

import websockets
from math import floor

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

    def __init__(self):
        for i in range(52):
            self.karten.append(Karte(i))
        random.shuffle(self.karten)

    def zieheKarte(self):
        if len(self.karten) > 0:
            return self.karten.pop()
        return Karte(-1)

    def oben(self):
        if len(self.karten) > 0:
            return self.karten[-1].id
        return -1

    def verteileKarten(self):
        ret = []
        for i in range(9):
            ret.append(self.zieheKarte())
        return ret

    def verbrennbar(self):
        if len(self.karten) >= 4:
            k = self.karten[-1]
            for i in range(-2, -4, -1):
                if k.zahl != self.karten[i].zahl:
                    return False
            return True
        return False


# Ablegestapel
class Ablage:
    karten = []

    def kartenAufnehmen(self):
        k = self.karten
        self.karten = []
        return k

    def oben(self):
        if len(self.karten) == 0:
            return Karte(-1)
        for i in range(len(self.karten)):
            if self.karten[-1 - i].zahl != 3:
                return self.karten[-1 - i]
        return Karte(-1)

    def ablegen(self, karte):
        self.karten.append(karte)


class Spieler:
    verdeckt, offen, karten = [], [], []
    name = ""
    websocket = None

    def __init__(self, name, karten, socket):
        self.verdeckt = karten[0:3]
        self.offen = karten[3:6]
        self.karten = karten[6:9]
        self.websocket = socket
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
            if karte.zahl == 10 or stapel.verbrennbar():
                ablage.karten = []
                return False

            return True
        return False


class Spiel:
    st = Stapel()
    ablage = Ablage()
    dran = 0
    spieler = []

    for i in range(3):
        spieler.append(Spieler("bot"+str(i), st.verteileKarten(), None))

    def addSpieler(self, name, socket):
        for spieler in self.spieler:
            if spieler.name == name and False:
                return
        self.spieler.append(Spieler(name, self.st.verteileKarten(), socket))

    def getSpielerByName(self, name):
        for sp in self.spieler:
            if sp.name == name:
                return sp
        return None

    async def benachrichtige(self):
        for i in range(len(self.spieler)):
            print(self.spieler[i].websocket)
            if self.spieler[i].websocket:
                await self.spieler[i].websocket.send(self.socketNachricht(i))

    def naechster(self):
        self.dran = (self.dran + 1 + (self.ablage.oben().zahl == 4)) % 4

    def spielzug(self, karteId):
        if karteId >= len(self.spieler[self.dran].karten):
            return False

        if karteId >= 0:
            k = self.spieler[self.dran].karten[karteId]
            spielzugErfolgreich = self.spieler[self.dran].spielzug(k, self.ablage, self.st,
                                                                   self.spieler[self.dran].karten)
        else:
            k = self.spieler[self.dran].offen[-1 - karteId]
            spielzugErfolgreich = self.spieler[self.dran].spielzug(k, self.ablage, self.st,
                                                                   self.spieler[self.dran].offen)

        if spielzugErfolgreich:
            self.naechster()

    def nehme(self):
        karten = self.ablage.kartenAufnehmen()
        self.spieler[self.dran].karten += karten
        print(self.spieler[self.dran].karten)

    def istdran(self, name):
        print(self.spieler[self.dran].name)
        print(name)
        return self.spieler[self.dran].name == name

    def socketNachricht(self, nr):
        msg = "{\n"
        msg = addJson(msg, "Dran", str(self.istdran(self.spieler[nr].name)).lower())
        msg = addJson(msg, "Namen", str(self.spieler).replace("[", "[\"").replace("]", "\"]")).replace(", ", "\", \"")
        msg = addJson(msg, "Karten", str(self.spieler[nr].karten))
        msg = addJson(msg, "Offen", str(self.spieler[nr].offen))
        msg = addJson(msg, "Verdeckt", str(self.spieler[nr].verdeckt[-1].id))
        msg = addJson(msg, "Ablage", str(self.ablage.karten))
        msg = addJson(msg, "Ziehen", str(self.st.oben()))[:-2] + "\n"
        msg += "}"
        print(msg)
        return msg

    def laeuft(self):
        a = 1
        for s in self.spieler:
            a *= len(s.karten)
        return a > 0

    # Karten senden


if __name__ == '__main__':
    sp = Spiel()


    async def socketLoop(websocket, path):
        print("New Client!")
        while True:
            msg = await websocket.recv()
            msg = str(msg).split(";")
            print(msg)
            if len(msg) > 1 and len(sp.spieler) == 4:
                if sp.istdran(msg[0]):
                    if msg[1] == "nehme":
                        sp.nehme()
                    else:
                        sp.spielzug(int(msg[1]))
            else:
                if sp.getSpielerByName(msg[0]):
                    sp.getSpielerByName(msg[0]).websocket = websocket
                elif len(sp.spieler) < 4:
                    sp.addSpieler(msg[0], websocket)

            await sp.benachrichtige()

    start_server = websockets.serve(socketLoop, "localhost", 8442)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
