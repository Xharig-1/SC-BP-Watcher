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
ENTWURF des Einstellungsfensters — zum Ansehen, noch nicht Teil des Programms.

Gehört zu Phase 4 des Neubauplans. Diese Datei liegt bewusst unter `tools/`:
Sie zeigt, wie das Fenster aussehen soll, ohne schon im Watcher zu hängen.
Wird der Entwurf angenommen, wandert er als `scbp/einstellungsfenster.py`
hinüber und bekommt echte Funktionen hinter den Feldern.

Aufruf:
    python3 tools/entwurf_einstellungen.py
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scbp import pfade                                       # noqa: E402

# Farben — dieselben wie im Overlay (`sc_bp_watcher.py`). Beim Ändern beide
# Stellen anfassen, sonst laufen zwei Grüntöne nebeneinander.
BG      = '#10141c'
FLAECHE = '#161c28'
BAR     = '#1b2230'
FG      = '#e6edf3'
SUB     = '#8b98a5'
ACCENT  = '#9ce430'
GELB    = '#d8a03a'


def schrift(groesse, fett=False):
    fam = 'Segoe UI' if pfade.WINDOWS else 'Helvetica'
    return (fam, groesse, 'bold' if fett else 'normal')


def mono(groesse):
    return ('Consolas' if pfade.WINDOWS else 'Menlo', groesse)


