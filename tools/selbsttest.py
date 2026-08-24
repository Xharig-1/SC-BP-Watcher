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
import os
import shutil
import sys
import tempfile
import time

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WURZEL)

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
    'arclight pistol battery (30 cap)',
    'cf-117 bulldog "hazard-zone" repeater',
    'singe cannon (s2)',
    'scalpel sniper rifle magazine (12 schuss)',
}

fehler = []


def pruefe(bedingung, was):
    print(('  [ok]   ' if bedingung else '  [FEHL] ') + was)
    if not bedingung:
        fehler.append(was)


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
    basis = tempfile.mkdtemp(prefix='sc-bp-selbsttest-')
    live = baue(basis)
    os.environ['SC_INSTALL_DIR'] = live
    os.environ['SC_BP_HOME'] = os.path.join(basis, 'eigene')
    os.environ['SC_BP_NO_NET'] = '1'
    os.environ.pop('SC_BP_LAUNCHER', None)
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
        pruefe(pf.spiel_ordner() is None, 'ohne Eintrag wird nichts gefunden')
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

        print('\n6. Erster Start nimmt dem Spieler die Arbeit ab')
        from scbp import assistent as assi, pfade as pf2
        # Frischer Ordner, damit "erster Start" wirklich zutrifft
        frisch = os.path.join(basis, 'frisch')
        os.makedirs(frisch)
        os.environ['SC_BP_HOME'] = frisch
        os.environ.pop('SC_INSTALL_DIR', None)
        pruefe(assi.noetig(), 'Assistent meldet sich beim ersten Start')
        pruefe(pf2.spiel_ordner() is None, 'ohne Angabe wird nichts gefunden')
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

        print('\n8. Fensterlage von einem fremden Rechner')
        kaputt = w.geometrie_pruefen('440x1098+999999+-999999', _wurzel())
        pruefe('+999999' not in kaputt, 'unsinnige Position verworfen (%s)' % kaputt)

    finally:
        shutil.rmtree(basis, ignore_errors=True)

    print()
    if fehler:
        print('%d von %d Prüfungen fehlgeschlagen:' % (len(fehler), len(fehler) + 0))
        for f in fehler:
            print('  ·', f)
        return 1
    print('Alle Prüfungen bestanden.')
    return 0


def _wurzel():
    """Ein unsichtbares Fenster, nur um die Bildschirmgröße erfragen zu können."""
    import tkinter as tk
    r = tk.Tk()
    r.withdraw()
    return r


if __name__ == '__main__':
    sys.exit(main())
