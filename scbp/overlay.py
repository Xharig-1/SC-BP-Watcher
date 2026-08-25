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
Wie sich das Overlay im Spiel verhält.

Anlass war eine Rückmeldung aus der Orga: „Das Overlay ist permanent zu sehen und
nicht durchklickbar. Wenn ich im Kampf mit der Maus hineinkomme, wird das
unangenehm." — Recht hat er. Ein Werkzeug, das beim Spielen im Weg steht, benutzt
niemand, egal wie gut es sonst ist.

Zwei getrennte Antworten darauf, beide abschaltbar:

**1. Nur zeigen, wenn es etwas zu sagen gibt.** Statt dauernd dazustehen bleibt das
Overlay unsichtbar und taucht bei einem neuen Bauplan für ein paar Sekunden auf.
Was dann noch fehlt, ist ein Weg zurück — den liefert der Einzelinstanz-Wächter
(siehe `zeigen_bitte`): Das Programm ein zweites Mal starten holt das vorhandene
Fenster hervor, statt eine zweite Fassung zu öffnen. Damit reicht eine ganz normale
Tastenkombination des Systems auf die Verknüpfung.

**2. Mausklicks durchreichen.** Das Fenster ist dann zwar sichtbar, fängt aber keine
Klicks mehr ab — der Schuss geht ins Spiel, nicht ins Overlay.

  * **Windows:** sauber über `WS_EX_TRANSPARENT`. Genau so machen es die
    Spiel-Overlays, die man kennt.
  * **Linux/X11:** über die XShape-Erweiterung, indem die Eingabe-Region des
    Fensters auf leer gesetzt wird. Tk bietet das nicht an, `libXext` schon.
    Läuft auch unter XWayland, weil das eine X11-Umsetzung ist.
  * **Wayland (nativ):** geht nicht. Ein gewöhnliches Fenster kann dort keine
    Eingaben weiterreichen. Wir sagen das ehrlich, statt es still zu ignorieren.

