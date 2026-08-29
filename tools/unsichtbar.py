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
Fensterlos prüfen — hält Prüfläufe vom Bildschirm des Nutzers fern.

Alle Werkzeuge, die Oberfläche prüfen, bauen echte tkinter-Fenster. Auf einem
Rechner, an dem gerade jemand arbeitet oder spielt, blitzen die auf und reißen
den Tastaturfokus mit: Wer in Star Citizen fliegt, landet mitten im Kampf auf
dem Desktop. Genau das ist am 29.08.2026 passiert — rund zwanzig Prüfläufe
während einer laufenden Spielsitzung.

Der Ausweg ist ein unsichtbarer Bildschirm (Xvfb). Sich daran zu erinnern hat
nicht funktioniert, deshalb erledigt es das Werkzeug jetzt selbst: Hängt ein
echter Bildschirm dran, startet es sich auf einem unsichtbaren neu.

Einbau — ganz oben in der `main()` des Werkzeugs, vor dem ersten Fenster:

    import unsichtbar
    unsichtbar.sicherstellen()

Wer die Fenster ausnahmsweise sehen will, setzt `SC_BP_SICHTBAR=1`.
"""
import os
import shutil
import subprocess
import sys

# Merker im Kindprozess — ohne ihn würde er sich endlos weiter neu starten.
SCHON_UNSICHTBAR = 'SC_BP_UNSICHTBAR'

# Notausgang: Fenster bewusst sichtbar bauen (Fehlersuche von Hand).
SICHTBAR_GEWOLLT = 'SC_BP_SICHTBAR'


def noetig():
    """Muss dieser Lauf umgeleitet werden?

    Nein, wenn wir schon im unsichtbaren Kindprozess stecken, wenn jemand
    ausdrücklich zusehen will, wenn ohnehin kein Bildschirm dranhängt (Server,
    CI) oder wenn Xvfb gar nicht installiert ist.
    """
    if os.environ.get(SCHON_UNSICHTBAR):
        return False
    if os.environ.get(SICHTBAR_GEWOLLT):
        return False
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        return False
    return bool(shutil.which('xvfb-run'))


def sicherstellen(breite=1400, hoehe=1000):
    """Startet den eigenen Lauf auf einem unsichtbaren Bildschirm neu.

    Kehrt nur zurück, wenn nichts zu tun ist — sonst endet der Prozess hier
    mit dem Rückgabewert des Kindprozesses.
    """
    if not noetig():
        return

    umgebung = dict(os.environ, **{SCHON_UNSICHTBAR: '1'})
    # -a sucht sich selbst eine freie Nummer, damit sich parallele Läufe
    # nicht gegenseitig den Bildschirm wegnehmen.
    befehl = [
        'xvfb-run', '-a',
        '-s', '-screen 0 %dx%dx24' % (breite, hoehe),
        sys.executable, os.path.abspath(sys.argv[0]),
    ] + sys.argv[1:]

    sys.exit(subprocess.call(befehl, env=umgebung))
