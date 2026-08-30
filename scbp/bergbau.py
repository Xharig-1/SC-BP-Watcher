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
Wo welches Erz abzubauen ist.

Beantwortet **zwei** Fragen mit denselben Daten — beide sind echte Fälle:

  * „Ich brauche Iron, wo bekomme ich das?"  → 27 Orte
  * „Ich bin auf Daymar, was gibt es hier?"  → 14 Erze

⚠ **Das ist bewusst keine Kopie von scmdb.** Keine Wahrscheinlichkeits-Balken,
kein Refinery-Vergleich — wer es genau wissen will, ist auf scmdb.net besser
aufgehoben, und dorthin wird auch verwiesen. Der Wert hier ist, dass man das
Spiel nicht verlassen muss und aus dem Rezept direkt herspringt.

**Woher die Daten kommen**

`mining_data-<build>.json` von scmdb.net, 0,4 MB, einmal je Spiel-Build. Nichts
davon wird mitgeliefert (CC BY-NC-ND); die Nutzung ist von Krovax am 29.08.2026
freigegeben, die Weitergabe nicht.

**Die Kette durch die Daten** (drei Anläufe gekostet, deshalb hier festgehalten)

    locations[]                     50 Orte in Nyx, Pyro, Stanton
      groups[]                      FPS_Mineables · SpaceShip_Mineables ·
                                    SpaceShip_Mineables_Rare ·
                                    GroundVehicle_Mineables · (Salvage/Harvest)
        deposits[]
          compositionGuid   ─┐
                             ├─→ compositions[guid].parts[].elementName
                             ┘

⚠ **Nicht über `presetName` gehen.** Bei Erz-Vorkommen ist das Feld leer (364
mal); nur Wrackteile tragen dort einen Namen. Wer darüber verknüpft, bekommt
0 Treffer — genau so gemessen am 29.08.2026.

