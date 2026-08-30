# -*- coding: utf-8 -*-
#
# SC BP Watcher — zeigt live neue Star-Citizen-Baupläne an.
# Copyright (C) 2026 Xharig
#
# SPDX-License-Identifier: GPL-3.0-only
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
Selbsttest — prüft die Erkennung ohne Star Citizen und ohne den Launcher.

Baut in einem Wegwerf-Ordner eine Spielinstallation nach (Game.log plus zwei
aufgehobene Sitzungen), lässt den Watcher darauf los und vergleicht, was
herauskommt. Nichts davon fasst echte Daten an.

Aufruf:
    python3 tools/selbsttest.py

Sinn der Sache: Die Erkennung hat ein paar Fallstricke, die man beim Lesen des
Codes nicht sieht und die schon einmal Fehler verursacht haben — abgeschnittene
Namensklammern, doppelt gezählte Meldungen, verlorene Lesestände. Sie stehen
hier als Fälle drin, damit ein Umbau sie nicht unbemerkt wieder einreißt.
"""
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

# Prueflaeufe bauen echte Fenster. Ohne diese Umleitung blitzen sie ueber
# einem laufenden Spiel auf und reissen den Fokus mit — siehe unsichtbar.py.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unsichtbar                                              # noqa: E402
unsichtbar.sicherstellen()


# Die Zeilen, wie Star Citizen sie wirklich schreibt.
def zeile(text, nummer=1, art='Added'):
    return ('<2026-08-20T21:23:49.123Z> [Notice] <SHUDEvent_OnNotification> '
            '%s notification "%s: " [%d] to queue. '
            '[Team_CoreGameplayFeatures][Missions][Comms]\n' % (art, text, nummer))


SITZUNG_1 = [
    zeile('Bauplan erhalten: Attrition-5 Repeater', 1),
    # Schiffskomponente mit Klassen-Zusatz — der muss abgeschnitten werden
    zeile("Bauplan erhalten: 7CA 'Nargun' (Civ/3/A)", 2),
    # Dieselbe Meldung als Ausblende-Ereignis — darf NICHT doppelt zählen
    zeile("Bauplan erhalten: 7CA 'Nargun' (Civ/3/A)", 2, art='Removed'),
    # Echte Namensklammer — die muss stehen bleiben
    zeile('Bauplan erhalten: Arclight Pistol Battery (30 cap)', 3),
    # Anführungszeichen mitten im Namen
    zeile('Bauplan erhalten: CF-117 Bulldog "Hazard-Zone" Repeater', 4),
    # Andere Meldung — geht uns nichts an
    zeile('Mission abgeschlossen: Irgendwas', 5),
]
SITZUNG_2 = [
    zeile('Blueprint Received: Singe Cannon (S2)', 1),        # englischer Client
    zeile('Bauplan erhalten: Attrition-5 Repeater', 2),       # Dublette über Dateien
]
LAUFEND = [zeile('Bauplan erhalten: Scalpel Sniper Rifle Magazine (12 Schuss)', 1)]

ERWARTET = {
    'attrition-5 repeater',
    "7ca 'nargun'",
    # ⚠ `(30)` statt `(30 cap)`: `pfade.namensform()` laesst die ZAHL stehen und
    # wirft nur das Wort weg — sonst waeren `(16 cap)` (Launcher, englisch) und
    # `(16 Schuss)` (Log-Nachlese, deutsch) zwei Eintraege fuer dieselbe Kiste.
    'arclight pistol battery (30)',
    # ⚠ Einfache Anführungszeichen, obwohl die Log-Zeile oben doppelte hat:
    # `pfade.namensform()` zieht alle Anführungszeichen auf ein einfaches `'`,
    # damit derselbe Bauplan aus Launcher-Export und scmdb-Katalog denselben
    # Schlüssel bekommt.
    "cf-117 bulldog 'hazard-zone' repeater",
    'singe cannon (s2)',
    # ⚠ `(12)`, nicht `(12 schuss)`: Die Log-Zeile oben ist DEUTSCH — genau der
    # Fall, der den Bauplan frueher doppelt in den Bestand gelegt hat, weil der
    # Launcher dieselbe Kiste als `(12 cap)` fuehrt.
    'scalpel sniper rifle magazine (12)',
}

fehler = []
# ⚠ Die Bilanz am Ende sagte immer „N von N fehlgeschlagen", weil sie die
# Gesamtzahl aus der Fehlerzahl selbst errechnete (`len(fehler) + 0`). Ein
# einzelner Fehler unter zweihundert Prüfungen las sich damit als „1 von 1" —
# also als hätte gar nichts geklappt. Deshalb wird jetzt wirklich gezählt.
geprueft = [0]


def hat_anzeige():
    """Lässt sich hier überhaupt ein Fenster öffnen?

    Auf einem Bau-Rechner gibt es keinen Bildschirm — dort scheitert schon
    `tk.Tk()` mit „no display name and no $DISPLAY". Die Erkennung, der Bestand
    und die Pfade brauchen kein Fenster; nur die paar Prüfungen, die eines
    aufmachen, werden dann übersprungen statt den ganzen Lauf zu versenken."""
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        r.destroy()
        return True
    except Exception:
        return False


def uebersprungen(was, grund='kein Bildschirm vorhanden'):
    print('  [--]   %s — übersprungen (%s)' % (was, grund))


def pruefe(bedingung, was):
    geprueft[0] += 1
    print(('  [ok]   ' if bedingung else '  [FEHL] ') + was)
    if not bedingung:
        fehler.append(was)


# ---------------------------------------------------------------------------
# ⚠ Am 28.08.2026 stand in `release.yml` zweimal `shell: bash` untereinander.
# YAML verbietet denselben Schlüssel zweimal in einer Map — GitHub lehnte die
# **ganze Datei** ab. Folge: Jeder Bau brach nach 0 Sekunden ab („workflow file
# issue"), über eine Stunde lang unbemerkt, weil niemand hinsah. Die Commits
# von 00:03 bis 00:57 wurden nie gebaut.
#
# Genau die Sorte Fehler, die der Selbsttest sonst sichtbar macht — nur prüfte
# er die Workflow-Dateien nicht.
#
# ⚠ Und PyYAML hilft hier NICHT: `safe_load` meldet doppelte Schlüssel nicht,
# es nimmt still den letzten Wert. Gemessen, nicht vermutet. Also von Hand über
# die Zeilen — was zugleich heißt: keine Fremdbibliothek, die fehlen kann.
_YAML_SCHLUESSEL = re.compile(r'^(\s*)(-\s+)?([A-Za-z_][\w.\- ]*):(\s|$)')
_YAML_BLOCK = re.compile(
    r'^(\s*)(?:-\s+)?[A-Za-z_][\w.\- ]*:\s*[|>][-+]?\d*\s*(?:#.*)?$')


def doppelte_schluessel(text):
    """Schlüssel, die in derselben Map zweimal stehen. [(zeile, name, erste), …]

    Zwei Fallen, an denen eine naive Zeilensuche scheitert:

    1. **Listeneinträge sind eigene Maps.** In `steps:` darf `name` bei jedem
       Schritt wieder stehen — ein `- ` beginnt eine neue Map, der Zähler wird
       zurückgesetzt.
    2. **Textblöcke enthalten alles Mögliche.** Hinter `run: |` stehen bei uns
       Shell- und Python-Zeilen, Heredocs inklusive; `on: 1` darin ist Text,
       kein Schlüssel. Alles, was tiefer eingerückt ist als der Blockschlüssel,
       wird deshalb übersprungen.
    """
    funde = []
    stapel = []          # [(einrueckung, {schluessel: zeile}), …]
    block_ein = None     # in einem |- oder >-Textblock: dessen Einrückung
    for nr, zeile in enumerate(text.splitlines(), 1):
        if block_ein is not None:
            if not zeile.strip():
                continue
            if len(zeile) - len(zeile.lstrip()) > block_ein:
                continue                      # gehört noch zum Textblock
            block_ein = None
        roh = zeile.rstrip()
        if not roh.strip() or roh.lstrip().startswith('#'):
            continue
        treffer = _YAML_SCHLUESSEL.match(roh)
        if not treffer:
            continue
        vor, strich, name = treffer.group(1), treffer.group(2), treffer.group(3)
        tiefe = len(vor) + (len(strich) if strich else 0)
        while stapel and stapel[-1][0] > tiefe:
            stapel.pop()
        if strich:
            # Neuer Listeneintrag = neue Map; was davor stand, zählt nicht mehr.
            while stapel and stapel[-1][0] >= tiefe:
                stapel.pop()
            stapel.append((tiefe, {}))
        elif not stapel or stapel[-1][0] < tiefe:
            stapel.append((tiefe, {}))
        map_ = stapel[-1][1]
        if name in map_:
            funde.append((nr, name, map_[name]))
        else:
            map_[name] = nr
        if _YAML_BLOCK.match(roh):
            block_ein = tiefe
    return funde


def baue(basis):
    live = os.path.join(basis, 'LIVE')
    os.makedirs(os.path.join(live, 'logbackups'))
    with open(os.path.join(live, 'logbackups', 'Game.log.1'), 'w',
              encoding='utf-8') as f:
        f.writelines(SITZUNG_1)
    with open(os.path.join(live, 'logbackups', 'Game.log.2'), 'w',
              encoding='utf-8') as f:
        f.writelines(SITZUNG_2)
    with open(os.path.join(live, 'Game.log'), 'w', encoding='utf-8') as f:
        f.writelines(LAUFEND)
    return live


def main():
    global ANZEIGE
    ANZEIGE = hat_anzeige()
    if not ANZEIGE:
        print('Hinweis: kein Bildschirm — Fenster-Prüfungen werden übersprungen.')
    basis = tempfile.mkdtemp(prefix='sc-bp-selbsttest-')
    live = baue(basis)
    os.environ['SC_INSTALL_DIR'] = live
    os.environ['SC_BP_HOME'] = os.path.join(basis, 'eigene')
    os.environ['SC_BP_NO_NET'] = '1'
    # Leer heisst ausdruecklich 'kein Launcher' - nur zu loeschen reicht
    # nicht: dann sucht pfade.py weiter und findet womoeglich einen
    # echten Launcher-Stand auf einer eingehaengten Windows-Platte.
    os.environ['SC_BP_LAUNCHER'] = ''
    os.environ.pop('SC_BP_OVERRIDES', None)

    try:
        import queue
        import sc_bp_watcher as w
        from scbp import bestand as bd

        print('\n1. Pfade finden')
        pruefe(w.pfade.spiel_ordner() == live, 'Spielordner gefunden')
        pruefe(len(w.pfade.log_sicherungen()) == 2, 'beide Sicherungen gefunden')
        pruefe(not w.HAT_LAUNCHER, 'läuft ohne SC Deutsch Launcher')

        print('\n2. Nachlese und laufende Sitzung')
        q = queue.Queue()
        wa = w.Watcher(q)
        wa.start()
        time.sleep(1.5)
        b = bd.laden()
        gefunden = set(b['bauplaene'])
        pruefe(gefunden == ERWARTET,
               'genau die %d erwarteten Baupläne (gefunden: %d)'
               % (len(ERWARTET), len(gefunden)))
        if gefunden != ERWARTET:
            for x in sorted(gefunden ^ ERWARTET):
                print('         Abweichung:', x)

        print('\n3. Neuer Fund im laufenden Spiel')
        # ⚠ Erst die Schlange leeren. Seit v3.1.0 meldet die Nachlese, was sie
        #   gefunden hat (bis zu `NACHLESE_MELDEN_BIS` Stück) — das sind hier
        #   sieben, und die stünden sonst in der Auswertung unten und ließen den
        #   frischen Fund wie einen von acht aussehen. Der Test prüft, dass
        #   **dieser eine** gemeldet wird, nicht wie viele vorher kamen.
        _vorher = []
        while not q.empty():
            _vorher.append(q.get())
        _nachgelesen = [m for m in _vorher if m[0] == 'new']
        pruefe(bool(_nachgelesen),
               'die Nachlese meldet ihre Funde (%d Zeilen)' % len(_nachgelesen))
        # ⚠ Und sie sind als nachgelesen gekennzeichnet, sonst sehen sie aus wie
        #   ein Fund von eben — wer gerade nichts freigeschaltet hat, wundert sich.
        pruefe(all(m[-1] is True for m in _nachgelesen),
               'und zwar als nachgelesen gekennzeichnet')

        with open(os.path.join(live, 'Game.log'), 'a', encoding='utf-8') as f:
            f.write(zeile('Bauplan erhalten: Behring FS-9 LMG', 2))
        time.sleep(w.POLL_SEC + 2)
        meldungen = []
        while not q.empty():
            meldungen.append(q.get())
        neu = [m[1] for m in meldungen if m[0] == 'new']
        pruefe(neu == ['Behring FS-9 LMG'],
               'genau eine Meldung, und zwar die richtige (war: %s)' % neu)
        pruefe(any(m[0] == 'hinweis' for m in meldungen)
               or bd.anzahl(bd.laden()) > 0, 'Lückenhinweis wurde ausgegeben')
        wa.stop()

        print('\n4. Neustart — nichts doppelt, nichts verloren')
        vorher = bd.anzahl(bd.laden())
        q2 = queue.Queue()
        wa2 = w.Watcher(q2)
        wa2.start()
        time.sleep(1.5)
        wa2.stop()
        doppelt = [m for m in list(q2.queue) if m[0] == 'new']
        pruefe(not doppelt, 'keine Meldung wiederholt (waren: %d)' % len(doppelt))
        pruefe(bd.anzahl(bd.laden()) == vorher, 'Bestand unverändert (%d)' % vorher)

        print('\n5. Eigener Pfad statt Suche')
        import json
        from scbp import pfade as pf
        os.environ.pop('SC_INSTALL_DIR')        # Suche muss jetzt scheitern
        anders = os.path.join(basis, 'woanders', 'LIVE')
        os.makedirs(anders)
        open(os.path.join(anders, 'Game.log'), 'w').close()

        # ⚠ Die Suche darf hier nichts finden — sonst prüft der Test nur, ob auf
        # DIESEM Rechner zufällig kein Star Citizen liegt. Auf einem Spielrechner
        # war er deshalb rot, obwohl das Programm richtig arbeitete. Also werden
        # die Suchwurzeln für diesen Abschnitt geleert; gesucht wird gleich
        # nochmal ausdrücklich MIT Wurzel.
        echte_wurzeln = pf._spiel_wurzeln
        pf._spiel_wurzeln = lambda: []
        pruefe(pf.spiel_ordner() is None,
               'ohne Eintrag und ohne Fundort wird nichts gefunden')
        datei = pf.vorlage_anlegen()
        pruefe(os.path.exists(datei), 'Einstellungsdatei wird zum Ausfüllen angelegt')
        d = json.load(open(datei, encoding='utf-8'))
        d['spiel_ordner'] = anders
        json.dump(d, open(datei, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        pruefe(pf.spiel_ordner() == anders, 'selbst eingetragener Pfad wird genommen')
        orte = pf.gesuchte_spielorte()
        pruefe(bool(orte), 'Suchorte werden genannt, auch wenn nichts gefunden wurde')
        d2 = json.load(open(datei, encoding='utf-8'))
        pruefe('_spiel_ordner_gesucht_wird_hier' in d2,
               'die Vorlage nennt die Suchorte beim Feld')

        # Und die Gegenprobe: Liegt an einem Suchort wirklich ein Spiel, muss es
        # gefunden werden. Ohne diese Hälfte wäre „nichts gefunden" wertlos —
        # eine kaputte Suche fände auch nichts.
        with open(datei, encoding='utf-8') as f:
            ohne = json.load(f)
        ohne['spiel_ordner'] = ''
        with open(datei, 'w', encoding='utf-8') as f:
            json.dump(ohne, f, ensure_ascii=False, indent=2)
        wurzel_mit_spiel = os.path.join(basis, 'installiert')
        echt = os.path.join(wurzel_mit_spiel, pf.SC_UNTERPFAD, 'LIVE')
        os.makedirs(echt)
        open(os.path.join(echt, 'Game.log'), 'w').close()
        pf._spiel_wurzeln = lambda: [wurzel_mit_spiel]
        pruefe(pf.spiel_ordner() == echt, 'ein Spiel an einem Suchort wird gefunden')
        pf._spiel_wurzeln = echte_wurzeln

        print('\n6. Erster Start nimmt dem Spieler die Arbeit ab')
        from scbp import assistent as assi, pfade as pf2
        # Frischer Ordner, damit "erster Start" wirklich zutrifft
        frisch = os.path.join(basis, 'frisch')
        os.makedirs(frisch)
        os.environ['SC_BP_HOME'] = frisch
        os.environ.pop('SC_INSTALL_DIR', None)
        echte_wurzeln6 = pf2._spiel_wurzeln
        pf2._spiel_wurzeln = lambda: []        # siehe Abschnitt 5
        pruefe(assi.noetig(), 'Assistent meldet sich beim ersten Start')
        pruefe(pf2.spiel_ordner() is None, 'ohne Angabe und ohne Fundort: nichts')
        pf2._spiel_wurzeln = echte_wurzeln6
        # Der Spieler wählt irgendeine Ebene — auch die falsche muss reichen
        gedeutet = pf2.spielordner_deuten(os.path.dirname(live))
        pruefe(gedeutet == live,
               'Elternordner wird zum richtigen Ordner gedeutet')
        pf2.einstellung_setzen('spiel_ordner', gedeutet)
        pruefe(pf2.spiel_ordner() == live, 'Angabe wirkt sofort, ohne Neustart')
        # Und jetzt der Punkt: Der Bestand füllt sich von allein
        from scbp import logquelle as lq
        funde, _ = lq.nachlesen(lq.Lesestand())
        frischer_bestand = bd.leer()
        for n, _z in funde:
            bd.hinzufuegen(frischer_bestand, n, 'nachlese')
        # +1, weil Schritt 3 dem laufenden Log noch einen Bauplan angehängt hat
        pruefe(bd.anzahl(frischer_bestand) == len(ERWARTET) + 1,
               'Bestand kommt aus den Logs, ohne dass jemand etwas eintippt (%d)'
               % bd.anzahl(frischer_bestand))
        pruefe(not assi.noetig(),
               'beim nächsten Mal läuft der Assistent nicht mehr von allein')

        # Der Assistent muss sich wiederholen lassen — für Leute, die sich nicht
        # durch Menüs klicken wollen. Vier Schritte, ohne Absturz durchgereicht.
        if ANZEIGE:
            a = assi.Assistent()
            a.root.withdraw()
            titel = []
            for _ in range(assi.SCHRITTE):
                titel.append(a.titel.cget('text'))
                if a.schritt == 2:
                    a.pfad.set(live)
                a._weiter()
            pruefe(len(set(titel)) == assi.SCHRITTE,
                   'Assistent hat %d unterschiedliche Schritte' % len(set(titel)))
            pruefe(assi.noetig() is False, 'nach dem Durchlauf ist alles gesetzt')
        else:
            uebersprungen('Assistent-Durchlauf')

        print('\n7. Sprache')
        from scbp import sprache
        luecken = [k for k, v in sprache.TEXTE.items()
                   if len(v) != 2 or not all(v)]
        pruefe(not luecken, 'jeder Text hat beide Sprachen (%d Einträge)'
               % len(sprache.TEXTE))
        for k in luecken[:5]:
            print('         unvollständig:', k)
        sprache.setzen('de'); deutsch = sprache.t('filter_fehlt')
        sprache.setzen('en'); englisch = sprache.t('filter_fehlt')
        pruefe(deutsch != englisch,
               'Umschalten wirkt (%s / %s)' % (deutsch, englisch))
        pruefe(sprache.t('gibtesnicht') == 'gibtesnicht',
               'fehlender Schlüssel stürzt nicht ab, sondern fällt auf')
        # Arten aus dem Katalog müssen alle eine Übersetzung haben — nach einem
        # SC-Patch können neue dazukommen, und dann steht sonst „Char_Armor_…"
        # mitten in der Liste.
        from scbp import katalog
        kat = katalog.laden()
        if kat['bauplaene']:
            roh = {e.get('a') for e in kat['bauplaene'].values()}
            offen = [r for r in roh if ('art_%s' % r) not in sprache.TEXTE]
            pruefe(not offen, 'alle %d Bauplan-Arten übersetzt %s'
                   % (len(roh), offen or ''))
        else:
            print('  [--]   Katalog nicht vorhanden, Arten nicht prüfbar')
        sprache.setzen('de')

        print('\n8. Spielsprache selbst erkennen')
        from scbp import phrasen as ph
        # Eine Sprache, die nirgends im Code steht: Der Katalog mit den
        # Bauplan-Namen verrät, welcher Text davor die Bauplan-Meldung ist.
        fremd = os.path.join(basis, 'fremd')
        os.makedirs(os.path.join(fremd, 'logbackups'))
        open(os.path.join(fremd, 'Game.log'), 'w').close()
        with open(os.path.join(fremd, 'logbackups', 'alt.log'), 'w',
                  encoding='utf-8') as f:
            f.write(zeile('Plan de construction reçu: Attrition-5 Repeater', 1))
            f.write(zeile('Mission terminée: Irgendwas', 2))
            f.write(zeile('Plan de construction reçu: Singe Cannon (S2)', 3))
        katalognamen = ['Attrition-5 Repeater', 'Singe Cannon (S2)',
                        '10-Series Greatsword Cannon']
        sicherungen = [os.path.join(fremd, 'logbackups', 'alt.log')]
        gefunden = ph.selbst_finden(katalognamen, sicherungen)
        pruefe(gefunden == 'Plan de construction reçu',
               'unbekannte Sprache wird erkannt (%r)' % gefunden)
        # Ein einzelner Treffer reicht nicht — das könnte Zufall sein
        with open(os.path.join(fremd, 'logbackups', 'einzeln.log'), 'w',
                  encoding='utf-8') as f:
            f.write(zeile('Irgendein Text: Attrition-5 Repeater', 1))
        einzeln = ph.selbst_finden(
            katalognamen, [os.path.join(fremd, 'logbackups', 'einzeln.log')])
        pruefe(einzeln is None, 'ein einzelner Treffer gilt nicht als Beleg')

        print('\n9. Merkliste')
        from scbp import merkliste as mk
        os.environ['SC_BP_HOME'] = os.path.join(basis, 'merk')
        os.makedirs(os.environ['SC_BP_HOME'], exist_ok=True)
        pruefe(mk.anzahl() == 0, 'startet leer')
        pruefe(mk.umschalten('Wunschteil') is True, 'ein Klick trägt ein')
        pruefe(mk.enthaelt('wunschteil'), 'Groß- und Kleinschreibung egal')
        pruefe(mk.umschalten('Wunschteil') is False, 'zweiter Klick trägt aus')
        mk.umschalten('Wunschteil')
        # Muster-Einträge von außen (ein eigenes Werkzeug des Autors schreibt so)
        d = mk.laden()
        d['eintraege'].append({'titel': 'Beispielsatz',
                               'muster': ['adp-mk4', 'woodland']})
        mk.speichern(d)
        pruefe(mk.treffer('ADP-mk4 Woodland Helmet') == 'Beispielsatz',
               'Muster von außen greifen weiter')
        pruefe(mk.erledigen('Wunschteil') == 'Wunschteil',
               'erfüllter Wunsch wird ausgetragen')
        pruefe(not mk.enthaelt('Wunschteil'), 'und ist danach wirklich weg')
        pruefe(mk.erledigen('Irgendwas anderes') is None,
               'was nie beobachtet wurde, ändert nichts')

        print('\n10. Deutsch und Englisch decken sich')
        import sprachen_pruefen
        beanstandungen = sprachen_pruefen.pruefe(melden=lambda *_: None)
        pruefe(not beanstandungen,
               'Projektseite, Changelog und Roadmap sind in beiden Sprachen gleich')
        for b in beanstandungen[:5]:
            print('        ·', b)

        # Der Bericht zählte einmal die Felder der Datei statt der Baupläne
        # darin: „3 Baupläne" bei 394 im Bestand, weil die Datei drei Felder
        # oben hat (version, stand, bauplaene). Eine falsche Zahl, die
        # plausibel aussieht — genau die Sorte, die niemand nachprüft.
        # Geprüft wird die Zählfunktion selbst, nicht der Bericht: Sie hängt
        # nicht davon ab, wie viel gerade im Bestand steht.
        import json as json_pruef
        import scbp.bericht as bericht_pruef
        probe = os.path.join(basis, 'zaehlprobe.json')
        with open(probe, 'w', encoding='utf-8') as f:
            json_pruef.dump({'version': 1, 'stand': 'x',
                             'bauplaene': {'a': 1, 'b': 2, 'c': 3, 'd': 4}}, f)
        pruefe(bericht_pruef._json_groesse(probe, 'bauplaene') == 4,
               'die Zählung im Bericht nimmt die Einträge, nicht die Felder')
        pruefe(bericht_pruef._json_groesse(probe, 'gibtsnicht') == '—',
               'ein fehlender Schlüssel gibt „—" statt einer erfundenen Zahl')

        # Testdaten mit ausgedachten Art-Kennungen sehen aus wie ein Fehler
        # der Oberfläche: Alles landet in „Sonstiges", und der Filter „nur
        # FPS-Waffen" zeigt nichts. Genau so ist es einmal gelaufen.
        import probe_daten
        unbekannt = probe_daten.arten_pruefen()
        pruefe(not unbekannt,
               'die Beispieldaten benutzen echte Art-Kennungen')
        for art in unbekannt[:5]:
            print('        · %s kennt katalog.ART_GRUPPE nicht' % art)

        # ⚠ Die Namensform stand dreimal im Programm und lief auseinander.
        # Folge: Der SC Deutsch Launcher schreibt 7MA "Lorica" mit geraden
        # Anführungszeichen, scmdb mit einfachen — der Bauplan galt als
        # „fehlt", obwohl er im Bestand stand. Hier wird geprüft, dass alle
        # drei Module dieselbe Form liefern.
        from scbp import bestand as b_norm, katalog as k_norm
        from scbp import merkliste as m_norm, pfade as p_norm
        proben = ('7MA "Lorica"', "7MA 'Lorica'", 'CF-117 „Hazard" Repeater',
                  'Test\xa0Name')
        gleich = all(b_norm.norm(x) == k_norm._norm(x) == m_norm._norm(x)
                     == p_norm.namensform(x) for x in proben)
        pruefe(gleich, 'alle Module vergleichen Namen gleich')
        pruefe(p_norm.namensform('7MA "Lorica"')
               == p_norm.namensform("7MA 'Lorica'"),
               'gerade und einfache Anführungszeichen gelten als derselbe Name')

        formatfehler = probe_daten.formate_pruefen()
        pruefe(not formatfehler,
               'die Beispieldaten haben die Formate des echten Katalogs')
        for satz in formatfehler[:5]:
            print('        · ' + satz)

        # Die Dokumente allein reichen nicht: Die Oberfläche zeigte an über
        # hundert Stellen deutschen Text, während oben alles grün meldete.
        import texte_pruefen
        feste = []
        for name in sorted(os.listdir(os.path.join(WURZEL, 'scbp'))):
            if name.endswith('.py'):
                feste += texte_pruefen.pruefe(
                    os.path.join(WURZEL, 'scbp', name))
        pruefe(not feste,
               'jeder sichtbare Text der Oberfläche läuft durch t()')
        # ⚠ Nicht `zeile` als Schleifenvariable — so heißt weiter oben eine
        # Hilfsfunktion, und Python macht daraus für die ganze Funktion eine
        # lokale Variable. Der Selbsttest stirbt dann Hunderte Zeilen früher.
        for nr, stelle, roh in feste[:5]:
            print('        · Zeile %d (%s): %s' % (nr, stelle, roh[:50]))

        print('\n11. Fensterlage von einem fremden Rechner')
        if ANZEIGE:
            kaputt = w.geometrie_pruefen('440x1098+999999+-999999', _wurzel())
            pruefe('+999999' not in kaputt,
                   'unsinnige Position verworfen (%s)' % kaputt)
        else:
            uebersprungen('Fensterlage von einem fremden Rechner')

        # ------------------------------------------------------------------ 12
        # Fehler mitschreiben. Der Sinn der Sache ist, dass ein Nutzer den
        # Bericht in ein **öffentliches** Issue kopieren kann — deshalb wird
        # hier vor allem geprüft, dass kein Benutzername durchrutscht.
        print()
        print('12. Fehler werden mitgeschrieben')
        os.environ['SC_BP_HOME'] = os.path.join(basis, 'fehlerbuch')
        os.makedirs(os.environ['SC_BP_HOME'], exist_ok=True)
        from scbp import fehler as fehlerbuch, bericht
        importlib.reload(fehlerbuch)

        fehlerbuch.leeren()
        with fehlerbuch.gefangen('probe.stelle'):
            raise ValueError('etwas ging schief in %s'
                             % os.path.expanduser('~/geheim/pfad'))
        eintraege = fehlerbuch.letzte(1)
        pruefe(len(eintraege) == 1, 'ein gefangener Fehler wird festgehalten')
        pruefe(eintraege and eintraege[0].get('stelle') == 'probe.stelle',
               'die Stelle steht dabei')
        pruefe(eintraege and eintraege[0].get('art') == 'ValueError',
               'die Art des Fehlers steht dabei')

        name = os.path.basename(os.path.expanduser('~').rstrip('/\\'))
        roh = json.dumps(eintraege, ensure_ascii=False)
        pruefe(len(name) < 3 or name.lower() not in roh.lower(),
               'kein Benutzername im Protokoll')
        pruefe('<heim>' in roh, 'der Heimatpfad ist ersetzt')

        # Der Ringpuffer darf die Datei nicht wachsen lassen.
        for i in range(fehlerbuch.HOECHSTENS + 12):
            fehlerbuch.merken('probe.viele', ValueError('Nummer %d' % i))
        pruefe(fehlerbuch.anzahl() == fehlerbuch.HOECHSTENS,
               'es bleiben höchstens %d Einträge liegen' % fehlerbuch.HOECHSTENS)

        text = bericht.bauen(version='0.0.0-test')
        pruefe(bool(text) and 'SC BP Watcher' in text, 'der Bericht wird gebaut')

        # ⚠ Ein Schreibfehler darf nicht spurlos verschwinden. Bis zum
        # 26.08.2026 gab `einstellungen_schreiben` nur `False` zurück — und
        # **kein einziger Aufrufer** wertet das aus. Eine Einstellung war nach
        # dem Neustart einfach wieder alt, ohne jeden Hinweis.
        # ⚠ Jede Datei, die der Code über `_mitgeliefert()` lädt, muss der Bau
        # auch einpacken. Sonst fehlt sie NUR in der fertigen Version — beim
        # Start aus dem Quellcode fällt es nie auf. Genau so fehlte das Logo auf
        # der Seite „Update & Über": Der Code lud `assets/xharig.png`, der Bau
        # lieferte nur `assets/icon.png`. Gemeldet am 26.08.2026 ,
        # dem es im Bild eines Testers auffiel.
        import re as re_
        bauplan = open(os.path.join(WURZEL, '.github', 'workflows',
                                    'release.yml'), encoding='utf-8').read()
        gebraucht = set()
        for datei in ('sc_bp_watcher.py',) + tuple(
                os.path.join('scbp', n) for n in os.listdir(
                    os.path.join(WURZEL, 'scbp')) if n.endswith('.py')):
            quelle_ = open(os.path.join(WURZEL, datei), encoding='utf-8').read()
            for treffer in re_.finditer(
                    r"_mitgeliefert\(\s*(?:os\.path\.join\()?([^)]+)\)", quelle_):
                teile = re_.findall(r"'([^']+)'", treffer.group(1))
                if teile:
                    gebraucht.add(teile[-1])
        for name in sorted(gebraucht):
            pruefe(name in bauplan,
                   'der Bau liefert „%s" mit' % name)

        # ⚠ Zwei Fallen stecken in diesem Test, beide am 26.08.2026 erlebt:
        #
        # 1. **Nicht per `chmod` sperren.** Auf den Bau-Rechnern läuft alles als
        #    root, und root schreibt auch in einen Ordner mit entzogenen
        #    Rechten. Der Test war dort grün, ohne etwas zu prüfen.
        # 2. **Nicht den ganzen Ablageordner unbrauchbar machen.** Dann kann
        #    auch das Fehlerprotokoll nicht mehr geschrieben werden — und genau
        #    das soll ja geprüft werden.
        #
        # Deshalb wird **nur die Einstellungsdatei** blockiert: Dort, wo die
        # Nebendatei `…json.tmp` entstehen müsste, liegt ein Ordner. Daran
        # scheitert das Schreiben, unabhängig von Rechten und Benutzer — der
        # Rest der Ablage bleibt heil.
        sperr = os.path.join(basis, 'sperrprobe')
        os.makedirs(sperr, exist_ok=True)
        os.makedirs(os.path.join(sperr, 'einstellungen.json.tmp'),
                    exist_ok=True)
        alt_home = os.environ.get('SC_BP_HOME')
        os.environ['SC_BP_HOME'] = sperr
        try:
            from scbp import pfade as pf_sperr
            fehlerbuch.leeren()
            geschrieben = pf_sperr.einstellung_setzen('probe', 2)
            pruefe(not geschrieben,
                   'ein blockiertes Ziel meldet einen Fehlschlag')
            stellen = [e.get('stelle') for e in fehlerbuch.letzte(3)]
            pruefe('pfade.einstellungen_schreiben' in stellen,
                   'und der Grund steht im Fehlerprotokoll')
        finally:
            if alt_home:
                os.environ['SC_BP_HOME'] = alt_home

        # ⚠ Die Zeile „Spielsprache" stand drei Übergaben lang auf „—", weil
        # `phrasen.sammeln()` ein Tupel liefert und der Bericht es wie eine
        # Liste behandelte. Der TypeError wurde von `_sicher()` verschluckt.
        # Geprüft wird deshalb der Wert selbst, nicht nur dass der Bericht baut.
        pruefe(bericht._spielsprache() and 'Bauplan erhalten'
               in bericht._spielsprache(),
               'die Spielsprache-Zeile nennt die gesuchten Formulierungen')
        for zeile_ in text.split('\n'):
            if zeile_.startswith('Spielsprache') or zeile_.startswith('Game language'):
                pruefe(zeile_.strip().rstrip() not in
                       ('Spielsprache —', 'Game language —')
                       and '—' != zeile_.split()[-1],
                       'im Bericht steht bei der Spielsprache kein Strich')
                break
        pruefe(len(name) < 3 or name.lower() not in text.lower(),
               'kein Benutzername im Bericht')
        pruefe('Letzte Fehler' in text, 'die letzten Fehler stehen im Bericht')

        fehlerbuch.leeren()
        pruefe(fehlerbuch.anzahl() == 0, 'das Protokoll lässt sich leeren')

        # ------------------------------------------------------------------ 13
        # Bestand einlesen. Wichtig ist vor allem, dass NICHTS verloren geht:
        # zusammenführen heißt zusammenführen.
        print()
        print('13. Vorhandenen Bestand einlesen')
        from scbp import importieren, bestand as bestandsmodul

        proben = {
            'eigen': {'werkzeug': 'SC BP Watcher',
                      'bauplaene': [{'name': 'XL-1', 'zeit': '2026-08-01 10:00:00'}]},
            'scmdb': {'exportSchemaVersion': 1,
                      'blueprints': [{'productName': 'XL-1', 'ts': 1756000000}]},
            'basetool': {'blueprints': [{'productName': 'XL-1',
                                         'receivedAt': '2026-08-02T01:49:03.322Z'}]},
            'launcher': {'blueprints': [{'key': 'XL-1'}]},
        }
        erkannt = all(importieren.erkennen(d) == art for art, d in proben.items())
        pruefe(erkannt, 'alle vier Formate werden am Inhalt erkannt')
        pruefe(importieren.erkennen({'irgendwas': [1, 2, 3]}) is None,
               'eine fremde Datei wird nicht erkannt')

        datei = os.path.join(basis, 'einlesen.json')
        with open(datei, 'w', encoding='utf-8') as f:
            json.dump({'blueprints': [
                {'productName': 'Attrition-5 Repeater',
                 'receivedAt': '2026-08-02T01:49:03.322Z'},
                {'productName': 'Attrition-5 Repeater'},          # Dublette
                {'productName': 'Voll Neuer Bauplan'},
            ]}, f)
        art, eintraege = importieren.lesen(datei)
        pruefe(art == 'basetool', 'die Datei wird als Basetool-Ausgabe gelesen')
        pruefe(len(eintraege) == 3, 'alle Zeilen kommen an')

        vorher = bestandsmodul.leer()
        bestandsmodul.hinzufuegen(vorher, 'Attrition-5 Repeater', 'log')
        bestandsmodul.hinzufuegen(vorher, 'Nur Im Bestand', 'log')
        v = importieren.vorschau(eintraege, vorher,
                                 katalog_namen=['Attrition-5 Repeater',
                                                'Scalpel Sniper Rifle Magazine (12 cap)'])
        pruefe(v['gesamt'] == 2, 'Dubletten in der Datei zählen einmal')
        pruefe(v['neu'] == ['Voll Neuer Bauplan'], 'nur wirklich Neues gilt als neu')
        pruefe(v['schon_da'] == ['Attrition-5 Repeater'], 'Vorhandenes wird erkannt')
        pruefe(v['unbekannt'] == ['Voll Neuer Bauplan'],
               'ein dem Katalog unbekannter Name wird gemeldet')

        dazu = importieren.uebernehmen(eintraege, vorher, speichern=False)
        pruefe(dazu == 1, 'genau ein Eintrag kommt dazu')
        pruefe('nur im bestand' in vorher['bauplaene'],
               'der vorhandene Bestand bleibt vollständig erhalten')
        pruefe(vorher['bauplaene']['attrition-5 repeater']['quelle'] == 'log',
               'ein Import überschreibt keine bessere Quelle')

        # ------------------------------------------------------------------ 14
        # "Neu"-Marken. Der ganze Nutzen haengt daran, dass sie wieder
        # verschwinden — sonst ist nach drei Versionen alles markiert.
        print()
        print('14. „Neu"-Marken an den Bereichen')
        os.environ['SC_BP_HOME'] = os.path.join(basis, 'neu1')
        os.makedirs(os.environ['SC_BP_HOME'], exist_ok=True)
        from scbp import neuheiten
        importlib.reload(neuheiten)

        neuheiten.erster_start('3.0.0')
        pruefe(neuheiten.offene('3.0.0') == [],
               'frische Installation bekommt keine Marken')

        os.environ['SC_BP_HOME'] = os.path.join(basis, 'neu2')
        os.makedirs(os.environ['SC_BP_HOME'], exist_ok=True)
        neuheiten.erster_start('2.0.0')
        # ⚠ Gegen die **höchste** Version in NEU_SEIT prüfen, nicht gegen eine
        # feste Nummer. Sonst schlägt der Test fehl, sobald ein Bereich für eine
        # spätere Version einträgt (bei „herstellung" = 3.3.0 genau so passiert):
        # Der Bereich ist bei 3.0.0 zu Recht noch nicht offen.
        hoechste = max(neuheiten.NEU_SEIT.values(),
                       key=lambda v: [int(x) for x in v.split('.')])
        offen = sorted(neuheiten.offene(hoechste))
        pruefe(offen == sorted(neuheiten.NEU_SEIT),
               'wer von 2.0.0 kommt, sieht die neuen Bereiche')
        neuheiten.gesehen('bestand', hoechste)
        pruefe('bestand' not in neuheiten.offene(hoechste),
               'die Marke verschwindet, sobald der Bereich offen war')
        pruefe(len(neuheiten.offene(hoechste)) == len(offen) - 1,
               'die übrigen Marken bleiben stehen')
        pruefe(not neuheiten.ist_neu('bestand', '2.0.0'),
               'was es in der eigenen Version noch nicht gibt, wird nicht markiert')

        # ------------------------------------------------------------------ 14a
        # Der Änderungstext wird für „Was ist neu" zerlegt. Zwei Fallen, beide
        # schon zugeschnappt: Unterpunkte als eigene Zeilen (Liste doppelt so
        # lang) und verworfene Fortsetzungszeilen (Sätze enden mittendrin).
        print()
        print('14a. Änderungstext zerlegen')
        from scbp import aktualisierung as akt
        probe = """### Hinzugefügt
- **Ein Fenster mit Reitern.** Oben die Baupläne, darunter die Einstellungen,
  ganz unten eingeklappt, was nur Fortgeschrittene brauchen.
  - Ein Unterpunkt, der nicht als eigene Zeile zählt
### Behoben
- **Das Icon fehlte.**
"""
        punkte = akt.punkte_nach_art(probe)
        pruefe(len(punkte) == 2, 'zwei Punkte, nicht vier')
        pruefe(punkte and punkte[0][0] == 'neu' and punkte[1][0] == 'fix',
               'die Art kommt aus der Zwischenüberschrift')
        pruefe(punkte and punkte[0][1].endswith('brauchen.'),
               'die Fortsetzungszeile gehört zum Satz')
        pruefe(punkte and 'Unterpunkt' not in punkte[0][1],
               'ein Unterpunkt wird nicht angehängt')

        # ------------------------------------------------------------------ 14b
        # Sprachwechsel im Hauptfenster. Es darf dabei KEIN zweites Fenster
        # aufgehen — das alte Einstellungsfenster baute sich bei einem Wechsel
        # komplett neu auf, und als Seite im Hauptfenster wurde daraus ein
        # eigenes Fenster mit halbem Inhalt.
        if ANZEIGE:
            print()
            print('14b. Sprachwechsel im Hauptfenster')
            from scbp import hauptfenster, seiten as seitenmodul, sprache as spr
            import tkinter as _tk
            spr.setzen('de')
            hf = hauptfenster.Hauptfenster(version='3.0.0')
            hf.root.withdraw()
            try:
                hf.oeffnen('allgemein')
                hf.root.update()
                vorher = hf.knoepfe['allgemein'][3].cget('text')

                def fenster_zaehlen(w):
                    n = 0
                    for k in w.winfo_children():
                        if isinstance(k, (_tk.Toplevel, _tk.Tk)):
                            n += 1
                        n += fenster_zaehlen(k)
                    return n

                seitenmodul._einstellungen(hf)._sprache_waehlen('en')
                hf.root.update()
                pruefe(fenster_zaehlen(hf.root) == 0,
                       'kein zweites Fenster beim Sprachwechsel')
                pruefe(vorher == 'Allgemein'
                       and hf.knoepfe['allgemein'][3].cget('text') == 'General',
                       'die Reiter sind übersetzt')
                pruefe(hf.aktuell == 'allgemein',
                       'die geöffnete Seite bleibt geöffnet')
                # Feste Zahl mit Absicht: Der Test soll auffallen, wenn beim
                # Sprachwechsel ein Reiter verschwindet. Kommt einer dazu,
                # wird sie hier mitgezogen. 11 = die Hauptleiste ohne die zwei
                # unter „Für Fortgeschrittene".
                #
                # ⚠ Am 28.08.2026 von 10 auf 11: **Diagnose ist nach oben
                # gewandert.** Wer die Seite braucht, hat ein Problem — und
                # sucht sie nicht in einem zugeklappten Menü namens
                # „Fortgeschritten". Seit dem Knopf „Fehlerbericht absenden"
                # ist sie zudem der Weg, auf dem Meldungen ankommen.
                pruefe(len(hf.knoepfe) == 14, 'alle Reiter sind wieder da')

                # Die Wahl muss festgehalten werden — ohne Speichern-Knopf gibt
                # es keinen zweiten Versuch. Vorher stand die Markierung
                # danach weiter auf der alten Sprache.
                from scbp import pfade as pf4
                pruefe(pf4.einstellung('sprache') == 'en',
                       'die gewählte Sprache ist gespeichert')
                pruefe(seitenmodul._einstellungen(hf).sprache_wahl.get() == 'en',
                       'und die Markierung steht darauf')
            finally:
                spr.setzen('de')
                hf.root.destroy()
        else:
            uebersprungen('Sprachwechsel im Hauptfenster')

        # ------------------------------------------------------------------ 15
        # Umzug in den sichtbaren Ordner. Hier hängt der Bauplan-Bestand dran —
        # geht das schief, steht ein Nutzer nach dem Update vor einer leeren
        # Liste, obwohl er nichts verloren hat.
        print()
        print('15. Umzug in den sichtbaren Ordner')
        import json as _json
        from scbp import pfade as pf3
        importlib.reload(pf3)

        alt_ordner = os.path.join(basis, 'alt-appdata')
        neu_ordner = os.path.join(basis, 'Dokumente')
        os.makedirs(alt_ordner, exist_ok=True)
        os.makedirs(neu_ordner, exist_ok=True)
        os.environ.pop('SC_BP_HOME', None)
        echte_alt, echte_dok = pf3.alter_app_ordner, pf3._dokumente
        pf3.alter_app_ordner = lambda: alt_ordner
        pf3._dokumente = lambda: neu_ordner
        try:
            with open(os.path.join(alt_ordner, 'bestand.json'), 'w',
                      encoding='utf-8') as f:
                _json.dump({'bauplaene': {'xl-1': {'name': 'XL-1'}}}, f)
            with open(os.path.join(alt_ordner, 'katalog-cache.json'), 'w',
                      encoding='utf-8') as f:
                _json.dump({'x': 1}, f)

            pruefe(pf3.umzug_noetig(), 'ein alter Ordner wird erkannt')
            anzahl = pf3.umziehen()
            pruefe(anzahl == 2, 'beide Dateien wandern mit')
            pruefe(os.path.exists(os.path.join(neu_ordner, 'SC BP Watcher',
                                               'Bauplaene', 'bestand.json')),
                   'der Bestand landet unter „Bauplaene"')
            pruefe(os.path.exists(os.path.join(neu_ordner, 'SC BP Watcher',
                                               'Intern', 'katalog-cache.json')),
                   'technischer Kleinkram landet unter „Intern"')
            pruefe(os.path.exists(os.path.join(alt_ordner, 'bestand.json')),
                   'der alte Ordner bleibt unangetastet liegen')
            pruefe(not pf3.umzug_noetig(), 'ein zweiter Umzug ist nicht nötig')
            pruefe(pf3.umziehen() == 0, 'und überschreibt nichts')

            # ⚠ Die Ablage-Einstellung darf `app_ordner()` nicht in eine Schleife
            # schicken. Ein scharfes Rekursionslimit macht das sofort sichtbar.
            grenze = sys.getrecursionlimit()
            sys.setrecursionlimit(120)
            try:
                pf3.app_datei('bestand.json')
                pruefe(True, 'kein Kreisverkehr zwischen Ordner und Einstellungen')
            except RecursionError:
                pruefe(False, 'kein Kreisverkehr zwischen Ordner und Einstellungen')
            finally:
                sys.setrecursionlimit(grenze)
        finally:
            pf3.alter_app_ordner, pf3._dokumente = echte_alt, echte_dok
            os.environ['SC_BP_HOME'] = os.path.join(basis, 'eigene')

        # Der Klammer-Abgleich: (12 Schuss) gegen (12 cap) — derselbe Bauplan.
        v2 = importieren.vorschau(
            [{'name': 'Scalpel Sniper Rifle Magazine (12 Schuss)', 'zeit': None}],
            bestandsmodul.leer(),
            katalog_namen=['Scalpel Sniper Rifle Magazine (12 cap)'])
        pruefe(v2['unbekannt'] == [],
               'abweichender Klammer-Zusatz gilt nicht als unbekannt')

        # ------------------------------------------------------------------ 16
        # Neustart nach dem Update. Dieser Fehler ist dreimal aufgetreten und
        # war jedes Mal schwer zu sehen, weil er nur in der verpackten Version
        # unter Windows auftritt — hier wird deshalb die Entscheidung geprüft,
        # nicht das Ergebnis.
        print()
        print('16. Neustart nach dem Update')
        from scbp import aktualisierung as akt

        gestartet = []

        umgebungen = []

        class _FalschesPopen(object):
            def __init__(self, *a, **k):
                gestartet.append(a[0] if a else None)
                umgebungen.append(k.get('env') or {})

            def poll(self):
                return None          # tut so, als lebe die neue Version

        echtes_popen = subprocess.Popen
        echte_verpackung = akt.verpackung
        merker_vorher = akt._TAUSCH_LAEUFT[0]
        try:
            subprocess.Popen = _FalschesPopen
            akt.verpackung = lambda: 'exe'

            # Wartet ein Hilfsskript auf den Dateitausch, darf `neu_starten()`
            # NICHT selbst starten: Auf der Platte liegt dann noch die ALTE
            # `.exe`, und ein eigener Start fährt genau die wieder hoch. Sie
            # hält danach den Temp-Ordner fest, der Tausch scheitert endgültig,
            # und der Nutzer sieht die alte Version weiterlaufen.
            akt._TAUSCH_LAEUFT[0] = True
            akt.neu_starten()
            pruefe(gestartet == [],
                   'wartet ein Dateitausch, wird nichts selbst gestartet')

            # Ohne wartenden Tausch (AppImage: schon getauscht) muss gestartet
            # werden — sonst bliebe das Programm nach dem Update einfach zu.
            akt._TAUSCH_LAEUFT[0] = False
            akt.neu_starten()
            pruefe(len(gestartet) == 1,
                   'ohne wartenden Tausch startet die neue Version')

            # ⚠ **Die Umgebung muss gewaschen sein.** Genau hier ist der
            # Neustart unter Linux monatelang gescheitert: `LD_LIBRARY_PATH`,
            # `PYTHONHOME` und `PYTHONPATH` zeigen im AppImage in den entpackten
            # Mount der ALTEN Version. Zwei Sekunden spaeter beendet sie sich,
            # der Mount verschwindet, und die neue Version findet ihre
            # Bibliotheken nicht mehr. Fuer den Nutzer: „es geht aus, startet
            # aber nicht" (Bomb20, 27.08.2026).
            geerbt = umgebungen[-1] if umgebungen else {}
            uebrig = [n for n in ('LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH',
                                  'APPIMAGE', 'APPDIR', 'ARGV0', '_MEIPASS')
                      if n in geerbt]
            pruefe(not uebrig,
                   'die neue Version erbt keine Pfade der alten (%s)'
                   % (', '.join(uebrig) or 'keine'))

            # Und: Stirbt die neue Version sofort, darf die alte NICHT abtreten.
            class _TotesPopen(_FalschesPopen):
                returncode = 1

                def poll(self):
                    return 1         # schon gestorben
            akt._GESTARTET[0] = _TotesPopen('x')
            pruefe(akt.neue_fassung_laeuft(wartezeit=0.3) is False,
                   'eine sofort gestorbene neue Version wird erkannt')
            akt._GESTARTET[0] = _FalschesPopen('x')
            pruefe(akt.neue_fassung_laeuft(wartezeit=0.3) is True,
                   'eine laufende neue Version gilt als geglueckt')
            akt._GESTARTET[0] = None
        finally:
            subprocess.Popen = echtes_popen
            akt.verpackung = echte_verpackung
            akt._TAUSCH_LAEUFT[0] = merker_vorher

        # Den Spiel-Starter neben dem Spielordner finden. Feste Pfadlisten
        # gehen genau dann schief, wenn jemand woanders installiert hat — und
        # das ist der Normalfall, nicht die Ausnahme.
        starter_basis = os.path.join(basis, 'starterprobe')
        rsi = os.path.join(starter_basis, 'Program Files',
                           'Roberts Space Industries')
        spiel_pfad = os.path.join(rsi, 'StarCitizen', 'LIVE')
        os.makedirs(spiel_pfad)
        os.makedirs(os.path.join(rsi, 'RSI Launcher'))
        launcher = os.path.join(rsi, 'RSI Launcher', 'RSI Launcher.exe')
        open(launcher, 'w').close()

        from scbp import pfade as pf_start
        alt_windows = pf_start.WINDOWS
        alt_ordner = pf_start.spiel_ordner
        alt_einst = pf_start.einstellung
        # ⚠ Die Registry-Suche muss ebenfalls stillgelegt werden. Sie geht an
        # den umgebogenen Umgebungsvariablen vorbei und findet auf einem Rechner
        # mit echtem Spiel den richtigen Launcher — der Test praeft sonst wieder
        # den Rechner statt den Code.
        alt_registry = pf_start._launcher_aus_registry
        pf_start._launcher_aus_registry = lambda: None

        # ⚠ Die Umgebungsvariablen MÜSSEN mit umgebogen werden. `spielstarter()`
        # sucht nach dem Spielordner noch feste Orte unter `LOCALAPPDATA`,
        # `PROGRAMFILES` und `PROGRAMW6432` ab — und auf einem Rechner, auf dem
        # Star Citizen wirklich installiert ist, findet es dort den **echten**
        # RSI Launcher. Die zweite Prüfung unten schlug deshalb bei der Autor
        # unter Windows immer fehl, während sie auf Linux und Mac grün war: Der
        # Test löschte seinen Schein-Launcher, und `spielstarter()` lieferte
        # trotzdem einen Pfad — nur eben den vom richtigen Spiel.
        #
        # Ein Test, der vom Rechner abhängt, auf dem er läuft, prüft nichts.
        alt_umgebung = {}
        for schluessel in ('LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMW6432'):
            alt_umgebung[schluessel] = os.environ.get(schluessel)
            os.environ[schluessel] = starter_basis
        try:
            pf_start.WINDOWS = True
            pf_start.spiel_ordner = lambda: spiel_pfad
            pf_start.einstellung = lambda name: None
            pruefe(pf_start.spielstarter() == launcher,
                   'der Launcher wird neben dem Spielordner gefunden')

            # Ohne Launcher darf KEIN Pfad zurückkommen — sonst erschiene ein
            # Knopf, der nichts tut.
            os.remove(launcher)
            pruefe(pf_start.spielstarter() is None,
                   'ohne Launcher gibt es keinen Knopf')
        finally:
            pf_start.WINDOWS = alt_windows
            pf_start.spiel_ordner = alt_ordner
            pf_start.einstellung = alt_einst
            pf_start._launcher_aus_registry = alt_registry
            for schluessel, wert in alt_umgebung.items():
                if wert is None:
                    os.environ.pop(schluessel, None)
                else:
                    os.environ[schluessel] = wert

        # Und dasselbe unter Linux: Dort ist der Starter **nicht** der
        # `lug-helper` (der verwaltet nur und kann gar nicht starten), sondern
        # das `sc-launch.sh` im Wine-Präfix — eine Ebene über `drive_c`.
        # Der Fehler dahinter kostete am 27.08.2026 zwei Melder und einen
        # halben Vormittag: Der Knopf war da, meldete „wird gestartet …" und
        # nichts geschah.
        linux_basis = os.path.join(basis, 'linuxprobe', 'star-citizen')
        linux_spiel = os.path.join(linux_basis, 'drive_c', 'Program Files',
                                   'Roberts Space Industries', 'StarCitizen',
                                   'LIVE')
        os.makedirs(linux_spiel)
        skript = os.path.join(linux_basis, 'sc-launch.sh')
        open(skript, 'w').close()
        os.chmod(skript, 0o755)
        # ⚠ Auch `HOME` umbiegen — aus demselben Grund wie oben bei den
        # Windows-Variablen: Der Rückfall sieht in `~/Games/star-citizen` nach,
        # und auf einem Rechner mit echtem Spiel liegt dort ein echtes Skript.
        # Die zweite Prüfung unten fände es und wäre wertlos.
        alt_heim = os.environ.get('HOME')
        os.environ['HOME'] = os.path.join(basis, 'linuxprobe', 'leeres-heim')
        try:
            pf_start.WINDOWS = False
            pf_start.spiel_ordner = lambda: linux_spiel
            pf_start.einstellung = lambda name: None
            pruefe(pf_start.spielstarter() == skript,
                   'unter Linux wird sc-launch.sh über drive_c gefunden')

            # Ohne Startskript darf KEIN Pfad kommen — auch dann nicht, wenn auf
            # dem Rechner ein `lug-helper` im Suchpfad liegt. Genau der wurde
            # früher zurückgegeben, und der Knopf tat nichts.
            os.remove(skript)
            pruefe(pf_start.spielstarter() is None,
                   'ohne sc-launch.sh gibt es unter Linux keinen Knopf')
        finally:
            pf_start.WINDOWS = alt_windows
            pf_start.spiel_ordner = alt_ordner
            pf_start.einstellung = alt_einst
            if alt_heim is None:
                os.environ.pop('HOME', None)
            else:
                os.environ['HOME'] = alt_heim

        # Jeder Ausgang beim Ablagesymbol muss im Startverlauf landen. Der
        # Fehler war zweimal nicht zu finden, weil weder ein Fehler noch eine
        # Spur im Bericht stand — geprüft wird hier deshalb, dass überhaupt
        # gemeldet wird, nicht was dabei herauskommt (das geht nur unter
        # Windows).
        quelle_start = open(os.path.join(WURZEL, 'sc_bp_watcher.py'),
                            encoding='utf-8').read()
        block = quelle_start.split('def ablagesymbol_starten')[1].split('\n    def ')[0]
        for erwartet, wofuer in (
                ("fehler.spur('Ablagesymbol: entfällt", 'nicht Windows'),
                ("fehler.spur('Ablagesymbol: abgeschaltet", 'abgeschaltet'),
                ("fehler.spur('Ablagesymbol: %s'", 'angelegt oder nicht'),
                ("fehler.spur('Ablagesymbol: Fehler", 'Ausnahme')):
            pruefe(erwartet in block,
                   'Ablagesymbol meldet den Fall „%s"' % wofuer)

        symbol_quelle = open(os.path.join(WURZEL, 'scbp', 'ablagesymbol.py'),
                             encoding='utf-8').read()
        pruefe('except Exception:\n            bereit.set()' not in symbol_quelle,
               'der Faden verschluckt Fehler nicht mehr stillschweigend')

        # Der Notausgang darf nicht an Tk hängen: Feuert der `after`-Rückruf
        # nicht, würde ein dort gestarteter Faden nie laufen — und der Prozess
        # liefe weiter, während sein Temp-Ordner schon abgeräumt wird.
        #
        # ⚠ Geprüft wird **innerhalb** von `_abtreten()`. Früher lag der
        # Notausgang direkt in `_fassung_holen`, und der Test schnitt die Quelle
        # bei `def _abtreten` ab — damals der Name der dortigen *lokalen*
        # Funktion. Seit `_abtreten()` eine eigene Funktion ist (beide
        # Abtritts-Wege teilen sie sich), traf dieser Schnitt ins Leere.
        quelle = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                      encoding='utf-8').read()
        block = quelle.split('def _abtreten')[1].split('\ndef ')[0]
        vor_rueckruf = block.split('fenster.root.after')[0]
        pruefe('os._exit(0)' in vor_rueckruf,
               'der Notausgang steht vor dem Tk-Rückruf, nicht darin')


        # ---------------------------------------------------------------- 17
        print()
        print('17. Zweisprachigkeit: kein fester Text in der Oberfläche')
        # ⚠ Warum das geprüft wird: Am 26.08.2026 stellte der Autor auf Englisch um
        # und bekam ein englisches Hauptfenster mit einer **deutschen** Melde-
        # Leiste. Die Übersetzungen dafür gab es längst — `ueberwache`,
        # `mit_launcher`, `ohne_launcher`, `nachgelesen`, `vorlaeufig` —, nur
        # benutzt hat sie niemand. Der Code setzte die deutschen Sätze weiter fest
        # zusammen.
        #
        # Deshalb prüft das hier nicht „gibt es unbenutzte Schlüssel", sondern die
        # eigentliche Ursache: **Steht sichtbarer Text fest im Code?**
        import ast as _ast
        import re as _re

        _zeichen = _re.compile(r'^[\W\d_]+$', _re.UNICODE)   # ✕ ▾ ⏻ · ✓ – …

        # Eigennamen bleiben in jeder Sprache gleich — die gehören nicht
        # übersetzt, sondern stehen genau so da.
        _namen = ('Xharig', 'Star Citizen', 'SC BP Watcher', 'GitHub',
                  'Windows', 'Linux', 'Discord')

        def _verdaechtig(wert):
            """Ist das ein sichtbarer Satz statt eines Symbols?"""
            if not isinstance(wert, str) or len(wert) < 4:
                return False
            if wert.strip() in _namen:
                return False
            if _zeichen.match(wert):        # reine Symbole sind keine Sprache
                return False
            return bool(_re.search(r'[A-Za-zÄÖÜäöüß]{3}', wert))

        def _feste_texte(datei):
            """Alle Stellen, die einem Element **wörtlich** Text mitgeben."""
            quelle = open(datei, encoding="utf-8").read()
            gefunden = []
            for knoten in _ast.walk(_ast.parse(quelle)):
                if not isinstance(knoten, _ast.Call):
                    continue
                # a) text='…' an einem Widget oder in .config()
                for wort in knoten.keywords:
                    if wort.arg != 'text':
                        continue
                    if (isinstance(wort.value, _ast.Constant)
                            and _verdaechtig(wort.value.value)):
                        gefunden.append((wort.value.lineno, wort.value.value))
                # b) q.put(('status', '…')) und ('hinweis', '…')
                for arg in knoten.args:
                    if not isinstance(arg, _ast.Tuple) or len(arg.elts) != 2:
                        continue
                    erst, zweit = arg.elts
                    if (isinstance(erst, _ast.Constant)
                            and erst.value in ('status', 'hinweis')
                            and isinstance(zweit, _ast.Constant)
                            and _verdaechtig(zweit.value)):
                        gefunden.append((zweit.lineno, zweit.value))
            return gefunden

        # ⚠ Zweiter Anlauf: Die erste Version dieser Prüfung sah nur
        # `text='…'` direkt am Widget — und übersah dadurch
        #     unten = f'{titel} — jetzt craftbar!' if titel else 'neu …'
        # weil der Satz erst in eine Variable geht und später zusammengesetzt
        # wird. Genau so lag der Fehler im Overlay. Deshalb prüfen die
        # Oberflächen-Dateien zusätzlich **jedes** String-Literal auf deutsche
        # Wörter, Docstrings ausgenommen.
        _deutsch = _re.compile(
            r'[äöüßÄÖÜ]|\b(?:jetzt|neu|nicht|kein[e]?|wird|wurde|von|aus|mit'
            r'|noch|schon|hier|dein|alle)\b')

        def _docstrings(baum):
            raus = set()
            for k in _ast.walk(baum):
                if isinstance(k, (_ast.Module, _ast.FunctionDef,
                                  _ast.AsyncFunctionDef, _ast.ClassDef)):
                    kopf = k.body[0] if k.body else None
                    if (isinstance(kopf, _ast.Expr)
                            and isinstance(kopf.value, _ast.Constant)
                            and isinstance(kopf.value.value, str)):
                        raus.add(id(kopf.value))
            return raus

        def _deutsche_saetze(datei):
            """Deutscher Satz irgendwo im Code — auch über eine Variable."""
            quelle = open(datei, encoding='utf-8').read()
            baum = _ast.parse(quelle)
            weg = _docstrings(baum)
            # Interne Protokolle (`fehler.merken`, `fehler.spur`) sind kein
            # Oberflächentext. Über den Baum ausschließen, nicht über die
            # Zeile: Ein Aufruf darf sich über mehrere Zeilen ziehen.
            for _k in _ast.walk(baum):
                if (isinstance(_k, _ast.Call)
                        and getattr(_k.func, 'attr', '') in ('merken', 'spur')):
                    for _teil in _ast.walk(_k):
                        if isinstance(_teil, _ast.Constant):
                            weg.add(id(_teil))
                # Der `if __name__ == '__main__'`-Block ist der Aufruf von der
                # Kommandozeile — den sieht kein Spieler, nur der Entwickler.
                if (isinstance(_k, _ast.If) and isinstance(_k.test, _ast.Compare)
                        and getattr(_k.test.left, 'id', '') == '__name__'):
                    for _teil in _ast.walk(_k):
                        if isinstance(_teil, _ast.Constant):
                            weg.add(id(_teil))
            gefunden = []
            for k in _ast.walk(baum):
                if not isinstance(k, _ast.Constant) or not isinstance(k.value, str):
                    continue
                if id(k) in weg:
                    continue
                wert = k.value.strip()
                if len(wert) < 8 or not _deutsch.search(wert):
                    continue
                gefunden.append((k.lineno, wert))
            return gefunden

        _wurzelpfad = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _zu_pruefen = [os.path.join(_wurzelpfad, 'sc_bp_watcher.py')]
        for _name in sorted(os.listdir(os.path.join(_wurzelpfad, 'scbp'))):
            if _name.endswith('.py') and _name not in ('sprache.py', 'fehler.py'):
                _zu_pruefen.append(os.path.join(_wurzelpfad, 'scbp', _name))

        _treffer = []
        for _datei in _zu_pruefen:
            for _zeilennr, _text in _feste_texte(_datei):
                _treffer.append('%s:%d  %r' % (os.path.basename(_datei), _zeilennr,
                                               _text[:45]))
        if _treffer:
            for _t in _treffer[:8]:
                print('       ' + _t)
        pruefe(not _treffer,
               'kein fest eingebauter Anzeigetext (%d gefunden)' % len(_treffer))

        # ⚠ ALLE Module, nicht nur die mit „Fenster" im Namen.
        #
        # Die erste Version prüfte eine Handauswahl von Oberflächen-Dateien —
        # und ließ `logquelle.py` aus, weil das nach Hintergrund klingt. Genau
        # von dort kam aber „Zwischen … hat Star Citizen Logs weggeräumt", und
        # der Satz stand fest auf Deutsch im Overlay. Auch `pfade.py` gab „kein
        # Starter gefunden" in die Statuszeile.
        #
        # Wer entscheidet, was „sichtbar" ist, irrt sich. Deshalb: alles
        # prüfen, Ausnahmen einzeln benennen und begründen.
        _AUSNAHMEN = {
            # Suchwörter und Datenzuordnung — werden nie angezeigt
            ('scbp/aktualisierung.py', 'geändert'),
            ('scbp/aktualisierung.py', 'hinzugefügt'),
            ('scbp/katalog.py', 'CDS-Rüstung'),
            ('scbp/katalog.py', 'geschütz'),
            # Wortlaut des SPIELS, mit dem im Log GESUCHT wird — angezeigt
            # wird er nie. Rueckfall, falls die `global.ini` fehlt.
            ('scbp/auftraege.py', 'Auftrag zurückgezogen'),
            # ⚠ Die schweizerdeutsche Fassung (live-CH) derselben
            # Rueckfall-Tabelle. Kein Anzeigetext, sondern ein Suchmuster
            # fuer die Log-Zeile.
            ('scbp/auftraege.py', 'Uftrag zurückgezogen'),
            # Datenfeld der Übersetzungsquellen, nirgends angezeigt (geprüft)
            ('scbp/uebersetzung.py', 'Deutsche Übersetzung (rjcncpt)'),
            ('scbp/uebersetzung.py', 'StarStrings (aufgeräumte englische Texte)'),
        }
        # Ganze Dateien, deren deutsche Texte begründet fest sind
        _AUSNAHME_DATEIEN = {
            # Was ins SPIEL geschrieben wird, folgt der Spielsprache — nicht
            # der Sprache des Werkzeugs. Wer das deutsche Sprachpaket fährt,
            # will deutsche Auftragstexte, auch wenn das Fenster englisch ist.
            'scbp/injektion.py',
            # `.desktop`-Dateien: Das Betriebssystem zeigt sie, nicht wir.
            'scbp/autostart.py', 'scbp/verknuepfung.py',
            # Kommentare in der einstellungen.json und eine Entwickler-Hilfe
            # zum fehlenden Entpacker — beides kein Oberflächentext.
            'scbp/pfade.py', 'scbp/spieltexte.py', 'scbp/phrasen.py',
            # Feldnamen der `global.ini` („Gütegrad:", „Verfolgungssignal:") —
            # damit wird in der Spieldatei GESUCHT, angezeigt wird nichts
            # davon. Gleiche Lage wie bei `phrasen.py` eine Zeile höher.
            'scbp/angaben.py',
            # Erklärender Kopf in der patch-historie.json. Steht in der Datei,
            # damit man sie im Repo ohne Quelltext versteht — nie im Fenster.
            'scbp/patchhistorie.py',
        }
        _oberflaeche = ['sc_bp_watcher.py'] + [
            'scbp/' + _n for _n in sorted(os.listdir(os.path.join(_wurzelpfad, 'scbp')))
            if _n.endswith('.py') and _n not in ('sprache.py', 'fehler.py')
            and ('scbp/' + _n) not in _AUSNAHME_DATEIEN]
        _saetze = []
        for _rel in _oberflaeche:
            _voll = os.path.join(_wurzelpfad, _rel)
            if not os.path.exists(_voll):
                continue
            for _nr, _satz in _deutsche_saetze(_voll):
                if (_rel, _satz) in _AUSNAHMEN:
                    continue
                _saetze.append('%s:%d  %r' % (_rel, _nr, _satz[:44]))
        for _s in _saetze[:14]:
            print('       ' + _s)
        pruefe(not _saetze,
               'kein deutscher Satz fest in der Oberfläche (%d gefunden)'
               % len(_saetze))

        sys.path.insert(0, _wurzelpfad)
        from scbp import sprache as _spr

        # Der schärfste Test: jede Seite in **beiden** Sprachen wirklich
        # bauen. `sprache.t()` gibt bei einem fehlenden Schlüssel dessen
        # Namen zurück statt abzustürzen — sichtbar wird das erst, wenn die
        # Seite vor einem steht. Genau so ließe sich ein zu viel gelöschter
        # Eintrag sofort erkennen: Dann stünde `e_gespeichert` als
        # Beschriftung da.
        if not hat_anzeige():
            uebersprungen('Seiten in beiden Sprachen bauen')
        else:
            import tkinter as _tk
            from scbp import hauptfenster as _hf, seiten as _st
            _schluesselartig = _re.compile(r'^[a-z][a-z0-9]*(_[a-z0-9]+){1,}$')

            def _durchsuchen(widget, gefunden):
                try:
                    _text = widget.cget('text')
                except Exception:
                    _text = None
                if isinstance(_text, str) and _schluesselartig.match(_text.strip()):
                    gefunden.append(_text.strip())
                for _kind in widget.winfo_children():
                    _durchsuchen(_kind, gefunden)

            _SEITEN = ('liste', 'fortschritt', 'allgemein', 'anzeige', 'pfade',
                       'spieltexte', 'bestand', 'wasistneu', 'ueber')
            _vorher = _spr.aktuelle()
            _kaputt, _rohe = [], []
            for _kuerzel in ('de', 'en'):
                _spr.setzen(_kuerzel)
                _f = _hf.Hauptfenster(version='0.0.0-test')
                _f.root.geometry('900x600+3000+3000')       # aus dem Blick
                for _seite in _SEITEN:
                    _rahmen = _tk.Frame(_f.root)
                    try:
                        _st.bauen(_f, _seite, _rahmen)
                        _f.root.update()
                        _durchsuchen(_rahmen, _rohe)
                    except Exception as _fehler:
                        _kaputt.append('%s/%s: %s' % (_kuerzel, _seite,
                                                      type(_fehler).__name__))
                    _rahmen.destroy()
                _f.root.destroy()
            _spr.setzen(_vorher)
            if _kaputt:
                print('       ' + '; '.join(_kaputt[:4]))
            pruefe(not _kaputt,
                   'jede Seite baut auf Deutsch und Englisch (%d Fehler)'
                   % len(_kaputt))
            if _rohe:
                print('       roh angezeigt: %s' % ', '.join(sorted(set(_rohe))[:6]))
            pruefe(not _rohe,
                   'kein Schlüsselname als Beschriftung (%d gefunden)'
                   % len(set(_rohe)))

        # Und die Gegenrichtung: Ein Schlüssel, den es nur auf Deutsch gibt, ist
        # eine halbe Übersetzung — die wirkt schlechter als gar keine.
        _halbe = [k for k, v in _spr.TEXTE.items()
                  if not isinstance(v, tuple) or len(v) < 2 or not v[1]]
        if _halbe:
            print('       ohne englische Version: %s' % ', '.join(sorted(_halbe)[:6]))
        pruefe(not _halbe,
               'jeder Text hat eine englische Version (%d ohne)' % len(_halbe))

        # ------------------------------------------------------------------ 18
        # Meldungen ziehen beim Sprachwechsel mit.
        #
        # ⚠ Abschnitt 17 prüft, dass kein Text **fest** in der Oberfläche
        # steht. Das reicht nicht: Ein Text kann sauber durch `t()` laufen und
        # trotzdem falsch stehen bleiben — nämlich dann, wenn er einmal fertig
        # zusammengesetzt in ein Label geschrieben wurde. Wer danach die
        # Sprache wechselt, hat ein englisches Fenster mit einer deutschen
        # Zeile darin. Genau so gefunden am 26.08.2026 bei „Keine
        # Log-Sicherungen gefunden".
        #
        # Der Weg dagegen: `sprache.Satz` trägt Schlüssel und Werte mit, das
        # Label merkt sich den Träger, `_neu_beschriften()` wertet ihn neu aus.
        print()
        print('18. Meldungen ziehen beim Sprachwechsel mit')
        from scbp import sprache as spr18, logquelle as lq18

        # a) Die Quelle liefert einen Träger, keinen fertigen Satz.
        grund = lq18._luecke_pruefen(0.0, [__file__])['grund']
        pruefe(spr18.auffrischbar(grund),
               'die Lücken-Meldung kommt als Träger, nicht als fertiger Text')

        spr18.setzen('de'); deutsch = str(grund)
        spr18.setzen('en'); englisch = str(grund)
        spr18.setzen('de')
        pruefe(deutsch != englisch and 'First run' in englisch,
               'derselbe Träger spricht beide Sprachen')
        # Das Datum steckt mit drin: im Deutschen 22.08.2026, im Englischen
        # 2026-08-22. Ein fertig formatiertes Datum bliebe deutsch.
        pruefe(englisch.count('-') >= 2,
               'auch das Datum wechselt seine Schreibweise')

        # b) Am echten Fenster — nicht nur an der Datenschicht.
        if ANZEIGE:
            import tkinter as _tk18
            spr18.setzen('de')
            _wz = _tk18.Tk(); _wz.withdraw()
            ov18 = None
            try:
                import sc_bp_watcher as _w18
                ov18 = _w18.Overlay(wurzel=_wz)
                ov18.root.withdraw()
                ov18.add_hinweis(grund)
                ov18._status_setzen(spr18.Satz('katalog_holt'))
                ov18.root.update()

                def _zeilen():
                    raus = []
                    for zeile in ov18.list.pack_slaves():
                        for teil in zeile.winfo_children():
                            if getattr(teil, '_quelle', None) is not None:
                                raus.append(teil.cget('text'))
                    return raus

                vorher_h = _zeilen()
                vorher_s = ov18.status.cget('text')
                spr18.setzen('en')
                ov18.root.update()
                nachher_h = _zeilen()
                nachher_s = ov18.status.cget('text')

                pruefe(vorher_h and nachher_h and vorher_h != nachher_h
                       and 'First run' in nachher_h[0],
                       'eine stehende Hinweiszeile wird mit übersetzt')
                pruefe(vorher_s != nachher_s and 'Fetching' in nachher_s,
                       'die Statuszeile wird mit übersetzt')
            finally:
                spr18.setzen('de')
                if ov18 is not None:
                    try:
                        ov18.root.destroy()
                    except Exception:
                        pass
                else:
                    _wz.destroy()
        else:
            uebersprungen('Sprachwechsel am Overlay')

        # c) Rückfallschutz. Beides sind Fehler, die sich beim nächsten Umbau
        #    leicht wieder einschleichen — und die man am laufenden Programm
        #    erst merkt, wenn jemand die Sprache umstellt.
        import re as _re18
        _quelle18 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'),
                         encoding='utf-8').read()
        _alt_puts = _re18.findall(
            r"q\.put\(\('(?:status|hinweis)', sprache\.t\(", _quelle18)
        pruefe(not _alt_puts,
               'keine Meldung geht als fertiger Text in die Warteschlange '
               '(%d gefunden)' % len(_alt_puts))

        # Jeder Schreibzugriff auf die Statuszeile muss durch `_status_setzen`
        # gehen, sonst merkt sich niemand die Quelle — und beim nächsten
        # Sprachwechsel springt eine **ältere** Meldung zurück auf den Schirm.
        _direkt = [n for n, z in enumerate(_quelle18.splitlines(), 1)
                   if 'self.status.config(' in z]
        # Erlaubt: die Zeile in `_status_setzen` selbst und die beiden in
        # `_neu_beschriften`, die genau dort bewusst neu setzen.
        pruefe(len(_direkt) <= 3,
               'die Statuszeile wird nicht an der Merkstelle vorbei gesetzt '
               '(%d Direktzugriffe)' % len(_direkt))

        # ------------------------------------------------------------------
        # ⚠ Am 27.08.2026 stand im Auswahlfeld „4.10.0 (21)" und in der Liste
        # darunter „Nichts gefunden". Grund: Das Feld liest die Patch-Historie
        # direkt, der Filter prüft den Stempel `seit` im Katalog — und gestempelt
        # wurde nur beim Neubau. Wer seinen Katalog vor rc55 geholt hat, wartet
        # sonst bis zum nächsten Patch, und der wäre obendrein stumm geblieben.
        print()
        print('19. Der Katalog holt fehlende Patch-Stempel nach')
        from scbp import katalog as kat19, patchhistorie as ph19

        os.environ['SC_BP_HOME'] = os.path.join(basis, 'stempel')
        os.makedirs(os.environ['SC_BP_HOME'], exist_ok=True)
        _kat19 = os.path.join(os.environ['SC_BP_HOME'], 'katalog-cache.json')
        _hist19 = {'4.9.9-live.1': {'datum': '2026-01-01',
                                    'neu': ['Alter Bauplan']},
                   '4.10.0-live.2': {'datum': '2026-08-26',
                                     'neu': ['Neuer Bauplan']}}
        ph19._schreib(os.path.join(os.environ['SC_BP_HOME'],
                           'patch-historie.json'), _hist19)

        def _katalog_schreiben(version, **zusatz):
            eintraege = {'alter bauplan': {'n': 'Alter Bauplan'},
                         'neuer bauplan': {'n': 'Neuer Bauplan'}}
            eintraege.update(zusatz)
            with open(_kat19, 'w', encoding='utf-8') as f:
                json.dump({'version': version, 'geholt': '',
                           'bauplaene': eintraege, 'missionen': {}}, f)

        # a) Ein Katalog ohne jeden Stempel — wie bei jedem Bestandsnutzer.
        _katalog_schreiben('4.10.0-live.2')
        pruefe(kat19.stempel_nachziehen() == 2,
               'beide fehlenden Stempel werden nachgetragen')

        _d19 = kat19.laden()
        pruefe(_d19['bauplaene']['neuer bauplan'].get('seit') == '4.10.0-live.2',
               'der Neuzugang trägt die Version, die ihn gebracht hat')
        pruefe(kat19.neue(_d19) == {'neuer bauplan'},
               '„neu im Spiel" zeigt genau den einen Zugang')

        # b) Zweiter Start: nichts zu tun. Sonst schriebe das Werkzeug bei
        #    jedem Start eine Megabyte-Datei neu, ohne dass sich etwas ändert.
        pruefe(kat19.stempel_nachziehen() == 0,
               'ein zweiter Start schreibt nicht noch einmal')

        # c) Ohne Katalog darf nichts passieren und nichts fliegen.
        os.remove(_kat19)
        pruefe(kat19.stempel_nachziehen() == 0,
               'ohne Katalog bleibt es ruhig')

        # d) ⚠ Der teurere Fehler: Fehlt die Vergleichsgrundlage, hielte
        #    `erzeugen()` jeden Bauplan für „schon immer da" und der nächste
        #    Patch meldete NULL Zugänge. Der vorhandene Katalog ist die
        #    richtige Grundlage — was darin steht, war vorher im Spiel.
        _katalog_schreiben('4.10.0-live.2')
        pruefe(not ph19.gesehen(), 'Ausgangslage: keine Vergleichsgrundlage')
        pruefe(kat19._vergleichsgrundlage() == {'alter bauplan', 'neuer bauplan'},
               'ersatzweise gilt der vorhandene Katalog als Grundlage')
        pruefe('quantum drive' not in kat19._vergleichsgrundlage(),
               'was der Katalog nicht kennt, bleibt ein Zugang')

        # Ist die Grundlage vorhanden, gilt sie — und nicht der Katalog.
        ph19.gesehen_setzen({'alter bauplan'})
        pruefe(kat19._vergleichsgrundlage() == {'alter bauplan'},
               'die eigene Grundlage schlaegt den Katalog')

        # ⚠ Beim allerersten Katalogbau gibt es beides nicht — dann MUSS die
        # Grundlage leer bleiben, sonst staenden alle 738 als „neu" da.
        os.remove(kat19.pfade.app_datei('bauplaene-gesehen.json'))
        os.remove(_kat19)
        pruefe(kat19._vergleichsgrundlage() == set(),
               'beim allerersten Bau bleibt sie leer')

        # e) ⚠ Und wird das Nachziehen ueberhaupt angestossen? Die Funktion
        #    allein nuetzt nichts, wenn sie niemand ruft — und sie muss VOR dem
        #    Netz drankommen, sonst bleibt der Stempel aus, sobald die Leitung
        #    weg ist. Deshalb hier ohne Netz: Die Versionsabfrage wird
        #    stillgelegt, gestempelt werden muss trotzdem.
        _katalog_schreiben('4.10.0-live.2')
        _echte_version = kat19.aktuelle_version
        kat19.aktuelle_version = lambda: ''
        try:
            kat19.aktualisieren()
        finally:
            kat19.aktuelle_version = _echte_version
        pruefe(kat19.laden()['bauplaene']['neuer bauplan'].get('seit')
               == '4.10.0-live.2',
               'auch ohne Netz stempelt der Start nach')

        # ------------------------------------------------------------------
        # ⚠ Am 27.08.2026 antwortete „Auf Aktualität prüfen" mit
        # `name 'datei' is not defined` — ein Rückruf griff auf eine Variable
        # zu, die es in seiner Funktion nie gab. Python merkt das erst beim
        # **Klicken**; im Selbsttest lief die Zeile nie. Zwei weitere Fälle
        # derselben Art steckten still im Code (`os` im Bestandsfenster, `t`
        # statt `sprache.t` beim Ordner-Umzug) — beide in einem `except`
        # begraben, also unsichtbar.
        #
        # Ein undefinierter Name ist ohne Ausführen findbar. Genau das prüft
        # `pyflakes`. Fehlt es, wird die Prüfung übersprungen statt zu scheitern:
        # Der Selbsttest soll auf jedem Rechner laufen, auch ohne Zusatzpaket.
        print()
        print('20. Kein Zugriff auf Namen, die es nicht gibt')
        try:
            from pyflakes import api as _pfapi, reporter as _pfrep
        except ImportError:
            print('  [--]   pyflakes fehlt — Prüfung übersprungen '
                  '(pip install pyflakes)')
        else:
            import io as _io20
            _wurzel20 = os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))
            _aus, _err = _io20.StringIO(), _io20.StringIO()
            for _ort in ('scbp', 'tools', 'sc_bp_watcher.py'):
                _pfapi.checkRecursive([os.path.join(_wurzel20, _ort)],
                                      _pfrep.Reporter(_aus, _err))
            _offen = [z for z in _aus.getvalue().splitlines()
                      if 'undefined name' in z]
            for _z in _offen:
                print('         ' + _z.replace(_wurzel20 + os.sep, ''))
            pruefe(not _offen,
                   'kein undefinierter Name im ganzen Programm (%d gefunden)'
                   % len(_offen))

        # ------------------------------------------------------------------
        # ⚠ Am 27.08.2026 meldete gemeldet, dass bei „sehr gross" die Knoepfe
        # der Overlay-Wahl abgeschnitten sind. Ein benanntes Tk-Font wirkt
        # sofort auf jeden Text — aber die gezeichneten Rundknoepfe legen ihre
        # Leinwand beim Bauen **einmal** auf `schrift.measure(text)` fest.
        # Gemessen: 177 px Kasten, 206 px Text. 29 px fehlten.
        print()
        print('21. Groessere Schrift sprengt keine Knoepfe mehr')
        import tkinter as tk21
        import tkinter.font as tkfont21
        from scbp import seiten as se21
        from scbp.hauptfenster import Hauptfenster as HF21

        wurzel = _wurzel()
        _sch21 = tkfont21.Font(root=wurzel, family='Segoe UI', size=10)

        class _Traeger21:
            f_klein = _sch21

        _wahl21 = se21._wahl(_Traeger21(), tk21.Frame(wurzel),
                             [('popup', 'nur bei einem Neuzugang')],
                             'popup', lambda k: None)
        wurzel.update_idletasks()
        _vorher21 = _wahl21.winfo_children()[0].winfo_reqwidth()
        _sch21.configure(size=12)              # klein -> sehr gross
        wurzel.update_idletasks()
        _nachher21 = _wahl21.winfo_children()[0].winfo_reqwidth()
        _noetig21 = _sch21.measure('nur bei einem Neuzugang') + 26

        # a) Die Falle gibt es wirklich — sonst prueft (b) ins Leere.
        pruefe(_nachher21 == _vorher21 and _noetig21 > _nachher21,
               'ein fertiger Rundknopf waechst NICHT von allein (%d px fehlen)'
               % (_noetig21 - _nachher21))

        # b) Deshalb muss das Umstellen der Schriftgroesse neu aufbauen — und
        #    die Rueckmeldung DANACH sagen, sonst zerstoert der Aufbau sie.
        _ablauf21 = []

        class _Fenster21:
            f_grund = f_fett = f_klein = f_titel = f_zeichen = _sch21
            beim_schriftwechsel = None
            root = wurzel
            neu_aufbauen = lambda self: _ablauf21.append('aufbauen')
            sagen = lambda self, text: _ablauf21.append('sagen')

        HF21.schriftgroesse_setzen(_Fenster21(), 'gross')
        wurzel.update()                        # die `after`-Schlange abarbeiten
        pruefe(_ablauf21 == ['aufbauen', 'sagen'],
               'Schriftwechsel baut neu auf und meldet danach (%s)'
               % (' -> '.join(_ablauf21) or 'nichts passiert'))

        # c) ⚠ Die Mindestgroesse haengt an der Seitenleiste, die Seitenleiste
        #    an der Schrift. Ohne Nachziehen ragen bei „sehr gross" die unteren
        #    Eintraege („Star Citizen starten", „Kaffee spendieren", „Discord")
        #    aus dem Fenster — sie werden von unten gepackt und fallen heraus.
        #    Gerechnet wurde immer richtig; der Aufruf fehlte im Neuaufbau.
        import inspect as _ins21
        _quelle21 = _ins21.getsource(HF21.neu_aufbauen)
        pruefe('_mindesthoehe_nachziehen' in _quelle21,
               'der Neuaufbau zieht die Mindestgroesse nach')

        # d) ⚠ Die zwei Kanal-Kaesten muessen gleich gross sein. `pack` kann das
        #    nicht: Es verteilt nur den UEBERSCHUSS gleichmaessig, der laengere
        #    Text bleibt breiter. Nur `grid` mit `uniform` sagt Gleichheit zu.
        # ⚠ Ohne echte Fenstergroesse meldet Tk fuer beide Kaesten 1 Pixel —
        # dann waeren sie „gleich gross" und die Pruefung ginge immer durch.
        # Deshalb eine Groesse setzen und das Layout wirklich rechnen lassen.
        # ⚠ `_wurzel()` liefert ein verstecktes Fenster — ein verstecktes Fenster
        # rechnet Tk nicht aus, beide Kaesten meldeten 1 Pixel. Dann waeren sie
        # „gleich gross" und die Pruefung ginge immer durch. Also kurz zeigen.
        # ⚠ **Weit ausserhalb des Bildschirms** zeigen, nicht mittendrin.
        # Tk rechnet ein verstecktes Fenster nicht aus, gezeigt werden muss es
        # also — aber es muss niemand sehen. Der Selbsttest laeuft nach jeder
        # Aenderung, und jedes Mal sprang hier ein 1100x760-Fenster ueber den
        # Bildschirm und riss den Fokus mit. Gemeldet am 28.08.2026: „du hast
        # mich staendig aus dem rausgezogen was ich mache, den ganzen Abend
        # schon." Negative Koordinaten loesen das auf beiden Systemen.
        wurzel.geometry('1100x760+-4000+-4000')
        wurzel.attributes('-alpha', 0.0)
        wurzel.deiconify()
        _rahmen21 = tk21.Frame(wurzel)
        _rahmen21.pack(fill='both', expand=True)

        class _Traeger21b:
            f_klein = _sch21
            f_fett = _sch21
            version = '0.0.0'

        _t21 = _Traeger21b()
        se21._kanalkasten(_t21, _rahmen21, 'Kurz', 'Zwei Woerter.',
                          True, lambda: None, platz=0)
        se21._kanalkasten(_t21, _rahmen21, 'Deutlich laenger',
                          'Ein merklich laengerer Satz, der mehr Platz braucht '
                          'als der andere Kasten daneben.',
                          False, lambda: None, platz=1)
        wurzel.update()
        _br21 = [k.winfo_width() for k in _rahmen21.winfo_children()]
        _ho21 = [k.winfo_height() for k in _rahmen21.winfo_children()]
        # ⚠ Erst pruefen, dass ueberhaupt gezeichnet wurde. Sonst vergliche man
        # zwei Einsen und haette nichts geprueft.
        pruefe(len(_br21) == 2 and min(_br21) > 100,
               'die Kanal-Kaesten wurden wirklich gezeichnet (%s px)' % _br21)
        pruefe(len(_br21) == 2 and _br21[0] == _br21[1] and _ho21[0] == _ho21[1],
               'beide Kanal-Kaesten sind gleich gross (%s px breit, %s hoch)'
               % (_br21, _ho21))

        wurzel.withdraw()
        wurzel.destroy()

        print()
        print('26. Ein Absturz und die Bedienung hinterlassen eine Spur')
        # ⚠ Bomb20 meldete am 27.08.2026 einen reproduzierbaren Absturz beim
        # Oeffnen von "Was ist neu" — und sein Bericht wusste NICHTS davon. Die
        # Fehlerhaken fangen Python-Ausnahmen; ein harter Abbruch ist keine, und
        # die Spur endete beim letzten Startschritt.
        #
        # ⚠ Der erste Anlauf (rc74) hat den Fehler halb wiederholt: Start und
        # Bedienung landeten in EINEM Topf, der Bericht nahm die letzten zwoelf
        # Zeilen — fuenf Klicks genuegten, und der Startverlauf war weg.
        # Ein rc74-Bericht zeigte keinen einzigen Startschritt mehr.
        import os as os26
        from scbp import fehler as fe26
        from scbp import pfade as pf26

        ordner26 = os.path.join(basis, 'spur26')
        os26.makedirs(ordner26, exist_ok=True)
        alt_datei26 = pf26.app_datei
        try:
            pf26.app_datei = lambda name: os26.path.join(ordner26, name)
            if hasattr(fe26.spur, '_offen'):
                del fe26.spur._offen

            fe26.spur('Start, Version 3.0.0-test, testos')
            fe26.spur('Tk-Wurzel steht')
            # ⚠ Genau die Zeile, an der getrennt wird — nicht eine
            # nachgetippte Fassung davon. Bis rc42 stand hier
            # „Hauptschleife laeuft" ohne Umlaut; die Pruefung lief gruen,
            # obwohl das Programm etwas anderes schreibt.
            fe26.spur(fe26.SPUR_GRENZE)
            for _ in range(40):
                fe26.spur('Seite liste: bauen beginnt')
                fe26.spur('Seite liste: steht')

            start26, seiten26 = fe26.spur_geteilt()
            pruefe(len(start26) == 3,
                   'Start und Bedienung werden getrennt (%d Startzeilen)' % len(start26))
            pruefe(len(seiten26) == 80,
                   'die Seitenwechsel stehen vollstaendig da (%d)' % len(seiten26))

            # Und jetzt der Punkt, der in rc74 fehlte.
            fe26._spur_kuerzen(pf26.app_datei(fe26.SPUR_DATEI))
            start27, seiten27 = fe26.spur_geteilt()
            pruefe(len(start27) == 3,
                   'der Startverlauf ueberlebt das Kuerzen')
            pruefe(len(seiten27) == fe26.SPUR_REST,
                   'gekuerzt wird nur der Bedienteil (%d Zeilen)' % len(seiten27))

            # Der Absturzfaenger legt einen vorigen Lauf beiseite.
            with open(pf26.app_datei(fe26.ABSTURZ_DATEI), 'w', encoding='utf-8') as f26:
                f26.write('Current thread 0x0000 (most recent call first):\n')
            pruefe(fe26.absturzfaenger(), 'der Absturzfaenger laesst sich setzen')
            pruefe(len(fe26.letzter_absturz()) == 1,
                   'der Abbruch des vorigen Laufs ist lesbar')
            pruefe(fe26.absturz_abhaken() and not fe26.letzter_absturz(),
                   'und laesst sich abhaken')
        finally:
            pf26.app_datei = alt_datei26
            if hasattr(fe26.spur, '_offen'):
                del fe26.spur._offen

        # Beides muss auch wirklich im Bericht landen, sonst nuetzt es nichts.
        quelle26 = open(os.path.join(WURZEL, 'scbp', 'bericht.py'),
                        encoding='utf-8').read()
        pruefe("t('b_spur_seiten')" in quelle26,
               'der Bericht hat einen eigenen Abschnitt fuer die Seiten')
        pruefe("fehler.letzter_absturz" in quelle26,
               'und einen fuer den harten Abbruch')
        pruefe("'Seite diagnose' in seiten[-1]" in quelle26,
               'die Diagnose-Seite selbst steht nicht als letzte Zeile drin')
        quelle26b = open(os.path.join(WURZEL, 'scbp', 'hauptfenster.py'),
                         encoding='utf-8').read()
        # ⚠ Drei Stellen seit dem 28.08.2026: „bauen beginnt" beim ersten
        # Aufbauen, „zeigen" beim erneuten Einblenden, „steht" am Ende. Vorher
        # gab es die mittlere nicht — ging beim zweiten Besuch etwas schief,
        # fehlte die Zeile GANZ statt zur Haelfte, und der Bericht verspricht,
        # dass die letzte Zeile ohne „steht" die ist, an der es hing.
        pruefe(quelle26b.count("fehler.spur('Seite ") == 3,
               'jeder Seitenwechsel schreibt zwei Zeilen (bauen bzw. zeigen, dann steht)')
        pruefe("Seite %s: zeigen" in quelle26b,
               'auch der zweite Besuch hinterlaesst eine Spur')
        quelle26c = open(os.path.join(WURZEL, 'sc_bp_watcher.py'),
                         encoding='utf-8').read()
        pruefe('fehler.absturzfaenger()' in quelle26c,
               'der Faenger wird beim Start gesetzt')

        print()
        print('27. Angaben am Gegenstand: Kuerzel aus der Beschreibung')
        # ⚠ Die Fallen hier sind Datenfallen, keine Programmierfehler — sie
        # fallen nur auf, wenn man die echte `global.ini` daneben legt. Beim Bau
        # (27.08.2026) stand sechsmal `Individuell angefertigt` und dreimal
        # `N/A` im Feld Guetegrad; wer den ersten Buchstaben nimmt, schreibt
        # `(Ind/4/I)` in einen Spielnamen. So etwas sieht man erst im Spiel.
        from scbp import angaben as an27

        def besch27(**felder):
            """Eine Beschreibungszeile bauen — `\\n` ist die ZEICHENFOLGE."""
            return '\\n'.join('%s: %s' % (k, v) for k, v in felder.items())

        pruefe(an27.aus_beschreibung(
                   besch27(**{'Größe': 'S1', 'Gütegrad': 'A',
                              'Klasse': 'Military (Militär)'})) == '(Mil/1/A)',
               'Komponente wird zu Klasse/Groesse/Guete')
        pruefe(an27.aus_beschreibung(
                   besch27(**{'Größe': 'S2', 'Verfolgungssignal': 'Infrarot'}))
               == '(IR2)',
               'Rakete bekommt den Suchkopf, keine Fraktion')
        pruefe(an27.aus_beschreibung(
                   besch27(**{'Klasse': 'Ballistisch'})) == '(Bal)',
               'Waffe: die Klasse allein genuegt (FPS-Waffen haben keine Groesse)')
        pruefe(an27.aus_beschreibung(besch27(**{'Größe': 'S3'})) is None,
               'Groesse allein gibt KEINEN Zusatz (waere Laerm im Namen)')
        pruefe(an27.aus_beschreibung(
                   besch27(**{'Größe': 'S4', 'Gütegrad': 'Individuell angefertigt',
                              'Klasse': 'Industrial (Industrie)'})) == '(Ind/4/–)',
               'ein Guetegrad, den es nicht gibt, wird zum Strich')
        pruefe(an27.aus_beschreibung(
                   besch27(**{'Größe': 'S1', 'Gütegrad': 'N/A',
                              'Klasse': 'Zivil'})) == '(Civ/1/–)',
               '`N/A` ebenso — und die Kurzform `Zivil` wird erkannt')
        pruefe(an27.aus_beschreibung(
                   besch27(**{'Größe': 'S2 (Nur Fahrzeuge)',
                              'Klasse': 'Military', 'Gütegrad': 'B'}))
               == '(Mil/–/B)',
               'eine Groesse mit Zusatztext gehoert nicht ins Kuerzel')
        # Die Uebersetzung ist uneinheitlich: dieselbe Klasse in drei Formen.
        pruefe(len({an27.aus_beschreibung(
                        besch27(**{'Größe': 'S1', 'Gütegrad': 'C', 'Klasse': k}))
                    for k in ('Civilian (Zivil)', 'Zivil', 'Civilian')}) == 1,
               'alle drei Schreibweisen derselben Klasse ergeben dasselbe')
        pruefe(an27.zusatz_entfernen('Spark I-G Missile (CS1)')
               == 'Spark I-G Missile',
               'ein Zusatz des SC Deutsch Launchers wird abgeschnitten')
        pruefe(an27.zusatz_entfernen('Inspire Advanced (Ind/2/C)')
               == 'Inspire Advanced',
               'und der eigene ebenso — sonst stapeln sie sich')
        pruefe(an27.zusatz_entfernen('Omnisky III Cannon')
               == 'Omnisky III Cannon',
               'ein Name ohne Zusatz bleibt unangetastet')
        # Der ganze Weg: Tabelle aus Rohzeilen, ueber den gemeinsamen Stamm.
        zeilen27 = ['item_DescXY_Test=' + besch27(**{'Größe': 'S3',
                                                     'Gütegrad': 'B',
                                                     'Klasse': 'Stealth (Tarnung)'}),
                    'item_NameXY_Test=Testkuehler',
                    'item_NameOhne_Beschreibung=Einsam']
        tab27 = an27.tabelle_bauen(zeilen27)
        pruefe(tab27.get('item_NameXY_Test') == '(Sth/3/B)',
               'Beschreibung und Name finden ueber den Schluesselstamm zusammen')
        pruefe('item_NameOhne_Beschreibung' not in tab27,
               'ein Name ohne Beschreibung kommt nicht in die Tabelle')

        print()
        print('28. Ohne Launcher: Ordner und user.cfg entstehen selbst')
        # ⚠ Gemeldet am 27.08.2026: „das hat bei mir und meinem bruder nur
        # geklappt WEIL wir vorher den launcher hatten von sc deutsch." Genau
        # das ist der ungetestete Fall — wer den SC Deutsch Launcher nie hatte,
        # hat **keinen** Ordner `data/Localization/<sprache>/`, und ohne den
        # landet die Datei irgendwo, wo Star Citizen sie nicht sucht.
        #
        # Dazu die Tonspur: Star Citizen hat **keine deutsche Sprachausgabe**.
        # Ohne `g_languageAudio = english` neben der deutschen Textsprache
        # fehlt der Ton. Der Launcher setzt beides, also müssen wir es auch.
        from scbp import uebersetzung as ue28
        frisch28 = os.path.join(basis, 'frischeinstallation', 'LIVE')
        os.makedirs(frisch28)
        open(os.path.join(frisch28, 'Data.p4k'), 'w').close()

        ziel28 = ue28.ziel_ini('german_(germany)', frisch28)
        pruefe(ziel28.endswith(os.path.join('data', 'Localization',
                                            'german_(germany)', 'global.ini')),
               'der Zielpfad steht dort, wo Star Citizen sucht')
        os.makedirs(os.path.dirname(ziel28), exist_ok=True)
        pruefe(os.path.isdir(os.path.dirname(ziel28)),
               'die ganze Ordnerkette entsteht ohne Launcher')

        ue28.user_cfg_setzen('german_(germany)', 'english', frisch28)
        cfg28 = open(os.path.join(frisch28, 'user.cfg'), encoding='utf-8').read()
        pruefe('g_language = german_(germany)' in cfg28,
               'g_language wird gesetzt — sonst liest das Spiel die Datei nicht')
        pruefe('g_languageAudio = english' in cfg28,
               'g_languageAudio = english MUSS mit rein (SC hat keinen deutschen Ton)')

        # Eine vorhandene user.cfg voller Grafikeinstellungen darf das nicht
        # verlieren — dort steht die Arbeit des Spielers drin.
        cfgpfad28 = os.path.join(frisch28, 'user.cfg')
        with open(cfgpfad28, 'w', encoding='utf-8') as f28:
            f28.write('r_DisplayInfo = 3\nsys_maxfps = 0\n'
                      'g_language = english\n')
        ue28.user_cfg_setzen('german_(germany)', 'english', frisch28)
        cfg28b = open(cfgpfad28, encoding='utf-8').read()
        pruefe('r_DisplayInfo = 3' in cfg28b and 'sys_maxfps = 0' in cfg28b,
               'vorhandene Grafikeinstellungen bleiben unangetastet')
        pruefe('g_language = english' not in cfg28b,
               'eine alte Sprachzeile wird ersetzt, nicht verdoppelt')
        pruefe(cfg28b.count('g_language =') == 1,
               'g_language steht genau einmal da')

        # Der Weg ueber die EINSTELLUNGEN (Assistent abgebrochen) muss dasselbe
        # tun wie der Assistent. Beide laufen ueber `uebersetzung.holen()`.
        quelle28 = open(os.path.join(WURZEL, 'scbp', 'uebersetzung.py'),
                        encoding='utf-8').read()
        holen28 = quelle28[quelle28.index('def holen('):]
        holen28 = holen28[:holen28.index('\ndef ', 1)] if '\ndef ' in holen28[1:] else holen28
        pruefe('os.makedirs(' in holen28,
               'holen() legt die Ordnerkette selbst an')
        pruefe('user_cfg_setzen(' in holen28,
               'holen() setzt die user.cfg — auch wenn der Assistent uebersprungen wurde')
        pruefe(ue28.QUELLEN['deutsch']['ton'] == 'english',
               'die deutsche Quelle bringt den englischen Ton mit')

        # StarStrings (MrKraken) ist derselbe Fall — nur mit englischem
        # Zielordner. Gemeldet: „ist ja wie die deutsche im grunde."
        ss28 = os.path.join(basis, 'starstringsprobe', 'LIVE')
        os.makedirs(ss28)
        ziel_ss = ue28.ziel_ini(ue28.QUELLEN['starstrings']['sprache'], ss28)
        pruefe(ziel_ss.endswith(os.path.join('data', 'Localization',
                                             'english', 'global.ini')),
               'StarStrings landet im englischen Ordner, ebenfalls selbst angelegt')
        ue28.user_cfg_setzen(ue28.QUELLEN['starstrings']['sprache'],
                             ue28.QUELLEN['starstrings']['ton'], ss28)
        cfg_ss = open(os.path.join(ss28, 'user.cfg'), encoding='utf-8').read()
        pruefe('g_language = english' in cfg_ss,
               'auch StarStrings traegt seine Sprache in die user.cfg ein')

        # ⚠ Der Wechsel deutsch → StarStrings: Die Tonzeile stammt aus der
        # deutschen Einrichtung und muss stehen bleiben. `ton` ist bei
        # StarStrings None — eine Fassung, die dabei alles anfasst, wuerde sie
        # verlieren, und der Spieler saesse ohne Ton da.
        with open(os.path.join(ss28, 'user.cfg'), 'w', encoding='utf-8') as f_ss:
            f_ss.write('g_language = german_(germany)\n'
                       'g_languageAudio = english\n'
                       'r_VSync = 0\n')
        ue28.user_cfg_setzen('english', None, ss28)
        cfg_ss2 = open(os.path.join(ss28, 'user.cfg'), encoding='utf-8').read()
        pruefe('g_language = english' in cfg_ss2,
               'beim Wechsel wird die Textsprache umgestellt')
        pruefe('g_languageAudio = english' in cfg_ss2,
               'die Tonzeile ueberlebt den Wechsel (ton=None fasst sie nicht an)')
        pruefe('r_VSync = 0' in cfg_ss2,
               'und die Grafikeinstellung ebenso')

        # ⚠ Der dritte Weg — und der eigentliche „ohne Launcher"-Fall: Wer
        # **englisch original** spielt, will vielleicht nur die Angaben am
        # Gegenstand und gar keine Übersetzung. Der hat **gar keine**
        # `global.ini` auf der Platte, nur die `Data.p4k`. Ohne `g_language`
        # liest Star Citizen eine dort abgelegte Datei nicht einmal an.
        # Gemeldet: „sonst kann man das nie ohne eine übersetzung nutzen."
        from scbp import spieltexte as st28
        quelle_st = open(os.path.join(WURZEL, 'scbp', 'spieltexte.py'),
                         encoding='utf-8').read()
        pruefe('_sprache_eintragen(' in quelle_st,
               'holen() traegt g_language selbst ein, nicht der Aufrufer')
        pruefe(quelle_st.count('_sprache_eintragen(sprache, spielordner)') >= 2,
               'auch wenn die Datei schon da war — sonst bleibt sie ungelesen')
        # Kein Aufrufer darf sich mehr darauf verlassen, es selbst zu tun.
        for datei_st in ('assistent.py', 'einstellungsfenster.py'):
            inhalt_st = open(os.path.join(WURZEL, 'scbp', datei_st),
                             encoding='utf-8').read()
            block_st = inhalt_st[inhalt_st.index('spieltexte.holen('):][:900]
            pruefe('user_cfg_setzen(' not in block_st,
                   '%s verlaesst sich auf holen(), statt es zu wiederholen'
                   % datei_st)
        # Und der englische Zielordner entsteht genauso von selbst.
        orig28 = os.path.join(basis, 'englischoriginal', 'LIVE')
        os.makedirs(orig28)
        ziel_or = ue28.ziel_ini('english', orig28)
        os.makedirs(os.path.dirname(ziel_or), exist_ok=True)
        st28._sprache_eintragen('english', orig28)
        cfg_or = open(os.path.join(orig28, 'user.cfg'), encoding='utf-8').read()
        pruefe('g_language = english' in cfg_or,
               'englisch original: g_language wird ebenfalls gesetzt')

        print()
        print('29. Bedienelemente stehen einheitlich — Symmetrie')
        # ⚠ Gemeldet am 27.08.2026: „im gleichen tab sind die einstellings
        # schalter mal mittig mal rechts, das muss einheitlich sein, im gesamten
        # projekt gilt das natuerlich." Und: „Symetrie ist fuer mich EXTREM
        # wichtig bei eigentlich allem."
        #
        # Woher der Unterschied kam: `_feld(..., breit=True)` legt das
        # Bedienelement UNTER die Beschreibung, ueber die volle Breite — ein
        # `.pack()` ohne Anker sitzt darin **mittig**. Ohne `breit` steht es
        # rechts neben dem Text. Auf der Seite „Texte im Spiel" standen dadurch
        # drei Schiebeschalter untereinander: mittig, rechts, mittig.
        #
        # `breit=True` ist fuer BREITE Bedienelemente da (Knopfreihen, die auf
        # Englisch sonst abgeschnitten werden). Ein Schiebeschalter ist schmal
        # und gehoert nach rechts — wie in jeder Einstellungsliste.
        import re as _re29
        quelle29 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                        encoding='utf-8').read().split('\n')

        def _aufruf29(zeilen, start):
            """Der VOLLSTAENDIGE `_feld(...)`-Aufruf ab `start`.

            ⚠ Nicht bei der ersten `)` abschneiden — die schliesst `t('...')`,
            und `breit=True` steht dahinter. Genau daran ist die erste Fassung
            dieser Pruefung gescheitert: Sie meldete brav 0 Ausreisser, auch
            als absichtlich einer eingebaut wurde. Deshalb zaehlen."""
            text, tiefe = '', 0
            for _z in zeilen[start:start + 4]:
                for _c in _z:
                    text += _c
                    if _c == '(':
                        tiefe += 1
                    elif _c == ')':
                        tiefe -= 1
                        if tiefe == 0:
                            return text
                text += ' '
            return text

        offen29, falsch29 = None, []
        for _i29, _z29 in enumerate(quelle29):
            _m29 = _re29.search(r"_feld\(fenster, \w+, t\('([^']+)'\)", _z29)
            if _m29:
                _ab29 = _z29.index('_feld(') + 5
                _voll29 = _aufruf29([_z29[_ab29:]] + quelle29[_i29 + 1:], 0)
                offen29 = (_m29.group(1), 'breit=True' in _voll29, _i29 + 1)
            elif 'schiebeschalter(' in _z29 and offen29:
                if offen29[1]:
                    falsch29.append('%s (Zeile %d)' % (offen29[0], offen29[2]))
                offen29 = None
        for _f29 in falsch29:
            print('       mittig statt rechts: ' + _f29)
        pruefe(not falsch29,
               'jeder Schiebeschalter steht rechts, keiner mittig (%d Ausreisser)'
               % len(falsch29))

        print()
        print('30. Nur noch der Installer — und v2.0.0 kommt trotzdem mit')
        # Entscheidung Gemeldet am 27.08.2026: „ich will die exe ohne install
        # loswerden … sie belastet mich nur und war damals deine Entscheidung,
        # als wir sagten, wir machen es so, um Vertrauen aufzubauen. ABER das
        # haben wir doch schon, nun wollen wir es funktionierend. Und einfach."
        #
        # Zwei Auslieferungswege heissen zwei Fehlerquellen und doppelte
        # Unterstuetzung. Ab v3.0.0 gibt es unter Windows nur den Installer.
        #
        # ⚠ Der Haken, den das aufwirft: **v2.0.0 gab es NUR als nackte .exe.**
        # Ihre Update-Logik nimmt die erste Datei auf `.exe` — jetzt also den
        # Installer. Das ging frueher schief, weil die alte `einspielen()` den
        # Fund roh ueber das laufende Programm schob. ABER ihr Hilfsskript
        # startet die getauschte Datei anschliessend (`start "" "<ziel>"`) —
        # der Installer laeuft also und richtet alles ein. Was frueher der
        # Fehler war, ist jetzt der Weg hinaus.
        from scbp import aktualisierung as ak30
        yml30 = open(os.path.join(WURZEL, '.github', 'workflows',
                                  'release.yml'), encoding='utf-8').read()
        anhang30 = yml30[yml30.index('files: |'):][:400]
        pruefe('SC-BP-Watcher-Setup.exe' in anhang30,
               'der Installer haengt am Release')
        pruefe('windows/SC-BP-Watcher.exe' not in anhang30,
               'die nackte .exe haengt NICHT mehr daran')
        pruefe('AppImage' in anhang30,
               'Linux bekommt weiter sein AppImage')
        # Was gebaut wird, muss zu dem passen, was gesucht wird.
        iss30 = open(os.path.join(WURZEL, 'packaging', 'installer.iss'),
                     encoding='utf-8').read()
        pruefe('OutputBaseFilename=SC-BP-Watcher-Setup' in iss30,
               'der Installer heisst so, wie rc39-rc75 ihn suchen')
        pruefe(ak30.WINDOWS_INSTALLER[0] == '-setup.exe',
               'und die Suche faengt genau damit an')
        # Der Weg von v2.0.0: erste Datei auf .exe — das MUSS der Installer sein.
        anhaenge30 = sorted(['SC-BP-Watcher-Setup.exe',
                             'SC-BP-Watcher-x86_64.AppImage'])
        erste_exe30 = next((n for n in anhaenge30
                            if n.lower().endswith('.exe')), None)
        pruefe(erste_exe30 == 'SC-BP-Watcher-Setup.exe',
               'v2.0.0 greift den Installer — und startet ihn (%s)' % erste_exe30)
        # ⚠ Und der Installer muss dorthin, wo das Programm liegt: sonst
        # entsteht eine zweite Fassung neben der alten Datei.
        ak30q = open(os.path.join(WURZEL, 'scbp', 'aktualisierung.py'),
                     encoding='utf-8').read()
        start30 = ak30q[ak30q.index("schalter = '/SILENT"):][:1400]
        pruefe('/DIR=' in start30,
               'der Installer bekommt /DIR — ersetzen statt danebenlegen')
        pruefe('sys.executable' in start30,
               'und zwar den Ordner des laufenden Programms')

        print()
        print('31. Das Schloss holt einen aus dem Durchreichen zurueck')
        # ⚠ Gemeldet am 27.08.2026: „der zweite Programmstart ist die denkbar
        # duemmste Loesung, weil man dann raustabben muss aus dem Spiel."
        #
        # Und er hat recht: Wer Klicks durchreichen laesst, will im Spiel
        # bleiben. Bis dahin fuehrte der einzige Rueckweg genau dort hinaus.
        # Ryze loest es beim TeamSpeak-Plugin mit einem Schloss, das anklickbar
        # bleibt — dasselbe macht jetzt ein eigenes kleines Fenster, das nie
        # durchlaessig gemacht wird.
        from scbp import overlay as ov31
        pruefe(hasattr(ov31, 'SCHLOSS_RUECKRUF'),
               'overlay kennt den Rueckruf fuers Schloss')
        # Der Rueckruf MUSS beim Umschalten kommen — sonst bliebe das Schloss
        # stehen, obwohl niemand mehr durchklickt (oder umgekehrt).
        gerufen31 = []
        alt31 = ov31.SCHLOSS_RUECKRUF[0]
        ov31.SCHLOSS_RUECKRUF[0] = lambda an: gerufen31.append(an)
        try:
            ov31.durchklickbar_setzen(None, False)
        except Exception:
            pass
        ov31.SCHLOSS_RUECKRUF[0] = alt31
        pruefe(len(gerufen31) == 1,
               'jedes Umschalten meldet sich beim Schloss (%d Rufe)' % len(gerufen31))
        # ⚠ Scheitert das Durchreichen, darf KEIN Schloss stehen — es waere ein
        # Schloss an einer Tuer, die offen ist.
        pruefe(gerufen31 == [False],
               'ohne wirksames Durchreichen kommt auch kein Schloss')
        # Ein Rueckruf, der wirft, darf das Schalten nicht kippen.
        ov31.SCHLOSS_RUECKRUF[0] = lambda an: 1 / 0
        try:
            ov31.durchklickbar_setzen(None, False)
            heil31 = True
        except ZeroDivisionError:
            heil31 = False
        ov31.SCHLOSS_RUECKRUF[0] = alt31
        pruefe(heil31, 'ein Fehler im Schloss reisst das Umschalten nicht mit')
        # Die Symbole muessen da sein — sonst ist das Schloss unsichtbar, und
        # genau das ist heute schon einmal passiert (das X im Herkunftskasten).
        for name31 in ('schloss_zu', 'schloss_auf'):
            pfad31 = os.path.join(WURZEL, 'assets', 'symbole', '18',
                                  name31 + '-gruen.png')
            pruefe(os.path.isfile(pfad31), 'Symbol %s liegt in 18 px vor' % name31)
        from scbp import sprache as sp31
        for schl31 in ('hinweis_schloss', 'ov_schloss_offen'):
            pruefe(bool(sp31.t(schl31)) and schl31 not in sp31.t(schl31),
                   'Text %s ist gesetzt, nicht der Schluesselname' % schl31)

        print()
        print('32. Die Log-Erkennung kennt UNSERE eigenen Zusaetze')
        # ⚠ Der gefaehrlichste Fehler dieser Nacht, gefunden am 28.08.2026 beim
        # Nachgehen einer Frage von Morkhan.
        #
        # Seit rc76 schreibt das Werkzeug die Angaben selbst an die
        # Gegenstandsnamen (`scbp/angaben.py`). Das Spiel schreibt den Namen
        # anschliessend **mitsamt Zusatz** in die Game.log:
        #
        #     Bauplan erhalten: Spectre (Sth/1/A)
        #
        # `SUFFIX_RE` kannte aber nur `Civ|Mil|Ind|Sth|Cmp` mit Grad `A-D` —
        # also genau die Form, die der SC Deutsch Launcher erzeugte. Alles, was
        # wir zusaetzlich schreiben, blieb am Namen kleben: Der Bauplan landet
        # unter falschem Namen im Bestand und wird **nie abgehakt**.
        #
        # Betroffen waeren 344 Waffen und 62 Raketen gewesen — und niemand
        # haette es gemerkt, weil das Werkzeug ja etwas anzeigt.
        from scbp.logquelle import teile_namen as tn32
        faelle32 = [
            ('Spectre (Sth/1/A)',            'Spectre'),
            ('7CA \'Nargun\' (Civ/3/A)',      "7CA 'Nargun'"),
            ('Omnisky III Cannon (Las/2/A)', 'Omnisky III Cannon'),
            ('Inspire Advanced (Ind/2/C)',   'Inspire Advanced'),
            ('P4-AR Rifle (Bal)',            'P4-AR Rifle'),
            ('Arrowhead Sniper Rifle (Las)', 'Arrowhead Sniper Rifle'),
            ("'Arrow' I Missile (IR1)",      "'Arrow' I Missile"),
            ('Argos IX Torpedo (CS9)',       'Argos IX Torpedo'),
            ('Pioneer I-G Missile (EM1)',    'Pioneer I-G Missile'),
            ('Glacis (Ind/4/\u2013)',          'Glacis'),
            ('V60-26 (Mil/\u2013/B)',          'V60-26'),
        ]
        for roh32, erwartet32 in faelle32:
            pruefe(tn32(roh32)[0] == erwartet32,
                   'abgeschnitten: %s' % roh32)
        # ⚠ Und die Gegenrichtung: Echte Namensklammern duerfen NICHT fallen.
        # Sonst hiesse „Singe Cannon (S2)" plötzlich nur noch „Singe Cannon",
        # und zwei verschiedene Waffen waeren derselbe Eintrag.
        for roh32 in ('Singe Cannon (S2)', 'Irgendwas (30 cap)',
                      'Ding (Alpha/1/A)', 'Sache (Mil/1/Z)'):
            pruefe(tn32(roh32)[0] == roh32,
                   'unangetastet: %s' % roh32)
        # Die Kuerzel-Liste MUSS zu angaben.py passen — sonst reisst genau
        # diese Luecke beim naechsten neuen Kuerzel wieder auf.
        from scbp import angaben as an32, logquelle as lq32
        for _teile32, kurz32 in an32.KLASSEN:
            pruefe(kurz32.lower() in lq32._KUERZEL.lower(),
                   'logquelle kennt das Kuerzel %s aus angaben.py' % kurz32)

        print()
        print('33. Bestand und Liste finden zueinander, egal woher der Name kam')
        # ⚠ Der Fehler, der Morkhans leere Kaestchen erklaert (28.08.2026).
        #
        # `pfade.namensform()` nennt sich selbst „die EINZIGE Stelle" fuer
        # Vergleichsschluessel — schnitt den Klassen-Zusatz aber nicht ab. Das
        # tat nur `logquelle.teile_namen()`. Also:
        #
        #     aus der Game.log:        'xl-1'            ✅ geschnitten
        #     aus der Launcher-Datei:  'xl-1 (mil/2/a)'  ❌ ungeschnitten
        #     aus einem Import:        'xl-1 (mil/2/a)'  ❌ ungeschnitten
        #
        # Zwei Schluessel, die nie zueinander finden: Der Bauplan galt als
        # fehlend, obwohl er im Bestand stand. Betroffen war jeder, der seinen
        # Stand aus dem SC Deutsch Launcher oder einer Sicherung mitbrachte —
        # also genau die Leute, die schon laenger spielen.
        from scbp.pfade import namensform as nfm33
        gleich33 = [
            ('XL-1 (Mil/2/A)',            'XL-1'),
            ('7CA \'Nargun\' (Civ/3/A)',   "7CA 'Nargun'"),
            ('7MA "Lorica" (Civ/3/B)',    "7MA 'Lorica'"),
            ('P4-AR Rifle (Bal)',         'P4-AR Rifle'),
            ("'Arrow' I Missile (IR1)",   "'Arrow' I Missile"),
            ('Argos IX Torpedo (CS9)',    'Argos IX Torpedo'),
            ('Glacis (Ind/4/\u2013)',       'Glacis'),
            ('V60-26 (Mil/\u2013/B)',       'V60-26'),
        ]
        for mit33, ohne33 in gleich33:
            pruefe(nfm33(mit33) == nfm33(ohne33),
                   'mit und ohne Kuerzel derselbe Schluessel: %s' % mit33)
        # ⚠ Gegenrichtung: Echte Namensklammern MUESSEN bleiben, sonst waeren
        # zwei verschiedene Waffen plötzlich derselbe Eintrag.
        for roh33 in ('Singe Cannon (S2)', 'Ding (Alpha/1/A)'):
            pruefe(nfm33(roh33) == roh33.lower(),
                   'unangetastet: %s' % roh33)
        # ⚠ Die Mengenangabe ist der Sonderfall: Das WORT faellt weg, die ZAHL
        # bleibt. Sonst zaehlt derselbe Bauplan doppelt, sobald das Spiel auf
        # Deutsch laeuft (gemessen 29.08.2026: 405 angezeigt, 403 echt).
        pruefe(nfm33('Ravager-212 Magazine (16 cap)')
               == nfm33('Ravager-212 Magazine (16 Schuss)'),
               'deutsch und englisch ergeben denselben Schluessel')
        pruefe(nfm33('Irgendwas (30 cap)') == 'irgendwas (30)',
               'die Zahl bleibt stehen, nur das Wort faellt weg')
        pruefe(nfm33('Magazin (40 cap)') != nfm33('Magazin (60 cap)'),
               'verschiedene Kapazitaeten bleiben verschiedene Bauplaene')
        pruefe(nfm33('Singe Cannon (S1)') != nfm33('Singe Cannon (S2)'),
               'Klammern ohne fuehrende Ziffer bleiben unangetastet')
        # ⚠ Und der wichtigste Teil: Ein **schon gespeicherter** Bestand muss
        # mitziehen. `namensform()` zu reparieren hilft nur neuen Eintraegen —
        # Morkhans 320 Bauplaene lagen mit den alten Schluesseln auf der Platte.
        import json as js33, tempfile as tf33, shutil as sh33
        heim33 = tf33.mkdtemp(prefix='bestand33-')
        alt_heim33 = os.environ.get('SC_BP_HOME')
        os.environ['SC_BP_HOME'] = heim33
        try:
            import importlib as im33
            from scbp import pfade as pf33
            im33.reload(pf33)
            from scbp import bestand as be33
            im33.reload(be33)
            with open(be33.pfad(), 'w', encoding='utf-8') as f33:
                js33.dump({'version': 1, 'stand': '2026-08-01 12:00:00',
                           'bauplaene': {
                               'xl-1 (mil/2/a)': {'name': 'XL-1 (Mil/2/A)',
                                                  'quelle': 'launcher',
                                                  'zeit': '2026-08-01 10:00:00'},
                               'guardian (ind/1/b)': {'name': 'Guardian (Ind/1/B)',
                                                      'quelle': 'launcher',
                                                      'zeit': '2026-08-05 09:00:00'},
                               'guardian': {'name': 'Guardian', 'quelle': 'log',
                                            'zeit': '2026-08-02 08:00:00'},
                               'ravager-212 magazine (16 cap)': {
                                   'name': 'Ravager-212 Magazine (16 cap)',
                                   'quelle': 'launcher', 'zeit': '2026-08-03 07:00:00'},
                               'ravager-212 magazine (16 schuss)': {
                                   'name': 'Ravager-212 Magazine (16 Schuss)',
                                   'quelle': 'nachlese', 'zeit': '2026-08-04 07:00:00'},
                           }}, f33, ensure_ascii=False)
            d33 = be33.laden()
            pruefe('xl-1' in d33['bauplaene'],
                   'ein gespeicherter Schluessel mit Kuerzel zieht um')
            pruefe('xl-1 (mil/2/a)' not in d33['bauplaene'],
                   'und der alte bleibt nicht daneben stehen')
            pruefe(len([k for k in d33['bauplaene'] if k.startswith('guardian')]) == 1,
                   'eine Dublette wird zu einem Eintrag zusammengefuehrt')
            pruefe(d33['bauplaene']['guardian'].get('zeit') == '2026-08-02 08:00:00',
                   'dabei gewinnt der aeltere Fund, nicht der zuletzt gelesene')
            pruefe(d33.get('version') == be33.DATEI_VERSION,
               'die Datei-Version wird hochgesetzt')
            # ⚠ Nur EINMAL umziehen — sonst schreibt jeder Start die Datei neu.
            auf_platte33 = js33.load(open(be33.pfad(), encoding='utf-8'))
            pruefe(auf_platte33.get('version') == be33.DATEI_VERSION,
                   'der Umzug wird auf die Platte geschrieben, nicht nur gedacht')
            # ⚠ Und der Umzug muss die Sprach-Dublette einsammeln — genau die,
            # die am 29.08.2026 in einem echten Bestand lag. Nur `namensform()` zu
            # reparieren haette den gespeicherten Bestand nicht angefasst.
            pruefe(len([k for k in d33['bauplaene']
                        if k.startswith('ravager-212')]) == 1,
                   'die deutsche und die englische Fassung werden zusammengefuehrt')
        finally:
            if alt_heim33 is None:
                os.environ.pop('SC_BP_HOME', None)
            else:
                os.environ['SC_BP_HOME'] = alt_heim33
            sh33.rmtree(heim33, ignore_errors=True)
            im33.reload(pf33)
            im33.reload(be33)

        # Und der Weg, um den es eigentlich geht: Ein Bestand aus der
        # Launcher-Datei muss die Liste abhaken koennen.
        from scbp import katalog as kat33
        habe33 = {nfm33('XL-1 (Mil/2/A)'), nfm33('Siren (Mil/1/B)')}
        pruefe(kat33._norm('XL-1') in habe33,
               'ein Launcher-Bestand hakt die Bauplan-Liste ab')
        pruefe(kat33._norm('Siren') in habe33,
               'und zwar fuer jeden Namen, nicht nur zufaellig einen')

        print()
        print('34. Fehlerbericht absenden — ein Knopf statt einer Erklaerstunde')
        # ⚠ Gemeldet am 28.08.2026: „ich will nicht jedem eine Stunde erklaeren,
        # wie ich zu dem Bericht komme, das ist nervenaufreibend." Und sein
        # Bruder, um den es ging: „weil ich kein nerd bin … ich installiere und
        # es funktioniert, wenn nicht, unbrauchbar."
        #
        # Kopieren und in Discord einfuegen scheitert dreifach: Der Bericht
        # steckt unter „Fortgeschritten", er ist zu lang fuer eine Nachricht,
        # und man muss wissen, wohin damit.
        from scbp import berichtziel as bz34, bericht as be34
        pruefe(bz34.ziel() == '',
               'im Repo steht KEINE Adresse — sie ist ein Geheimnis')
        pruefe(not bz34.moeglich(),
               'ohne Adresse meldet moeglich() sauber False')
        # ⚠ Der Knopf wird trotzdem GEZEIGT — er sagt beim Druecken, was fehlt.
        # Ihn auszublenden traf nur den Quellcode, also den Entwickler selbst:
        # „nicht mal ICH finde den" (28.08.2026). Ein fehlender Knopf sieht aus
        # wie ein Fehler.
        quelle34 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                        encoding='utf-8').read()
        stelle34 = quelle34[quelle34.index("s_di_absenden"):][:200]
        pruefe('if ' not in stelle34.split(chr(10))[0],
               'der Knopf haengt an keiner Bedingung')
        ok34, grund34 = be34.absenden('Probe', '3.0.0-test')
        pruefe(ok34 is False, 'ohne Ziel wird nichts gesendet')
        pruefe('http' not in grund34.lower(),
               'und die Meldung verraet die Adresse nicht')
        # ⚠ Der Bau MUSS die Datei ersetzen — sonst hat niemand den Knopf.
        yml34 = open(os.path.join(WURZEL, '.github', 'workflows',
                                  'release.yml'), encoding='utf-8').read()
        pruefe(yml34.count('scbp/berichtziel.py') >= 2,
               'Windows UND Linux setzen das Ziel beim Bau ein')
        pruefe('BERICHT_WEBHOOK' in yml34,
               'und zwar aus dem Secret, nicht aus dem Quelltext')
        # Die Adresse darf nirgends im Repo stehen.
        for _wo34, _unter34, _dateien34 in os.walk(os.path.join(WURZEL, 'scbp')):
            for _d34 in _dateien34:
                if not _d34.endswith('.py'):
                    continue
                _inh34 = open(os.path.join(_wo34, _d34),
                              encoding='utf-8', errors='ignore').read()
                pruefe('discord.com/api/webhooks' not in _inh34,
                       'keine Webhook-Adresse in scbp/%s' % _d34)

        print()
        print('35. Ein Textfeld rollt sich selbst, nicht die Seite dahinter')
        # ⚠ Von zwei Leuten unabhaengig gemeldet (28.08.2026): Im Bericht auf
        # der Diagnose-Seite liess sich erst rollen, NACHDEM man die ganze
        # Seite nach unten geschoben hatte. Das Rad ging an die Rollflaeche
        # dahinter, weil ein `tk.Text` keine registrierte Flaeche ist.
        from scbp import hauptfenster as hf35
        import tkinter as tk35
        w35 = tk35.Tk()
        # ⚠ Zeigen, sonst rechnet Tk das Layout nicht — `yview()` liefert dann
        # (0.0, 0.0), und jedes Feld saehe nach Ueberlauf aus. Weit ausserhalb
        # des Bildschirms und durchsichtig, damit niemand es sieht (siehe 23).
        w35.geometry('300x200+-4000+-4000')
        w35.attributes('-alpha', 0.0)
        w35.deiconify()
        try:
            rahmen35 = tk35.Frame(w35)
            rahmen35.pack(fill='both', expand=True)
            feld35 = tk35.Text(rahmen35, height=3)
            feld35.pack()
            # Kurzer Inhalt: passt hinein, also soll die SEITE rollen.
            feld35.insert('1.0', 'kurz')
            # ⚠ `update()`, nicht nur `update_idletasks()`. Unter Windows
            # rechnet Tk das Layout eines Fensters ausserhalb des Bildschirms
            # sonst nicht zu Ende: `yview()` gibt dann (0.0, 0.0), das sieht
            # wie Ueberlauf aus, und die Pruefung schlug im Bau fehl, obwohl
            # sie hier gruen war (28.08.2026).
            w35.update()
            oben35, unten35 = feld35.yview()
            if (unten35 - oben35) <= 0.0:
                # Tk hat trotzdem nicht gerechnet — dann ist hier nichts zu
                # pruefen. Lieber offen ueberspringen als falschen Alarm geben.
                print('  [--]   Tk rechnet dieses Fenster nicht durch — '
                      'Rollpruefung uebersprungen')
            else:
                pruefe(hf35._eigenes_rollen(feld35, rahmen35) is None,
                       'ein Feld ohne Ueberlauf gibt das Rad an die Seite weiter')
            # Langer Inhalt: laeuft ueber, also gehoert ihm das Rad.
            feld35.insert('end', '\n'.join('Zeile %d' % i for i in range(60)))
            w35.update()
            pruefe(hf35._eigenes_rollen(feld35, rahmen35) is feld35,
                   'ein ueberlaufendes Feld rollt sich selbst')
            # Und Widgets ohne Textfeld dazwischen aendern nichts.
            marke35 = tk35.Label(rahmen35, text='x')
            pruefe(hf35._eigenes_rollen(marke35, rahmen35) is None,
                   'eine Beschriftung faengt das Rad nicht ab')
        finally:
            w35.destroy()

        print()
        print('36. Der Reiter „Fehler melden“ faellt auf, ohne zu luegen')
        # ⚠ Zwei Stufen, damit Rot etwas bedeutet (Entscheidung 28.08.2026):
        #   * Das Wort ist IMMER rot — wer ein Problem hat, soll den Reiter
        #     finden, ohne ein Menue zu durchsuchen.
        #   * Das Symbol wird NUR rot, wenn wirklich Fehler mitgeschrieben
        #     wurden. Sonst stuende der Reiter dauerhaft auf Alarm, obwohl
        #     alles laeuft — und niemand naehme ihn noch ernst.
        quelle36 = open(os.path.join(WURZEL, 'scbp', 'hauptfenster.py'),
                        encoding='utf-8').read()
        stelle36 = quelle36[quelle36.index('def _reiter_faerben'):][:2200]
        pruefe("rot = (kennung == 'diagnose')" in stelle36,
               'der Reiter diagnose wird gesondert behandelt')
        pruefe('_fehler_liegen_an()' in stelle36,
               'das Symbol haengt an tatsaechlichen Fehlern, nicht am Reiter')
        pruefe('fg=ROT if rot' in stelle36,
               'das Wort ist unabhaengig davon rot')
        # Die Farbe muss es als Bild wirklich geben, sonst bleibt es unsichtbar
        # — genau so ist heute Nacht schon einmal ein X verschwunden.
        from scbp import zeichen as zi36
        pruefe(zi36.ROT == 'rot', 'zeichen kennt die Farbe rot')
        for n36 in ('diagnose',):
            pfad36 = os.path.join(WURZEL, 'assets', 'symbole', '22',
                                  n36 + '-rot.png')
            pruefe(os.path.isfile(pfad36),
                   'das Symbol %s liegt in Rot vor' % n36)
        # Und der Reiter heisst, was er tut.
        from scbp import sprache as sp36
        sp36.setzen('de')
        pruefe(sp36.t('hf_diagnose') == 'Fehler melden',
               'der Reiter heisst „Fehler melden“, nicht „Diagnose“')

        print()
        print('25. Eigener Startbefehl und die Starter-Zeile im Bericht')
        # ⚠ Wer ueber Lutris, Heroic oder Flatpak spielt, bekam GAR KEINEN
        # Startknopf. Der Ausweg (Einstellung `spielstarter`) existierte, stand
        # aber nur in der einstellungen.json — fuer jemanden, der spielen und
        # nicht schrauben will, heisst das: gibt es nicht.
        from scbp import pfade as pf25
        from scbp import bericht as be25

        # Ein Befehl mit Argumenten muss zerlegt werden, eine echte Datei NICHT.
        skript25 = os.path.join(basis, 'mein start skript.sh')
        open(skript25, 'w').close()
        pruefe(pf25._startbefehl(skript25) == [skript25],
               'eine vorhandene Datei mit Leerzeichen bleibt ganz')
        pruefe(pf25._startbefehl('lutris rungame/star-citizen')
               == ['lutris', 'rungame/star-citizen'],
               'ein Befehl mit Argumenten wird zerlegt')
        pruefe(pf25._startbefehl('flatpak run org.starcitizen-lug.Helper')
               == ['flatpak', 'run', 'org.starcitizen-lug.Helper'],
               'auch der Flatpak-Aufruf')
        # Unpaariges Anfuehrungszeichen darf nicht in eine Ausnahme laufen.
        pruefe(pf25._startbefehl('kaputt "offen') == ['kaputt "offen'],
               'ein unpaariges Anfuehrungszeichen wirft nicht')

        # Der eingetragene Befehl schlaegt die Suche.
        alt_einst25 = pf25.einstellung
        try:
            pf25.einstellung = lambda name: ('mein-eigener-start --jetzt'
                                             if name == 'spielstarter' else None)
            pruefe(pf25.spielstarter() == 'mein-eigener-start --jetzt',
                   'der eingetragene Startbefehl schlaegt die Suche')
        finally:
            pf25.einstellung = alt_einst25

        # ⚠ Und er muss im BERICHT stehen. Ohne diese Zeile ist "der Startknopf
        # tut nichts" nicht zu beantworten, ohne den Nutzer auszufragen — genau
        # das kostete am 27.08.2026 zwei Stunden.
        pruefe(hasattr(be25, '_spielstarter'),
               'der Bericht kennt eine Starter-Zeile')
        quelle25 = open(os.path.join(WURZEL, 'scbp', 'bericht.py'),
                        encoding='utf-8').read()
        pruefe("zeile(t('b_starter')" in quelle25,
               'und gibt sie auch aus')
        pruefe('kuerzen(' in quelle25.split('def _spielstarter')[1][:900],
               'gekuerzt — kein Benutzername im oeffentlichen Bericht')

        print()
        print('24. Der Waechter gibt den Port wirklich frei')
        # ⚠ **Der Kern des Selbst-Neustarts.** Steht im Lausch-Faden ein
        # `accept()`, weckt ein `close()` aus einem anderen Faden es NICHT: Der
        # Deskriptor bleibt gueltig, der Port belegt. Die frisch gestartete
        # Fassung kann sich dann nicht binden, haelt sich fuer die zweite
        # Instanz und beendet sich planmaessig — fuer den Nutzer sieht das aus
        # wie "geht aus und kommt nicht wieder".
        #
        # Drei Anlaeufe (rc67, rc68, rc70) haben das nicht geloest, weil geraten
        # statt gemessen wurde. Der Beweis kam aus einem Bericht vom
        # 27.08.2026: "neustart_tot, Rueckgabewert 0 — keine Ausgabe". Kein
        # Absturz, sondern ein geordneter Abgang.
        import socket as so24
        from scbp import overlay as ov24
        alt_port24 = ov24.WAECHTER_PORT
        ov24.WAECHTER_PORT = 47990
        try:
            gestartet24 = ov24.waechter_starten(lambda: None)
            pruefe(gestartet24, 'der Waechter laesst sich starten')
            time.sleep(0.2)
            ov24.waechter_stoppen()
            time.sleep(0.3)
            probe24 = so24.socket(so24.AF_INET, so24.SOCK_STREAM)
            probe24.setsockopt(so24.SOL_SOCKET, so24.SO_REUSEADDR, 1)
            frei24 = True
            grund24 = ''
            try:
                probe24.bind(('127.0.0.1', ov24.WAECHTER_PORT))
                probe24.listen(4)
            except OSError as ausnahme24:
                frei24 = False
                grund24 = str(ausnahme24)
            finally:
                probe24.close()
            pruefe(frei24,
                   'nach dem Stoppen laesst sich der Port neu binden%s'
                   % (' (%s)' % grund24 if grund24 else ''))

            # Und der Weg dorthin: ohne `shutdown()` bleibt der Faden haengen.
            quelle24 = open(os.path.join(WURZEL, 'scbp', 'overlay.py'),
                            encoding='utf-8').read()
            # ⚠ Bis zur naechsten Funktion schneiden, nicht auf Zeichenzahl —
            # ein langer Kommentar schob den Aufruf sonst aus dem Fenster.
            block24 = quelle24.split('def waechter_stoppen')[1].split('\ndef ')[0]
            pruefe('shutdown(' in block24,
                   'waechter_stoppen bricht das wartende accept() ab')
        finally:
            ov24.WAECHTER_PORT = alt_port24
            try:
                ov24.waechter_stoppen()
            except Exception:
                pass

        print()
        print('23. Bei der Mindestgroesse ist alles Wichtige sichtbar')
        # ⚠ Die Seite „Update & Ueber" ist die einzige, auf der ein nicht
        # gefundener Knopf richtig weh tut: Wer den Update-Knopf nicht sieht,
        # updatet nicht. Gemeldet am 27.08.2026: „das nervt user weil die den
        # button zum updaten nicht sofort finden."
        #
        # Geprueft wird bei der MINDESTGROESSE des Fensters (1100x760) — nicht
        # bei der Groesse, die der Entwickler zufaellig offen hat.
        import tkinter as tk23
        import tkinter.font as tkfont23
        from scbp import seiten as se23
        from scbp.hauptfenster import MIN_BREITE as MB23, MIN_HOEHE as MH23

        wurzel23 = tk23.Tk()
        _k23 = tkfont23.Font(root=wurzel23, family='Segoe UI', size=10)
        _t23 = tkfont23.Font(root=wurzel23, family='Segoe UI', size=12,
                             weight='bold')

        class _Traeger23:
            f_klein = _k23; f_titel = _t23; f_fett = _t23; f_gross = _t23
            f_mittel = _k23; f_normal = _k23; version = '3.0.0'
            def sagen(self, *a, **k): pass
            def oeffnen(self, *a, **k): pass
            def _einrichtung(self, *a, **k): pass

        try:
            rahmen23 = tk23.Frame(wurzel23)
            rahmen23.pack(fill='both', expand=True)
            wurzel23.geometry('%dx%d' % (MB23, MH23))
            se23._ueber(_Traeger23(), rahmen23)
            wurzel23.update_idletasks()
            wurzel23.update()

            hoehe23 = wurzel23.winfo_height()
            abgeschnitten = []
            def _sammeln(w):
                for kind in w.winfo_children():
                    if (kind.winfo_class() == 'Canvas'
                            and kind.winfo_height() > 20
                            and kind.winfo_width() > 300):
                        y = kind.winfo_rooty() - wurzel23.winfo_rooty()
                        unten = y + kind.winfo_height()
                        # Die Rollflaeche selbst reicht bis zum Rand — die zaehlt
                        # nicht als abgeschnitten.
                        if unten > hoehe23 + 2 and kind.winfo_height() < hoehe23 - 50:
                            abgeschnitten.append((y, unten))
                    _sammeln(kind)
            _sammeln(rahmen23)
            # ⚠ **Nicht auf MIN_HOEHE bestehen.** Der Windows-Runner hat einen
            # virtuellen Bildschirm, auf dem Tk das Fenster nur 749 px hoch
            # bekommt — die Pruefung schlug dort fehl und brach den Bau von
            # rc68 ab, obwohl am Code nichts falsch war. Ist das Fenster
            # kleiner als die Mindestgroesse, wird die Kanten-Pruefung darunter
            # sogar STRENGER; verlangt wird deshalb nur ein echtes Fenster.
            pruefe(hoehe23 >= 600,
                   'die Probe hat ein echtes Fenster (%d px, Mindestgroesse %d)'
                   % (hoehe23, MH23))
            pruefe(not abgeschnitten,
                   'kein Knopf der Update-Seite faellt unter die Kante (%s)'
                   % (abgeschnitten or 'keiner'))
        finally:
            try:
                wurzel23.destroy()
            except Exception:
                pass

        print()
        print('22. Die Ablage schreibt bei jedem neuen Bauplan mit')
        # Bis rc65 wurden die drei Ausgabe-Dateien NUR auf Knopfdruck
        # geschrieben. Wer einmal geklickt hatte, hielt sie fuer aktuell — sie
        # standen aber fuer immer auf dem Stand jenes Klicks.
        import importlib as _imp22
        heim22 = os.path.join(basis, 'ablageprobe')
        os.makedirs(heim22)
        alt_heim22 = os.environ.get('SC_BP_HOME')
        os.environ['SC_BP_HOME'] = heim22
        try:
            from scbp import pfade as pf22
            _imp22.reload(pf22)
            from scbp import bestand as be22, export as ex22
            _imp22.reload(ex22)
            _imp22.reload(be22)

            ordner22 = ex22.ablage_ordner()
            # Altbestand aus der Zeit der datierten Namen — und eine fremde
            # Datei, die auf keinen Fall angefasst werden darf.
            for name in ('SC-Blueprints-Basetool-2026-08-01.json',
                         'scmdb-import-2026-07-30.json'):
                open(os.path.join(ordner22, name), 'w').close()
            open(os.path.join(ordner22, 'meine-notiz.json'), 'w').close()

            daten22 = be22.leer()
            be22.hinzufuegen(daten22, 'Testbauplan Alpha', 'log')
            be22.speichern(daten22)

            liegt = set(os.listdir(ordner22))
            pruefe({'SC-Blueprints-Basetool.json', 'scmdb-import.json',
                    'SC-BP-Watcher-Bestand.json'} <= liegt,
                   'speichern() schreibt alle drei Versionen mit')

            # ⚠ Ohne Datum im Namen — sonst entstuenden taeglich drei neue
            # Dateien, und niemand wuesste, welche die aktuelle ist.
            be22.hinzufuegen(daten22, 'Testbauplan Beta', 'log')
            be22.speichern(daten22)
            json_dateien = [d for d in os.listdir(ordner22)
                            if d.endswith('.json')]
            pruefe(len(json_dateien) == 4,      # drei Versionen + fremde Datei
                   'zweimal speichern erzeugt keine zweite Garnitur (%d Dateien)'
                   % len(json_dateien))

            pruefe(os.path.isfile(os.path.join(ordner22, 'meine-notiz.json')),
                   'eine fremde Datei im Ordner bleibt unangetastet')
            aelter = os.path.join(ordner22, ex22.ALTORDNER)
            pruefe(os.path.isdir(aelter) and len(os.listdir(aelter)) == 2,
                   'die alten datierten Versionen sind weggeraeumt, nicht geloescht')

            # Der Speichern-Dialog dagegen behaelt das Datum: Dort haelt jemand
            # bewusst einen Stand fest.
            pruefe('2026' in ex22.vorschlag('scmdb') or
                   time.strftime('%Y') in ex22.vorschlag('scmdb'),
                   'der Speichern-Dialog schlaegt weiterhin einen Namen mit Datum vor')

            # Und der Knopf je Zeile muss die Version durchreichen, statt
            # 'basetool' fest verdrahtet zu haben.
            quelle22 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                            encoding='utf-8').read()
            pruefe('def einzeln(art):' in quelle22,
                   'Einzeln speichern nimmt die Version entgegen')
            pruefe("export.schreiben(ziel, art=art)" in quelle22,
                   'und gibt sie auch weiter (nicht mehr fest basetool)')
        finally:
            if alt_heim22 is None:
                os.environ.pop('SC_BP_HOME', None)
            else:
                os.environ['SC_BP_HOME'] = alt_heim22
            from scbp import pfade as pf22b
            _imp22.reload(pf22b)

    finally:
        shutil.rmtree(basis, ignore_errors=True)

    print()
    print('37. Ein Auftrag mit mehreren Preisstufen verliert keine Bauplaene')
    # ⚠ Der Fehler vom 28.08.2026, gemeldet von Morkhan. `_missionen()` legte
    # die Auftraege unter ihrem Textschluessel ab — und Vertraege, die sich
    # einen teilen (123 von 353), ueberschrieben sich gegenseitig. Der zuletzt
    # gelesene gewann, 797 Bauplan-Eintraege sah nie jemand.
    #
    # Geprueft wird an einem winzigen Dump mit genau dieser Falle: zwei
    # Stufen, ein Schluessel, verschiedene Toepfe. Kommt nur eine Seite an,
    # ist der alte Fehler zurueck.
    from scbp import katalog as k37
    dump37 = {
        'blueprintPools': {
            'p-klein': {'blueprints': [{'name': 'Kleiner Plan'}]},
            'p-gross': {'blueprints': [{'name': 'Grosser Plan'}]},
        },
        'factionRewardsPools': [],
        'contracts': [
            {'titleLocKey': 'geteilt_title', 'descriptionLocKey': 'geteilt_desc',
             'rewardUEC': 50000, 'blueprintRewards': [{'blueprintPool': 'p-klein',
                                                       'chance': 1}],
             'minStanding': {'name': 'Neuling', 'minReputation': 800}},
            {'titleLocKey': 'geteilt_title', 'descriptionLocKey': 'geteilt_desc',
             'rewardUEC': 260000, 'blueprintRewards': [{'blueprintPool': 'p-gross',
                                                        'chance': 1}],
             'minStanding': {'name': 'Meister', 'minReputation': 38000}},
            # Dritte Stufe, die gar nichts ausschuettet — der Fall, wegen dem
            # jemand fuer eine Liste hinfliegt, die seine Stufe nie hergibt.
            {'titleLocKey': 'geteilt_title', 'descriptionLocKey': 'geteilt_desc',
             'rewardUEC': 20000, 'blueprintRewards': [],
             'minStanding': {'name': 'Anwaerter', 'minReputation': 1}},
        ],
    }
    m37 = k37._missionen(dump37)
    e37 = m37.get('geteilt_title') or {}
    pruefe(sorted(e37.get('bp') or []) == ['Grosser Plan', 'Kleiner Plan'],
           'beide Stufen kommen an, keine ueberschreibt die andere')
    pruefe(e37.get('leer') == 1 and e37.get('stufen') == 3,
           'die Stufe ohne Bauplaene wird vermerkt (1 von 3)')
    pruefe((e37.get('ab') or {}).get('Grosser Plan', {}).get('rep') == 38000,
           'der hoehere Plan traegt seinen eigenen Rang')
    pruefe((e37.get('ab') or {}).get('Kleiner Plan', {}).get('rep') == 800,
           'und der kleine seinen')
    # Gegenprobe: Brauchen alle Plaene denselben Rang, faellt die Angabe weg —
    # sonst stuende zwoelfmal dieselbe Zeile untereinander.
    gleich37 = json.loads(json.dumps(dump37))
    gleich37['contracts'][1]['minStanding'] = {'name': 'Neuling',
                                               'minReputation': 800}
    pruefe(not (k37._missionen(gleich37).get('geteilt_title') or {}).get('ab'),
           'bei gleichem Rang steht die Angabe NICHT an jedem Plan')
    # Und der Katalog auf der Platte muss den Umbau ueberhaupt mitbekommen.
    pruefe(k37.FORMAT >= 2,
           'der Katalog hat eine Aufbau-Nummer (sonst greift der Umbau nie)')

    # ------------------------------------------------------------------
    # Die Bau-Anleitungen selbst. Ein Tippfehler darin kostet keinen Fehler
    # im Programm, sondern **jeden Bau** — und zwar stumm: GitHub meldet nur
    # „workflow file issue", nichts davon steht im Fehlerbericht eines
    # Nutzers. Am 28.08.2026 lief das über eine Stunde so.
    print()
    print('38. Die Bau-Anleitungen sind gueltiges YAML')
    _wf = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), '.github', 'workflows')
    _dateien = sorted(f for f in (os.listdir(_wf) if os.path.isdir(_wf) else [])
                      if f.endswith(('.yml', '.yaml')))
    pruefe(bool(_dateien), 'es gibt ueberhaupt Bau-Anleitungen zu pruefen')
    for _name in _dateien:
        with open(os.path.join(_wf, _name), encoding='utf-8') as _f:
            _funde = doppelte_schluessel(_f.read())
        pruefe(not _funde, '%s hat keinen doppelten Schluessel%s'
               % (_name, '' if not _funde else
                  ' (Zeile %d: „%s“ stand schon in Zeile %d)'
                  % (_funde[0][0], _funde[0][1], _funde[0][2])))

    # Gegenprobe — eine Prüfung, die nie anschlägt, prüft nichts. Das hier ist
    # der echte Fehler vom 28.08.2026, Zeichen für Zeichen.
    _kaputt = ('jobs:\n  bau:\n    steps:\n'
               '      - name: Berichtsziel einsetzen\n'
               '        shell: bash\n        shell: bash\n'
               '        run: echo hi\n')
    pruefe([f[1] for f in doppelte_schluessel(_kaputt)] == ['shell'],
           'und der Fehler von damals wird auch wirklich gefunden')
    # Und die Gegenrichtung: Was erlaubt ist, darf nicht gemeldet werden —
    # sonst schaltet man die Prüfung nach dem dritten Fehlalarm ab.
    _erlaubt = ('jobs:\n  bau:\n    steps:\n'
                '      - name: A\n        run: |\n'
                '          cat <<X\n          on: 1\n          on: 2\n          X\n'
                '      - name: B\n        run: echo b\n')
    pruefe(not doppelte_schluessel(_erlaubt),
           'gleiche Namen in getrennten Schritten sind KEIN Fehler')


    # ------------------------------------------------------------------
    # ⚠ Der häufigste Support-Fall: „ich sehe deine Angaben im Spiel nicht
    # mehr". Ein Übersetzungs-Update oder ein Spiel-Patch schreibt die
    # `global.ini` neu und wirft die Angaben dabei stillschweigend hinaus.
    # Am 28.08.2026 stand in Morkhans Bericht nur `inj_quelle=deutsch` — ob
    # etwas eingetragen war, musste erschlossen werden statt abgelesen.
    print()
    print('39. Der Bericht sagt, ob die Angaben im Spiel stehen')
    from scbp import bericht as ber39, injektion as inj39
    # ⚠ Eigener Ordner statt `basis`: Der ist an dieser Stelle bereits
    # aufgeräumt, und ein Schreibversuch darin bricht den ganzen Lauf ab.
    _ordner39 = tempfile.mkdtemp(prefix='sc-bp-inj39-')
    _ini39 = os.path.join(_ordner39, 'global39.ini')
    _echt39 = inj39.ini_datei
    try:
        # Datei da, Angaben vom Launcher hinausgeworfen — Morkhans Lage.
        with open(_ini39, 'w', encoding='utf-8') as f:
            f.write('mission_a_desc=Deliver cargo.\n')
        inj39.ini_datei = lambda: (_ini39, 'german_(germany)', 'deutsch')
        _l39 = ber39._injektionslage()
        pruefe('NICHT' in _l39 or 'NOT' in _l39,
               'ohne Angaben in der Datei sagt der Bericht das auch')

        # ⚠ MrKrakens Kennzeichnung allein ist KEINE Injektion. Er schreibt in
        # StarStrings dasselbe blanke `<EM4>[BP]</EM4>` an seine Titel (314 in
        # der Fassung vom 29.08.2026). Bis dahin meldete der Bericht deshalb
        # „steht drin", sobald jemand StarStrings frisch eingesetzt hatte.
        with open(_ini39, 'a', encoding='utf-8') as f:
            f.write('mission_b_title=Bounty <EM4>[BP]</EM4>\n')
        _l39ss = ber39._injektionslage()
        pruefe('NICHT' in _l39ss or 'NOT' in _l39ss,
               'MrKrakens blankes [BP] allein gilt NICHT als eigene Injektion')

        # Dieselbe Datei, eigene Angaben drin — die Block-Überschrift ist die
        # Form, die jede echte Injektion hinterlässt.
        with open(_ini39, 'a', encoding='utf-8') as f:
            f.write('mission_c_desc=Deliver cargo.\\n\\n--------------------'
                    '\\nMÖGLICHE BAUPLÄNE FÜR DIESEN MISSIONSTYP\\n'
                    '    [x] Atzkav Sniper Rifle\n')
        _l39b = ber39._injektionslage()
        pruefe('NICHT' not in _l39b and 'NOT' not in _l39b,
               'und mit Angaben meldet er sie als eingetragen')

        # ⚠ Gar keine Datei ist NICHT dasselbe wie „nicht eingetragen": Unter
        # Linux ohne Übersetzung ist das der Normalzustand, und eine Warnung
        # davor wäre eine Warnung vor nichts.
        inj39.ini_datei = lambda: (None, 'english', None)
        _l39c = ber39._injektionslage()
        pruefe('NICHT' not in _l39c and 'NOT' not in _l39c,
               'ohne Textdatei warnt er NICHT vor dem Normalzustand')
    finally:
        inj39.ini_datei = _echt39
        shutil.rmtree(_ordner39, ignore_errors=True)


    print()
    print('40. Der Installer haelt das Programm auch UNTEN, nicht nur zu')
    # ⚠ Gemessen am 28.08.2026 (beim Update rc75 -> rc83). Im
    # Setup-Protokoll steht die ganze Kette:
    #
    #     05:43:47  Shutting down applications using our files. (forced)
    #     05:43:55  << Watcher laeuft wieder, Elternprozess explorer.exe >>
    #     05:44:17  DeleteFile: The existing file appears to be in use (5).
    #
    # `CloseApplications=force` hat sauber geschlossen. Acht Sekunden spaeter
    # hat der **Autostart** das Programm wieder hochgefahren, und das Kopieren
    # lief gegen Code 5. Bewiesen ueber den Elternprozess: `explorer.exe`
    # arbeitet die Run-Werte verzoegert nach seinem eigenen Start ab.
    #
    # `CloseApplications` kann das prinzipiell nicht loesen — es schliesst
    # einmal. Deshalb faehrt `PrepareToInstall` direkt vor dem Kopieren nach.
    # Ohne diese Pruefung faellt der Fix bei der naechsten Ueberarbeitung
    # unbemerkt heraus, und der Fehler kommt bei Nutzern wieder — dort, wo
    # ihn niemand messen kann.
    iss40 = open(os.path.join(WURZEL, 'packaging', 'installer.iss'),
                 encoding='utf-8').read()
    pruefe('[Code]' in iss40 and 'PrepareToInstall' in iss40,
           'PrepareToInstall faehrt vor dem Kopieren nach')
    pruefe('taskkill' in iss40,
           'und beendet dabei einen wieder hochgefahrenen Watcher')
    pruefe('FileExists' in iss40,
           'nur beim Update — Erstinstallationen warten nicht')
    # Die zwei Direktiven, an denen der Weg schon zweimal gescheitert ist.
    aktiv40 = [z.strip() for z in iss40.splitlines()
               if z.strip() and not z.strip().startswith(';')]
    pruefe(not any(z.startswith('AppMutex=') for z in aktiv40),
           'AppMutex steht NICHT drin (blockierte den Weg am 26.08.2026)')
    pruefe('RestartApplications=no' in aktiv40,
           'RestartApplications=no — der RM faehrt nichts von selbst hoch')
    # ⚠ Und die Erklaerung im Code muss dazu passen. Sie tat es bis zum
    # 28.08.2026 nicht und schickte die Fehlersuche in die falsche Richtung.
    ak40 = open(os.path.join(WURZEL, 'scbp', 'aktualisierung.py'),
                encoding='utf-8').read()
    kopf40 = ak40[ak40.index('Der Eigenbau ist deshalb weg'):][:3000]
    # ⚠ Auf Wortabwesenheit zu pruefen waere falsch: Der Kommentar ZITIERT die
    # beiden alten Falschaussagen, um sie zu widerlegen. Geprueft wird deshalb,
    # ob er den echten Stand nennt — daran haengt, ob der naechste Leser richtig
    # informiert wird.
    pruefe('RestartApplications=no' in kopf40,
           'der Code nennt den echten Stand: RestartApplications=no')
    pruefe('PrepareToInstall' in kopf40,
           'und verweist auf das Nachfassen im Installer')

    print()
    print('41. Ein Schalter, der aus sagt, macht auch aus')
    # ⚠ Gemessen am 28.08.2026 (gemessen): „Angaben am Gegenstand“ abgeschaltet,
    # Statuszeile meldete „aus“ — und die `global.ini` blieb unangetastet. 1.217
    # Angaben standen weiter drin, das Spiel zeigte sie unverändert.
    #
    # Schlimmer noch der Kasten darüber: „Änderungen wirken beim nächsten
    # Spielstart“ — wer danach neu startete und alles unverändert vorfand, hielt
    # das Werkzeug für kaputt. Gemeldet: „ein user erwartet das was er liest und
    # sieht, ist es aus angaben weg also muss das auch so sein.“
    #
    # Der Schalter stößt das Neuschreiben jetzt selbst an. Diese Prüfung hält das
    # fest — fällt es heraus, ist der Fehler zurück, und zwar unsichtbar.
    se41 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                encoding='utf-8').read()
    i41 = se41.index('def angaben_um():')
    rumpf41 = se41[i41:se41.index('return neu_wert', i41)]
    pruefe('_inj_erneuern' in rumpf41,
           'Umlegen schreibt die Textdatei neu')
    pruefe('lage_zeigen' in rumpf41,
           'und der Zustandskasten wird danach aufgefrischt')
    # ⚠ Zwei Riegel, sonst stößt ein Formatschalter eine Einfügung an, die
    # niemand wollte — der obere Schalter lässt Vorhandenes mit Absicht stehen.
    pruefe("inj_an" in rumpf41,
           'aber nur, wenn das Schreiben überhaupt eingeschaltet ist')
    pruefe("drin" in rumpf41,
           'und nur, wenn schon etwas in der Datei steht')

    # ⚠ Derselbe Anspruch für den Hauptschalter — der Autor fiel im eigenen Test
    # darauf herein und hat damit den Punkt bewiesen: „ich hab das fette gelesen
    # aber nicht das kleinere“. Der Hinweis stand im Kleingedruckten, und genau
    # das liest niemand. Aus heißt jetzt weg, an heißt da.
    i41b = se41.index('def inj_an_um():')
    rumpf41b = se41[i41b:se41.index('return neu_wert', i41b)]
    pruefe('_inj_entfernen' in rumpf41b,
           'Ausschalten nimmt vorhandene Angaben heraus')
    pruefe('_inj_erneuern' in rumpf41b,
           'und Einschalten trägt sie wieder ein')
    # ⚠ Der Hilfetext MUSS mitziehen, sonst behauptet er das Gegenteil des
    # Verhaltens — schlimmer als gar kein Hinweis.
    from scbp import sprache as sp41
    hilfe41 = sp41.TEXTE['s_sp_an_h']
    pruefe('entfernt vorhandene Angaben nicht' not in hilfe41[0],
           'der Hilfetext behauptet nicht mehr das Gegenteil (de)')
    pruefe('does not remove' not in hilfe41[1],
           'dasselbe auf Englisch')
    # ⚠ Und der Kasten muss den Rest zugeben, statt „nichts geschrieben“ zu sagen.
    pruefe('s_sp_aus_rest' in sp41.TEXTE and 's_sp_aus_rest_h' in sp41.TEXTE,
           'der Kasten kann sagen, dass noch Angaben im Spiel stehen')
    pruefe('s_sp_aus_rest' in se41,
           'und benutzt das auch')

    # ⚠ Der Autostart wird an ZWEI Stellen gesetzt: vom [Registry]-Abschnitt des
    # Installers (nur bei gewaehltem Haekchen) und vom Programm selbst
    # (`scbp/autostart.py`). `uninsdeletevalue` raeumt nur den ersten Fall weg.
    #
    # Gemessen am 28.08.2026 (gemessen): Nach dem Deinstallieren stand der Wert
    # weiter in der Registry und zeigte auf eine geloeschte Datei. Windows
    # versucht sie bei jeder Anmeldung zu starten und scheitert still.
    #
    # Derselbe Autostart hat morgens den Update-Fehler (Code 5) ausgeloest — er
    # war an beiden Enden nur halb geregelt.
    pruefe('CurUninstallStepChanged' in iss40 and 'RegDeleteValue' in iss40,
           'der Deinstaller raeumt den Autostart-Eintrag weg')
    # ⚠ Beide Seiten MUESSEN denselben Wertnamen meinen, sonst raeumt der
    # Deinstaller ins Leere und der echte Eintrag bleibt liegen.
    from scbp import autostart as as41
    pruefe("'" + as41.NAME + "'" in iss40,
           'und zwar genau den Namen, den das Programm schreibt (%s)' % as41.NAME)

    print()
    print('42. Ein eigener Fund ergaenzt einen Patch, er ersetzt ihn nicht')
    # ⚠ Gemessen am 28.08.2026 (gemessen): Im Filter stand „4.10.0 (3)", und
    # darunter drei Schiffswaffen. Mitgeliefert waren 21 Baupläne für dieselbe
    # Version — der ganze Patch war aus der Anzeige verschwunden.
    #
    # Ursache: `laden()` legte die eigene Historie per `update()` über die
    # mitgelieferte. Bei gleichem Versionsschlüssel gewann die eigene komplett.
    # Nur: Was `eintragen()` schreibt, ist immer bloß der **Zuwachs seit dem
    # letzten Lauf** — hier drei Waffen, die scmdb zwei Tage später nachreichte.
    # Als vollständige Patch-Liste gelesen ist das zwangsläufig falsch.
    #
    # Diese Prüfung hält beide Richtungen fest: mitgeliefert + eigen, und eigen
    # + eigen. Fällt eine heraus, frisst der nächste Nachzügler wieder den Patch.
    import tempfile as _tf42
    from scbp import patchhistorie as ph42
    _alt_home42 = os.environ.get('SC_BP_HOME')
    os.environ['SC_BP_HOME'] = _tf42.mkdtemp(prefix='sc-bp-historie-')
    try:
        _mit42 = ph42._lies(ph42.pfade.programm_datei(ph42.MITGELIEFERT))
        _v42 = sorted(_mit42, key=ph42.rang)[-1]
        _vorher42 = len(_mit42[_v42].get('neu') or [])
        pruefe(_vorher42 > 1,
               'die mitgelieferte Historie fuehrt mehrere Bauplaene (%d)'
               % _vorher42)

        # a) Der Fall vom 28.08.2026: zwei Nachzuegler in derselben Version.
        ph42.eintragen(_v42, ['Testwaffe A', 'Testwaffe B'], datum='2099-12-31')
        pruefe(len(ph42.laden()[_v42]['neu']) == _vorher42 + 2,
               'eigene Funde kommen dazu, statt den Patch zu ersetzen')
        pruefe(ph42.laden()[_v42]['datum'] == _mit42[_v42].get('datum'),
               'und das fruehere Datum bleibt stehen')

        # b) Und der zweite eigene Fund wirft den ersten nicht weg.
        ph42.eintragen(_v42, ['Testwaffe C'])
        pruefe(len(ph42.laden()[_v42]['neu']) == _vorher42 + 3,
               'ein zweiter eigener Fund loescht den ersten nicht')

        # c) Was schon dasteht, darf nicht doppelt gezaehlt werden.
        ph42.eintragen(_v42, [_mit42[_v42]['neu'][0], 'Testwaffe A'])
        pruefe(len(ph42.laden()[_v42]['neu']) == _vorher42 + 3,
               'bekannte Namen kommen nicht ein zweites Mal hinein')

        # d) ⚠ Und der Bericht muss die Zahlen zeigen. Ohne diese Zeile stand im
        #    Bericht nur der Katalogstand — der war in Ordnung, die Historie
        #    darunter nicht. Genau deshalb blieb der Fehler unsichtbar.
        from scbp import bericht as ber42
        pruefe('(%d)' % (_vorher42 + 3) in (ber42._patchhistorie() or ''),
               'der Bericht nennt die Anzahl je Patch')
    finally:
        if _alt_home42 is None:
            os.environ.pop('SC_BP_HOME', None)
        else:
            os.environ['SC_BP_HOME'] = _alt_home42

    print()
    print('43. Das Auswahlfeld verspricht nur, was die Liste zeigen kann')
    # ⚠ Gemessen am 28.08.2026 (gemessen), direkt nach dem Fix an der Historie:
    # Im Feld stand „4.10.0 (24)", darunter drei Zeilen. Die Zahl in Klammern
    # ist eine Zusage, wie viele Zeilen kommen — und sie kam aus einer anderen
    # Quelle als die Zeilen selbst: `patches()` las die Historie, der Filter
    # prueft den Stempel `seit` im Katalog.
    #
    # Zwei Quellen fuer dieselbe Frage gehen irgendwann auseinander. Das Feld
    # zaehlt jetzt den Katalog. Damit dort auch alles gestempelt ist, zieht das
    # Fenster den Stempel nach, BEVOR es den Katalog liest — vorher hing das
    # allein am Netz-Takt, der irgendwann nach dem Start in einem eigenen Faden
    # laeuft (gemessen: Fenster 10:44:02, Stempel 10:44:03 — eine Sekunde zu
    # spaet, und die Liste blieb bis zum naechsten Oeffnen falsch).
    import tempfile as _tf43
    from scbp import katalog as kat43, patchhistorie as ph43
    _alt_home43 = os.environ.get('SC_BP_HOME')
    os.environ['SC_BP_HOME'] = _tf43.mkdtemp(prefix='sc-bp-patchfeld-')
    try:
        # Die Historie kennt DREI Bauplaene, der Katalog fuehrt nur zwei davon.
        ph43._schreib(ph43.pfade.app_datei('patch-historie.json'),
                      {'4.10.0-live.7': {'datum': '2026-08-26',
                                         'neu': ['Erster Bauplan',
                                                 'Zweiter Bauplan',
                                                 'Nicht im Katalog']}})
        with open(kat43.pfade.app_datei('katalog-cache.json'), 'w',
                  encoding='utf-8') as f:
            json.dump({'version': '4.10.0-live.7', 'geholt': '',
                       'bauplaene': {'erster bauplan': {'n': 'Erster Bauplan'},
                                     'zweiter bauplan': {'n': 'Zweiter Bauplan'},
                                     'alter bauplan': {'n': 'Alter Bauplan'}},
                       'missionen': {}}, f)

        # a) Ungestempelt darf das Feld gar nichts versprechen.
        pruefe(kat43.patches(kat43.laden()) == [],
               'ohne Stempel bleibt das Feld leer, statt zu versprechen')

        # b) Nach dem Nachziehen: genau die zwei, die es im Katalog gibt.
        pruefe(kat43.stempel_nachziehen() == 2,
               'zwei Stempel werden nachgetragen')
        _p43 = kat43.patches(kat43.laden())
        pruefe(_p43 == [('4.10.0-live.7', '4.10.0', 2)],
               'das Feld zaehlt den Katalog (2), nicht die Historie (3)')

        # c) Und die Liste kommt auf dieselbe Zahl — das ist der ganze Punkt.
        _d43 = kat43.laden()
        pruefe(len(kat43.neue(_d43)) == _p43[0][2],
               'Feld und Liste kommen auf dieselbe Zahl')

        # d) ⚠ Und das Fenster muss stempeln, BEVOR es liest. Andersherum sieht
        #    es beim ersten Start nach einem Update den alten Stand.
        _q43 = open(os.path.join(WURZEL, 'scbp', 'bestandsfenster.py'),
                    encoding='utf-8').read()
        pruefe('katalog_modul.stempel_nachziehen()' in _q43
               and (_q43.index('katalog_modul.stempel_nachziehen()')
                    < _q43.index('self.katalog = katalog_modul.laden()')),
               'das Fenster stempelt, BEVOR es den Katalog liest')
    finally:
        if _alt_home43 is None:
            os.environ.pop('SC_BP_HOME', None)
        else:
            os.environ['SC_BP_HOME'] = _alt_home43

    print()
    print('44. Das Schloss laesst sich auch wieder ZUsperren')
    # ⚠ Haldjas (pr0) am 28.08.2026: „man kann das durckclicken entfernen, aber
    # eventuell kann der button zum locken stehen bleiben? sonst muss man ja
    # erst wieder in die einstellungen."
    #
    # Er hat den blinden Fleck getroffen: Gebaut war nur der Rueckweg. Das
    # schwebende Schloss erscheint, solange durchgereicht wird — schaltet man ab,
    # ist es weg, und der Hinweg fuehrte allein ueber Einstellungen -> Overlay.
    # Ein Weg hin und her gehoert an dieselbe Stelle.
    import tempfile as _tf44
    from scbp import pfade as pf44, sprache as sp44
    import sc_bp_watcher as w44
    _q44 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'), encoding='utf-8').read()

    pruefe("zeichen.knopf(bar, 'schloss_auf'" in _q44,
           'in der Overlay-Leiste steht ein offenes Schloss')
    # ⚠ Nur, wo das System es kann. Unter nativem Wayland waere ein Knopf ohne
    #   Wirkung schlimmer als keiner — dieselbe Regel wie beim Schalter.
    pruefe(_q44.index('overlay.durchklickbar_moeglich()')
           < _q44.index("zeichen.knopf(bar, 'schloss_auf'"),
           'und zwar nur, wenn das System Klicks durchreichen kann')
    pruefe(os.path.exists(os.path.join(WURZEL, 'assets', 'symbole',
                                       'schloss_auf.png'))
           or "'schloss_auf'" in open(os.path.join(WURZEL, 'tools',
                                                   'symbole_bauen.py'),
                                      encoding='utf-8').read(),
           'das Symbol dafuer gibt es')
    for _sl44 in ('hinweis_schloss_zu', 'ov_schloss_zu'):
        _e44 = sp44.TEXTE.get(_sl44)
        pruefe(bool(_e44) and len(_e44) == 2 and all(_e44),
               'Text %s steht in beiden Sprachen' % _sl44)

    # ⚠ Der teurere Teil: Klappt das Durchreichen nicht, MUSS die Einstellung
    #   zurueckgenommen werden. Ein gespeichertes „an", waehrend in Wahrheit
    #   nichts durchgereicht wird, ist das schlechteste von beidem — der Nutzer
    #   sieht einen Zustand, den es nicht gibt. Der Schalter in den
    #   Einstellungen macht es genauso (`seiten._durchklick_um`).
    _alt_home44 = os.environ.get('SC_BP_HOME')
    os.environ['SC_BP_HOME'] = _tf44.mkdtemp(prefix='sc-bp-schloss-')
    try:
        class _Ohne44:
            """Ein Overlay ohne Tk — die Methode braucht nur diese zwei Dinge."""
            gemeldet = None
            klappt = False

            def _status_setzen(self, satz):
                self.gemeldet = satz

            def durchklick_anwenden(self):
                return self.klappt

        _o44 = _Ohne44()
        w44.Overlay._schloss_zusperren(_o44)
        pruefe(pf44.einstellung_wahrheit('durchklickbar', False) is False,
               'geht das Durchreichen nicht, wird die Einstellung zurueckgenommen')
        pruefe(_o44.gemeldet is None,
               'und es wird kein Erfolg gemeldet, den es nicht gab')

        _o44.klappt = True
        w44.Overlay._schloss_zusperren(_o44)
        pruefe(pf44.einstellung_wahrheit('durchklickbar', False) is True,
               'klappt es, bleibt das Durchreichen an')
        pruefe(_o44.gemeldet is not None,
               'und der Nutzer erfaehrt, wie er zurueckkommt')

        # ⚠ Zweiter Wunsch von Gemeldet am selben Tag: „am besten waere das
        #   gleiche schloss gruen zu faerben was eh in der leiste ist, und es
        #   damit auch wieder zu entsperren."
        #
        #   Ein eigenes Fenster MUSS es bleiben — durchgereicht wird immer fuer
        #   das ganze Fenster, ein Knopf in der Leiste waere in dem Moment
        #   genauso tot wie der Rest. Also liegt es passgenau darueber. Diese
        #   Pruefung haelt fest, dass die Lage vom Leisten-Knopf kommt und nicht
        #   wieder in die Ecke rutscht.
        _ank44 = _q44.index('def _schloss_anwenden')
        _bis44 = _q44.index('def _leistenschloss')
        _rumpf44 = _q44[_ank44:_bis44]
        pruefe('knopf.winfo_rootx()' in _rumpf44,
               'das schwebende Schloss nimmt die Lage vom Leisten-Knopf')
        pruefe('winfo_ismapped()' in _rumpf44,
               'und faellt auf die Ecke zurueck, wenn der Knopf nicht da ist')

        # ⚠ Der Fall, an dem rc92 noch scheiterte — gemeldet von Haldjas (pr0)
        #   am 28.08.2026, belegt durch seinen Bericht: `overlay_modus=popup`.
        #
        #   Im Pop-up-Betrieb ruft `verhalten_anwenden()` `withdraw()`, BEVOR je
        #   gezeichnet wurde. Der Knopf ist dann dauerhaft nicht gemappt, das
        #   Nachfassen laeuft zehnmal leer — und danach rechnete die Stelle aus
        #   der Lage eines UNSICHTBAREN Fensters. Gemessen:
        #
        #       versteckt (war sichtbar):  ismapped=0  w=56  rootx=1161
        #       nie gemalt, dann versteckt: ismapped=0  w=1   rootx=0
        #
        #   `_anfasser_zeigen()` loest denselben Fall seit jeher richtig: aus
        #   `self._letzte_lage`. Das Schloss geht jetzt denselben Weg.
        # ⚠ Ein Toplevel erbt die Deckkraft des Hauptfensters NICHT. Ohne diese
        #   Zeile lag ein voll deckendes Schloss ueber einem zu 93 % durch-
        #   scheinenden Knopf — zwei Symbole mit verschiedener Saettigung.
        # ⚠ Der Feinausgleich gilt NUR im sichtbaren Fall. Der Aufblend-Betrieb
        #   rechnet aus der Streifen-Position — wer ihn dort mit einrechnet,
        #   bricht das eine, waehrend er das andere geradezieht.
        pruefe('SCHLOSS_FEIN_X' in _rumpf44,
               'der Feinausgleich steht als benannte Konstante im sichtbaren Fall')
        _versteckt44 = _rumpf44[_rumpf44.index('ANFASSER_BREITE + 4'):]
        pruefe('SCHLOSS_FEIN_X' not in _versteckt44,
               'und fasst den Aufblend-Betrieb nicht an')
        pruefe('DECKKRAFT' in _rumpf44,
               'das Schloss traegt dieselbe Deckkraft wie das Overlay')
        pruefe('self._letzte_lage' in _rumpf44,
               'im Pop-up-Betrieb gilt die gemerkte Lage, nicht das '
               'versteckte Fenster')
        # ⚠ Und dort gehoert es an den Anfasser-Streifen. An der rechten Ecke
        #   der gemerkten Lage saesse es einsam, weit weg von der einzigen Marke,
        #   die im Aufblend-Betrieb ueberhaupt zu sehen ist.
        pruefe('ANFASSER_BREITE' in _rumpf44,
               'und haengt am Anfasser-Streifen, nicht in der leeren Ecke')
        # ⚠ Und OHNE die Hoehe auf null zu klemmen. `_current_geom()` bewahrt
        #   negatives Y ausdruecklich („so bleibt negatives Y als absolute
        #   Position erhalten") — auf mehreren Bildschirmen ist das eine
        #   gueltige Angabe, keine kaputte. `max(0, oben)` warf Streifen und
        #   Schloss auf den Hauptmonitor.
        for _wo, _name in ((_rumpf44, 'das Schloss'),
                           (_q44[_q44.index('def _anfasser_zeigen'):]
                            [:_q44[_q44.index('def _anfasser_zeigen'):]
.index('    def ', 10)], 'der Anfasser')):
            pruefe('max(0, oben)' not in _wo,
                   '%s klemmt die Hoehe nicht auf null (zweiter Monitor)'
                   % _name)
        # Und wenn sich der Bezugspunkt aendert, muss es mitkommen.
        for _wo44, _was44 in (('def _popup_zeigen', 'beim Aufblenden'),
                              ('def _popup_verstecken', 'beim Zublenden')):
            _teil44 = _q44[_q44.index(_wo44):]
            _teil44 = _teil44[:_teil44.index('    def ', 10)]
            pruefe('_schloss_nachziehen()' in _teil44,
                   'das Schloss zieht %s mit' % _was44)
        # ⚠ Gemessen am 28.08.2026: Ein ungezeichnetes Widget meldet Breite 1 und
        #   Position 0. `ismapped()` allein reicht deshalb nicht — sonst saesse
        #   das Schloss in der Bildschirmecke statt auf der Leiste.
        pruefe('winfo_width() > 1' in _rumpf44,
               'und prueft die Masse mit, nicht nur ismapped')

        # Und das Schloss darunter sagt dasselbe — sonst stuende dort das
        # Gegenteil des wahren Zustands, falls das Fenster darueber ausbleibt.
        from scbp import zeichen as zn44

        class _Knopf44:
            symbol, farbe = 'schloss_auf', zn44.GRAU

            def symbol_tauschen(self, name):
                self.symbol = name

            def faerben(self, farbe):
                self.farbe = farbe

        class _Leiste44:
            pass

        _l44 = _Leiste44()
        _l44.schloss_lbl = _Knopf44()
        w44.Overlay._leistenschloss(_l44, True)
        pruefe(_l44.schloss_lbl.symbol == 'schloss_zu'
               and _l44.schloss_lbl.farbe == zn44.GRUEN,
               'beim Zusperren wird das Leisten-Schloss zu und gruen')
        w44.Overlay._leistenschloss(_l44, False)
        pruefe(_l44.schloss_lbl.symbol == 'schloss_auf'
               and _l44.schloss_lbl.farbe == zn44.GRAU,
               'und danach wieder offen und grau')

        # ⚠ Gemeldet von Haldjas (pr0) am 28.08.2026 zu rc91: „nach dem ersten
        #   start ist das schloss symbol weiterhin in der ecke wie vorher auch,
        #   erst wenn man es einmal benutzt hat aendert es die position in die
        #   leiste."
        #
        #   Grund: `verhalten_anwenden()` laeuft unmittelbar vor `mainloop()`.
        #   Die Leiste steht dann im Baum, aber Tk hat noch nichts gemalt — also
        #   meldet `winfo_ismapped()` falsch, und der Rueckfall auf die Ecke
        #   greift bei JEDEM Start, sobald jemand das Durchreichen eingeschaltet
        #   gespeichert hat. Es wird deshalb nachgefasst.
        pruefe('_nachfassen' in _rumpf44,
               'ist die Leiste noch nicht gezeichnet, wird nachgefasst')
        # ⚠ Und zwar OHNE vorher eines an der falschen Stelle zu bauen. Genau
        #   das hat Haldjas gesehen: „Schloss ist an 2 Positionen". Ein kurz
        #   aufblitzendes falsches Schloss waere nur die halbe Reparatur.
        _warte44 = _rumpf44.split('_nachfassen(versuch + 1)', 1)[1]
        pruefe(_warte44.lstrip(') ' + chr(10)).startswith('return'),
               'und zwar ohne vorher eines an der falschen Stelle zu bauen')
        _nach44 = _q44[_q44.index('def _nachfassen'):]
        _nach44 = _nach44[:_nach44.index('def _leistenschloss')]
        pruefe("einstellung_wahrheit('durchklickbar'" in _nach44,
               'und zwar nur, solange das Durchreichen ueberhaupt noch an ist')
        # ⚠ Begrenzt — sonst liefe es ewig weiter, solange das Overlay
        #   eingeklappt oder im Pop-up-Betrieb versteckt ist.
        pruefe('versuch < 10' in _rumpf44,
               'und begrenzt, damit es nicht ewig weiterlaeuft')
        # Und NUR, solange die Leiste ueberhaupt noch kommt. Gemeldet von
        # Haldjas (pr0) zu rc95: Beim Zublenden lief das Nachfassen blind mit
        # und verzoegerte den Ruecksprung um genau 10 x 300 ms = 3 Sekunden.
        # Gemessen trennt root.winfo_ismapped() die Faelle:
        #     Start, nach update_idletasks   root=1  knopf=0  -> wird gemalt
        #     nach withdraw()                root=0  knopf=0  -> soll weg sein
        pruefe('_wird_noch_gezeichnet()' in _rumpf44,
               'und nur, solange die Leiste ueberhaupt noch kommt')
        _wnz = _q44[_q44.index('def _wird_noch_gezeichnet'):]
        _wnz = _wnz[:_wnz.index('    def ', 10)]
        pruefe('self.root.winfo_ismapped()' in _wnz,
               'unterschieden am Fenster selbst, nicht am Knopf')
    finally:
        if _alt_home44 is None:
            os.environ.pop('SC_BP_HOME', None)
        else:
            os.environ['SC_BP_HOME'] = _alt_home44

    print()
    print('45. Kein totes Bild in der Anleitung')
    # ⚠ Gefunden am 28.08.2026 beim Ergaenzen der Funktionsliste: Drei Bilder
    # in der Tabelle zeigten ins Leere — `symbole/22/punkt-blau.png` (zweimal)
    # und `symbole/22/gemerkt-gruen.png`. Beides sind **Zeilen**-Symbole, und die
    # werden nur bis 18 px gebaut (`tools/symbole_bauen.py`: ZEILE geht bis 18,
    # KNOPF bis 30). Auf GitHub stand dort ein kaputtes Bild-Kaestchen — in der
    # Funktionsliste, also auf dem, was ein Interessierter als Erstes sieht.
    #
    # Niemand hat es gemeldet, weil ein fehlendes Bild niemandem wehtut. Genau
    # deshalb gehoert es in den Selbsttest: Wer ein Symbol umbenennt oder eine
    # Groesse nicht baut, erfaehrt es hier statt gar nicht.
    import re as _re45
    _tot45 = []
    for _d45 in ('README.md', 'README.de.md', 'CHANGELOG.md', 'CHANGELOG.de.md',
                 'ROADMAP.md', 'ROADMAP.de.md'):
        _pfad45 = os.path.join(WURZEL, _d45)
        if not os.path.exists(_pfad45):
            continue
        _inhalt45 = open(_pfad45, encoding='utf-8').read()
        _bilder45 = (_re45.findall(r'src="([^":]+)"', _inhalt45)
                     + _re45.findall(r'!\[[^\]]*\]\(([^):]+)\)', _inhalt45))
        for _b45 in _bilder45:
            if not os.path.exists(os.path.join(WURZEL, _b45)):
                _tot45.append('%s -> %s' % (_d45, _b45))
    for _z45 in _tot45:
        print('         ' + _z45)
    pruefe(not _tot45,
           'jedes Bild in der Doku liegt auch im Repo (%d tote)' % len(_tot45))

    print()
    print('46. Ein Fund ist ein Fund - kein Wartezustand mehr')
    # ⚠ Bis v3.0.0-rc94 stand ein Bauplan aus der Game.log GELB da: „vorlaeufig",
    # bis die Launcher-Datei ihn auf Gruen bestaetigt. Diese Bestaetigung kann es
    # nicht mehr geben — die Game.log ist die Quelle, der Launcher nur noch eine
    # Ergaenzung. Uebrig blieb ein Zustand, aus dem nichts mehr herausfuehrt:
    # Wer den Launcher hatte, sah dauerhaft Gelb; wer ihn nicht hat, dauerhaft
    # Gruen — bei genau derselben Sicherheit.
    #
    # Gemeldet am 28.08.2026: die Bestaetigung wird „nicht nur nicht mehr
    # gebraucht, sondern kann auch gar nicht mehr geben".
    #
    # Diese Pruefung haelt fest, dass die Mechanik WEG ist und nicht nur
    # stillgelegt — halb entfernter Code kommt sonst beim naechsten Umbau
    # zurueck.
    _q46 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'), encoding='utf-8').read()
    for _rest46 in ('provisional', '_match_prov', 'self.prov',
                    "'vorlaeufig'", "'confirm'"):
        pruefe(_rest46 not in _q46,
               'keine Spur mehr von %s im Programm' % _rest46)
    from scbp import sprache as sp46
    pruefe('vorlaeufig' not in sp46.TEXTE,
           'und der Text „vorlaeufig" ist aus der Sprachdatei raus')
    # ⚠ Und die Anleitung darf die zwei Stufen nicht weiter versprechen — sonst
    #   sucht jemand einen gelben Punkt, den es nicht gibt.
    for _d46 in ('README.de.md', 'README.md'):
        _t46 = open(os.path.join(WURZEL, _d46), encoding='utf-8').read()
        pruefe('vorlaeufig-gelb' not in _t46,
               '%s zeigt keinen gelben Wartepunkt mehr' % _d46)

    print()
    print('47. Protokolle lassen sich erneut einlesen')
    # ⚠ Gemeldet am 28.08.2026, wenige Stunden nach v3.0.0: Ein
    # Bauplan kam an, waehrend der Watcher zu war und Star Citizen weiterlief.
    # Beim naechsten Start war er weg — und zwar dauerhaft.
    #
    # Der Grund: `nachlesen()` fasste die laufende Game.log nur an, wenn sie
    # NOCH NIE gelesen war. Danach galt sie als erledigt, das Mitlesen setzte
    # beim gemerkten Stand an, und alles davor war unerreichbar. In
    # `logbackups/` landet die Datei erst beim naechsten Spielstart.
    #
    # Gemessen: Bauplan bei Byte 11.987.664, Lesestand 12.759.872.
    _q47 = open(os.path.join(WURZEL, 'scbp', 'logquelle.py'),
                encoding='utf-8').read()
    _lauf47 = _q47[_q47.index('if auch_laufende:'):]
    _lauf47 = _lauf47[:_lauf47.index('bericht[')]
    # ⚠ Nur den Code ansehen. Die alte Bedingung steht als Zitat im Kommentar
    #   daneben — wer die Zeilen nicht filtert, prueft die Erklaerung statt der
    #   Sache und meldet einen Fehler, den es nicht gibt.
    _code47 = chr(10).join(z for z in _lauf47.split(chr(10))
                           if not z.lstrip().startswith('#'))
    pruefe("aktiv_holen(aktiv) is None" not in _code47,
           'die laufende Game.log wird immer gelesen, nicht nur beim ersten Mal')
    from scbp import logquelle as lq47
    pruefe(hasattr(lq47, 'alles_neu'),
           'es gibt einen Weg, alles noch einmal einzulesen')

    # ⚠ Und beides muss BEDIENBAR sein — an zwei Stellen, wie gewuenscht:
    #    am Overlay (dort merkt man den fehlenden Bauplan) und in den
    #    Einstellungen (dort sucht man danach).
    from scbp import overlay as ov47
    pruefe(hasattr(ov47, 'neu_einlesen_anstossen'),
           'der Anstoss geht ueber einen Rueckruf wie beim Schloss')
    _w47 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'), encoding='utf-8').read()
    pruefe('self.neulesen_lbl' in _w47, 'ein Knopf sitzt in der Overlay-Leiste')
    _s47 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'), encoding='utf-8').read()
    pruefe("t('s_be_neu')" in _s47, 'und einer in den Einstellungen')
    # ⚠ Die Arbeit gehoert in den Watcher-Faden. Laese die Seite selbst ein und
    #   speicherte, ueberschriebe der Faden das beim naechsten Fund mit seinem
    #   aelteren Stand — die gefundenen Bauplaene waeren wieder weg.
    pruefe('alles_neu' not in _s47,
           'die Seite liest NICHT selbst ein (der Bestand hat einen Besitzer)')

    print()
    print('48. Nach einer neuen Fassung wird immer wieder gesehen')
    # ⚠ Gemeldet am 28.08.2026: v3.0.1 war draussen, der laufende
    # Watcher schwieg — obwohl er die Fassung laengst abgerufen hatte und sie in
    # seinem Zwischenspeicher stand.
    #
    # Der Grund: `_nach_version_sehen()` wurde GENAU EINMAL gerufen, zwei
    # Sekunden nach dem Start. Der Stundenabstand in `aktualisierung.nachsehen()`
    # begrenzt nur, wie oft gefragt werden DARF — fragen muss trotzdem jemand.
    # Wer den Watcher durchlaufen liess, erfuhr nie von einer neuen Fassung.
    _w48 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'), encoding='utf-8').read()
    _f48 = _w48[_w48.index('def _nach_version_sehen'):]
    _f48 = _f48[:_f48.index('    def ', 10)]
    pruefe('_nach_version_sehen' in _f48.split('def _nach_version_sehen', 1)[1],
           'die Pruefung plant sich selbst wieder ein')
    pruefe('VERSION_TAKT' in _f48, 'und zwar in einem benannten Takt')

    # ⚠ Und ein erwarteter Fehler darf das Protokoll nicht fluten: Beim Download
    #   kommt der Fortschritt im Sekundentakt; geht dabei das Fenster zu, wirft
    #   jeder Aufruf. Ein Bericht zeigte 50 von 50 Plaetzen mit derselben
    #   Meldung — jeder echte Fehler war daraus verdraengt.
    _s48 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'), encoding='utf-8').read()
    pruefe('_IM_TK_GEMELDET' in _s48,
           'derselbe erwartete Fehler wird nur einmal gemerkt')

    print()
    print('49. Jeder Sprachschluessel, der gerufen wird, gibt es auch')
    # ⚠ Gemeldet am 28.08.2026: Am Raketen-Symbol stand als Hinweis
    # woertlich `s_sp_start` — der Schluesselname statt des Textes.
    #
    # `t()` gibt den Schluessel zurueck, wenn die Tabelle ihn nicht kennt. Das
    # ist als Notnagel richtig (besser als ein Absturz), macht den Fehler aber
    # unsichtbar, bis ihn jemand im laufenden Programm sieht. Der Selbsttest
    # pruefte bis dahin nur, ob deutscher Text in der englischen Oberflaeche
    # steht — ein FEHLENDER Schluessel ist etwas anderes.
    #
    # Die Pruefung fand auf einen Schlag drei: `s_sp_start`, `m_keine_fassung`
    # und `aktuelle_fassung`. Von Hand ist das bei ueber 600 Eintraegen nicht zu
    # halten.
    import ast as _ast49
    from scbp import sprache as _sp49

    _RUFER49 = ('t', 'Satz', 'text')
    _fehlend49 = []
    for _ordner49, _unter49, _dateien49 in os.walk(WURZEL):
        if any(_teil in _ordner49 for _teil in
               ('.git', 'build', 'dist', '__pycache__', 'tools')):
            continue
        for _name49 in _dateien49:
            if not _name49.endswith('.py'):
                continue
            _pfad49 = os.path.join(_ordner49, _name49)
            try:
                _baum49 = _ast49.parse(open(_pfad49, encoding='utf-8').read())
            except Exception:
                continue
            for _kn49 in _ast49.walk(_baum49):
                if not isinstance(_kn49, _ast49.Call) or not _kn49.args:
                    continue
                _f49 = _kn49.func
                _ruf49 = (_f49.attr if isinstance(_f49, _ast49.Attribute)
                          else (_f49.id if isinstance(_f49, _ast49.Name) else None))
                if _ruf49 not in _RUFER49:
                    continue
                _erst49 = _kn49.args[0]
                if not isinstance(_erst49, _ast49.Constant):
                    continue
                if not isinstance(_erst49.value, str) or not _erst49.value:
                    continue
                if _erst49.value not in _sp49.TEXTE:
                    _fehlend49.append('%s:%d  %s(%r)' % (
                        os.path.relpath(_pfad49, WURZEL), _kn49.lineno,
                        _ruf49, _erst49.value))
    for _z49 in sorted(set(_fehlend49)):
        print('         ' + _z49)
    pruefe(not _fehlend49,
           'kein Aufruf zeigt den Schluesselnamen statt des Textes (%d)'
           % len(set(_fehlend49)))

    print()
    print('50. Der Autostart merkt sich einen Pfad, den es morgen noch gibt')
    # ⚠ Gefunden am 29.08.2026 auf einem Linux-Rechner: In der Autostart-Datei
    # stand `Exec=/tmp/.mount_SC-BP-ji95vH/usr/bin/SC-BP-Watcher` — der temporaere
    # Einhaengepunkt des AppImage. Der bekommt bei JEDEM Start einen neuen
    # Zufallsnamen. Folge: Der Watcher startete nach einem Neustart nie wieder,
    # ohne Fehlermeldung — die Datei sah ja voellig richtig aus.
    #
    # Ursache war die Reihenfolge: Ein AppImage ist ebenfalls `sys.frozen`, also
    # gewann die frozen-Abfrage und `APPIMAGE` kam nie dran. Genau das wird hier
    # geprueft, weil es sich nur an der Reihenfolge entscheidet und ein spaeteres
    # Umsortieren den Fehler lautlos zurueckholen wuerde.
    import importlib as _im50
    from scbp import autostart as _as50
    _alt_appimage50 = os.environ.get('APPIMAGE')
    _alt_frozen50 = getattr(sys, 'frozen', None)
    try:
        os.environ['APPIMAGE'] = '/home/wer/Programme/SC-BP-Watcher.AppImage'
        sys.frozen = True
        _im50.reload(_as50)
        _befehl50 = _as50.befehl()
        pruefe('/tmp/.mount' not in _befehl50,
               'kein Wegwerf-Pfad aus dem AppImage-Einhaengepunkt')
        pruefe(_befehl50 == '/home/wer/Programme/SC-BP-Watcher.AppImage',
               'die echte AppImage-Datei gewinnt gegen die frozen-Abfrage')
    finally:
        if _alt_appimage50 is None:
            os.environ.pop('APPIMAGE', None)
        else:
            os.environ['APPIMAGE'] = _alt_appimage50
        if _alt_frozen50 is None:
            try:
                del sys.frozen
            except AttributeError:
                pass
        else:
            sys.frozen = _alt_frozen50
        _im50.reload(_as50)
    print()
    print('51. Angenommene Auftraege: bringt der etwas, das mir fehlt?')
    # Der Weg hat vier Glieder (Log -> Phrase -> Missionsschluessel -> Katalog).
    # Geprueft wird jedes einzeln, damit ein Bruch benannt werden kann statt nur
    # "meldet nichts". Die Daten werden nachgebaut — auf dem Bau-Rechner gibt es
    # weder Spiel noch Katalog.
    import importlib as _im51
    from scbp import auftraege as _au51

    # a) Die Marken des eigenen Werkzeugs muessen aus dem Titel verschwinden.
    _faelle51 = [
        ('Retake Platforms From Nine Tails <EM4>[BP!]</EM4>',
         'Retake Platforms From Nine Tails'),
        ('Retake Platforms[SCBPW] <EM4>[BP 4/8]</EM4>[/SCBPW]', 'Retake Platforms'),
        ('Ganz normaler Titel', 'Ganz normaler Titel'),
    ]
    for _roh51, _soll51 in _faelle51:
        pruefe(_au51.sauber(_roh51) == _soll51, 'Marken entfernt: %s' % _soll51[:34])

    # b) ⚠ Die Phrase kommt aus der global.ini MIT Platzhalter (`... : %s`).
    #    Bliebe er stehen, passte die Zeile nie — die Funktion waere tot und
    #    niemand haette es gemerkt.
    pruefe(_au51._phrase_kuerzen('Auftrag angenommen: %s') == 'Auftrag angenommen',
           'der Platzhalter am Phrasen-Ende faellt weg')

    # c) Das Suchmuster muss die echte Logzeile treffen — und die Zwischenziele
    #    in Ruhe lassen. ⚠ Auf Deutsch heissen `MissionEvent_Available` UND
    #    `ObjectiveEvent_Activated` beide "Neuer Auftrag"; wer darauf hoert,
    #    meldet bei jedem Etappenziel.
    _m51 = _au51.muster()
    _treffer51 = _m51.findall(
        'Added notification "Auftrag angenommen: Retake Platforms: "\n'
        'Added notification "Contract Accepted: Data Transfer: "\n')
    pruefe(_treffer51 == ['Retake Platforms', 'Data Transfer'],
           'Annahme wird erkannt, deutsch und englisch')
    pruefe(not _m51.findall('Added notification "Neuer Auftrag: Koerper durchsuchen: "'),
           'ein Zwischenziel loest NICHTS aus')
    pruefe(not _m51.findall('Added notification "Auftrag zurueckgezogen: Irgendwas: "'),
           'ein zurueckgezogener Auftrag loest NICHTS aus')

    # d) Die Auswertung selbst, mit nachgebautem Katalog.
    _alt51 = _au51._missionen, _au51._index, _au51._muster_index
    try:
        _au51._missionen = {'test_title_001': {'bp': ['Alpha BP', 'Beta BP', 'Gamma BP']}}
        _au51._index = {'testauftrag': 'test_title_001'}
        _au51._muster_index = []
        _hat51 = lambda n: n in ('Alpha BP', 'Beta BP')
        pruefe(_au51.pruefen('Testauftrag', _hat51) == (3, ['Gamma BP']),
               'meldet Gesamtzahl und was davon fehlt')
        pruefe(_au51.pruefen('Testauftrag', lambda n: True) == (3, []),
               'hat man alles, bleibt die Liste leer')
        pruefe(_au51.pruefen('Voellig unbekannter Auftrag', _hat51) is None,
               'unbekannter Auftrag: es wird GESCHWIEGEN, nicht geraten')
        # ⚠ Platzhalter-Titel: 58 von 353 tragen `~mission(...)`, ein woertlicher
        #    Vergleich scheitert dort. Der Rest muss trotzdem woertlich passen.
        _au51._index = {}
        _au51._muster_index = [(__import__('re').compile(r'^High\-Risk Bounty: .+$'),
                                'test_title_001')]
        pruefe(_au51.pruefen('High-Risk Bounty: Jemand', _hat51) == (3, ['Gamma BP']),
               'Platzhalter-Titel werden ueber ein Muster gefunden')
        pruefe(_au51.pruefen('Low-Risk Bounty: Jemand', _hat51) is None,
               'und das Muster passt nicht auf einen anderen Auftragstyp')
    finally:
        _au51._missionen, _au51._index, _au51._muster_index = _alt51

    # e) Jeder Text der neuen Zeile muss in BEIDEN Sprachen dastehen.
    from scbp import sprache as _sp51
    for _k51 in ('auftrag_zeile', 'auftrag_fehlt', 'auftrag_fehlt_mehr',
                 'auftrag_komplett'):
        _w51 = _sp51.TEXTE.get(_k51)
        pruefe(bool(_w51) and len(_w51) == 2 and all(_w51),
               'Text %s gibt es deutsch und englisch' % _k51)

    # f) Der Log-Leser darf den Bauplan-Weg nicht angetastet haben.
    from scbp import logquelle as _lq51
    _tail51 = _lq51.LogTail(_lq51.Lesestand())
    pruefe(getattr(_tail51, 'auftrag_muster', 'fehlt') is None,
           'ein frischer LogTail sucht KEINE Auftraege (muss gesetzt werden)')
    pruefe(_tail51.auftraege == [],
           'und traegt eine leere Auftragsliste')
    # ⚠ Der Bauplan-Weg darf sich nicht veraendert haben: `new_names()` liefert
    #    weiterhin Paare (Name, Zusatz) — mehrere Stellen verlassen sich darauf.
    pruefe(_lq51.LogTail.new_names.__doc__ and
           'Name, Zusatz' in _lq51.LogTail.new_names.__doc__,
           'new_names() liefert unveraendert (Name, Zusatz)')

    # ------------------------------------------------------------------
    # 52. Kaestchen nur an Bauplaene — nicht an Regionen und Abgabeorte
    #
    # Die Bloecke des SCDL-Teams gliedern mit '#'-Ueberschriften, und unter
    # dreien davon stehen Listen: '# Baupläne' (4379 Zeilen), '# Abgabe' (323)
    # und '# Region' (239). Bis zum 29.08.2026 bekam jede davon ein Kaestchen —
    # im Spiel stand '[  ] Stanton-System - Gefahr 4-6/10', als koennte man eine
    # Region besitzen. Rund 620 Zeilen in den Rohdaten, 838 in der fertigen
    # Datei (Bloecke werden mehrfach verwendet).
    print()
    print('52. Kaestchen nur an Bauplaenen, nicht an Regionen')
    from scbp import injektion as _inj52
    _block52 = ('\\n# Baupläne:\\n    - Atzkav Sniper Rifle\\n    - Aril Arms'
                '\\n\\n# Region: \\n    - Stanton-System - Gefahr 4-6/10'
                '\\n    - \\n    - Nyx-System - Gefahr 3-6/10'
                '\\n\\n# Abgabe:\\n    - Port Olisar')
    _habe52 = {katalog._norm('Aril Arms')}
    _neu52, _meine52, _gesamt52 = _inj52._kaestchen_setzen(_block52, _habe52)
    pruefe('[  ] Atzkav Sniper Rifle' in _neu52,
           'ein Bauplan, den man nicht hat, bekommt ein leeres Kaestchen')
    pruefe('[x]' in _neu52 and 'Aril Arms' in _neu52,
           'ein Bauplan, den man hat, wird angehakt')
    pruefe('- Stanton-System - Gefahr 4-6/10' in _neu52
           and '[  ] Stanton-System' not in _neu52,
           'eine REGION bekommt KEIN Kaestchen')
    pruefe('- Nyx-System - Gefahr 3-6/10' in _neu52,
           'auch die zweite Region bleibt unangetastet')
    pruefe('- Port Olisar' in _neu52 and '[  ] Port Olisar' not in _neu52,
           'ein ABGABEORT bekommt KEIN Kaestchen')
    pruefe((_meine52, _gesamt52) == (1, 2),
           'gezaehlt werden nur die Bauplaene (1 von 2)')
    # Englisch ist derselbe Aufbau, nur andere Ueberschriften.
    _en52 = ('\\n# Blueprints:\\n    - Atzkav Sniper Rifle'
             '\\n\\n# Region: \\n    - Stanton System'
             '\\n\\n# Delivery:\\n    - Port Olisar')
    _neu52en, _m52en, _g52en = _inj52._kaestchen_setzen(_en52, set())
    pruefe('[  ] Atzkav Sniper Rifle' in _neu52en and _g52en == 1,
           'englisch: nur unter "# Blueprints" wird angekreuzt')
    pruefe('- Stanton System' in _neu52en and '- Port Olisar' in _neu52en,
           'englisch: Region und Delivery bleiben unangetastet')

    # 52b. Kein Knopf schneidet seine Beschriftung ab
    #
    # `_knopf` bemisst die Leinwand mit `schrift.measure()`. Gezeichnet wird
    # aber mit der Schrift, die das System hergibt — weichen die ab, steht der
    # Text ueber den Rand und wird beidseitig abgeschnitten. Am 29.08.2026 in
    # rc7 gemeldet: Auf dem Knopf stand „erung speichern".
    print()
    print('52b. Knoepfe schneiden ihre Beschriftung nicht ab')
    import tkinter as _tk52b
    from scbp import seiten as _se52b
    from scbp.hauptfenster import Hauptfenster as _HF52b
    _w52b = _tk52b.Tk()
    try:
        _f52b = _HF52b(_w52b, version='knopfprobe')
        _w52b.update_idletasks()
        # ⚠ `s_lg_trotzdem` gibt es nicht mehr (der Ausweg ist entfallen).
        # Statt seiner der laengste verbliebene Lager-Knopf.
        _lang = [_sp51.TEXTE[k][0] for k in
                 ('s_lg_speichern', 's_lg_abbrechen', 's_lg_posten_weg',
                  's_lg_eintragen')]
        _lang += [_sp51.TEXTE[k][1] for k in
                  ('s_lg_speichern', 's_lg_posten_weg')]
        _eng52b = []
        for _txt in _lang:
            _k = _se52b._knopf(_f52b, _w52b, _txt, lambda: None)
            # ⚠ Nur den TEXT messen. `bbox('all')` nimmt den Rahmen mit, und
            # der ist naturgemaess so breit wie die Leinwand — die Pruefung
            # schluege dann immer an.
            _text_ids = [_i for _i in _k.find_all()
                         if _k.type(_i) == 'text']
            _kasten = _k.bbox(_text_ids[0]) if _text_ids else None
            _breit = int(_k['width'])
            if _kasten and (_kasten[2] - _kasten[0]) > _breit:
                _eng52b.append('%r braucht %d, hat %d'
                               % (_txt, _kasten[2] - _kasten[0], _breit))
            _k.destroy()
        pruefe(not _eng52b,
               'jeder Knopf ist breit genug fuer seinen Text (%d zu eng)'
               % len(_eng52b))
        for _e in _eng52b[:4]:
            print('       ·', _e)
    finally:
        _w52b.destroy()

    # 52c. Die Mindestbreite des Overlays ist keine Fantasiezahl
    #
    # Der erste Anlauf fragte die Kopfleiste nach ihrer Wunschbreite. Die laeuft
    # aber mit `pack_propagate(False)` und meldete **1 Pixel** — die Grenze war
    # damit wirkungslos, und im Overlay war kein Symbol mehr zu sehen.
    print()
    print('52c. Mindestbreite des Overlays deckt die Symbolleiste')
    import importlib.util as _ilu52c
    _spec52c = _ilu52c.spec_from_file_location(
        '_scbpw52c', os.path.join(_wurzelpfad, 'sc_bp_watcher.py'))
    _m52c = _ilu52c.module_from_spec(_spec52c)
    sys.modules['_scbpw52c'] = _m52c
    _spec52c.loader.exec_module(_m52c)
    _ov52c = _m52c.Overlay()
    try:
        _ov52c.root.update_idletasks()
        _kinder52c = _ov52c.kopf.winfo_children()
        pruefe(len(_kinder52c) >= 5,
               'die Kopfleiste hat ihre Elemente (%d)' % len(_kinder52c))
        _summe52c = sum(_k.winfo_reqwidth() for _k in _kinder52c)
        _min52c = _ov52c._mindestbreite()
        pruefe(_min52c >= _summe52c,
               'die Mindestbreite deckt alle Elemente (%d >= %d)'
               % (_min52c, _summe52c))
        pruefe(_min52c > _ov52c.kopf.winfo_reqwidth(),
               'sie stuetzt sich NICHT auf die Wunschbreite der Leiste')
        pruefe(_ov52c.root.winfo_width() >= _min52c,
               'und das Fenster ist mindestens so breit')
    finally:
        _ov52c.root.destroy()

    # 52d. Suchfelder vergessen ihren Inhalt beim naechsten Aufruf
    #
    # Seiten werden EINMAL gebaut und danach nur ein- und ausgeblendet. Ohne
    # Rueckruf stand der Suchbegriff von vorhin noch da: „da sollte man den
    # Titan-Eintrag im Suchfeld nicht speichern" (29.08.2026).
    print()
    print('52d. Suchfelder sind beim erneuten Aufrufen leer')
    _w52d = _tk52b.Tk()
    try:
        _f52d = _HF52b(_w52d, version='suchprobe')
        for _seite in ('bergbau', 'herstellung'):
            _f52d.oeffnen(_seite)
        _w52d.update_idletasks()
        pruefe(hasattr(_f52d, 'beim_zeigen'),
               'das Fenster fuehrt ein Verzeichnis fuer das erneute Anzeigen')
        # ⚠ Im Wegwerf-Ordner fehlen Bergbau- und Rezeptdaten; die Seiten
        # brechen dann vor dem Suchfeld ab. Ob sie sich anmelden, steht
        # deshalb im Quelltext — datenunabhaengig und trotzdem verbindlich.
        with open(os.path.join(_wurzelpfad, 'scbp', 'seiten.py'),
                  encoding='utf-8') as _fh52d:
            _qu52d = _fh52d.read()
        for _seite in ('bergbau', 'herstellung'):
            pruefe("beim_zeigen['%s']" % _seite in _qu52d,
                   'Seite %s meldet sich fuers erneute Anzeigen an' % _seite)
        pruefe(_qu52d.count('_suche_leeren_kreuz(') >= 3,
               'beide Suchfelder haben ein Kreuz zum Leeren')
        # Und der Rueckruf muss auch wirklich leeren.
        _leer52d = []
        for _seite, _ruf in _f52d.beim_zeigen.items():
            try:
                _ruf()
            except Exception as _a:
                _leer52d.append('%s: %s' % (_seite, _a))
        pruefe(not _leer52d, 'die Rueckrufe laufen fehlerfrei (%d Fehler)'
               % len(_leer52d))
    finally:
        _w52d.destroy()

    # 52e. Unterarten — Waffenart und Ruestungsrolle
    #
    # Der Katalog kennt nur `WeaponGun`; welche davon ballistisch sind und
    # welche Laser, steht ausschliesslich in den Rezeptdaten. Umgekehrt kennt
    # er die Koerperteile der Ruestung, die dort fehlen. Erst beide zusammen
    # ergeben die Filter, nach denen am 29.08.2026 gefragt wurde: „ich weiss
    # grad nicht, welche Ballistik sind, welche Laser".
    print()
    print('52e. Unterarten aus den Rezeptdaten')
    from scbp import herstellung as _he52e
    _echt52e = _he52e.einordnung
    _he52e.einordnung = lambda: {
        'zehnserieskanone': ('weapons', 'ballistic'),
        'laserkanone': ('weapons', 'laser'),
        'kampfhelm': ('armour', 'combat'),
        'kuehlerzwei': ('cooler', 'size2'),
    }
    try:
        pruefe(_he52e.unterart_von('Zehn-Series Kanone') == 'ballistic',
               'die Waffenart kommt aus den Rezeptdaten')
        pruefe(_he52e.art_von('Kampfhelm') == 'armour',
               'und die Art dazu')
        pruefe(_he52e.unterart_von('gibt es nicht') == '',
               'ein unbekannter Name ergibt keine Unterart')
    finally:
        _he52e.einordnung = _echt52e
    # Anzeigenamen: zweisprachig und mit Rueckfall auf den Rohwert
    for _k52e in ('he_art_weapons', 'he_art_armour', 'he_sub_ballistic',
                  'he_sub_laser', 'he_sub_combat', 'he_sub_stealth'):
        _w52e = _sp51.TEXTE.get(_k52e)
        pruefe(bool(_w52e) and len(_w52e) == 2 and all(_w52e),
               'Anzeigename %s gibt es deutsch und englisch' % _k52e)
    pruefe(_he52e.unterartname('gibtsnichtimmer') == 'gibtsnichtimmer',
           'eine unbekannte Unterart wird roh gezeigt statt verschluckt')
    for _k52e in ('ff_alle_unterarten', 'ff_alle_rollen', 'ff_alle_hersteller',
                  'ff_alle_zustaende', 'ff_zustand_habe', 'ff_zustand_fehlt',
                  's_bg_alle_erze', 's_bg_alle_orte', 'merk_eigene',
                  'merk_wartet', 'merk_eigene_h'):
        _w52e = _sp51.TEXTE.get(_k52e)
        pruefe(bool(_w52e) and len(_w52e) == 2 and all(_w52e),
               'Text %s gibt es deutsch und englisch' % _k52e)

    # 52f. Zwei Ebenen statt einer langen Liste
    #
    # Die Art-Auswahl hatte dreissig Eintraege — „Ruestung (Arme)",
    # „Ruestung (Beine)", „Helm", „Rucksack" je einzeln. Die Gliederung folgt
    # jetzt der gepflegten Vergleichsliste: sieben Gruppen, darunter die feinen Arten.
    # Gemessen an echten Daten deckt sie sich mit dieser Liste exakt.
    print()
    print('52f. Ober- und Unterkategorie')
    from scbp import kategorien as _ka52f
    # Die feine Waffenart steckt im Tag — nur dort.
    pruefe(_ka52f.einordnen(tag='BP_CRAFT_APAR_BallisticGatling_S4')
           == (_ka52f.SCHIFFSWAFFE, 'ballistic_gatling'),
           'die ballistische Gatling wird aus dem Tag erkannt')
    pruefe(_ka52f.einordnen(tag='BP_CRAFT_HRST_LaserScatterGun_S1')
           == (_ka52f.SCHIFFSWAFFE, 'scatter_gun'),
           'auch die Scattergun — ihr Tag heisst LaserScatterGun')
    pruefe(_ka52f.einordnen(tag='BP_CRAFT_APAR_BallisticScatterGun_S1')
           == (_ka52f.SCHIFFSWAFFE, 'scatter_gun'),
           'und die ballistische Fassung ebenso')
    # ⚠ Ohne die Reihenfolge im Muster wuerde `ScatterGun` das laengere Wort
    # schlucken — sechs von sieben Scatterguns fielen durch.
    pruefe(_ka52f.einordnen(tag='BP_CRAFT_behr_lmg_ballistic_01_mag')
           == (_ka52f.AUSRUESTUNG, 'magazin'),
           'Magazine erkennt man am Tag-Ende, nicht an der Katalog-Art')
    pruefe(_ka52f.einordnen(art='Char_Armor_Helmet')
           == (_ka52f.RUESTUNG, 'helm'),
           'Koerperteile kommen aus der Katalog-Art')
    pruefe(_ka52f.einordnen(art='Char_Armor_Legs')
           == (_ka52f.RUESTUNG, 'beine'), 'Beine ebenso')
    pruefe(_ka52f.einordnen(unterart='sniper')
           == (_ka52f.FPS_WAFFE, 'sniper'),
           'FPS-Waffen kommen aus dem Rezept-Untertyp')
    # Was sich nicht buendeln laesst, bleibt allein stehen — nicht in einem
    # Sammeltopf.
    _einzeln = _ka52f.einordnen(art='DockingCollarXY')
    pruefe(not _ka52f.ist_gruppe(_einzeln[0])
           and _ka52f.rohe_art(_einzeln[0]) == 'DockingCollarXY',
           'eine unbekannte Art bleibt als eigener Eintrag stehen')
    for _k52f in ('kat_ober_schiffswaffe', 'kat_ober_ruestung',
                  'kat_unter_ballistic_gatling', 'kat_unter_scatter_gun',
                  'kat_unter_helm', 'kat_unter_magazin',
                  'ff_unterart_waehlen'):
        _w52f = _sp51.TEXTE.get(_k52f)
        pruefe(bool(_w52f) and len(_w52f) == 2 and all(_w52f),
               'Text %s gibt es deutsch und englisch' % _k52f)

    # 52g. Beobachtungs-Muster treffen an Wortgrenzen
    #
    # Ein blosses „steckt drin" liefert falsche Treffer, die niemand als solche
    # erkennt: `arden backpack` traf am 29.08.2026 auf *Warden Backpack
    # Purgatory Camo*, und der Watcher meldete ein Ruestungsteil als
    # verfuegbar, das mit der gesuchten Ausruestung nichts zu tun hat. Bei
    # einer Staffelruestung geht es um genau ein Teil je Platz — die Farben
    # sind ueber Monate auf Tarnung getestet.
    print()
    print('52g. Muster treffen nur an Wortgrenzen')
    from scbp import merkliste as _mk52g
    _eintrag52g = {'titel': 'Probe', 'muster': ['xyz-cl backpack beispiel']}
    pruefe(_mk52g._muster_trifft(_eintrag52g, 'xyz-cl backpack beispiel'),
           'das gesuchte Teil wird erkannt')
    pruefe(not _mk52g._muster_trifft(
               {'titel': 'P', 'muster': ['yz backpack']},
               'xyz backpack muster camo'),
           'ein Muster mitten im Wort trifft NICHT')
    pruefe(_mk52g._muster_trifft(
               {'titel': 'P', 'muster': ['abc-mk4 legs grey']},
               'abc-mk4 legs grey'),
           'Bindestriche und Leerzeichen zaehlen als Grenze')
    pruefe(not _mk52g._muster_trifft({'titel': 'P', 'muster': []}, 'irgendwas'),
           'ein Eintrag ohne Muster trifft nichts')
    pruefe(not _mk52g._muster_trifft({'titel': 'P', 'muster': ['']}, 'irgendwas'),
           'ein leeres Muster ebenso wenig')

    # 52h. Die Kategorie wird an genau EINER Stelle geprueft
    #
    # Bis rc19 gab es eine zweite: eine Abkuerzung, die ganze Gruppen vorab
    # aussortierte und dabei Katalog-Art gegen Oberkategorie verglich. Das
    # trifft nie zu — jede Gruppe fiel heraus, die Liste zeigte „Nichts
    # gefunden" bei 157 vorhandenen Bauplaenen. Zwei Stellen fuer dieselbe
    # Frage waren genau eine zu viel.
    print()
    print('52h. Kategorie-Pruefung nur an einer Stelle')
    with open(os.path.join(_wurzelpfad, 'scbp', 'bestandsfenster.py'),
              encoding='utf-8') as _fh52h:
        _qu52h = _fh52h.read()
    pruefe("art_kennung(liste[0])" not in _qu52h,
           'keine Gruppen-Vorpruefung ueber die Katalog-Art mehr')
    pruefe(_qu52h.count("!= self.fein['art']") <= 1,
           'die Art wird hoechstens an einer Stelle verglichen')

    # 52i. Suche nach dem Auftrag
    #
    # „Retake" fand bis rc21 nichts, obwohl sechs Bauplaene aus Auftraegen mit
    # diesem Wort stammen. Wer eine Quest fliegt, will wissen, was dabei
    # herausspringt.
    print()
    print('52i. Nach Auftrag, Fraktion und Auftragsart suchen')
    from scbp import bestandsfenster as _bf52i
    _bp52i = {'n': 'Test-Bauplan', 'a': 'Cooler', 'q': [
        {'auftrag': 'Retake Platforms From Nine Tails', 'typ': 'Mercenary',
         'fraktion': 'Headhunters', 'wo': {'ort': 'Stanton'}}]}
    pruefe(_bf52i._passt(_bp52i, 'retake'), 'der Auftragsname wird gefunden')
    pruefe(_bf52i._passt(_bp52i, 'headhunters'), 'die Fraktion ebenso')
    pruefe(_bf52i._passt(_bp52i, 'mercenary'), 'und die Auftragsart')
    pruefe(not _bf52i._passt(_bp52i, 'xenothreat'),
           'ein fremder Begriff trifft nicht')
    # ⚠ `wo` ist ein Objekt, kein Text — ohne Pruefung stuerzt die Suche bei
    # jedem Tastendruck ab, und weil das im Zeichnen passiert, haengt das
    # Fenster.
    pruefe(_bf52i._passt(_bp52i, 'test-bauplan'),
           'ein Objekt in den Herkunftsangaben laesst die Suche nicht abstuerzen')
    _kat52i = {'bauplaene': {'x': _bp52i, 'y': dict(_bp52i, n='Zweiter')}}
    pruefe(_bf52i.auftraege_zu('retake', _kat52i)
           == [('Retake Platforms From Nine Tails', 2)],
           'die Uebersicht zaehlt die Bauplaene je Auftrag')
    pruefe(_bf52i.auftraege_zu('', _kat52i) == [],
           'ohne Suchbegriff keine Auftragsliste')
    # ⚠ Die Auftragszeile muss anklickbar sein: „die Quest muss natuerlich
    # anklickbar sein, sonst bringt das nichts." Ein Filter, aus dem man nicht
    # herauskommt, waere allerdings schlimmer als keiner — deshalb schaltet
    # derselbe Auftrag beim zweiten Klick wieder ab.
    with open(os.path.join(_wurzelpfad, 'scbp', 'bestandsfenster.py'),
              encoding='utf-8') as _fh52j:
        _qu52j = _fh52j.read()
    pruefe('_auftrag_waehlen' in _qu52j,
           'die Auftragszeilen sind anklickbar')
    pruefe("self.auftrag = '' if self.auftrag == name else name" in _qu52j,
           'ein zweiter Klick loest den Auftrag wieder')
    pruefe("or bool(self.auftrag)" in _qu52j,
           'der Zuruecksetzen-Knopf erscheint auch bei gewaehltem Auftrag')

    # 52k. Ein alter Katalog bekommt neue Schluessel
    #
    # Der Katalog auf der Platte kann Monate alt sein. Am 29.08.2026 standen
    # dort Magazine noch als „… magazine (15 cap)", waehrend der Bestand sie
    # als „… magazine (15)" fuehrt — die Angleichung der Mengenangabe kam
    # spaeter dazu. Ergebnis: Das Overlay meldete 405 Bauplaene, der
    # Fortschritt 382 von 738, und niemand konnte die Zahlen erklaeren.
    print()
    print('52k. Alte Katalog-Schluessel werden angeglichen')
    from scbp import katalog as _ka52k
    _alt52k = {'a03 sniper rifle magazine (15 cap)':
               {'n': 'A03 Sniper Rifle Magazine (15 cap)', 'a': 'WeaponAttachment'},
               'bolide': {'n': 'Bolide', 'a': 'PowerPlant'}}
    _neu52k = _ka52k._schluessel_angleichen(_alt52k)
    pruefe('a03 sniper rifle magazine (15)' in _neu52k,
           'der Schluessel wird aus dem Namen neu gebildet')
    pruefe('bolide' in _neu52k, 'unauffaellige Schluessel bleiben, wie sie sind')
    pruefe(len(_neu52k) == len(_alt52k), 'kein Bauplan geht dabei verloren')
    # Passt schon alles, wird nichts angefasst — dasselbe Verzeichnis zurueck.
    _sauber52k = {'bolide': {'n': 'Bolide'}}
    pruefe(_ka52k._schluessel_angleichen(_sauber52k) is _sauber52k,
           'ein frischer Katalog wird nicht unnoetig umgebaut')

    # 52m. Der Ziehgriff ueberlebt ein niedriges Overlay
    #
    # Er hing an der Liste — eine gute Idee, solange die Liste den Rest des
    # Fensters bekam. Seit die Auftragsleiste darueber Platz nimmt, kann die
    # Liste niedriger werden als der Griff selbst: Bei einem schmalen Overlay
    # mit einem laufenden Auftrag blieben ihr rund 20 Pixel, der Griff braucht
    # 26 — und war weg. Zweimal gemeldet am 29.08.2026.
    print()
    print('52m. Ziehgriff bleibt sichtbar')
    import importlib.util as _ilu52m
    _spec52m = _ilu52m.spec_from_file_location(
        '_scbpw52m', os.path.join(_wurzelpfad, 'sc_bp_watcher.py'))
    _m52m = _ilu52m.module_from_spec(_spec52m)
    sys.modules['_scbpw52m'] = _m52m
    _spec52m.loader.exec_module(_m52m)
    _ov52m = _m52m.Overlay()
    try:
        _ov52m.auftraege_zeigen([('X', 'Auftrag angenommen: Testauftrag')])
        _fehlt52m = []
        for _h52m in (190, 130, 110):
            _ov52m.root.geometry('660x%d' % _h52m)
            _ov52m.root.update_idletasks()
            if not _ov52m.grip.winfo_ismapped():
                _fehlt52m.append(_h52m)
        pruefe(not _fehlt52m,
               'der Griff bleibt auch im niedrigen Fenster sichtbar (%s)'
               % (_fehlt52m or 'alle Hoehen'))
        pruefe(_ov52m.grip.master is _ov52m.root,
               'er haengt am Fenster, nicht an der Liste')
        _ov52m.eingeklappt = True
        _ov52m._grip_nachziehen()
        _ov52m.root.update_idletasks()
        pruefe(not _ov52m.grip.winfo_ismapped(),
               'eingeklappt verschwindet er weiterhin')
    finally:
        _ov52m.root.destroy()

    # 52n. Abbauart im Lager und die neuen Filter
    print()
    print('52n. Abbauart und Herstellungs-Filter')
    from scbp import bergbau as _bg52n
    _echt52n = _bg52n.erze
    _bg52n.erze = lambda: [
        {'name': 'Iron (Ore)', 'orte': [('Daymar', 'Stanton', {'schiff'}),
                                        ('Yela', 'Stanton', {'schiff_selten'})]},
        {'name': 'Aphorite', 'orte': [('Daymar', 'Stanton', {'fps'})]},
    ]
    try:
        pruefe(_bg52n.abbauart('Iron') == {'schiff'},
               'Schiffsabbau wird erkannt — auch aus schiff_selten')
        pruefe(_bg52n.abbauart('Aphorite') == {'fps'},
               'Handabbau ebenso')
        pruefe(_bg52n.abbauart('Gibtsnicht') == set(),
               'ein unbekannter Rohstoff ergibt keine Art')
    finally:
        _bg52n.erze = _echt52n
    for _k52n in ('s_lg_sp_abbau', 's_lg_abbau_fps', 's_lg_abbau_fahrzeug',
                  's_lg_abbau_schiff', 's_lg_posten_weg', 's_lg_posten_frage',
                  's_lg_leeren', 's_lg_leeren_frage', 's_lg_geleert',
                  'ff_alle_material', 'ff_material_reicht', 'ff_material_fehlt'):
        _w52n = _sp51.TEXTE.get(_k52n)
        pruefe(bool(_w52n) and len(_w52n) == 2 and all(_w52n),
               'Text %s gibt es deutsch und englisch' % _k52n)
    # ⚠ Das Suchfeld im Lager erscheint nicht mehr erst ab fuenf Posten — wer
    # viel hat, findet sonst nichts mehr.
    with open(os.path.join(_wurzelpfad, 'scbp', 'seiten.py'),
              encoding='utf-8') as _fh52n:
        _qu52n = _fh52n.read()
    pruefe('if len(posten) > 5:' not in _qu52n,
           'das Suchfeld im Lager haengt nicht mehr an einer Postenzahl')

    # 52p. Eingabefelder ueberleben das Neuzeichnen
    #
    # Das Suchfeld im Lager stand IN der Zeichenfunktion, und die raeumt bei
    # jeder Aenderung den Listenbereich leer: Mit jedem getippten Buchstaben
    # zerstoerte sich das Feld selbst und der Cursor war weg — „im Lager bei
    # Eingabe im Suchfeld tabt man automatisch raus" (30.08.2026).
    print()
    print('52p. Suchfelder werden nicht beim Zeichnen neu gebaut')
    with open(os.path.join(_wurzelpfad, 'scbp', 'seiten.py'),
              encoding='utf-8') as _fh52p:
        _qu52p = _fh52p.read()
    # Der Lager-Abschnitt: zwischen `def _lager(` und der naechsten Seite.
    _von52p = _qu52p.index('def _lager(')
    _lager52p = _qu52p[_von52p:]
    _zeichnen52p = _lager52p[_lager52p.index('    def zeichnen():'):]
    # Bis zum Ende der Zeichenfunktion — der naechste Ausdruck auf gleicher
    # Ebene ist die Anmeldung des Filters.
    _zeichnen52p = _zeichnen52p.split('filter_var.trace_add')[0]
    pruefe('rundes_feld' not in _zeichnen52p,
           'im Lager baut die Zeichenfunktion kein Eingabefeld mehr')
    pruefe('_such_feld' in _lager52p,
           'das Suchfeld entsteht einmal, ausserhalb')

    # 52q. Die gemerkte Fenstergroesse ueberlebt den Start
    #
    # Die Mindestbreiten-Pruefung lief ueber `after_idle` — da meldet Tk fuer
    # ein noch nicht angezeigtes Fenster die Breite 1. Der Vergleich traf immer
    # zu, das Overlay wurde auf die Mindestbreite gesetzt, und die Groesse aus
    # dem letzten Lauf war weg: „er startet bei mir immer mit der kleinsten
    # Groesse" (30.08.2026).
    print()
    print('52q. Gemerkte Fenstergroesse bleibt erhalten')
    _m52q = _m52c            # dasselbe Modul wie in 52c
    _alt52q = _m52q.load_geometry()
    try:
        _m52q.save_geometry('900x400+150+120')
        _ov52q = _m52q.Overlay()
        try:
            _ov52q.root.update_idletasks()
            _ov52q.root.update()
            _ov52q.root.update_idletasks()
            pruefe(_ov52q.root.winfo_width() == 900,
                   'die gemerkte Breite bleibt (900, ist %d)'
                   % _ov52q.root.winfo_width())
            pruefe(_ov52q.root.winfo_height() == 400,
                   'die gemerkte Hoehe bleibt (400, ist %d)'
                   % _ov52q.root.winfo_height())
            # Zu schmal gemerkt? Dann greift die Grenze trotzdem — sobald das
            # Fenster wirklich steht.
            _ov52q.root.geometry('300x150')
            for _ in range(3):
                _ov52q.root.update_idletasks()
                _ov52q.root.update()
            _ov52q._mindestgroesse_setzen()
            _ov52q.root.update_idletasks()
            pruefe(_ov52q.root.winfo_width() >= _ov52q._mindestbreite(),
                   'ein zu schmales Fenster wird weiterhin angehoben')
        finally:
            _ov52q.root.destroy()
    finally:
        if _alt52q:
            _m52q.save_geometry(_alt52q)

    # 52r. Kein Entwicklername im CHANGELOG
    #
    # ⚠ Die Regel „jeden Fehlerfinder namentlich nennen" gilt fuer Tester von
    # aussen, nicht fuer den Entwickler selbst — es ist sein Projekt. Zweimal
    # aufgeraeumt, zweimal wieder hineingerutscht: Beim ersten Mal war nur nach
    # nur nach dem Pseudonym gesucht worden — die Stellen mit dem Klarnamen
    # blieben stehen. Diese Pruefung sucht nach dem Klarnamen, und zwar im
    # ganzen Projekt statt nur in zwei Dateien.
    print()
    print('52r. Kein Klarname im ganzen Projekt')
    import re as _re52r
    # ⚠ `Xharig` allein ist erlaubt: Copyright-Zeile, Repo-Adresse, der
    # Autoren-Block der README. Der **Klarname** ist es nie.
    _NAMEN52r = _re52r.compile(r'\bRoberts?\b')
    _alle52r = []
    # ⚠⚠ **Der Klarname gehoert NIRGENDS hin** — nicht in den CHANGELOG, nicht
    # in Kommentare, nicht in die Danksagung: „es geht niemanden was an, wie
    # ich heisse" (30.08.2026). Deshalb sucht diese Pruefung im ganzen Projekt,
    # nicht nur in zwei Dateien. Beim ersten Aufraeumen war nur der CHANGELOG
    # geprueft worden — im Quelltext standen danach noch dreizehn Stellen.
    for _datei52r in sorted(_versionierte_dateien(_wurzelpfad)):
        _pfad52r = os.path.join(_wurzelpfad, _datei52r)
        if not os.path.exists(_pfad52r):
            continue
        with open(_pfad52r, encoding='utf-8') as _fh52r:
            _text52r = _fh52r.read()
        _treffer52r = []
        for _nr52r, _zeile52r in enumerate(_text52r.splitlines(), 1):
            # ⚠ „Roberts Space Industries" ist der Hersteller im Spiel und
            # muss stehen bleiben.
            #
            # ⚠⚠ **Auch halbiert.** In langen Texten bricht der Name ueber
            # zwei Quelltextzeilen („… or Roberts Space " + "Industries."),
            # und dann greift die Ausnahme oben nicht mehr — die Pruefung
            # meldete einen Klarnamen, wo der Hersteller stand. Am 30.08.2026
            # passiert. Genau derselbe Fehler hat frueher schon einmal den
            # Herstellernamen in 174 Commits auseinandergerissen, weil jemand
            # den Fehlalarm „bereinigt" hat.
            _sauber52r = _zeile52r.replace('Roberts Space Industries', '')
            _sauber52r = _sauber52r.replace('Roberts Space', '')
            if _NAMEN52r.search(_sauber52r):
                _treffer52r.append('%s:%d %s' % (_datei52r, _nr52r,
                                                 _zeile52r.strip()[:60]))
        _alle52r.extend(_treffer52r)
    pruefe(not _alle52r,
           'kein Klarname im Projekt (%d Stellen)' % len(_alle52r))
    for _x52r in _alle52r[:6]:
        print('       ·', _x52r)

    # 52s. Keine privaten Angaben im Projekt
    #
    # ⚠⚠ Nicht nur der Klarname (52r). Auch alles andere, was aus dem
    # Arbeitsalltag stammt und niemanden etwas angeht: die persoenliche
    # Wissenssammlung und ihr Programm, Adressen im Heimnetz, Passwort- und
    # Dokumentenverwaltung, die eigene Spielorganisation, Wohnort, Arbeitgeber.
    # Am 30.08.2026 stand solches im CHANGELOG, in sechzehn Release-Texten und
    # als fester Pfad im Quelltext.
    #
    # ⚠ Die Begriffe stehen hier zusammengesetzt, damit diese Datei nicht
    # selbst als Treffer gilt.
    print()
    print('52s. Keine privaten Angaben im Projekt')
    _PRIVAT52s = [
        'obsid' + 'ian', 'va' + 'ult', 'keep' + 'ass', 'paper' + 'less',
        'xharig' + 'ds', '192.168.' + '178', 'fritz.' + 'box',
        'kirch' + 'hain', 'gar' + 'the', 'das kar' + 'tell',
        'staffel ma' + 'mba', 'pi-' + 'hole',
    ]
    # Was im Spiel wirklich so heisst, darf nicht anschlagen.
    _ERLAUBT52s = ('racing helmet obsid', 'helmetobsid')
    _funde52s = []
    for _rel52s in sorted(_versionierte_dateien(_wurzelpfad)):
        if _rel52s.endswith('selbsttest.py'):
            continue              # hier stehen die Suchbegriffe selbst
        if _rel52s.startswith('daten' + os.sep) or _rel52s.startswith('daten/'):
            continue              # Spieldaten — dort heisst ein Helm wirklich so
        _voll52s = os.path.join(_wurzelpfad, _rel52s)
        if not os.path.exists(_voll52s):
            continue
        with open(_voll52s, encoding='utf-8') as _fh52s:
            for _nr52s, _zeile52s in enumerate(_fh52s, 1):
                _klein52s = _zeile52s.lower()
                if any(_e in _klein52s for _e in _ERLAUBT52s):
                    continue
                for _b52s in _PRIVAT52s:
                    if _b52s in _klein52s:
                        _funde52s.append('%s:%d %s'
                                         % (_rel52s, _nr52s,
                                            _zeile52s.strip()[:60]))
                        break
    pruefe(not _funde52s,
           'keine privaten Angaben im Projekt (%d Stellen)' % len(_funde52s))
    for _x52s in _funde52s[:6]:
        print('       ·', _x52s)

    # 53. Lagerbestand berichtigen — und Namen, die wirklich passen
    #
    # Eintragen ohne Berichtigen war halb fertig: Wer sich vertippt oder
    # Material weitergegeben hatte, konnte den Posten nur loeschen und neu
    # tippen. Und beim Neutippen entstand leicht ein zweiter Name fuer
    # dasselbe Material — der Bestand sieht dann richtig aus, wird von den
    # Rezepten aber nicht mehr gefunden. Am 29.08.2026 gemeldet.
    print()
    print('53. Lagerbestand berichtigen und Namen abgleichen')
    from scbp import rohstoffe as _ro53
    from scbp import herstellung as _he53

    _alt53 = _ro53.laden()
    try:
        _ro53.sichern([])
        _ro53.eintragen('Aslarite', 10, 500, 'Zuhause')
        _ro53.eintragen('Quantainium', 4, 800, 'Schiff')

        pruefe(len(_ro53.laden()) == 2, 'zwei Posten liegen im Lager')

        # Menge berichtigen, alles andere behalten
        _ro53.aendern(0, 'Aslarite', 8, 500, 'Zuhause')
        _p53 = _ro53.laden()[0]
        pruefe(_p53.get('menge') == 8, 'die Menge laesst sich berichtigen')
        pruefe(_p53.get('qualitaet') == 500,
               'dabei bleibt die Qualitaet stehen')

        # Umlagern und Qualitaet nachtragen
        _ro53.aendern(1, 'Quantainium', 4, 950, 'Lagerhaus Area18')
        _p53b = _ro53.laden()[1]
        pruefe(_p53b.get('ort') == 'Lagerhaus Area18',
               'der Lagerort laesst sich aendern (umlagern)')
        pruefe(_p53b.get('qualitaet') == 950,
               'die Qualitaet laesst sich anpassen')

        # Der Nachbarposten bleibt unberuehrt
        pruefe(_ro53.laden()[0].get('material') == 'Aslarite',
               'die andere Zeile bleibt unangetastet')

        # Unsinnige Nummer aendert nichts
        pruefe(_ro53.aendern(99, 'Irgendwas', 1, 1, '') is False,
               'eine Nummer ausserhalb der Liste aendert nichts')
        pruefe(len(_ro53.laden()) == 2,
               'und legt auch keinen neuen Posten an')
    finally:
        _ro53.sichern(_alt53)

    # Mehrfach herstellen — einmal klicken statt zehnmal
    _ro53.sichern([{'material': 'Iron', 'menge': 10.0, 'qualitaet': 500,
                    'ort': ''}])
    _zut53 = [('Frame', 'Iron', 2.0, 0)]
    _ok53, _fehlt53 = _ro53.abziehen(_zut53, 3)
    pruefe(_ok53 and abs(_ro53.menge_von('Iron') - 4.0) < 0.001,
           'dreimal herstellen zieht dreimal die Zutaten ab (10 - 3x2 = 4)')
    _ro53.sichern([{'material': 'Iron', 'menge': 10.0, 'qualitaet': 500,
                    'ort': ''}])
    _ro53.abziehen(_zut53)
    pruefe(abs(_ro53.menge_von('Iron') - 8.0) < 0.001,
           'ohne Angabe bleibt es bei einem Stueck')

    # Ausgeben und wieder einlesen
    _probe53 = [{'material': 'Iron', 'menge': 1.36, 'qualitaet': 540,
                 'ort': 'Zuhause'},
                {'material': 'Riccite', 'menge': 2.91, 'qualitaet': 800,
                 'ort': ''}]
    _csv53 = _ro53.als_csv(_probe53)
    pruefe(_csv53.startswith('Material;Menge;Qualitaet;Lagerort'),
           'die Tabelle hat eine Kopfzeile')
    pruefe('1,36' in _csv53,
           'Mengen stehen mit Komma darin (deutsches Tabellenprogramm)')
    pruefe(_csv53.count(chr(10)) == 3, 'zwei Posten ergeben zwei Zeilen')
    _zurueck53 = _ro53.aus_json(_ro53.als_json(_probe53))
    pruefe(_zurueck53 == _probe53,
           'was ausgegeben wurde, kommt unveraendert zurueck')
    pruefe(_ro53.aus_json('kein json') is None,
           'Unsinn wird nicht eingelesen')
    pruefe(_ro53.aus_json('{"format": 99, "posten": []}') is None,
           'und ein fremdes Format auch nicht')

    # Komma und Punkt gelten gleich — die einen tippen 12,5, die anderen 12.5
    pruefe(_ro53.zahl_lesen('12,5') == 12.5, 'ein Komma wird als Zahl gelesen')
    pruefe(_ro53.zahl_lesen('12.5') == 12.5, 'ein Punkt genauso')
    pruefe(_ro53.zahl_lesen(' 8 ') == 8.0, 'Leerzeichen stoeren nicht')
    pruefe(_ro53.zahl_lesen('-2,5') == -2.5, 'ein Minus bleibt erhalten')
    pruefe(_ro53.zahl_lesen('−2') == -2.0,
           'auch das lange Minus vom Ziffernblock')
    pruefe(_ro53.zahl_lesen('12 SCU') is None,
           'was keine Zahl ist, gibt None statt eines Absturzes')
    pruefe(_ro53.zahl_lesen('') is None, 'und ein leeres Feld ebenso')

    # Namensabgleich — der Schluessel zwischen Lager und Rezept.
    # ⚠ Mit eingespeister Namensliste pruefen. Im Wegwerf-Ordner gibt es keine
    # Rezeptdaten; ohne diesen Griff pruefte man nur, dass nichts geladen ist.
    _echt53 = _he53.rohstoffnamen
    _he53.rohstoffnamen = lambda: ['Aslarite', 'Quantainium', 'Aluminum',
                                   'Agricium', 'Titanium']
    pruefe(_he53.offizieller_name('aslarite') == 'Aslarite',
           'Kleinschreibung wird auf den richtigen Namen gezogen')
    pruefe(_he53.offizieller_name('  ASLARITE  ') == 'Aslarite',
           'Grossschreibung und Leerzeichen stoeren nicht')
    pruefe(_he53.offizieller_name('Aslarite (Raw)') == 'Aslarite',
           'die Bergbau-Schreibweise mit Klammer passt auch')
    pruefe(_he53.offizieller_name('aslerite') == 'Aslarite',
           'ein knapper Vertipper wird berichtigt')
    pruefe(_he53.offizieller_name('Bratkartoffeln') is None,
           'ein voellig fremder Name wird NICHT geraten')
    pruefe(_he53.offizieller_name('') is None,
           'und eine leere Eingabe ergibt nichts')
    pruefe(_he53.offizieller_name('Aluminium') == 'Aluminum',
           'die britische Schreibweise trifft die amerikanische')
    # ⚠ Ohne geladene Rezeptdaten darf NICHTS abgewiesen werden — sonst kann
    # beim ersten Start ohne Netz niemand sein Lager fuellen.
    _he53.rohstoffnamen = lambda: []
    pruefe(_he53.offizieller_name('Irgendwas') == 'Irgendwas',
           'ohne Rezeptdaten wird die Eingabe durchgelassen')
    _he53.rohstoffnamen = _echt53
    for _k53 in ('s_lg_speichern', 's_lg_abbrechen', 's_lg_geaendert',
                 's_lg_rechnen', 's_lg_zu_wenig', 's_lg_alles_weg',
                 's_lg_name_fremd', 's_lg_keine_guete',
                 's_lg_berichtigt', 's_lg_zeile_klick', 's_lg_bearbeite'):
        _w53 = _sp51.TEXTE.get(_k53)
        pruefe(bool(_w53) and len(_w53) == 2 and all(_w53),
               'Text %s gibt es deutsch und englisch' % _k53)
    # Der Lagerort heisst Lagerort — „Fundort" gehoert zum Bergbau und hat
    # hier jemanden ratlos gemacht.
    pruefe('Lagerort' in _sp51.TEXTE['s_lg_ort'][0],
           'das Ortsfeld heisst Lagerort, nicht Fundort')
    pruefe('freiwillig' not in _sp51.TEXTE['s_lg_qualitaet'][0],
           'die Qualitaet ist nicht mehr als freiwillig ausgewiesen')

    # ------------------------------------------------------------------
    # 58. Ein abgeschlossener Auftrag darf nicht als frisch angenommen gelten
    #
    # Am 30.08.2026 gemeldet: „Retake Platforms From Nine Tails" um 01:18
    # angenommen, um 01:59 abgeschlossen — der Watcher um 02:22 gestartet und
    # der Auftrag stand als laufend da. Zwei Ursachen, beide hier geprueft:
    #
    #   a) `new_names()` stieg aus, wenn nichts Neues in der Log stand — ohne
    #      die Auftragslisten des VORIGEN Abschnitts zu leeren. Der Aufrufer
    #      wertete sie ein zweites Mal aus.
    #   b) Die Auswertung nahm erst alle Enden und dann alle Annahmen. In einem
    #      Abschnitt, der beides enthaelt (jeder Neustart bei laufendem Spiel
    #      liest so etwas nach), traf das Ende ins Leere und die Annahme stellte
    #      den Auftrag danach wieder hin.
    print()
    print('58. Abgeschlossener Auftrag bleibt abgeschlossen')
    from scbp import logquelle as _lq58
    from scbp import auftraege as _au58
    from scbp import pfade as _pf58

    _log58 = os.path.join(tempfile.mkdtemp(), 'Game.log')
    with open(_log58, 'w', encoding='utf-8') as _f58:
        _f58.write('Added notification "Auftrag angenommen: Retake Platforms: " ...\n'
                   'irgendwas dazwischen\n'
                   'Added notification "Auftrag abgeschlossen: Retake Platforms: " ...\n')

    class _Stand58:
        def __init__(_s): _s.o = 0
        def aktiv_holen(_s, _p): return 0
        def aktiv_setzen(_s, _p, _o): _s.o = _o
        def speichern(_s): pass

    _echt58 = _pf58.game_log
    try:
        _pf58.game_log = lambda: _log58
        _t58 = _lq58.LogTail(_Stand58())
        _t58.auftrag_muster = _au58.muster()
        _t58.auftrag_ende_muster = _au58.ende_muster()

        _t58.new_names()
        pruefe(len(_t58.auftraege) == 1 and len(_t58.auftraege_beendet) == 1,
               'der erste Abschnitt bringt Annahme und Ende')

        # a) Zweiter Aufruf, nichts Neues in der Datei: die Listen MUESSEN leer
        #    sein. Bis v3.3.0-rc33 standen sie noch voll da.
        _t58.new_names()
        pruefe(_t58.auftraege == [] and _t58.auftraege_beendet == []
               and _t58.auftrag_ereignisse == [],
               'ohne neuen Text bleiben die Auftragslisten LEER')

        # b) Die Reihenfolge muss stimmen: Annahme, dann Ende.
        with open(_log58, 'a', encoding='utf-8') as _f58:
            _f58.write('Added notification "Auftrag angenommen: Zweiter Job: " ...\n'
                       'Added notification "Auftrag abgeschlossen: Zweiter Job: " ...\n')
        _t58.new_names()
        pruefe([e[0] for e in _t58.auftrag_ereignisse] == [True, False],
               'die Ereignisse kommen in der Reihenfolge des Logs')
        pruefe([e[1] for e in _t58.auftrag_ereignisse] == ['Zweiter Job', 'Zweiter Job'],
               'und tragen beide denselben Titel')

        # c) Und die Gesamtrechnung ueber die ganze Datei: nichts offen.
        _text58 = open(_log58, encoding='utf-8').read()
        pruefe(_au58.offene_aus_text(_text58, _t58.auftrag_muster,
                                     _t58.auftrag_ende_muster) == [],
               'ueber die ganze Log gerechnet ist KEIN Auftrag mehr offen')
    finally:
        _pf58.game_log = _echt58

    # d) Die Auswertung im Hauptprogramm muss der Reihenfolge folgen und darf
    #    nicht mehr auf die beiden getrennten Listen zurueckgreifen.
    _quelle58 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'),
                     encoding='utf-8').read()
    _ab58 = _quelle58.split('def _auftraege_melden')[1].split('def _emit')[0]
    pruefe('auftrag_ereignisse' in _ab58,
           'die Auswertung geht ueber die geordneten Ereignisse')
    pruefe('for titel in beendet:' not in _ab58,
           'und NICHT mehr erst ueber alle Enden')

    # e) Die Zeile in der Liste gehoert zum Auftrag — sonst bleibt sie stehen,
    #    wenn er endet, und traegt kein Zeichen zum Wegnehmen.
    pruefe("('hinweis', zeile, rein)" in _quelle58,
           'die Hinweiszeile bekommt den Auftrag mit')
    pruefe('def hinweis_entfernen' in _quelle58,
           'es gibt einen Weg, die Zeile wieder herauszunehmen')
    pruefe("'auftrag_weg'" in _quelle58,
           'und eine Meldung, die das ausloest')
    _ah58 = _quelle58.split('def add_hinweis')[1].split('def add_catalog')[0]
    pruefe("zeichen.zeile(row, 'ausblenden'" in _ah58,
           'die Zeile traegt dasselbe festgelegte Zeichen wie die Auftragsleiste')

    # ------------------------------------------------------------------
    # 59. Eine aufgeklappte Auswahlliste bleibt ueberschaubar
    #
    # Am 30.08.2026 gemeldet: Die Ortsliste im Bergbau (48 Eintraege) reichte
    # vom Auswahlfeld bis weit unter das Fenster ins Bild hinein. Die Hoehe war
    # bis dahin nur nach dem *Platz* begrenzt — und auf einem grossen Bildschirm
    # ist der riesig. Jetzt gilt zusaetzlich eine feste Zeilenzahl; alles
    # darueber wird gerollt, und die Rollleiste zeigt, dass mehr kommt.
    print()
    print('59. Aufgeklappte Auswahlliste bleibt ueberschaubar')
    import tkinter as _tk59
    from scbp import hauptfenster as _hf59

    pruefe(getattr(_hf59, 'MAX_WAHLZEILEN', 0) >= 8,
           'es gibt eine Obergrenze fuer die Zeilenzahl (%s)'
           % getattr(_hf59, 'MAX_WAHLZEILEN', '—'))

    _w59 = _tk59.Tk()
    try:
        _w59.geometry('1200x1130+0+0')
        _w59.update_idletasks()
        _hoehen59 = {}
        for _n59 in (5, _hf59.MAX_WAHLZEILEN, 48):
            _ein59 = ([('', 'Alle Orte')] +
                      [('o%d' % _i59, 'Ort Nummer %d' % _i59)
                       for _i59 in range(_n59 - 1)])
            _f59 = _hf59.rundwahl(_w59, _ein59, '', lambda _v: None,
                                  ('TkDefaultFont', 10))
            _f59.pack()
            _w59.update_idletasks()
            _f59.event_generate('<Button-1>', x=5, y=5)
            _w59.update_idletasks()
            _auf59 = [k for k in _f59.winfo_children()
                      if isinstance(k, _tk59.Toplevel)]
            _hoehen59[_n59] = (int(_auf59[0].wm_geometry().split('x')[1].split('+')[0])
                               if _auf59 else 0)
            for _tl59 in _auf59:
                _tl59.destroy()
            _f59.destroy()

        pruefe(_hoehen59[5] > 0, 'eine kurze Liste klappt auf')
        pruefe(_hoehen59[48] <= _hoehen59[_hf59.MAX_WAHLZEILEN],
               'eine lange Liste wird NICHT hoeher als die Obergrenze '
               '(48 Eintraege: %d px, Grenze: %d px)'
               % (_hoehen59[48], _hoehen59[_hf59.MAX_WAHLZEILEN]))
        pruefe(_hoehen59[48] < 1090,
               'und bleibt deutlich unter der Fensterhoehe (%d px)'
               % _hoehen59[48])
        pruefe(_hoehen59[5] < _hoehen59[48],
               'eine kurze Liste wird trotzdem nicht kuenstlich aufgeblaeht')

        # ⚠ Und die harte Grenze: NIE hoeher als das kleinstmoegliche Fenster.
        # Sonst passt die Liste nach dem Verkleinern nicht mehr hinein und
        # waere unten abgeschnitten. Geprueft bei GROSSEM Fenster — genau da
        # war die alte Rechnung grosszuegig.
        _w59.geometry('1600x1400')
        _w59.update_idletasks()
        _ein59 = [('', 'Alle')] + [('o%d' % _i59, 'Eintrag %d' % _i59)
                                   for _i59 in range(199)]
        _f59 = _hf59.rundwahl(_w59, _ein59, '', lambda _v: None,
                              ('TkDefaultFont', 10))
        _f59.pack()
        _w59.update_idletasks()
        _f59.event_generate('<Button-1>', x=5, y=5)
        _w59.update_idletasks()
        _auf59 = [k for k in _f59.winfo_children()
                  if isinstance(k, _tk59.Toplevel)]
        _hoch59 = (int(_auf59[0].wm_geometry().split('x')[1].split('+')[0])
                   if _auf59 else 0)
        pruefe(0 < _hoch59 <= _hf59.MIN_HOEHE,
               'auch bei 200 Eintraegen und grossem Fenster nie hoeher als das '
               'kleinstmoegliche Fenster (%d px, Grenze %d px)'
               % (_hoch59, _hf59.MIN_HOEHE))
        for _tl59 in _auf59:
            _tl59.destroy()
        _f59.destroy()

        # ⚠ Und der Fall, der den Fehler ueberhaupt sichtbar gemacht hat:
        # Fenster buendig am unteren Bildschirmrand. Dann ist unter dem Feld
        # kein Platz — die Liste MUSS nach oben aufklappen, sonst laege sie
        # unter dem Bildrand und waere abgeschnitten.
        _schirm59 = _w59.winfo_screenheight()
        _w59.geometry('1200x760+0+%d' % max(0, _schirm59 - 762))
        _w59.update_idletasks()
        _unten59 = _tk59.Frame(_w59)
        _unten59.pack(side='bottom', fill='x')
        _ein59 = [('', 'Alle')] + [('o%d' % _i59, 'Ort %d' % _i59)
                                   for _i59 in range(47)]
        _f59 = _hf59.rundwahl(_unten59, _ein59, '', lambda _v: None,
                              ('TkDefaultFont', 10))
        _f59.pack()
        _w59.update_idletasks()
        _f59.event_generate('<Button-1>', x=5, y=5)
        _w59.update_idletasks()
        _auf59 = [k for k in _f59.winfo_children()
                  if isinstance(k, _tk59.Toplevel)]
        if _auf59:
            _g59 = _auf59[0].wm_geometry().split('+')
            _bh59 = int(_g59[0].split('x')[1])
            _oben59 = int(_g59[2])
            pruefe(_oben59 < _f59.winfo_rooty(),
                   'am unteren Bildrand klappt die Liste nach OBEN auf')
            pruefe(_oben59 + _bh59 <= _f59.winfo_rooty() + 4,
                   'und endet ueber dem Feld statt unter dem Bildrand '
                   '(y=%d bis %d, Feld bei %d)'
                   % (_oben59, _oben59 + _bh59, _f59.winfo_rooty()))
            for _tl59 in _auf59:
                _tl59.destroy()
        _f59.destroy()
        _unten59.destroy()
    finally:
        _w59.destroy()

    # ------------------------------------------------------------------
    # 60. Das Mausrad rollt die aufgeklappte Liste — nicht die Seite dahinter
    #
    # Am 30.08.2026 gemeldet: „das dropdown laesst sich NICHT scrollen … wenn
    # man so wie jeder user es versucht zu scrollen, scrollt das fenster
    # dahinter und man kann die abgeschnittenen daten NICHT erreichen."
    #
    # Ursache: `rad_anschliessen` haengt global am Programm und sucht die
    # Rollflaeche, indem es vom Element unter dem Zeiger durch die Elternkette
    # nach oben geht. Die aufgeklappte Liste ist ein eigenes Fenster, ihr
    # Elternteil ist aber das Auswahlfeld — und das steht mitten in der
    # rollbaren Seite. Die Kette lief also aus der Liste heraus in die Seite
    # dahinter. Die rollte weg, das Feld wanderte mit, die Liste klappte zu.
    #
    # ⚠ Der Aufbau hier muss das nachstellen: Das Feld MUSS in der Rollflaeche
    # stecken. Ein Feld daneben zeigt den Fehler nicht — daran ist die erste
    # Messung vorbeigelaufen.
    print()
    print('60. Mausrad rollt die Klappliste, nicht die Seite dahinter')
    import tkinter as _tk60
    from scbp import hauptfenster as _hf60

    _w60 = _tk60.Tk()
    try:
        _w60.geometry('1200x1000+0+0')
        _seite60 = _tk60.Canvas(_w60, height=600)
        _seite60.pack(fill='both', expand=True)
        _inhalt60 = _tk60.Frame(_seite60)
        _seite60.create_window((0, 0), window=_inhalt60, anchor='nw')

        _ein60 = [('', 'Alle')] + [('h%d' % _i60, 'Eintrag %d' % _i60)
                                   for _i60 in range(47)]
        _feld60 = _hf60.rundwahl(_inhalt60, _ein60, '', lambda _v: None,
                                 ('TkDefaultFont', 10))
        _feld60.pack()
        for _i60 in range(200):
            _tk60.Label(_inhalt60, text='Zeile %d' % _i60).pack()
        _w60.update_idletasks()
        _seite60.configure(scrollregion=(0, 0, 400, _inhalt60.winfo_reqheight()))
        _hf60.rad_anschliessen(_seite60)

        _w60.update_idletasks()
        _feld60.event_generate('<Button-1>', x=5, y=5)
        _w60.update_idletasks()
        _auf60 = [k for k in _feld60.winfo_children()
                  if isinstance(k, _tk60.Toplevel)]
        pruefe(bool(_auf60), 'die Liste klappt auf')

        if _auf60:
            _auf60[0].update_idletasks()

            def _rollflaeche60(w):
                if isinstance(w, _tk60.Canvas) and w.winfo_width() > 20:
                    return w
                for _k in w.winfo_children():
                    _t = _rollflaeche60(_k)
                    if _t is not None:
                        return _t
                return None

            def _etiketten60(w, sammlung):
                if isinstance(w, _tk60.Label):
                    sammlung.append(w)
                for _k in w.winfo_children():
                    _etiketten60(_k, sammlung)
                return sammlung

            _liste60 = _rollflaeche60(_auf60[0])
            _zeilen60 = _etiketten60(_auf60[0], [])
            _ziel60 = _zeilen60[3]

            # ⚠ **Das Rad heisst auf jedem System anders.** Linux meldet es
            # als Maustaste 4/5, Windows und macOS als `<MouseWheel>` mit einem
            # Ausschlag — unter Windows ±120, auf dem Mac ±1. Ein Test, der nur
            # `<Button-5>` schickt, faellt unter Windows durch, obwohl das
            # Programm dort in Ordnung ist. Genau so am 30.08.2026 im Bau-Lauf
            # passiert: Linux gruen, Windows rot.
            def _radeln60(male):
                for _ in range(male):
                    if sys.platform.startswith('linux'):
                        _ziel60.event_generate(
                            '<Button-5>', x=5, y=5,
                            rootx=_ziel60.winfo_rootx() + 5,
                            rooty=_ziel60.winfo_rooty() + 5)
                    else:
                        _ziel60.event_generate(
                            '<MouseWheel>',
                            delta=(-1 if sys.platform == 'darwin' else -120),
                            x=5, y=5,
                            rootx=_ziel60.winfo_rootx() + 5,
                            rooty=_ziel60.winfo_rooty() + 5)
                _w60.update_idletasks()

            _vl60, _vs60 = _liste60.yview(), _seite60.yview()
            _radeln60(5)
            _nl60, _ns60 = _liste60.yview(), _seite60.yview()

            pruefe(_nl60[0] > _vl60[0],
                   'das Rad rollt die Klappliste (%.3f -> %.3f)'
                   % (_vl60[0], _nl60[0]))
            pruefe(abs(_ns60[0] - _vs60[0]) < 1e-6,
                   'und die Seite dahinter bleibt stehen (%.3f -> %.3f)'
                   % (_vs60[0], _ns60[0]))

            _radeln60(80)
            pruefe(_liste60.yview()[1] > 0.999,
                   'der letzte Eintrag ist erreichbar (Ende bei %.3f)'
                   % _liste60.yview()[1])
            for _tl60 in _auf60:
                _tl60.destroy()
    finally:
        _w60.destroy()

    # Und: Jedes Auswahlfeld im Programm muss ueber `rundwahl` laufen — nur
    # dort steckt die Rad-Behandlung. Ein selbstgebautes `OptionMenu` oder eine
    # `ttk.Combobox` haette den Fehler sofort wieder.
    _fremde60 = []
    for _p60 in _versionierte_dateien(WURZEL, ('.py',)):
        if _p60.endswith('selbsttest.py'):
            continue
        _q60 = open(_p60, encoding='utf-8', errors='ignore').read()
        for _muster60 in ('OptionMenu(', 'Combobox('):
            if _muster60 in _q60:
                _fremde60.append('%s: %s' % (os.path.relpath(_p60, WURZEL),
                                             _muster60))
    pruefe(not _fremde60,
           'kein Auswahlfeld am Hausstil vorbei (%d gefunden)' % len(_fremde60))
    for _x60 in _fremde60[:5]:
        print('       ·', _x60)

    # ------------------------------------------------------------------
    # 61. Stueckzahl, Abzug und die Grenze des Lagers
    #
    # Am 30.08.2026 gemeldet, drei Fragen auf einmal:
    #   „10 als Menge eingegeben sollte auch 10fache Menge an benoetigtem
    #    Material sein, angezeigt wird es nicht — wuerde es ueberhaupt richtig
    #    abgezogen? Kann der Bestand im Lager ins Minus gehen? (Darf er nicht,
    #    wenn was fehlt ist es ja nicht herstellbar.)"
    #
    # Der Abzug rechnete richtig, die Anzeige nicht. Ins Minus konnte der
    # Bestand nie geraten — aber er wurde LEERGERAEUMT, wenn etwas fehlte.
    print()
    print('61. Stueckzahl, Abzug und die Grenze des Lagers')
    from scbp import rohstoffe as _ro61

    _sichern61 = _ro61.laden()
    try:
        _zut61 = [('Frame', 'Iron', 1.16, 0), ('Cycler', 'Riccite', 0.17, 0)]

        # a) Die ANZEIGE muss die Stueckzahl mitrechnen. Genau das fehlte.
        _ro61.sichern([])
        _eins61 = {m: br for m, br, _da, _f, _zg, _mq
                   in _ro61.pruefen(_zut61, 1)}
        _zehn61 = {m: br for m, br, _da, _f, _zg, _mq
                   in _ro61.pruefen(_zut61, 10)}
        pruefe(abs(_eins61['Iron'] - 1.16) < 1e-6,
               'ein Stueck braucht 1,16 Iron')
        pruefe(abs(_zehn61['Iron'] - 11.6) < 1e-6,
               'zehn Stueck brauchen das Zehnfache (%.2f)' % _zehn61['Iron'])
        _fehl61 = {m: f for m, _br, _da, f, _zg, _mq
                   in _ro61.pruefen(_zut61, 10)}
        pruefe(abs(_fehl61['Iron'] - 11.6) < 1e-6,
               'und bei leerem Lager fehlt auch das Zehnfache')

        # b) Der ABZUG rechnet die Stueckzahl mit — das war schon richtig.
        _ro61.sichern([{'material': 'Iron', 'menge': 20.0, 'qualitaet': 500,
                        'ort': ''},
                       {'material': 'Riccite', 'menge': 5.0, 'qualitaet': 500,
                        'ort': ''}])
        _ok61, _weg61 = _ro61.abziehen(_zut61, 10)
        pruefe(_ok61, 'zehn Stueck lassen sich abziehen, wenn genug da ist')
        pruefe(abs(_ro61.menge_von('Iron') - 8.4) < 1e-6,
               '20 - 10x1,16 = 8,40 Iron bleiben (%.2f)'
               % _ro61.menge_von('Iron'))

        # c) ⚠⚠ Reicht es NICHT, wird GAR NICHTS genommen.
        _ro61.sichern([{'material': 'Iron', 'menge': 3.0, 'qualitaet': 500,
                        'ort': ''},
                       {'material': 'Riccite', 'menge': 5.0, 'qualitaet': 500,
                        'ort': ''}])
        _ok61, _weg61 = _ro61.abziehen(_zut61, 10)
        pruefe(not _ok61, 'zehn Stueck aus zu wenig Material gehen NICHT')
        pruefe(abs(_ro61.menge_von('Iron') - 3.0) < 1e-6,
               'das Iron bleibt UNANGETASTET im Lager (%.2f statt 0)'
               % _ro61.menge_von('Iron'))
        pruefe(abs(_ro61.menge_von('Riccite') - 5.0) < 1e-6,
               'und das Riccite auch — kein halber Abzug (%.2f)'
               % _ro61.menge_von('Riccite'))
        pruefe(any(n == 'Iron' and abs(f - 8.6) < 1e-6 for n, f in _weg61),
               'gemeldet wird die FEHLMENGE, nicht nur der Name (%s)'
               % (_weg61,))

        # d) Und nie ins Minus — auch nicht bei einer unsinnigen Stueckzahl.
        _ro61.sichern([{'material': 'Iron', 'menge': 3.0, 'qualitaet': 500,
                        'ort': ''}])
        _ro61.abziehen([('Frame', 'Iron', 1.0, 0)], 9999)
        pruefe(_ro61.menge_von('Iron') >= 0,
               'der Bestand kann nicht negativ werden (%.2f)'
               % _ro61.menge_von('Iron'))
        pruefe(abs(_ro61.menge_von('Iron') - 3.0) < 1e-6,
               'und bleibt bei 9999 Stueck unberuehrt stehen')

        # e) Zutat zweimal im Rezept: die Summe zaehlt, nicht jede fuer sich.
        _ro61.sichern([{'material': 'Iron', 'menge': 3.0, 'qualitaet': 500,
                        'ort': ''}])
        _ok61, _weg61 = _ro61.abziehen(
            [('A', 'Iron', 2.0, 0), ('B', 'Iron', 2.0, 0)], 1)
        pruefe(not _ok61,
               'zweimal 2 aus 3 im Lager geht nicht — die Summe zaehlt')
        pruefe(abs(_ro61.menge_von('Iron') - 3.0) < 1e-6,
               'und auch hier bleibt alles liegen')
    finally:
        _ro61.sichern(_sichern61)

    # f) Die Oberflaeche muss die Stueckzahl wirklich durchreichen — und je
    #    Material einen eigenen Regler bauen.
    _seiten61 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                     encoding='utf-8').read()
    pruefe('lager.pruefen(stufe[\'zutaten\'], wie_viele)' in _seiten61,
           'die Zutatenliste rechnet mit der eingegebenen Stueckzahl')
    pruefe("anzahl_var.trace_add('write', mengen_setzen)" in _seiten61,
           'und rechnet sofort neu, wenn man die Zahl aendert')
    pruefe('def mengen_setzen' in _seiten61
           and 'neu_zeichnen()' not in _seiten61.split('def mengen_setzen')[1]
           .split('anzahl_var.trace_add')[0],
           'ohne die Seite neu zu bauen (sonst verliert das Feld den Cursor)')
    # ⚠ **Nicht auf die ersten 1500 Zeichen begrenzen.** Genau daran ist die
    # Pruefung am 30.08.2026 gescheitert: Ein Einschub zwischen Kommentar und
    # Schleife schob die gesuchte Zeile aus dem Fenster, und der Test meldete
    # einen Fehler, den es nicht gab. Ein Suchfenster mit fester Groesse ist
    # eine Wette darauf, dass niemand mehr etwas dazwischenschreibt.
    _regler61 = _seiten61.split('Ein Regler je Material')[1]
    pruefe('for _mat in alle_materialien' in _regler61,
           'es gibt einen Regler JE MATERIAL, nicht einen fuer alle')

    # ------------------------------------------------------------------
    # 62. Nicht jede Eigenschaft wird durch eine hoehere Zahl besser
    #
    # Am 30.08.2026 gemeldet: „ist es realistisch das sich bei niedrigerer
    # Qualitaet die Werte erhoehen? Und bei besserer Qualitaet die Werte
    # verschlechtern?"
    #
    # Die Daten sind in Ordnung, die Anzeige war es nicht. Bei 852 der 6524
    # Modifikatoren (Spielstand 4.10.0) SINKT der Faktor mit steigender
    # Qualitaet — Rueckstoss, Quantum-Treibstoff — und genau das ist dort die
    # Verbesserung. Die Anzeige faerbte stur „>= 1 ist gut": Der bestmoegliche
    # Rueckstoss (x 0.800) stand in der Warnfarbe, der schlechteste (x 1.200)
    # in Gruen.
    print()
    print('62. Richtung der Qualitaetswirkung')
    from scbp import herstellung as _he62

    # a) Die Richtung kommt aus dem Modifikator, nicht aus dem Namen.
    _hoch62 = [{'startQuality': 0, 'endQuality': 1000,
                'modifierAtStart': 0.925, 'modifierAtEnd': 1.075}]
    _runter62 = [{'startQuality': 0, 'endQuality': 1000,
                  'modifierAtStart': 1.2, 'modifierAtEnd': 0.8}]
    pruefe(_he62.besser_ist_hoch(_hoch62) is True,
           'steigt der Faktor mit der Qualitaet, ist hoeher besser')
    pruefe(_he62.besser_ist_hoch(_runter62) is False,
           'faellt er, ist NIEDRIGER besser (Rueckstoss, Treibstoff)')

    # b) Mehrteilige Spannen beschreiben EINE Kurve — Anfang gegen Ende.
    #    Ein flaches Teilstueck in der Mitte darf die Richtung nicht drehen.
    _geteilt62 = [{'startQuality': 501, 'endQuality': 1000,
                   'modifierAtStart': 1.0, 'modifierAtEnd': 0.8},
                  {'startQuality': 0, 'endQuality': 500,
                   'modifierAtStart': 1.2, 'modifierAtEnd': 1.0}]
    pruefe(_he62.besser_ist_hoch(_geteilt62) is False,
           'ueber mehrere Spannen zaehlt die Gesamtrichtung (1,2 -> 0,8)')
    pruefe(_he62.besser_ist_hoch([]) is True,
           'ohne Modifikator wird nichts behauptet (Vorgabe: hoeher ist besser)')

    # c) Und die Probe aufs Ganze an echten Daten, wenn welche da sind:
    #    Bei Qualitaet 0 muss JEDER Wert schlecht sein, bei 1000 JEDER gut.
    #    Ein Rezept, bei dem das nicht gilt, waere ein Widerspruch.
    def _gut62(w):
        return (w['faktor'] >= 1 if w.get('besser_hoch', True)
                else w['faktor'] <= 1)

    _daten62 = _he62.laden().get('blueprints') or []
    if _daten62:
        _schlecht62 = _falsch62 = 0
        _geprueft62 = 0
        for _b62 in _daten62[:400]:
            _name62 = _b62.get('productName')
            _mats62 = {}
            for _t62 in _b62.get('tiers') or []:
                for _s62 in _t62.get('slots') or []:
                    for _o62 in _s62.get('options') or []:
                        if _o62.get('resourceName'):
                            _mats62[_o62['resourceName']] = 0
            if not _mats62:
                continue
            _unten62 = _he62.werte_mit_lager(
                _name62, {m: 0 for m in _mats62})
            _oben62 = _he62.werte_mit_lager(
                _name62, {m: 1000 for m in _mats62})
            if not _unten62:
                continue
            _geprueft62 += 1
            for _w62 in _unten62:
                if _gut62(_w62):
                    _schlecht62 += 1
            for _w62 in _oben62:
                if not _gut62(_w62):
                    _falsch62 += 1
        pruefe(_geprueft62 > 0,
               'es liessen sich %d Bauplaene durchrechnen' % _geprueft62)
        pruefe(_schlecht62 == 0,
               'bei Qualitaet 0 gilt KEIN Wert als gut (%d Ausreisser)'
               % _schlecht62)
        pruefe(_falsch62 == 0,
               'bei Qualitaet 1000 gilt JEDER Wert als gut (%d Ausreisser)'
               % _falsch62)
    else:
        print('  [–]    keine Rezeptdaten vorhanden — uebersprungen')

    # d) ⚠ Nicht jede Wirkung ist ueberhaupt ein Multiplikator.
    #    „Power Pips" (itemresource_powergeneration) fuehrt Werte von -3 bis
    #    +3 in festen Qualitaetsstufen — Stueckzahlen. Als Faktor gelesen stand
    #    dort „× -1.000", ein Multiplikator, den es nicht geben kann. 598 der
    #    6524 Modifikatoren im Spielstand 4.10.0 sind so gebaut, das betrifft
    #    saemtliche Kraftwerke.
    pruefe(_he62.ist_absolut([{'modifierAtStart': -1.0,
                               'modifierAtEnd': -1.0}]) is True,
           'ein negativer Wert kann kein Multiplikator sein')
    pruefe(_he62.ist_absolut([{'modifierAtStart': 0.0,
                               'modifierAtEnd': 0.0}]) is True,
           'eine Null auch nicht (sie wuerde den Wert ausloeschen)')
    pruefe(_he62.ist_absolut([{'modifierAtStart': 0.925,
                               'modifierAtEnd': 1.075}]) is False,
           'ein Wert um 1 herum dagegen schon')
    pruefe(_he62.ist_absolut([]) is False,
           'ohne Angaben wird nichts behauptet')

    # e) Die Anzeige muss die Richtung auch benutzen.
    _seiten62 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                     encoding='utf-8').read()
    pruefe("w.get('besser_hoch', True)" in _seiten62,
           'die Anzeige faerbt nach der Richtung, nicht stur nach der Zahl')
    pruefe("fg=(ACCENT if w['faktor'] >= 1 else GOLD)" not in _seiten62,
           'die alte Regel „groesser als 1 ist gut" steht nicht mehr da')
    pruefe("w.get('absolut')" in _seiten62,
           'und unterscheidet Stueckzahl von Multiplikator')
    from scbp import sprache as _sp62
    for _k62 in ('s_he_weniger_gut', 's_he_absolut', 's_he_absolut_null'):
        _w62 = _sp62.TEXTE.get(_k62)
        pruefe(bool(_w62) and len(_w62) == 2 and all(_w62),
               'Text %s gibt es deutsch und englisch' % _k62)

    # ------------------------------------------------------------------
    # 63. Raffinerien — wohin mit dem Erz?
    #
    # Die Bergbau-Seite beantwortete nur die halbe Frage. Zwanzig Raffinerien
    # teilen sich zehn Profile, und der Unterschied ist kein Rundungsfehler:
    # Bei Bexalite liegen 18 Prozentpunkte zwischen bester und schlechtester
    # Wahl. Die Daten standen die ganze Zeit im selben Abruf — der Watcher hat
    # sie beim Sichern weggeworfen.
    print()
    print('63. Raffinerien')
    from scbp import bergbau as _bg63

    _daten63 = _bg63.laden()
    if not _daten63.get('refineryProfiles'):
        print('  [–]    keine Raffineriedaten vorhanden — uebersprungen')
    else:
        # Gegen die Tabelle auf scmdb.net gerechnet (Stand 4.10.0):
        _soll63 = {'Quartz': ('ARC-L1', 11), 'Titanium': ('MIC-L5', 13),
                   'Bexalite': ('MIC-L5', 12)}
        for _erz63, (_beste63, _bonus63) in _soll63.items():
            _r63 = _bg63.raffinerien_fuer(_erz63)
            pruefe(bool(_r63), '%s findet Raffinerien' % _erz63)
            if _r63:
                _namen63, _sys63, _wert63 = _r63[0]
                pruefe(_wert63 == _bonus63,
                       '%s: bester Bonus %+d %% (erwartet %+d)'
                       % (_erz63, _wert63, _bonus63))
                pruefe(any(n.startswith(_beste63) for n in _namen63),
                       '%s: beste Raffinerie ist %s' % (_erz63, _beste63))
        # ⚠ Was nicht im Profil steht, ist 0 % — nicht „unbekannt".
        _r63 = _bg63.raffinerien_fuer('Riccite')
        pruefe(_r63 and all(w == 0 for _n, _s, w in _r63),
               'ein Erz ohne Profileintrag steht ueberall auf 0 %')
        # ⚠ Schreibweisen: Profile sagen „Aluminum (Ore)", Rezepte „Aluminium".
        pruefe(bool(_bg63.raffinerien_fuer('Aluminium')),
               'die britische Schreibweise findet dieselben Raffinerien')
        # Und die Reihenfolge: beste zuerst.
        _r63 = _bg63.raffinerien_fuer('Bexalite')
        pruefe(all(_r63[i][2] >= _r63[i+1][2] for i in range(len(_r63)-1)),
               'die Liste steht nach Bonus sortiert, beste zuerst')

    # Die Daten muessen beim Sichern erhalten bleiben — genau daran lag es.
    _q63 = open(os.path.join(WURZEL, 'scbp', 'bergbau.py'), encoding='utf-8').read()
    pruefe("'refineries': roh.get('refineries')" in _q63,
           'die Raffinerien werden beim Sichern behalten')
    pruefe("da.get('refineries') is not None" in _q63,
           'und eine alte Ablage ohne sie wird einmal neu geholt')
    _q63b = open(os.path.join(WURZEL, 'scbp', 'herstellung.py'), encoding='utf-8').read()
    pruefe("'dismantle': roh.get('dismantle')" in _q63b,
           'dasselbe fuer die Zerlege-Sperrliste')
    from scbp import sprache as _sp63
    for _k63 in ('s_bg_raff_kopf', 's_bg_raff_zeile', 's_bg_raff_egal',
                 's_bg_raff_spanne', 's_bg_raff_weitere', 's_he_prozent',
                 's_he_spanne', 's_he_zerlegen'):
        _w63 = _sp63.TEXTE.get(_k63)
        pruefe(bool(_w63) and len(_w63) == 2 and all(_w63),
               'Text %s gibt es deutsch und englisch' % _k63)

    # ------------------------------------------------------------------
    # 64. Scan-Signatur — aus der Zahl des Scanners das Erz bestimmen
    #
    # Der Bergbau-Scanner im Spiel zeigt eine Zahl und verraet nicht, was
    # dahintersteckt. Die Zahl ist die Signatur des Rohstoffs mal der Zahl der
    # Brocken; wie viele es hoechstens sein koennen, sagt die Seltenheit.
    # Gegengerechnet gegen die Tabelle auf scmdb.net (Stand 4.10.0).
    print()
    print('64. Scan-Signatur')
    from scbp import bergbau as _bg64

    if not (_bg64.laden().get('elemente') or {}):
        print('  [–]    keine Rohstoff-Stammdaten vorhanden — uebersprungen')
    else:
        # a) Punktgenaue Treffer aus der Tabelle.
        for _eingabe64, _soll64, _anz64 in (
                ('7080', 'Beryl', 2),        # scmdb: „1 MATCH — 2x Beryl"
                ('3170', 'Quantainium', 1),
                ('4270', 'Iron', 1),
                ('25800', 'Ice', 6),
                ('19500', 'Torite', 5)):
            _tr64 = _bg64.signatur_suchen(_eingabe64)
            pruefe(bool(_tr64) and _tr64[0][0].startswith(_soll64)
                   and _tr64[0][1] == _anz64,
                   '%s -> %d× %s (gefunden: %s)'
                   % (_eingabe64, _anz64, _soll64,
                      ('%d× %s' % (_tr64[0][1], _tr64[0][0])) if _tr64 else 'nichts'))

        # b) ⚠ Ohne Toleranz wird NICHTS gerundet. Wer daneben liegt, soll das
        #    erfahren statt einen falschen Treffer vorgesetzt zu bekommen.
        pruefe(_bg64.signatur_suchen('9999') == [],
               'ein Wert ohne Entsprechung liefert nichts, statt zu raten')
        pruefe(len(_bg64.signatur_suchen('~8600')) > 1,
               'mit ~ davor kommen die Nachbarn dazu')
        pruefe(len(_bg64.signatur_suchen('12000-13000')) > 1,
               'eine Bereichssuche findet mehrere')

        # c) Die Seltenheit begrenzt die Vielfachen. Quantainium ist legendaer
        #    (hoechstens 2 Brocken) — ein drittes Vielfaches darf es NICHT
        #    geben, sonst behauptet das Werkzeug unmoegliche Vorkommen.
        _drei64 = _bg64.signatur_suchen('9510')      # 3170 x 3
        pruefe(not any(n.startswith('Quantainium') for n, _a, _g, _ab in _drei64),
               'legendaeres Erz wird nicht mit 3 Brocken gemeldet')
        _zwei64 = _bg64.signatur_suchen('6340')      # 3170 x 2
        pruefe(any(n.startswith('Quantainium') for n, _a, _g, _ab in _zwei64),
               'mit 2 Brocken dagegen schon')

        # d) Sortierung: die genaueste Uebereinstimmung zuerst.
        _tr64 = _bg64.signatur_suchen('~8600')
        pruefe(abs(_tr64[0][3]) <= abs(_tr64[-1][3]),
               'die genaueste Uebereinstimmung steht oben')

    # Die Stammdaten muessen beim Sichern erhalten bleiben.
    _q64 = open(os.path.join(WURZEL, 'scbp', 'bergbau.py'), encoding='utf-8').read()
    pruefe("'elemente': roh.get('mineableElements')" in _q64,
           'die Rohstoff-Stammdaten werden beim Sichern behalten')
    pruefe("da.get('elemente') is not None" in _q64,
           'und eine alte Ablage ohne sie wird einmal neu geholt')
    # ⚠ Das Eingabefeld darf NICHT im Neuzeichnen gebaut werden.
    _q64b = open(os.path.join(WURZEL, 'scbp', 'seiten.py'), encoding='utf-8').read()
    _vor64 = _q64b.split('def sig_zeichnen')[0]
    pruefe('sig_feld = rundes_feld' in _vor64,
           'das Scan-Feld steht ausserhalb des Neuzeichnens (Cursor bleibt)')
    from scbp import sprache as _sp64
    for _k64 in ('s_bg_sig_feld', 's_bg_sig_hilfe', 's_bg_sig_treffer',
                 's_bg_sig_nichts', 's_bg_sig_anzahl', 's_bg_sig_genau'):
        _w64 = _sp64.TEXTE.get(_k64)
        pruefe(bool(_w64) and len(_w64) == 2 and all(_w64),
               'Text %s gibt es deutsch und englisch' % _k64)

    # ------------------------------------------------------------------
    # 65. Auch eine umgestellte Uebersetzung wird erkannt
    #
    # Bis v3.3.0-rc37 wurde aus der `global.ini` nur der Teil VOR dem `%s`
    # genommen. Bei „Bauplan erhalten: %s" ist das richtig. Bei einer
    # umgestellten Formulierung — „%s ist eingetroffen" — waere davor nichts,
    # die Erkennung fiele auf die mitgelieferte Tabelle zurueck und faende
    # NICHTS: keine Fehlermeldung, keine uebersprungene Datei, einfach null
    # Bauplaene. Die gefaehrlichste Art zu scheitern.
    #
    # ⚠⚠ Das ist der Weg, auf dem JEDER Bauplanfund laeuft. Deshalb prueft (a)
    # zuerst, dass der heutige Fall zeichengleich geblieben ist.
    print()
    print('65. Umgestellte Uebersetzung')
    import re as _re65
    from scbp import phrasen as _ph65
    from scbp import logquelle as _lq65

    # a) ⚠ Der Normalfall MUSS unveraendert sein — Zeichen fuer Zeichen.
    _liste65 = _ph65.sammeln()[0]
    _alt65 = _ph65.RAHMEN % '|'.join(_re65.escape(_p) for _p in _liste65)
    pruefe(_ph65.muster().pattern == _alt65,
           'ohne umgestellte Formulierung ist der Ausdruck zeichengleich '
           'mit dem alten')

    # b) Zerlegen in Vor- und Nachtext.
    for _phrase65, _soll65 in (
            ('Bauplan erhalten: %s', ('Bauplan erhalten', '')),
            ('%s ist eingetroffen', ('', 'ist eingetroffen')),
            ('Bauplan: %s erhalten', ('Bauplan', 'erhalten')),
            ('Received Blueprint', ('Received Blueprint', ''))):
        pruefe(_ph65.zerlegen(_phrase65) == _soll65,
               'zerlegen(%r) -> %r' % (_phrase65, _ph65.zerlegen(_phrase65)))

    # c) Und die Erkennung an echten Zeilenformen.
    _m65 = _ph65.muster(['Bauplan erhalten', '%s ist eingetroffen',
                         'Bauplan: %s erhalten'])
    for _zeile65, _soll65 in (
            ('Added notification "Bauplan erhalten: Yubarev Pistol: " [3] to queue.',
             'Yubarev Pistol'),
            ('Added notification "Attrition-5 Repeater ist eingetroffen: " [1] to queue.',
             'Attrition-5 Repeater'),
            ('Added notification "Bauplan: Aves Shrike Helmet erhalten: " [2] to queue.',
             'Aves Shrike Helmet')):
        _funde65 = _lq65._namen_aus_text(_zeile65, _m65)
        pruefe(bool(_funde65) and _funde65[0][0] == _soll65,
               'erkannt: %s' % (_funde65[0][0] if _funde65 else 'NICHTS'))

    # d) ⚠ Auftrags-Meldungen duerfen NICHT mitgehen — sie haben dieselbe
    #    Zeilenform und wuerden den Bestand mit Auftragsnamen fluten.
    for _zeile65 in (
            'Added notification "Auftrag angenommen: Retake Platforms: " [4] to queue.',
            'Added notification "Neuer Auftrag: Koerper durchsuchen: " [5] to queue.'):
        pruefe(not _lq65._namen_aus_text(_zeile65, _m65),
               'eine Auftrags-Meldung loest nichts aus')

    # e) Die schweizerdeutsche Fassung steht in der Rueckfall-Tabelle.
    pruefe(any('überchoo' in _p for _p in _ph65.TABELLE.get('de', [])),
           'die live-CH-Formulierung ist dabei')

    # f) Ohne jede Formulierung darf der Ausdruck NIE treffen — ein Muster,
    #    das auf alles passt, waere schlimmer als gar keines.
    pruefe(not _ph65.muster([]).findall(
               'Added notification "Irgendwas: Irgendwer: " [9] to queue.'),
           'eine leere Liste ergibt einen Ausdruck, der nie trifft')

    # ------------------------------------------------------------------
    # 66. Preise — „kaufen oder abbauen?"
    #
    # Die Herstellung sagte, WAS fehlt, aber nicht, ob man es ueberhaupt kaufen
    # kann. Gemessen am 30.08.2026 ueber alle 26 Rohstoffe in Rezepten: 19
    # kaufbar, **7 nicht** (Aslarite, Lindinium, Ouratite, Quantainium,
    # Riccite, Savrilium, Torite). Fuenf davon stehen zusaetzlich auf der
    # Zerlege-Sperrliste — weder kaufbar noch zurueckzugewinnen.
    print()
    print('66. Rohstoffpreise')
    from scbp import preise as _pr66

    # a) ⚠ Ohne Netz und ohne Ablage darf NICHTS passieren.
    _echt66 = _pr66.laden
    try:
        _pr66.laden = lambda: {}
        pruefe(_pr66.preis('Iron') is None,
               'ohne Preisdaten kommt None zurueck, kein Absturz')
        pruefe(_pr66.alter() is None,
               'und das Alter ist None statt einer erfundenen Zahl')
    finally:
        _pr66.laden = _echt66

    # b) ⚠⚠ Jedes Material steht bei UEX ZWEIMAL — veredelt und als Erz. Wer
    #    beim Einlesen ueberschreibt, bekommt zufaellig die falsche Form: Beim
    #    ersten Versuch stand bei Iron „Kaufpreis 0", obwohl es fuer 2.643 im
    #    Regal liegt.
    _bau66 = {'format': _pr66.FORMAT, 'geholt': 1.0, 'waren': {
        'iron': [{'name': 'Iron', 'kauf': 2643.0, 'verkauf': 3376.0},
                 {'name': 'Iron (Ore)', 'kauf': 0.0, 'verkauf': 1000.0}],
        'borase': [{'name': 'Borase', 'kauf': 0.0, 'verkauf': 27266.0},
                   {'name': 'Borase (Ore)', 'kauf': 5520.0, 'verkauf': 14000.0}],
        'quantainium': [{'name': 'Quantainium', 'kauf': 0.0,
                         'verkauf': 145789.0}]}}
    _pr66.laden = lambda: _bau66
    try:
        pruefe(_pr66.preis('Iron')[0] == 2643.0,
               'Iron nimmt die veredelte Form (2643), nicht das Erz')
        pruefe(_pr66.preis('Borase')[0] == 5520.0
               and _pr66.preis('Borase')[2] == 'Borase (Ore)',
               'Borase nimmt das Erz — dort steht der einzige Kaufpreis')
        pruefe(_pr66.preis('Quantainium')[0] == 0.0,
               'Quantainium ist nicht kaufbar (Kaufpreis 0)')
        pruefe(_pr66.preis('Quantainium')[1] == 145789.0,
               'der Verkaufspreis kommt trotzdem mit')
        # ⚠ Die Namensangleichung muss auch hier greifen.
        pruefe(_pr66.preis('Iron (Ore)')[0] == 2643.0,
               'die Erz-Schreibweise findet denselben Eintrag')
        pruefe(_pr66.preis('Voellig Unbekanntes') is None,
               'ein unbekannter Name ergibt None, keinen Nullpreis')
    finally:
        _pr66.laden = _echt66

    # c) Die Anzeige darf „nicht kaufbar" NIE als „0 aUEC" schreiben.
    _seiten66 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                     encoding='utf-8').read()
    pruefe("t('s_he_nur_abbau')" in _seiten66,
           'fuer nicht kaufbare Rohstoffe steht ein eigener Text da')
    pruefe('def _geld' in _seiten66,
           'Betraege bekommen Tausenderpunkte (145789 liest sonst niemand)')
    # d) Der Abruf laeuft im Hintergrund, nicht beim Seitenaufbau.
    _haupt66 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'),
                    encoding='utf-8').read()
    pruefe('def _preise_tick' in _haupt66 and 'self._preise_tick()' in _haupt66,
           'die Preise werden im Hintergrund-Faden geholt')
    # ⚠ Die Qualitaet MUSS am Preis stehen. Ohne sie liest sich „kaufen" wie
    #   ein gleichwertiger Weg, der nur Geld statt Zeit kostet — und das ist
    #   falsch: Am Terminal gekaufte Ware hat immer Q 500, den Nullpunkt, also
    #   exakt x1,000 auf jede Eigenschaft.
    pruefe(_pr66.KAUF_QUALITAET == 500,
           'die Qualitaet gekaufter Ware ist als 500 festgehalten')
    pruefe('preis_modul.KAUF_QUALITAET' in _seiten66,
           'und steht in der Anzeige neben dem Preis')
    pruefe("t('s_he_kauf_q')" in _seiten66,
           'dazu der Satz, der die Regler einordnet')

    from scbp import sprache as _sp66
    for _k66 in ('s_he_kaufen', 's_he_nur_abbau', 's_he_kauf_q'):
        _w66 = _sp66.TEXTE.get(_k66)
        pruefe(bool(_w66) and len(_w66) == 2 and all(_w66),
               'Text %s gibt es deutsch und englisch' % _k66)

    # ------------------------------------------------------------------
    # 67. Ein Rezept wirklich AUFKLAPPEN
    #
    # ⚠⚠ Der Fehler, der diese Pruefung erzwungen hat (rc37 und rc38
    # ausgeliefert): Beim Auspacken der Zerlege-Angaben bekam eine Variable den
    # Namen `_dauer` — und ueberschrieb damit die gleichnamige Funktion in
    # derselben Datei. Ein paar Zeilen spaeter warf `_dauer(stufe['zeit'])`
    # dann `TypeError: 'int' object is not callable`.
    #
    # Sichtbar wurde das als **verschwundener Qualitaets-Block**: Die Ausnahme
    # brach den Aufbau mitten drin ab, die Herstellzeit blieb ohne Wert, und
    # alles danach — Regler, Wirkungen, Hinweise — fehlte ersatzlos.
    #
    # Der Selbsttest hat es nicht gesehen, weil er die Seite **baute**, aber
    # nie eine Zeile aufklappte. Genau das tut er jetzt: Ohne aufgeklapptes
    # Rezept laeuft `_herstellung_zeile` gar nicht bis zu der Stelle.
    print()
    print('67. Ein Rezept aufklappen')
    import tkinter as _tk67
    from scbp import seiten as _se67
    from scbp import herstellung as _he67

    # ⚠⚠ **Notfalls eigene Daten hinlegen.** Die Rezepte sind ein
    # heruntergeladener Zwischenspeicher im Ablageordner — der Selbsttest
    # arbeitet in einem Wegwerf-Ordner, dort liegt keiner. Bis rc42 hiess das:
    # Diese Pruefung wurde **immer uebersprungen**, auf jedem frischen Rechner
    # und im Bau-Lauf sowieso. Sie war fuer den `_dauer`-Fehler gebaut worden,
    # der zwei ausgelieferte Fassungen unbrauchbar gemacht hat — und lief nie.
    # Eine Pruefung, die nur bei ihrem Autor anschlaegt, ist keine.
    if not (_he67.laden().get('blueprints') or []):
        _mini67 = {
            'format': _he67.FORMAT, 'build': 'selbsttest',
            'blueprints': [{
                'tag': 'BP_TEST_Pruefung67', 'productName': 'Testgegenstand',
                'manufacturer': 'Behring', 'gear': 'fpsgear',
                'type': 'armour', 'subtype': 'combat',
                'tiers': [{'craftTimeSeconds': 200, 'slots': [
                    {'name': 'Armored Carapace',
                     'options': [{'type': 'resource', 'quantity': 0.04,
                                  'minQuality': 0, 'resourceName': 'Iron'}],
                     'modifiers': [{'startQuality': 0, 'endQuality': 1000,
                                    'modifierAtStart': 0.9,
                                    'modifierAtEnd': 1.1,
                                    'propertyName': 'Damage Mitigation',
                                    'propertyKey': 'armor_damagemitigation'}]},
                    {'name': 'Insulative Liner',
                     'options': [{'type': 'resource', 'quantity': 0.02,
                                  'minQuality': 0, 'resourceName': 'Aslarite'}],
                     'modifiers': [{'startQuality': 0, 'endQuality': 1000,
                                    'modifierAtStart': 0.8,
                                    'modifierAtEnd': 1.2,
                                    'propertyName': 'Min Temp',
                                    'propertyKey': 'armor_temperaturemin'},
                                   {'startQuality': 0, 'endQuality': 1000,
                                    'modifierAtStart': 0.8,
                                    'modifierAtEnd': 1.2,
                                    'propertyName': 'Max Temp',
                                    'propertyKey': 'armor_temperaturemax'}]}]}]}],
            'dismantle': {'returnPercentage': 50, 'blacklistedResources': []}}
        from scbp import pfade as _pf67
        with open(_pf67.app_datei(_he67.CACHE), 'w', encoding='utf-8') as _f67:
            json.dump(_mini67, _f67)
        _he67.vergessen()

    _rez67 = _he67.laden().get('blueprints') or []
    if not _rez67:
        print('  [–]    keine Rezeptdaten vorhanden — uebersprungen')
    else:
        # Ein Bauplan mit Zutaten UND Qualitaetswirkungen — nur der laeuft
        # durch alle Zweige.
        _kandidat67 = None
        for _b67 in _rez67:
            for _t67 in _b67.get('tiers') or []:
                for _s67 in _t67.get('slots') or []:
                    if _s67.get('modifiers') and _s67.get('options'):
                        _kandidat67 = _b67.get('productName')
                        break
                if _kandidat67:
                    break
            if _kandidat67:
                break
        pruefe(bool(_kandidat67), 'ein Bauplan mit Qualitaetswirkungen gefunden')

        if _kandidat67:
            _w67 = _tk67.Tk()
            _w67.withdraw()          # ⚠ kein Fenster ins Bild schieben
            try:
                # ⚠ **Echte Schrift-Objekte, keine Tupel.** Die Regler und
                # Auswahlfelder rufen `.metrics()` und `.measure()` darauf auf;
                # mit einem Tupel bricht der Aufbau mit
                # `AttributeError: 'tuple' object has no attribute 'metrics'`
                # ab — und der Test wuerde einen Fehler melden, den es im
                # Programm gar nicht gibt.
                import tkinter.font as _tkfont67
                _schrift67 = _tkfont67.Font(root=_w67, family='TkDefaultFont',
                                            size=10)

                class _Fenster67:
                    f_grund = f_klein = f_item = _schrift67
                    beim_zeigen = {}
                    bergbau_suche = ''

                    def oeffnen(self, _name):
                        pass

                _rahmen67 = _tk67.Frame(_w67)
                _eintrag67 = {'name': _kandidat67, 'basis': _kandidat67,
                              'habe': True, 'hersteller': 'Behring'}
                _offen67 = {'name': _kandidat67}      # ⭐ AUFGEKLAPPT
                _fehler67 = None
                try:
                    _se67._herstellung_zeile(_Fenster67(), _rahmen67,
                                             _eintrag67, _offen67,
                                             lambda: None)
                except Exception as _aus67:
                    _fehler67 = '%s: %s' % (type(_aus67).__name__, _aus67)
                pruefe(_fehler67 is None,
                       'ein aufgeklapptes Rezept baut ohne Ausnahme (%s)'
                       % (_fehler67 or 'sauber'))

                # Und der Qualitaets-Block muss wirklich dastehen — nicht nur
                # „keine Ausnahme". Genau der war ja verschwunden.
                def _texte67(w, raus):
                    try:
                        raus.append(str(w.cget('text')))
                    except Exception:
                        pass
                    for _k in w.winfo_children():
                        _texte67(_k, raus)
                    return raus

                _alle67 = ' | '.join(_texte67(_rahmen67, []))
                from scbp import sprache as _sp67
                pruefe(_sp67.t('s_he_regler_kopf') in _alle67,
                       'die Ueberschrift der Qualitaetsregler steht da')
                pruefe('Q ' in _alle67 or '×' in _alle67,
                       'und die Spannen-Angaben darunter')

                # ⚠⚠ Und JEDE Spanne steht unter IHRER Zeile.
                #
                # Bis rc42 bekam das Spannen-Etikett den Behaelter eine Ebene
                # hoeher als Elternteil. Es baute sich fehlerfrei auf, es stand
                # auch alles da — nur sammelten sich alle Spannen am Ende des
                # Blocks, waehrend die Werte oben blieben. Drei gleich
                # aussehende Zeilen `Q 0-1000 · x0.9-1.1`, und keine sagte mehr,
                # zu welchem Wert sie gehoert. Kein Absturz, keine Ausnahme —
                # nur eine Anzeige, die nichts mehr aussagt.
                #
                # Der Massstab ist deshalb die **Reihenfolge**: Im Behaelter der
                # Wertezeilen muessen sich Zeile (Frame) und Spanne (Label)
                # abwechseln.
                def _ist_wertezeile67(w):
                    # Eine Wertezeile ist ein Rahmen aus genau vier Etiketten:
                    # Eigenschaft, Faktor, Prozent, Herkunft. Nichts sonst
                    # darin — sonst waere es ein Behaelter, kein Zeile.
                    kinder = w.winfo_children()
                    return (w.winfo_class() == 'Frame' and len(kinder) == 4
                            and all(_x.winfo_class() == 'Label'
                                    for _x in kinder))

                def _wertebehaelter67(w):
                    for _k in w.winfo_children():
                        if _ist_wertezeile67(_k):
                            return _k.master
                        _tiefer = _wertebehaelter67(_k)
                        if _tiefer is not None:
                            return _tiefer
                    return None

                _halter67 = _wertebehaelter67(_rahmen67)
                pruefe(_halter67 is not None,
                       'der Behaelter mit den Wertezeilen ist auffindbar')
                if _halter67 is not None:
                    _folge67 = [_s.winfo_class() for _s in _halter67.pack_slaves()]
                    _zeilen67 = _folge67.count('Frame')
                    _spannen67 = _folge67.count('Label')
                    # Nach jeder Zeile genau ein Etikett — dann wechseln sich
                    # Frame und Label ab, und keine Spanne ist verrutscht.
                    _wechsel67 = _folge67[:2 * _zeilen67] == (
                        ['Frame', 'Label'] * _zeilen67)
                    pruefe(_zeilen67 > 0 and _wechsel67,
                           'jede Spanne steht direkt unter ihrer Wertezeile '
                           '(%d Zeilen, %d Spannen: %s)'
                           % (_zeilen67, _spannen67,
                              ' '.join(_folge67[:6]) or 'leer'))
            finally:
                _w67.destroy()

    # ⚠ Kein lokaler Name darf eine Funktion derselben Datei verdecken.
    # Statische Gegenprobe fuer genau diesen Fehler.
    import re as _re67
    _q67 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'), encoding='utf-8').read()
    _funktionen67 = set(_re67.findall(r'^def (_?\w+)\(', _q67, _re67.M))
    _verdeckt67 = []
    for _m67 in _re67.finditer(r'^\s+([_a-zA-Z][\w, ]*?)\s*=\s*\S', _q67, _re67.M):
        for _name67 in (_n.strip() for _n in _m67.group(1).split(',')):
            if _name67 in _funktionen67:
                _zeile67 = _q67[:_m67.start()].count('\n') + 1
                _verdeckt67.append('%s (Zeile %d)' % (_name67, _zeile67))
    pruefe(not _verdeckt67,
           'kein lokaler Name verdeckt eine Funktion derselben Datei (%d)'
           % len(_verdeckt67))
    for _x67 in _verdeckt67[:5]:
        print('       ·', _x67)

    # ------------------------------------------------------------------
    # 68. Der Namensvorschlag steht NEBEN dem Eingabefeld
    #
    # Bis v3.3.0-rc39 hing er ganz unten unter den Knoepfen — 557 Pixel unter
    # dem Feld, in das getippt wird. Am 30.08.2026 gemeldet: „wenn ich
    # Savrilium einlagern will, suche ich nicht dort unten nach dem Begriff um
    # drauf zu klicken." Ein Vorschlag, den man suchen muss, ist keiner.
    print()
    print('68. Namensvorschlag am Eingabefeld')
    import tkinter as _tk68
    import tkinter.font as _tkfont68
    from scbp import seiten as _se68

    _w68 = _tk68.Tk()
    _w68.withdraw()                      # ⚠ kein Fenster ins Bild schieben
    try:
        _w68.geometry('1200x900')
        _s68 = _tkfont68.Font(root=_w68, family='TkDefaultFont', size=10)

        class _Fenster68:
            f_grund = f_klein = f_item = f_fett = f_titel = f_sub = _s68
            beim_zeigen = {}
            bergbau_suche = ''

            def oeffnen(self, _n):
                pass

            def sagen(self, *_a):
                pass

        _rahmen68 = _tk68.Frame(_w68)
        _rahmen68.pack(fill='both', expand=True)
        _se68._lager(_Fenster68(), _rahmen68)
        _w68.update_idletasks()

        def _sammeln68(w, art, raus):
            if isinstance(w, art):
                raus.append(w)
            for _k in w.winfo_children():
                _sammeln68(_k, art, raus)
            return raus

        def _mit_text68(w, text, raus):
            try:
                if text in str(w.cget('text')):
                    raus.append(w)
            except Exception:
                pass
            for _k in w.winfo_children():
                _mit_text68(_k, text, raus)
            return raus

        _felder68 = _sammeln68(_rahmen68, _tk68.Entry, [])
        pruefe(bool(_felder68), 'die Lager-Seite hat Eingabefelder')
        # ⚠ Ohne Rezeptdaten gibt es keine Namen, zu denen etwas vorgeschlagen
        # werden koennte — auf dem Bau-Laeufer ist das der Normalfall.
        from scbp import herstellung as _he68
        if _felder68 and _he68.aehnliche_rohstoffe('sa'):
            _felder68[0].insert(0, 'sa')
            _w68.update_idletasks()
            _v68 = _mit_text68(_rahmen68, 'Savrilium', [])
            pruefe(bool(_v68), 'nach „sa" erscheint ein Vorschlag')
            if _v68:
                _abstand68 = abs(_v68[0].winfo_rooty()
                                 - _felder68[0].winfo_rooty())
                pruefe(_abstand68 < 80,
                       'der Vorschlag steht auf Hoehe des Feldes (%d px, '
                       'vorher 557)' % _abstand68)
                pruefe(_v68[0].winfo_rootx() < _felder68[0].winfo_rootx(),
                       'und links davon')
        elif _felder68:
            print('  [–]    keine Rezeptdaten — Vorschlagstest uebersprungen')

        # ---- Rechnen im Mengenfeld ----
        # ⚠⚠ Beim Bearbeiten steht die aktuelle Menge schon im Feld. Wer drei
        # dazulegen will, tippt hinten „+3" an — und hat „1.04+3" dastehen.
        # Bis v3.3.0-rc39 zaehlte nur ein FUEHRENDES Vorzeichen; genau die
        # natuerliche Eingabe wurde abgelehnt („Trag eine Menge ein, zum
        # Beispiel 12,5"). Am 30.08.2026 gemeldet.
        from scbp import rohstoffe as _ro68
        for _eingabe68, _vorher68, _soll68 in (
                ('4,5', 1.04, 4.5),          # blosse Zahl
                ('+3', 1.04, 4.04),          # nur Buchung
                ('1.04+3', 1.04, 4.04),      # angehaengt — das war der Fehler
                ('1,04+3', 1.04, 4.04),      # mit Komma genauso
                ('12,5-0,5', 0.0, 12.0),     # Minus mitten drin
                ('-0,5', 1.04, 0.54)):       # abbuchen
            _ist68 = _ro68.rechnen(_eingabe68, _vorher68)
            pruefe(_ist68 is not None and abs(_ist68 - _soll68) < 1e-9,
                   '%r bei Bestand %g ergibt %s (erwartet %g)'
                   % (_eingabe68, _vorher68, _ist68, _soll68))
        # ⚠ Beide Wege muessen dasselbe ergeben — das ist der Punkt: Niemand
        #   muss wissen, welchen das Programm meint.
        pruefe(_ro68.rechnen('+3', 1.04) == _ro68.rechnen('1.04+3', 1.04),
               '„+3" und „1.04+3" ergeben dasselbe')
        for _unsinn68 in ('12 SCU', '', '+abc', 'abc'):
            pruefe(_ro68.rechnen(_unsinn68, 1.0) is None,
                   'Unsinn (%r) ergibt None statt einer Zahl' % _unsinn68)

        # ---- Und der Hinweistext darf nicht wieder abstrakt werden ----
        from scbp import sprache as _sp68
        _hinweis68 = _sp68.TEXTE['s_lg_rechnen'][0]
        pruefe('+3' in _hinweis68 and '-3' in _hinweis68,
               'der Hinweis nennt die Zeichen konkret')
        pruefe('abgebucht' not in _hinweis68,
               'und benutzt keine Buchhaltersprache mehr')
        for _k68 in ('s_lg_ergibt', 's_lg_ergibt_null', 's_lg_ergibt_minus'):
            _w68t = _sp68.TEXTE.get(_k68)
            pruefe(bool(_w68t) and len(_w68t) == 2 and all(_w68t),
                   'Text %s gibt es deutsch und englisch' % _k68)
    finally:
        _w68.destroy()

    # ------------------------------------------------------------------
    # 69. Kein abgeschnittener Text im aufgeklappten Rezept
    #
    # ⚠⚠ Der Fehler, der diese Pruefung erzwungen hat: Das Etikett fuer den
    # Qualitaetsfaktor hatte `width=9` — eine **Zusage ueber den Inhalt**. Als
    # in v3.3.0-rc37 die Prozentzahl in dasselbe Etikett geschrieben wurde,
    # schnitt Tk sie stumm ab: Auf dem Bildschirm stand „× 1.047  +4.(" statt
    # „+4,70 %". Kein Fehler, keine Meldung — nur eine halbe Zahl.
    #
    # Wer Inhalt zu einem Feld fester Breite dazutut, muss die Breite anfassen.
    # Diese Pruefung merkt es, wenn er es vergisst — an JEDEM Etikett, nicht
    # nur an diesem einen.
    print()
    print('69. Nichts wird abgeschnitten')
    import tkinter as _tk69
    import tkinter.font as _tkfont69
    from scbp import seiten as _se69
    from scbp import herstellung as _he69

    _rez69 = _he69.laden().get('blueprints') or []
    if not _rez69:
        print('  [–]    keine Rezeptdaten vorhanden — uebersprungen')
    else:
        _kandidat69 = None
        for _b69 in _rez69:
            for _t69 in _b69.get('tiers') or []:
                for _s69 in _t69.get('slots') or []:
                    if _s69.get('modifiers') and _s69.get('options'):
                        _kandidat69 = _b69.get('productName')
                        break
                if _kandidat69:
                    break
            if _kandidat69:
                break

        _w69 = _tk69.Tk()
        _w69.withdraw()                  # ⚠ kein Fenster ins Bild schieben
        try:
            _w69.geometry('1300x1000')
            _s69f = _tkfont69.Font(root=_w69, family='TkDefaultFont', size=10)

            class _Fenster69:
                f_grund = f_klein = f_item = f_fett = f_titel = f_sub = _s69f
                beim_zeigen = {}
                bergbau_suche = ''

                def oeffnen(self, _n):
                    pass

                def sagen(self, *_a):
                    pass

            _rahmen69 = _tk69.Frame(_w69)
            _rahmen69.pack(fill='both', expand=True)
            _se69._herstellung_zeile(
                _Fenster69(), _rahmen69,
                {'name': _kandidat69, 'basis': _kandidat69, 'habe': True,
                 'hersteller': 'Behring'},
                {'name': _kandidat69}, lambda: None)
            _w69.update_idletasks()

            _kurz69 = []

            def _messen69(w):
                if isinstance(w, _tk69.Label):
                    _txt69 = str(w.cget('text'))
                    # ⚠ Nur Etiketten OHNE Umbruch pruefen. Fliesstext soll
                    #   umbrechen, nicht in eine Zeile passen.
                    try:
                        _umbruch69 = int(w.cget('wraplength') or 0)
                    except Exception:
                        _umbruch69 = 0
                    if _txt69.strip() and not _umbruch69:
                        _noetig69 = _s69f.measure(_txt69)
                        # ⚠⚠ **`winfo_width()` taugt hier NICHT.** Das Fenster
                        # ist bewusst nicht angezeigt (sonst schoebe der Test
                        # ein Fenster ins Bild); fuer alles Unangezeigte
                        # liefert Tk stur **1**. Ein Vergleich dagegen
                        # ueberspringt jede Zeile und die Pruefung meldet
                        # zufrieden „nichts abgeschnitten", waehrend auf dem
                        # Bildschirm eine halbe Zahl steht. Genau so lief mein
                        # erster Anlauf am 30.08.2026 ins Leere.
                        #
                        # `winfo_reqwidth()` ist die Breite, die Tk dem
                        # Etikett geben WIRD — bei `width=9` sind das 76 px,
                        # der Text braucht 112. Das ist messbar, ohne etwas
                        # anzuzeigen.
                        _hat69 = w.winfo_reqwidth()
                        if _hat69 > 1 and _noetig69 > _hat69:
                            _kurz69.append('%r braucht %d px, hat %d'
                                           % (_txt69, _noetig69, _hat69))
                for _k69 in w.winfo_children():
                    _messen69(_k69)

            _messen69(_rahmen69)
            pruefe(not _kurz69,
                   'kein Etikett im Rezept schneidet seinen Text ab (%d)'
                   % len(_kurz69))
            for _x69 in _kurz69[:6]:
                print('       ·', _x69)

            # Und die Prozentzahl muss VOLLSTAENDIG dastehen — genau die war
            # es ja.
            def _prozente69(w, raus):
                try:
                    _x = str(w.cget('text'))
                    if '%' in _x and any(_z in _x for _z in '+-−'):
                        raus.append(_x)
                except Exception:
                    pass
                for _k in w.winfo_children():
                    _prozente69(_k, raus)
                return raus

            _p69 = _prozente69(_rahmen69, [])
            pruefe(bool(_p69), 'die Prozentangaben stehen da (%d)' % len(_p69))
            pruefe(all(_x.rstrip().endswith('%') for _x in _p69),
                   'und enden auf das Prozentzeichen — keine halbe Zahl (%s)'
                   % (_p69[:2],))
        finally:
            _w69.destroy()

    # ------------------------------------------------------------------
    # 70. Nur Echtes ins Lager — Rohstoff UND Lagerort
    #
    # ⚠⚠ Der Grund ist nicht Ordnungssinn. Ein freies Textfeld heisst, dass
    # jemand Schimpfwoerter, Religioeses oder Politisches eintraegt, ein
    # Bildschirmfoto macht und es verbreitet — und am Ende fragt niemand, wer
    # getippt hat: Es steht in diesem Werkzeug. Am 30.08.2026 festgelegt:
    # „NUR was auch in der Rohstoff-Liste ist darf speicherbar sein, sonst
    # nichts." Und: „Lagerort gilt exakt das Gleiche."
    print()
    print('70. Nur Echtes ins Lager')
    from scbp import herstellung as _he70
    from scbp import orte as _or70

    # a) Der Ausweg-Knopf ist WEG und darf nicht zurueckkommen.
    _q70 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'), encoding='utf-8').read()
    pruefe("t('s_lg_trotzdem')" not in _q70,
           'es gibt keinen Knopf „Trotzdem eintragen" mehr')
    # ⚠ Auch der TEXT muss weg. Beim Aufraeumen blieb `s_lg_unbekannt` stehen
    # und behauptete weiter „Du kannst es trotzdem eintragen" — das Programm
    # versprach also etwas, das es nicht mehr tut (30.08.2026 aufgefallen).
    # Wer eine Funktion entfernt, sucht nach ALLEN Stellen, die sie
    # beschreiben, nicht nur nach dem Knopf.
    from scbp import sprache as _sp70
    pruefe('s_lg_trotzdem' not in _sp70.TEXTE,
           'und keinen Text mehr dafuer')
    for _k70 in ('s_lg_unbekannt', 's_lg_name_fremd'):
        _w70 = _sp70.TEXTE.get(_k70) or ('', '')
        pruefe('trotzdem' not in _w70[0].lower()
               and 'still add' not in _w70[1].lower(),
               '%s verspricht keinen Ausweg mehr' % _k70)
    pruefe('h_modul.lager_name(name)' in _q70,
           'der Name wird gegen die Lagerliste geprueft')
    pruefe('orte_modul.offizieller_name(ort.get())' in _q70,
           'und der Lagerort gegen die Ortsliste')

    # b) Die Liste selbst.
    _liste70 = _he70.einlagerbar()
    if len(_liste70) > 30:
        pruefe(len(_liste70) >= 39,
               'die Lagerliste hat %d Namen (Mineralien + Pflanzen)' % len(_liste70))
        for _pflanze70 in ('Flareweed', 'Heart of the Woods', 'Sunset Berry'):
            pruefe(_he70.darf_ins_lager(_pflanze70),
                   'Pflanze %s ist einlagerbar' % _pflanze70)
        for _erz70 in ('Sadaryx', 'Saldynium', 'Jaclium'):
            pruefe(_he70.darf_ins_lager(_erz70),
                   'Mineral ohne Rezept (%s) ist einlagerbar' % _erz70)
        for _mist70 in ('savratum', 'Bei Oma im Keller', 'Politik', 'xyz123'):
            pruefe(not _he70.darf_ins_lager(_mist70),
                   '%r wird abgelehnt' % _mist70)
        # ⚠ Vorschlaege muessen aus der GANZEN Liste kommen. Sadaryx kam nicht,
        #   weil sie nur aus den Rezept-Materialien stammten.
        pruefe(_he70.aehnliche_lagernamen('Sad') == ['Sadaryx'],
               'Sadaryx wird vorgeschlagen (kam frueher nicht)')
    else:
        print('  [–]    keine Rezept-/Bergbaudaten — Listentest uebersprungen')

    # c) Der Lagerort.
    if _or70.alle():
        pruefe(len(_or70.alle()) > 100,
               'die Ortsliste hat %d Eintraege' % len(_or70.alle()))
        pruefe(_or70.kennt('Orison') and _or70.kennt('Lorville'),
               'bekannte Orte werden erkannt')
        pruefe(not _or70.kennt('Bei Oma im Keller'),
               'ein erfundener Ort wird abgelehnt')
        pruefe(_or70.kennt(''), 'leer bleibt erlaubt — das Feld ist freiwillig')
        # ⚠ Teiltext, nicht nur Wortanfang: UEX schreibt „Pyro Gateway
        #   (Stanton)" und „Checkmate Station".
        pruefe(any('Pyro Gateway' in o for o in _or70.aehnliche('pyro')),
               '„pyro" schlaegt die Gateways vor')
        pruefe(_or70.aehnliche('checkmate') == ['Checkmate Station'],
               '„checkmate" findet die Station')
    else:
        # ⚠ Ohne Liste darf NICHTS blockieren — sonst laesst sich bei einem
        #   ersten Start ohne Netz gar nichts eintragen.
        pruefe(_or70.kennt('Irgendwo'),
               'ohne Ortsliste blockiert das Feld nicht')
        print('  [–]    keine Ortsliste vorhanden — Rest uebersprungen')

    # d) Qualitaet: nur 0 bis 1000.
    pruefe('0 <= q <= 1000' in _q70,
           'die Qualitaet ist auf 0–1000 begrenzt')

    # ------------------------------------------------------------------
    # 71. Keine fremde Uebersetzung im Paket
    #
    # ⚠⚠ Die deutsche Uebersetzung des Spiels stammt von rjcncpt
    # (StarCitizen-Deutsch-INI) und steht unter **CC BY-NC-SA 4.0**. Der Autor
    # setzt das durch: Am 10.04.2025 wurde ein Repository nach einer
    # DMCA-Beschwerde von GitHub entfernt — Grund war „nicht-konforme
    # Weitergabe unter CC-BY-NC-SA-4.0" und fehlende Namensnennung.
    #
    # Der Watcher ist davon nicht betroffen, weil er die Uebersetzung **nicht
    # weitergibt**: Er liest die Datei auf dem Rechner des Nutzers und ergaenzt
    # sie dort. Damit das so bleibt, prueft das hier bei jedem Bau nach — eine
    # mitgelieferte `global.ini` waere genau der Fehler, der ein Repo kostet.
    print()
    print('71. Keine fremde Uebersetzung im Paket')
    _versioniert71 = _versionierte_dateien(WURZEL, ('.ini', '.json', '.txt'))
    _verdaechtig71 = []
    for _p71 in _versioniert71:
        _rel71 = os.path.relpath(_p71, WURZEL)
        if _rel71.endswith('.ini'):
            _verdaechtig71.append('%s (eine .ini gehoert nicht ins Repo)' % _rel71)
            continue
        if not _rel71.endswith('.json'):
            continue
        try:
            _txt71 = open(_p71, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        # ⚠ Deutsche Spieltexte erkennt man an Umlauten und ß. Ein Katalog aus
        #   der ENGLISCHEN global.ini (CIGs eigene Datei) hat davon keinen.
        _umlaute71 = sum(_txt71.count(_z) for _z in 'äöüßÄÖÜ')
        if _umlaute71 > 40:
            _verdaechtig71.append('%s (%d Umlaute — uebersetzte Spieltexte?)'
                                  % (_rel71, _umlaute71))
    pruefe(not _verdaechtig71,
           'keine fremde Uebersetzung im Repo (%d Funde)' % len(_verdaechtig71))
    for _x71 in _verdaechtig71[:5]:
        print('       ·', _x71)

    # Der mitgelieferte Katalog muss sagen, woher er stammt — und das muss die
    # ENGLISCHE Datei sein.
    _kat71 = os.path.join(WURZEL, 'daten', 'katalog.json')
    if os.path.exists(_kat71):
        import json as _json71
        _d71 = _json71.load(open(_kat71, encoding='utf-8'))
        pruefe('englisch' in str(_d71.get('quelle', '')).lower(),
               'der mitgelieferte Katalog stammt aus der englischen Datei (%r)'
               % _d71.get('quelle'))
        pruefe(_d71.get('weitergabe') is True,
               'und ist ausdruecklich als weitergebbar gekennzeichnet')

    # Und der Urheber muss genannt sein — Name UND Repository, so verlangt es
    # die Lizenz.
    _q71 = open(os.path.join(WURZEL, 'scbp', 'seiten.py'), encoding='utf-8').read()
    pruefe('rjcncpt' in _q71,
           'der Urheber der Uebersetzung ist im Programm genannt')
    pruefe('CC BY-NC-SA 4.0' in _q71,
           'mit seiner Lizenz')
    pruefe('github.com/rjcncpt/StarCitizen-Deutsch-INI' in _q71,
           'und mit seinem Repository')
    for _readme71 in ('README.md', 'README.de.md'):
        _r71 = open(os.path.join(WURZEL, _readme71), encoding='utf-8').read()
        pruefe('rjcncpt' in _r71 and 'CC BY-NC-SA' in _r71,
               '%s nennt Urheber und Lizenz' % _readme71)

    # ⚠⚠ **Die erste Zeile der `global.ini` muss stehen bleiben.** Der Autor
    # verlangt das ausdruecklich: „belasse in der global.ini-Datei die erste
    # Zeile mit der Angabe zur Ursprungsuebersetzung bestehen. Das hilft
    # anderen Spielern ohne Umwege an die urspruengliche Uebersetzung zu
    # gelangen."
    #
    # Bisher blieb sie stehen, weil die Injektion den Schluessel schlicht nicht
    # anfasst — also zufaellig. Diese Pruefung macht daraus eine Zusage.
    _inj71 = open(os.path.join(WURZEL, 'scbp', 'injektion.py'),
                  encoding='utf-8').read()
    pruefe('Frontend_PU_Version' not in _inj71
           or 'nicht anfassen' in _inj71,
           'die Injektion fasst die Quellenangabe nicht an')

    # Und am echten Fall gegengeprueft — an **jeder** vorhandenen Sprachdatei.
    #
    # ⚠ Nur Dateien mit einer Quellenangabe zaehlen. Die englische `global.ini`
    # ist CIGs eigene und traegt keine; sie mit zu pruefen hiesse, einen Fehler
    # zu melden, wo keiner sein kann. Genau so lief mein erster Anlauf: Er nahm
    # die erste Datei im Ordner — die englische — und schlug an.
    from scbp import pfade as _pf71
    _dateien71 = []
    try:
        _basis71 = os.path.join(_pf71.spiel_ordner() or '', 'data', 'Localization')
        for _ordner71 in (sorted(os.listdir(_basis71))
                          if os.path.isdir(_basis71) else []):
            _kandidat71 = os.path.join(_basis71, _ordner71, 'global.ini')
            if os.path.isfile(_kandidat71):
                _dateien71.append((_ordner71, _kandidat71))
    except Exception:
        _dateien71 = []

    _geprueft71 = 0
    for _name71, _pfad71 in _dateien71:
        with open(_pfad71, encoding='utf-8-sig', errors='ignore') as _fh71:
            _zeile1_71 = _fh71.readline()
            _rest71 = _fh71.read()
        # Eine Quellenangabe erkennt man am Schluessel UND daran, dass sie auf
        # die Herkunft verweist.
        if not _zeile1_71.startswith('Frontend_PU_Version'):
            continue
        _geprueft71 += 1
        _marken71 = _rest71.count('[SCBPW]') + _rest71.count('<EM4>')
        pruefe('[SCBPW]' not in _zeile1_71 and '<EM4>' not in _zeile1_71,
               '%s: die Quellenangabe traegt keine unserer Marken '
               '(%d Marken in der Datei)' % (_name71, _marken71))
        pruefe('sc-deutsch-launcher' in _zeile1_71.lower()
               or 'übersetzung' in _zeile1_71.lower()
               or 'übersetzig' in _zeile1_71.lower(),
               '%s: der Verweis auf die Ursprungsuebersetzung steht noch da'
               % _name71)
    if not _geprueft71:
        print('  [–]    keine Datei mit Quellenangabe gefunden — '
              'Gegenprobe uebersprungen')

    # ------------------------------------------------------------------
    # 72. Der Startverlauf im Bericht bleibt lesbar
    #
    # ⚠ Die Spur ist bei einem harten Absturz das Einzige, was uebrig bleibt —
    # die letzte Zeile sagt, wie weit der Start kam. Im rc42-Bericht stand
    # davon **kein einziger Schritt** mehr: zwoelfmal „Liste: zeichnen
    # beginnt" hatte den ganzen Ausschnitt gefuellt. Zwei Ursachen, beide hier
    # abgesichert:
    #
    #   a) Getrennt wurde per Vorsilbe („Seite ") — jeder neue Spur-Aufruf
    #      irgendwo im Programm galt damit als Startschritt. Jetzt ist die
    #      Grenze die Zeile, mit der der Start endet.
    #   b) Wiederholungen wurden Zeile fuer Zeile gezeigt. Jetzt zaehlt der
    #      Bericht sie zusammen.
    print()
    print('72. Der Startverlauf im Bericht bleibt lesbar')
    from scbp import fehler as _fh72
    from scbp import bericht as _br72

    # a) Die Grenze muss die Zeile sein, die das Programm wirklich schreibt.
    _quelle72 = open(os.path.join(WURZEL, 'sc_bp_watcher.py'),
                     encoding='utf-8').read()
    pruefe("fehler.spur('%s')" % _fh72.SPUR_GRENZE in _quelle72,
           'die Grenzzeile „%s" wird beim Start auch wirklich geschrieben'
           % _fh72.SPUR_GRENZE)

    # b) Ein Bedien-Ereignis nach der Grenze darf nicht im Start landen —
    #    auch dann nicht, wenn es nicht mit „Seite " anfaengt.
    _echt72 = _fh72.letzte_spur
    try:
        _spur72 = ['05:10:00  Start, Version 9.9.9, test',
                   '05:10:01  Tk-Wurzel steht',
                   '05:10:02  Overlay wird gebaut',
                   '05:10:03  Overlay steht',
                   '05:10:04  ' + _fh72.SPUR_GRENZE]
        _spur72 += ['05:11:%02d  Liste: zeichnen beginnt' % _i
                    for _i in range(12)]
        _spur72 += ['05:12:00  Seite lager: zeigen']
        _fh72.letzte_spur = lambda: _spur72
        _start72, _bedien72 = _fh72.spur_geteilt()
    finally:
        _fh72.letzte_spur = _echt72
    pruefe(len(_start72) == 5 and _start72[-1].endswith(_fh72.SPUR_GRENZE),
           'der Startverlauf endet an der Grenzzeile (%d Zeilen)'
           % len(_start72))
    pruefe(not [_z for _z in _start72 if 'Liste: zeichnen' in _z],
           'Bedienung nach dem Start faellt nicht in den Startverlauf')

    # c) Zwoelf gleiche Zeilen werden zu einer mit Zaehler.
    _knapp72 = _br72._gedraengt(_bedien72)
    pruefe(len(_knapp72) == 2,
           'zwoelf gleiche Zeilen werden zusammengefasst (%d Zeilen uebrig)'
           % len(_knapp72))
    pruefe('(12×)' in _knapp72[0],
           'die Zusammenfassung nennt die Anzahl')

    # d) Und der Ausschnitt, den der Bericht zeigt, enthaelt den Start noch.
    _sichtbar72 = _br72._gedraengt(_start72)[-12:]
    pruefe(any('Start, Version' in _z for _z in _sichtbar72)
           and any(_fh72.SPUR_GRENZE in _z for _z in _sichtbar72),
           'im sichtbaren Ausschnitt stehen erster und letzter Startschritt')

    # ------------------------------------------------------------------
    # 73. Die Zahlen in der Anleitung stimmen noch
    #
    # ⚠ In der README stehen Zahlen: „für 670 der 738 Bauplaene steht, woher
    # sie kommen", „zu jedem der 1.597 herstellbaren Gegenstaende". Die sind
    # kein Beiwerk — sie sind das Versprechen, das jemand vor dem Herunterladen
    # liest. Und sie veralten mit **jedem** Spiel-Patch, ohne dass irgendetwas
    # anschlaegt: Am 30.08.2026 stand dort 655 von 722, waehrend die Daten
    # laengst 670 von 738 hergaben. Aufgefallen ist es nur, weil jemand von
    # Hand nachgezaehlt hat.
    #
    # ⚠ Diese Pruefung braucht die heruntergeladenen Daten und wird ohne sie
    # uebersprungen — im Bau-Lauf also immer. Sie greift dort, wo sie greifen
    # muss: auf dem Rechner, auf dem veroeffentlicht wird.
    print()
    print('73. Die Zahlen in der Anleitung stimmen noch')
    import re as _re73
    from scbp import katalog as _ka73
    from scbp import herstellung as _he73

    # ⚠ Kurz aus dem Wegwerf-Ordner heraustreten. Der Selbsttest arbeitet in
    # einem leeren `SC_BP_HOME`; die echten Daten liegen im Ablageordner des
    # Nutzers, und genau die zeigt die Anleitung.
    _heim73 = os.environ.pop('SC_BP_HOME', None)
    try:
        _ka73.vergessen() if hasattr(_ka73, 'vergessen') else None
        _he73.vergessen()
        try:
            _bp73 = (_ka73.laden().get('bauplaene') or {})
        except Exception:
            _bp73 = {}
        _gezeigt73 = []
        try:
            _gezeigt73 = _he73.mit_bestand(set())
        except Exception:
            pass
    finally:
        if _heim73 is not None:
            os.environ['SC_BP_HOME'] = _heim73
        _ka73.vergessen() if hasattr(_ka73, 'vergessen') else None
        _he73.vergessen()

    if not _bp73 or not _gezeigt73:
        print('  [–]    keine Katalog- oder Rezeptdaten — uebersprungen')
    else:
        _mitq73 = sum(1 for _v in _bp73.values() if _v.get('q'))
        _soll73 = {'baupläne': len(_bp73), 'herkunft': _mitq73,
                   'herstellbar': len(_gezeigt73)}
        print('       Daten: %d Baupläne, %d mit Herkunft, %d herstellbar'
              % (_soll73['baupläne'], _soll73['herkunft'],
                 _soll73['herstellbar']))

        def _zahlen73(text):
            # „670 der 738", „670 of 738", „670 von 738" — beide Zahlen.
            paare = set()
            for _m in _re73.finditer(
                    r'\*\*([\d.,]+)\s+(?:der|von|of(?: the)?)\s+([\d.,]+)\*\*',
                    text):
                paare.add((int(_m.group(1).replace('.', '').replace(',', '')),
                           int(_m.group(2).replace('.', '').replace(',', ''))))
            einzeln = set()
            for _m in _re73.finditer(r'\*\*([\d][\d.,]{2,})\*\*', text):
                einzeln.add(int(_m.group(1).replace('.', '').replace(',', '')))
            return paare, einzeln

        for _name73 in ('README.de.md', 'README.md'):
            _txt73 = open(os.path.join(WURZEL, _name73), encoding='utf-8').read()
            _paare73, _einzeln73 = _zahlen73(_txt73)
            _falsch73 = [pa for pa in _paare73
                         if pa != (_soll73['herkunft'], _soll73['baupläne'])]
            pruefe(not _falsch73,
                   '%s: „X von Y Bauplaenen" stimmt (%s)'
                   % (_name73, _falsch73 or 'alles aktuell'))
            # Die Zahl der herstellbaren Gegenstaende steht allein da.
            _herst73 = [z for z in _einzeln73 if 1000 <= z <= 5000]
            pruefe(all(z == _soll73['herstellbar'] for z in _herst73),
                   '%s: die Zahl der herstellbaren Gegenstaende stimmt (%s)'
                   % (_name73, sorted(_herst73) or 'keine genannt'))

    # ------------------------------------------------------------------
    # 74. `SC_BP_NO_NET` gilt ueberall
    #
    # ⚠ Die Anleitung verspricht: „Beides laesst sich mit `SC_BP_NO_NET=1`
    # abschalten." Bis rc42 stimmte das nur zur Haelfte — Katalog, Preise,
    # Orte, Serverstatus und Update-Frage hielten sich daran, die
    # Uebersetzungsquellen und die Auftragsdaten des SCDL-Teams nicht. Wer die
    # Schalterstellung ernst nimmt, muss sich darauf verlassen koennen.
    #
    # Ausgenommen ist einzig `bericht.py`: Es sendet nur, wenn jemand den Knopf
    # drueckt, und sagt dabei selbst, was es tut.
    print()
    print('74. Netzabrufe halten sich an SC_BP_NO_NET')
    _ausnahmen74 = {'bericht.py'}       # nur auf Knopfdruck, siehe oben
    _offen74 = []
    for _name74 in sorted(os.listdir(os.path.join(WURZEL, 'scbp'))):
        if not _name74.endswith('.py') or _name74 in _ausnahmen74:
            continue
        _q74 = open(os.path.join(WURZEL, 'scbp', _name74),
                    encoding='utf-8').read()
        if 'urlopen(' not in _q74:
            continue
        if 'AUS' not in _q74 and 'SC_BP_NO_NET' not in _q74:
            _offen74.append(_name74)
    pruefe(not _offen74,
           'jedes Modul mit Netzabruf kennt den Schalter (%s)'
           % (', '.join(_offen74) or 'alle'))

    print()
    if fehler:
        print('%d von %d Prüfungen fehlgeschlagen:' % (len(fehler), geprueft[0]))
        for f in fehler:
            print('  ·', f)
        return 1
    print('Alle Prüfungen bestanden.')
    return 0


def _versionierte_dateien(wurzel, endungen=('.py', '.md', '.yml')):
    """Die Dateien, die wirklich veroeffentlicht werden — laut Git.

    ⚠ **Nicht `os.walk`.** Der Maßstab ist nicht, was auf der Platte liegt,
    sondern was im Repo landet: Eine Anleitung, die per `.gitignore`
    ausgeschlossen ist, darf privates Beiwerk enthalten — sie geht niemanden
    an, weil sie nirgends hinkommt. Am 30.08.2026 meldete die Pruefung genau
    so eine Datei, waehrend der Bau-Laeufer sie gar nicht kannte: lokal rot,
    im Bau gruen. Zwei verschiedene Wahrheiten ueber dieselbe Frage.

    Ohne Git (entpacktes Archiv) faellt die Pruefung auf das Dateisystem
    zurueck — dann lieber zu viel pruefen als zu wenig.
    """
    import subprocess
    try:
        roh = subprocess.run(['git', '-C', wurzel, 'ls-files'],
                             capture_output=True, text=True, timeout=30)
        if roh.returncode == 0 and roh.stdout.strip():
            return [z for z in roh.stdout.splitlines() if z.endswith(endungen)]
    except Exception:
        pass
    raus = []
    for ordner, _o, namen in os.walk(wurzel):
        if any(x in ordner for x in ('.git', 'assets', 'build', 'dist')):
            continue
        for n in namen:
            if n.endswith(endungen):
                raus.append(os.path.relpath(os.path.join(ordner, n), wurzel))
    return raus


def _wurzel():
    """Ein unsichtbares Fenster, nur um die Bildschirmgröße erfragen zu können."""
    import tkinter as tk
    r = tk.Tk()
    r.withdraw()
    return r


if __name__ == '__main__':
    sys.exit(main())
