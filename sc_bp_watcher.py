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
SC BP Watcher — zeigt live an, sobald im SC Deutsch Launcher ein neuer
Bauplan (Blueprint) freigeschaltet wird.

Überwacht:  die Star-Citizen-Game.log (die eigentliche Quelle) und liest beim
            Start auch die aufgehobenen Logs vergangener Sitzungen nach
            + den SC Deutsch Launcher, **falls** er vorhanden ist (er bestätigt
              die Funde und liefert einen gepflegten Katalog)
            + bp_item_types.json bzw. die scmdb-Craftdaten als Katalog-Wache —
              meldet, was im Spiel NEU craftbar wurde
Bestand:    wird ab v2.0 selbst geführt (`bestand.json` im eigenen Ordner) —
            der SC Deutsch Launcher ist damit kein Muss mehr.
Werte:      Art/Größe/Gütegrad/Klasse aus dem Launcher-Katalog, sonst von
            scmdb.net (seit v1.5.0).
Anzeige:    kleines, immer-im-Vordergrund Overlay-Fenster (verschiebbar).

Reines Python-Standardbibliothek-Tool (tkinter) — keine Zusatzpakete nötig.
Läuft unter **Windows und Linux**; wo die Dateien jeweils liegen, weiß `scbp/pfade.py`.
"""
import os, re, sys, json, time, threading, queue
import tkinter as tk
from tkinter import font as tkfont

# Eigene Bausteine. Sie kapseln alles, was sich zwischen Windows und Linux
# unterscheidet — der Rest dieser Datei muss das Betriebssystem nicht kennen.
from scbp import sprache
from scbp import (aktualisierung, assistent, autostart,
                  bestand as bestand_datei, einstellungsfenster, hinweis,
                  katalog as katalog_modul, logquelle, merkliste, pfade,
                  phrasen, ton)

try:
    import winsound                      # nur Windows; unter Linux übernimmt tkinter
except ImportError:
    winsound = None

__version__ = '2.0.0-rc7'

# ---------------------------------------------------------------- Konfiguration
# Wo die Dateien liegen, entscheidet `scbp/pfade.py` je nach Betriebssystem.
# Der SC Deutsch Launcher ist ab jetzt **optional**: Ist er da, wird er genutzt;
# fehlt er (immer unter Linux), fällt nur seine Bestätigung weg — gemeldet wird
# trotzdem, denn die Game.log ist die eigentliche Quelle.
BP_DIR   = pfade.launcher_ordner() or ''
BP_FILE  = pfade.launcher_datei('sc_bp_erledigt.json', BP_DIR)
TYPE_FILE = pfade.launcher_datei('bp_item_types.json', BP_DIR)
CAT_DIR  = pfade.launcher_datei('catalog', BP_DIR)               # Launcher-Katalog (Size/Grade/Klasse)
HAT_LAUNCHER = bool(BP_DIR) and os.path.isdir(BP_DIR)
# Manuelle Korrekturen an Size/Grade/Klasse, Vorrang vor dem Launcher-Katalog.
# Standard: neben den eigenen Einstellungen in %APPDATA%\sc-bp-watcher\.
# Wer die Datei woanders pflegt, setzt die
# Umgebungsvariable SC_BP_OVERRIDES auf den vollen Pfad. Fehlt beides, gilt der
# Katalog unverändert — die Datei ist optional.
OVERRIDES_FILE = os.environ.get('SC_BP_OVERRIDES') or pfade.app_datei(
    'bp-overrides.json')
# Wie oft die Game.log angesehen wird. Einstellbar über `pruefintervall_sekunden`
# in der `einstellungen.json`; 3 Sekunden sind ein guter Mittelweg zwischen
# „steht sofort da" und „liest dauernd die Platte". Grenzen 1–60, damit eine
# vertippte 0 keine Dauerschleife wird.
POLL_SEC = pfade.einstellung_zahl('pruefintervall_sekunden', 3, 1, 60)
# Signalton bei einem Fund — manche wollen im Spiel keinen zusätzlichen Ton.
TON_AN = pfade.einstellung_wahrheit('signalton', True)
DECKKRAFT = pfade.einstellung_zahl('deckkraft_prozent', 93, 30, 100)
MAX_ROWS = 200          # so viele Neuzugänge max. in der Liste behalten

# --- Katalog-Wache (ab v1.3.0) ---------------------------------------------
# `bp_item_types.json` listet, was im Spiel überhaupt craftbar ist. Der Launcher
# frischt sie mit den SC-Patches auf. Wächst sie, ist etwas NEU craftbar geworden —
# unabhängig davon, ob man es freigeschaltet hat. Der Stand liegt bewusst in einer
# eigenen Datei, damit ein zweites Werkzeug auf denselben Daten dem Watcher
# nicht die Meldung wegnimmt.
APP_DIR    = pfade.app_ordner()
CAT_SEEN   = pfade.app_datei('catalog-seen.json')
# Optionale Beobachtungsliste: Gegenstände, auf die man besonders wartet.
# Format: {"eintraege": [{"titel": "…", "muster": ["teilstring", …]}, …]} — Muster
# kleingeschrieben, Treffer per Teilstring. Fehlt die Datei, meldet der Watcher
# einfach jeden Katalog-Zuwachs.
WATCHLIST  = pfade.app_datei('watchlist.json')
CAT_POLL   = 60         # Katalogdatei nur jede Minute prüfen (ändert sich nur bei Patches)

# --- scmdb-Craftdaten (ab v1.5.0) ------------------------------------------
# Woher Art, Größe, Gütegrad und Klasse kommen, wenn der Launcher-Katalog sie
# nicht kennt (oder gar nicht da ist). scmdb.net liefert je Spielversion eine
# fertige Datei mit genau diesen Werten — kein Entpacken von `Data.p4k` nötig,
# reines urllib aus der Standardbibliothek.
#
#   versions.json                        -> welche Spielversion ist aktuell
#   crafting_items-<version>.json        -> name, attachType, size, grade,
#                                           componentClass, manufacturer
#
# RANGFOLGE (wichtig): bp-overrides.json  >  Launcher-Katalog/Spieldaten  >  scmdb.
# scmdb füllt nur Lücken und überschreibt nie. Grund: Am 11.08.2026 verglichen —
# 55 von 56 Werten stimmen exakt mit dem überein, was das Spiel selbst in die
# Log schreibt, aber beim Kühler „Elsen" nennt scmdb Grad A, während Log UND
# `components.ini` übereinstimmend B sagen (auch der Hersteller ist dort falsch).
# Eine sehr gute Quelle, aber keine unfehlbare.
SCMDB_BASE     = 'https://scmdb.net/data'
SCMDB_CACHE    = pfade.app_datei('scmdb-items.json')   # aufbereitet, klein
SCMDB_POLL_SEC = 6 * 3600    # nur alle 6 Stunden nach einer neuen Spielversion sehen
SCMDB_TIMEOUT  = 30
# Wer die Netzabfrage nicht will, setzt SC_BP_NO_NET=1 — dann bleibt alles beim
# Launcher-Katalog wie bisher.
SCMDB_AUS      = os.environ.get('SC_BP_NO_NET', '') not in ('', '0')
# Gütegrad steht bei scmdb als Zahl. Zuordnung am 11.08.2026 gegen 56 Log-Zeilen
# geprüft: A=1 (21x), B=2 (20x), C=3 (7x), D=4 (7x).
GRADE_LETTER = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}

# Fenstergröße beim allerersten Start. **Ohne feste Position**: Wo das Fenster
# gut aufgehoben ist, hängt am Monitoraufbau, und eine Position vom Rechner des
# Entwicklers ist auf einem anderen im besten Fall unsichtbar — unter macOS
# stürzt Tk dabei sogar ab. Tk sucht sich beim ersten Mal selbst eine Stelle,
# danach gilt die zuletzt gemerkte (siehe `geometrie_pruefen`).
# Wer sie fest vorgeben will, setzt SC_BP_GEOMETRIE (Format BxH+X+Y).
DEFAULT_GEOM  = os.environ.get('SC_BP_GEOMETRIE') or '440x1000'
SETTINGS_FILE = pfade.app_datei('watcher.json')

# Farben (dunkles Overlay)
# Xharig-Grün für dunklen Grund. Bis v1.5.0 stand hier noch #47aa42 — die alte
# Markenfarbe von vor dem Logo-Wechsel. Zwei Grüntöne im selben Programm gehen nicht.
BG, FG, ACCENT, SUB, BAR = '#10141c', '#e6edf3', '#9ce430', '#8b98a5', '#1b2230'
PROV = '#d8a03a'        # Gelb für „vorläufig" (aus der Game.log, noch nicht vom Launcher bestätigt)
CATA = '#4aa3d8'        # Blau für „neu im Spiel craftbar" (Katalog-Zuwachs, kein eigener Fund)


# ---------------------------------------------------------------- Daten-Helfer
def load_keys():
    """Liest die freigeschalteten BP-Namen. Gibt set() zurück (leer bei Fehler)."""
    try:
        with open(BP_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return {b['key'] for b in data.get('blueprints', [])}
    except Exception:
        return None   # None = Datei (gerade) nicht lesbar -> Tick überspringen


def load_types():
    """Was im Spiel überhaupt craftbar ist: Name -> Art.

    Erste Wahl ist die Launcher-Datei (deutsche Bezeichnungen, gepflegt). Fehlt
    der Launcher — unter Linux immer —, treten die scmdb-Craftdaten an ihre
    Stelle. Ohne diesen Rückfall wäre die Katalog-Wache dort tot, dabei liegen
    die Daten längst im Zwischenspeicher."""
    try:
        with open(TYPE_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        pass
    return {name: (eintrag.get('art') or eintrag.get('attachType') or '—')
            for name, eintrag in (SCMDB or {}).items()} if SCMDB else {}


# Die Merkliste steckt in `scbp/merkliste.py` — sie wird im Fenster per Klick
# gepflegt, nicht mehr nur von Hand in der Datei.


# Vorbelegung, damit `load_types()` weiter unten nicht ins Leere greift: Die
# scmdb-Daten werden erst nach diesen Zeilen geladen (sie brauchen Funktionen,
# die weiter unten stehen). Direkt danach wird TYPES neu gesetzt.
SCMDB, SCMDB_VERSION = {}, ''
TYPES = load_types()


def art_of(key):
    global TYPES
    k = key.lower().replace('\xa0', ' ')
    art = TYPES.get(k)
    if art is None:
        # Frisch freigeschaltetes Item kann neu im Katalog sein -> einmal nachladen
        TYPES = load_types()
        art = TYPES.get(k)
    if art is None:
        art = scmdb_art(key)      # ab v1.5.0: Rückfall auf die scmdb-Craftdaten
    return art or '—'


# Rüstungs-Slots von scmdb -> die des Autors: Begriffe. Die Gewichtsklasse (Heavy/Medium/
# Light) steht bei scmdb getrennt in `attachSubType`, beim Launcher steckt sie im
# Begriff selbst („Heavy Armor"). Beides wird hier wieder zusammengesetzt.
_SCMDB_SLOT = {
    'Char_Armor_Helmet':    'Helmet',
    'Char_Armor_Torso':     'Armor',
    'Char_Armor_Legs':      'Armor',
    'Char_Armor_Arms':      'Armor',
    'Char_Armor_Backpack':  'Backpack',
    'Char_Armor_Undersuit': 'Undersuit',
}
# Reine Umbenennungen, wo scmdb zusammenschreibt und der Launcher trennt.
_SCMDB_ART = {
    'QuantumDrive':   'Quantum Drive',
    'PowerPlant':     'Power Plant',
    'WeaponGun':      'Ship Weapon',
    'WeaponPersonal': 'FPS Weapon',
    'WeaponMining':   'Mining Laser',
    'SalvageModifier': 'Salvage Modifier',
}


def scmdb_art(key):
    """Art aus den scmdb-Craftdaten, auf die Begriffe des Launchers gebracht.
    Nur Rückfall — der Launcher-Katalog ist bei Schiffswaffen feiner (er kennt
    `Laser Cannon`, scmdb nur `WeaponGun`)."""
    e = scmdb_of(key)
    if not e or not e.get('a'):
        return None
    a = e['a']
    slot = _SCMDB_SLOT.get(a)
    if slot:
        gewicht = (e.get('sub') or '').strip()
        return ('%s %s' % (gewicht, slot)).strip() if gewicht in (
            'Heavy', 'Medium', 'Light') else slot
    return _SCMDB_ART.get(a, a)


# ------------------------------------------------ Size / Grade / Klasse (M/A/1)
# Ableitung: Launcher-Katalog +
# manuelle Overrides (bp-overrides.json, Vorrang). Ausgabe-Kürzel: Klasse/Grade/Size,
# z. B. Military / Grade A / Size 1  ->  "M/A/1". Nur Size (Waffen) -> "–/–/2".
CLASS_LETTER = {'Military': 'M', 'Stealth': 'S', 'Industrial': 'I',
                'Civilian': 'C', 'Competition': 'K'}
_CLASS_FULL  = {'Civ': 'Civilian', 'Mil': 'Military', 'Ind': 'Industrial',
                'Sth': 'Stealth', 'Cmp': 'Competition'}
_CLASS_SHORT = {v: k for k, v in _CLASS_FULL.items()}


def _norm(s):
    return s.lower().replace('\xa0', ' ').replace('�', ' ').strip()


def load_display():
    """Kleingeschriebener Katalog-Schlüssel -> Schreibweise wie im Spiel.
    `bp_item_types.json` führt alles klein; für die Anzeige holen wir den echten
    Namen aus dem Launcher-Katalog. Wird nur bei einem Katalog-Zuwachs gebraucht."""
    d = {}
    try:
        for line in open(os.path.join(CAT_DIR, 'components.ini'), encoding='utf-8'):
            if '=' not in line: continue
            v = line.strip().split('=', 1)[1]
            m = re.match(r'(.*?)\s*\([^/]+/[^/]+/[^)]+\)', v)
            if m: d.setdefault(_norm(m.group(1)), m.group(1).strip())
    except Exception:
        pass
    try:
        for line in open(os.path.join(CAT_DIR, 'items_raw.ini'), encoding='utf-8'):
            if '=' not in line: continue
            k, v = line.split('=', 1); v = v.strip()
            if k.endswith('_short') or not v: continue
            d.setdefault(_norm(v), v)
    except Exception:
        pass
    return d


def load_meta():
    """comp[name] = (Klasse, Size, Grade) für Schiffskomponenten;
    size_by_name[name] = Size für Waffen/Werkzeuge. Katalog + Overrides (Vorrang)."""
    comp, size_by_name = {}, {}
    # Schiffskomponenten aus components.ini:  "Name (Klasse/Size/Grade)"
    try:
        for line in open(os.path.join(CAT_DIR, 'components.ini'), encoding='utf-8'):
            if '=' not in line: continue
            _, v = line.strip().split('=', 1)
            m = re.search(r'^(.*?)\s*\(([^/]+)/([^/]+)/([^)]+)\)', v)
            if m: comp[m.group(1).strip().lower()] = (m.group(2), m.group(3), m.group(4))
    except Exception:
        pass
    # Size aus items_raw.ini:  Schlüssel enthält _S1 / _S01 …
    try:
        for line in open(os.path.join(CAT_DIR, 'items_raw.ini'), encoding='utf-8'):
            line = line.rstrip('\n')
            if '=' not in line: continue
            k, v = line.split('=', 1)
            if k.endswith('_short'): continue
            m = re.search(r'_S0?(\d)\b', k)
            if m: size_by_name.setdefault(v.strip().lower(), m.group(1))
    except Exception:
        pass
    # Manuelle Overrides (Vorrang): vollständige Komponente -> comp, nur Size -> size_by_name
    try:
        ov = json.load(open(OVERRIDES_FILE, encoding='utf-8')).get('overrides', {})
        for k, o in ov.items():
            if o.get('class') and o.get('size') and o.get('grade'):
                comp[k] = (_CLASS_SHORT.get(o['class'], o['class']), str(o['size']), o['grade'])
            elif o.get('size') is not None:
                size_by_name[k] = str(o['size'])
    except Exception:
        pass
    return comp, size_by_name


COMP, SIZE_BY_NAME = load_meta()


# ------------------------------------------------------- scmdb-Craftdaten (v1.5.0)
def _scmdb_key(s):
    """Vergleichsschlüssel: nur Buchstaben und Ziffern. Fängt typografische
    Anführungszeichen und geschützte Leerzeichen mit ab, an denen ein reiner
    Kleinschreib-Vergleich sonst scheitert."""
    return re.sub(r'[^a-z0-9]', '', ' '.join(str(s or '').split()).lower())


def _scmdb_hole(url, timeout=SCMDB_TIMEOUT):
    # Ehrliche Kennung mit Projektadresse: Der Betreiber von scmdb.net soll im
    # Protokoll sehen können, welches Werkzeug da abruft und wo er nachfragen
    # kann. Kostet nichts und ist schlicht anständig.
    import urllib.request
    kennung = 'SC-BP-Watcher/%s (+https://github.com/Xharig-1/SC-BP-Watcher)' % __version__
    req = urllib.request.Request(url, headers={'User-Agent': kennung})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def load_scmdb():
    """Liest den aufbereiteten Zwischenspeicher. Gibt (items, version) zurück."""
    try:
        with open(SCMDB_CACHE, encoding='utf-8') as f:
            d = json.load(f)
        return d.get('items', {}), d.get('version', '')
    except Exception:
        return {}, ''


def scmdb_aktualisieren():
    """Holt die Craftdaten, wenn eine neue Spielversion da ist. Gibt True zurück,
    wenn der Zwischenspeicher erneuert wurde. Wirft nie — ohne Netz bleibt der
    letzte Stand gültig, ohne Zwischenspeicher läuft alles wie vor v1.5.0."""
    if SCMDB_AUS:
        return False
    try:
        versionen = _scmdb_hole(SCMDB_BASE + '/versions.json', timeout=10)
        live = next((v for v in versionen
                     if 'ptu' not in (v.get('version') or '').lower()), None)
        if not live:
            return False
        version = live.get('version') or ''
        if not version or version == load_scmdb()[1]:
            return False          # schon aktuell
        roh = _scmdb_hole('%s/crafting_items-%s.json' % (SCMDB_BASE, version))
        items = {}
        for e in roh.get('items', []):
            name = e.get('name')
            if not name:
                continue
            items.setdefault(_scmdb_key(name), {
                'n': name,
                'a': e.get('attachType') or e.get('cgItemType'),
                'sub': e.get('attachSubType'),   # Heavy/Medium/Light bei Rüstung
                's': e.get('size'),
                'g': e.get('grade'),
                'c': e.get('componentClass'),
                'm': e.get('manufacturer'),
            })
        os.makedirs(APP_DIR, exist_ok=True)
        with open(SCMDB_CACHE, 'w', encoding='utf-8') as f:
            json.dump({'version': version, 'geholt': time.strftime('%Y-%m-%d %H:%M'),
                       'items': items}, f, ensure_ascii=False)
        return True
    except Exception:
        return False


SCMDB, SCMDB_VERSION = load_scmdb()
# Jetzt, wo die scmdb-Daten stehen, kann der Katalog auch ohne Launcher gefüllt
# werden — vorhin war er es nur, wenn die Launcher-Datei da war.
if not TYPES:
    TYPES = load_types()


def scmdb_of(key):
    """Eintrag aus den scmdb-Craftdaten oder None. Skin-/Sondervarianten mit
    Zusatzname in "…" fallen auf den Grundnamen zurück (wie beim Katalog)."""
    if not SCMDB:
        return None
    e = SCMDB.get(_scmdb_key(key))
    if e is None:
        basis = re.sub(r'\s*"[^"]*"\s*', ' ', str(key))
        if basis != key:
            e = SCMDB.get(_scmdb_key(basis))
    return e


def _size_grade_class(key):
    lk = _norm(key)
    if lk in COMP:
        cl, sz, gr = COMP[lk]
        return sz, gr, _CLASS_FULL.get(cl, cl)
    s = SIZE_BY_NAME.get(lk) or SIZE_BY_NAME.get(key.lower())
    if s is None:  # Skin-/Sondervariante (Zusatz in "…") erbt die Size der Basis
        base = re.sub(r'\s+', ' ', re.sub(r'\s*"[^"]*"\s*', ' ', lk)).strip()
        if base != lk: s = SIZE_BY_NAME.get(base)
    # Rückfall auf scmdb — füllt nur, was die Spieldaten nicht hergeben.
    #
    # ACHTUNG: scmdb vergibt `size` und `grade` an JEDEN Gegenstand, auch an
    # Rüstung und FPS-Waffen, wo beides bedeutungslos ist (ein Helm als „Grade A,
    # Size 1"). Ungefiltert übernommen stünde hinter jedem Rüstungsteil ein
    # erfundenes Kürzel. Deshalb:
    #   * Klasse/Gütegrad nur, wenn scmdb eine `componentClass` führt — das sind
    #     genau die echten Schiffskomponenten (489 von 1591).
    #   * Größe zusätzlich für Schiffswaffen, die haben eine, aber keinen Grad.
    #   * Rüstung, FPS-Waffen, Kleidung: nichts.
    e = scmdb_of(key)
    if e:
        if e.get('c'):                                   # echte Schiffskomponente
            if s is None and e.get('s') is not None:
                s = str(e['s'])
            return s, GRADE_LETTER.get(e.get('g')), e.get('c')
        if e.get('a') == 'WeaponGun' and s is None and e.get('s') is not None:
            s = str(e['s'])                              # Schiffswaffe: nur Größe
    return s, None, None


def meta_of(key):
    """Kürzel Klasse/Grade/Size, z. B. 'M/A/1'. '' wenn nichts bekannt (FPS-Waffe,
    Rüstung). Fehlende Einzelwerte werden als '–' angezeigt."""
    sz, gr, cl = _size_grade_class(key)
    if sz is None and gr is None and cl is None:
        return ''
    c = CLASS_LETTER.get(cl, '–') if cl else '–'
    return f'{c}/{gr or "–"}/{sz or "–"}'


# ------------------------------------------------------- Game.log (Sofort-Meldung)
# Das Lesen der Log steckt seit v1.6 in `scbp/logquelle.py` — samt Nachlese der
# aufgehobenen Sitzungen und einem Lesestand, der Programmneustarts übersteht.
# Welche Formulierung im Log steht, hängt an der Spielsprache; darum kümmert
# sich `scbp/phrasen.py`. Hier bleibt nur, was mit der ANZEIGE zu tun hat.


def kuerzel_aus_zusatz(zusatz):
    """('Civ', '3', 'A') -> 'C/A/3'.

    Der Zusatz hinter dem Namen im Log ist der Rückfall fürs Kürzel, falls ein
    Gegenstand nach einem SC-Patch noch in keinem Katalog steht."""
    if not zusatz:
        return None
    klasse, size, grade = zusatz
    letter = CLASS_LETTER.get(_CLASS_FULL.get(klasse, klasse), '–')
    return f'{letter}/{grade}/{size}'


def _loose(name):
    """Name ohne Klammer-Zusatz am Ende — für den Notfall-Abgleich, wenn Log und
    Launcher unterschiedlich übersetzt sind (gesehen: „Scalpel Sniper Rifle Magazine
    (12 Schuss)" im Log vs. „… (12 cap)" beim Launcher)."""
    return re.sub(r'\s*\([^()]*\)\s*$', '', _norm(name)).strip()



# ------------------------------------------------ Fensterposition merken/laden
def load_geometry():
    try:
        g = json.load(open(SETTINGS_FILE, encoding='utf-8')).get('geometry')
        return g or DEFAULT_GEOM
    except Exception:
        return DEFAULT_GEOM


GEOM_RE = re.compile(r'^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$')


def geometrie_pruefen(geom, root):
    """Liegt die gemerkte Fensterlage auf diesem Rechner überhaupt im Bild?

    Der Watcher speichert seine Lage, damit er beim nächsten Mal wieder dort
    steht — bei der Autor auf dem oberen von drei Monitoren, also bei X≈3656 und
    negativem Y. Auf einem Rechner mit einem einzigen Bildschirm zeigt dieselbe
    Angabe ins Nichts: Das Fenster ist unsichtbar, unter macOS reißt Tk sogar
    das ganze Programm mit. Sobald die Fassung öffentlich wird, landet sie auf
    genau solchen Rechnern.

    Geprüft wird **großzügig**: Mehrere Monitore sollen weiter funktionieren
    (Tk kennt oft nur den Hauptbildschirm), es geht nur darum, offensichtlichen
    Unsinn abzufangen. Passt die Lage nicht, bleibt die Größe erhalten und nur
    die Position fällt weg — Tk platziert das Fenster dann selbst."""
    m = GEOM_RE.match(geom or '')
    if not m:
        return DEFAULT_GEOM
    breite, hoehe, x, y = m.groups()
    if x is None:
        return geom
    # macOS ist kein Zielsystem (Star Citizen gibt es dort nicht), aber am Mac
    # wird geplant und entwickelt. Tk rechnet dort negative Fensterkoordinaten
    # in einen Unsinnswert um und reißt das Programm mit — deshalb zählt die
    # gemerkte Position dort nicht.
    if sys.platform == 'darwin' and (int(x) < 0 or int(y) < 0):
        return '%sx%s' % (breite, hoehe)
    try:
        sb = max(root.winfo_screenwidth(), root.winfo_vrootwidth())
        sh = max(root.winfo_screenheight(), root.winfo_vrootheight())
    except Exception:
        return geom
    # Bis zum Zweifachen der Bildschirmgröße nach jeder Seite gilt als plausibel:
    # Das deckt übliche Mehrschirm-Aufbauten ab, ohne Fantasiewerte durchzulassen.
    if -2 * sb <= int(x) <= 3 * sb and -2 * sh <= int(y) <= 3 * sh:
        return geom
    return '%sx%s' % (breite, hoehe)


def save_geometry(geom):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        json.dump({'geometry': geom}, open(SETTINGS_FILE, 'w', encoding='utf-8'))
    except Exception:
        pass


# ------------------------------------------------ Mit dem Rechner starten
# Steckt seit v1.6 in `scbp/autostart.py`: unter Windows ein Registry-Wert,
# unter Linux eine `.desktop`-Datei in ~/.config/autostart/.
AUTOSTART_TEXT = ('Mit Windows starten' if pfade.WINDOWS
                  else 'Beim Anmelden starten')


# ------------------------------------------------------------------ Signalton
def signalton(auffaellig=False):
    """Kurzer Ton bei einem Fund.

    Unter Windows `winsound`, unter Linux ein Systemklang über `scbp/ton.py`.

    Bis v2.0.0-rc3 stand hier für Linux nur `bell()` mit der Begründung
    „bleibt es still, ist das kein Fehler". Beim ersten echten Bauplan blieb
    es still, und das **war** ein Fehler: `bell()` ist die X11-Systemglocke,
    die auf modernen Arbeitsplätzen praktisch überall aus ist. `bell()` bleibt
    als letzter Rückfall — schaden kann es nicht."""
    if not TON_AN:
        return
    if winsound:
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION if auffaellig
                                 else winsound.MB_ICONASTERISK)
        except Exception:
            pass
        return
    if ton.abspielen('auffaellig' if auffaellig else 'normal'):
        return
    try:
        _WURZEL[0].bell()
    except Exception:
        pass


# Das Hauptfenster, damit `signalton()` es erreicht, ohne es durchreichen zu müssen.
_WURZEL = [None]



# ---------------------------------------------------------------- Watcher-Thread
class Watcher(threading.Thread):
    def __init__(self, out_queue):
        super().__init__(daemon=True)
        self.q = out_queue
        self.known = None       # BP-Namen aus der Launcher-Datei (None = kein Launcher)
        self.seen = set()       # schon angezeigte Namen (normalisiert) — gegen Dubletten
        self.prov = {}          # noch unbestätigt: norm(Log-Name) -> Log-Name
        self.stand = logquelle.Lesestand()
        self.tail = logquelle.LogTail(self.stand)
        self.bestand = bestand_datei.laden()   # der eigene, dauerhafte Bestand
        self.running = True
        self.cat_next = 0.0     # nächster Katalog-Check (Zeitstempel)
        self.cat_mtime = None   # letzter gesehener Änderungszeitpunkt der Katalogdatei
        self.scmdb_next = 0.0   # nächster Blick auf die scmdb-Craftdaten
        self.kat_next = 0.0     # nächster Blick auf den Bauplan-Katalog
        self.kat_laeuft = False  # holt gerade ein Nebenthread den Katalog?

    # ---- scmdb-Craftdaten frisch halten (ab v1.5.0) ----
    def _scmdb_tick(self):
        """Sieht selten nach, ob eine neue Spielversion vorliegt, und lädt dann die
        Werte-Datei neu. Läuft im Hintergrund-Thread, damit die Oberfläche nicht
        hängt, und schluckt jeden Fehler — ohne Netz bleibt der letzte Stand."""
        global SCMDB, SCMDB_VERSION
        if time.time() < self.scmdb_next:
            return
        self.scmdb_next = time.time() + SCMDB_POLL_SEC
        if scmdb_aktualisieren():
            SCMDB, SCMDB_VERSION = load_scmdb()
            self.q.put(('status', 'scmdb-Craftdaten aktualisiert (%s, %d Gegenstände)'
                        % (SCMDB_VERSION, len(SCMDB))))

    # ---- Bauplan-Katalog holen und frisch halten ----
    def _katalog_tick(self):
        """Holt den Bauplan-Katalog von scmdb, wenn er fehlt oder veraltet ist.

        Bis v2.0.0-rc1 wurde `katalog.aktualisieren()` von **nirgendwo** aufgerufen:
        Der Katalog kam nie an, das Bauplan-Fenster blieb bei jedem Nutzer leer und
        der Hinweistext versprach etwas, das nicht geschah.

        Der Abruf läuft in einem **eigenen** Thread, nicht hier im Watcher-Takt:
        Es sind rund 12 MB, und die Log-Erkennung ist die Kernaufgabe — sie darf
        dafür keine Sekunde stehenbleiben. `kat_laeuft` verhindert, dass bei einer
        langsamen Leitung mehrere Abrufe übereinander laufen."""
        if SCMDB_AUS or self.kat_laeuft or time.time() < self.kat_next:
            return
        self.kat_next = time.time() + SCMDB_POLL_SEC
        self.kat_laeuft = True

        def holen():
            try:
                gab_es_schon = bool(katalog_modul.laden()['bauplaene'])
                if not gab_es_schon:
                    self.q.put(('status', sprache.t('katalog_holt')))
                neu, anzahl, version = katalog_modul.aktualisieren()
                if neu:
                    self.q.put(('status', sprache.t('katalog_geholt', anzahl, version)))
                else:
                    # Nichts zu tun heißt: schon aktuell — oder kein Netz. Im
                    # zweiten Fall bald noch einmal versuchen statt sechs Stunden
                    # warten, sonst bleibt ein kurzer Aussetzer den ganzen Tag hängen.
                    if not gab_es_schon and not katalog_modul.laden()['bauplaene']:
                        self.kat_next = time.time() + 300
            finally:
                self.kat_laeuft = False

        threading.Thread(target=holen, daemon=True).start()

    # ---- Katalog-Wache: was ist NEU craftbar im Spiel? ----
    def _catalog_tick(self):
        """Prüft, ob der Craftbar-Katalog gewachsen ist. Der Vergleichsstand überlebt
        Neustarts (CAT_SEEN), sonst käme nach jedem Programmstart alles doppelt."""
        try:
            marke = os.path.getmtime(TYPE_FILE)
        except OSError:
            # Kein Launcher: Dann ist die Spielversion der scmdb-Daten die Marke.
            # Sie ändert sich genau dann, wenn ein Patch neue Baupläne bringt —
            # also genau dann, wenn nachgesehen werden muss.
            marke = SCMDB_VERSION or None
            if marke is None:
                return
        if marke == self.cat_mtime:
            return
        self.cat_mtime = marke
        jetzt = load_types()
        if not jetzt:
            return
        try:
            with open(CAT_SEEN, encoding='utf-8') as f:
                bekannt = set(json.load(f).get('namen', []))
        except Exception:
            bekannt = set()
        if not bekannt:                       # erster Lauf: nur Basis setzen, nichts melden
            self._save_catalog(jetzt)
            return
        neu = sorted(n for n in jetzt if n not in bekannt)
        if not neu:
            self._save_catalog(jetzt)
            return
        anzeige = load_display()
        for name in neu:
            titel = merkliste.treffer(name)
            self.q.put(('catalog', anzeige.get(_norm(name)) or name.title(),
                        jetzt.get(name) or '—', time.strftime('%H:%M:%S'), titel))
        self._save_catalog(jetzt)

    @staticmethod
    def _save_catalog(jetzt):
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            with open(CAT_SEEN, 'w', encoding='utf-8') as f:
                json.dump({'stand': time.strftime('%Y-%m-%d %H:%M:%S'),
                           'namen': sorted(jetzt)}, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _emit(self, key, provisional, log_meta=None):
        # log_meta = Kürzel aus dem Log-Zusatz; wird nur genommen, wenn der
        # Launcher-Katalog nichts hergibt (brandneues Item nach einem SC-Patch).
        self.q.put(('new', key, art_of(key), meta_of(key) or log_meta or '',
                    time.strftime('%H:%M:%S'), provisional))

    def _match_prov(self, key):
        """Zeile suchen, die diesen Launcher-Schlüssel vorläufig schon anzeigt.
        Erst exakt, dann (nur bei Eindeutigkeit) ohne Klammer-Zusatz."""
        row = self.prov.pop(_norm(key), None)
        if row:
            return row
        hits = [v for k, v in self.prov.items() if _loose(k) == _loose(key)]
        if len(hits) == 1:
            self.prov.pop(_norm(hits[0]), None)
            return hits[0]
        return None

    # ---- Sprache des Spiels erschließen ----
    def _sprache_erschliessen(self):
        """Herausfinden, wie die Bauplan-Meldung in DIESEM Client lautet.

        Nötig, weil die mitgelieferte Tabelle nur Deutsch sicher kennt; die
        englischen Formulierungen sind Kandidaten, und Französisch oder Spanisch
        stehen gar nicht drin. Der Katalog mit über 700 Bauplan-Namen macht es
        möglich: Wer in einer Logzeile einen bekannten Bauplan findet, kennt
        auch den Text davor.

        Läuft nur, solange die Formulierung nicht ohnehin feststeht — und nur
        einmal, denn danach steht sie in `phrasen.json`."""
        try:
            if phrasen.bestaetigt():
                return
            namen = [e['n'] for e in katalog_modul.laden()['bauplaene'].values()]
            if not namen:
                return
            gefunden = phrasen.selbst_finden(namen, pfade.log_sicherungen())
            if gefunden and phrasen.merken(gefunden):
                self.tail.muster = phrasen.muster()
                self.q.put(('hinweis', sprache.t('sprache_erkannt', gefunden)))
        except Exception:
            pass            # ohne Erkennung gilt die mitgelieferte Tabelle

    # ---- Nachlese: was wurde ohne laufenden Watcher freigeschaltet? ----
    def _nachlese(self):
        """Beim Start die aufgehobenen Logs durchsehen und in den Bestand nehmen.

        Bewusst **still**: Es geht um Vergangenes, das gehört nicht als Meldung
        in die Liste — sonst stünden nach jedem Start hunderte Zeilen da. Nur
        die Zahl kommt in die Statuszeile, und eine verbleibende Lücke wird
        deutlich gesagt, damit niemand seinen Bestand für vollständig hält."""
        try:
            funde, bericht = logquelle.nachlesen(self.stand)
        except Exception:
            return
        neu = 0
        for name, _zusatz in funde:
            if bestand_datei.hinzufuegen(self.bestand, name, 'nachlese'):
                neu += 1
        if neu:
            bestand_datei.speichern(self.bestand)
            self.q.put(('status', 'Nachgelesen: %d Baupläne aus %d früheren '
                                  'Sitzungen übernommen.' % (neu, bericht['dateien'])))
        if bericht.get('luecke') and bericht.get('grund'):
            self.q.put(('hinweis', bericht['grund']))

    def _launcher_uebernehmen(self, keys):
        """Was der Launcher kennt, gehört auch in den eigenen Bestand.

        Kein „Import" im Sinne eines einmaligen Grundstocks (den macht das
        Hilfsprogramm unter `tools/`), sondern laufender Betrieb: Er ist die
        genauere Quelle, solange er da ist."""
        neu = 0
        for k in keys:
            if bestand_datei.hinzufuegen(self.bestand, k, 'launcher'):
                neu += 1
        if neu:
            bestand_datei.speichern(self.bestand)
        return neu

    def _katalog_beim_start(self):
        """Fehlt der Katalog ganz, wird er **vor** allem anderen geholt — hier
        ausnahmsweise im Watcher-Takt, nicht nebenher.

        Grund: `_sprache_erschliessen()` braucht die Bauplan-Namen, um aus den
        Logs die Formulierung dieses Clients abzuleiten, und die Nachlese braucht
        diese Formulierung. Käme der Katalog nebenher, liefe beim allerersten
        Start beides ins Leere — bei einem englischen Client hieße das: kein
        einziger Bauplan gefunden, ohne dass jemand den Grund sähe.

        Nur beim ersten Mal. Ist der Katalog da, hält ihn `_katalog_tick()`
        frisch, ohne den Start aufzuhalten."""
        if SCMDB_AUS or katalog_modul.laden()['bauplaene']:
            return
        self.q.put(('status', sprache.t('katalog_holt')))
        try:
            neu, anzahl, version = katalog_modul.aktualisieren()
            if neu:
                self.q.put(('status', sprache.t('katalog_geholt', anzahl, version)))
                self.kat_next = time.time() + SCMDB_POLL_SEC
            else:
                # Kein Netz: bald noch einmal versuchen, statt sechs Stunden warten.
                self.kat_next = time.time() + 300
        except Exception:
            self.kat_next = time.time() + 300

    def run(self):
        # 0) Ohne Bauplan-Namen lässt sich die Spielsprache nicht erschließen —
        #    also zuerst den Katalog, falls er noch gar nicht da ist.
        self._katalog_beim_start()

        # 1) Klären, wonach überhaupt gesucht wird — sonst liest die
        #    Nachlese mit der falschen Formulierung und findet nichts.
        self._sprache_erschliessen()

        # 2) Vergangenes nachlesen (still, nur in den Bestand)
        self._nachlese()

        # 3) Launcher-Stand holen — wenn es ihn gibt. Ohne ihn wird nicht mehr
        #    gewartet: Bis v1.5.0 hing der Watcher hier in einer Endlosschleife,
        #    wenn die Launcher-Datei fehlte. Unter Linux wäre er nie gestartet.
        if HAT_LAUNCHER:
            for _ in range(10):
                if not self.running:
                    return
                self.known = load_keys()
                if self.known is not None:
                    break
                time.sleep(POLL_SEC)
            if self.known:
                self._launcher_uebernehmen(self.known)

        # 4) Alles, was schon im Bestand steht, gilt als bekannt — es wird nicht
        #    als „neu" gemeldet.
        self.seen = set(bestand_datei.schluessel(self.bestand))
        self.tail.new_names()          # Lesestand der Game.log setzen/fortführen
        self.q.put(('status', self._statuszeile()))
        while self.running:
            time.sleep(POLL_SEC)

            # 0) Werte-Daten und Bauplan-Katalog frisch halten
            #    (selten, nur bei neuer Spielversion)
            self._scmdb_tick()
            self._katalog_tick()

            # 1) Game.log: die eigentliche Quelle. Ohne Launcher ist die Meldung
            #    endgültig, mit Launcher zunächst vorläufig (er bestätigt gleich).
            geaendert = False
            for name, zusatz in self.tail.new_names():
                nk = _norm(name)
                if nk in self.seen:
                    continue
                self.seen.add(nk)
                if bestand_datei.hinzufuegen(self.bestand, name, 'log'):
                    geaendert = True
                if HAT_LAUNCHER:
                    self.prov[nk] = name
                self._emit(name, HAT_LAUNCHER, kuerzel_aus_zusatz(zusatz))
                self._merkliste_erledigen(name)
            if geaendert:
                bestand_datei.speichern(self.bestand)

            # 2) Launcher-Datei: bestätigt die Funde und meldet nach, was im Log
            #    fehlte. Gibt es keinen Launcher, entfällt dieser Schritt still.
            cur = load_keys() if HAT_LAUNCHER else None
            if cur is not None:
                zuwachs = False
                for k in sorted(cur - (self.known or set())):
                    row = self._match_prov(k)
                    dup = _norm(k) in self.seen      # steht schon in der Liste
                    self.seen.add(_norm(k))
                    if bestand_datei.hinzufuegen(self.bestand, k, 'launcher'):
                        zuwachs = True
                    self._merkliste_erledigen(k)
                    if row:
                        self.q.put(('confirm', row, k, art_of(k), meta_of(k)))
                    elif not dup:
                        self._emit(k, False)
                if zuwachs:
                    bestand_datei.speichern(self.bestand)
                self.known = cur

            # 3) Katalog-Wache (selten, die Datei ändert sich nur bei SC-Patches)
            if time.time() >= self.cat_next:
                self.cat_next = time.time() + CAT_POLL
                self._catalog_tick()

            self.q.put(('status', self._statuszeile()))

    def _merkliste_erledigen(self, name):
        """Worauf gewartet wurde und was jetzt da ist, fliegt von der Merkliste.

        Eine Liste voller längst erfüllter Wünsche wäre keine Merkliste, sondern
        ein Archiv. Der Watcher sagt einmal Bescheid, dann ist es erledigt."""
        try:
            titel = merkliste.erledigen(name)
        except Exception:
            return
        if titel:
            self.q.put(('hinweis', sprache.t('merk_erledigt', titel)))

    def _statuszeile(self):
        """Was unten im Fenster steht. Zeigt den **eigenen** Bestand — nicht mehr
        die Launcher-Zahl, denn der Launcher ist ab jetzt nur noch eine von
        mehreren Quellen (und zählt nachweislich zu niedrig)."""
        log_state = '✓' if self.tail.path else '–'
        quelle = 'Launcher ✓' if (HAT_LAUNCHER and self.known) else 'ohne Launcher'
        return ('%d Baupläne · Log %s · %s · geprüft %s'
                % (bestand_datei.anzahl(self.bestand), log_state, quelle,
                   time.strftime('%H:%M:%S')))

    def stop(self):
        self.running = False


# ---------------------------------------------------------------- GUI / Overlay
# Mauszeiger heißen je Fenstersystem anders. `size_nw_se` gibt es nur unter
# Windows — unter Linux und macOS wirft tkinter dafür einen Fehler und das
# Fenster kommt gar nicht erst hoch. `hand2` dagegen kennen alle drei.
CURSOR_GROESSE = 'size_nw_se' if pfade.WINDOWS else 'bottom_right_corner'


def sicherer_cursor(name):
    """Gibt den Zeigernamen zurück, wenn dieses System ihn kennt — sonst ''.

    Geprüft wird an einem Wegwerf-Widget: Das ist der einzige verlässliche Weg,
    weil die Namensliste von der Tk-Fassung abhängt, nicht nur vom System."""
    try:
        probe = tk.Label(None, cursor=name)
        probe.destroy()
        return name
    except Exception:
        return ''



class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        _WURZEL[0] = self.root                    # damit signalton() klingeln kann
        self.root.title('SC BP Watcher')
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)          # randloses Overlay
        self.root.attributes('-topmost', True)    # immer im Vordergrund
        # Durchsichtigkeit einstellbar (30–100 %). Wer nur **einen** Monitor hat,
        # legt das Overlay zwangsläufig übers Spiel — dann muss man hindurchsehen
        # können. 93 % bleibt der Standard, das ist auf zwei Bildschirmen richtig.
        self.root.attributes('-alpha', DECKKRAFT / 100.0)
        self.root.geometry(geometrie_pruefen(load_geometry(), self.root))
        # Fenster-/Taskleisten-Icon setzen, falls icon.ico daneben liegt
        try:
            ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except Exception:
            pass
        self.count = 0
        self.rows = {}          # normalisierter Name -> Zeilen-Widgets (für die Bestätigung)

        self.f_title = tkfont.Font(family='Segoe UI Semibold', size=10)
        self.f_item  = tkfont.Font(family='Consolas', size=9)
        self.f_sub   = tkfont.Font(family='Segoe UI', size=8)

        # --- Titelleiste (Drag-Griff + Schließen) ---
        bar = tk.Frame(self.root, bg=BAR, height=26)
        bar.pack(fill='x', side='top')
        bar.pack_propagate(False)
        titel_lbl = tk.Label(bar, text=f'● SC BP Watcher v{__version__}', bg=BAR,
                             fg=ACCENT, font=self.f_title)
        titel_lbl.pack(side='left', padx=8)
        hinweis.anhaengen(titel_lbl, lambda: sprache.t('hinweis_ziehen'))
        zu_lbl = tk.Label(bar, text='✕', bg=BAR, fg=SUB, font=self.f_title,
                          cursor='hand2')
        zu_lbl.pack(side='right', padx=8)
        zu_lbl.bind('<Button-1>', lambda e: self.quit())
        hinweis.anhaengen(zu_lbl, lambda: sprache.t('hinweis_schliessen'))
        leeren_lbl = tk.Label(bar, text='🗑', bg=BAR, fg=SUB, font=self.f_title,
                              cursor='hand2')
        leeren_lbl.pack(side='right')
        leeren_lbl.bind('<Button-1>', lambda e: self.clear())
        hinweis.anhaengen(leeren_lbl, lambda: sprache.t('hinweis_leeren'))
        # Schalter „mit Windows starten" — grün = an, grau = aus.
        self.as_lbl = tk.Label(bar, text='⏻', bg=BAR, fg=SUB, font=self.f_title,
                               cursor='hand2')
        self.as_lbl.pack(side='right', padx=(0, 6))
        # Zwei Ansichten, ein Programm: die schmale Melde-Leiste bleibt, das
        # Verwaltungsfenster kommt auf Klick dazu.
        self.liste_lbl = tk.Label(bar, text='☰', bg=BAR, fg=SUB,
                                  font=self.f_title, cursor='hand2')
        self.liste_lbl.pack(side='right', padx=(0, 6))
        self.liste_lbl.bind('<Button-1>', lambda e: self.liste_oeffnen())
        hinweis.anhaengen(self.liste_lbl, lambda: sprache.t('hinweis_liste'))
        # Einrichtung erneut — bewusst als eigener Knopf und nicht in einem
        # Einstellungsmenü versteckt: Wer sich nicht auskennt, soll etwas
        # nachstellen können, ohne zu wissen, wo es steckt.
        self.assi_lbl = tk.Label(bar, text='⟳', bg=BAR, fg=SUB,
                                 font=self.f_title, cursor='hand2')
        self.assi_lbl.pack(side='right', padx=(0, 6))
        self.assi_lbl.bind('<Button-1>', lambda e: self.einrichtung_erneut())
        hinweis.anhaengen(self.assi_lbl, lambda: sprache.t('hinweis_assistent'))
        # Zwei Wege zum selben Ziel, absichtlich beide da: der Assistent führt
        # Schritt für Schritt (wer nicht weiß, dass es das gibt), das Zahnrad
        # ist der direkte Griff für alle fünf Felder auf einmal (wer genau
        # weiß, was er ändern will). Bis hierher gab es nur den Assistenten —
        # gemeldet als „ich finde den Einstellungs-Button gar nicht".
        self.einst_lbl = tk.Label(bar, text='⚙', bg=BAR, fg=SUB,
                                  font=self.f_title, cursor='hand2')
        self.einst_lbl.pack(side='right', padx=(0, 6))
        self.einst_lbl.bind('<Button-1>', lambda e: self.einstellungen_oeffnen())
        hinweis.anhaengen(self.einst_lbl, lambda: sprache.t('hinweis_einstellungen'))
        # „Was ist neu" — färbt sich grün, sobald es eine neuere Fassung gibt.
        self.info_lbl = tk.Label(bar, text='ⓘ', bg=BAR, fg=SUB,
                                 font=self.f_title, cursor='hand2')
        self.info_lbl.pack(side='right', padx=(0, 6))
        self.info_lbl.bind('<Button-1>', lambda e: self.versionen_zeigen())
        hinweis.anhaengen(self.info_lbl, self._hinweis_info)
        self.as_lbl.bind('<Button-1>', lambda e: self._toggle_autostart())
        hinweis.anhaengen(self.as_lbl, self._hinweis_autostart)
        self._show_autostart()
        for w in (bar, bar.winfo_children()[0]):
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)
            w.bind('<ButtonRelease-1>', self._save_geo)   # Position nach dem Ziehen merken

        # --- Statuszeile ---
        self.status = tk.Label(self.root, text='Starte …', bg=BG, fg=SUB,
                               font=self.f_sub, anchor='w')
        self.status.pack(fill='x', padx=8, pady=(4, 2))

        # --- Liste (scrollbar) ---
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill='both', expand=True, padx=6, pady=(0, 6))
        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient='vertical', command=self.canvas.yview)
        self.list = tk.Frame(self.canvas, bg=BG)
        self.list.bind('<Configure>',
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        # Die Liste muss so breit sein wie das Fenster. Bis v1.2.0 stand hier ein fester
        # Wert (312 px) — dadurch wurden lange Namen abgeschnitten und Breiterziehen
        # brachte nichts. Jetzt wird die Breite bei jeder Größenänderung nachgezogen.
        self._list_id = self.canvas.create_window((0, 0), window=self.list, anchor='nw', width=312)
        self._wrap_labels = []          # Untertitel, die umbrechen dürfen
        self.canvas.bind('<Configure>', self._fit_width)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self._placeholder()

        # Resize-Griff unten rechts
        grip = tk.Label(self.root, text='◢', bg=BG, fg=SUB,
                        cursor=sicherer_cursor(CURSOR_GROESSE))
        grip.place(relx=1.0, rely=1.0, anchor='se')
        grip.bind('<B1-Motion>', self._resize)
        grip.bind('<ButtonRelease-1>', self._save_geo)    # Größe nach dem Skalieren merken
        hinweis.anhaengen(grip, lambda: sprache.t('hinweis_groesse'))

        # Watcher starten
        self.q = queue.Queue()
        self.watcher = Watcher(self.q)
        self.watcher.start()
        self.root.after(200, self._poll_queue)
        self.root.after(2000, self._nach_version_sehen)   # nicht beim Start drängeln

    # ---- Drag & Resize ----
    # ---- Schalter „mit dem Rechner starten" ----
    # ---- Erklärtexte, die ihren Zustand kennen ----
    def _hinweis_autostart(self):
        """⏻ sagt an, was ein Klick bewirkt — nicht nur, was das Zeichen bedeutet.

        Die Farbe zeigt den Zustand, aber nur wer das Programm kennt, weiß das.
        Also ausschreiben: was gerade gilt und was der Klick daraus macht."""
        return sprache.t('hinweis_autostart_an' if autostart.ist_an()
                         else 'hinweis_autostart_aus')

    def _hinweis_info(self):
        """ⓘ heißt zweierlei — Versionsgeschichte, und bei Grün: „es gibt Neues"."""
        grün = str(self.info_lbl.cget('fg')).lower() == ACCENT.lower()
        return sprache.t('hinweis_neue_version' if grün else 'hinweis_versionen')

    def _show_autostart(self):
        an = autostart.ist_an()
        self.as_lbl.config(fg=ACCENT if an else SUB)
        # Kein echtes Kurzinfo-Fenster in der Standardbibliothek — der Text in der
        # Statuszeile beim Umschalten reicht, und die Farbe zeigt den Zustand.
        return an

    def _toggle_autostart(self):
        neu = not autostart.ist_an()
        if autostart.setzen(neu):
            self._show_autostart()
            self.status.config(text='%s: %s' % (AUTOSTART_TEXT,
                                                'an' if neu else 'aus'))
        else:
            self.status.config(text='Autostart ließ sich nicht ändern.')

    def _drag_start(self, e): self._dx, self._dy = e.x, e.y
    def _drag_move(self, e):
        self.root.geometry(f'+{self.root.winfo_x()+e.x-self._dx}+{self.root.winfo_y()+e.y-self._dy}')
    def _resize(self, e):
        w = max(260, self.root.winfo_pointerx() - self.root.winfo_x())
        h = max(160, self.root.winfo_pointery() - self.root.winfo_y())
        self.root.geometry(f'{w}x{h}')

    # ---- Liste ----
    def _fit_width(self, e=None):
        """Listenbreite an die Fensterbreite koppeln und lange Untertitel neu umbrechen."""
        w = e.width if e is not None else self.canvas.winfo_width()
        if w < 2:
            return
        self.canvas.itemconfigure(self._list_id, width=w)
        self._wrap_labels = [lb for lb in self._wrap_labels if lb.winfo_exists()]
        for lb in self._wrap_labels:
            lb.config(wraplength=max(160, w - 40))

    def _placeholder(self):
        self._ph = tk.Label(self.list, text='Warte auf neue Baupläne …',
                            bg=BG, fg=SUB, font=self.f_sub)
        self._ph.pack(anchor='w', padx=4, pady=6)

    def clear(self):
        for w in self.list.winfo_children():
            w.destroy()
        self.rows.clear()
        self.count = 0
        self._placeholder()

    @staticmethod
    def _sub_text(art, meta, ts, provisional):
        parts = [p for p in (art, meta) if p]
        parts.append(ts)
        if provisional:
            parts.append('vorläufig')
        return ' · '.join(parts)

    def add_new(self, key, art, meta, ts, provisional):
        if self.count == 0 and hasattr(self, '_ph') and self._ph.winfo_exists():
            self._ph.destroy()
        self.count += 1
        nk = _norm(key)
        top = self.list.pack_slaves()          # aktuell oberste Zeile (Reihenfolge im Fenster!)
        row = tk.Frame(self.list, bg=BG)
        row.pack(fill='x', anchor='w', padx=2, pady=1)
        dot = tk.Label(row, text='🟡' if provisional else '🟢', bg=BG, font=self.f_item)
        dot.pack(side='left')
        txt = tk.Frame(row, bg=BG); txt.pack(side='left', fill='x', expand=True)
        name = tk.Label(txt, text=key, bg=BG, fg=FG, font=self.f_item,
                        anchor='w', justify='left')
        name.pack(fill='x', anchor='w')
        sub = tk.Label(txt, text=self._sub_text(art, meta, ts, provisional), bg=BG,
                       fg=PROV if provisional else SUB, font=self.f_sub, anchor='w')
        sub.pack(fill='x', anchor='w')
        row._bpkey = nk
        self.rows[nk] = {'frame': row, 'dot': dot, 'name': name, 'sub': sub, 'ts': ts}
        # neueste oben einsortieren. WICHTIG: pack_slaves() (= Reihenfolge im Fenster),
        # nicht winfo_children() (= Reihenfolge der Erzeugung) — sonst landen neue
        # Zeilen unter den älteren (Fehler bis v1.1.0).
        if top:
            row.pack_configure(before=top[0])
        self._trim()
        self.canvas.yview_moveto(0)
        signalton()

    def add_hinweis(self, text):
        """Eine Zeile, die keine Freischaltung meldet, sondern etwas erklärt —
        derzeit nur: „im Bestand fehlt möglicherweise etwas".

        Kein Signalton, kein Ausrufezeichen: Es ist eine Information beim Start,
        keine Neuigkeit aus dem Spiel."""
        if self.count == 0 and hasattr(self, '_ph') and self._ph.winfo_exists():
            self._ph.destroy()
        self.count += 1
        top = self.list.pack_slaves()
        row = tk.Frame(self.list, bg=BG)
        row.pack(fill='x', anchor='w', padx=2, pady=1)
        tk.Label(row, text='ℹ', bg=BG, fg=SUB, font=self.f_item).pack(side='left')
        lbl = tk.Label(row, text=text, bg=BG, fg=SUB, font=self.f_sub,
                       anchor='w', justify='left')
        lbl.pack(side='left', fill='x', expand=True, anchor='w')
        self._wrap_labels.append(lbl)
        self._fit_width()
        row._bpkey = None
        if top:
            row.pack_configure(before=top[0])
        self._trim()
        self.canvas.yview_moveto(0)

    def add_catalog(self, name, art, ts, titel):
        """Katalog-Zuwachs: im Spiel ist etwas NEU craftbar (nicht: selbst freigeschaltet).
        `titel` gesetzt = Treffer aus der Beobachtungsliste → auffällig in Gold."""
        if self.count == 0 and hasattr(self, '_ph') and self._ph.winfo_exists():
            self._ph.destroy()
        self.count += 1
        top = self.list.pack_slaves()
        row = tk.Frame(self.list, bg=BG)
        row.pack(fill='x', anchor='w', padx=2, pady=1)
        tk.Label(row, text='⭐' if titel else '🔵', bg=BG, font=self.f_item).pack(side='left')
        txt = tk.Frame(row, bg=BG); txt.pack(side='left', fill='x', expand=True)
        tk.Label(txt, text=name, bg=BG, fg=PROV if titel else FG, font=self.f_item,
                 anchor='w', justify='left').pack(fill='x', anchor='w')
        unten = f'{titel} — jetzt craftbar!' if titel else 'neu im Spiel craftbar'
        # Titel aus der Beobachtungsliste können lang sein -> umbrechen statt abschneiden
        sub = tk.Label(txt, text=' · '.join(x for x in (unten, art, ts) if x), bg=BG,
                       fg=PROV if titel else CATA, font=self.f_sub, anchor='w', justify='left')
        sub.pack(fill='x', anchor='w')
        self._wrap_labels.append(sub)
        self._fit_width()
        row._bpkey = None                      # kein BP-Schlüssel: nie „bestätigen"
        if top:
            row.pack_configure(before=top[0])
        self._trim()
        self.canvas.yview_moveto(0)
        signalton(auffaellig=bool(titel))

    def confirm(self, row_key, key, art, meta):
        """Der Launcher hat den vorläufig (aus der Game.log) gemeldeten BP bestätigt:
        Punkt auf Grün, „vorläufig" raus, Name/Art/Kürzel mit den Launcher-Daten
        auffrischen (`row_key` = angezeigter Log-Name, `key` = Launcher-Schlüssel)."""
        r = self.rows.pop(_norm(row_key), None)
        if not r or not r['frame'].winfo_exists():
            return
        r['dot'].config(text='🟢')
        r['name'].config(text=key)
        r['sub'].config(text=self._sub_text(art, meta, r['ts'], False), fg=SUB)
        r['frame']._bpkey = _norm(key)
        self.rows[_norm(key)] = r

    def _trim(self):
        """Nur MAX_ROWS Zeilen behalten — älteste (unten im Fenster) fliegen raus."""
        rows = self.list.pack_slaves()
        while len(rows) > MAX_ROWS:
            old = rows.pop()
            self.rows.pop(getattr(old, '_bpkey', None), None)
            old.destroy()
            self.count -= 1

    # ---- Queue vom Watcher abarbeiten ----
    def _poll_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == 'status':
                    self.status.config(text=msg[1])
                elif msg[0] == 'hinweis':
                    # Bleibt stehen, bis die nächste Statusmeldung kommt, und
                    # wird farblich abgesetzt — eine Lücke im Bestand soll
                    # auffallen, aber kein Fenster aufreißen.
                    self.add_hinweis(msg[1])
                elif msg[0] == 'new':
                    self.add_new(msg[1], msg[2], msg[3], msg[4], msg[5])
                elif msg[0] == 'confirm':
                    self.confirm(msg[1], msg[2], msg[3], msg[4])
                elif msg[0] == 'catalog':
                    self.add_catalog(msg[1], msg[2], msg[3], msg[4])
        except queue.Empty:
            pass
        self.root.after(300, self._poll_queue)

    def versionen_zeigen(self):
        """Das Fenster „Was ist neu" öffnen."""
        from scbp.versionsfenster import Versionsfenster
        vorhanden = getattr(self, '_versionen', None)
        if vorhanden is not None:
            try:
                vorhanden.root.lift()
                return
            except Exception:
                pass
        self._versionen = Versionsfenster(
            self.root, eigene_version=__version__,
            beim_schliessen=lambda: setattr(self, '_versionen', None))

    def _nach_version_sehen(self):
        """Im Hintergrund nachsehen, ob es etwas Neues gibt.

        Im Nebenläufer, damit der Start nicht auf das Netz wartet — und still,
        wenn nichts da ist. Ein Werkzeug, das beim Spielen im Vordergrund liegt,
        soll nicht ungefragt Fenster aufreißen; der Knopf färbt sich, mehr nicht."""
        def arbeit():
            try:
                neu = aktualisierung.nachsehen(__version__)
            except Exception:
                return
            if neu:
                self.root.after(0, lambda: self._version_melden(neu))
        threading.Thread(target=arbeit, daemon=True).start()

    def _version_melden(self, neu):
        try:
            self.info_lbl.config(fg=ACCENT)
            self.q.put(('hinweis', '%s — %s'
                        % (sprache.t('neue_version_da', neu['version']),
                           sprache.t('was_ist_neu'))))
        except Exception:
            pass

    def einstellungen_oeffnen(self):
        einstellungsfenster.oeffnen(self.root)

    def einrichtung_erneut(self):
        """Den Assistenten noch einmal durchlaufen lassen."""
        fertig, zeige_liste = assistent.starten(self.root)
        if fertig and zeige_liste:
            self.liste_oeffnen()

    def liste_oeffnen(self):
        """Das Verwaltungsfenster zeigen. Ein zweiter Klick holt es nach vorn,
        statt ein zweites Fenster aufzumachen."""
        from scbp.bestandsfenster import Bestandsfenster
        vorhanden = getattr(self, '_liste', None)
        if vorhanden is not None:
            try:
                vorhanden.root.lift()
                vorhanden.root.focus_force()
                return
            except Exception:
                pass                       # war schon zu
        self._liste = Bestandsfenster(self.root,
                                      beim_schliessen=self._liste_zu)
        self.liste_lbl.config(fg=ACCENT)

    def _liste_zu(self):
        self._liste = None
        self.liste_lbl.config(fg=SUB)

    def _current_geom(self):
        # Aus winfo bauen (nicht root.geometry()): so bleibt negatives Y als absolute
        # Position erhalten ('+-1439') statt als „vom unteren Rand" missverstanden zu werden.
        return (f'{self.root.winfo_width()}x{self.root.winfo_height()}'
                f'+{self.root.winfo_x()}+{self.root.winfo_y()}')

    def _save_geo(self, e=None):
        save_geometry(self._current_geom())

    def quit(self):
        self._save_geo()
        self.watcher.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    # Ablauf beim Start — in dieser Reihenfolge mit Absicht:
    #
    #   1. Spielordner beschaffen. Wird er nicht gefunden, FRAGEN wir danach,
    #      statt eine Meldung hinzuwerfen und uns zu beenden. Ohne die Game.log
    #      kann das Programm nichts, also ist das die eine Angabe, die es
    #      wirklich braucht.
    #   2. Beim allerersten Mal die alten Logs nachlesen — sichtbar, denn hier
    #      bekommt der Spieler seinen ganzen bisherigen Bestand geschenkt.
    #   3. Erst danach darf von Hand nachgetragen werden, und nur das, was
    #      wirklich keine Logdatei mehr hergibt.
    zeige_liste = False
    if assistent.noetig():
        fertig, zeige_liste = assistent.starten()
        if not fertig:
            sys.exit(0)                 # Nutzer hat abgebrochen
    fenster = Overlay()
    if zeige_liste:
        fenster.liste_oeffnen()
    fenster.run()
