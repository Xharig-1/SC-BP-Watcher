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
Die Merkliste — Baupläne, auf die man wartet.

Trägt man einen Bauplan hier ein, meldet der Watcher ihn **auffällig**, sobald
er auftaucht: gold statt grün, mit Stern. Danach fliegt er von selbst wieder
raus, denn eine Merkliste voller längst erledigter Wünsche ist keine.

Gepflegt wird sie **im Fenster mit einem Klick** — niemand soll dafür eine
Datei bearbeiten müssen. Die Datei (`watchlist.json`) bleibt trotzdem lesbar
und von Hand änderbar, denn ein eigenes Werkzeug des Autors schreibt dort Teile der
Staffelrüstung hinein.

Zwei Arten von Einträgen leben nebeneinander:

  **Namen** — was im Fenster angeklickt wurde. Genauer Abgleich.
  **Muster** — Teilstücke eines Namens, von außen eingetragen (der Skill kennt
  die endgültigen Namen künftiger Gegenstände ja noch nicht). Trifft ein Muster,
  gilt der Eintrag als erfüllt.

Format:

    {
      "namen": ["Attrition-5 Repeater"],
      "eintraege": [{"titel": "Mamba-Helm", "muster": ["adp-mk4", "woodland"]}]
    }
"""
import json
import os

from . import pfade

DATEI = 'watchlist.json'


def _norm(s):
    """Vergleichsform eines Namens — siehe `pfade.namensform`."""
    return pfade.namensform(s)


def pfad():
    return pfade.app_datei(DATEI)


def laden():
    """Die Merkliste. Fehlt die Datei, ist sie leer — das ist kein Fehler."""
    try:
        with open(pfad(), encoding='utf-8') as f:
            d = json.load(f)
    except Exception:
        return {'namen': [], 'eintraege': []}
    if not isinstance(d, dict):
        return {'namen': [], 'eintraege': []}
    d.setdefault('namen', [])
    d.setdefault('eintraege', [])
    if not isinstance(d['namen'], list):
        d['namen'] = []
    if not isinstance(d['eintraege'], list):
        d['eintraege'] = []
    return d


def speichern(daten):
    """Schreibt über eine Nebendatei, damit ein Absturz nichts zerreißt."""
    ziel = pfad()
    temp = ziel + '.tmp'
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=1)
        os.replace(temp, ziel)
        return True
    except OSError as ausnahme:
        try:
            from . import fehler
            fehler.merken('merkliste.speichern', ausnahme)
        except Exception:
            pass
        try:
            os.remove(temp)
        except OSError:
            pass
        return False


# ---------------------------------------------------------------- Nach außen
def namen(daten=None):
    """Die angeklickten Namen in Vergleichsform."""
    return {_norm(n) for n in (daten or laden())['namen']}


def enthaelt(name, daten=None):
    return _norm(name) in namen(daten)


def hinzufuegen(name, daten=None):
    """Aufnehmen. Gibt die geänderten Daten zurück (noch nicht gespeichert)."""
    daten = daten or laden()
    if not enthaelt(name, daten):
        daten['namen'].append(name.strip())
    return daten


def entfernen(name, daten=None):
    """Herausnehmen — auch aus den Muster-Einträgen, falls einer greift."""
    daten = daten or laden()
    k = _norm(name)
    daten['namen'] = [n for n in daten['namen'] if _norm(n) != k]
    daten['eintraege'] = [e for e in daten['eintraege']
                          if not _muster_trifft(e, k)]
    return daten


def umschalten(name):
    """Klick im Fenster: rein oder raus. Gibt zurück, ob er jetzt drin ist."""
    daten = laden()
    drin = enthaelt(name, daten)
    daten = entfernen(name, daten) if drin else hinzufuegen(name, daten)
    speichern(daten)
    return not drin


def _muster_trifft(eintrag, name_norm):
    muster = [str(m).lower() for m in (eintrag.get('muster') or [])]
    return bool(muster) and any(m in name_norm for m in muster)


def treffer(name, daten=None):
    """Wird auf diesen Bauplan gewartet? Rückgabe: Titel des Eintrags oder None.

    Bei einem angeklickten Namen ist der Titel der Name selbst, bei einem
    Muster-Eintrag dessen Titel („Mamba-Helm")."""
    daten = daten or laden()
    k = _norm(name)
    for n in daten['namen']:
        if _norm(n) == k:
            return n
    for e in daten['eintraege']:
        if _muster_trifft(e, k):
            return e.get('titel') or name
    return None


def erledigen(name):
    """Einen erfüllten Wunsch austragen. Gibt den Titel zurück, wenn einer weg ist.

    Wird aufgerufen, sobald ein Bauplan im eigenen Bestand landet: Worauf man
    gewartet hat und was man jetzt hat, gehört nicht mehr auf die Liste."""
    daten = laden()
    titel = treffer(name, daten)
    if not titel:
        return None
    speichern(entfernen(name, daten))
    return titel


def alle(daten=None):
    """Alles, worauf gewartet wird — für die Anzeige. Namen zuerst."""
    daten = daten or laden()
    liste = [{'titel': n, 'art': 'name'} for n in sorted(daten['namen'])]
    liste += [{'titel': e.get('titel') or '?', 'art': 'muster',
               'muster': e.get('muster') or []}
              for e in daten['eintraege']]
    return liste


def anzahl(daten=None):
    daten = daten or laden()
    return len(daten['namen']) + len(daten['eintraege'])


if __name__ == '__main__':
    print('Datei:', pfad())
    for e in alle():
        print('  %-8s %s %s' % (e['art'], e['titel'], e.get('muster') or ''))
    print('Gesamt:', anzahl())
