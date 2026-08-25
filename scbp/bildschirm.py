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
Welcher Bildschirm ist der Hauptbildschirm — und wo ist dessen Mitte?

**Warum es dieses Modul gibt.** Tk kennt nur *einen* Bildschirm: Bei mehreren
Monitoren meldet `winfo_screenwidth()` die Größe der gesamten zusammengesetzten
Fläche. Wer ein Fenster damit „mittig" setzt, landet bei drei Monitoren genau auf
einer Kante — oder in einer Lücke, wenn die Bildschirme unterschiedlich hoch sind.
Ohne Positionsangabe stellt Tk das Fenster irgendwohin, in der Praxis nach `+0+0`;
bei einem hochkant gestellten Monitor links außen ist das ein Bereich, in dem gar
kein Bild liegt. Genau so ist das Overlay einmal unauffindbar geworden.

Deshalb wird der Hauptbildschirm hier beim jeweiligen System erfragt:

  * **Windows** — `GetSystemMetrics`. Der Primärbildschirm liegt dort immer bei
    (0,0), seine Größe steht in SM_CXSCREEN/SM_CYSCREEN. Das ist der Zielfall:
    Star Citizen gibt es nur unter Windows.
  * **Linux** — `xrandr --listmonitors`. Die Zeile mit dem Stern ist der primäre
    Monitor, dahinter steht seine Lage. Das funktioniert auch unter Wayland, weil
    Tk ohnehin über XWayland läuft und dort dieselben Angaben ankommen (samt
    Skalierung, die Tk auch sonst benutzt).
  * **Sonst** — die gesamte Fläche. Schlechter als nichts ist es nicht.

Alles ist gutmütig gebaut: Findet sich nichts, wird die Tk-Fläche genommen, statt
einen Fehler zu werfen. Eine falsch platzierte Fensterecke darf nie ein Programm
anhalten.
"""
import os
import re
import subprocess
import sys

# Das Overlay-Fenster. Das Hauptprogramm trägt sich hier beim Start ein, damit der
# Knopf „Fensterlage zurücksetzen" es sofort verschieben kann — ohne dass dieses
# Modul das Hauptprogramm importieren muss (das gäbe einen Ringschluss).
OVERLAY = [None]

WINDOWS = sys.platform.startswith('win')

# Zeilenform von `xrandr --listmonitors`:
#   0: +*DP-2 5120/1193x1440/336+1080+1440  DP-2
# Gebraucht werden die vier Zahlen: Breite, Höhe, X, Y. Die Angaben mit Schrägstrich
# dahinter sind Millimeter — die interessieren nicht.
_XRANDR = re.compile(r'^\s*\d+:\s*\+\*\S*\s+(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)')


def _ganze_flaeche(root):
    """Rückfall: alles, was Tk sieht."""
    try:
        return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
    except Exception:
        return 0, 0, 1920, 1080


def _windows_hauptschirm():
    try:
        import ctypes
        benutzer = ctypes.windll.user32
        # 0 = SM_CXSCREEN, 1 = SM_CYSCREEN — beides bezieht sich auf den Primärschirm.
        breite = int(benutzer.GetSystemMetrics(0))
        hoehe = int(benutzer.GetSystemMetrics(1))
        if breite > 0 and hoehe > 0:
            return 0, 0, breite, hoehe
    except Exception:
        pass
    return None


def _linux_hauptschirm():
    try:
        umgebung = dict(os.environ)
        umgebung['LC_ALL'] = 'C'
        ausgabe = subprocess.run(['xrandr', '--listmonitors'],
                                 capture_output=True, text=True, timeout=3,
                                 env=umgebung).stdout
        for zeile in ausgabe.splitlines():
            treffer = _XRANDR.match(zeile)
            if treffer:
                b, h, x, y = (int(z) for z in treffer.groups())
                if b > 0 and h > 0:
                    return x, y, b, h
    except Exception:
        pass
    return None


def hauptbildschirm(root):
    """Lage und Größe des Hauptbildschirms als (x, y, breite, hoehe)."""
    gefunden = _windows_hauptschirm() if WINDOWS else _linux_hauptschirm()
    return gefunden or _ganze_flaeche(root)


def mittig(root, breite, hoehe):
    """Geometrie-Angabe für ein Fenster in der Mitte des Hauptbildschirms.

    Das Ergebnis ist die übliche Tk-Form `BREITExHOEHE+X+Y`. Passt das Fenster
    nicht auf den Bildschirm, wird es an dessen Kante gesetzt statt darüber hinaus —
    ein Fenster, dessen Titelleiste oberhalb des Bildes liegt, lässt sich nicht mehr
    anfassen.
    """
    sx, sy, sb, sh = hauptbildschirm(root)
    x = sx + max(0, (sb - breite) // 2)
    y = sy + max(0, (sh - hoehe) // 2)
    return '%dx%d+%d+%d' % (breite, hoehe, x, y)
