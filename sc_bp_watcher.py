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
from scbp import fehler
from scbp import (ablagesymbol, aktualisierung, assistent, autostart,
                  bildschirm, overlay,
                  bestand as bestand_datei, bestandsfenster as bestandsfenster_modul,
                  einstellungsfenster, hinweis, injektion,
                  katalog as katalog_modul, logquelle, merkliste,
                  pfade, phrasen, ton, uebersetzung)

try:
    import winsound                      # nur Windows; unter Linux übernimmt tkinter
except ImportError:
    winsound = None

__version__ = '3.0.0-rc35'


def _mitgeliefert(name):
    """Pfad zu einer mitgelieferten Datei — im Quellcode wie im fertigen Paket.

    PyInstaller entpackt alles nach `sys._MEIPASS`; daneben zu suchen geht dort
    ins Leere. Beim Start aus dem Quellcode gibt es das Attribut nicht, dann
    gilt der Ordner dieser Datei.
    """
    try:
        basis = getattr(sys, '_MEIPASS', None) or os.path.dirname(
            os.path.abspath(__file__))
        return os.path.join(basis, name)
    except Exception:
        return None

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
# So viele Neuzugänge bleiben im Overlay stehen, ältere rutschen heraus.
#
# ⚠ Zweierlei war hier falsch. Erstens war die Zahl **fest** — die Einstellung
# „Zeilen im Overlay" wurde brav gespeichert und dann nie gelesen. Zweitens war
# die Vorgabe 200: So viele Baupläne sammelt in einer Spielsitzung niemand, und
# ein Overlay, das theoretisch 200 Zeilen hoch werden kann, steht im Weg.
# Jetzt gilt die Einstellung, mit 20 als Vorgabe.
MAX_ROWS_VORGABE = 20


def max_zeilen():
    """Wie viele Zeilen das Overlay behält — jedes Mal frisch gelesen, damit
    eine Änderung in den Einstellungen sofort wirkt und nicht erst nach einem
    Neustart."""
    return pfade.einstellung_zahl('max_zeilen', MAX_ROWS_VORGABE, 5, 100)

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
# Übersetzung und Bauplan-Angaben: beim Start und danach alle sechs Stunden.
# Häufiger bringt nichts — die Quellen aktualisieren im Tagesrhythmus.
TEXTE_POLL_SEC = 6 * 3600
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
# Nur die **Größe** — die Position wird beim Start ausgerechnet (mittig auf dem
# Hauptbildschirm, siehe `startlage`). Eine feste Position wäre auf jedem anderen
# Rechner falsch, und gar keine Position lässt Tk nach `+0+0` platzieren — bei einem
# hochkant stehenden Monitor links außen ist dort schlicht kein Bild.
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


# Rüstungs-Slots von scmdb -> die hier verwendeten Begriffe. Die Gewichtsklasse (Heavy/Medium/
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
    """Die gemerkte Fensterlage — oder `None`, wenn es noch keine gibt.

    Bewusst `None` statt der Standardgröße: Nur so unterscheidet der Aufrufer
    „der Nutzer hat sein Fenster irgendwohin gestellt" von „erster Start", und
    nur beim ersten Start soll das Fenster mittig gesetzt werden.
    """
    try:
        return json.load(open(SETTINGS_FILE, encoding='utf-8')).get('geometry') or None
    except Exception:
        return None


GEOM_RE = re.compile(r'^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$')


