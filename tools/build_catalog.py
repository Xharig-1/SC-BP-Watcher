# -*- coding: utf-8 -*-
#
# SC BP Watcher — Katalog aus den Spieldaten bauen.
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
Baut aus der `global.ini` von Star Citizen eine kompakte Katalogdatei mit
Art, Größe, Gütegrad, Klasse und Hersteller je Gegenstand.

Warum: Damit der Watcher diese Werte kennt, ohne den SC Deutsch Launcher und ohne
scmdb.net. Die Daten stammen dann direkt von CIG — ein nicht-kommerzielles
Fan-Projekt darf sie mitliefern.

Läuft NICHT beim Nutzer, sondern hier: einmal je SC-Patch. Ergebnis ist eine
kleine JSON, die ins Repo geschoben wird; die Nutzer laden nur diese Datei.

QUELLEN — in dieser Reihenfolge:

  1. `--ini <Pfad>`  auf eine **englische** `global.ini`, die du selbst aus
     `Data.p4k` extrahiert hast (Werkzeug: unp4k, https://github.com/dolkensp/unp4k).
     Das ist der saubere Weg: reine CIG-Daten, weitergabefähig.

  2. Ohne `--ini`: die im Spielordner liegende Sprachdatei. ACHTUNG — wer den
     SC Deutsch Launcher nutzt, hat dort eine **bearbeitete** Fassung: Der Launcher
     hängt Kürzel an die Namen ("SparkFire (Cmp/2/C)") und die deutschen
     Übersetzungen sind seine Arbeit. Zum Selbernutzen in Ordnung, aber das
     Ergebnis darf dann NICHT weitergegeben werden. Das Skript schreibt in dem
     Fall `"weitergabe": false` in die Datei und sagt es deutlich an.

Aufruf:
    python tools/build_catalog.py                     # aus dem Spielordner
    python tools/build_catalog.py --ini global.ini    # aus eigener Extraktion
    python tools/build_catalog.py --out daten/katalog.json
"""
import argparse
import io
import json
import os
import re
import sys
import time

# Standardorte der Sprachdatei. Über SC_INSTALL_DIR lässt sich ein abweichender
# Installationsort angeben — im Repo stehen bewusst keine festen Laufwerkspfade.
SC_DIRS = [
    os.environ.get('SC_INSTALL_DIR', ''),
    r'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE',
    r'C:\Program Files (x86)\Roberts Space Industries\StarCitizen\LIVE',
]
LOC_REL = os.path.join('data', 'Localization')

# Aus `item_Desc…` — die Datei nennt die Werte im Klartext. Die beiden Fassungen
# beschriften sie unterschiedlich:
#
#   CIG, englisch:   Item Type: Quantum Drive\nManufacturer: RAMP Corporation
#                    \nSize: 1\nGrade: B\nClass: Stealth
#   Deutsch-Launcher: Hersteller: RAMP Corporation\nTyp (En): Quantum Drive
#                    \nTyp (De): Quantenantrieb\n\nGröße: S1\nGütegrad: B\nKlasse: Stealth (Tarnung)
#
# Deshalb je Feld mehrere Muster, der erste Treffer gewinnt. Bei der Art wird
# bewusst zuerst auf die englische CIG-Schreibweise geprüft.
FELDER = {
    'a': (r'Item Type:\s*([^\\\n]+)',   r'Typ \(En\):\s*([^\\\n]+)', r'Type \(En\):\s*([^\\\n]+)'),
    's': (r'Size:\s*S?(\d+)',           r'Größe:\s*S?(\d+)'),
    'g': (r'Grade:\s*([A-D])',          r'Gütegrad:\s*([A-D])'),
    'c': (r'Class:\s*([A-Za-z]+)',      r'Klasse:\s*([A-Za-z]+)'),
    'm': (r'Manufacturer:\s*([^\\\n]+)', r'Hersteller:\s*([^\\\n]+)'),
}
FELDER = {k: [re.compile(p) for p in v] for k, v in FELDER.items()}

# Der Deutsch-Launcher hängt "(Klasse/Size/Grade)" an die Namen. Für den Katalog
# muss das weg, sonst findet später kein Name-Abgleich mehr statt.
SUFFIX = re.compile(r'\s*\([^)]*\)\s*$')


def norm(s):
    """Vergleichsschlüssel: nur Buchstaben und Ziffern. Fängt typografische
    Anführungszeichen und geschützte Leerzeichen gleich mit ab."""
    return re.sub(r'[^a-z0-9]', '', ' '.join(str(s or '').split()).lower())


def finde_ini():
    """Sucht die Sprachdatei im Spielordner. Bevorzugt Englisch (unbearbeitet),
    nimmt sonst, was da ist. Gibt (Pfad, ist_englisch) zurück."""
    for basis in SC_DIRS:
        if not basis:
            continue
        loc = os.path.join(basis, LOC_REL)
        if not os.path.isdir(loc):
            continue
        sprachen = sorted(os.listdir(loc))
        for bevorzugt in ('english', 'english_(us)'):
            if bevorzugt in sprachen:
                p = os.path.join(loc, bevorzugt, 'global.ini')
                if os.path.exists(p):
                    return p, True
        for s in sprachen:
            p = os.path.join(loc, s, 'global.ini')
            if os.path.exists(p):
                return p, False
    return None, False


def lies_ini(pfad):
    """global.ini -> (namen, beschreibungen), jeweils Item-ID -> Wert."""
    namen, descs = {}, {}
    with io.open(pfad, encoding='utf-8', errors='replace') as f:
        for zeile in f:
            if '=' not in zeile:
                continue
            k, v = zeile.split('=', 1)
            if k.startswith('item_Name'):
                namen[k[len('item_Name'):].lstrip('_')] = SUFFIX.sub('', v.strip())
            elif k.startswith('item_Desc'):
                descs[k[len('item_Desc'):].lstrip('_')] = v.rstrip('\n')
    return namen, descs


def baue(namen, descs):
    """Kompakter Katalog: Normschlüssel -> {n,a,s,g,c,m}. Feldnamen absichtlich
    identisch zum scmdb-Zwischenspeicher des Watchers, damit beide Quellen ohne
    Umbau austauschbar sind."""
    katalog = {}
    for ident, text in descs.items():
        name = namen.get(ident)
        if not name:
            continue
        eintrag = {}
        for feld, muster in FELDER.items():
            for rx in muster:
                m = rx.search(text)
                if m:
                    eintrag[feld] = m.group(1).strip()
                    break
        if not eintrag.get('a'):
            continue                      # ohne Art ist der Eintrag wertlos
        eintrag['n'] = name
        if 's' in eintrag:
            eintrag['s'] = int(eintrag['s'])
        katalog.setdefault(norm(name), eintrag)
    return katalog


def spielversion(basis):
    """Spielversion aus der `build_manifest.id`. Die Felder liegen dort unter
    `Data`; aus Branch (`sc-alpha-4.9.0`) und `RequestedP4ChangeNum` wird dieselbe
    Schreibweise gebaut, die auch scmdb benutzt: `4.9.0-live.12344265`."""
    for datei in ('build_manifest.id', 'f_win_game_manifest.id'):
        p = os.path.join(basis, datei)
        if not os.path.exists(p):
            continue
        try:
            d = json.load(io.open(p, encoding='utf-8', errors='replace'))
        except Exception:
            continue
        d = d.get('Data', d) if isinstance(d, dict) else {}
        zweig = str(d.get('Branch', ''))
        nummer = str(d.get('RequestedP4ChangeNum', ''))
        kurz = re.sub(r'^sc-\w+-', '', zweig)          # sc-alpha-4.9.0 -> 4.9.0
        tag = 'ptu' if 'ptu' in zweig.lower() else 'live'
        if kurz and nummer:
            return '%s-%s.%s' % (kurz, tag, nummer)
        return nummer or kurz or str(d.get('Version', ''))
    return ''


def main():
    ap = argparse.ArgumentParser(description='Baut den Bauplan-Katalog aus der global.ini.')
    ap.add_argument('--ini', help='Pfad zu einer global.ini (bevorzugt die englische '
                                  'Originalfassung aus dem Data.p4k)')
    ap.add_argument('--out', default=os.path.join('daten', 'katalog.json'),
                    help='Zieldatei (Standard: daten/katalog.json)')
    args = ap.parse_args()

    if args.ini:
        pfad, englisch = args.ini, True     # eigene Extraktion: als sauber behandeln
        if not os.path.exists(pfad):
            print('FEHLER: %s gibt es nicht.' % pfad)
            return 2
        # Die Datei liegt dann irgendwo, die Spielversion steht aber im
        # Installationsordner — den trotzdem suchen, sonst bliebe das Feld leer
        # und der Watcher könnte seinen Katalogstand nicht vergleichen.
        basis = next((b for b in SC_DIRS
                      if b and os.path.exists(os.path.join(b, 'build_manifest.id'))), '')
    else:
        pfad, englisch = finde_ini()
        # global.ini -> <sprache> -> Localization -> data -> LIVE : vier Ebenen hoch
        basis = pfad
        for _ in range(4):
            basis = os.path.dirname(basis) if basis else ''
        if not pfad:
            print('FEHLER: Keine global.ini gefunden.')
            print('        Spielordner über SC_INSTALL_DIR angeben oder --ini nutzen.')
            return 2

    print('Quelle: %s' % pfad)
    namen, descs = lies_ini(pfad)
    print('  item_Name: %d | item_Desc: %d' % (len(namen), len(descs)))

    katalog = baue(namen, descs)
    voll = sum(1 for e in katalog.values() if e.get('s') is not None and e.get('g'))
    print('  Katalog-Einträge: %d (davon %d mit Größe UND Gütegrad)' % (len(katalog), voll))

    # Wurde aus einer bearbeiteten Sprachdatei gebaut? Dann Sperrvermerk setzen.
    weitergabe = bool(englisch)
    if not weitergabe:
        print()
        print('!! ACHTUNG: gebaut aus einer NICHT-englischen Sprachdatei.')
        print('!! Wer den SC Deutsch Launcher nutzt, hat dort eine bearbeitete Fassung')
        print('!! (angehängte Kürzel, deutsche Übersetzungen = Arbeit des Launcher-Teams).')
        print('!! Diese Datei ist zum Selbernutzen gedacht und darf NICHT weitergegeben')
        print('!! werden. Für eine weitergabefähige Fassung die englische global.ini aus')
        print('!! Data.p4k extrahieren (unp4k) und mit --ini übergeben.')

    ziel = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    with io.open(ziel, 'w', encoding='utf-8') as f:
        json.dump({
            'quelle': 'global.ini (englisch)' if englisch else 'global.ini (bearbeitet)',
            'weitergabe': weitergabe,
            'spielversion': spielversion(basis) if basis else '',
            'gebaut': time.strftime('%Y-%m-%d %H:%M'),
            'items': katalog,
        }, f, ensure_ascii=False, separators=(',', ':'))
    print()
    print('Geschrieben: %s (%.0f KB)' % (ziel, os.path.getsize(ziel) / 1024.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
