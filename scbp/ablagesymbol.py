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
Das Symbol im Infobereich der Windows-Taskleiste („Ablage", System Tray).

**Wozu.** Das Overlay kann sich seit v3.0.0 zurückhalten und nur bei einem
neuen Bauplan aufblenden. Dann ist es aber die meiste Zeit unsichtbar, und wer
an die Liste oder die Einstellungen will, braucht einen Weg dorthin. Unter Linux
ist das der Startmenü-Eintrag; unter Windows gehört das Symbol neben die Uhr —
dort sucht man Hintergrundprogramme.

**Warum von Hand und nicht mit einer Bibliothek.** Das Programm kommt ohne
Zusatzpakete aus; das ist Absicht und steht so in der Roadmap. Windows bietet
`Shell_NotifyIcon` an, und der Weg dorthin führt über `ctypes`.

**Wie es zusammenhängt.** Ein Symbol im Infobereich braucht ein Fenster, an das
Windows seine Nachrichten schicken kann — Klicks landen dort als selbst
vergebene Nachrichtennummer. Dieses Fenster ist unsichtbar und tut sonst nichts.
Weil es eine eigene Nachrichtenschleife braucht, läuft es in einem eigenen
Faden; alles, was daraufhin passieren soll, wird per Rückruf an den Tk-Faden
übergeben — Tk verträgt keine Aufrufe aus fremden Fäden.

⚠ Alles hier ist gutmütig gebaut: Klappt irgendein Schritt nicht, gibt es eben
kein Symbol, und das Programm läuft weiter. Ein Werkzeug darf nicht daran
scheitern, dass ein Symbol neben der Uhr fehlt.
"""
import ctypes
import os
import sys
import threading

WINDOWS = sys.platform.startswith('win')

# Eigene Nachrichtennummer für alles, was das Symbol meldet. WM_APP ist der
# Bereich, den Windows für Programme frei lässt.
WM_APP = 0x8000
NACHRICHT = WM_APP + 17

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x01, 0x02, 0x04

IMAGE_ICON = 1
LR_LOADFROMFILE, LR_DEFAULTSIZE = 0x0010, 0x0040
IDI_APPLICATION = 32512

TPM_RIGHTBUTTON = 0x0002
MF_STRING = 0x0000

BEFEHL_ZEIGEN = 1001
BEFEHL_BEENDEN = 1002


def moeglich():
    return WINDOWS


class Ablagesymbol(object):
    """Das Symbol neben der Uhr. `starten()` und `stoppen()` — mehr braucht es nicht."""

    def __init__(self, beim_zeigen=None, beim_beenden=None, titel='SC BP Watcher'):
        self.beim_zeigen = beim_zeigen
        self.beim_beenden = beim_beenden
        self.titel = titel
        self.fenster = None
        self._faden = None
        self._laeuft = False
        # ⚠ Muss als Attribut gehalten werden. Ein Rückruf, den nur Windows
        # kennt, wird von Python sonst irgendwann aufgeräumt — und der nächste
        # Klick auf das Symbol beendet das Programm mit einem Speicherauszug.
        self._fensterfunktion = None
        self._klasse = None

    # ------------------------------------------------------------- Aufbau
    def _symbol_laden(self):
        """Das Programmsymbol — sonst das Standardsymbol von Windows."""
        benutzer = ctypes.windll.user32
        for ordner in (getattr(sys, '_MEIPASS', ''),
                       os.path.dirname(os.path.abspath(sys.executable)),
                       os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
            if not ordner:
                continue
            pfad = os.path.join(ordner, 'icon.ico')
            if os.path.isfile(pfad):
                kennung = benutzer.LoadImageW(None, pfad, IMAGE_ICON, 0, 0,
                                              LR_LOADFROMFILE | LR_DEFAULTSIZE)
                if kennung:
                    return kennung
        return benutzer.LoadIconW(None, ctypes.c_wchar_p(IDI_APPLICATION))

    def _daten(self, flags):
        """Die NOTIFYICONDATAW-Struktur, die Windows erwartet."""
        from ctypes import wintypes

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('hWnd', wintypes.HWND),
                ('uID', wintypes.UINT),
                ('uFlags', wintypes.UINT),
                ('uCallbackMessage', wintypes.UINT),
                ('hIcon', wintypes.HICON),
                ('szTip', wintypes.WCHAR * 128),
                ('dwState', wintypes.DWORD),
                ('dwStateMask', wintypes.DWORD),
                ('szInfo', wintypes.WCHAR * 256),
                ('uVersion', wintypes.UINT),
                ('szInfoTitle', wintypes.WCHAR * 64),
                ('dwInfoFlags', wintypes.DWORD),
            ]

        daten = NOTIFYICONDATAW()
        daten.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        daten.hWnd = self.fenster
        daten.uID = 1
        daten.uFlags = flags
        daten.uCallbackMessage = NACHRICHT
        daten.hIcon = self._symbol
        daten.szTip = self.titel[:127]
        return daten

    def _menue_zeigen(self):
        """Das Rechtsklick-Menü — zwei Punkte, mehr braucht niemand."""
        benutzer = ctypes.windll.user32
        menue = benutzer.CreatePopupMenu()
        if not menue:
            return
        try:
            benutzer.AppendMenuW(menue, MF_STRING, BEFEHL_ZEIGEN, self._text_zeigen)
            benutzer.AppendMenuW(menue, MF_STRING, BEFEHL_BEENDEN, self._text_beenden)
            from ctypes import wintypes

            class POINT(ctypes.Structure):
                _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

            punkt = POINT()
            benutzer.GetCursorPos(ctypes.byref(punkt))
            # ⚠ Ohne SetForegroundWindow bleibt das Menü stehen, bis man ein
            # zweites Mal klickt — ein bekannter Sonderfall von Windows.
            benutzer.SetForegroundWindow(self.fenster)
            benutzer.TrackPopupMenu(menue, TPM_RIGHTBUTTON, punkt.x, punkt.y,
                                    0, self.fenster, None)
            benutzer.PostMessageW(self.fenster, 0, 0, 0)
        finally:
            benutzer.DestroyMenu(menue)

    def _behandeln(self, fenster, nachricht, wparam, lparam):
        try:
            if nachricht == NACHRICHT:
                if lparam == WM_LBUTTONUP:
                    self._rufen(self.beim_zeigen)
                elif lparam == WM_RBUTTONUP:
                    self._menue_zeigen()
                return 0
            if nachricht == WM_COMMAND:
                befehl = wparam & 0xFFFF
                if befehl == BEFEHL_ZEIGEN:
                    self._rufen(self.beim_zeigen)
                elif befehl == BEFEHL_BEENDEN:
                    self._rufen(self.beim_beenden)
                return 0
            if nachricht == WM_DESTROY:
                ctypes.windll.user32.PostQuitMessage(0)
                return 0
        except Exception:
            pass
        return ctypes.windll.user32.DefWindowProcW(fenster, nachricht,
                                                   wparam, lparam)

    @staticmethod
    def _rufen(was):
        if was:
            try:
                was()
            except Exception:
                pass

    # ------------------------------------------------------------ Betrieb
    def starten(self, text_zeigen='Fenster zeigen', text_beenden='Beenden'):
        """Symbol anlegen. Gibt zurück, ob es geklappt hat."""
        if not WINDOWS or self._laeuft:
            return False
        self._text_zeigen = text_zeigen
        self._text_beenden = text_beenden
        bereit = threading.Event()
        self._geklappt = False
        self._faden = threading.Thread(target=self._schleife, args=(bereit,),
                                       daemon=True)
        self._faden.start()
        bereit.wait(5)
        return self._geklappt

    def _schleife(self, bereit):
        from ctypes import wintypes
        try:
            benutzer = ctypes.windll.user32
            kern = ctypes.windll.kernel32

            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND,
                                         wintypes.UINT, wintypes.WPARAM,
                                         wintypes.LPARAM)
            self._fensterfunktion = WNDPROC(self._behandeln)

            class WNDCLASS(ctypes.Structure):
                _fields_ = [('style', wintypes.UINT),
                            ('lpfnWndProc', WNDPROC),
                            ('cbClsExtra', ctypes.c_int),
                            ('cbWndExtra', ctypes.c_int),
                            ('hInstance', wintypes.HINSTANCE),
                            ('hIcon', wintypes.HICON),
                            ('hCursor', wintypes.HANDLE),
                            ('hbrBackground', wintypes.HBRUSH),
                            ('lpszMenuName', wintypes.LPCWSTR),
                            ('lpszClassName', wintypes.LPCWSTR)]

            klasse = WNDCLASS()
            klasse.lpfnWndProc = self._fensterfunktion
            klasse.lpszClassName = 'SCBPWatcherAblage'
            klasse.hInstance = kern.GetModuleHandleW(None)
            self._klasse = klasse
            benutzer.RegisterClassW(ctypes.byref(klasse))

            self.fenster = benutzer.CreateWindowExW(
                0, klasse.lpszClassName, klasse.lpszClassName, 0,
                0, 0, 0, 0, None, None, klasse.hInstance, None)
            if not self.fenster:
                bereit.set()
                return

            self._symbol = self._symbol_laden()
            daten = self._daten(NIF_MESSAGE | NIF_ICON | NIF_TIP)
            self._geklappt = bool(
                ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD,
                                                        ctypes.byref(daten)))
            self._laeuft = self._geklappt
            bereit.set()

            nachricht = wintypes.MSG()
            while benutzer.GetMessageW(ctypes.byref(nachricht), None, 0, 0) > 0:
                benutzer.TranslateMessage(ctypes.byref(nachricht))
                benutzer.DispatchMessageW(ctypes.byref(nachricht))
        except Exception:
            bereit.set()
        finally:
            self._laeuft = False

    def stoppen(self):
        """Symbol wieder wegnehmen — sonst bleibt eine tote Hülle neben der Uhr."""
        if not WINDOWS or not self.fenster:
            return
        try:
            daten = self._daten(NIF_MESSAGE)
            ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE,
                                                    ctypes.byref(daten))
            ctypes.windll.user32.DestroyWindow(self.fenster)
        except Exception:
            pass
        finally:
            self.fenster = None
            self._laeuft = False
