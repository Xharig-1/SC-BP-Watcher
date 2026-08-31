# -*- coding: utf-8 -*-
#
# SC BP Watcher — zeigt live neue Star-Citizen-Bauplaene an.
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
Eine Tastenkombination, die auch im Spiel greift.

Star Citizen laeuft im Vollbild und blendet den Mauszeiger aus. Wer nachsehen
will, ob er einen Bauplan schon hat, muss heraustabben und das Fenster dann
**blind** suchen und anklicken. Am 31.08.2026 als Nutzerwunsch gemeldet:
„Hotkey um die Bauplanliste aufzurufen, da man in SC erst raustabben muss und
die Maus ueber dem SC-Fenster nicht sichtbar ist."

## Was auf welchem System geht

| System | Weg | greift im Spiel |
|---|---|---|
| Windows | `RegisterHotKey` (user32) | ja |
| Linux, X11 | `XGrabKey` (libX11) | ja |
| Linux, Wayland | **gar nicht von innen** | — |

⚠⚠ **Wayland ist keine Faulheit, sondern Absicht des Systems.** Ein Programm
darf dort nicht mithoeren, was in einem anderen Fenster getippt wird — genau
das braeuchte ein globaler Hotkey. Der Weg dorthin fuehrt ueber die
Tastenkombinationen des Schreibtischs; `grund()` sagt das, und die
Einstellungsseite zeigt den fertigen Befehl zum Hinterlegen. Der Doppelstart
holt das laufende Programm schon heute nach vorn (siehe `overlay.zeigen_bitte`).

⚠ **Frueher stand hier: „unter Windows fragil".** Das galt fuer
Tastatur-Haken (`SetWindowsHookEx`), die tief im System sitzen und von
Virenwaechtern angefasst werden. `RegisterHotKey` ist etwas anderes: die dafuer
vorgesehene Schnittstelle, seit Windows 95 unveraendert. Sie kann nur eines
nicht — eine Kombination belegen, die schon jemand anders hat. Dann sagt sie
das, und wir geben es weiter, statt so zu tun, als laege es an uns.

## Gelesen wird nicht mitgehoert

