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

Überwacht:  %APPDATA%\\sc-deutsch-launcher\\blueprints\\sc_bp_erledigt.json
            + (ab v1.2.0) die Star-Citizen-Game.log für die Sofort-Meldung
            + (ab v1.3.0) bp_item_types.json — meldet, was im Spiel NEU craftbar wurde
Anzeige:    kleines, immer-im-Vordergrund Overlay-Fenster (verschiebbar).

Reines Python-Standardbibliothek-Tool (tkinter) — keine Zusatzpakete nötig.
Läuft unter Windows mit dem normalen Python.
"""
import os, re, json, time, threading, queue
import tkinter as tk
from tkinter import font as tkfont
try:
    import winsound
except ImportError:
    winsound = None

__version__ = '1.4.0'

# ---------------------------------------------------------------- Konfiguration
BP_DIR   = os.path.join(os.environ.get('APPDATA', ''), 'sc-deutsch-launcher', 'blueprints')
BP_FILE  = os.path.join(BP_DIR, 'sc_bp_erledigt.json')
TYPE_FILE = os.path.join(BP_DIR, 'bp_item_types.json')
CAT_DIR  = os.path.join(BP_DIR, 'catalog')                       # Launcher-Katalog (Size/Grade/Klasse)
SCDL_SETTINGS = os.path.join(BP_DIR, 'scdl-settings.json')       # kennt den SC-Installationsordner
SCAN_STATE    = os.path.join(BP_DIR, 'scan-state.json')          # kennt die zuletzt gelesene Game.log
# Manuelle Korrekturen an Size/Grade/Klasse, Vorrang vor dem Launcher-Katalog.
# Standard: neben den eigenen Einstellungen in %APPDATA%\sc-bp-watcher\.
# Wer die Datei woanders pflegt, setzt die
# Umgebungsvariable SC_BP_OVERRIDES auf den vollen Pfad. Fehlt beides, gilt der
# Katalog unverändert — die Datei ist optional.
OVERRIDES_FILE = os.environ.get('SC_BP_OVERRIDES') or os.path.join(
    os.environ.get('APPDATA', ''), 'sc-bp-watcher', 'bp-overrides.json')
POLL_SEC = 3            # wie oft die Dateien geprüft werden (Sekunden)
MAX_ROWS = 200          # so viele Neuzugänge max. in der Liste behalten

# --- Katalog-Wache (ab v1.3.0) ---------------------------------------------
# `bp_item_types.json` listet, was im Spiel überhaupt craftbar ist. Der Launcher
# frischt sie mit den SC-Patches auf. Wächst sie, ist etwas NEU craftbar geworden —
# unabhängig davon, ob man es freigeschaltet hat. Der Stand liegt bewusst in einer
# eigenen Datei, damit ein zweites Werkzeug auf denselben Daten dem Watcher
# nicht die Meldung wegnimmt.
APP_DIR    = os.path.join(os.environ.get('APPDATA', ''), 'sc-bp-watcher')
CAT_SEEN   = os.path.join(APP_DIR, 'catalog-seen.json')
# Optionale Beobachtungsliste: Gegenstände, auf die man besonders wartet.
# Format: {"eintraege": [{"titel": "…", "muster": ["teilstring", …]}, …]} — Muster
# kleingeschrieben, Treffer per Teilstring. Fehlt die Datei, meldet der Watcher
# einfach jeden Katalog-Zuwachs.
WATCHLIST  = os.path.join(APP_DIR, 'watchlist.json')
CAT_POLL   = 60         # Katalogdatei nur jede Minute prüfen (ändert sich nur bei Patches)

# Fensterposition/-größe. Standard = dort, wo Xharig es haben will: oberer Monitor
# (nicht der Spiel-Monitor) → man tabbt nicht mehr versehentlich aus dem Spiel.
# Wird beim Beenden/Verschieben in SETTINGS_FILE gespeichert und beim nächsten Start
# von dort wiederhergestellt. Format: BxH+X+Y (negatives Y als „+-1439" = absolut).
DEFAULT_GEOM  = '440x1098+3656+-1439'
SETTINGS_FILE = os.path.join(os.environ.get('APPDATA', ''), 'sc-bp-watcher', 'watcher.json')

# Farben (dunkles Overlay)
BG, FG, ACCENT, SUB, BAR = '#10141c', '#e6edf3', '#47aa42', '#8b98a5', '#1b2230'
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
    try:
        with open(TYPE_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def load_watchlist():
    """Optionale Beobachtungsliste -> [(Titel, [Muster, …]), …]. Fehlt sie, ist sie leer."""
    try:
        with open(WATCHLIST, encoding='utf-8') as f:
            eintraege = json.load(f).get('eintraege', [])
        return [(e['titel'], [m.lower() for m in e.get('muster', [])])
                for e in eintraege if e.get('muster')]
    except Exception:
        return []


TYPES = load_types()
def art_of(key):
    global TYPES
    k = key.lower().replace('\xa0', ' ')
    art = TYPES.get(k)
    if art is None:
        # Frisch freigeschaltetes Item kann neu im Katalog sein -> einmal nachladen
        TYPES = load_types()
        art = TYPES.get(k)
    return art or '—'


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


def _size_grade_class(key):
    lk = _norm(key)
    if lk in COMP:
        cl, sz, gr = COMP[lk]
        return sz, gr, _CLASS_FULL.get(cl, cl)
    s = SIZE_BY_NAME.get(lk) or SIZE_BY_NAME.get(key.lower())
    if s is None:  # Skin-/Sondervariante (Zusatz in "…") erbt die Size der Basis
        base = re.sub(r'\s+', ' ', re.sub(r'\s*"[^"]*"\s*', ' ', lk)).strip()
        if base != lk: s = SIZE_BY_NAME.get(base)
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
# Das Spiel schreibt beim Freischalten eine Notification im Klartext, z. B.:
#   <SHUDEvent_OnNotification> Added notification "Bauplan erhalten: Attrition-5 Repeater: " [136] …
# Der SC Deutsch Launcher liest dieselbe Log, exportiert seine Datei aber nur alle
# paar Minuten — deshalb lesen wir den Namen zusätzlich selbst mit und zeigen ihn
# sofort als „vorläufig" (gelb) an. Sobald der Launcher nachzieht, wird die Zeile
# bestätigt (grün). Size/Grade/Klasse/Art kommen weiterhin aus dem Launcher-Katalog.
#
# Nur die deutsche Meldung ist verifiziert (Xharigs Client, Translation "de"). Bei
# anderer Spielsprache greift der Log-Weg einfach nicht — dann bleibt es beim
# bisherigen Verhalten (Meldung erst, wenn der Launcher exportiert hat).
LOG_PHRASES = ['Bauplan erhalten']
LOG_RE = re.compile(r'Added notification "(?:%s):\s*(.+?)\s*:\s*"'
                    % '|'.join(re.escape(p) for p in LOG_PHRASES))

# Schiffskomponenten stehen im Log MIT Zusatz „(Klasse/Size/Grade)", z. B.
# „7CA 'Nargun' (Civ/3/A)" — der Launcher-Schlüssel ist aber „7CA 'Nargun'".
# Ohne Abschneiden würde die Bestätigung nie greifen (Zeile bliebe gelb + Dublette).
# Bewusst eng gefasst (nur die bekannten Klassen-Kürzel), damit echte Namens-Klammern
# wie „(30 cap)" oder „Singe Cannon (S2)" unangetastet bleiben.
LOG_SUFFIX_RE = re.compile(r'\s*\((Civ|Mil|Ind|Sth|Cmp)/(\d+)/([A-D])\)\s*$', re.I)


def clean_log_name(name):
    """('7CA 'Nargun'', 'C/A/3')  aus  \"7CA 'Nargun' (Civ/3/A)\".
    Zweiter Wert = Kürzel aus dem Log-Zusatz (None, wenn keiner da war)."""
    m = LOG_SUFFIX_RE.search(name)
    if not m:
        return name.strip(), None
    cl, sz, gr = m.group(1).title(), m.group(2), m.group(3).upper()
    letter = CLASS_LETTER.get(_CLASS_FULL.get(cl, cl), '–')
    return name[:m.start()].strip(), f'{letter}/{gr}/{sz}'


def _loose(name):
    """Name ohne Klammer-Zusatz am Ende — für den Notfall-Abgleich, wenn Log und
    Launcher unterschiedlich übersetzt sind (gesehen: „Scalpel Sniper Rifle Magazine
    (12 Schuss)" im Log vs. „… (12 cap)" beim Launcher)."""
    return re.sub(r'\s*\([^()]*\)\s*$', '', _norm(name)).strip()


def find_game_log():
    """Pfad zur aktiven Game.log — 1. aus den Launcher-Einstellungen (Installfolder),
    2. aus dem Lesestand des Launchers (scan-state.json), 3. Standard-Installpfad."""
    cands = []
    try:
        for s in json.load(open(SCDL_SETTINGS, encoding='utf-8')).get('Settings', []):
            f = s.get('Installfolder')
            if f: cands.append(os.path.join(f, 'Game.log'))
    except Exception:
        pass
    try:
        for p in json.load(open(SCAN_STATE, encoding='utf-8')).get('files', {}):
            if os.path.basename(p).lower() == 'game.log' and 'logbackups' not in p.lower():
                cands.append(p)
    except Exception:
        pass
    cands.append(r'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Game.log')
    for p in cands:
        try:
            if os.path.isfile(p): return p
        except Exception:
            pass
    return None


class LogTail:
    """Liest die Game.log fortlaufend ab dem Startzeitpunkt (Historie wird ignoriert).
    Erkennt einen Spiel-Neustart daran, dass die Datei kürzer wird als der Lesestand —
    dann wird von vorn gelesen (frische Log = nur die laufende Session)."""

    def __init__(self):
        self.path, self.offset = None, 0

    def _locate(self):
        p = find_game_log()
        if p and p != self.path:
            self.path = p
            try: self.offset = os.path.getsize(p)   # ab jetzt mitlesen, nicht die Historie
            except OSError: self.offset = 0
        elif not p:
            self.path = None
        return self.path

    def new_names(self):
        """Neue Bauplan-Namen seit dem letzten Aufruf (Liste, evtl. leer)."""
        if not self._locate():
            return []
        try:
            size = os.path.getsize(self.path)
            if size < self.offset:      # Log rotiert -> neue Spiel-Session
                self.offset = 0
            if size == self.offset:
                return []
            with open(self.path, 'rb') as f:
                f.seek(self.offset)
                chunk = f.read()
        except OSError:
            return []
        cut = chunk.rfind(b'\n')        # angefangene letzte Zeile stehen lassen
        if cut < 0:
            return []
        self.offset += cut + 1
        text = chunk[:cut].decode('utf-8', 'ignore')
        return [clean_log_name(m.group(1)) for m in LOG_RE.finditer(text)]


# ------------------------------------------------ Fensterposition merken/laden
def load_geometry():
    try:
        g = json.load(open(SETTINGS_FILE, encoding='utf-8')).get('geometry')
        return g or DEFAULT_GEOM
    except Exception:
        return DEFAULT_GEOM


def save_geometry(geom):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        json.dump({'geometry': geom}, open(SETTINGS_FILE, 'w', encoding='utf-8'))
    except Exception:
        pass


# ---------------------------------------------------------------- Watcher-Thread
class Watcher(threading.Thread):
    def __init__(self, out_queue):
        super().__init__(daemon=True)
        self.q = out_queue
        self.known = None       # BP-Namen aus der Launcher-Datei
        self.seen = set()       # schon angezeigte Namen (normalisiert) — gegen Dubletten
        self.prov = {}          # noch unbestätigt: norm(Log-Name) -> Log-Name
        self.tail = LogTail()
        self.running = True
        self.cat_next = 0.0     # nächster Katalog-Check (Zeitstempel)
        self.cat_mtime = None   # letzter gesehener Änderungszeitpunkt der Katalogdatei

    # ---- Katalog-Wache: was ist NEU craftbar im Spiel? ----
    def _catalog_tick(self):
        """Prüft, ob der Craftbar-Katalog gewachsen ist. Der Vergleichsstand überlebt
        Neustarts (CAT_SEEN), sonst käme nach jedem Programmstart alles doppelt."""
        try:
            mt = os.path.getmtime(TYPE_FILE)
        except OSError:
            return
        if mt == self.cat_mtime:
            return
        self.cat_mtime = mt
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
        muster, anzeige = load_watchlist(), load_display()
        for name in neu:
            titel = next((t for t, muss in muster if any(m in name for m in muss)), None)
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

    def run(self):
        # Basisstand setzen (nicht alle vorhandenen BPs als "neu" melden)
        while self.known is None and self.running:
            self.known = load_keys()
            if self.known is None:
                time.sleep(POLL_SEC)
        self.seen = {_norm(k) for k in self.known}
        self.tail.new_names()          # Lesestand der Game.log auf „jetzt" setzen
        self.q.put(('status', f'Überwache {len(self.known)} BPs …'))
        while self.running:
            time.sleep(POLL_SEC)

            # 1) Game.log: sofortige, aber noch unbestätigte Meldung
            for name, log_meta in self.tail.new_names():
                nk = _norm(name)
                if nk in self.seen:
                    continue
                self.seen.add(nk)
                self.prov[nk] = name
                self._emit(name, True, log_meta)

            # 2) Launcher-Datei: die verbindliche Quelle (bestätigt bzw. meldet nach)
            cur = load_keys()
            if cur is None:
                continue
            for k in sorted(cur - self.known):
                row = self._match_prov(k)
                dup = _norm(k) in self.seen      # steht schon in der Liste
                self.seen.add(_norm(k))
                if row:
                    self.q.put(('confirm', row, k, art_of(k), meta_of(k)))
                elif not dup:
                    self._emit(k, False)
            self.known = cur

            # 3) Katalog-Wache (selten, die Datei ändert sich nur bei SC-Patches)
            if time.time() >= self.cat_next:
                self.cat_next = time.time() + CAT_POLL
                self._catalog_tick()

            log_state = '✓' if self.tail.path else '–'
            self.q.put(('status', f'Überwache {len(cur)} BPs · Log {log_state} · '
                                  f'geprüft {time.strftime("%H:%M:%S")}'))

    def stop(self):
        self.running = False


# ---------------------------------------------------------------- GUI / Overlay
class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('SC BP Watcher')
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)          # randloses Overlay
        self.root.attributes('-topmost', True)    # immer im Vordergrund
        self.root.attributes('-alpha', 0.93)      # leicht durchscheinend
        self.root.geometry(load_geometry())
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
        tk.Label(bar, text=f'● SC BP Watcher v{__version__}', bg=BAR, fg=ACCENT,
                 font=self.f_title).pack(side='left', padx=8)
        tk.Label(bar, text='✕', bg=BAR, fg=SUB, font=self.f_title,
                 cursor='hand2').pack(side='right', padx=8)
        bar.winfo_children()[-1].bind('<Button-1>', lambda e: self.quit())
        tk.Label(bar, text='🗑', bg=BAR, fg=SUB, font=self.f_title,
                 cursor='hand2').pack(side='right')
        bar.winfo_children()[-1].bind('<Button-1>', lambda e: self.clear())
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
        grip = tk.Label(self.root, text='◢', bg=BG, fg=SUB, cursor='size_nw_se')
        grip.place(relx=1.0, rely=1.0, anchor='se')
        grip.bind('<B1-Motion>', self._resize)
        grip.bind('<ButtonRelease-1>', self._save_geo)    # Größe nach dem Skalieren merken

        # Watcher starten
        self.q = queue.Queue()
        self.watcher = Watcher(self.q)
        self.watcher.start()
        self.root.after(200, self._poll_queue)

    # ---- Drag & Resize ----
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
        if winsound:
            try: winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception: pass

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
        if winsound:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION if titel
                                     else winsound.MB_ICONASTERISK)
            except Exception:
                pass

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
                elif msg[0] == 'new':
                    self.add_new(msg[1], msg[2], msg[3], msg[4], msg[5])
                elif msg[0] == 'confirm':
                    self.confirm(msg[1], msg[2], msg[3], msg[4])
                elif msg[0] == 'catalog':
                    self.add_catalog(msg[1], msg[2], msg[3], msg[4])
        except queue.Empty:
            pass
        self.root.after(300, self._poll_queue)

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
    if not os.path.exists(BP_FILE):
        # Minimaler Hinweis, falls der Launcher-Ordner fehlt
        r = tk.Tk(); r.title('SC BP Watcher')
        tk.Label(r, text='Datei nicht gefunden:\n' + BP_FILE +
                 '\n\nIst der SC Deutsch Launcher installiert?',
                 justify='left', padx=20, pady=20).pack()
        r.mainloop()
    else:
        Overlay().run()
