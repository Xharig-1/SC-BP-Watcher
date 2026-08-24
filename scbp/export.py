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
Den eigenen Bauplan-Bestand als Datei ausgeben.

Zwei Formate, zwei Zwecke:

**1. Für das KRT Profit Basetool** (`profit-base.online`) — dessen Import nimmt
eine JSON entgegen und gleicht sie in einer Vorschau gegen seinen Katalog ab:

    {"blueprints": [{"productName": "Manticore Helmet",
                     "receivedAt": "2026-08-02T01:49:03.322Z"}]}

`productName` ist Pflicht, `receivedAt` optional (ISO 8601). Ein kaputter
Zeitwert lässt den Import **nicht** scheitern — deshalb wird er weggelassen,
wenn er nicht sauber zu bilden ist, statt etwas Erfundenes zu schreiben.

**2. Als vollständige Sicherung** — alles, was hier bekannt ist: Name, Art,
Klasse, Größe, Gütegrad, Hersteller, Quelle und Zeitpunkt. Für eigene
Auswertungen und als Rückfall, unabhängig von jedem fremden Dienst.

> **Hochgeladen wird nichts.** Der Export schreibt eine Datei, den Rest macht
> der Spieler. Alles andere hieße fremde Zugangsdaten verwalten und ungefragt
> Daten verschicken — das gehört nicht in ein Overlay.
"""
import json
import os
import time

from . import bestand as bestand_datei
from . import katalog as katalog_modul


def _iso(zeit_text):
    """„2026-08-24 07:57:59" -> „2026-08-24T07:57:59Z" oder None.

    Der Bestand hält die Zeit in lesbarer Form; das Basetool erwartet ISO 8601.
    Lässt sich der Wert nicht deuten, wird das Feld **weggelassen** — laut
    Format ist es optional, und ein erfundener Zeitpunkt wäre schlechter als
    gar keiner."""
    if not zeit_text:
        return None
    try:
        t = time.strptime(str(zeit_text), '%Y-%m-%d %H:%M:%S')
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', t)
    except (ValueError, TypeError):
        return None


def fuer_basetool(bestand=None):
    """Die Struktur, die `profit-base.online` beim Import erwartet."""
    daten = bestand if bestand is not None else bestand_datei.laden()
    eintraege = []
    for schluessel, e in sorted((daten.get('bauplaene') or {}).items()):
        name = (e.get('name') or '').strip()
        if not name:
            continue                     # leere Namen fliegen beim Import raus
        satz = {'productName': name}
        zeit = _iso(e.get('zeit'))
        if zeit:
            satz['receivedAt'] = zeit
        eintraege.append(satz)
    return {'blueprints': eintraege}


def vollstaendig(bestand=None, katalog=None):
    """Alles, was das Werkzeug über den eigenen Bestand weiß."""
    daten = bestand if bestand is not None else bestand_datei.laden()
    kat = (katalog if katalog is not None else katalog_modul.laden())
    kb = kat.get('bauplaene') or {}
    eintraege = []
    for schluessel, e in sorted((daten.get('bauplaene') or {}).items()):
        k = kb.get(schluessel) or {}
        satz = {
            'name': e.get('name'),
            'quelle': e.get('quelle'),
            'zeit': e.get('zeit'),
            'art': katalog_modul.art_lesbar(k.get('a')) if k.get('a') else None,
            'klasse': k.get('c'),
            'size': k.get('s'),
            'grade': k.get('g'),
            'hersteller': k.get('m'),
        }
        eintraege.append({kk: v for kk, v in satz.items() if v not in (None, '')})
    return {
        'werkzeug': 'SC BP Watcher',
        'erstellt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'spielversion': kat.get('version') or None,
        'anzahl': len(eintraege),
        'bauplaene': eintraege,
    }


def schreiben(pfad, art='basetool', bestand=None, katalog=None):
    """Eine der beiden Fassungen in eine Datei schreiben. (Erfolg, Meldung)."""
    try:
        doc = (fuer_basetool(bestand) if art == 'basetool'
               else vollstaendig(bestand, katalog))
        anzahl = len(doc.get('blueprints') or doc.get('bauplaene') or [])
        if not anzahl:
            return False, 'leerer Bestand'
        ordner = os.path.dirname(os.path.abspath(pfad))
        if ordner:
            os.makedirs(ordner, exist_ok=True)
        with open(pfad + '.tmp', 'w', encoding='utf-8', newline='\n') as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        os.replace(pfad + '.tmp', pfad)
        return True, str(anzahl)
    except OSError as fehler:
        return False, str(fehler)


def vorschlag(art='basetool'):
    """Ein sinnvoller Dateiname für den Speichern-Dialog."""
    heute = time.strftime('%Y-%m-%d')
    return ('SC-Blueprints-%s.json' % heute if art == 'basetool'
            else 'SC-BP-Watcher-Bestand-%s.json' % heute)
