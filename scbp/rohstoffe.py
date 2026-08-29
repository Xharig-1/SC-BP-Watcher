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
Das eigene Rohstoff-Lager — von Hand geführt.

**Warum von Hand.** Die `Game.log` sagt **nichts** über Rohstoffe: In 17 MB
Protokollen (aktuelles plus 18 Sicherungen, Stand 29.08.2026) kommt kein
einziges Mal `craft`, `resource`, `inventory` oder `cargo` vor. Was im
Frachtraum liegt, kann der Watcher also nicht wissen — anders als bei den
Bauplänen, die im Log stehen.

**Der Vorschlag dahinter** stammt von **Horthy (KRT)** (29.08.2026):
Rohstoffe selbst eintragen, und beim Herstellen sagt man dem Werkzeug „Bauplan
X baue ich jetzt" — dann zieht es die Zutaten ab. Die Mengen kennt es seit
v3.3.0 ohnehin (`herstellung.rezept()`).

⚠ **Haltung: Hinweis, keine Behauptung.**

Zugänge muss der Spieler eintragen — wer das zweimal vergisst, hat ein
lückenhaftes Lager. Deshalb sagt das Werkzeug **nie** „du kannst das nicht
bauen", sondern höchstens „dir fehlt Iron". Ein veraltetes Lager wird dadurch
nicht falsch, nur weniger hilfreich. Dieselbe Linie wie bei der gelöschten
Zählung `[BP 3/12]`: lieber nichts sagen als etwas Unwahres.

**Aufbau der Datei** (`rohstoffe.json` im eigenen Ordner)

    {"format": 1,
     "posten": [{"material": "Iron", "menge": 12.5,
                 "qualitaet": 80, "ort": "Daymar"}]}