class Entwurf:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('SC BP Watcher — Einstellungen')
        self.root.configure(bg=BG)
        self.root.geometry('660x720+60+60')

        self._titelleiste()
        self._inhalt()
        self._fussleiste()

    # ------------------------------------------------------------ Titelleiste
    def _titelleiste(self):
        bar = tk.Frame(self.root, bg=BAR)
        bar.pack(fill='x')
        tk.Label(bar, text='⚙  Einstellungen', bg=BAR, fg=FG,
                 font=schrift(12, True)).pack(side='left', padx=14, pady=10)
        tk.Label(bar, text='✕', bg=BAR, fg=SUB, font=schrift(12),
                 cursor='hand2').pack(side='right', padx=14)

    # ---------------------------------------------------------------- Bausteine
    def _abschnitt(self, eltern, titel):
        tk.Label(eltern, text=titel.upper(), bg=BG, fg=ACCENT,
                 font=schrift(9, True), anchor='w').pack(
                     fill='x', padx=18, pady=(18, 6))
        kasten = tk.Frame(eltern, bg=FLAECHE)
        kasten.pack(fill='x', padx=18)
        return kasten

    def _pfadfeld(self, eltern, beschriftung, wert, gefunden, orte):
        """Ein Pfad-Eingabefeld mit ausgegrauter Herkunftsangabe darunter."""
        f = tk.Frame(eltern, bg=FLAECHE)
        f.pack(fill='x', padx=14, pady=(12, 10))

        kopf = tk.Frame(f, bg=FLAECHE)
        kopf.pack(fill='x')
        tk.Label(kopf, text=beschriftung, bg=FLAECHE, fg=FG,
                 font=schrift(10), anchor='w').pack(side='left')
        tk.Label(kopf, text=('● gefunden' if gefunden else '● nicht gefunden'),
                 bg=FLAECHE, fg=(ACCENT if gefunden else GELB),
                 font=schrift(9), anchor='e').pack(side='right')

        zeile = tk.Frame(f, bg=FLAECHE)
        zeile.pack(fill='x', pady=(6, 0))
        eingabe = tk.Entry(zeile, bg=BG, fg=FG, insertbackground=FG,
                           relief='flat', font=mono(9))
        eingabe.insert(0, wert)
        eingabe.pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 8))
        tk.Label(zeile, text=' Durchsuchen… ', bg=BAR, fg=FG, font=schrift(9),
                 cursor='hand2', padx=6, pady=5).pack(side='right')

        # Genau das, worum es hier geht: Wo normalerweise gesucht wird.
        tk.Label(f, text='leer lassen = automatisch suchen. Gesucht wird hier:',
                 bg=FLAECHE, fg=SUB, font=schrift(8), anchor='w').pack(
                     fill='x', pady=(8, 2))
        for ort in orte[:3]:
            tk.Label(f, text=ort, bg=FLAECHE, fg=SUB, font=mono(8),
                     anchor='w').pack(fill='x')

    def _schalter(self, eltern, text, erklaerung, an=True):
        f = tk.Frame(eltern, bg=FLAECHE)
        f.pack(fill='x', padx=14, pady=9)
        tk.Label(f, text=('◉' if an else '○'), bg=FLAECHE,
                 fg=(ACCENT if an else SUB), font=schrift(12),
                 cursor='hand2').pack(side='left', padx=(0, 10))
        rechts = tk.Frame(f, bg=FLAECHE)
        rechts.pack(side='left', fill='x', expand=True)
        tk.Label(rechts, text=text, bg=FLAECHE, fg=FG, font=schrift(10),
                 anchor='w').pack(fill='x')
        tk.Label(rechts, text=erklaerung, bg=FLAECHE, fg=SUB, font=schrift(8),
                 anchor='w').pack(fill='x')

    def _zahl(self, eltern, text, wert, einheit, erklaerung):
        f = tk.Frame(eltern, bg=FLAECHE)
        f.pack(fill='x', padx=14, pady=9)
        links = tk.Frame(f, bg=FLAECHE)
        links.pack(side='left', fill='x', expand=True)
        tk.Label(links, text=text, bg=FLAECHE, fg=FG, font=schrift(10),
                 anchor='w').pack(fill='x')
        tk.Label(links, text=erklaerung, bg=FLAECHE, fg=SUB, font=schrift(8),
                 anchor='w').pack(fill='x')
        rechts = tk.Frame(f, bg=FLAECHE)
        rechts.pack(side='right')
        tk.Label(rechts, text='−', bg=BAR, fg=FG, font=schrift(11), width=2,
                 cursor='hand2').pack(side='left')
        tk.Label(rechts, text=' %s %s ' % (wert, einheit), bg=BG, fg=FG,
                 font=mono(10), padx=8, pady=4).pack(side='left', padx=2)
        tk.Label(rechts, text='+', bg=BAR, fg=FG, font=schrift(11), width=2,
                 cursor='hand2').pack(side='left')

    # ---------------------------------------------------------------- Inhalt
    def _inhalt(self):
        # Statuszeile: was hat der Watcher gefunden?
        k = self._abschnitt(self.root, 'Status')
        for beschriftung, wert, farbe in (
                ('Star Citizen', 'LIVE — Game.log wird mitgelesen', ACCENT),
                ('Frühere Sitzungen', '127 Sicherungen, alle nachgelesen', ACCENT),
                ('SC Deutsch Launcher', 'nicht vorhanden — nicht nötig', SUB),
                ('Eigener Bestand', '394 Baupläne', ACCENT),
                ('Craftdaten (scmdb)', '4.9.0 — 719 Gegenstände', ACCENT)):
            z = tk.Frame(k, bg=FLAECHE)
            z.pack(fill='x', padx=14, pady=4)
            tk.Label(z, text=beschriftung, bg=FLAECHE, fg=SUB, font=schrift(9),
                     width=20, anchor='w').pack(side='left')
            tk.Label(z, text=wert, bg=FLAECHE, fg=farbe, font=schrift(9),
                     anchor='w').pack(side='left')
        tk.Frame(k, bg=FLAECHE, height=6).pack()

        # Pfade — der Grund für dieses Fenster
        k = self._abschnitt(self.root, 'Pfade')
        self._pfadfeld(k, 'Spielordner (mit der Game.log darin)', '', True,
                       pfade.gesuchte_spielorte())
        tk.Frame(k, bg=BG, height=1).pack(fill='x', padx=14)
        self._pfadfeld(k, 'SC Deutsch Launcher (optional)', '', False,
                       pfade.gesuchte_launcherorte())

        # Verhalten
        k = self._abschnitt(self.root, 'Verhalten')
        self._zahl(k, 'Prüfintervall', 3, 'Sek.',
                   'Wie oft Game.log und Launcher-Datei angesehen werden')
        self._schalter(k, 'Signalton bei neuem Bauplan',
                       'Kurzer Ton, wenn etwas in der Liste erscheint', True)
        self._schalter(k, 'Mit dem Rechner starten',
                       'Trägt den Watcher in den Autostart ein', False)
        self._schalter(k, 'Craftdaten aus dem Netz holen',
                       'Nur bei neuer Spielversion. Aus = letzter Stand gilt', True)

    # ------------------------------------------------------------ Fussleiste
    def _fussleiste(self):
        bar = tk.Frame(self.root, bg=BAR)
        bar.pack(fill='x', side='bottom')
        tk.Label(bar, text='Fensterlage zurücksetzen', bg=BAR, fg=SUB,
                 font=schrift(9), cursor='hand2').pack(side='left', padx=16,
                                                       pady=12)
        tk.Label(bar, text='  Speichern  ', bg=ACCENT, fg='#10141c',
                 font=schrift(10, True), cursor='hand2', padx=10,
                 pady=5).pack(side='right', padx=16)
        tk.Label(bar, text='Abbrechen', bg=BAR, fg=SUB, font=schrift(10),
                 cursor='hand2').pack(side='right')

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    Entwurf().run()