def geometrie_pruefen(geom, root):
    """Liegt die gemerkte Fensterlage auf diesem Rechner überhaupt im Bild?

    Der Watcher speichert seine Lage, damit er beim nächsten Mal wieder dort
    steht — beim Autor auf dem oberen von drei Monitoren, also bei X≈3656 und
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


def standardlage(root):
    """Die Lage, mit der jeder anfängt: mittig auf dem **Hauptbildschirm**.

    Dieselbe Lage stellt auch der Knopf „Fensterlage zurücksetzen" wieder her.
    Wie viele Bildschirme jemand hat, weiß niemand vorher — die Mitte des
    Hauptbildschirms ist die einzige Stelle, die überall sinnvoll ist.
    """
    m = GEOM_RE.match(DEFAULT_GEOM or '')
    breite, hoehe = (int(m.group(1)), int(m.group(2))) if m else (440, 1000)
    return bildschirm.mittig(root, breite, hoehe)


def startlage(root):
    """Wohin das Overlay beim Start gehört.

    Gemerkte Lage, wenn es eine gibt und sie auf diesem Rechner plausibel ist;
    sonst die Standardlage. `geometrie_pruefen` gibt bei einer unglaubwürdigen
    Lage nur noch die Größe zurück — auch dann wird mittig gesetzt, statt Tk
    raten zu lassen.
    """
    gemerkt = load_geometry()
    if not gemerkt:
        return standardlage(root)
    geprueft = geometrie_pruefen(gemerkt, root)
    if '+' not in geprueft:
        return standardlage(root)
    return geprueft


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
        self.texte_next = 0.0   # nächster Blick auf Übersetzung und Injektion
        self.texte_laeuft = False

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

    # ---- Bauplan-Angaben im Spiel frisch halten ----
    def _texte_tick(self):
        """Übersetzung, Vertragsdaten und Injektion nachziehen — von selbst.

        **Warum das nicht optional sein kann:** Jedes Übersetzungs-Update und
        jeder Spiel-Patch schreibt die `global.ini` neu; die eingetragenen
        Bauplan-Angaben sind dann **weg**, ohne dass irgendetwas darauf
        hinweist. Und nach einem Patch geben Missionen andere Baupläne aus —
        wer dann noch die alten Angaben liest, plant mit falschen Daten.
        Beides fällt niemandem auf, weil das Spiel ja normal weiterläuft.

        Angefasst wird nur, was der Spieler selbst eingerichtet hat: Ohne
        vermerkte Quelle passiert hier gar nichts.

        Läuft im **eigenen** Thread — es sind mehrere Megabyte, und die
        Log-Erkennung darf dafür nicht stehenbleiben."""
        if SCMDB_AUS or self.texte_laeuft or time.time() < self.texte_next:
            return
        # ⚠ Zwei Schalter, und beide müssen hier gelten:
        #   `inj_an`   — schreibt das Werkzeug überhaupt in die Auftragstexte?
        #                Aus lassen will, wer gerade auf PTU spielt oder seine
        #                Textdatei in Ruhe haben möchte.
        #   `inj_auto` — hält es sich von selbst aktuell?
        # Der erste fehlte ganz: Ausschalten ging nur über „Wieder entfernen",
        # und beim nächsten Start schrieb das Werkzeug wieder hinein.
        if not pfade.einstellung_wahrheit('inj_an', True):
            self.texte_next = time.time() + TEXTE_POLL_SEC
            return
        if not pfade.einstellung_wahrheit('inj_auto', True):
            self.texte_next = time.time() + TEXTE_POLL_SEC
            return
        quelle = next((q for q in uebersetzung.QUELLEN
                       if uebersetzung.installiert(q)), None)
        eigene_texte = bool(uebersetzung.installiert('original'))
        if not quelle and not eigene_texte:
            return                      # nie eingerichtet — Finger weg
        self.texte_next = time.time() + TEXTE_POLL_SEC
        self.texte_laeuft = True

        def arbeit():
            try:
                self._texte_abgleichen(quelle)
            finally:
                self.texte_laeuft = False

        threading.Thread(target=arbeit, daemon=True).start()

    def _texte_abgleichen(self, quelle):
        """Der eigentliche Abgleich. Meldet nur, wenn sich etwas geändert hat."""
        sprache_ordner = (uebersetzung.QUELLEN[quelle]['sprache'] if quelle
                          else 'english')
        ziel = uebersetzung.ziel_ini(sprache_ordner)
        if not ziel:
            return
        kuerzel = injektion._sprachkuerzel(sprache_ordner)
        neu_noetig = False

        # 1. Neue Fassung der Übersetzung? Die schreibt die Datei komplett neu,
        #    danach ist die Injektion in jedem Fall weg.
        if quelle:
            da, kennung = uebersetzung.update_da(quelle)
            if da:
                ok, meldung = uebersetzung.holen(quelle)
                if ok:
                    self.q.put(('status', sprache.t('texte_erneuert', kennung)))
                    neu_noetig = True

        # 2. Neue Vertragsdaten? Nach einem Patch geben Missionen anderes aus.
        da, kennung = injektion.scdl_update_da(kuerzel)
        if da:
            self.q.put(('status', sprache.t('bpdaten_erneuert', kennung)))
            neu_noetig = True

        # 3. Ist die Auszeichnung überhaupt noch drin? Ein Spiel-Patch ersetzt
        #    die Datei, ohne dass jemand etwas davon merkt.
        if not neu_noetig and not injektion.ist_drin(ziel):
            neu_noetig = True

        if neu_noetig and os.path.isfile(ziel):
            ok, anzahl, _meldung = injektion.einrichten(ziel, sprache_ordner)
            if ok:
                self.q.put(('status', sprache.t('inj_aktiv', anzahl)))

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

    def _startbauplaene_eintragen(self):
        """Die acht Startbaupläne in den Bestand — falls noch nicht drin.

        Quelle `start` (Rang 2): höher als ein Log-Fund, niedriger als ein von
        Hand gesetztes Häkchen oder der Launcher. Wer sie also selbst abgehakt
        hat, behält seinen Eintrag."""
        try:
            std = katalog_modul.startbauplaene()
            if not std:
                return
            katalog = katalog_modul.laden()['bauplaene']
            neu = 0
            for schluessel in std:
                name = (katalog.get(schluessel) or {}).get('n')
                if name and bestand_datei.hinzufuegen(self.bestand, name, 'start'):
                    neu += 1
            if neu:
                bestand_datei.speichern(self.bestand)
                self.q.put(('status', sprache.t('start_eingetragen', neu)))
        except Exception:
            pass          # ein Fehler hier darf den Start nicht aufhalten

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

        # 2) Startbaupläne eintragen — die hat jeder Spieler von Anfang an,
        #    sie stehen deshalb in **keinem** Log und in keinem Belohnungs-Pool.
        #    Ohne diesen Schritt fehlen sie dauerhaft im Bestand, und der
        #    Fortschritt zeigt weniger an, als man tatsächlich hat.
        self._startbauplaene_eintragen()

        # 3) Vergangenes nachlesen (still, nur in den Bestand)
        self._nachlese()

        # 4) Launcher-Stand holen — wenn es ihn gibt. Ohne ihn wird nicht mehr
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

        # 5) Alles, was schon im Bestand steht, gilt als bekannt — es wird nicht
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
            self._texte_tick()

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
    def __init__(self, wurzel=None):
        """`wurzel` ist die eine Tk-Instanz des Programms — siehe unten, warum es
        nur eine geben darf."""
        # ⚠ Vor allem anderen: Liegen die Dateien noch am alten Ort (bis v2.x
        # versteckt in %APPDATA% bzw. ~/.config), werden sie in den sichtbaren
        # Ordner unter Dokumente **kopiert**. Erst danach darf irgendetwas
        # gelesen werden — sonst startet der Spieler mit leerer Liste, obwohl
        # sein Bestand nur woanders liegt.
        # Nach einem Selbst-Update zeigt Windows sonst weiter die alte Nummer.
        try:
            aktualisierung.windows_eintrag_pflegen(__version__)
        except Exception as ausnahme:
            fehler.merken('start.windows_eintrag', ausnahme)

        self.umzug_meldung = ''
        try:
            if pfade.umzug_noetig():
                anzahl = pfade.umziehen()
                if anzahl:
                    self.umzug_meldung = t('umzug_fertig', anzahl,
                                           pfade.app_ordner())
                    sys.stdout.write(self.umzug_meldung + '\n')
        except Exception as ausnahme:
            fehler.merken('start.umzug', ausnahme)

        # ⚠ **Nur eine einzige `tk.Tk()` im ganzen Programm.** Vorher legte der
        # Assistent eine eigene an, zerstörte sie am Ende — und hier entstand eine
        # zweite. Das ist der Fall, den Tk nicht verlässlich verträgt: Nach dem
        # `destroy()` der ersten leben Schriften, Bilder und offene `after`-Aufträge
        # weiter und zeigen auf einen toten Interpreter. Ob das gutgeht, hängt am
        # Zeitpunkt — bei einem Tester (Bomb20, 25.08.2026) endete der **erste**
        # Programmstart reproduzierbar mit `SIGSEGV`, direkt nach dem Nachlesen der
        # Logs. Sein Satz „mit Debugging an lief es durch" ist der Fingerabdruck
        # eines solchen Zeitproblems: Langsamer läuft es zufällig richtig.
        #
        # Deshalb wird die Wurzel **einmal** erzeugt und weitergereicht; der
        # Assistent ist seitdem ein `Toplevel` daran.
        self.root = wurzel if wurzel is not None else tk.Tk()
        # Ab hier werden auch Fehler in Rückrufen der Oberfläche festgehalten.
        # Ohne diesen Haken schreibt Tk sie auf die Standardausgabe — und die
        # sieht in einer .exe oder einem AppImage niemand.
        fehler.haken_setzen(self.root)
        _WURZEL[0] = self.root                    # damit signalton() klingeln kann
        # Damit der Knopf „Fensterlage zurücksetzen" das Overlay sofort in die Mitte
        # setzen kann, ohne dass `seiten.py` das Hauptprogramm importieren müsste.
        bildschirm.OVERLAY[0] = self.root
        overlay.OVERLAY_FENSTER[0] = self.root
        # Merken, ob der Zeiger auf dem Overlay steht — das entscheidet, ob eine
        # Einblendung stehen bleibt. Echte Ereignisse statt Positionsabfrage.
        self.root.bind('<Enter>', lambda e: setattr(self, '_maus_drauf', True),
                       add='+')
        self.root.bind('<Leave>', lambda e: setattr(self, '_maus_drauf', False),
                       add='+')
        overlay.OVERLAY_STEUERUNG[0] = self
        # Damit jeder festgehaltene Fehler weiß, aus welcher Fassung er stammt.
        fehler.VERSION[0] = __version__
        self.root.title('SC BP Watcher')
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)          # randloses Overlay
        self.root.attributes('-topmost', True)    # immer im Vordergrund
        # Wie sich das Fenster im Spiel verhält — siehe scbp/overlay.py.
        # 'immer' = steht dauerhaft da (wie bisher), 'popup' = zeigt sich nur,
        # wenn wirklich ein Bauplan dazukommt.
        self.anzeigeart = pfade.einstellung('overlay_modus') or 'immer'
        self._popup_uhr = None
        self._letzte_lage = ''
        self._anfasser = None
        self._maus_drauf = False
        # Durchsichtigkeit einstellbar (30–100 %). Wer nur **einen** Monitor hat,
        # legt das Overlay zwangsläufig übers Spiel — dann muss man hindurchsehen
        # können. 93 % bleibt der Standard, das ist auf zwei Bildschirmen richtig.
        self.root.attributes('-alpha', DECKKRAFT / 100.0)
        self.root.geometry(startlage(self.root))
        self._icon_setzen()
        self.count = 0
        self.rows = {}          # normalisierter Name -> Zeilen-Widgets (für die Bestätigung)

        # ⚠ Die Schriftgröße aus den Einstellungen gilt **auch hier**. Sie wirkte
        # lange nur im großen Fenster; im Overlay standen feste Größen. Wer sie
        # auf „groß" stellte, weil er die Zeilen im Spiel nicht lesen konnte,
        # änderte damit ausgerechnet das Fenster nicht, um das es ihm ging.
        # Gemeldet von Haldjas, 25.08.2026.
        #
        # Die Grundwerte liegen eins unter den früheren festen Größen, damit die
        # Stufe „normal" (= 1) genau das bisherige Aussehen ergibt — niemand,
        # der nichts eingestellt hat, sieht plötzlich ein anderes Overlay.
        self.f_title, self.f_item, self.f_sub = self._schriften_anlegen()

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
        # Einklappen: nur die Titelleiste bleibt stehen. Für alle mit **einem**
        # Bildschirm — dort liegt das Overlay zwangsläufig über dem Spiel, und
        # Durchsichtigkeit allein reicht nicht, wenn man gerade freie Sicht
        # braucht. Ersetzt zugleich das nie gebaute Ablage-Symbol (Tray): Das
        # bräuchte Zusatzpakete, ein eingeklappter Streifen nicht.
        self.klapp_lbl = tk.Label(bar, text='▾', bg=BAR, fg=SUB,
                                  font=self.f_title, cursor='hand2')
        self.klapp_lbl.pack(side='right', padx=(0, 6))
        self.klapp_lbl.bind('<Button-1>', lambda e: self.umklappen())
        hinweis.anhaengen(self.klapp_lbl, self._hinweis_klappen)
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
        # ⚠ Der Startknopf gehört **hierher**, nicht auf eine Unterseite. Er saß
        # erst unter „Angaben im Spiel" — also dort, wo es um Auftragstexte
        # geht, und da sucht ihn niemand. Dazu: „wenn leute den suchen
        # müssen ist er falsch platziert."
        #
        # Wer das Spiel starten will, hat das große Fenster nicht offen; er
        # sieht das Overlay. Deshalb steht das Zeichen hier, in Grün und als
        # erstes der Gruppe — und nur dann, wenn wirklich ein Weg gefunden
        # wurde (siehe `pfade.spielstarter()`).
        if pfade.spielstarter():
            self.start_lbl = tk.Label(bar, text='▶', bg=BAR, fg=ACCENT,
                                      font=self.f_title, cursor='hand2')
            self.start_lbl.pack(side='right', padx=(0, 6))
            self.start_lbl.bind('<Button-1>', lambda e: self._spiel_starten())
            # Ein „▶" allein sagt niemandem, was passiert. Die Statuszeile
            # darunter gibt es ohnehin — beim Überfahren steht dort im Klartext,
            # was der Klick tut. Kein zusätzliches Sprechblasen-Werk nötig.
            self.start_lbl.bind(
                '<Enter>',
                lambda e: self.status.config(text=sprache.t('s_sp_start')))
            self.start_lbl.bind(
                '<Leave>', lambda e: self.status.config(text=self._status_text))

        self.info_lbl = tk.Label(bar, text='ⓘ', bg=BAR, fg=SUB,
                                 font=self.f_title, cursor='hand2')
        self.info_lbl.pack(side='right', padx=(0, 6))
        self.info_lbl.bind('<Button-1>', lambda e: self.versionen_zeigen())
        hinweis.anhaengen(self.info_lbl, self._hinweis_info)
        self.as_lbl.bind('<Button-1>', lambda e: self._toggle_autostart())
        hinweis.anhaengen(self.as_lbl, self._hinweis_autostart)
        self._show_autostart()
        # Mitschalten, wenn der Autostart in den Einstellungen umgestellt wird.
        autostart.anzeige_anmelden(self._show_autostart)
        for w in (bar, bar.winfo_children()[0]):
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)
            w.bind('<ButtonRelease-1>', self._save_geo)   # Position nach dem Ziehen merken

        # --- Statuszeile ---
        self._status_text = 'Starte …'
        self.status = tk.Label(self.root, text='Starte …', bg=BG, fg=SUB,
                               font=self.f_sub, anchor='w')
        self.status.pack(fill='x', padx=8, pady=(4, 2))

        # --- Liste (scrollbar) ---
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill='both', expand=True, padx=6, pady=(0, 6))
        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        # ⚠ Keine tk.Scrollbar: Die reicht Tk an das System durch — unter Linux
        # grau, auf dem Mac hellweiss, und damit der einzige Fleck, der aus dem
        # Bild faellt. Genau so gemeldet: "scrollbalken im watcher selber ist
        # auch nicht passend". Die vier Rollbereiche im Hauptfenster hatten den
        # Umbau schon; hier stand er noch aus.
        from scbp.hauptfenster import rundleiste
        sb = rundleiste(wrap, self.canvas, grund=BG)
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
        # Version an die Bauplan-Liste durchreichen — sie landet im
        # scmdb-Export als Kennung des erzeugenden Werkzeugs.
        bestandsfenster_modul.VERSION[0] = __version__
        self.eingeklappt = False
        self.hoehe_offen = None      # Fensterhöhe vor dem Einklappen
        if pfade.einstellung_wahrheit('eingeklappt', False):
            self.root.after(120, self.umklappen)

        self.q = queue.Queue()
        self.watcher = Watcher(self.q)
        self.watcher.start()
        self.root.after(200, self._poll_queue)
        self.root.after(2000, self._nach_version_sehen)   # nicht beim Start drängeln

    # ---- Drag & Resize ----
    # ---- Schalter „mit dem Rechner starten" ----
    # ---- Erklärtexte, die ihren Zustand kennen ----
    # --------------------------------------------------------- Schriftgrößen
    OVERLAY_GRUND = (('f_title', 'Segoe UI Semibold', 9),
                     ('f_item', 'Consolas', 8),
                     ('f_sub', 'Segoe UI', 7))

    def _stufe(self):
        from scbp.hauptfenster import STUFEN
        return STUFEN.get(pfade.einstellung('schriftgroesse') or 'normal', 1)

    def _schriften_anlegen(self):
        n = self._stufe()
        return tuple(tkfont.Font(family=fam, size=grund + n)
                     for _, fam, grund in self.OVERLAY_GRUND)

    def schriftgroesse_anwenden(self, stufe=None):
        """Zieht die Overlay-Schriften nach — sofort, ohne Neustart.

        Tk-Font-Objekte sind benannt: Ein `configure` wirkt auf jedes Widget,
        das die Schrift benutzt. Deshalb genügt es, die drei Objekte zu ändern,
        statt die Zeilen neu zu bauen.
        """
        from scbp.hauptfenster import STUFEN
        n = STUFEN.get(stufe, self._stufe()) if stufe else self._stufe()
        for (name, _, grund) in self.OVERLAY_GRUND:
            try:
                getattr(self, name).configure(size=grund + n)
            except Exception as ausnahme:
                fehler.merken('overlay.schriftgroesse', ausnahme)

    def _spiel_starten(self):
        """Star Citizen starten — über den Weg, den der Spieler ohnehin nutzt."""
        ok, grund = pfade.spiel_starten()
        if ok:
            self.status.config(text=sprache.t('s_sp_start_lauft'))
        else:
            self.status.config(text=sprache.t('s_sp_start_nein', grund))
            fehler.merken('overlay.spiel_starten', OSError(str(grund)))

    def _ganz_beenden(self):
        """Beenden über das Symbol neben der Uhr — und zwar wirklich.

        ⚠ `destroy()` allein hat das Fenster geschlossen und den Prozess leben
        lassen: Es beendet die Ereignisschleife, nicht das Programm. Läuft noch
        ein Faden (Watcher, Netzabruf), bleibt das Ganze im Speicher stehen —
        genau das, was Haldjas am 25.08.2026 gesehen hat („als hätte er nur das
        symbol von der taskleiste gekillt").

        Zuerst wird sauber zugemacht, damit der Bestand geschrieben wird. Wer
        nach drei Sekunden immer noch hängt, wird hart beendet — bis dahin ist
        alles Wichtige auf der Platte.
        """
        threading.Timer(3.0, lambda: os._exit(0)).start()
        try:
            self.root.destroy()
        except Exception:
            pass

    def _icon_setzen(self):
        """Fenster- und Taskleisten-Icon — auf beiden Systemen und für alle Fenster.

        Vorher stand hier nur `iconbitmap('icon.ico')`. Das hatte zwei Löcher:
        `iconbitmap` mit einer `.ico` ist **Windows-only**, unter Linux blieb das
        Fenster ohne Icon. Und die Datei lag zur Laufzeit gar nicht daneben —
        PyInstallers `--icon` setzt nur das Symbol der `.exe` selbst, es packt
        die Datei nicht mit ein. In der fertigen Fassung gab es das Icon also
        nirgends, auch unter Windows nicht.

        `iconphoto(True, …)` mit dem PNG kann Tk auf beiden Systemen, und das
        `True` vererbt es an **alle** weiteren Fenster (Liste, Einstellungen,
        Assistent) — sonst müsste jedes es selbst setzen.
        """
        try:
            png = _mitgeliefert(os.path.join('assets', 'icon.png'))
            if png and os.path.exists(png):
                # ⚠ Die Referenz muss am Objekt hängen bleiben. Eine lokale
                # Variable wird nach der Methode aufgeräumt, und Tk zeigt dann
                # ein leeres Icon — das Bild ist weg, bevor es gebraucht wird.
                self._icon_bild = tk.PhotoImage(file=png)
                self.root.iconphoto(True, self._icon_bild)
        except Exception as ausnahme:
            fehler.merken('oberflaeche.icon', ausnahme)

        if sys.platform.startswith('win'):
            # Zusätzlich unter Windows: Die .ico bringt mehrere Auflösungen mit
            # und sieht in der Taskleiste schärfer aus als ein skaliertes PNG.
            try:
                ico = _mitgeliefert('icon.ico')
                if ico and os.path.exists(ico):
                    self.root.iconbitmap(ico)
            except Exception:
                pass

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
        self._popup_zeigen()

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
        """Nur so viele Zeilen behalten wie eingestellt — älteste fliegen raus."""
        rows = self.list.pack_slaves()
        grenze = max_zeilen()
        while len(rows) > grenze:
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

    def _hinweis_klappen(self):
        return sprache.t('hinweis_ausklappen' if self.eingeklappt
                         else 'hinweis_einklappen')

    def umklappen(self):
        """Auf die Titelleiste zusammenschieben — oder wieder aufmachen.

        Gemerkt wird die Höhe **vor** dem Einklappen, nicht eine feste Zahl:
        Wer sich das Fenster auf 900 Pixel gezogen hat, will es beim Aufklappen
        auch wieder so haben."""
        try:
            if self.eingeklappt:
                hoehe = self.hoehe_offen or 400
                self.root.geometry('%dx%d+%d+%d' % (
                    self.root.winfo_width(), hoehe,
                    self.root.winfo_x(), self.root.winfo_y()))
                self.klapp_lbl.configure(text='▾')
                self.eingeklappt = False
            else:
                self.hoehe_offen = self.root.winfo_height()
                # Die Höhe der Titelleiste, nicht geraten: Ein fester Wert säße
                # bei anderer Schriftgröße daneben.
                leiste = self.root.winfo_children()[0]
                hoehe = max(leiste.winfo_height(), 26)
                self.root.geometry('%dx%d+%d+%d' % (
                    self.root.winfo_width(), hoehe,
                    self.root.winfo_x(), self.root.winfo_y()))
                self.klapp_lbl.configure(text='▸')
                self.eingeklappt = True
            pfade.einstellung_setzen('eingeklappt', self.eingeklappt)
        except tk.TclError:
            pass

    def einstellungen_oeffnen(self):
        """Seit v3.0.0 führen beide Wege ins **eine** Fenster — nur auf eine
        andere Seite. Zwei getrennte Fenster hießen: raten, in welchem etwas
        steckt."""
        self.fenster_oeffnen('allgemein')

    def einrichtung_erneut(self):
        """Den Assistenten noch einmal durchlaufen lassen."""
        fertig, zeige_liste = assistent.starten(self.root)
        if fertig and zeige_liste:
            self.liste_oeffnen()

    def liste_oeffnen(self):
        """Das große Fenster auf der Bauplan-Liste öffnen."""
        self.fenster_oeffnen('liste')

    def fenster_oeffnen(self, seite='liste'):
        """Das Hauptfenster zeigen — und darin die gewünschte Seite.

        Ein zweiter Klick holt das vorhandene Fenster nach vorn und wechselt die
        Seite, statt ein zweites aufzumachen. Zwei gleiche Fenster nebeneinander
        sind für niemanden nachvollziehbar."""
        from scbp.hauptfenster import Hauptfenster
        vorhanden = getattr(self, '_fenster', None)
        if vorhanden is not None:
            try:
                vorhanden.root.lift()
                vorhanden.root.focus_force()
                vorhanden.oeffnen(seite)
                return
            except Exception:
                pass                       # war schon zu
        self._fenster = Hauptfenster(self.root, beim_schliessen=self._liste_zu,
                                     version=__version__,
                                     beim_schriftwechsel=self.schriftgroesse_anwenden)
        self._fenster.oeffnen(seite)
        self.liste_lbl.config(fg=ACCENT)

    def _liste_zu(self):
        self._fenster = None
        self.liste_lbl.config(fg=SUB)
        # ⚠ Genau hier zieht eine geänderte Anzeigeart. Stellt jemand in den
        # Einstellungen auf „nur bei einem Neuzugang" um, darf das Overlay nicht
        # sofort verschwinden — er steht ja noch davor und will das Ergebnis
        # sehen. Beim Schließen des Fensters ist der richtige Moment: Wer fertig
        # eingestellt hat, will zurück ins Spiel.
        self.verhalten_anwenden()

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

    # ------------------------------------------------- Verhalten im Spiel
    def verhalten_anwenden(self):
        """Pop-up-Betrieb und Durchklickbarkeit setzen — nach dem Aufbau.

        ⚠ Erst hier, nicht im Aufbau: Beides fasst das fertige Fenster an. Vorher
        hat es unter X11 noch keine Kennung, die man einer Maske geben könnte.
        """
        self.anzeigeart = pfade.einstellung('overlay_modus') or 'immer'
        if self.anzeigeart == 'popup':
            # ⚠ Die Lage merken, **bevor** versteckt wird. Ein Fenster, das noch
            # nie zu sehen war, meldet `1x1+0+0` — die Mauswache suchte dann in der
            # linken oberen Bildschirmecke statt dort, wo das Overlay steht, und
            # ging nie an. Beim Start im Aufblend-Betrieb ist genau das der Fall.
            self._letzte_lage = self._current_geom()
            if '+' not in self._letzte_lage or self._letzte_lage.startswith('1x1'):
                # Noch nie gezeichnet: dann gilt, was gespeichert ist.
                self._letzte_lage = load_geometry() or startlage(self.root)
            # Läuft gerade eine Einblendung, wird sie nicht abgeschnitten — der
            # Zähler räumt gleich selbst auf.
            if self._popup_uhr is None:
                self.root.withdraw()
                self._anfasser_zeigen()
        else:
            self._anfasser_weg()
            try:
                self.root.deiconify()
            except tk.TclError:
                pass
        self.durchklick_anwenden()

    def durchklick_anwenden(self):
        """Klicks durchreichen, wenn eingestellt — und melden, wenn es nicht geht."""
        an = pfade.einstellung_wahrheit('durchklickbar', False)
        if not an and not getattr(self, '_durchklick_war_an', False):
            return                       # nie eingeschaltet gewesen: nichts zu tun
        self._durchklick_war_an = an
        try:
            geklappt = overlay.durchklickbar_setzen(self.root, an)
        except Exception as ausnahme:
            fehler.merken('overlay.durchklick', ausnahme)
            geklappt = False
        if an and not geklappt:
            self.status.config(text=sprache.t('ov_durchklick_geht_nicht'))

    # ---------------------------------------------- Der Anfasser holt es zurück
    #
    # Gemeldet am 25.08.2026: „Wie schaut es aus, das Fenster bei Mouseover sichtbar
    # zu machen, damit man den Umweg nicht gehen muss es erneut zu starten? Die
    # Logik kenne ich bisher ohnehin nicht bei anderen Programmen dieser Art."
    #
    # Er hat recht — „zum Zurückholen das Programm neu starten" verlangt kein
    # anderes Overlay.
    #
    # ⚠ Der erste Anlauf fragte die Mausposition ab (`winfo_pointerxy`) und blendete
    # ein, sobald sie im Bereich lag. Das **kann unter Wayland nicht gehen**:
    # Gemessen auf einem Rechner meldete Tk zwölfmal hintereinander exakt
    # dieselben Koordinaten, während die Maus quer über den Schirm fuhr. Eine
    # Anwendung erfährt die Zeigerposition dort nur, solange er über einem **ihrer
    # eigenen** Fenster steht — und ein verstecktes Fenster ist keines.
    #
    # Also bleibt ein Fenster stehen: ein schmaler Streifen an der oberen Kante der
    # letzten Position. Der bekommt echte `<Enter>`-Ereignisse, unter Wayland wie
    # unter X11 und Windows. Nebenbei ist er ehrlicher als eine unsichtbare
    # Zauberzone — man **sieht**, wo das Overlay wartet.
    ANFASSER_BREITE = 54
    ANFASSER_HOEHE = 5

    def _anfasser_zeigen(self):
        """Den Streifen an die letzte Position des Overlays legen."""
        if self.anzeigeart != 'popup':
            return self._anfasser_weg()
        lage = self._letzte_lage or ''
        m = GEOM_RE.match(lage)
        if not m or m.group(3) is None:
            return
        breite, _hoehe, links, oben = (int(z) for z in m.groups())
        x = links + max(0, (breite - self.ANFASSER_BREITE) // 2)
        y = max(0, oben)
        try:
            if self._anfasser is None or not self._anfasser.winfo_exists():
                self._anfasser = tk.Toplevel(self.root)
                self._anfasser.overrideredirect(True)
                self._anfasser.attributes('-topmost', True)
                self._anfasser.configure(bg=ACCENT, cursor='hand2')
                try:
                    self._anfasser.attributes('-alpha', 0.55)
                except tk.TclError:
                    pass
                self._anfasser.bind('<Enter>',
                                    lambda e: self._popup_zeigen(wegen_maus=True))
                self._anfasser.bind('<Button-1>',
                                    lambda e: self._popup_zeigen(wegen_maus=True))
                hinweis.anhaengen(self._anfasser,
                                  lambda: sprache.t('hinweis_anfasser'))
            self._anfasser.geometry('%dx%d+%d+%d'
                                    % (self.ANFASSER_BREITE, self.ANFASSER_HOEHE,
                                       x, y))
            self._anfasser.deiconify()
            self._anfasser.lift()
        except tk.TclError:
            pass

    def _anfasser_weg(self):
        try:
            if self._anfasser is not None and self._anfasser.winfo_exists():
                self._anfasser.withdraw()
        except tk.TclError:
            pass

    def _popup_zeigen(self, wegen_maus=False):
        """Das Overlay kurz einblenden — im Pop-up-Betrieb nach einem Fund.

        Der Zähler wird bei jedem neuen Fund neu gestellt: Wer drei Baupläne
        hintereinander bekommt, soll nicht dreimal ein Fenster aufblitzen sehen,
        sondern eines, das stehen bleibt, solange etwas passiert.
        """
        if self.anzeigeart != 'popup':
            return
        try:
            self._anfasser_weg()
            self.root.deiconify()
            self.root.lift()
            self.root.attributes('-topmost', True)
        except tk.TclError:
            return
        if self._popup_uhr is not None:
            try:
                self.root.after_cancel(self._popup_uhr)
            except (tk.TclError, ValueError):
                pass
        sekunden = pfade.einstellung_zahl('popup_sekunden', 6, 2, 60)
        if wegen_maus:
            # Von der Maus geholt: nicht nach ein paar Sekunden wieder wegnehmen,
            # während jemand hinsieht. Es verschwindet, wenn die Maus weg ist —
            # darum kümmert sich `_popup_verstecken`.
            self._wegen_maus = True
        self._popup_uhr = self.root.after(sekunden * 1000, self._popup_verstecken)

    def _popup_verstecken(self):
        self._popup_uhr = None
        if self.anzeigeart != 'popup':
            return
        # Solange die Maus darauf steht, bleibt es stehen. Ein Fenster, das unter
        # dem Mauszeiger verschwindet, während man es ansieht, ist ärgerlicher als
        # eines, das zu lange bleibt.
        # ⚠ Über `<Enter>`/`<Leave>` am Fenster, **nicht** über die Mausposition.
        # Die abzufragen geht unter Wayland nicht: Sobald der Zeiger kein eigenes
        # Fenster mehr berührt, meldet Tk denselben Wert weiter, und das Overlay
        # bliebe für immer stehen.
        if getattr(self, '_maus_drauf', False):
            self._popup_uhr = self.root.after(800, self._popup_verstecken)
            return
        # Solange ein Fenster davor offen ist, bleibt auch das Overlay stehen —
        # sonst verschwindet es unter den Händen, während man die Liste liest.
        for name in ('listenfenster', 'hauptfenster'):
            fenster = getattr(self, name, None)
            try:
                if fenster is not None and fenster.root.winfo_exists():
                    self._popup_uhr = self.root.after(2000, self._popup_verstecken)
                    return
            except (tk.TclError, AttributeError):
                pass
        try:
            # Die Lage merken, bevor das Fenster verschwindet — danach meldet Tk
            # für ein verstecktes Fenster keine brauchbaren Werte mehr, und die
            # Mauswache wüsste nicht, wo sie hinsehen soll.
            jetzt = self._current_geom()
            if '+' in jetzt and not jetzt.startswith('1x1'):
                self._letzte_lage = jetzt
            self.root.withdraw()
            self._anfasser_zeigen()
        except tk.TclError:
            pass

    def hervorholen(self):
        """Von außen gerufen: Fenster her, egal in welchem Betrieb.

        Das ist der Rückweg aus dem Pop-up-Betrieb. Ausgelöst wird er dadurch,
        dass jemand das Programm ein zweites Mal startet (siehe
        `scbp/overlay.py`) — auf die Verknüpfung lässt sich eine ganz normale
        Tastenkombination des Systems legen.
        """
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.liste_oeffnen()
        except Exception as ausnahme:
            fehler.merken('overlay.hervorholen', ausnahme)

    def ablagesymbol_starten(self):
        """Das Symbol neben der Uhr — nur unter Windows und nur, wenn gewünscht.

        ⚠ Es gehört zum Pop-up-Betrieb: Blendet sich das Overlay nur noch bei
        einem Fund ein, braucht es einen Weg zurück. Unter Linux ist das der
        Startmenü-Eintrag, unter Windows dieses Symbol.
        """
        # ⚠ Jeder Ausgang wird in den Startverlauf geschrieben. Zweimal wurde
        # hier auf Verdacht repariert (rc24, rc29), weil niemand sagen konnte,
        # ob das Symbol scheitert oder gar nicht erst versucht wird — Haldjas'
        # Bericht zeigte weder einen Fehler noch eine Spur. Eine Zeile im
        # Startverlauf beantwortet das beim nächsten Bericht sofort.
        if not ablagesymbol.moeglich():
            fehler.spur('Ablagesymbol: entfällt (nicht Windows)')
            return
        if not pfade.einstellung_wahrheit('tray', True):
            fehler.spur('Ablagesymbol: abgeschaltet (Einstellung „tray")')
            return
        try:
            self._ablage = ablagesymbol.Ablagesymbol(
                beim_zeigen=lambda: self.root.after(0, self.hervorholen),
                beim_beenden=lambda: self.root.after(0, self._ganz_beenden))
            geklappt = self._ablage.starten(sprache.t('tray_zeigen'),
                                            sprache.t('tray_beenden'))
            fehler.spur('Ablagesymbol: %s'
                        % ('steht' if geklappt else 'NICHT angelegt'))
            if not geklappt:
                # Der Rückgabewert wurde bisher weggeworfen. Ein „nein" ist
                # aber genau die Auskunft, die in den Bericht gehört.
                fehler.merken('overlay.ablagesymbol',
                              OSError('Ablagesymbol.starten() meldet, dass es '
                                      'nicht angelegt werden konnte'))
        except Exception as ausnahme:
            fehler.spur('Ablagesymbol: Fehler beim Anlegen')
            fehler.merken('overlay.ablagesymbol', ausnahme)

    def run(self):
        self.verhalten_anwenden()
        self.ablagesymbol_starten()
        # Ein zweiter Start soll das vorhandene Fenster hervorholen, statt eine
        # zweite Fassung zu öffnen. Der Rückruf kommt aus einem eigenen Faden —
        # deshalb die Arbeit per `after` an Tk übergeben, nicht dort erledigen.
        overlay.waechter_starten(
            lambda: self.root.after(0, self.hervorholen))
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
    # ⚠ Läuft schon eine Fassung? Dann keine zweite öffnen, sondern der
    # vorhandenen sagen, sie soll sich zeigen. Genau darüber führt der Weg zurück,
    # wenn das Overlay im Pop-up-Betrieb unsichtbar ist.
    if overlay.zeigen_bitte():
        sys.exit(0)

    # ⚠ Windows-Kennzeichen, damit der Installer uns findet und vor dem
    # Überschreiben schließen kann. Ohne das bricht das Setup mitten im
    # Kopieren ab: „DeleteFile failed; code 32 — Der Prozess kann nicht auf die
    # Datei zugreifen, da sie von einem anderen Prozess verwendet wird."
    # Beim Testen so gemeldet (Haldjas, 25.08.2026); die Installation blieb halb
    # fertig liegen, und danach startete nur noch das Setup.
    #
    # Der Name muss mit `AppMutex` in `packaging/installer.iss` übereinstimmen.
    # Das Kennzeichen wird nur gesetzt, nie abgefragt — den Einzelstart regelt
    # `overlay.zeigen_bitte()` oben.
    if pfade.WINDOWS:
        try:
            import ctypes
            ctypes.windll.kernel32.CreateMutexW(
                None, False, 'SC-BP-Watcher-Einzelstart')
        except Exception as ausnahme:
            fehler.merken('start.mutex', ausnahme)

    # ⚠ Die **eine** Tk-Instanz des Programms. Sie entsteht hier und wird an alles
    # weitergereicht — Assistent wie Overlay. Vorher legte der Assistent eine
    # eigene an und zerstörte sie am Ende; die zweite, die das Overlay danach
    # anlegte, lief auf einem Interpreter, in dem noch Schriften und Bilder der
    # ersten hingen. Ergebnis war ein `SIGSEGV` beim **ersten** Programmstart —
    # also bei jedem neuen Nutzer, und nur dort, weil der Assistent nur einmal
    # läuft. Gemeldet von Bomb20 am 25.08.2026.
    #
    # Sie bleibt versteckt, bis das Overlay sie übernimmt: Ein leeres graues
    # Fenster hinter dem Assistenten hätte niemand erklären können.
    fehler.spur('Start, Fassung %s, %s' % (__version__, sys.platform))
    wurzel = tk.Tk()
    wurzel.withdraw()
    fehler.spur('Tk-Wurzel steht')

    zeige_liste = False
    if assistent.noetig():
        fehler.spur('Assistent beginnt')
        fertig, zeige_liste = assistent.starten(eltern=wurzel)
        fehler.spur('Assistent fertig (Liste zeigen: %s)' % zeige_liste)
        if not fertig:
            sys.exit(0)                 # Nutzer hat abgebrochen
    fehler.spur('Overlay wird gebaut')
    fenster = Overlay(wurzel=wurzel)
    fehler.spur('Overlay steht')
    if zeige_liste:
        fehler.spur('Bauplan-Liste wird geöffnet')
        fenster.liste_oeffnen()
        fehler.spur('Bauplan-Liste steht')
    fehler.spur('Hauptschleife läuft')
    fenster.run()
