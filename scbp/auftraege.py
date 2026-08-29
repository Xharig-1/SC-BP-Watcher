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
Angenommene Aufträge — „bringt mir der etwas, das mir fehlt?"

Der Watcher beantwortet seine eigene Frage damit **früher**: Nicht erst wenn der
Bauplan im Spiel auftaucht, sondern schon beim Annehmen des Auftrags.

    Auftrag angenommen: Retake Platforms From Nine Tails
      → 3 Baupläne · dir fehlt: H4-PBF Ammo Carrier

Es ist bewusst **keine Auftragsverwaltung**: keine Liste, kein Reiter, kein
zweites Fenster. Eine Zeile im Overlay, wie ein Bauplanfund auch.

## Der Weg durch die Daten

| Schritt | Woher |
|---|---|
| 1. Auftrag angenommen | `Game.log`, Zeile `Added notification "<Phrase>: <Titel>: "` |
| 2. Welche Phrase | `mobiGlas_ui_MissionEvent_Activated` aus der `global.ini` |
| 3. Titel → Missionsschlüssel | Rückwärtssuche in der `global.ini` |
| 4. Schlüssel → Baupläne | `missionen[<schlüssel>]['bp']` im Katalog |
| 5. Was davon fehlt | der eigene Bestand |

## ⚠ Die Fallen, alle an echten Daten gemessen (29.08.2026)

1. **Auf den SCHLÜSSEL gehen, nie auf die Formulierung.** Auf Deutsch heißen
   `mobiGlas_ui_MissionEvent_Available` **und** `mobiGlas_ui_ObjectiveEvent_Activated`
   beide „Neuer Auftrag" — das sind Zwischenziele. Wer darauf hört, meldet bei
   jedem Etappenziel. Nur `MissionEvent_Activated` ist die Annahme.
2. **Der Titel trägt unsere eigenen Marken.** Im Log steht
   `Retake Platforms From Nine Tails <EM4>[BP!]</EM4>`, in der injizierten
   `global.ini` sogar `…[SCBPW] <EM4>[BP 4/8]</EM4>[/SCBPW]`. Vor jedem
   Vergleich müssen sie weg — auf **beiden** Seiten.
3. **58 von 353 Titeln enthalten Platzhalter** (`~mission(TargetName)`), die das
   Spiel erst zur Laufzeit einsetzt. Ein wörtlicher Vergleich scheitert dort.
   Deshalb wird aus dem Titel ein Muster gebaut: `High-Risk Bounty:
   ~mission(TargetName)` wird zu einem Muster mit `.+` an der Platzhalter-Stelle,
   der Rest woertlich. Damit sind 337 der
   353 erreichbar statt 279.
4. **Ist der Auftrag unbekannt, wird geschwiegen.** Für 16 der 353 findet sich
   kein Titel, und nicht jeder angenommene Auftrag steht überhaupt im Katalog.
   Lieber nichts melden als raten — eine falsche Bauplan-Zusage ist schlimmer
   als keine.

