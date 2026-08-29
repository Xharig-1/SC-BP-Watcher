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
Was ein Bauplan zum Herstellen braucht.

Beantwortet **eine** Frage: „Ich will die XL-1 bauen — was brauche ich dafür?"
Also Zutaten, Mengen und Herstellzeit zu jedem der 1.607 Baupläne.

⚠ **Was hier NICHT beantwortet wird: ob man es herstellen kann.** Der Watcher
liest Baupläne aus der `Game.log`; was an Erz im Frachtraum oder im Lager liegt,
steht dort nicht. Also „braucht 0,3 SCU Iron" — nie „du kannst das jetzt bauen".
Dieselbe Linie wie bei der Zählung `[BP 3/12]`, die am 28.08.2026 herausflog,
weil sie mehr behauptete, als sie wusste.

**Woher die Daten kommen**

`crafting_blueprints-<build>.json` von scmdb.net, 4,1 MB, einmal je Spiel-Build.
Dazu `crafting_items-<build>.json` (1,3 MB) für die Eigenschaften des Produkts —
die lädt der Katalog ohnehin schon, siehe `katalog.py`.

> **Nichts davon wird mitgeliefert.** scmdb steht unter CC BY-NC-ND 4.0; geholt
> wird zur Laufzeit auf dem Rechner des Nutzers, von der Original-Adresse. Die
> Nutzung ist von Krovax (scmdb) am 29.08.2026 ausdrücklich freigegeben — die
> Weitergabe **nicht**, und die könnte er auch gar nicht erlauben: die Rohdaten
> sind CIGs Eigentum.

**Aufbau der Quelle** (gemessen 29.08.2026, Build 4.10.0-live.12519617)

    blueprints[1607]
      productName          "Drake Ore Pod"
      manufacturer         "Drake Interplanetary"
      productEntityClass   -> items[].entityClass in crafting_items
      type / subtype       "orepod" / None
      tiers[]              je Preisstufe eine
        craftTimeSeconds   95
        slots[]            "Frame", "Core", ...
          options[]        type="resource", resourceName="Iron",
                           quantity=0.3, minQuality=0

Die Struktur sieht mehrere `tiers` je Bauplan vor. **Gemessen an Build
4.10.0-live.12519617 hat aber keiner mehr als einen** (0 von 1607) — hier steht
bewusst keine Warnung vor einem Fall, den es nicht gibt. Gelesen werden trotzdem
alle Stufen, damit es nicht bricht, falls CIG welche nachliefert.

