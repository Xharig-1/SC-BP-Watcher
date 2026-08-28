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
Die Game.log lesen — laufend und rückwirkend.

Zwei Aufgaben:

  **Mitlesen.** Wie bisher: ab dem Startzeitpunkt die laufende Game.log
  verfolgen und neue Baupläne sofort melden.

  **Nachlesen.** Beim Start werden die aufgehobenen Logs
  vergangener Sitzungen (`logbackups/`) durchgesehen. Wer ohne laufenden
  Watcher gespielt hat, verliert dadurch nichts mehr. Was schon gelesen wurde,
  merkt sich der Lesestand — beim nächsten Start wird nicht alles erneut
  durchgekaut.

**Und die ehrliche Lücke:** Star Citizen hebt nur eine begrenzte Zahl alter Logs
auf. Liegt die letzte gelesene Sitzung weiter zurück als die älteste noch
vorhandene Sicherung, fehlt dazwischen etwas — das lässt sich nicht
zurückholen, aber sagen. Genau dafür ist `bericht['luecke']` da: Der Nutzer
soll die fehlenden Baupläne im Verwaltungsfenster von Hand abhaken können,
statt sich auf eine stille Untergrenze zu verlassen.
"""
import json
import os
import re
import time

from . import pfade, phrasen
from .sprache import t, Satz, Zeitpunkt

# Schiffskomponenten stehen im Log MIT Zusatz „(Klasse/Size/Grade)", z. B.
# „7CA 'Nargun' (Civ/3/A)" — der Launcher-Schlüssel ist aber „7CA 'Nargun'".
# Bewusst eng gefasst (nur die bekannten Kürzel), damit echte Namens-Klammern
# wie „(30 cap)" oder „Singe Cannon (S2)" unangetastet bleiben.
#
# ⚠ **Die Liste muss zu `scbp/angaben.py` passen.** Seit v3.0.0 schreibt das
# Werkzeug diese Zusätze selbst an die Gegenstandsnamen (Angaben am
# Traktorstrahl) — und das Spiel schreibt den Namen anschließend **mitsamt
# Zusatz** in die Game.log. Wird hier einer nicht erkannt, landet der Bauplan
# unter falschem Namen im Bestand und wird **nie abgehakt**.
#
# Dazu kommen zwei Formen, die es beim Launcher nicht gab:
#   * **Striche** für Unbekanntes — `Glacis (Ind/4/–)`, `V60-26 (Mil/–/B)`
#   * **Waffen ohne Größe** — `P4-AR "Warhawk" Rifle (Bal)`; FPS-Waffen haben
#     in Star Citizen weder Größe noch Gütegrad
#   * **Raketen** — `'Arrow' I Missile (IR1)`, Suchkopf statt Fraktion
_KUERZEL = ('Civ|Mil|Ind|Sth|Cmp'          # Fraktion, auch CIGs eigene Schreibweise
            '|Las|Ele|Pla|Dis|Mic|Bal'     # Waffenwirkung
            '|Nah|Min|Slv|Med|Tool|Trc')   # Nahkampf, Bergbau, Bergung, Medizin
_STRICH = '\u2013|-'                        # Gedankenstrich oder Bindestrich
SUFFIX_RE = re.compile(
    r'\s*\((?:(%s)/(\d+|%s)/([A-D]|%s)'      # (Mil/1/A), auch mit Strichen
    r'|(%s)'                                 # (Bal) — Waffe ohne Größe/Grad
    r'|(IR|EM|CS)(\d{1,2}))\)\s*$'           # (IR1) — Rakete
    % (_KUERZEL, _STRICH, _STRICH, _KUERZEL), re.I)

# Wie viel einer Sicherung am Stück gelesen wird. Die Dateien werden mehrere
# hundert Megabyte groß; sie komplett in den Speicher zu holen wäre unnötig.
BLOCK = 4 * 1024 * 1024


def teile_namen(roh):
    """('7CA \\'Nargun\\'', ('Civ', '3', 'A'))  aus  "7CA 'Nargun' (Civ/3/A)".

    Zweiter Wert ist None, wenn kein Zusatz dranhing (FPS-Waffen, Rüstung)."""
    m = SUFFIX_RE.search(roh)
    if not m:
        return roh.strip(), None
    name = roh[:m.start()].strip()
    if m.group(1):                       # (Mil/1/A) — die vollständige Form
        return name, (m.group(1).title(), m.group(2), m.group(3).upper())
    if m.group(4):                       # (Bal) — nur die Klasse
        return name, (m.group(4).title(), None, None)
    return name, (m.group(5).upper(), m.group(6), None)   # (IR1) — Rakete


def _namen_aus_text(text, muster):
    return [teile_namen(m.group(1)) for m in muster.finditer(text)]


# ------------------------------------------------------------------ Lesestand
class Lesestand:
    """Merkt sich, was schon gelesen wurde — über Programmneustarts hinweg."""

    def __init__(self):
        self.pfad = pfade.app_datei('logstand.json')
        self.daten = self._laden()

    def _laden(self):
        try:
            with open(self.pfad, encoding='utf-8') as f:
                d = json.load(f)
            d.setdefault('aktiv', {})
            d.setdefault('sicherungen', {})
            d.setdefault('letzte_sitzung', 0.0)
            return d
        except Exception:
            return {'aktiv': {}, 'sicherungen': {}, 'letzte_sitzung': 0.0}

    def speichern(self):
        try:
            os.makedirs(os.path.dirname(self.pfad), exist_ok=True)
            temp = self.pfad + '.tmp'
            with open(temp, 'w', encoding='utf-8') as f:
                json.dump(self.daten, f, ensure_ascii=False, indent=1)
            os.replace(temp, self.pfad)
        except Exception:
            pass

    # --- Sicherungen ---
    def kennt(self, datei):
        """Wurde diese Sicherung schon gelesen? Erkannt an Name, Größe und Zeit —
        wächst eine Datei doch noch, gilt sie wieder als ungelesen."""
        e = self.daten['sicherungen'].get(os.path.basename(datei))
        if not e:
            return False
        try:
            return (e.get('groesse') == os.path.getsize(datei)
                    and abs(e.get('mtime', 0) - os.path.getmtime(datei)) < 1)
        except OSError:
            return False

    def merke(self, datei):
        try:
            self.daten['sicherungen'][os.path.basename(datei)] = {
                'groesse': os.path.getsize(datei),
                'mtime': os.path.getmtime(datei),
            }
            self.daten['letzte_sitzung'] = max(
                self.daten.get('letzte_sitzung', 0.0), os.path.getmtime(datei))
        except OSError:
            pass

    def aufraeumen(self, vorhandene):
        """Einträge zu Sicherungen wegwerfen, die es nicht mehr gibt — sonst
        wächst die Datei mit jeder Spielsitzung weiter."""
        da = {os.path.basename(p) for p in vorhandene}
        self.daten['sicherungen'] = {k: v for k, v
                                     in self.daten['sicherungen'].items() if k in da}

    # --- laufende Log ---
    def aktiv_holen(self, pfad):
        e = self.daten['aktiv']
        return e.get('offset', 0) if e.get('pfad') == pfad else None

    def aktiv_setzen(self, pfad, offset):
        self.daten['aktiv'] = {'pfad': pfad, 'offset': offset, 'zeit': time.time()}
        self.daten['letzte_sitzung'] = max(self.daten.get('letzte_sitzung', 0.0),
                                           time.time())


# ------------------------------------------------------------------- Nachlese
def nachlesen(stand=None, muster=None, nur_neue=True, auch_laufende=True):
    """Die aufgehobenen Logs durchsehen.

    Rückgabe: (namen, bericht). `namen` ist eine Liste von (Name, Zusatz) —
    dieselbe Form, die auch das Mitlesen liefert, damit beide Wege im
    Hauptprogramm gleich behandelt werden können.

    `bericht` sagt, was passiert ist: wie viele Dateien gelesen wurden, ob eine
    Lücke bleibt und warum."""
    stand = stand or Lesestand()
    muster = muster or phrasen.muster()
    alle = pfade.log_sicherungen()
    # Vergleichswert VOR dem Lauf festhalten — `stand.merke()` schreibt ihn
    # gleich fort, danach ließe sich keine Lücke mehr erkennen.
    vorher = stand.daten.get('letzte_sitzung', 0.0)
    bericht = {'dateien': 0, 'uebersprungen': 0, 'gefunden': 0,
               'vorhanden': len(alle), 'luecke': False, 'grund': '',
               'laufende': False}

    treffer, gesehen = [], set()
    for datei in alle:
        if nur_neue and stand.kennt(datei):
            bericht['uebersprungen'] += 1
            continue
        for name, zusatz in _lies_datei(datei, muster):
            schluessel = name.lower().strip()
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            treffer.append((name, zusatz))
        stand.merke(datei)
        bericht['dateien'] += 1

    # Die laufende Game.log gehört mit dazu, wenn sie noch nie gelesen wurde:
    # Wer den Watcher startet, während Star Citizen schon läuft, hätte sonst
    # ausgerechnet die aktuelle Sitzung als Loch im Bestand. Danach steht der
    # Lesestand auf dem Dateiende, das Mitlesen setzt dort nahtlos an.
    if auch_laufende:
        aktiv = pfade.game_log()
        if aktiv and stand.aktiv_holen(aktiv) is None:
            for name, zusatz in _lies_datei(aktiv, muster):
                schluessel = name.lower().strip()
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                treffer.append((name, zusatz))
            try:
                stand.aktiv_setzen(aktiv, os.path.getsize(aktiv))
            except OSError:
                pass
            bericht['laufende'] = True

    bericht['gefunden'] = len(treffer)
    bericht.update(_luecke_pruefen(vorher, alle))
    stand.aufraeumen(alle)
    stand.speichern()
    return treffer, bericht


def _lies_datei(datei, muster):
    """Eine ganze Logdatei blockweise durchsuchen."""
    gefunden = []
    try:
        with open(datei, 'rb') as f:
            rest = b''
            while True:
                block = f.read(BLOCK)
                if not block:
                    break
                block = rest + block
                schnitt = block.rfind(b'\n')
                if schnitt < 0:            # eine sehr lange Zeile — weitersammeln
                    rest = block
                    continue
                rest = block[schnitt + 1:]
                text = block[:schnitt].decode('utf-8', 'ignore')
                gefunden.extend(_namen_aus_text(text, muster))
            if rest:
                gefunden.extend(_namen_aus_text(rest.decode('utf-8', 'ignore'),
                                                muster))
    except OSError:
        pass
    return gefunden


def _luecke_pruefen(vorher, alle):
    """Bleibt trotz Nachlese etwas unbekannt?

    Zwei Fälle sagen Ja:
      * **Erster Start überhaupt** — was vor der ältesten aufgehobenen Sicherung
        liegt, hat nie jemand gelesen. Das ist der Normalfall bei der ersten
        Benutzung und der Grund, warum es die Liste zum Abhaken gibt.
      * **Zu lange nicht gelaufen** — die älteste vorhandene Sicherung ist neuer
        als die zuletzt gelesene Sitzung. Dazwischen hat Star Citizen Logs
        weggeräumt, die niemand mehr hat."""
    # ⚠ Zurück kommt ein `Satz`, **kein fertiger Text**: Diese Meldung landet in
    # der Melde-Leiste und bleibt dort stehen. Ein fertig zusammengesetzter Satz
    # wäre in der Sprache von damals eingefroren — wer später umstellt, hätte
    # eine deutsche Zeile in einem englischen Fenster. Genau so gefunden am
    # 26.08.2026. Der `Satz` merkt sich Schlüssel und Werte und lässt sich beim
    # Sprachwechsel neu auswerten.
    if not alle:
        return {'luecke': True, 'grund': Satz('m_keine_logs')}
    aeltester = min((os.path.getmtime(p) for p in alle
                     if os.path.exists(p)), default=0.0)
    if not vorher:
        return {'luecke': True,
                'grund': Satz('m_erster_lauf', Zeitpunkt(aeltester))}
    if aeltester > vorher + 60:
        return {'luecke': True,
                # ⚠ Auch das Datumsformat ist sprachabhängig: Im Englischen
                # steht das Jahr vorn (`m_erster_datum`). Deshalb wandert hier
                # der rohe Zeitstempel weiter (`Zeitpunkt`) statt eines fertig
                # formatierten Datums — sonst stünde in der englischen Meldung
                # ein deutsches Datum.
                'grund': Satz('m_luecke_logs',
                              Zeitpunkt(vorher), Zeitpunkt(aeltester))}
    return {'luecke': False, 'grund': ''}


# ------------------------------------------------------------------- Mitlesen
class LogTail:
    """Liest die laufende Game.log fortlaufend weiter.

    Neu gegenüber v1.5.0: Der Lesestand überlebt einen Programmneustart. Wer den
    Watcher neu startet, während das Spiel läuft, verliert die Baupläne dieser
    Sitzung nicht mehr."""

    def __init__(self, stand=None, muster=None):
        self.stand = stand or Lesestand()
        self.muster = muster or phrasen.muster()
        self.path, self.offset = None, 0

    def _locate(self):
        p = pfade.game_log()
        if p and p != self.path:
            self.path = p
            gemerkt = self.stand.aktiv_holen(p)
            try:
                groesse = os.path.getsize(p)
            except OSError:
                groesse = 0
            # Gemerkter Stand nur, wenn er noch in die Datei passt — ist sie
            # kürzer, lief inzwischen eine neue Spielsitzung.
            self.offset = gemerkt if (gemerkt is not None
                                      and gemerkt <= groesse) else groesse
        elif not p:
            self.path = None
        return self.path

    def new_names(self):
        """Neue Baupläne seit dem letzten Aufruf — Liste von (Name, Zusatz)."""
        if not self._locate():
            return []
        try:
            size = os.path.getsize(self.path)
            if size < self.offset:          # Log rotiert -> neue Spielsitzung
                self.offset = 0
            if size == self.offset:
                return []
            with open(self.path, 'rb') as f:
                f.seek(self.offset)
                chunk = f.read()
        except OSError:
            return []
        cut = chunk.rfind(b'\n')            # angefangene letzte Zeile stehen lassen
        if cut < 0:
            return []
        self.offset += cut + 1
        self.stand.aktiv_setzen(self.path, self.offset)
        self.stand.speichern()
        return _namen_aus_text(chunk[:cut].decode('utf-8', 'ignore'), self.muster)


if __name__ == '__main__':
    funde, b = nachlesen()
    print('Sicherungen vorhanden:', b['vorhanden'],
          '· gelesen:', b['dateien'], '· übersprungen:', b['uebersprungen'])
    print('Baupläne gefunden:', b['gefunden'])
    if b['luecke']:
        print('LÜCKE:', b['grund'])
    for n, z in funde[:20]:
        print(' ·', n, z or '')