Die Auftrags-Herkunft stammt aus dem Katalog von scmdb.net und wird **nicht
mitgeliefert** (CC BY-NC-ND). Fehlt sie, tut dieses Modul nichts und der Watcher
läuft unverändert weiter.
"""
import os
import re

from . import fehler, katalog, pfade

# Der sprachneutrale Schlüssel für „Auftrag angenommen" — in jeder Sprache derselbe.
INI_SCHLUESSEL = 'mobiGlas_ui_MissionEvent_Activated'

# Rückfall, falls die `global.ini` nicht vorliegt. Beide an echten Logs gemessen.
TABELLE = {
    'de': ['Auftrag angenommen'],
    'en': ['Contract Accepted'],
}

# Dieselbe Zeilenform wie bei den Bauplänen — sie ist zu eigen, als dass sie
# zufällig entstünde.
RAHMEN = r'Added notification "(?:%s):\s*(.+?)\s*:\s*"'

# Unsere eigenen Marken im Titel. `injektion.py` schreibt sie, hier müssen sie
# vor jedem Vergleich wieder weg.
_MARKEN = re.compile(
    r'\[SCBPW\].*?\[/SCBPW\]'                       # der ganze eingefügte Block
    r'|<EM4>\[(?:BP|Bauplan)(?:\s+\d+/\d+)?!?\]</EM4>'   # nur die Blase
)
_PLATZHALTER = re.compile(r'~mission\([^)]*\)')

_index = None            # {sauberer Titel: schluessel}
_muster_index = None     # [(kompiliertes Muster, schluessel)] für Platzhalter-Titel
_missionen = None        # Zwischenspeicher: der Katalog ist rund 1 MB gross


def missionen():
    """Die Missionen aus dem Katalog — einmal lesen, dann gemerkt.

    `katalog.laden()` liest jedes Mal die ganze Datei. Bei einem Auftrag alle
    paar Minuten faellt das nicht auf, aber es waere unnoetige Arbeit.
    """
    global _missionen
    if _missionen is None:
        try:
            _missionen = katalog.laden().get('missionen') or {}
        except Exception as ausnahme:
            fehler.merken('auftraege.katalog', ausnahme)
            _missionen = {}
    return _missionen


def vergessen():
    """Zwischenspeicher leeren — nach einem Katalog-Update aufzurufen."""
    global _missionen, _index, _muster_index
    _missionen, _index, _muster_index = None, None, None


# Die `global.ini` schreibt die Meldung mit Platzhalter: `Auftrag angenommen: %s`.
# Fuer die Suche zaehlt nur der Wortlaut davor — mit dem Platzhalter passt die
# Zeile nie, weil im Log der echte Titel steht.
_PLATZHALTER_ENDE = re.compile(r'\s*:?\s*%[sd]\s*$')


def sauber(titel):
    """Titel ohne unsere Marken und ohne doppelte Leerzeichen."""
    return ' '.join(_MARKEN.sub(' ', str(titel)).split())


def _phrase_kuerzen(wert):
    """Aus `Auftrag angenommen: %s` wird `Auftrag angenommen`."""
    return _PLATZHALTER_ENDE.sub('', sauber(wert)).strip()


def phrasen():
    """Wie „Auftrag angenommen" in der laufenden Spielsprache heißt.

    Erst aus der `global.ini` des Spiels — die ist immer richtig, auch in
    Sprachen, die wir nie gesehen haben. Sonst die mitgelieferte Tabelle.
    """
    gefunden = []
    for pfad in _ini_dateien():
        try:
            with open(pfad, encoding='utf-8', errors='ignore') as f:
                for zeile in f:
                    if zeile.startswith(INI_SCHLUESSEL + '='):
                        wert = _phrase_kuerzen(zeile.split('=', 1)[1])
                        if wert and wert not in gefunden:
                            gefunden.append(wert)
                        break
        except OSError:
            continue
    for liste in TABELLE.values():
        for p in liste:
            if p not in gefunden:
                gefunden.append(p)
    return gefunden


def _ini_dateien():
    """Alle vorhandenen `global.ini` der Installation."""
    try:
        basis = os.path.join(pfade.spiel_ordner() or '', 'data', 'Localization')
    except Exception:
        return []
    if not os.path.isdir(basis):
        return []
    gefunden = []
    try:
        for name in sorted(os.listdir(basis)):
            p = os.path.join(basis, name, 'global.ini')
            if os.path.isfile(p):
                gefunden.append(p)
    except OSError:
        pass
    return gefunden


def muster():
    """Das fertige Suchmuster für die Log-Zeile."""
    teile = '|'.join(re.escape(p) for p in phrasen())
    return re.compile(RAHMEN % teile)


def _index_bauen():
    """Titel → Missionsschlüssel, aus der `global.ini` und dem Katalog.

    Es werden nur die Schlüssel aufgenommen, die der Katalog überhaupt kennt —
    die `global.ini` hat über 9.000 Einträge, davon sind 353 für uns relevant.
    """
    global _index, _muster_index
    _index, _muster_index = {}, []
    bekannt = set(missionen())
    if not bekannt:
        return
    for pfad in _ini_dateien():
        try:
            with open(pfad, encoding='utf-8', errors='ignore') as f:
                for zeile in f:
                    trenner = zeile.find('=')
                    if trenner < 1:
                        continue
                    schluessel = zeile[:trenner]
                    if schluessel not in bekannt:
                        continue
                    titel = sauber(zeile[trenner + 1:])
                    if not titel:
                        continue
                    if '~mission(' in titel:
                        # Platzhalter -> Muster. Der Rest wird woertlich
                        # genommen, damit „High-Risk Bounty: X" nicht auf
                        # „Low-Risk Bounty: X" passt.
                        roh = '^' + '.+'.join(
                            re.escape(t) for t in _PLATZHALTER.split(titel)) + '$'
                        try:
                            _muster_index.append((re.compile(roh), schluessel))
                        except re.error:
                            pass
                    else:
                        _index.setdefault(titel.lower(), schluessel)
        except OSError:
            continue


def schluessel_zu(titel):
    """Der Missionsschlüssel zu einem angezeigten Titel, oder None."""
    if _index is None:
        _index_bauen()
    rein = sauber(titel)
    treffer = _index.get(rein.lower())
    if treffer:
        return treffer
    for mst, schluessel in _muster_index:
        if mst.match(rein):
            return schluessel
    return None


def pruefen(titel, hat_bereits):
    """Was bringt dieser Auftrag — und was davon fehlt noch?

    `hat_bereits` ist eine Funktion `name -> bool`. Rückgabe ist `None`, wenn
    der Auftrag unbekannt ist oder keine Baupläne bringt; sonst
    `(gesamtzahl, [fehlende Namen])`.
    """
    schluessel = schluessel_zu(titel)
    if not schluessel:
        return None
    eintrag = missionen().get(schluessel) or {}
    namen = [n for n in (eintrag.get('bp') or []) if n]
    if not namen:
        return None
    fehlend = [n for n in namen if not hat_bereits(n)]
    return len(namen), fehlend