⚠⚠ Es wird **eine** Kombination angemeldet, und das System weckt uns nur bei
genau dieser. Alles andere sieht das Programm nie — kein Mitschreiben, kein
Zugriff auf das, was im Spiel getippt wird. Das ist der Unterschied zwischen
`RegisterHotKey` und einem Tastatur-Haken, und er ist der Grund, warum hier
nur der erste Weg in Frage kam.
"""
import os
import sys

# Was sich kombinieren laesst. ⚠ Bewusst klein gehalten: Modifikatoren plus
# EINE gewoehnliche Taste. Wer eine Kombination aus drei Buchstaben zulaesst,
# baut sich Konflikte mit den Spiel-Belegungen, die niemand mehr findet.
MODIFIKATOREN = {
    'strg': 'strg', 'ctrl': 'strg', 'control': 'strg',
    'alt': 'alt',
    'umschalt': 'umschalt', 'shift': 'umschalt',
}

STANDARD = 'Strg+Alt+B'          # B wie Bauplan


def zerlegen(kombination):
    """`"Strg+Alt+B"` -> `({'strg', 'alt'}, 'B')`. Bei Unsinn: `(None, None)`.

    ⚠ Grosz/klein und Leerzeichen sind egal — die Kombination steht in einer
    Einstellungsdatei, die auch von Hand bearbeitet wird.
    """
    if not kombination:
        return None, None
    mods, taste = set(), None
    for teil in str(kombination).replace('-', '+').split('+'):
        teil = teil.strip()
        if not teil:
            continue
        klein = teil.lower()
        if klein in MODIFIKATOREN:
            mods.add(MODIFIKATOREN[klein])
            continue
        if taste is not None:
            return None, None            # zwei gewoehnliche Tasten
        taste = teil.upper()
    if not taste:
        return None, None
    if not (len(taste) == 1 and (taste.isalpha() or taste.isdigit())) and             not (taste.startswith('F') and taste[1:].isdigit()
                 and 1 <= int(taste[1:]) <= 12):
        return None, None
    # ⚠⚠ **Ohne Modifikator nicht.** Eine nackte Taste global zu belegen heisst,
    # sie im Spiel unbrauchbar zu machen — und der Nutzer sucht den Grund dann
    # ueberall, nur nicht hier.
    if not mods:
        return None, None
    return mods, taste


def _wayland():
    return (os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland'
            or (os.environ.get('WAYLAND_DISPLAY') and not os.environ.get('DISPLAY')))


def moeglich():
    """Geht ein echter Hotkey auf diesem System? Gibt `(ja, grund)` zurueck."""
    if sys.platform.startswith('win'):
        return True, ''
    if sys.platform.startswith('linux'):
        if _wayland():
            return False, 'wayland'
        if os.environ.get('DISPLAY'):
            return True, ''
        return False, 'kein_bildschirm'
    return False, 'system'


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------
#
# ⚠ `RegisterHotKey(None, ...)` haengt die Kombination an den **Faden**, nicht
# an ein Fenster. Die Meldung landet damit in der Nachrichtenschlange genau des
# Fadens, der angemeldet hat — deshalb muss beides im Tk-Faden passieren:
# anmelden und nachsehen. Ein Hintergrundfaden bekaeme nie etwas zu sehen.
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
MOD_ALT, MOD_CONTROL, MOD_SHIFT = 0x0001, 0x0002, 0x0004
MOD_NOREPEAT = 0x4000            # nicht dauerfeuern, solange man haelt
KENNUNG = 0xB9CB                 # irgendeine Zahl, nur fuer uns


def _vk(taste):
    """Der Tastencode von Windows fuer unsere kleine Auswahl."""
    if len(taste) == 1 and (taste.isalpha() or taste.isdigit()):
        return ord(taste)
    if taste.startswith('F') and taste[1:].isdigit():
        return 0x70 + int(taste[1:]) - 1        # VK_F1 = 0x70
    return None


class _Windows:
    def __init__(self):
        self.angemeldet = False

    def anmelden(self, mods, taste):
        import ctypes
        flaggen = MOD_NOREPEAT
        flaggen |= MOD_CONTROL if 'strg' in mods else 0
        flaggen |= MOD_ALT if 'alt' in mods else 0
        flaggen |= MOD_SHIFT if 'umschalt' in mods else 0
        code = _vk(taste)
        if code is None:
            return False, 'taste'
        self.abmelden()
        if not ctypes.windll.user32.RegisterHotKey(None, KENNUNG, flaggen, code):
            # ⚠⚠ **Belegt heisst belegt.** Hat ein anderes Programm die
            # Kombination, gibt Windows sie nicht her — daran laesst sich
            # nichts drehen. Der Nutzer muss es erfahren, sonst sucht er den
            # Fehler bei sich.
            return False, 'belegt'
        self.angemeldet = True
        return True, ''

    def abmelden(self):
        if not self.angemeldet:
            return
        try:
            import ctypes
            ctypes.windll.user32.UnregisterHotKey(None, KENNUNG)
        except Exception:
            pass
        self.angemeldet = False

    def nachsehen(self):
        """Wurde gedrueckt? Nimmt die Meldung aus der Schlange."""
        if not self.angemeldet:
            return False
        try:
            import ctypes
            from ctypes import wintypes

            class MSG(ctypes.Structure):
                _fields_ = [('hwnd', wintypes.HWND), ('message', wintypes.UINT),
                            ('wParam', wintypes.WPARAM), ('lParam', wintypes.LPARAM),
                            ('time', wintypes.DWORD), ('pt', wintypes.POINT)]

            msg = MSG()
            getroffen = False
            # ⚠ Alle abholen, die aufgelaufen sind — sonst bleibt eine liegen
            # und feuert beim naechsten Nachsehen ein zweites Mal.
            while ctypes.windll.user32.PeekMessageW(
                    ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
                if msg.wParam == KENNUNG:
                    getroffen = True
            return getroffen
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Linux, X11
# ---------------------------------------------------------------------------
#
# ⚠ **Eine EIGENE Verbindung zum Bildschirm, nicht die von Tk.** Tk verarbeitet
# seine Ereignisse selbst; wer sich in dieselbe Verbindung setzt, klaut ihm
# welche und das Fenster reagiert nicht mehr richtig. Eine zweite Verbindung
# kostet fast nichts und stoert niemanden.
SHIFT_MASK, LOCK_MASK, CONTROL_MASK, MOD1_MASK, MOD2_MASK = 1, 2, 4, 8, 16
KEY_PRESS = 2
GRAB_ASYNC = 1

# ⚠⚠ **Feststell- und Nummerntaste zaehlen als Modifikator mit.** Wer nur die
# reine Kombination anmeldet, bekommt sie nicht mehr, sobald jemand Num-Lock
# eingeschaltet hat — und das ist der Normalzustand an einer Tastatur mit
# Ziffernblock. Deshalb alle vier Spielarten anmelden.
ZUSATZ = (0, LOCK_MASK, MOD2_MASK, LOCK_MASK | MOD2_MASK)


class _X11:
    def __init__(self):
        self.lib = None
        self.anzeige = None
        self.wurzel = None
        self.gegriffen = []

    def _laden(self):
        if self.lib is not None:
            return True
        import ctypes
        import ctypes.util
        pfad = ctypes.util.find_library('X11')
        if not pfad:
            return False
        self.lib = ctypes.cdll.LoadLibrary(pfad)
        self.lib.XOpenDisplay.restype = ctypes.c_void_p
        self.lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.lib.XDefaultRootWindow.restype = ctypes.c_ulong
        self.lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.lib.XStringToKeysym.restype = ctypes.c_ulong
        self.lib.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.lib.XKeysymToKeycode.restype = ctypes.c_ubyte
        self.lib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.anzeige = self.lib.XOpenDisplay(None)
        if not self.anzeige:
            self.lib = None
            return False
        self.wurzel = self.lib.XDefaultRootWindow(self.anzeige)
        return True

    def anmelden(self, mods, taste):
        import ctypes
        if not self._laden():
            return False, 'kein_x11'
        maske = 0
        maske |= CONTROL_MASK if 'strg' in mods else 0
        maske |= MOD1_MASK if 'alt' in mods else 0
        maske |= SHIFT_MASK if 'umschalt' in mods else 0
        # X11 nennt die Tasten beim Namen: 'b', '5', 'F3'.
        name = taste.lower() if len(taste) == 1 else taste
        keysym = self.lib.XStringToKeysym(name.encode('ascii', 'ignore'))
        if not keysym:
            return False, 'taste'
        code = self.lib.XKeysymToKeycode(self.anzeige, keysym)
        if not code:
            return False, 'taste'
        self.abmelden()
        for zusatz in ZUSATZ:
            self.lib.XGrabKey(ctypes.c_void_p(self.anzeige), ctypes.c_int(code),
                              ctypes.c_uint(maske | zusatz),
                              ctypes.c_ulong(self.wurzel), ctypes.c_int(1),
                              ctypes.c_int(GRAB_ASYNC), ctypes.c_int(GRAB_ASYNC))
            self.gegriffen.append((code, maske | zusatz))
        self.lib.XSync(ctypes.c_void_p(self.anzeige), ctypes.c_int(0))
        # ⚠ X11 sagt beim Greifen nicht, ob es geklappt hat — der Fehler kommt
        # asynchron. Wir melden Erfolg und lassen den Nutzer sehen, ob die
        # Taste wirkt; eine Falschmeldung „belegt" waere hier geraten.
        return True, ''

    def abmelden(self):
        if not self.gegriffen or self.lib is None:
            self.gegriffen = []
            return
        try:
            import ctypes
            for code, maske in self.gegriffen:
                self.lib.XUngrabKey(ctypes.c_void_p(self.anzeige),
                                    ctypes.c_int(code), ctypes.c_uint(maske),
                                    ctypes.c_ulong(self.wurzel))
            self.lib.XSync(ctypes.c_void_p(self.anzeige), ctypes.c_int(0))
        except Exception:
            pass
        self.gegriffen = []

    def nachsehen(self):
        if not self.gegriffen or self.lib is None:
            return False
        try:
            import ctypes
            puffer = (ctypes.c_byte * 224)()      # XEvent ist hoechstens so gross
            getroffen = False
            while self.lib.XPending(ctypes.c_void_p(self.anzeige)) > 0:
                self.lib.XNextEvent(ctypes.c_void_p(self.anzeige),
                                    ctypes.byref(puffer))
                if ctypes.cast(ctypes.byref(puffer),
                               ctypes.POINTER(ctypes.c_int))[0] == KEY_PRESS:
                    getroffen = True
            return getroffen
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Die Wache — eine Stelle für beide Systeme
# ---------------------------------------------------------------------------


class Wache:
    """Meldet die Kombination an und sagt auf Nachfrage, ob gedrückt wurde.

    ⚠⚠ **Es wird NICHT mitgehört.** Angemeldet wird genau eine Kombination;
    alles andere sieht das Programm nie. Das ist der Unterschied zu einem
    Tastatur-Haken — und der Grund, warum hier nur dieser Weg in Frage kam.

    ⚠ **Gefragt wird im Tk-Faden**, nicht in einem eigenen. Unter Windows
    landet die Meldung in der Schlange genau des Fadens, der angemeldet hat;
    ein Hintergrundfaden bekäme nie etwas zu sehen. Also hängt `nachsehen()`
    am selben Takt wie die übrige Warteschlange.
    """

    def __init__(self):
        self.helfer = None
        self.kombination = ''
        self.grund = ''

    def anmelden(self, kombination):
        """Sagt `(ja, grund)`. `grund` ist ein Kürzel, kein fertiger Satz —
        die Oberfläche macht daraus einen Text in der richtigen Sprache."""
        self.abmelden()
        geht, warum = moeglich()
        if not geht:
            self.grund = warum
            return False, warum
        mods, taste = zerlegen(kombination)
        if not mods:
            self.grund = 'kombination'
            return False, 'kombination'
        helfer = _Windows() if sys.platform.startswith('win') else _X11()
        ok, warum = helfer.anmelden(mods, taste)
        if not ok:
            self.grund = warum
            return False, warum
        self.helfer = helfer
        self.kombination = kombination
        self.grund = ''
        return True, ''

    def abmelden(self):
        if self.helfer is not None:
            try:
                self.helfer.abmelden()
            except Exception:
                pass
        self.helfer = None
        self.kombination = ''

    def nachsehen(self):
        """Wurde die Kombination seit dem letzten Mal gedrückt?"""
        if self.helfer is None:
            return False
        try:
            return bool(self.helfer.nachsehen())
        except Exception:
            return False
