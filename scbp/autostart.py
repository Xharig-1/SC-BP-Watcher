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
Mit dem Rechner starten — auf beiden Systemen.

Bewusst **freiwillig**: Der Watcher schaltet sich nicht selbst ein, es gibt
einen Schalter in der Titelleiste. Der Zustand steht ausschließlich dort, wo
das System ihn ohnehin führt — es gibt keine zweite Wahrheit, die auseinander-
laufen könnte.

  Windows:  ein Wert unter HKCU\\…\\CurrentVersion\\Run
  Linux:    eine `.desktop`-Datei in ~/.config/autostart/ (der Standard, den
            KDE, GNOME und XFCE gleichermaßen lesen)
"""
import os
import sys

from . import pfade

NAME = 'SC BP Watcher'

try:
    import winreg
except ImportError:
    winreg = None

REG_SCHLUESSEL = r'Software\Microsoft\Windows\CurrentVersion\Run'


def _startdatei():
    """Die Datei, die gestartet werden muss, um den Watcher hochzufahren."""
    haupt = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'sc_bp_watcher.py')
    return haupt if os.path.exists(haupt) else os.path.abspath(sys.argv[0])


def befehl():
    """Womit das System den Watcher starten soll.

    Als fertiges Paket (`.exe` oder AppImage) sich selbst. Aus dem Quellcode
    heraus unter Windows über `pythonw.exe` — ohne das w bliebe bei jedem
    Anmelden ein Konsolenfenster offen, das im Spiel den Fokus klaut.

    ⚠ **`APPIMAGE` muss VOR der `frozen`-Abfrage kommen.** Ein AppImage ist
    ebenfalls „frozen", und `sys.executable` zeigt darin auf den **temporären
    Einhängepunkt** (`/tmp/.mount_SC-BP-ji95vH/usr/bin/SC-BP-Watcher`). Den
    gibt es beim nächsten Start nicht mehr — er bekommt jedes Mal einen neuen
    Zufallsnamen. Stand die Reihenfolge andersherum, schrieb „Mit System
    starten" genau diesen Wegwerf-Pfad in die Autostart-Datei, und der Watcher
    startete nach einem Neustart **nie** wieder — ohne Fehlermeldung, die Datei
    sah ja richtig aus. Gefunden am 29.08.2026 auf der Autors Rechner, wo der
    Eintrag seit dem Umstieg auf Linux tot dalag. Die Variable `APPIMAGE` setzt
    das AppImage selbst und sie zeigt auf die **echte** Datei."""
    appimage = os.environ.get('APPIMAGE')
    if appimage:
        return appimage
    if getattr(sys, 'frozen', False):
        return '"%s"' % sys.executable if pfade.WINDOWS else sys.executable
    if pfade.WINDOWS:
        pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
        if not os.path.exists(pyw):
            pyw = sys.executable
        return '"%s" "%s"' % (pyw, _startdatei())
    return '%s %s' % (sys.executable, _startdatei())


# ------------------------------------------------------------------- Windows
def _win_an():
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SCHLUESSEL) as k:
            wert, _ = winreg.QueryValueEx(k, NAME)
        return bool(wert)
    except Exception:
        return False


def _win_setzen(an):
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SCHLUESSEL, 0,
                            winreg.KEY_SET_VALUE) as k:
            if an:
                winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, befehl())
            else:
                try:
                    winreg.DeleteValue(k, NAME)
                except FileNotFoundError:
                    pass          # war schon aus
        return True
    except Exception as ausnahme:
        # Der Spieler hat den Schalter umgelegt und erwartet, dass es wirkt.
        # Ohne Meldung sieht er beim nächsten Start nur, dass nichts passiert.
        try:
            from . import fehler
            fehler.merken('autostart.setzen', ausnahme)
        except Exception:
            pass
        return False


# --------------------------------------------------------------------- Linux
def _desktop_datei():
    basis = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(basis, 'autostart', 'sc-bp-watcher.desktop')


def _linux_an():
    return os.path.isfile(_desktop_datei())


def _linux_setzen(an):
    ziel = _desktop_datei()
    if not an:
        try:
            os.remove(ziel)
        except FileNotFoundError:
            pass
        except OSError:
            return False
        return True
    inhalt = (
        '[Desktop Entry]\n'
        'Type=Application\n'
        'Name=%s\n'
        'Comment=Zeigt neue Star-Citizen-Baupläne an\n'
        'Exec=%s\n'
        'Terminal=false\n'
        'X-GNOME-Autostart-enabled=true\n'
    ) % (NAME, befehl())
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, 'w', encoding='utf-8') as f:
            f.write(inhalt)
        os.chmod(ziel, 0o755)
        return True
    except OSError:
        return False


# ------------------------------------------------------------------ Nach außen
def ist_an():
    """Startet der Watcher mit dem System? Fehler gelten als „aus"."""
    return _win_an() if pfade.WINDOWS else _linux_an()


# Wer den Autostart anzeigt, trägt sich hier ein.
#
# ⚠ Der Autostart wird an ZWEI Stellen umgeschaltet: am Symbol im Overlay und am
# Schiebeschalter in den Einstellungen. Beide lasen ihren Zustand bisher nur
# einmal — beim Zeichnen. Schaltete man an der einen Stelle um, blieb die andere
# auf ihrem alten Stand stehen: Im Overlay leuchtete es grün, in den Einstellungen
# stand „aus". Deshalb meldet `setzen()` jede Änderung an alle Anzeigen.
ANZEIGEN = []


def anzeige_anmelden(rueckruf):
    """Einen Rückruf eintragen, der bei jeder Änderung aufgerufen wird."""
    if rueckruf not in ANZEIGEN:
        ANZEIGEN.append(rueckruf)


def _melden():
    """Alle Anzeigen auffrischen — und dabei aufräumen, was es nicht mehr gibt.

    Die Seiten des Fensters werden bei einem Sprachwechsel neu gebaut; ihre alten
    Rückrufe zeigen dann auf zerstörte Bedienelemente und werfen `TclError`. Die
    fliegen hier still heraus, statt eine Fehlermeldung zu erzeugen.
    """
    for rueckruf in list(ANZEIGEN):
        try:
            rueckruf()
        except Exception:
            try:
                ANZEIGEN.remove(rueckruf)
            except ValueError:
                pass


def setzen(an):
    """Ein- oder ausschalten. Gibt zurück, ob es geklappt hat."""
    geklappt = _win_setzen(an) if pfade.WINDOWS else _linux_setzen(an)
    if geklappt:
        _melden()
    return geklappt


def moeglich():
    """Lässt sich der Autostart auf diesem System überhaupt schalten?"""
    return winreg is not None if pfade.WINDOWS else True


if __name__ == '__main__':
    print('möglich:', moeglich(), '· an:', ist_an())
    print('Befehl :', befehl())
    if not pfade.WINDOWS:
        print('Datei  :', _desktop_datei())
