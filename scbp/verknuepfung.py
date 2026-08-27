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
Ein Eintrag im Startmenü — damit das Werkzeug auffindbar ist.

**Warum das nötig ist.** Unter Windows legt der Installer alles an. Unter Linux
gibt es keinen Installer: Dort lädt man ein AppImage herunter, und das liegt dann
im Download-Ordner. Es steht in keinem Menü, es hat kein Symbol, und wer es
starten will, muss wissen, wo es liegt. Nach einem Neustart sucht man es.

Angelegt wird eine `.desktop`-Datei nach dem Freedesktop-Standard in
`~/.local/share/applications/`. Das ist der Ort für Einträge eines einzelnen
Nutzers — kein Systemordner, keine Administratorrechte, und beim Entfernen bleibt
nichts zurück außer dieser einen Datei.

Zwei Dinge macht die Datei nebenbei mit möglich:

  * **Ein Tastenkürzel.** Die Arbeitsumgebung (KDE, GNOME …) lässt auf jeden
    Menüeintrag eine Tastenkombination legen. Zusammen mit dem
    Einzelinstanz-Wächter aus `overlay.py` ist das der Weg, das Overlay im
    Pop-up-Betrieb zurückzuholen.
  * **Anheften.** Was im Menü steht, lässt sich in die Leiste ziehen.

Das Symbol wird als eigene Datei danebengelegt: Ein AppImage bringt sein Symbol
zwar mit, aber erst nach dem Entpacken — die Menüverwaltung kommt nicht hinein.
"""
import os
import shutil
import subprocess
import sys

WINDOWS = sys.platform.startswith('win')

DATEINAME = 'sc-bp-watcher.desktop'
SYMBOLNAME = 'sc-bp-watcher.png'


def moeglich():
    """Lohnt sich der Eintrag auf diesem System?"""
    return not WINDOWS and sys.platform != 'darwin'


def _programmpfad():
    """Womit das Programm gestartet wird — AppImage oder das laufende Python.

    ⚠ Bei einem AppImage steht der Pfad **nur** in `APPIMAGE`; `sys.executable`
    zeigt in den entpackten Zwischenordner unter `/tmp`, der beim nächsten Start
    einen anderen Namen hat. Ein Menüeintrag darauf wäre nach einem Neustart tot.
    """
    appimage = os.environ.get('APPIMAGE')
    if appimage and os.path.isfile(appimage):
        return os.path.abspath(appimage), None
    if getattr(sys, 'frozen', False):
        return os.path.abspath(sys.executable), None
    # Aus dem Quellcode: das Startskript nehmen, damit der Eintrag auch nach
    # einem `git pull` noch stimmt.
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skript = os.path.join(wurzel, 'sc_bp_watcher.py')
    return os.path.abspath(sys.executable), skript


def _menue_ordner():
    basis = (os.environ.get('XDG_DATA_HOME')
             or os.path.join(os.path.expanduser('~'), '.local', 'share'))
    return os.path.join(basis, 'applications')


def ziel_datei():
    return os.path.join(_menue_ordner(), DATEINAME)


def vorhanden():
    """Gibt es den Eintrag schon — und zeigt er noch auf ein Programm, das da ist?"""
    pfad = ziel_datei()
    if not os.path.isfile(pfad):
        return False
    try:
        with open(pfad, encoding='utf-8') as f:
            for zeile in f:
                if zeile.startswith('Exec='):
                    befehl = zeile.split('=', 1)[1].strip().strip('"').split('"')[0]
                    return os.path.exists(befehl.split(' ')[0].strip('"'))
    except OSError:
        return False
    return True


def _symbol_ablegen(ordner):
    """Das Programmsymbol neben den Eintrag legen. Gibt den Pfad zurück."""
    quelle = None
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for kandidat in (os.path.join(getattr(sys, '_MEIPASS', ''), 'icon.png'),
                     os.path.join(wurzel, 'assets', 'icon.png'),
                     os.path.join(wurzel, 'icon.png')):
        if kandidat and os.path.isfile(kandidat):
            quelle = kandidat
            break
    if not quelle:
        return 'sc-bp-watcher'          # kein Bild da: Name reicht als Kennung
    ziel = os.path.join(ordner, SYMBOLNAME)
    try:
        os.makedirs(ordner, exist_ok=True)
        shutil.copyfile(quelle, ziel)
        return ziel
    except OSError:
        return 'sc-bp-watcher'


def anlegen():
    """Den Menüeintrag schreiben. Gibt (geklappt, Pfad-oder-Meldung) zurück."""
    if not moeglich():
        return False, 'nur unter Linux'
    programm, skript = _programmpfad()
    if not os.path.exists(programm):
        return False, programm
    ordner = _menue_ordner()
    symbol_ordner = os.path.join(
        os.environ.get('XDG_DATA_HOME')
        or os.path.join(os.path.expanduser('~'), '.local', 'share'),
        'icons', 'hicolor', '256x256', 'apps')
    symbol = _symbol_ablegen(symbol_ordner)

    # Pfade mit Leerzeichen gehören in Anführungszeichen — das AppImage liegt bei
    # vielen unter „Programme"/„Downloads", und ohne Anführungszeichen bricht der
    # Start still ab.
    befehl = '"%s"' % programm
    if skript:
        befehl += ' "%s"' % skript

    inhalt = (
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Name=SC BP Watcher\n'
        'Comment=Zeigt neue Star-Citizen-Baupläne an\n'
        'Comment[en]=Shows new Star Citizen blueprints\n'
        'Exec=%s\n'
        'Icon=%s\n'
        'Terminal=false\n'
        'Categories=Utility;Game;\n'
        'StartupWMClass=SC BP Watcher\n'
        'Keywords=Star Citizen;Blueprint;Bauplan;\n' % (befehl, symbol))
    try:
        os.makedirs(ordner, exist_ok=True)
        pfad = ziel_datei()
        with open(pfad, 'w', encoding='utf-8') as f:
            f.write(inhalt)
        os.chmod(pfad, 0o755)
    except OSError as ausnahme:
        return False, str(ausnahme)

    # Die Menüverwaltung anstoßen. Fehlt das Werkzeug, taucht der Eintrag
    # spätestens nach dem nächsten Anmelden auf — kein Grund für eine Fehlermeldung.
    try:
        if shutil.which('update-desktop-database'):
            subprocess.run(['update-desktop-database', ordner],
                           capture_output=True, timeout=20)
    except Exception:
        pass
    return True, pfad


def entfernen():
    """Den Eintrag wieder wegnehmen."""
    try:
        pfad = ziel_datei()
        if os.path.isfile(pfad):
            os.remove(pfad)
        return True
    except OSError:
        return False
