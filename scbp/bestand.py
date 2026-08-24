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
Der eigene Bauplan-Bestand — die Liste „welche habe ich".

Bis v1.5.0 kam sie ausschließlich vom SC Deutsch Launcher. Ab jetzt führt der
Watcher sie selbst: Jeder Bauplan, der in der Game.log auftaucht, wird
dauerhaft festgehalten. Damit läuft das Programm ohne den Launcher — und
unter Linux, wo es ihn gar nicht gibt.

**Warum das nicht der schlechtere Weg ist:** Am 11.08.2026 gemessen — dem
Launcher fehlt die P4-AR Rifle, obwohl sie im Fabricator als „im Besitz" steht.
Startbaupläne wurden nie „erhalten" und stehen deshalb in keinem Log. Seine
Zahl ist eine Untergrenze, kein Bestand. Ein selbst geführter Bestand, der
Startbaupläne kennt und Nachlese aus den Log-Sicherungen betreibt, ist genauer.

Die Datei liegt im App-Ordner (`bestand.json`) und sieht so aus:

    {
      "version": 1,
      "stand": "2026-08-24 02:31:00",
      "bauplaene": {
        "7ca 'nargun'": {"name": "7CA 'Nargun'", "quelle": "log",
                         "zeit": "2026-08-24 02:31:00"}
      }
    }

Der Schlüssel ist der kleingeschriebene Name — derselbe Abgleich, den auch
das Hauptprogramm benutzt, damit Log-Fund und Launcher-Eintrag zusammenfinden.
Bekannte Quellen: `log` (aus der laufenden Game.log), `nachlese` (aus einer
Log-Sicherung), `launcher` (vom SC Deutsch Launcher bestätigt), `start`
(Startbauplan, war von Anfang an da) und `hand` (im Fenster abgehakt).
"""
import json
import os
import time

from . import fehler, pfade

DATEI_VERSION = 1

# Rangfolge der Quellen: Ein Eintrag wird nur „aufgewertet", nie herabgestuft.
# Sonst überschriebe eine spätere vorläufige Log-Zeile eine bereits vom
# Launcher bestätigte Angabe.
RANG = {'log': 1, 'nachlese': 1, 'start': 2, 'hand': 3, 'launcher': 4}


def norm(s):
    """Vergleichsform eines Namens — identisch zum Hauptprogramm."""
    return s.lower().replace('\xa0', ' ').replace('�', ' ').strip()


def _jetzt():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def pfad():
    return pfade.app_datei('bestand.json')


def leer():
    return {'version': DATEI_VERSION, 'stand': _jetzt(), 'bauplaene': {}}


def laden():
    """Bestand von der Platte. Fehlt die Datei oder ist sie beschädigt, wird mit
    einem leeren Bestand weitergearbeitet — der Watcher soll nie am Start scheitern."""
    try:
        with open(pfad(), encoding='utf-8') as f:
            daten = json.load(f)
    except Exception:
        return leer()
    if not isinstance(daten.get('bauplaene'), dict):
        return leer()
    daten.setdefault('version', DATEI_VERSION)
    return daten


def speichern(daten):
    """Schreibt den Bestand — mit Vorgängerfassung und ohne Halbfertiges.

    Erst in eine Nebendatei schreiben, dann umbenennen: Stürzt der Rechner
    mitten im Schreiben ab, ist die alte Datei noch vollständig da. Die
    Vorgängerfassung (`bestand.bak.json`) bleibt als Rückfall liegen."""
    daten['version'] = DATEI_VERSION
    daten['stand'] = _jetzt()
    ziel = pfad()
    temp = ziel + '.tmp'
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=1, sort_keys=True)
        if os.path.exists(ziel):
            sicherung = ziel.replace('.json', '.bak.json')
            try:
                os.replace(ziel, sicherung)
            except OSError:
                pass
        os.replace(temp, ziel)
        return True
    except Exception as ausnahme:
        # Hier ist der eigene Bauplan-Bestand betroffen — das Wichtigste, was
        # das Werkzeug hat. Ein stiller Fehlschlag wäre nicht zu verzeihen.
        fehler.merken('bestand.speichern', ausnahme, ziel)
        try:
            os.remove(temp)
        except OSError:
            pass
        return False


def hinzufuegen(daten, name, quelle='log', zeit=None):
    """Einen Bauplan aufnehmen. Gibt True zurück, wenn er vorher nicht drin war.

    Ein schon bekannter Bauplan wird nicht doppelt angelegt; steht die neue
    Quelle höher (z. B. `launcher` statt `log`), wird sie nachgetragen."""
    schluessel = norm(name)
    if not schluessel:
        return False
    eintrag = daten['bauplaene'].get(schluessel)
    if eintrag is None:
        daten['bauplaene'][schluessel] = {
            'name': name.strip(),
            'quelle': quelle,
            'zeit': zeit or _jetzt(),
        }
        return True
    if RANG.get(quelle, 0) > RANG.get(eintrag.get('quelle'), 0):
        eintrag['quelle'] = quelle
    return False


def entfernen(daten, name):
    """Häkchen wieder wegnehmen (Verwaltungsfenster)."""
    return daten['bauplaene'].pop(norm(name), None) is not None


def enthaelt(daten, name):
    return norm(name) in daten['bauplaene']


def schluessel(daten):
    """Alle Namen in Vergleichsform — als Menge, für schnelle Abgleiche."""
    return set(daten['bauplaene'])


def namen(daten):
    """Die Namen in Schreibweise wie gefunden, alphabetisch."""
    return sorted((e.get('name') or k) for k, e in daten['bauplaene'].items())


def anzahl(daten):
    return len(daten['bauplaene'])


def nach_quelle(daten):
    """Wie viele Baupläne kommen woher — für die Statusanzeige."""
    zaehler = {}
    for e in daten['bauplaene'].values():
        q = e.get('quelle') or 'unbekannt'
        zaehler[q] = zaehler.get(q, 0) + 1
    return zaehler


if __name__ == '__main__':
    b = laden()
    print('Datei:  ', pfad())
    print('Anzahl: ', anzahl(b))
    print('Quellen:', nach_quelle(b) or '—')
