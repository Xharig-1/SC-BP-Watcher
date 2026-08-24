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
Die Bauplan-Meldung in der Game.log erkennen — in jeder Spielsprache.

Beim Freischalten schreibt Star Citizen eine Zeile wie

    <SHUDEvent_OnNotification> Added notification "Bauplan erhalten: Attrition-5 Repeater: " [136] …

Der Text davor ist **übersetzt**. Bis v1.5.0 stand die deutsche Formulierung fest
im Code — bei englischem Client griff die Sofort-Meldung deshalb gar nicht. Das
ist unter Linux keine Randerscheinung mehr, dort spielen die meisten auf Englisch.

Drei Quellen, in dieser Rangfolge:

  1. **Eigene Ergänzung** — `phrasen.json` im App-Ordner. Wer eine Formulierung
     findet, die hier fehlt, trägt sie ein, ohne auf eine neue Fassung zu warten.
  2. **Die `global.ini` der eigenen Installation** — die genaueste Quelle, denn
     sie ist die Datei, aus der das Spiel den Text selbst nimmt. Dort steht

         crafting_hud_notification_received_blueprint,P=Bauplan erhalten: %s

     Daraus lässt sich das Suchmuster exakt bauen. Sie liegt aber nur entpackt
     vor, wenn jemand sie ausgepackt hat (beim deutschen Client tut das der
     SC Deutsch Launcher) — sonst steckt sie in `Data.p4k`.
  3. **Die mitgelieferte Tabelle** unten — greift immer.

> Stand: **Deutsch ist gemessen** (an 127 Log-Sicherungen gegengeprüft). Die
> englischen Formulierungen sind bislang **nicht** an einem echten englischen
> Log bestätigt; deshalb stehen dort mehrere Kandidaten nebeneinander. Sobald
> eine echte englische Zeile vorliegt, bleibt die zutreffende stehen.
> Mit `tools/extract_global_ini.py --sprache english` lässt sich der Wortlaut
> aus der eigenen Installation holen, ohne auf einen fremden Log zu warten.
"""
import json
import os
import re

from . import pfade

# Der sprachneutrale Schlüssel — er ist in allen Sprachen derselbe.
INI_SCHLUESSEL = 'crafting_hud_notification_received_blueprint'

# Mitgelieferte Formulierungen. Alle werden gleichzeitig gesucht: Eine Phrase, die
# es in der eigenen Sprache nicht gibt, kann keinen Fehltreffer erzeugen — die
# Zeilenform drumherum ist zu eigen, als dass sie zufällig entstünde.
TABELLE = {
    'de': ['Bauplan erhalten'],                     # gemessen
    'en': ['Blueprint Received', 'Received Blueprint',
           'Blueprint Acquired', 'Blueprint Obtained',
           'Blueprint Unlocked'],                   # Kandidaten, s. o.
}

# Nur diese Zeilen zählen. Die anderen Notification-Zeilen sind Ein- und
# Ausblende-Ereignisse — wer sie mitzählt, meldet jeden Bauplan mehrfach.
RAHMEN = r'Added notification "(?:%s):\s*(.+?)\s*:\s*"'


def _ini_dateien():
    """Alle entpackten `global.ini` der Installation (kann leer sein)."""
    ordner = pfade.lokalisierung_ordner()
    if not ordner:
        return []
    gefunden = []
    try:
        for sprache in sorted(os.listdir(ordner)):
            p = os.path.join(ordner, sprache, 'global.ini')
            if os.path.isfile(p):
                gefunden.append(p)
    except OSError:
        pass
    return gefunden


def _aus_ini(pfad):
    """Die Formulierung aus einer `global.ini` — oder None.

    Gelesen wird zeilenweise und nur bis zum Treffer: Die Datei ist mehrere
    Megabyte groß, sie komplett in den Speicher zu holen wäre unnötig."""
    try:
        with open(pfad, encoding='utf-8-sig', errors='ignore') as f:
            for zeile in f:
                if not zeile.startswith(INI_SCHLUESSEL):
                    continue
                # Format: schluessel,P=Text mit %s   (das ,P ist optional)
                wert = zeile.split('=', 1)[1].strip() if '=' in zeile else ''
                vorne = wert.split('%s', 1)[0].strip()
                # Ein abschließender Doppelpunkt gehört zum Rahmen, nicht zur Phrase
                vorne = vorne.rstrip(':').strip()
                return vorne or None
    except OSError:
        return None
    return None


def _eigene():
    """Selbst ergänzte Formulierungen aus `phrasen.json` im App-Ordner.

    Format:  {"phrasen": ["Blueprint Received"]}"""
    try:
        with open(pfade.app_datei('phrasen.json'), encoding='utf-8') as f:
            werte = json.load(f).get('phrasen') or []
        return [str(p).strip() for p in werte if str(p).strip()]
    except Exception:
        return []


def sammeln():
    """Alle Formulierungen, nach denen gesucht wird — samt Herkunft.

    Rückgabe: (liste_der_phrasen, herkunft) — Herkunft ist 'ini', 'eigen'
    oder 'tabelle', je nachdem, was den genauesten Beitrag geliefert hat."""
    phrasen, herkunft = [], 'tabelle'
    for p in _eigene():
        if p not in phrasen:
            phrasen.append(p)
            herkunft = 'eigen'
    for datei in _ini_dateien():
        p = _aus_ini(datei)
        if p and p not in phrasen:
            phrasen.append(p)
            herkunft = 'ini'
    for sprache in TABELLE.values():
        for p in sprache:
            if p not in phrasen:
                phrasen.append(p)
    return phrasen, herkunft


def muster(phrasen=None):
    """Fertiger regulärer Ausdruck für die Log-Zeilen."""
    if phrasen is None:
        phrasen, _ = sammeln()
    return re.compile(RAHMEN % '|'.join(re.escape(p) for p in phrasen))


def bestaetigt():
    """Steht die Formulierung fest — oder wird geraten?

    True, sobald sie aus der eigenen `global.ini` oder aus `phrasen.json` stammt.
    Bei einem deutschen Client ist sie auch aus der Tabelle heraus verlässlich,
    weil genau diese gemessen wurde."""
    _, herkunft = sammeln()
    return herkunft in ('ini', 'eigen')


if __name__ == '__main__':
    ps, woher = sammeln()
    print('Herkunft:', woher, '· bestätigt:', bestaetigt())
    for p in ps:
        print(' ·', p)
