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
Die Einstellungen — sichtbar, statt in einer Datei.

Bis v2.0.0-rc3 gab es dieses Fenster nicht. Sprache und Spielordner ließen sich
nur über den **Einrichtungsassistenten** ändern, die übrigen drei Felder gar
nicht — für die musste man `einstellungen.json` von Hand bearbeiten und das
Programm neu starten. Gemeldet als „ich finde den Einstellungs-Button gar
nicht", und das zu Recht: Niemand kommt darauf, dass „Einrichtung wiederholen"
der Weg zur Spracheinstellung ist.

Das widersprach auch der eigenen Projektregel — *fehlt eine Angabe, wird
gefragt, nie „bearbeite diese Datei und starte neu"*.

Aufbau: fünf Felder, jedes mit **einem Satz Erklärung darunter**. Die Erklärungen
standen vorher schon in der JSON-Datei, weil man dort keine ausgegraute
Beschriftung hat — hier stehen sie da, wo sie hingehören.

Der Assistent bleibt daneben bestehen. Er führt Schritt für Schritt durch die
Ersteinrichtung; dieses Fenster ist zum gezielten Nachstellen einer Sache.
"""
import os
import tkinter as tk
from tkinter import filedialog

from . import pfade
from . import sprache
from .sprache import t

BG      = '#10141c'
FLAECHE = '#161c28'
BAR     = '#1b2230'
FG      = '#e6edf3'
SUB     = '#8b98a5'
ACCENT  = '#9ce430'
ROT     = '#e05252'

INTERVALL_MIN, INTERVALL_MAX = 1, 60


def schrift(groesse, fett=False):
    return ('Segoe UI', groesse, 'bold' if fett else 'normal')


class Einstellungsfenster:
    """Ein Fenster, kein Dauerzustand — beim Schließen ist es weg."""

    def __init__(self, eltern=None):
        self.root = tk.Toplevel(eltern) if eltern else tk.Tk()
        self.root.title(t('titel_einstellungen'))
        self.root.configure(bg=BG)
        self.root.geometry('640x620')

        # Werte laden. Leere Felder heißen „selbst suchen" — das bleibt so,
        # ein leeres Feld ist hier kein Fehler.
        self.sprache_wahl = tk.StringVar(value=pfade.einstellungen().get('sprache')
                                         or 'auto')
        self.spiel = tk.StringVar(value=pfade.einstellungen().get('spiel_ordner') or '')
        self.launcher = tk.StringVar(value=pfade.einstellungen().get('launcher_ordner')
                                     or '')
        self.intervall = tk.StringVar(
            value=str(pfade.einstellung_zahl('pruefintervall_sekunden', 3,
                                             INTERVALL_MIN, INTERVALL_MAX)))
        self.ton = tk.BooleanVar(value=pfade.einstellung_wahrheit('signalton', True))

        self._kopf()
        flaeche = tk.Frame(self.root, bg=BG)
        flaeche.pack(fill='both', expand=True, padx=20, pady=(4, 0))

        self._sprachwahl(flaeche)
        self._ordnerfeld(flaeche, t('e_spiel'), t('e_spiel_hilfe'), self.spiel)
        self._ordnerfeld(flaeche, t('e_launcher'), t('e_launcher_hilfe'),
                         self.launcher)
        self._intervallfeld(flaeche)
        self._tonfeld(flaeche)

        self._fuss()

    # ------------------------------------------------------------- Bausteine
    def _kopf(self):
        bar = tk.Frame(self.root, bg=BAR)
        bar.pack(fill='x')
        tk.Label(bar, text=t('einstellungen'), bg=BAR, fg=FG,
                 font=schrift(12, True)).pack(side='left', padx=18, pady=10)
        zu = tk.Label(bar, text='✕', bg=BAR, fg=SUB, font=schrift(12),
                      cursor='hand2')
        zu.pack(side='right', padx=16)
        zu.bind('<Button-1>', lambda e: self.schliessen())

    def _titel(self, eltern, text, hilfe):
        tk.Label(eltern, text=text, bg=BG, fg=FG, font=schrift(11, True),
                 anchor='w').pack(fill='x', pady=(16, 2))
        tk.Label(eltern, text=hilfe, bg=BG, fg=SUB, font=schrift(9),
                 anchor='w', justify='left', wraplength=590).pack(fill='x',
                                                                  pady=(0, 6))

    def _sprachwahl(self, eltern):
        self._titel(eltern, t('e_sprache'), t('e_sprache_hilfe'))
        reihe = tk.Frame(eltern, bg=BG)
        reihe.pack(fill='x')
        self.sprach_knoepfe = {}
        for wert, text in (('auto', t('e_sprache_auto')),
                           ('de', 'Deutsch'), ('en', 'English')):
            k = tk.Label(reihe, text=' %s ' % text, bg=FLAECHE, fg=SUB,
                         font=schrift(10), cursor='hand2', padx=10, pady=6)
            k.pack(side='left', padx=(0, 6))
            k.bind('<Button-1>', lambda e, w=wert: self._sprache_waehlen(w))
            self.sprach_knoepfe[wert] = k
        self._sprach_knoepfe_faerben()

    def _sprache_waehlen(self, wert):
        """Sofort umschalten, nicht erst beim Speichern.

        Wer eine Sprache wählt, will sehen, ob es die richtige ist. Gespeichert
        wird trotzdem erst mit dem Knopf — sonst könnte man nichts ausprobieren,
        ohne es zu übernehmen."""
        self.sprache_wahl.set(wert)
        sprache.setzen(wert)
        self._sprach_knoepfe_faerben()
        self._neu_beschriften()

    def _sprach_knoepfe_faerben(self):
        for wert, knopf in self.sprach_knoepfe.items():
            an = wert == self.sprache_wahl.get()
            knopf.configure(fg=BG if an else SUB, bg=ACCENT if an else FLAECHE)

    def _ordnerfeld(self, eltern, titel, hilfe, variable):
        self._titel(eltern, titel, hilfe)
        reihe = tk.Frame(eltern, bg=BG)
        reihe.pack(fill='x')
        feld = tk.Entry(reihe, textvariable=variable, bg=FLAECHE, fg=FG,
                        insertbackground=FG, relief='flat', font=schrift(10))
        feld.pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 8))
        knopf = tk.Label(reihe, text=' %s ' % t('e_durchsuchen'), bg=FLAECHE,
                         fg=FG, font=schrift(10), cursor='hand2', padx=8, pady=6)
        knopf.pack(side='left')
        knopf.bind('<Button-1>', lambda e, v=variable, ti=titel: self._waehlen(v, ti))

    def _waehlen(self, variable, titel):
        ordner = filedialog.askdirectory(title=titel, parent=self.root,
                                         initialdir=variable.get() or None)
        if ordner:
            variable.set(ordner)

    def _intervallfeld(self, eltern):
        self._titel(eltern, t('e_intervall'), t('e_intervall_hilfe'))
        tk.Entry(eltern, textvariable=self.intervall, bg=FLAECHE, fg=FG,
                 insertbackground=FG, relief='flat', font=schrift(10),
                 width=8).pack(anchor='w', ipady=6)

    def _tonfeld(self, eltern):
        self._titel(eltern, t('e_ton'), t('e_ton_hilfe'))
        self.ton_lbl = tk.Label(eltern, bg=FLAECHE, font=schrift(10),
                                cursor='hand2', padx=12, pady=6)
        self.ton_lbl.pack(anchor='w')
        self.ton_lbl.bind('<Button-1>', lambda e: self._ton_umschalten())
        self._ton_beschriften()

    def _ton_umschalten(self):
        self.ton.set(not self.ton.get())
        self._ton_beschriften()

    def _ton_beschriften(self):
        an = self.ton.get()
        self.ton_lbl.configure(text=' %s ' % (t('e_an') if an else t('e_aus')),
                               fg=BG if an else SUB,
                               bg=ACCENT if an else FLAECHE)

    def _fuss(self):
        fuss = tk.Frame(self.root, bg=BG)
        fuss.pack(fill='x', side='bottom', padx=20, pady=16)
        self.meldung = tk.Label(fuss, text='', bg=BG, fg=SUB, font=schrift(9),
                                anchor='w', justify='left', wraplength=420)
        self.meldung.pack(side='left', fill='x', expand=True)
        self.speichern_lbl = tk.Label(fuss, text='  %s  ' % t('e_speichern'),
                                      bg=ACCENT, fg=BG, font=schrift(11, True),
                                      cursor='hand2', padx=10, pady=8)
        self.speichern_lbl.pack(side='right')
        self.speichern_lbl.bind('<Button-1>', lambda e: self._speichern())

    def _neu_beschriften(self):
        """Nach einem Sprachwechsel alles neu aufbauen — einfacher und
        verlässlicher, als zwanzig Beschriftungen einzeln nachzuziehen."""
        werte = (self.sprache_wahl.get(), self.spiel.get(), self.launcher.get(),
                 self.intervall.get(), self.ton.get())
        eltern = self.root.master
        self.root.destroy()
        neu = Einstellungsfenster(eltern)
        (neu.sprache_wahl.set(werte[0]), neu.spiel.set(werte[1]),
         neu.launcher.set(werte[2]), neu.intervall.set(werte[3]),
         neu.ton.set(werte[4]))
        neu._sprach_knoepfe_faerben()
        neu._ton_beschriften()

    # -------------------------------------------------------------- Speichern
    def _speichern(self):
        """Alles auf einmal — und vorher prüfen, was prüfbar ist.

        Ein Ordner, den es nicht gibt, wird **nicht** gespeichert: Sonst sucht
        der Watcher beim nächsten Start an einem Ort, den der Spieler für
        richtig hält, und meldet nichts, ohne dass jemand den Grund sieht."""
        for variable in (self.spiel, self.launcher):
            wert = variable.get().strip()
            if wert and not os.path.isdir(os.path.expanduser(wert)):
                self.meldung.configure(text=t('e_pfad_fehlt'), fg=ROT)
                return

        try:
            takt = int(self.intervall.get())
        except ValueError:
            takt = 3
        takt = max(INTERVALL_MIN, min(INTERVALL_MAX, takt))
        self.intervall.set(str(takt))

        pfade.einstellung_setzen('sprache', self.sprache_wahl.get())
        pfade.einstellung_setzen('spiel_ordner', self.spiel.get().strip())
        pfade.einstellung_setzen('launcher_ordner', self.launcher.get().strip())
        pfade.einstellung_setzen('pruefintervall_sekunden', takt)
        pfade.einstellung_setzen('signalton', bool(self.ton.get()))

        # Ehrlich sagen, was sofort gilt und was nicht: Die Sprache schaltet
        # dieses Fenster gerade selbst um, Ordner und Takt liest der laufende
        # Watcher-Thread aber nur beim Start.
        self.meldung.configure(text=t('e_neustart_noetig'), fg=SUB)

    def schliessen(self):
        self.root.destroy()


def oeffnen(eltern=None):
    """Das Fenster zeigen — oder ein schon offenes nach vorn holen."""
    vorhanden = getattr(oeffnen, '_offen', None)
    if vorhanden is not None:
        try:
            vorhanden.root.lift()
            return vorhanden
        except tk.TclError:
            pass
    fenster = Einstellungsfenster(eltern)
    oeffnen._offen = fenster
    return fenster