⚠ **Die Rohstoffnamen sind nicht dieselben wie im Bergbau.** Hier steht
`Aslarite`, in `mining_data` steht `Aslarite (Raw)`. Für die spätere Verknüpfung
gibt es `norm_rohstoff()`.
"""
import json
import os
import re

from . import fehler, pfade
from .katalog import AUS, hole_datei, _norm
from .sprache import t

# Die Datei heißt beim Anbieter so; <build> ist die Spielversion.
# Nur der Dateiname — welche Adresse benutzt wird, entscheidet
# `katalog.hole_datei()` (Spiegel zuerst, scmdb.net als Rückfall).
QUELLE = 'crafting_blueprints-%s.json'
CACHE = 'crafting-blueprints.json'

# Aufbau-Nummer wie im Katalog: hochzählen, sobald hier etwas anders abgelegt
# wird. Sonst behielte jeder seinen alten Stand bis zum nächsten Spiel-Patch,
# und der Umbau wäre für ihn unsichtbar.
FORMAT = 1

# Das Geruest, wenn noch nichts geladen ist.
LEER = {'format': FORMAT, 'build': None, 'blueprints': []}


# --------------------------------------------------------------- Holen/Laden


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
        fehler.merken('herstellung._sichern', ausnahme)
        return False


def stand():
    """Für welchen Spiel-Build liegen die Rezepte hier? Oder None."""
    return laden().get('build')


def aktualisieren(build, fortschritt=None):
    """Die Rezepte holen, wenn sie fehlen oder zu einem alten Build gehören.

    Gibt (Erfolg, Meldung) zurück. **Sparsam**: Liegt derselbe Build schon da,
    wird gar nichts abgerufen — die Datei ist 4,1 MB groß."""
    if AUS:
        return False, t('m_h_kein_netz')
    da = laden()
    if da.get('build') == build and da.get('blueprints'):
        return True, t('m_h_aktuell') % len(da['blueprints'])
    if fortschritt:
        fortschritt(t('z_laedt') % ('Herstellung', 4.1))
    roh = hole_datei(QUELLE % build)
    liste = roh.get('blueprints') or []
    if not liste:
        return False, t('m_h_leer')
    _sichern({'format': FORMAT, 'build': build, 'blueprints': liste})
    return True, t('m_h_geladen') % len(liste)


# ------------------------------------------------------------- Auswerten
def norm_rohstoff(name):
    """Rohstoffnamen vergleichbar machen — über Datenquellen hinweg.

    ⚠ Die Baupläne sagen `Aslarite`, `mining_data` sagt `Aslarite (Raw)`, und
    bei Agricium steht dort `Agricium (Ore)`. Ohne diese Angleichung findet die
    Bergbau-Sicht später zu **keinem** Rohstoff einen Fundort — beim Messen am
    29.08.2026 waren es 0 von 26.

    Dazu die englische/amerikanische Schreibweise: `Aluminium` / `Aluminum`.
    """
    if not name:
        return ''
    kurz = name.split('(')[0].strip().lower()
    return kurz.replace('aluminium', 'aluminum')


def _zutaten(tier):
    """Die Zutaten einer Ausbaustufe: [(Slot, Rohstoff, Menge, Mindestgüte)]."""
    raus = []
    for slot in tier.get('slots') or []:
        for o in slot.get('options') or []:
            if o.get('type') == 'resource' and o.get('resourceName'):
                raus.append((slot.get('name') or '',
                             o['resourceName'],
                             o.get('quantity') or 0,
                             o.get('minQuality') or 0))
    return raus


def _name_aus_tag(tag):
    """Ein lesbarer Ersatzname, wenn `productName` fehlt.

    ⚠ **Fünf Baupläne tragen keinen Produktnamen** (gemessen 29.08.2026):
    die Kühler von Idris und Pioneer, die Radare von Idris, Lephari und Polaris.
    Ohne Ersatz stünden in der Liste fünf Einträge namens „?".

    Aus `BP_CRAFT_RADR_GNRP_S03_Idris_TEMP` wird `RADR GNRP S03 Idris`.
    """
    roh = (tag or '').replace('BP_CRAFT_', '').replace('_SCItem', '')
    roh = roh.replace('_TEMP', '').replace('_', ' ').strip()
    return roh or '?'


def _unterscheider(tag, name):
    """Woran man zwei gleichnamige Gegenstände auseinanderhält.

    Aus `BP_CRAFT_POWR_AEGS_S04_Idris_SCItem` neben `…_S04_Reclaimer_SCItem`
    wird `Idris` bzw. `Reclaimer`; bei `…_S02_BroadSpec_Lite` neben
    `…_S03_BroudSpec` bleibt die Größe `S02` / `S03` übrig.

    Genommen wird das, was **nicht** schon im Namen steht.
    """
    roh = _name_aus_tag(tag)
    im_namen = {w.lower() for w in (name or '').split()}
    teile = [w for w in roh.split()
             if w.lower() not in im_namen and w.upper() not in ('BP', 'CRAFT')]
    # Von hinten: dort steht der Schiffs-/Variantenname, vorne die Kürzel.
    return ' '.join(teile[-2:]) if teile else roh


def _fasse_zusammen(liste):
    """Mehrere Baupläne zu einem Listeneintrag — oder eben nicht.

    ⚠ **14 Produktnamen kommen mehrfach vor** (29.08.2026):

      * **10** sind echte Dubletten — dasselbe Rezept, nur eine andere Nummer
        im Tag (`…_01_01_13` neben `…_01_01_15`). Die gehören zusammen, sonst
        steht derselbe Gegenstand zweimal in der Liste.
      * **4** sind verschiedene Gegenstände mit gleichem Namen: „Main
        Powerplant" gibt es für Idris und Reclaimer, „BroadSpec" in S02 und
        S03, und „FoxFire" heißt bei scmdb auch der JUST Goliath. Die müssen
        getrennt bleiben — sonst verschwindet ein Rezept.

    Unterschieden wird am **Rezept**: gleiche Zutaten = ein Eintrag.
    """
    nach_rezept = {}
    for b in liste:
        schluessel = tuple(sorted(
            '%s|%s|%s' % (slot, roh, menge)
            for t_ in (b.get('tiers') or [])
            for slot, roh, menge, _g in _zutaten(t_)))
        nach_rezept.setdefault(schluessel, []).append(b)
    return list(nach_rezept.values())


def alle():
    """Alle herstellbaren Dinge, für die Liste in der Oberfläche.

    Je Eintrag: Name, Hersteller, Art, Anzahl Ausbaustufen — und `tags`, weil
    zu einem Eintrag mehrere Baupläne gehören können.

    **Ein Eintrag je Gegenstand**, nicht je Bauplan: Gleiche Namen mit gleichem
    Rezept werden zusammengefasst (siehe `_fasse_zusammen`). Sonst zählt die
    Übersicht zu hoch — beim Messen am 29.08.2026 kamen so 406 „herstellbare"
    heraus, obwohl es 404 Baupläne waren."""
    nach_name = {}
    for b in laden().get('blueprints') or []:
        name = b.get('productName') or _name_aus_tag(b.get('tag'))
        nach_name.setdefault(_norm(name), []).append(b)

    raus = []
    for gruppe in nach_name.values():
        teile = _fasse_zusammen(gruppe)
        for teil in teile:
            b = teil[0]
            name = b.get('productName') or _name_aus_tag(b.get('tag'))
            # ⚠ Bleiben mehrere Einträge unter demselben Namen übrig, sind es
            # **verschiedene Gegenstände** (Idris- und Reclaimer-Kraftwerk,
            # BroadSpec in zwei Größen). Ohne Unterscheidung stünden sie
            # zweimal gleich in der Liste, und niemand wüsste, welches welches
            # ist. Der Zusatz kommt aus dem Tag.
            #
            # ⚠ `basis` bleibt dabei der ursprüngliche Name — **danach** wird
            # mit dem Bestand verglichen. Wer den Anzeigenamen vergleicht,
            # findet den eigenen Bauplan nicht mehr wieder.
            anzeige = name
            if len(teile) > 1:
                anzeige = '%s (%s)' % (name, _unterscheider(b.get('tag'), name))
            raus.append({
                'basis': name,
                'name': anzeige,
                'hersteller': b.get('manufacturer') or '',
                'art': b.get('type') or '',
                'unterart': b.get('subtype') or '',
                'stufen': len(b.get('tiers') or []),
                'tag': b.get('tag') or '',
                'tags': [x.get('tag') or '' for x in teil],
                'entity': b.get('productEntityClass') or '',
            })
    raus.sort(key=lambda x: x['name'].lower())
    return raus


_einordnung_gemerkt = {'stand': None, 'daten': None}


def _schluessel(name):
    """Namen vergleichbar machen — nur Buchstaben und Ziffern, klein."""
    return re.sub(r'[^a-z0-9]+', '', (name or '').lower())


def einordnung():
    """Zu jedem Bauplan seine Art und Unterart aus den Rezeptdaten.

        {'10seriesgreatswordcannon': ('weapons', 'laser'), …}

    ⚠ **Das ist der Schlüssel für die Filter.** Der Katalog kennt bei
    Schiffswaffen nur `WeaponGun` — welche davon ballistisch und welche Laser
    sind, steht ausschliesslich hier. Umgekehrt kennt er die Körperteile der
    Rüstung (`Char_Armor_Helmet`), die den Rezeptdaten fehlen; dort steht
    stattdessen die **Rolle** (`combat`, `engineer`, `stealth`).

    Beide Quellen zusammen ergeben also erst das vollständige Bild. Verknüpft
    wird über den Namen — gemessen am 29.08.2026: **738 von 738** Bauplänen des
    Katalogs finden so ihr Rezept.

    Wird einmal gelesen und gemerkt; die 2-MB-Datei bei jedem Filterklick neu
    zu lesen wäre dieselbe Falle wie beim Qualitätsregler.
    """
    daten = laden()
    kennung = id(daten)
    if _einordnung_gemerkt['stand'] == kennung:
        return _einordnung_gemerkt['daten']
    zuordnung = {}
    for b in daten.get('blueprints') or []:
        name = b.get('productName') or _name_aus_tag(b.get('tag'))
        if not name:
            continue
        zuordnung[_schluessel(name)] = ((b.get('type') or ''),
                                        (b.get('subtype') or ''))
    _einordnung_gemerkt['stand'] = kennung
    _einordnung_gemerkt['daten'] = zuordnung
    return zuordnung


# Wie die Unterarten und Arten im Fenster heissen sollen. Was hier fehlt,
# wird unveraendert gezeigt — lieber der englische Rohwert als gar nichts.
def _uebersetzt(vorsilbe, wert):
    """Den Anzeigenamen holen — oder den Rohwert, wenn er unbekannt ist.

    Die Namen stehen in `sprache.py` unter `he_art_*` und `he_sub_*`. Fehlt
    einer (neue Waffenart nach einem Patch), wird der englische Rohwert
    gezeigt: lieber `tachyon` als eine leere Zeile.
    """
    from .sprache import TEXTE
    schluessel = 'he_%s_%s' % (vorsilbe, (wert or '').lower())
    if schluessel in TEXTE:
        return t(schluessel)
    return wert or ''


def artname(wert):
    """Wie eine Rezept-Art im Fenster heisst."""
    return _uebersetzt('art', wert)


def unterartname(wert):
    """Wie eine Unterart im Fenster heisst — Waffenart oder Rüstungsrolle."""
    return _uebersetzt('sub', wert)


def unterart_von(name):
    """Die Unterart eines Bauplans — `ballistic`, `laser`, `combat` … oder ''."""
    return einordnung().get(_schluessel(name), ('', ''))[1]


def art_von(name):
    """Die Rezept-Art eines Bauplans — `weapons`, `armour`, `cooler` … oder ''."""
    return einordnung().get(_schluessel(name), ('', ''))[0]


def rezept(name_oder_tag):
    """Das Rezept zu einem Bauplan — oder None.

    Gibt je Ausbaustufe die Zutaten und die Herstellzeit zurück:

        {'name': 'Drake Ore Pod', 'hersteller': 'Drake Interplanetary',
         'stufen': [{'zeit': 95,
                     'zutaten': [('Frame', 'Iron', 0.3, 0)]}]}

    Gelesen werden alle Stufen; aktuell hat jeder Bauplan genau eine.
    """
    gesucht = (name_oder_tag or '').strip().lower()
    for b in laden().get('blueprints') or []:
        if gesucht in ((b.get('productName') or '').lower(),
                       (b.get('tag') or '').lower()):
            return {
                'name': b.get('productName') or b.get('tag') or '?',
                'hersteller': b.get('manufacturer') or '',
                'art': b.get('type') or '',
                'stufen': [{'zeit': (t_.get('craftTimeSeconds') or 0),
                            'zutaten': _zutaten(t_)}
                           for t_ in (b.get('tiers') or [])],
            }
    return None


def rohstoff_bedarf():
    """Wie viele Baupläne brauchen welchen Rohstoff? {Rohstoff: Anzahl}.

    Grundlage für die spätere Umkehrsicht („dir fehlen 12, dafür brauchst du
    vor allem Aslarite"). Gemessen am 29.08.2026: Aslarite steckt in 856 der
    1.607 Baupläne."""
    zaehl = {}
    for b in laden().get('blueprints') or []:
        namen = set()
        for t_ in b.get('tiers') or []:
            for _slot, rohstoff, _menge, _guete in _zutaten(t_):
                namen.add(rohstoff)
        for n in namen:
            zaehl[n] = zaehl.get(n, 0) + 1
    return zaehl


# ------------------------------------------------- Verknüpfung mit dem Bestand
#
# ⭐ **Das ist der Teil, den kein anderes Werkzeug kann.** scmdb lässt Besitz von
# Hand markieren („Mark Owned"); der Watcher weiß ihn aus der `Game.log`. Damit
# ist die Herstellungs-Liste keine Nachschlagetabelle, sondern trägt denselben
# Mehrwert wie die Bauplan-Liste: das Kästchen.
#
# ⚠ **Immer über `_norm()` vergleichen, nie stumpf.** Gemessen am 29.08.2026 an
# einem echten Bestand: 404 von 404 Bauplänen finden ihr Produkt — ohne
# Normalisierung nur 402. Die beiden Ausreißer (`7MA "Lorica"`, `Oracle Helmet`)
# sind die bekannte Anführungszeichen-Falle, die `katalog._norm()` behandelt.


def habe_ich(bestand_schluessel, produktname):
    """Hat der Spieler den Bauplan zu diesem Produkt?

    `bestand_schluessel` ist das Ergebnis von `bestand.schluessel(...)` — also
    bereits normalisierte Namen. Deshalb wird hier nur die andere Seite
    normalisiert."""
    return _norm(produktname or '') in (bestand_schluessel or set())


def mit_bestand(bestand_schluessel):
    """Alle herstellbaren Dinge, jedes mit der Angabe „Bauplan vorhanden".

    Gibt dieselbe Liste wie `alle()` zurück, je Eintrag zusätzlich `habe`:

        True   der Bauplan liegt vor
        False  er fehlt
        None   **unklar** — siehe unten

    ⚠ **`None` ist der wichtige Fall.** Drei Gegenstandsnamen meinen mehrere
    verschiedene Dinge („BroadSpec" gibt es in S02 und S03, „Main Powerplant"
    für Idris und Reclaimer). Der Bestand kennt nur den Namen, nicht die
    Variante. Wer hier beide anhakt, verspricht dem Spieler, er könne **beide**
    bauen — und das wissen wir nicht.

    Gemessen am 29.08.2026 an einem echten Bestand: Ohne diese Unterscheidung
    standen 405 Häkchen in einer Liste, obwohl es 404 Baupläne sind. Die Linie
    ist dieselbe wie überall im Werkzeug: Was wir nicht wissen, behaupten wir
    nicht — „kennt der Katalog den Auftrag nicht, wird geschwiegen"."""
    raus = alle()
    mehrdeutig = set()
    gesehen = set()
    for e in raus:
        k = _norm(e['basis'])
        if k in gesehen:
            mehrdeutig.add(k)
        gesehen.add(k)
    for e in raus:
        # ⚠ Gegen `basis` vergleichen, nicht gegen den Anzeigenamen.
        da = habe_ich(bestand_schluessel, e['basis'])
        e['habe'] = (None if (da and _norm(e['basis']) in mehrdeutig) else da)
    return raus


def zaehlung(bestand_schluessel):
    """(sicher, gesamt, unklar) — für die Zeile über der Liste.

    Gedacht als Gegenstück zum Bauplan-Fortschritt: Dort steht, wie viele
    Baupläne man kennt; hier, wie viele der herstellbaren Dinge man davon
    tatsächlich bauen kann.

    ⚠ **Gezählt werden die eigenen Baupläne, nicht die Listeneinträge.** Vier
    Produktnamen kommen doppelt vor und meinen verschiedene Gegenstände
    („Main Powerplant" für Idris und Reclaimer, „BroadSpec" in zwei Größen).
    Wer über die Liste zählt, zählt so einen Bauplan zweimal — beim Messen am
    29.08.2026 kamen 405 heraus, obwohl der Bestand 404 hatte."""
    liste = mit_bestand(bestand_schluessel)
    sicher = sum(1 for e in liste if e['habe'] is True)
    unklar = sum(1 for e in liste if e['habe'] is None)
    return sicher, len(liste), unklar


# ------------------------------------------------- Was die Qualität bewirkt
#
# ⭐ **Der Teil, den keine Webseite leisten kann.** Die Rezepte sagen nicht nur,
# *welches* Material gebraucht wird, sondern auch, **wie stark die Qualität die
# Werte des Produkts verändert**:
#
#     {"startQuality": 0, "endQuality": 1000,
#      "modifierAtStart": 0.9, "modifierAtEnd": 1.1,
#      "propertyName": "Damage Mitigation"}
#
# Also: mieses Erz → 0,9-fache Schadensminderung, bestes Erz → 1,1-fache.
# Dazwischen wird linear gerechnet.
#
# Gemessen am 29.08.2026: **1.540 von 1.607 Bauplänen (96 %)** haben solche
# Angaben. Betroffen sind Min/Max Temp, Damage Mitigation, Integrity, Power
# Pips, Impact Force, Coolant Rating, Schildstärke, Rückstoß und mehr.
#
# ⚠ **Die Skala ist 0 bis 1000** — daher stammen auch die `minQuality`-Werte
# 500 bis 900 in den Rezepten.
#
# ⚠ **Es gibt mehrere Spannen je Eigenschaft** (etwa 0–500 und 501–1000): Die
# Kurve ist stückweise linear, nicht durchgehend. Wer nur die erste Spanne
# nimmt, rechnet oberhalb davon falsch.


def _spanne_fuer(modifikatoren, qualitaet):
    """Die Spanne, in die diese Qualität fällt — sonst die nächstgelegene."""
    q = float(qualitaet or 0)
    for m in modifikatoren:
        if float(m.get('startQuality', 0)) <= q <= float(m.get('endQuality', 0)):
            return m
    # Außerhalb aller Spannen: die mit der nächsten Grenze nehmen, damit das
    # Ergebnis nicht einfach verschwindet.
    if not modifikatoren:
        return None
    return min(modifikatoren,
               key=lambda m: min(abs(q - float(m.get('startQuality', 0))),
                                 abs(q - float(m.get('endQuality', 0)))))


def faktor(modifikatoren, qualitaet):
    """Der Multiplikator für diese Qualität — linear in der passenden Spanne."""
    m = _spanne_fuer(modifikatoren, qualitaet)
    if not m:
        return None
    start, ende = float(m.get('startQuality', 0)), float(m.get('endQuality', 0))
    a, b = float(m.get('modifierAtStart', 1)), float(m.get('modifierAtEnd', 1))
    if ende == start:
        return b
    anteil = (float(qualitaet or 0) - start) / (ende - start)
    anteil = max(0.0, min(1.0, anteil))          # außerhalb nicht extrapolieren
    return a + anteil * (b - a)


def slots(name_oder_tag):
    """Die Slots eines Bauplans mit Material **und** Qualitätswirkung.

    [{slot, material, menge, mindestguete, wirkungen:[{eigenschaft, key, mods}]}]
    """
    gesucht = (name_oder_tag or '').strip().lower()
    for b in laden().get('blueprints') or []:
        if gesucht not in ((b.get('productName') or '').lower(),
                           (b.get('tag') or '').lower()):
            continue
        raus = []
        for t_ in b.get('tiers') or []:
            for s in t_.get('slots') or []:
                material = menge = guete = None
                for o in s.get('options') or []:
                    if o.get('type') == 'resource' and o.get('resourceName'):
                        material = o['resourceName']
                        menge = o.get('quantity') or 0
                        guete = o.get('minQuality') or 0
                        break
                nach_eigenschaft = {}
                for m in s.get('modifiers') or []:
                    nach_eigenschaft.setdefault(
                        (m.get('propertyName'), m.get('propertyKey')),
                        []).append(m)
                raus.append({
                    'slot': s.get('name') or '',
                    'material': material,
                    'menge': menge,
                    'mindestguete': guete,
                    'wirkungen': [{'eigenschaft': n, 'key': k, 'mods': v}
                                  for (n, k), v in nach_eigenschaft.items()],
                })
        return raus
    return None


def werte_mit_lager(name_oder_tag, qualitaet_je_material):
    """Was käme mit **diesem** Material heraus?

    `qualitaet_je_material` ist {Material: Qualität} — in der Regel die beste
    brauchbare Qualität aus dem eigenen Lager
    (`rohstoffe.beste_qualitaet()`). Materialien ohne Eintrag werden
    übersprungen; über sie ist nichts bekannt, und geraten wird nicht.

    Gibt [{eigenschaft, material, qualitaet, faktor}] zurück.
    """
    raus = []
    for s in (slots(name_oder_tag) or []):
        q = (qualitaet_je_material or {}).get(s['material'])
        if q is None:
            continue
        for w in s['wirkungen']:
            f = faktor(w['mods'], q)
            if f is None:
                continue
            raus.append({'eigenschaft': w['eigenschaft'], 'key': w['key'],
                         'material': s['material'], 'qualitaet': q,
                         'faktor': f, 'slot': s['slot']})
    return raus


def rohstoffnamen():
    """Alle Materialien, die in Rezepten vorkommen — alphabetisch.

    ⚠ **Damit niemand raten oder tippen muss.** Ein freies Textfeld für einen
    Namen, der exakt passen muss, ist eine stille Fehlerquelle: Wer „Aslerite"
    schreibt, bekommt nie einen Treffer und erfährt auch nicht, warum. Gemessen
    am 29.08.2026 sind es **26** Materialien — eine Liste, die in jede Auswahl
    passt.
    """
    namen = set()
    for b in laden().get('blueprints') or []:
        for t_ in b.get('tiers') or []:
            for slot, rohstoff, _menge, _guete in _zutaten(t_):
                if rohstoff:
                    namen.add(rohstoff)
    return sorted(namen, key=lambda x: x.lower())


def kennt_rohstoff(name):
    """Ist dieser Name einem Rezept-Material zuzuordnen?"""
    if not (name or '').strip():
        return False
    gesucht = norm_rohstoff(name)
    return any(norm_rohstoff(n) == gesucht for n in rohstoffnamen())


def offizieller_name(eingabe):
    """Die verbindliche Schreibweise zu einer Eingabe — oder `None`.

    ⚠ **Der Name ist der Schlüssel.** Steht im Lager `aslarite` oder
    `Aslerite`, findet kein Rezept den Bestand, und niemand sieht, warum: Die
    Liste sieht richtig aus, nur die Häkchen bleiben aus. Deshalb wird die
    Eingabe hier auf einen bekannten Namen gezogen, statt sie zu übernehmen,
    wie sie getippt wurde.

    Was zusammengeführt wird:
      * Groß- und Kleinschreibung sowie Leerzeichen am Rand
      * die Bergbau-Schreibweise mit Klammer (`Aslarite (Raw)`)
      * `Aluminium` gegen `Aluminum`
      * ein knapper Vertipper, solange er **eindeutig** einem Namen zuzuordnen
        ist — bei zwei ähnlich nahen Kandidaten wird nichts geraten

    Gibt `None` zurück, wenn nichts sicher passt. Dann entscheidet die
    Oberfläche, ob sie nachfragt.
    """
    import difflib
    text = (eingabe or '').strip()
    if not text:
        return None
    alle = rohstoffnamen()
    if not alle:
        # ⚠ Keine Rezeptdaten geladen — dann gibt es nichts zu vergleichen.
        # Hier `None` zu melden hiesse: „kenne ich nicht", und die Oberfläche
        # wuerde **jede** Eingabe abweisen. Wer beim ersten Start ohne Netz
        # sein Lager fuellen will, kaeme nicht weiter. Also durchlassen.
        return text
    gesucht = norm_rohstoff(text)

    for n in alle:
        if norm_rohstoff(n) == gesucht:
            return n

    # Vertipper: hohe Schwelle, und nur wenn der zweitbeste Treffer deutlich
    # schlechter ist. Sonst macht die Berichtigung aus einem falschen Namen
    # einen anderen falschen Namen.
    schluessel = {norm_rohstoff(n): n for n in alle}
    nahe = difflib.get_close_matches(gesucht, list(schluessel), n=2, cutoff=0.82)
    if len(nahe) == 1:
        return schluessel[nahe[0]]
    if len(nahe) == 2:
        g = difflib.SequenceMatcher
        a = g(None, gesucht, nahe[0]).ratio()
        b = g(None, gesucht, nahe[1]).ratio()
        if a - b >= 0.08:
            return schluessel[nahe[0]]
    return None


def aehnliche_rohstoffe(name, hoechstens=3):
    """Vorschläge zu einem Namen, der so nicht bekannt ist.

    Erst Namen, die den Text enthalten; sonst die mit der kleinsten
    Tippabweichung. Damit aus „Aslerite" ein „Aslarite" wird, statt eines
    stillen Fehlschlags."""
    import difflib
    text = (name or '').strip().lower()
    if not text:
        return []
    alle = rohstoffnamen()
    treffer = [n for n in alle if text in n.lower()]
    if treffer:
        return treffer[:hoechstens]
    return difflib.get_close_matches(text, alle, n=hoechstens, cutoff=0.6)
