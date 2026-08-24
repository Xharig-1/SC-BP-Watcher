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
Das Verwaltungsfenster — der eigene Bauplan-Bestand zum Nachschlagen und Abhaken.

Die Melde-Leiste zeigt, was gerade hereinkommt. Dieses Fenster zeigt den Stand:
was es gibt, was man hat, was fehlt — und **woher man das Fehlende bekommt**.

Drei Dinge, für die es da ist:

  **Nachschlagen.** „Habe ich den schon?" ohne im Spiel nachzusehen.
  **Nachtragen.** Was keine Log-Sicherung mehr hergibt, hakt man hier von Hand
  ab. Das ist die Antwort auf den Lückenhinweis beim Start — lieber ehrlich
  sagen, dass etwas fehlt, und eine Möglichkeit geben, es einzutragen.
  **Finden.** Bei jedem fehlenden Bauplan steht, welche Fraktion ihn auslobt,
  in welchem Auftrag, ab welchem Rang und was er einbringt.

Bedienung: tippen filtert, Klick auf eine Zeile setzt oder entfernt das Häkchen,
Klick auf ⓘ klappt die Bezugsquellen aus.
"""
import tkinter as tk

from . import bestand as bestand_datei
from . import hinweis
from . import katalog as katalog_modul
from . import merkliste as merk
from . import pfade
from .sprache import t

BG      = '#10141c'
FLAECHE = '#161c28'
BAR     = '#1b2230'
FG      = '#e6edf3'
SUB     = '#8b98a5'
ACCENT  = '#9ce430'
GELB    = '#d8a03a'

# Ab wie vielen Zeilen nur noch der Anfang gezeigt wird. 714 Zeilen einzeln zu
# bauen dauert in tkinter spürbar lange, und niemand scrollt durch 714 Zeilen —
# wer etwas sucht, tippt. Der Rest kommt auf Knopfdruck.
ZEILEN_ZUERST = 120


def schrift(groesse, fett=False):
    fam = 'Segoe UI' if pfade.WINDOWS else 'Helvetica'
    return (fam, groesse, 'bold' if fett else 'normal')


def mono(groesse):
    return ('Consolas' if pfade.WINDOWS else 'Menlo', groesse)


def kuerzel(eintrag):
    """Klasse/Grad/Größe als „M/A/1" — leer, wo es nichts zu zeigen gibt."""
    klasse, grad, groesse = eintrag.get('c'), eintrag.get('g'), eintrag.get('s')
    if not (klasse or grad or groesse):
        return ''
    buchstabe = {'Military': 'M', 'Stealth': 'S', 'Industrial': 'I',
                 'Civilian': 'C', 'Competition': 'K'}.get(klasse, '–')
    grad_b = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}.get(grad, '–')
    return '%s/%s/%s' % (buchstabe, grad_b, groesse if groesse else '–')


def quelle_text(q):
    """Eine Bezugsquelle in einem Satz."""
    teile = []
    if q.get('fraktion'):
        teile.append(q['fraktion'])
    if q.get('typ'):
        teile.append(q['typ'])
    kopf = ' · '.join(teile)
    unten = []
    if q.get('rang'):
        unten.append(t('ab_rang', q['rang'])
                     + (' ' + t('ruf_punkte', f"{q['rep']:,}".replace(',', '.'))
                        if q.get('rep') else ''))
    if q.get('uec'):
        unten.append('%s aUEC' % f"{q['uec']:,}".replace(',', '.'))
    if q.get('ruf'):
        unten.append(t('ruf_gewinn', q['ruf']))
    return kopf, (q.get('auftrag') or ''), ' · '.join(unten)


