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
Der Signalton — und warum `bell()` unter Linux nichts taugt.

Bis v2.0.0-rc3 rief der Watcher unter Linux `tkinter.bell()` auf, mit dem
Kommentar „bleibt es still, ist das kein Fehler". Beim ersten echten Drop am
24.08.2026 blieb es still — und **das** war der Fehler: `bell()` ist die
**X11-Systemglocke**, und die ist auf modernen Arbeitsplätzen praktisch
überall aus. Unter Wayland/XWayland gibt es sie faktisch gar nicht mehr; auf
dem Testrechner fehlte sogar `xset`, mit dem man sie einschalten könnte.

Ein Signalton, der genau dann nicht kommt, wenn er gebraucht wird, ist
schlimmer als keiner: Man verlässt sich darauf und verpasst den Drop.

**Der Weg stattdessen:** ein vorhandenes Abspielprogramm mit einem
Systemklang. Alle drei unten sind auf verbreiteten Linux-Systemen dabei,
keines ist ein Zusatzpaket für dieses Projekt — aufgerufen wird über
`subprocess` aus der Standardbibliothek.

  1. `canberra-gtk-play` — kennt das **Klang-Thema** des Desktops und trifft
     damit den Ton, den der Nutzer aus anderen Programmen gewohnt ist
  2. `paplay` (PulseAudio) und 3. `pw-play` (PipeWire) — spielen die
     freedesktop-Klangdatei direkt ab

`aplay` steht bewusst **nicht** in der Liste: Es kann kein Ogg, würde also
stumm scheitern und die Kaskade abbrechen, bevor der Rückfall greift.

Gefunden wird das Programm **einmal beim Start**, nicht bei jedem Ton — sonst
sucht das Programm bei jedem Bauplan erneut das Dateisystem ab.
"""
import os
import shutil
import subprocess
import sys

WINDOWS = sys.platform.startswith('win')

# Klangdatei und Themen-Kennung je Anlass.
KLAENGE = {
    'normal':     ('message', 'message.oga'),
    'auffaellig': ('complete', 'complete.oga'),
}

KLANG_ORDNER = '/usr/share/sounds/freedesktop/stereo'


def _finde_spieler():
    """Welches Abspielprogramm ist da? Einmal ermitteln, dann merken."""
    if shutil.which('canberra-gtk-play'):
        return 'canberra'
    for name in ('paplay', 'pw-play'):
        if shutil.which(name):
            return name
    return None


SPIELER = None if WINDOWS else _finde_spieler()


def datei(anlass):
    """Voller Pfad zur Klangdatei — oder None, wenn es sie hier nicht gibt."""
    _, name = KLAENGE.get(anlass, KLAENGE['normal'])
    pfad = os.path.join(KLANG_ORDNER, name)
    return pfad if os.path.isfile(pfad) else None


def abspielen(anlass='normal'):
    """Einen Systemklang abspielen. Gibt True zurück, wenn es losgeschickt wurde.

    Läuft **nebenher** (`Popen`, kein Warten): Ein Ton darf die Anzeige des
    Bauplans nicht aufhalten — die Meldung ist wichtiger als das Geräusch."""
    if not SPIELER:
        return False
    kennung, _ = KLAENGE.get(anlass, KLAENGE['normal'])
    if SPIELER == 'canberra':
        befehl = ['canberra-gtk-play', '-i', kennung]
    else:
        pfad = datei(anlass)
        if not pfad:
            return False
        befehl = [SPIELER, pfad]
    try:
        subprocess.Popen(befehl, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
