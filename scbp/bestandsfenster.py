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
from tkinter import filedialog

from . import bestand as bestand_datei
from . import export as export_modul
from . import hinweis
from . import katalog as katalog_modul
from . import merkliste as merk
from . import pfade
from .sprache import t

BG      = '#10141c'
FLAECHE = '#161c28'
BAR     = '#1b2230'
LINIE   = '#2a3345'   # Rand runder Kästen und Felder — überall dieselbe Linie
FG      = '#e6edf3'
SUB     = '#8b98a5'
ACCENT  = '#9ce430'
GELB    = '#d8a03a'

# Ab wie vielen Zeilen nur noch der Anfang gezeigt wird. 714 Zeilen einzeln zu
# bauen dauert in tkinter spürbar lange, und niemand scrollt durch 714 Zeilen —
# wer etwas sucht, tippt. Der Rest kommt auf Knopfdruck.
ZEILEN_ZUERST = 120
# Die Programmversion wird vom Hauptprogramm gesetzt; sie landet im
# scmdb-Export als Kennung des erzeugenden Werkzeugs.
VERSION = ['']


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
    return kopf, (q.get('auftrag') or ''), ' · '.join(unten), ort_text(q.get('wo'))


def ort_text(wo):
    """Wo der Auftrag angenommen wird — „Stanton: Hurston, Crusader, …".

    Von Nutzern gemeldet: Es stand da, *woher* ein Bauplan kommt, aber nicht,
    *wo* man den Auftrag findet. Ohne diese Zeile muss man den Missionsnamen
    anderswo nachschlagen, und damit ist der halbe Nutzen der Liste dahin."""
    if not wo:
        return ''
    orte = ', '.join(wo.get('orte') or [])
    if wo.get('mehr'):
        orte += t('und_weitere', wo['mehr'])
    system = wo.get('system')
    if system and orte:
        return '%s %s: %s' % (t('annehmen_in'), system, orte)
    return '%s %s' % (t('annehmen_in'), system or orte)


# Was die Suche außer dem Namen noch durchsucht. Von einem Nutzer gewünscht:
# nach „military", „civilian", „stealth" suchen können — die Klasse steht in
# jeder Zeile, war aber bis dahin nicht auffindbar. Hersteller und Gütegrad
# kommen mit, aus demselben Grund.
#
# Tatsächlich vorhandene Klassen (gemessen am Katalog 4.9.0): Civilian 72,
# Energy 45, Military 38, Ballistic 30, Industrial 25, Stealth 22, Electron 6,
# Laser 2. „Competition" kommt in den Daten nicht vor — es steht trotzdem in
# der Kürzel-Tabelle des Overlays, schadet aber nicht.
#
# Der Gütegrad steht als **Zahl** (1–4), angezeigt wird ein Buchstabe. Wer
# „Grade A" sucht, tippt den Buchstaben — also muss hier umgerechnet werden,
# sonst findet die Suche nie etwas.
GRAD_BUCHSTABE = {1: 'a', 2: 'b', 3: 'c', 4: 'd'}


def _passt(eintrag, text):
    """Trifft der Suchbegriff diesen Bauplan — Name, Klasse, Hersteller, Grad?"""
    if text in eintrag['n'].lower():
        return True
    klasse = (eintrag.get('c') or '').lower()
    if klasse and text in klasse:
        return True
    hersteller = (eintrag.get('m') or '').lower()
    if hersteller and text in hersteller:
        return True
    # „grade a" und „size 2" — so, wie es in der Zeile steht
    grad = GRAD_BUCHSTABE.get(eintrag.get('g'))
    if grad and text in ('grade %s' % grad, 'grad %s' % grad, grad):
        return True
    if eintrag.get('s') and text in ('size %s' % eintrag['s']).lower():
        return True
    return False