class Bestandsfenster:
    """Eigenständiges Fenster. Wird von der Melde-Leiste aus geöffnet."""

    def __init__(self, eltern=None, beim_schliessen=None):
        self.beim_schliessen = beim_schliessen
        self.root = tk.Toplevel(eltern) if eltern else tk.Tk()
        self.root.title(t('titel_bauplaene'))
        self.root.configure(bg=BG)
        self.root.geometry('720x780')

        self.bestand = bestand_datei.laden()
        self.katalog = katalog_modul.laden()
        self.filter = 'alle'
        self.suche = tk.StringVar()
        self.suche.trace_add('write', lambda *_: self._zeichnen(nach_oben=True))
        self.offen = set()          # Namen, deren Herkunft ausgeklappt ist
        self.alle_zeigen = False

        self._kopf()
        self._werkzeugleiste()
        self._liste()
        self._zeichnen()

    # ------------------------------------------------------------------ Aufbau
    def _kopf(self):
        bar = tk.Frame(self.root, bg=BAR)
        bar.pack(fill='x')
        tk.Label(bar, text=t('bauplaene'), bg=BAR, fg=FG,
                 font=schrift(12, True)).pack(side='left', padx=14, pady=10)
        self.fortschritt = tk.Label(bar, text='', bg=BAR, fg=SUB, font=schrift(10))
        self.fortschritt.pack(side='left')
        zu = tk.Label(bar, text='✕', bg=BAR, fg=SUB, font=schrift(12), cursor='hand2')
        zu.pack(side='right', padx=14)
        zu.bind('<Button-1>', lambda e: self.schliessen())
        hinweis.anhaengen(zu, lambda: t('hinweis_schliessen_liste'))

    def _werkzeugleiste(self):
        leiste = tk.Frame(self.root, bg=BG)
        leiste.pack(fill='x', padx=14, pady=(12, 8))

        feld = tk.Entry(leiste, textvariable=self.suche, bg=FLAECHE, fg=FG,
                        insertbackground=FG, relief='flat', font=schrift(11))
        feld.pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 10))
        feld.focus_set()

        self.knoepfe = {}
        for schluessel, text in (('alle', t('filter_alle')),
                                 ('habe', t('filter_habe')),
                                 ('fehlt', t('filter_fehlt')),
                                 ('merk', '⭐ ' + t('filter_merk'))):
            k = tk.Label(leiste, text=' %s ' % text, bg=FLAECHE, fg=SUB,
                         font=schrift(10), cursor='hand2', padx=8, pady=5)
            k.pack(side='left', padx=2)
            k.bind('<Button-1>', lambda e, s=schluessel: self._filter_setzen(s))
            self.knoepfe[schluessel] = k

    def _liste(self):
        rahmen = tk.Frame(self.root, bg=BG)
        rahmen.pack(fill='both', expand=True, padx=14, pady=(0, 10))
        self.leinwand = tk.Canvas(rahmen, bg=BG, highlightthickness=0)
        rolle = tk.Scrollbar(rahmen, orient='vertical',
                             command=self.leinwand.yview)
        self.inhalt = tk.Frame(self.leinwand, bg=BG)
        self.inhalt.bind('<Configure>', lambda e: self.leinwand.configure(
            scrollregion=self.leinwand.bbox('all')))
        self.fenster = self.leinwand.create_window((0, 0), window=self.inhalt,
                                                   anchor='nw')
        self.leinwand.bind('<Configure>', lambda e: self.leinwand.itemconfigure(
            self.fenster, width=e.width))
        self.leinwand.configure(yscrollcommand=rolle.set)
        self.leinwand.pack(side='left', fill='both', expand=True)
        rolle.pack(side='right', fill='y')
        for ereignis in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.leinwand.bind_all(ereignis, self._rollen)

    def _rollen(self, e):
        richtung = -1 if getattr(e, 'num', 0) == 4 or getattr(e, 'delta', 0) > 0 else 1
        self.leinwand.yview_scroll(richtung, 'units')

    # ----------------------------------------------------------------- Zeichnen
    def _filter_setzen(self, welcher):
        self.filter = welcher
        self.alle_zeigen = False
        self._zeichnen(nach_oben=True)

    def _auswahl(self):
        """Die Baupläne, die gerade angezeigt werden sollen."""
        text = self.suche.get().strip().lower()
        habe = bestand_datei.schluessel(self.bestand)
        beobachtet = merk.namen()
        ergebnis = []
        for art, liste in sorted(katalog_modul.nach_art(self.katalog).items()):
            treffer = []
            for e in liste:
                k = katalog_modul._norm(e['n'])
                drin = k in habe
                if self.filter == 'habe' and not drin:
                    continue
                if self.filter == 'fehlt' and drin:
                    continue
                if self.filter == 'merk' and katalog_modul._norm(e['n']) not in beobachtet:
                    continue
                if text and text not in e['n'].lower() and text not in art.lower():
                    continue
                treffer.append((e, drin))
            if treffer:
                ergebnis.append((art, treffer))
        return ergebnis

    def _zeichnen(self, nach_oben=False):
        """Die Liste neu aufbauen.

        `nach_oben` springt an den Anfang. Nötig bei Suche und Filter: Die
        Ansicht behält sonst ihre alte Scrollposition, und wenn aus 714 Zeilen
        plötzlich fünf werden, steht man vor **leerer Fläche** und hält die Suche
        für kaputt. Genau so gemeldet: „gebe ich xl ein, ist die Liste leer" —
        die fünf Treffer waren da, nur weit über dem sichtbaren Ausschnitt.

        Beim Abhaken, Merken und Ausklappen bleibt die Position dagegen stehen —
        dort wäre ein Sprung nach oben ein Verlust, man arbeitet ja an einer
        bestimmten Stelle."""
        for kind in self.inhalt.winfo_children():
            kind.destroy()

        for schluessel, knopf in self.knoepfe.items():
            an = schluessel == self.filter
            knopf.configure(fg=BG if an else SUB, bg=ACCENT if an else FLAECHE)

        gruppen = self._auswahl()
        habe = bestand_datei.schluessel(self.bestand)
        gesamt = len(self.katalog['bauplaene'])
        meine = sum(1 for k in self.katalog['bauplaene'] if k in habe)
        if gesamt:
            self.fortschritt.configure(
                text=t('von_gesamt', meine, gesamt,
                       round(100 * meine / gesamt)))
        elif not self.katalog['bauplaene']:
            self._hinweis_kein_katalog()
            return

        gezeichnet = 0
        for art, treffer in gruppen:
            if gezeichnet >= ZEILEN_ZUERST and not self.alle_zeigen:
                break
            self._gruppenkopf(art, treffer, habe)
            for eintrag, drin in treffer:
                if gezeichnet >= ZEILEN_ZUERST and not self.alle_zeigen:
                    break
                self._zeile(eintrag, drin)
                gezeichnet += 1

        rest = sum(len(t) for _, t in gruppen) - gezeichnet
        if rest > 0:
            mehr = tk.Label(self.inhalt, text=t('weitere_anzeigen', rest),
                            bg=BG, fg=ACCENT, font=schrift(10), cursor='hand2',
                            pady=10)
            mehr.pack(fill='x')
            mehr.bind('<Button-1>', lambda e: self._alle())
        if not gruppen:
            leer = (t('merkliste_leer') if self.filter == 'merk'
                    else t('nichts_gefunden'))
            tk.Label(self.inhalt, text=leer, bg=BG, fg=SUB, font=schrift(11),
                     pady=20, wraplength=520, justify='center').pack()

        if nach_oben:
            # Erst wenn Tk die neue Höhe kennt — sonst bezieht sich der Sprung
            # noch auf die Scrollfläche von vorher und landet daneben.
            self.root.after_idle(lambda: self.leinwand.yview_moveto(0))

    def _alle(self):
        self.alle_zeigen = True
        self._zeichnen()

    def _hinweis_kein_katalog(self):
        tk.Label(self.inhalt, text=t('kein_katalog'),
                 bg=BG, fg=FG, font=schrift(11), pady=14).pack()
        tk.Label(self.inhalt, bg=BG, fg=SUB, font=schrift(10), justify='left',
                 text=t('kein_katalog_hilfe')).pack()

    def _gruppenkopf(self, art, treffer, habe):
        drin = sum(1 for _, d in treffer if d)
        kopf = tk.Frame(self.inhalt, bg=BG)
        kopf.pack(fill='x', pady=(14, 4))
        tk.Label(kopf, text=art.upper(), bg=BG, fg=ACCENT, font=schrift(9, True),
                 anchor='w').pack(side='left')
        tk.Label(kopf, text='  %d/%d' % (drin, len(treffer)), bg=BG, fg=SUB,
                 font=schrift(9), anchor='w').pack(side='left')

    def _zeile(self, eintrag, drin):
        name = eintrag['n']
        zeile = tk.Frame(self.inhalt, bg=FLAECHE)
        zeile.pack(fill='x', pady=1)

        haken = tk.Label(zeile, text='✔' if drin else '○', bg=FLAECHE,
                         fg=ACCENT if drin else SUB, font=schrift(12),
                         cursor='hand2', padx=10, pady=6)
        haken.pack(side='left')
        haken.bind('<Button-1>', lambda e, n=name: self._umschalten(n))

        mitte = tk.Frame(zeile, bg=FLAECHE)
        mitte.pack(side='left', fill='x', expand=True)
        tk.Label(mitte, text=name, bg=FLAECHE, fg=FG if drin else SUB,
                 font=schrift(11), anchor='w').pack(fill='x')

        unten = [t for t in (kuerzel(eintrag), eintrag.get('m')) if t]
        if unten:
            tk.Label(mitte, text=' · '.join(unten), bg=FLAECHE, fg=SUB,
                     font=schrift(9), anchor='w').pack(fill='x')

        if eintrag.get('q'):
            zeichen = '▾' if name in self.offen else 'ⓘ'
            info = tk.Label(zeile, text=zeichen, bg=FLAECHE, fg=SUB,
                            font=schrift(11), cursor='hand2', padx=12)
            info.pack(side='right')
            info.bind('<Button-1>', lambda e, n=name: self._herkunft_umschalten(n))
            hinweis.anhaengen(info, lambda: t('hinweis_quellen'))

        # Stern: worauf man wartet, wird auffällig gemeldet, sobald es auftaucht.
        # Bei schon vorhandenen Bauplänen wäre das sinnlos — dort kein Stern.
        if not drin:
            gemerkt = merk.enthaelt(name)
            stern = tk.Label(zeile, text='⭐' if gemerkt else '☆', bg=FLAECHE,
                             fg=GELB if gemerkt else SUB, font=schrift(11),
                             cursor='hand2', padx=6)
            stern.pack(side='right')
            stern.bind('<Button-1>', lambda e, n=name: self._merken(n))
            hinweis.anhaengen(stern, lambda n=name: t('nicht_mehr_merken')
                              if merk.enthaelt(n) else t('merken'))

        if name in self.offen:
            self._herkunft(eintrag)

    def _herkunft(self, eintrag):
        kasten = tk.Frame(self.inhalt, bg=BG)
        kasten.pack(fill='x', padx=(34, 0), pady=(0, 6))
        for q in eintrag.get('q') or []:
            kopf, auftrag, unten = quelle_text(q)
            block = tk.Frame(kasten, bg=BG)
            block.pack(fill='x', pady=3)
            tk.Label(block, text=kopf, bg=BG, fg=GELB, font=schrift(10),
                     anchor='w').pack(fill='x')
            if auftrag:
                tk.Label(block, text='„%s"' % auftrag, bg=BG, fg=FG,
                         font=schrift(10), anchor='w',
                         wraplength=600, justify='left').pack(fill='x')
            if unten:
                tk.Label(block, text=unten, bg=BG, fg=SUB, font=schrift(9),
                         anchor='w').pack(fill='x')

    # ------------------------------------------------------------------ Aktion
    def _umschalten(self, name):
        """Häkchen setzen oder entfernen — und sofort auf die Platte schreiben."""
        if bestand_datei.enthaelt(self.bestand, name):
            bestand_datei.entfernen(self.bestand, name)
        else:
            bestand_datei.hinzufuegen(self.bestand, name, 'hand')
        bestand_datei.speichern(self.bestand)
        self._zeichnen()

    def _merken(self, name):
        """Stern an oder aus — sofort auf die Platte, kein Speichern-Knopf."""
        merk.umschalten(name)
        self._zeichnen()

    def _herkunft_umschalten(self, name):
        self.offen.discard(name) if name in self.offen else self.offen.add(name)
        self._zeichnen()

    def schliessen(self):
        if self.beim_schliessen:
            self.beim_schliessen()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    Bestandsfenster().run()
