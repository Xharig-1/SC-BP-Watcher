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
Die Titelleiste des Systems dunkel stellen (nur Windows).

Das Fenster ist von innen komplett dunkel — und obendrauf sass eine **weisse**
Leiste mit dem Fenstertitel und den drei Knoepfen. Am 31.08.2026 gemeldet:
„die Kopfleiste ist weiss, das ist mega haesslich". Sie gehoert nicht zum
Programm, sondern zu Windows: Wer im System das helle Design faehrt, bekommt
sie hell — egal, wie dunkel der Inhalt ist.

Windows laesst sie sich fensterweise umstellen, ueber
`DwmSetWindowAttribute` mit `DWMWA_USE_IMMERSIVE_DARK_MODE`. Reine
`ctypes`-Sache, kein Zusatzpaket — die Grundregel des Projekts bleibt
unangetastet.

⚠ **Die Kennzahl hat sich einmal geaendert.** Bis Windows 10 Build 18985 war
sie **19**, danach **20**. Deshalb werden beide versucht: Auf einem alten
System schlaegt 20 fehl und 19 greift, auf einem neuen umgekehrt. Raten waere
hier billiger als eine Fallunterscheidung nach Build-Nummer — die stimmt bei
Insider-Fassungen naemlich nicht.

⚠ **Erst wenn das Fenster wirklich existiert.** Vor dem ersten Zeichnen hat es
noch kein Handle; der Aufruf liefe ins Leere. Deshalb `update_idletasks()`
davor.

⚠ **Es darf nichts kosten, wenn es nicht geht.** Unter Linux, unter Wine, auf
einem Windows ohne `dwmapi` — ueberall gilt: still weiterlaufen. Eine helle
Leiste ist haesslich, ein Absturz beim Fensterbau waere schlimmer.
"""
import sys


ATTRIBUTE = (20, 19)                 # neu zuerst, dann die alte Kennzahl


def dunkel(fenster):
    """Die Titelleiste dieses Fensters dunkel stellen. Sagt, ob es klappte."""
    if not sys.platform.startswith('win'):
        return False
    try:
        import ctypes
        from ctypes import wintypes
        fenster.update_idletasks()
        # ⚠ `winfo_id()` liefert bei Tk das Handle des ZEICHENBEREICHS, nicht
        # des Rahmens. Die Titelleiste haengt am Elternfenster — ohne
        # `GetParent` faerbt man ein Fenster, das gar keine Leiste hat, und
        # der Aufruf meldet trotzdem Erfolg.
        griff = ctypes.windll.user32.GetParent(fenster.winfo_id())
        if not griff:
            return False
        wert = ctypes.c_int(1)
        for kennzahl in ATTRIBUTE:
            ergebnis = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(griff), ctypes.c_uint(kennzahl),
                ctypes.byref(wert), ctypes.sizeof(wert))
            if ergebnis == 0:
                return True
    except Exception:
        pass                          # helle Leiste ist haesslich, nicht schlimm
    return False


def uebernehmen(fenster):
    """Wie `dunkel()`, aber es wirkt auch auf ein schon sichtbares Fenster.

    ⚠ Windows zeichnet die Leiste nicht von selbst neu, wenn das Fenster
    bereits steht. Ein kurzes Aus und Ein zwingt es dazu — sonst bleibt sie
    hell, bis man das Fenster einmal minimiert.
    """
    if not dunkel(fenster):
        return False
    try:
        if fenster.winfo_viewable():
            fenster.withdraw()
            fenster.deiconify()
    except Exception:
        pass
    return True


def einrichten():
    """Jedes Fenster des Programms bekommt die dunkle Leiste — auch kuenftige.

    ⚠⚠ **Eine Stelle statt sieben.** Das Programm baut an sieben Orten echte
    Fenster (Hauptfenster, Bauplan-Liste, Einstellungen, Assistent, Versionen,
    Dialoge, Wurzel). Sie alle einzeln anzufassen hiesse: Das achte wird
    vergessen, und dann sitzt wieder eine weisse Leiste mitten im dunklen
    Programm. Derselbe Weg wie in `tools/unsichtbar.py`.

    ⚠ **Gehaengt wird an `<Map>`, nicht an den Bau.** Vor dem ersten Anzeigen
    gibt es noch kein Fensterhandle — der Aufruf liefe ins Leere und meldete
    trotzdem Erfolg.
    """
    if not sys.platform.startswith('win'):
        return False
    try:
        import tkinter as tk
    except ImportError:
        return False

    for klasse in (tk.Tk, tk.Toplevel):
        if getattr(klasse, '_scbp_dunkle_leiste', False):
            continue
        urspruenglich = klasse.__init__

        def bauen(self, *a, _urspruenglich=urspruenglich, **k):
            _urspruenglich(self, *a, **k)
            try:
                self.bind('<Map>', lambda _e, w=self: _einmal(w), add='+')
            except Exception:
                pass

        klasse.__init__ = bauen
        klasse._scbp_dunkle_leiste = True
    return True


def _einmal(fenster):
    """Beim ersten Anzeigen faerben — danach nie wieder.

    ⚠ `<Map>` feuert bei jedem Wiederherstellen aus der Taskleiste. Ohne
    Merker liefe der Aufruf dutzendfach, und `uebernehmen()` wuerde das
    Fenster dabei jedes Mal kurz aus- und einblenden.
    """
    try:
        if getattr(fenster, '_scbp_leiste_gesetzt', False):
            return
        fenster._scbp_leiste_gesetzt = True
        dunkel(fenster)
    except Exception:
        pass