⚠ **Nur die Erz-Gruppen nehmen.** `Salvage_*` und `Harvestables` stehen in
derselben Liste, sind aber Wracks und Pflanzen.
"""
import json
import os

from . import fehler, pfade
from .katalog import AUS, hole_datei
from .herstellung import norm_rohstoff
from .sprache import t

# Nur der Dateiname — siehe `katalog.hole_datei()`.
QUELLE = 'mining_data-%s.json'
CACHE = 'mining-data.json'
FORMAT = 1

# Das Geruest, wenn noch nichts geladen ist.
LEER = {'format': FORMAT, 'build': None, 'locations': [], 'compositions': {}}

# Welche Gruppe bedeutet welche Abbauart. Alles, was hier nicht steht, ist kein
# Erz (Wracks, Pflanzen) und wird übergangen.
ARTEN = {
    'FPS_Mineables':            'fps',
    'SpaceShip_Mineables':      'schiff',
    'SpaceShip_Mineables_Rare': 'schiff_selten',
    'GroundVehicle_Mineables':  'fahrzeug',
}




# ⚠⚠ **Die Daten bleiben im Speicher.**
#
# `laden()` las bis zum 29.08.2026 bei JEDEM Aufruf die ganze Datei von der
# Platte — bei den Rezepten sind das 4 MB und **22 ms**. Das fiel niemandem
# auf, solange nur beim Seitenaufbau geladen wurde. Mit dem Qualitäts-Regler
# wurde daraus ein Ladevorgang **pro Mausbewegung**: über 600 ms Rechenzeit je
# Sekunde, und der Regler ruckelte so, dass er unbenutzbar war.
#
# Gemerkt wird zusammen mit Zeitstempel und Größe der Datei. Ändert sich eine
# von beiden — etwa weil ein neuer Spiel-Build geladen wurde — wird neu
# gelesen. Damit bleibt der Zwischenspeicher richtig, ohne dass jemand ihn von
# Hand leeren muss.
_gemerkt = {'stand': None, 'daten': None}


def laden():
    """Der abgelegte Stand — aus dem Speicher, wenn die Datei unverändert ist."""
    pfad = pfade.app_datei(CACHE)
    try:
        st = os.stat(pfad)
        kennung = (st.st_mtime_ns, st.st_size)
    except OSError:
        kennung = None
    if kennung is not None and _gemerkt['stand'] == kennung:
        return _gemerkt['daten']
    try:
        with open(pfad, encoding='utf-8') as f:
            daten = json.load(f)
        if daten.get('format') == FORMAT:
            _gemerkt['stand'], _gemerkt['daten'] = kennung, daten
            return daten
    except Exception:
        pass
    return LEER.copy()

def stand():
    return laden().get('build')


def aktualisieren(build, fortschritt=None):
    """Die Bergbau-Daten holen, wenn sie fehlen oder veraltet sind."""
    if AUS:
        return False, t('m_h_kein_netz')
    da = laden()
    if da.get('build') == build and da.get('locations'):
        return True, t('m_b_aktuell') % len(da['locations'])
    if fortschritt:
        fortschritt(t('z_laedt') % ('Bergbau', 0.4))
    roh = hole_datei(QUELLE % build)
    orte = roh.get('locations') or []
    if not orte:
        return False, t('m_b_leer')
    _sichern({'format': FORMAT, 'build': build, 'locations': orte,
              'compositions': roh.get('compositions') or {}})
    return True, t('m_b_geladen') % len(orte)


def _sichern(daten):
    ziel = pfade.app_datei(CACHE)
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False)
        os.replace(ziel + '.tmp', ziel)
        # ⚠ Zwischenspeicher verwerfen: Zeitstempel und Groesse koennen sich
        # binnen derselben Sekunde wiederholen, dann bliebe der alte Stand.
        _gemerkt['stand'] = None
        return True
    except Exception as ausnahme:
        fehler.merken('bergbau._sichern', ausnahme)
        return False


# ------------------------------------------------------------- Auswerten
def _erze_am_ort(ort, compositions):
    """{Erzname: {Abbauart, …}} für einen Ort."""
    raus = {}
    for g in ort.get('groups') or []:
        art = ARTEN.get(g.get('groupName'))
        if not art:
            continue
        for d in g.get('deposits') or []:
            c = compositions.get(d.get('compositionGuid'))
            if not c:
                continue
            for teil in c.get('parts') or []:
                name = teil.get('elementName')
                if name:
                    raus.setdefault(name, set()).add(art)
    return raus


def orte():
    """Alle Orte mit Erzen: [{name, system, typ, erze:{name:{art}}}]."""
    daten = laden()
    comp = daten.get('compositions') or {}
    raus = []
    for o in daten.get('locations') or []:
        erze = _erze_am_ort(o, comp)
        if not erze:
            continue
        raus.append({'name': o.get('locationName') or '?',
                     'system': o.get('system') or '',
                     'typ': o.get('locationType') or '',
                     'erze': erze})
    raus.sort(key=lambda x: x['name'].lower())
    return raus


def abbauart(name):
    """Wie wird dieser Rohstoff abgebaut? — Menge aus `fps`, `fahrzeug`, `schiff`.

    ⚠ Gebraucht im Lager: Wer „Iron" einträgt, will auf einen Blick sehen, ob
    er dafür mit dem Multi-Tool loszieht oder ein Schiff braucht. Die Angabe
    steckt in den Bergbaudaten an jedem Fundort; hier werden sie über alle Orte
    des Rohstoffs zusammengefasst.

    `schiff_selten` zählt als `schiff` — für die Frage „womit hole ich das?"
    macht die Seltenheit keinen Unterschied.
    """
    gesucht = norm_rohstoff(name)
    arten = set()
    for e in erze():
        if norm_rohstoff(e.get('name')) != gesucht:
            continue
        for eintrag in e.get('orte') or []:
            for art in (eintrag[2] if len(eintrag) > 2 else ()):
                arten.add('schiff' if art.startswith('schiff') else art)
    return arten


def erze():
    """Alle Erze: [{name, orte:[(Ort, System, {Art})]}] — die Gegenrichtung."""
    sammlung = {}
    for o in orte():
        for name, arten in o['erze'].items():
            sammlung.setdefault(name, []).append((o['name'], o['system'], arten))
    raus = [{'name': n, 'orte': sorted(v)} for n, v in sammlung.items()]
    raus.sort(key=lambda x: x['name'].lower())
    return raus


def orte_fuer(rohstoff):
    """Wo gibt es diesen Rohstoff? Verträgt beide Schreibweisen.

    ⚠ Die Baupläne sagen `Aslarite`, hier heißt es `Aslarite (Raw)` — deshalb
    über `norm_rohstoff()` vergleichen. Ohne das findet der Sprung aus dem
    Rezept **nichts** (gemessen: 0 von 26)."""
    gesucht = norm_rohstoff(rohstoff)
    for e in erze():
        if norm_rohstoff(e['name']) == gesucht:
            return e
    return None