⚠ Wer durchklickbar einschaltet, kann das Overlay auch nicht mehr **verschieben**
oder seine Knöpfe treffen — es reicht ja alles durch. Deshalb hängt an der
Einstellung ein deutlicher Hinweis, und der Weg ins Fenster führt über den
zweiten Programmstart.
"""
import ctypes
import socket
import sys
import threading

WINDOWS = sys.platform.startswith('win')

# Fester Port auf dem eigenen Rechner für den Einzelinstanz-Wächter. Nichts
# davon geht ins Netz: gebunden wird ausschließlich an 127.0.0.1.
WAECHTER_PORT = 47913
_waechter = [None]

# Das Overlay-Fenster selbst. Das Hauptprogramm trägt sich beim Start ein, damit
# die Einstellungsseite eine Änderung sofort anwenden kann, ohne das
# Hauptprogramm importieren zu müssen (das gäbe einen Ringschluss).
OVERLAY_FENSTER = [None]

# Das Overlay-Objekt selbst (nicht nur sein Tk-Fenster). Darüber kann die
# Einstellungsseite eine Änderung sofort anwenden lassen.
OVERLAY_STEUERUNG = [None]


# --------------------------------------------------------- Mausklicks durchreichen

def _windows_durchklickbar(fenster, an):
    try:
        fenster.update_idletasks()
        kennung = ctypes.windll.user32.GetParent(fenster.winfo_id()) or fenster.winfo_id()
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        hole = getattr(ctypes.windll.user32, 'GetWindowLongPtrW',
                       ctypes.windll.user32.GetWindowLongW)
        setze = getattr(ctypes.windll.user32, 'SetWindowLongPtrW',
                        ctypes.windll.user32.SetWindowLongW)
        stil = hole(kennung, GWL_EXSTYLE)
        if an:
            stil |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            stil &= ~WS_EX_TRANSPARENT
        setze(kennung, GWL_EXSTYLE, stil)
        return True
    except Exception:
        return False


def _x11_durchklickbar(fenster, an):
    """Die Eingabe-Region auf leer setzen — dann fällt jeder Klick hindurch.

    ⚠ Die Typen müssen von Hand gesetzt werden. Ohne `restype` nimmt ctypes für
    jeden Rückgabewert ein 32-Bit-`int` an — auf einem 64-Bit-System wird der
    Zeiger auf den Display damit abgeschnitten, und der nächste Aufruf greift ins
    Nichts. Der erste Anlauf hat das Programm genau so mit einem Speicherauszug
    beendet, nicht mit einer Fehlermeldung.
    """
    from ctypes import c_int, c_ulong, c_void_p
    try:
        fenster.update_idletasks()
        x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
        xext = ctypes.cdll.LoadLibrary('libXext.so.6')

        x11.XOpenDisplay.restype = c_void_p
        x11.XOpenDisplay.argtypes = [c_void_p]
        x11.XCloseDisplay.restype = c_int
        x11.XCloseDisplay.argtypes = [c_void_p]
        x11.XFlush.restype = c_int
        x11.XFlush.argtypes = [c_void_p]
        x11.XCreateRegion.restype = c_void_p
        x11.XCreateRegion.argtypes = []
        x11.XDestroyRegion.restype = c_int
        x11.XDestroyRegion.argtypes = [c_void_p]
        xext.XShapeCombineRegion.restype = None
        xext.XShapeCombineRegion.argtypes = [c_void_p, c_ulong, c_int, c_int,
                                             c_int, c_void_p, c_int]
        xext.XShapeCombineMask.restype = None
        xext.XShapeCombineMask.argtypes = [c_void_p, c_ulong, c_int, c_int,
                                           c_int, c_ulong, c_int]
        xext.XShapeQueryExtension.restype = c_int
        xext.XShapeQueryExtension.argtypes = [c_void_p, ctypes.POINTER(c_int),
                                              ctypes.POINTER(c_int)]

        anzeige = x11.XOpenDisplay(None)
        if not anzeige:
            return False
        try:
            # Gibt es die Erweiterung auf diesem Server überhaupt? Ohne diese
            # Frage würde ein Aufruf ins Leere laufen.
            ereignis, fehlerbasis = c_int(), c_int()
            if not xext.XShapeQueryExtension(anzeige, ctypes.byref(ereignis),
                                             ctypes.byref(fehlerbasis)):
                return False
            kennung = c_ulong(fenster.winfo_id())
            ShapeInput, ShapeSet = 2, 0
            if an:
                # Eine Region ohne Fläche: Nichts davon nimmt noch Klicks an.
                region = x11.XCreateRegion()
                if not region:
                    return False
                xext.XShapeCombineRegion(anzeige, kennung, ShapeInput, 0, 0,
                                         region, ShapeSet)
                x11.XDestroyRegion(region)
            else:
                # Ohne Maske (None = 0) gilt wieder das ganze Fenster.
                xext.XShapeCombineMask(anzeige, kennung, ShapeInput, 0, 0, 0,
                                       ShapeSet)
            x11.XFlush(anzeige)
            return True
        finally:
            x11.XCloseDisplay(anzeige)
    except Exception:
        return False


def durchklickbar_moeglich():
    """Lässt sich auf diesem System überhaupt durchklicken?"""
    if WINDOWS:
        return True
    # Unter nativem Wayland gibt es keinen X-Server, an den wir uns wenden könnten.
    import os
    if os.environ.get('WAYLAND_DISPLAY') and not os.environ.get('DISPLAY'):
        return False
    return True


def durchklickbar_setzen(fenster, an):
    """Klicks durchreichen (oder wieder abfangen). Gibt zurück, ob es geklappt hat."""
    if WINDOWS:
        return _windows_durchklickbar(fenster, an)
    return _x11_durchklickbar(fenster, an)


# ------------------------------------------------ Zweiter Start holt das Fenster

def waechter_starten(beim_ruf):
    """Lauschen, ob jemand das Fenster hervorholen möchte.

    Warum überhaupt: Im Pop-up-Betrieb ist das Overlay die meiste Zeit unsichtbar.
    Ohne Rückweg wäre das Werkzeug dann unerreichbar — man käme an keine Liste und
    an keine Einstellung mehr. Statt einen eigenen Tastatur-Haken ins System zu
    setzen (unter Windows fragil, unter Wayland unmöglich), nutzen wir den
    einfachsten Weg, den jedes System schon kennt: **das Programm noch einmal
    starten**. Die zweite Fassung merkt, dass schon eine läuft, sagt ihr Bescheid
    und beendet sich. Auf die Verknüpfung lässt sich dann eine ganz normale
    Tastenkombination legen.

    `beim_ruf` wird im Lausch-Thread aufgerufen — dort nichts zeichnen, sondern
    die Arbeit an den Tk-Thread übergeben (`after`).
    """
    try:
        horcher = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        horcher.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        horcher.bind(('127.0.0.1', WAECHTER_PORT))
        horcher.listen(4)
    except OSError:
        return False                     # läuft schon — wir sind die zweite Fassung
    _waechter[0] = horcher

    def lauschen():
        while True:
            try:
                verbindung, _ = horcher.accept()
            except OSError:
                return
            try:
                verbindung.settimeout(2)
                verbindung.recv(64)
                beim_ruf()
            except Exception:
                pass
            finally:
                try:
                    verbindung.close()
                except OSError:
                    pass

    faden = threading.Thread(target=lauschen, daemon=True)
    faden.start()
    return True


def zeigen_bitte():
    """Einer laufenden Fassung sagen, sie soll sich zeigen. True = ausgerichtet."""
    try:
        with socket.create_connection(('127.0.0.1', WAECHTER_PORT), timeout=2) as s:
            s.sendall(b'zeigen')
        return True
    except OSError:
        return False