class Bestandsfenster:
    """Eigenständiges Fenster. Wird von der Melde-Leiste aus geöffnet."""

    def __init__(self, eltern=None, beim_schliessen=None, rahmen=None):
        """Ohne `rahmen` ein eigenes Fenster, mit `rahmen` eine Seite im Hauptfenster.

        Seit v3.0.0 liegt die Liste im Hauptfenster; der eigenständige Modus
        bleibt, weil er sich einzeln starten und prüfen lässt.
        """
        self.beim_schliessen = beim_schliessen
        self.eingebettet = rahmen is not None
        if self.eingebettet:
            self.root = rahmen
            self.root.configure(bg=BG)
        else:
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
        self.bereiche_aus = set()   # ausgeblendete Bereiche (Schiff, FPS, …)

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
        # Export rechts in der Kopfzeile — dort, wo man ihn sucht, wenn man die
        # Liste vor sich hat. Geschrieben wird eine Datei; hochladen macht der
        # Spieler selbst (nichts verlässt den Rechner ungefragt).
        # Ein Knopf für den Regelfall (alle Formate in die Ablage), einer für
        # den Einzelfall (eine Datei, Ziel selbst wählen). Drei Knöpfe für drei
        # Formate wären eine Zumutung — die wenigsten wollen sich mit dem
        # Unterschied befassen.
        for text, tat, abstand in (
                (t('export_ablage'), self._in_ablage, (0, 14)),
                (t('export_einzeln'), lambda: self._exportieren('basetool'), (0, 6))):
            from .hauptfenster import rundknopf
            k = rundknopf(bar, text, None, schrift(9), BAR, FLAECHE, LINIE, FG)
            k.pack(side='right', padx=abstand)
            k.bind('<Button-1>', lambda e, f=tat: f())
            hinweis.anhaengen(k, lambda: t('hinweis_export'))
        self.export_meldung = tk.Label(bar, text='', bg=BAR, fg=ACCENT,
                                       font=schrift(9))
        self.export_meldung.pack(side='right', padx=(0, 10))
        # Kein eigenes ✕: Dieses Fenster hat eine ganz normale Titelleiste vom
        # System, und die hat bereits eins. Zwei Kreuze übereinander sehen aus
        # wie ein Fehler — und man rät, welches was tut. (Betraf Windows genauso,
        # die Leiste kommt dort ebenfalls vom Fenstermanager.) Das randlose
        # Overlay ist der andere Fall: Dort gibt es keine Systemleiste, deshalb
        # behält es sein eigenes ✕.

    def _in_ablage(self):
        """Alle Formate auf einmal in den Ablage-Ordner — und ihn öffnen."""
        ok, ordner, dateien = export_modul.ablegen(self.bestand, self.katalog,
                                                   VERSION[0])
        if not ok:
            self.export_meldung.configure(text=t('export_fehler', ordner),
                                          fg=GELB)
            return
        self.export_meldung.configure(text=t('export_ablage_fertig',
                                             len(dateien)), fg=ACCENT)
        # Ordner zeigen: Eine Datei, die man nicht findet, hilft niemandem.
        try:
            import subprocess, sys as _sys
            if _sys.platform.startswith('win'):
                os.startfile(ordner)                       # noqa: S606
            else:
                subprocess.Popen(['xdg-open', ordner],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.root.after(8000, lambda: self.export_meldung.configure(text=''))

    def _exportieren(self, art):
        """Bestand als Datei ausgeben — Ziel wählt der Spieler."""
        pfad = filedialog.asksaveasfilename(
            parent=self.root, title=t('export_basetool' if art == 'basetool'
                                      else 'export_alles'),
            initialfile=export_modul.vorschlag(art),
            defaultextension='.json',
            filetypes=[('JSON', '*.json'), (t('alle_dateien'), '*.*')])
        if not pfad:
            return
        ok, meldung = export_modul.schreiben(pfad, art, self.bestand,
                                             self.katalog)
        self.export_meldung.configure(
            text=t('export_fertig', meldung) if ok else t('export_fehler', meldung),
            fg=ACCENT if ok else GELB)
        # Nach ein paar Sekunden wieder wegnehmen — eine Erfolgsmeldung, die
        # stehen bleibt, wird zur Beschriftung und sagt dann nichts mehr.
        self.root.after(6000, lambda: self.export_meldung.configure(text=''))

    def _werkzeugleiste(self):
        leiste = tk.Frame(self.root, bg=BG)
        leiste.pack(fill='x', padx=14, pady=(12, 4))

        # Suchfeld mit Löschkreuz: Das ✕ liegt im selben Kasten wie das Feld,
        # damit es dazugehörig aussieht und nicht wie ein weiterer Knopf.
        from .hauptfenster import rundrahmen
        kasten = rundrahmen(leiste, FLAECHE, LINIE, radius=8, grundfarbe=BG)
        kasten.halter.pack(side='left', fill='x', expand=True, padx=(0, 10))
        feld = tk.Entry(kasten, textvariable=self.suche, bg=FLAECHE, fg=FG,
                        insertbackground=FG, relief='flat', bd=0,
                        highlightthickness=0, font=schrift(11))
        feld.pack(side='left', fill='x', expand=True, ipady=6, padx=(8, 0))
        feld.focus_set()
        self.loeschen_lbl = tk.Label(kasten, text='✕', bg=FLAECHE, fg=SUB,
                                     font=schrift(10), cursor='hand2', padx=8)
        self.loeschen_lbl.bind('<Button-1>', lambda e: self._suche_leeren())
        hinweis.anhaengen(self.loeschen_lbl, lambda: t('hinweis_suche_leeren'))
        # Erscheint erst, wenn etwas drinsteht — ein ✕ an einem leeren Feld ist
        # nur ein Zeichen, das nichts tut.
        self._loeschkreuz_zeigen()

        self.knoepfe = {}
        for schluessel, text in (('alle', t('filter_alle')),
                                 ('habe', t('filter_habe')),
                                 ('fehlt', t('filter_fehlt')),
                                 ('merk', '⭐ ' + t('filter_merk'))):
            from .hauptfenster import rundknopf
            k = rundknopf(leiste, text, None, schrift(10), BG, FLAECHE, LINIE,
                          SUB)
            k.pack(side='left', padx=2)
            k.bind('<Button-1>', lambda e, s=schluessel: self._filter_setzen(s))
            self.knoepfe[schluessel] = k

        # Zweite Reihe: die Bereiche. 25 Kategorien einzeln wären keine Hilfe —
        # vier Knöpfe schon: Wer Rüstung sucht, blendet das Schiff weg und hat
        # statt 714 Zeilen noch 316.
        bereiche = tk.Frame(self.root, bg=BG)
        bereiche.pack(fill='x', padx=14, pady=(0, 8))
        self.bereich_knoepfe = {}
        for og in katalog_modul.OBERGRUPPEN:
            from .hauptfenster import rundknopf
            k = rundknopf(bereiche, t('gruppe_%s' % og), None, schrift(10), BG,
                          FLAECHE, LINIE, SUB)
            k.pack(side='left', padx=(0, 4))
            k.bind('<Button-1>', lambda e, g=og: self._bereich_umschalten(g))
            hinweis.anhaengen(k, lambda: t('hinweis_bereich'))
            self.bereich_knoepfe[og] = k

    def _suche_leeren(self):
        self.suche.set('')

    def _loeschkreuz_zeigen(self):
        """Das ✕ nur zeigen, wenn es etwas zu löschen gibt."""
        if self.suche.get():
            self.loeschen_lbl.pack(side='right')
        else:
            self.loeschen_lbl.pack_forget()

    def _bereich_umschalten(self, gruppe):
        """Einen Bereich ein- oder ausblenden.

        Der letzte sichtbare lässt sich nicht auch noch ausblenden — eine leere
        Liste ohne erkennbaren Grund ist keine Einstellung, sondern ein Rätsel."""
        if gruppe in self.bereiche_aus:
            self.bereiche_aus.discard(gruppe)
        elif len(self.bereiche_aus) < len(katalog_modul.OBERGRUPPEN) - 1:
            self.bereiche_aus.add(gruppe)
        self.alle_zeigen = False
        self._zeichnen(nach_oben=True)

    def _liste(self):
        rahmen = tk.Frame(self.root, bg=BG)
        rahmen.pack(fill='both', expand=True, padx=14, pady=(0, 10))
        self.leinwand = tk.Canvas(rahmen, bg=BG, highlightthickness=0)
        from .hauptfenster import rundleiste
        rolle = rundleiste(rahmen, self.leinwand, grund=BG)
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
        # ⚠ Hier stand `bind_all` OHNE `add='+'`. Das ersetzt jede vorher
        # gesetzte Bindung im ganzen Fenster — und weil diese Liste die
        # Startseite ist, war die Bindung aller anderen Seiten sofort wieder
        # weg. Danach rollte das Rad überall nur noch diese Liste, auch wenn
        # sie gar nicht zu sehen war.
        from .hauptfenster import rad_anschliessen
        rad_anschliessen(self.leinwand)

    # ----------------------------------------------------------------- Zeichnen
    def _filter_setzen(self, welcher):
        self.filter = welcher
        self.alle_zeigen = False
        self._zeichnen(nach_oben=True)

    def _auswahl(self):
        """Die Baupläne, die gerade angezeigt werden sollen.

        Die Reihenfolge kommt aus `katalog.gruppen_geordnet()`: erst die
        Schiffsteile, dann die FPS-Waffen, dann Rüstung und Kleidung. Nach
        Alphabet stand vorher „Andockkragen" ganz oben und die Rüstung
        mittendrin."""
        text = self.suche.get().strip().lower()
        habe = bestand_datei.schluessel(self.bestand)
        beobachtet = merk.namen()
        ergebnis = []
        for og, art, liste in katalog_modul.gruppen_geordnet(self.katalog):
            if og in self.bereiche_aus:
                continue
            # Suchwörter der Art: „Kühler" soll die Cooler finden, obwohl die
            # Kategorie im Spiel englisch heißt.
            wortliste = katalog_modul.suchworte(liste[0].get('a')) if liste else ()
            art_passt = bool(text) and (text in art.lower()
                                        or any(text in w for w in wortliste))
            treffer = []
            for e in liste:
                k = katalog_modul._norm(e['n'])
                drin = k in habe
                if self.filter == 'habe' and not drin:
                    continue
                if self.filter == 'fehlt' and drin:
                    continue
                if self.filter == 'merk' and k not in beobachtet:
                    continue
                if text and not art_passt and not _passt(e, text):
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
        bestimmten Stelle.

        ⚠ „Bleibt stehen" ging so nicht auf: Tk merkt sich den **Anteil** der
        Scrollfläche, nicht die Pixelhöhe. Klappt man die Herkunft aus, wird
        die Liste länger, derselbe Anteil zeigt plötzlich weiter oben — und die
        angeklickte Zeile ist weg. Gemessen: 0,50 sprang auf 0,43, also ein
        halbes Fenster weit. Deshalb wird hier die **Pixelhöhe** gemerkt und
        danach zurückgerechnet."""
        oben_px = None
        if not nach_oben:
            try:
                oben_px = self.leinwand.canvasy(0)
            except tk.TclError:
                oben_px = None

        for kind in self.inhalt.winfo_children():
            kind.destroy()

        for schluessel, knopf in self.knoepfe.items():
            an = schluessel == self.filter
            knopf.setzen(fuellung=ACCENT if an else FLAECHE,
                         neuer_rand=ACCENT if an else LINIE,
                         neues_fg=BG if an else SUB)

        # Ausgeblendete Bereiche werden abgedunkelt, nicht entfernt — man muss
        # sehen, dass man selbst etwas weggeklickt hat.
        for og, knopf in self.bereich_knoepfe.items():
            aus = og in self.bereiche_aus
            knopf.setzen(fuellung=BG if aus else FLAECHE,
                         neuer_rand=LINIE, neues_fg=SUB if aus else FG)
        self._loeschkreuz_zeigen()

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
        elif oben_px is not None:
            self.root.after_idle(lambda: self._zurueck_zu(oben_px))

    def _zurueck_zu(self, oben_px):
        """Denselben Pixel wieder nach oben holen, egal wie lang die Liste ist.

        ⚠ Zweimal aufgepasst werden muss hier:

        * **Wann** gemessen wird. `after_idle` allein reicht nicht — die Zeilen
          sind dann gepackt, aber noch nicht vermessen, und `winfo_reqheight`
          meldet einen zu kleinen Wert. Damit wird aus jedem Anteil eine 1,0,
          und die Liste springt ans Ende. Genau so gemessen: aus Pixel 1700
          wurde 5202. Deshalb erst `update_idletasks`.
        * **Woran** gemessen wird: an der Scrollfläche (`bbox('all')`), denn
          auf die bezieht sich `yview_moveto`.
        """
        try:
            self.leinwand.update_idletasks()
            bereich = self.leinwand.bbox('all')
            gesamt = float(bereich[3]) if bereich else 0.0
            if gesamt > 1:
                self.leinwand.yview_moveto(max(0.0, min(1.0, oben_px / gesamt)))
        except tk.TclError:
            pass

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
        elif eintrag.get('start'):
            # Startbaupläne: hat jeder von Anfang an, stehen in keinem Pool und
            # in keinem Log. Eigenes Zeichen, damit niemand nach einem Auftrag
            # sucht, den es nicht gibt.
            std = tk.Label(zeile, text='◆', bg=FLAECHE, fg=ACCENT,
                           font=schrift(10), padx=12)
            std.pack(side='right')
            hinweis.anhaengen(std, lambda: t('hinweis_startbauplan'))
        else:
            # 59 Baupläne haben in den Daten keine Bezugsquelle — überwiegend
            # Event-Belohnungen („Purgatory Camo", „SecondWind"). Ohne Zeichen
            # sähe die Zeile aus, als hätte jemand vergessen, die Herkunft
            # einzutragen; mit ? steht da, was Sache ist: Es gibt keinen Auftrag,
            # über den man da herankommt.
            leer = tk.Label(zeile, text='?', bg=FLAECHE, fg=SUB,
                            font=schrift(11), padx=12)
            leer.pack(side='right')
            hinweis.anhaengen(leer, lambda: t('hinweis_ohne_quelle'))

        # Stern: worauf man wartet, wird auffällig gemeldet, sobald es auftaucht.
        # Bei schon vorhandenen Bauplänen wäre das sinnlos — dort kein Stern.
        if not drin:
            gemerkt = merk.enthaelt(name)
            # Größer als der Rest: Der Stern ist das einzige Zeichen in der
            # Zeile, das man *trifft* statt liest — in Zeilenschrift war er zu
            # klein zum Klicken und ging neben dem Namen unter.
            stern = tk.Label(zeile, text='⭐' if gemerkt else '☆', bg=FLAECHE,
                             fg=GELB if gemerkt else SUB, font=schrift(16),
                             cursor='hand2', padx=10)
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
            kopf, auftrag, unten, wo = quelle_text(q)
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
            if wo:
                tk.Label(block, text=wo, bg=BG, fg=ACCENT, font=schrift(9),
                         anchor='w', wraplength=600,
                         justify='left').pack(fill='x')

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
        if getattr(self, 'eingebettet', False):
            return                     # eine Seite schließt sich nicht selbst
        if self.beim_schliessen:
            self.beim_schliessen()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    Bestandsfenster().run()