Mehrere Posten desselben Materials sind Absicht: 12 SCU Iron von Daymar mit
80 % Güte sind etwas anderes als 3 SCU aus dem Aaron Halo.
"""
import json
import os

from . import fehler, pfade
from .herstellung import norm_rohstoff

DATEI = 'rohstoffe.json'
FORMAT = 1


def laden():
    """Alle Posten — oder eine leere Liste."""
    try:
        with open(pfade.app_datei(DATEI), encoding='utf-8') as f:
            daten = json.load(f)
        if daten.get('format') == FORMAT:
            return daten.get('posten') or []
    except Exception:
        pass
    return []


def sichern(posten):
    """Die Posten schreiben. Meldet einen Fehlschlag, statt ihn zu schlucken."""
    ziel = pfade.app_datei(DATEI)
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel + '.tmp', 'w', encoding='utf-8') as f:
            json.dump({'format': FORMAT, 'posten': posten}, f,
                      ensure_ascii=False, indent=1)
        os.replace(ziel + '.tmp', ziel)
        return True
    except Exception as ausnahme:
        fehler.merken('rohstoffe.sichern', ausnahme)
        return False


def als_csv(posten=None):
    """Das Lager als Tabelle — Material, Menge, Qualität, Lagerort.

    Warum CSV und nicht nur JSON: Eine Tabelle öffnet sich in jedem
    Tabellenprogramm und lässt sich weiterreichen. Das eigene JSON ist zum
    Zurücklesen da, die Tabelle zum Ansehen und Teilen.

    ⚠ Semikolon als Trenner und Komma als Dezimalzeichen — so erwartet es ein
    deutsches Excel/LibreOffice. Mit Punkt und Komma-Trenner landet „1.36" dort
    als Datum oder in einer Spalte zu viel.
    """
    posten = laden() if posten is None else posten
    zeilen = ['Material;Menge;Qualitaet;Lagerort']
    for p in posten:
        menge = ('%g' % float(p.get('menge') or 0)).replace('.', ',')
        guete = ('%g' % float(p['qualitaet'])) if p.get('qualitaet') else ''
        zeilen.append(';'.join((
            (p.get('material') or '').replace(';', ','),
            menge, guete,
            (p.get('ort') or '').replace(';', ','))))
    return '\n'.join(zeilen) + '\n'


def als_json(posten=None):
    """Das Lager als JSON-Text — dasselbe Format, das `laden()` wieder liest.

    Damit ist der Export zugleich eine Sicherung: Datei wegschreiben, später
    zurückspielen, fertig.
    """
    posten = laden() if posten is None else posten
    return json.dumps({'format': FORMAT, 'posten': posten},
                      ensure_ascii=False, indent=1)


def aus_json(text):
    """Ein früher ausgegebenes Lager wieder einlesen.

    Gibt die Postenliste zurück oder `None`, wenn die Datei nicht passt. ⚠ Es
    wird **nichts** gespeichert — das entscheidet die Oberfläche, nachdem sie
    gefragt hat, ob ersetzt oder ergänzt werden soll.
    """
    try:
        daten = json.loads(text)
    except Exception:
        return None
    if not isinstance(daten, dict) or daten.get('format') != FORMAT:
        return None
    posten = daten.get('posten')
    if not isinstance(posten, list):
        return None
    sauber = []
    for p in posten:
        if not isinstance(p, dict) or not (p.get('material') or '').strip():
            continue
        sauber.append({'material': str(p.get('material')).strip(),
                       'menge': float(p.get('menge') or 0),
                       'qualitaet': p.get('qualitaet'),
                       'ort': str(p.get('ort') or '').strip()})
    return sauber


def zahl_lesen(text):
    """Eine getippte Zahl lesen — Komma und Punkt gelten gleich.

    ⚠ Die einen tippen `12,5`, die anderen `12.5`. Python kennt nur den Punkt,
    und `float('12,5')` wirft. Ohne diese Stelle haette jeder zweite Nutzer
    beim Eintragen eine Fehlermeldung bekommen und nicht gewusst, warum.

    Auch das lange Minus vom Ziffernblock (`−`) wird angenommen, sonst
    scheitert das Abbuchen an einem Zeichen, das man nicht sieht.

    Gibt `None`, wenn es keine Zahl ist — dann meldet die Oberfläche das.
    """
    roh = (text or '').strip().replace(',', '.').replace('−', '-')
    if not roh:
        return None
    try:
        return float(roh)
    except ValueError:
        return None


def eintragen(material, menge, qualitaet=None, ort=''):
    """Einen Posten hinzufügen. Gibt die neue Gesamtmenge des Materials zurück."""
    posten = laden()
    posten.append({'material': (material or '').strip(),
                   'menge': float(menge or 0),
                   'qualitaet': qualitaet,
                   'ort': (ort or '').strip()})
    sichern(posten)
    return menge_von(material)


def aendern(nummer, material, menge, qualitaet=None, ort=''):
    """Einen vorhandenen Posten überschreiben (Position in der Liste).

    Gebraucht wird das dauernd: Man vertippt sich bei der Menge, gibt jemandem
    zwei SCU ab oder trägt den Lagerort nach. Ohne diesen Weg blieb nur
    löschen und neu tippen — und wer beim Tippen den Namen anders schreibt,
    hat den Posten anschliessend doppelt.

    Gibt True zurück, wenn es die Nummer gab.
    """
    posten = laden()
    if not (0 <= nummer < len(posten)):
        return False
    posten[nummer] = {'material': (material or '').strip(),
                      'menge': float(menge or 0),
                      'qualitaet': qualitaet,
                      'ort': (ort or '').strip()}
    sichern(posten)
    return True


def entfernen(nummer):
    """Einen Posten löschen (Position in der Liste)."""
    posten = laden()
    if 0 <= nummer < len(posten):
        posten.pop(nummer)
        sichern(posten)
        return True
    return False


def menge_von(material):
    """Wie viel ist von diesem Material da? Über alle Posten summiert.

    ⚠ Über `norm_rohstoff()` vergleichen — das Rezept sagt `Aslarite`, im Lager
    steht vielleicht `Aslarite (Raw)`, weil es aus der Bergbau-Sicht kopiert
    wurde."""
    gesucht = norm_rohstoff(material)
    return sum(p.get('menge') or 0 for p in laden()
               if norm_rohstoff(p.get('material')) == gesucht)


def menge_mit_guete(material, mindestguete=0):
    """(passend, zu_gering) — wie viel taugt für die geforderte Qualität?

    ⚠ **Die Qualität ist keine Randnotiz.** 1.540 der 1.607 Baupläne (96 %)
    ändern die Werte des Produkts je nach Materialqualität, und 1.227 Zutaten
    fordern ausdrücklich eine Mindestqualität. Erz mit Q 200 in einem Rezept,
    das Q 500 verlangt, ist für diesen Bauplan nichts wert.

    Die Skala läuft **0 bis 1000** (aus den `modifiers` der Rezepte abgelesen).

    ⚠ Gefiltert, aber **nicht gesperrt**: Was nicht reicht, kommt als zweiter
    Wert zurück und wird als Hinweis angezeigt. Behauptet wird nichts — das
    Lager ist von Hand gepflegt und kann hinterherhinken.
    """
    gesucht = norm_rohstoff(material)
    passend = zu_gering = 0.0
    grenze = float(mindestguete or 0)
    for p in laden():
        if norm_rohstoff(p.get('material')) != gesucht:
            continue
        menge = float(p.get('menge') or 0)
        if float(p.get('qualitaet') or 0) >= grenze:
            passend += menge
        else:
            zu_gering += menge
    return passend, zu_gering


def beste_qualitaet(material, mindestguete=0):
    """Die höchste brauchbare Qualität dieses Materials im Lager — oder None.

    Damit lässt sich ausrechnen, **welche Werte** das Produkt bekäme; siehe
    `herstellung.werte_bei_qualitaet()`."""
    gesucht = norm_rohstoff(material)
    beste = None
    for p in laden():
        if norm_rohstoff(p.get('material')) != gesucht:
            continue
        if float(p.get('menge') or 0) <= 0:
            continue
        q = float(p.get('qualitaet') or 0)
        if q >= float(mindestguete or 0) and (beste is None or q > beste):
            beste = q
    return beste


def bestand():
    """{Material: Gesamtmenge} — für die Anzeige im Rezept."""
    raus = {}
    for p in laden():
        name = (p.get('material') or '').strip()
        if not name:
            continue
        schluessel = norm_rohstoff(name)
        vorher = raus.get(schluessel)
        raus[schluessel] = {
            'name': vorher['name'] if vorher else name,
            'menge': (vorher['menge'] if vorher else 0) + (p.get('menge') or 0),
        }
    return raus


def pruefen(zutaten):
    """Was fehlt für dieses Rezept?

    [(Material, gebraucht, da, fehlt, zu_geringe_qualitaet, mindestqualitaet)]

    `zutaten` ist die Liste aus `herstellung.rezept()` — (Slot, Material,
    Menge, Güte). Zurück kommt **jede** Zutat, auch die vorhandenen: Die
    Anzeige soll zeigen, was da ist, nicht nur was fehlt."""
    vorrat = bestand()
    raus = []
    gebraucht = {}
    for _slot, material, menge, _guete in zutaten:
        schluessel = norm_rohstoff(material)
        gebraucht[schluessel] = gebraucht.get(schluessel, 0) + (menge or 0)
    for _slot, material, menge, guete in zutaten:
        schluessel = norm_rohstoff(material)
        # ⚠ Seit 29.08.2026 zählt nur, was die geforderte Qualität erreicht.
        # Vorher wurde `guete` durchgereicht und nie benutzt — dadurch galt Erz
        # als brauchbar, das für dieses Rezept zu schlecht ist.
        passend, zu_gering = menge_mit_guete(material, guete)
        noetig = gebraucht[schluessel]
        raus.append((material, menge, passend, max(0.0, noetig - passend),
                     zu_gering, guete))
    return raus


def abziehen(zutaten, anzahl=1):
    """Die Zutaten eines Rezepts aus dem Lager nehmen — `anzahl` mal.

    ⚠ **`anzahl` gibt es, damit niemand zählen muss.** Wer zehn Stück am Stück
    baut, klickt sonst zehnmal — und beim elften Klick stimmt der Bestand nicht
    mehr, ohne dass es auffällt. Am 29.08.2026 genau so gemeldet: „ich klicke
    dann aber sogar 11 mal, weil ich mich verzählt habe."


    Gibt `(True, [])` zurück, wenn alles da war — sonst `(False, [Material, …])`
    mit dem, was fehlte. **Abgezogen wird trotzdem, so weit es reicht**: Wer
    etwas hergestellt hat, hat die Rohstoffe verbraucht; das Lager soll danach
    nicht mehr behaupten, sie lägen noch da.

    ⚠ Abgezogen wird vom **ältesten** Posten zuerst. Wer zwei Posten desselben
    Materials führt (verschiedene Güte oder Fundort), soll den älteren zuerst
    leer sehen — sonst bleiben lauter Reste stehen.
    """
    posten = laden()
    fehlt = []
    faktor = max(1, int(anzahl or 1))
    for _slot, material, menge, guete in zutaten:
        offen = float(menge or 0) * faktor
        gesucht = norm_rohstoff(material)
        # Nur Posten, die die geforderte Qualität erreichen — schlechteres Erz
        # wurde für dieses Rezept ja auch nicht verbraucht.
        for p in [x for x in posten
                  if float(x.get('qualitaet') or 0) >= float(guete or 0)]:
            if offen <= 0:
                break
            if norm_rohstoff(p.get('material')) != gesucht:
                continue
            da = float(p.get('menge') or 0)
            weg = min(da, offen)
            p['menge'] = round(da - weg, 6)
            offen -= weg
        if offen > 1e-9:
            fehlt.append(material)
    # Leere Posten verschwinden — sonst füllt sich die Liste mit Nullen.
    posten = [p for p in posten if (p.get('menge') or 0) > 1e-9]
    sichern(posten)
    return (not fehlt), fehlt
