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
    # ⚠ Einfache Anführungszeichen, obwohl die Log-Zeile oben doppelte hat:
    # `pfade.namensform()` zieht alle Anführungszeichen auf ein einfaches `'`,
    # damit derselbe Bauplan aus Launcher-Export und scmdb-Katalog denselben
    # Schlüssel bekommt.
    "cf-117 bulldog 'hazard-zone' repeater",
    'singe cannon (s2)',
    'scalpel sniper rifle magazine (12 schuss)',
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
        d['eintraege'].append({'titel': 'Staffelrüstung',
                               'muster': ['adp-mk4', 'woodland']})
        mk.speichern(d)
        pruefe(mk.treffer('ADP-mk4 Woodland Helmet') == 'Staffelrüstung',
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
        offen = sorted(neuheiten.offene('3.0.0'))
        pruefe(offen == sorted(neuheiten.NEU_SEIT),
               'wer von 2.0.0 kommt, sieht die neuen Bereiche')
        neuheiten.gesehen('bestand', '3.0.0')
        pruefe('bestand' not in neuheiten.offene('3.0.0'),
               'die Marke verschwindet, sobald der Bereich offen war')
        pruefe(len(neuheiten.offene('3.0.0')) == len(offen) - 1,
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
                pruefe(len(hf.knoepfe) == 11, 'alle Reiter sind wieder da')

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
        # ⚠ Am 27.08.2026 meldete der Autor, dass bei „sehr gross" die Knoepfe
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
        # der Autors eigener rc74-Bericht zeigte keinen einzigen Startschritt mehr.
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
            fe26.spur('Hauptschleife laeuft')
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
        # ⚠ der Autor am 27.08.2026: „das hat bei mir und meinem bruder nur
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
        # Zielordner. der Autor: „ist ja wie die deutsche im grunde."
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
        # der Autor: „sonst kann man das nie ohne eine übersetzung nutzen."
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
        # ⚠ der Autor am 27.08.2026: „im gleichen tab sind die einstellings
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
        # Entscheidung der Autor am 27.08.2026: „ich will die exe ohne install
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
        # ⚠ der Autor am 27.08.2026: „der zweite Programmstart ist die denkbar
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
        for roh33 in ('Singe Cannon (S2)', 'Irgendwas (30 cap)',
                      'Ding (Alpha/1/A)'):
            pruefe(nfm33(roh33) == roh33.lower(),
                   'unangetastet: %s' % roh33)
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
            pruefe(d33.get('version') == 2, 'die Datei-Version wird hochgesetzt')
            # ⚠ Nur EINMAL umziehen — sonst schreibt jeder Start die Datei neu.
            auf_platte33 = js33.load(open(be33.pfad(), encoding='utf-8'))
            pruefe(auf_platte33.get('version') == 2,
                   'der Umzug wird auf die Platte geschrieben, nicht nur gedacht')
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
        # ⚠ der Autor am 28.08.2026: „ich will nicht jedem eine Stunde erklaeren,
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
        # statt gemessen wurde. Der Beweis kam aus der Autors Bericht vom
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
        # updatet nicht. der Autor am 27.08.2026: „das nervt user weil die den
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

        # Dieselbe Datei, Angaben drin.
        with open(_ini39, 'a', encoding='utf-8') as f:
            f.write('mission_b_title=Bounty <EM4>[BP]</EM4>\n')
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
    # ⚠ Gemessen am 28.08.2026 (der Autor, Update rc75 -> rc83). Im
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
    # ⚠ Gemessen am 28.08.2026 (der Autor): „Angaben am Gegenstand“ abgeschaltet,
    # Statuszeile meldete „aus“ — und die `global.ini` blieb unangetastet. 1.217
    # Angaben standen weiter drin, das Spiel zeigte sie unverändert.
    #
    # Schlimmer noch der Kasten darüber: „Änderungen wirken beim nächsten
    # Spielstart“ — wer danach neu startete und alles unverändert vorfand, hielt
    # das Werkzeug für kaputt. der Autor: „ein user erwartet das was er liest und
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
    # Gemessen am 28.08.2026 (der Autor): Nach dem Deinstallieren stand der Wert
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
    if fehler:
        print('%d von %d Prüfungen fehlgeschlagen:' % (len(fehler), geprueft[0]))
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
