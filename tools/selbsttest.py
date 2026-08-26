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
import os
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
        # verschwinden — sonst ist nach drei Fassungen alles markiert.
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
               'was es in der eigenen Fassung noch nicht gibt, wird nicht markiert')

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
                pruefe(len(hf.knoepfe) == 9, 'alle Reiter sind wieder da')

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
        # war jedes Mal schwer zu sehen, weil er nur in der verpackten Fassung
        # unter Windows auftritt — hier wird deshalb die Entscheidung geprüft,
        # nicht das Ergebnis.
        print()
        print('16. Neustart nach dem Update')
        from scbp import aktualisierung as akt

        gestartet = []

        class _FalschesPopen(object):
            def __init__(self, *a, **k):
                gestartet.append(a[0] if a else None)

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
            # und der Nutzer sieht die alte Fassung weiterlaufen.
            akt._TAUSCH_LAEUFT[0] = True
            akt.neu_starten()
            pruefe(gestartet == [],
                   'wartet ein Dateitausch, wird nichts selbst gestartet')

            # Ohne wartenden Tausch (AppImage: schon getauscht) muss gestartet
            # werden — sonst bliebe das Programm nach dem Update einfach zu.
            akt._TAUSCH_LAEUFT[0] = False
            akt.neu_starten()
            pruefe(len(gestartet) == 1,
                   'ohne wartenden Tausch startet die neue Fassung')
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
        quelle = open(os.path.join(WURZEL, 'scbp', 'seiten.py'),
                      encoding='utf-8').read()
        vor_abtreten = quelle.split('def _abtreten')[0]
        pruefe('threading.Timer(2.0, lambda: os._exit(0)).start()' in vor_abtreten,
               'der Notausgang steht vor dem Tk-Rückruf, nicht darin')

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
