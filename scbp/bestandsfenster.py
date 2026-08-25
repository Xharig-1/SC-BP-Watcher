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

from . import fehler
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
#
# ⚠ Der Wert ist **gemessen**, nicht geschätzt. Das erste Zeichnen wächst
# überproportional, weil Tk alle Widgets auf einmal darstellen muss (gemessen
# auf dem Mac, Tk 9.0, echter Katalog mit 722 Bauplänen):
#
#     10 Zeilen   0,45 s        60 Zeilen    5,05 s
#     30 Zeilen   1,14 s       120 Zeilen   30,36 s
#
# Bei 120 waren es 801 Widgets und eine halbe Minute, in der das Fenster steht
# — gemeldet als „Fenster geht auf, dauert aber ewig". Jedes weitere Zeichnen
# danach dauert nur 0,4 s; teuer ist ausschließlich der erste Aufbau.
#
# 40 ist der Kompromiss: gut zwei Bildschirmhöhen sofort da, unter zwei
# Sekunden Wartezeit. Wer mehr will, tippt oder klickt auf „weitere anzeigen".
ZEILEN_ZUERST = 40

# Ab welcher Inhaltshöhe die Liste in Blöcken gezeigt werden muss.
#
# ⚠ Das ist keine Geschmacksfrage, sondern eine harte Grenze des Fenstersystems:
# X11 rechnet Fensterkoordinaten in **16 Bit**, es gibt also keine Position
# jenseits von 32767 Pixeln. Ein Frame in einer Leinwand, der höher wird, sitzt
# ab dort nicht mehr dort, wo Tk ihn hinrechnet — die Zeilen am Ende der Liste
# **überlappen einander**. Gemessen mit einem echten Katalog bei 125 % Anzeige-
# Skalierung: Inhalt 33452 px, davon 16 Elemente jenseits der Grenze — und genau
# die überlagerten sich.
#
# Ein Sicherheitsabstand bis 32000 px. Wie viele Zeilen das sind, hängt von
# Schriftgröße und Skalierung ab und wird gemessen, nicht geraten (siehe
# `_zeilen_deckel`). Wird es mehr, übernimmt der Blockmodus — abgeschnitten wird
# nichts, siehe „Lange Liste in Blöcken".
HOECHSTE_INHALTSHOEHE = 32000

# Wie viele Reihen in einen Block kommen, wenn die Liste in Blöcken gezeigt
# wird (siehe „Lange Liste in Blöcken"). 120 Reihen sind rund 5000 Pixel —
# klein genug, dass immer nur wenige Blöcke gleichzeitig gebaut sein müssen,
# und groß genug, dass beim Rollen nicht dauernd neu gebaut wird.
BLOCK_REIHEN = 120
# Die Programmversion wird vom Hauptprogramm gesetzt; sie landet im
# scmdb-Export als Kennung des erzeugenden Werkzeugs.
VERSION = ['']


def schrift(groesse, fett=False, unterstrichen=False):
    """Die Schrift dieses Fensters.

    `unterstrichen` ist für Textlinks — im Haus die Auszeichnung dafür, dass
    man klicken kann. Ohne sie sieht ein Textlink aus wie ein Hinweis.
    """
    fam = 'Segoe UI' if pfade.WINDOWS else 'Helvetica'
    stil = ' '.join(x for x, an in (('bold', fett),
                                    ('underline', unterstrichen)) if an)
    return (fam, groesse, stil or 'normal')


def mono(groesse):
    return ('Consolas' if pfade.WINDOWS else 'Menlo', groesse)


def kuerzel(eintrag):
    """Klasse/Größe/Grad als „M/1/A" — leer, wo es nichts zu zeigen gibt.

    ⚠ Die Reihenfolge ist **Klasse, Größe, Grad**, nicht Klasse, Grad, Größe.
    So liest es sich wie im Spiel („Size 1, Grade A"), und die Größe ist beim
    Suchen das Wichtigere: Ein Cooler der falschen Größe passt gar nicht,
    einer mit anderem Grad passt schlechter.
    """
    klasse, grad, groesse = eintrag.get('c'), eintrag.get('g'), eintrag.get('s')
    if not (klasse or grad or groesse):
        return ''
    buchstabe = KLASSE_BUCHSTABE.get(klasse, '–')
    grad_b = GRAD_BUCHSTABE.get(grad, '–').upper()
    return '%s/%s/%s' % (buchstabe, groesse if groesse else '–', grad_b)


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

# Die Klassen, wie das Spiel sie kennt — mit ihrem Kürzel in der Zeile.
KLASSE_BUCHSTABE = {'Military': 'M', 'Stealth': 'S', 'Industrial': 'I',
                    'Civilian': 'C', 'Competition': 'K'}

# ⚠ Klassen, Größen und Grade stehen hier **fest**, nicht aus dem Katalog
# abgeleitet. Grund: Was gerade kein Bauplan hat, fehlte sonst in der Auswahl —
# gemeldet für „Competition" (kommt im Katalog 4.9.0 nicht vor), für die Größen
# 4 bis 6 und für die Grade B bis D. Ein Auswahlfeld, dessen Inhalt sich mit
# jedem Spiel-Patch ändert, ist keins: Man sucht etwas und findet den Eintrag
# nicht, ohne zu erfahren warum. Was der Katalog darüber hinaus hergibt, wird
# unten trotzdem ergänzt — verlieren soll man nichts.
KLASSEN_FEST = ('Military', 'Stealth', 'Industrial', 'Civilian', 'Competition')
GROESSEN_FEST = ('1', '2', '3', '4', '5', '6')
GRADE_FEST = ('1', '2', '3', '4')


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
        # ⚠ Reihenfolge: erst der feste Block unten, dann die rollende Liste.
        # Wer die Liste zuerst packt, schiebt den Block aus dem Fenster.
        self._herkunftsbereich()
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

        # ⚠ Eigene Zeile für die Zähler-Knöpfe. Vorher teilten sie sich die
        # Zeile mit dem Suchfeld, das `expand=True` hat — wurde das Fenster
        # schmaler, schnitt Tk den letzten Knopf ab: „⭐ be…" statt
        # „⭐ beobachtet". Der Entwurf trennt das ebenfalls in eigene Zeilen.
        knopfzeile = tk.Frame(self.root, bg=BG)
        knopfzeile.pack(fill='x', padx=14, pady=(0, 6))

        self.knoepfe = {}
        for schluessel, text in (('alle', t('filter_alle')),
                                 ('habe', t('filter_habe')),
                                 ('fehlt', t('filter_fehlt')),
                                 ('merk', '⭐ ' + t('filter_merk'))):
            from .hauptfenster import rundknopf
            k = rundknopf(knopfzeile, text, None, schrift(10), BG, FLAECHE,
                          LINIE, SUB)
            k.bind('<Button-1>', lambda e, s=schluessel: self._filter_setzen(s))
            self.knoepfe[schluessel] = k
        # Auch diese Reihe bricht um, falls selbst die eigene Zeile nicht reicht.
        self._reihe_umbrechen(knopfzeile, list(self.knoepfe.values()))

        self._feinfilter()

    def _feinfilter(self):
        """Fünf Auswahlfelder: Art, Klasse, Größe, Quelle, Gütegrad.

        ⚠ Hier standen vier Knöpfe, die Bereiche **ausblendeten** — also das
        Gegenteil dessen, was man erwartet: Wer nur FPS-Waffen sehen wollte,
        musste drei andere Bereiche wegklicken, und blendete man alle bis auf
        einen aus, blieb die Liste manchmal leer, ohne dass der Grund
        erkennbar war. Jetzt wird ausgewählt, was man sehen will.

        Die Einträge kommen aus dem Katalog, nicht aus einer festen Liste: Was
        es im Spiel nicht gibt, steht auch nicht zur Wahl.
        """
        from .hauptfenster import rundwahl

        reihe = tk.Frame(self.root, bg=BG)
        reihe.pack(fill='x', padx=14, pady=(0, 8))
        self.fein = {'art': '', 'klasse': '', 'groesse': '', 'quelle': '',
                     'grad': ''}

        # ⚠ Eigener Rahmen für die Auswahlfelder. Sie werden per `grid`
        # angeordnet (damit sie umbrechen können), und Tk verträgt `grid` und
        # `pack` nicht im selben Elternteil — daneben liegen aber der
        # Trefferzähler und „zurücksetzen", die gepackt sind.
        self.fein_rahmen = tk.Frame(reihe, bg=BG)
        self.fein_rahmen.pack(side='left', fill='x', expand=True)

        def feld(schluessel, eintraege):
            if len(eintraege) <= 1:      # nichts zu wählen — Feld weglassen
                return
            w = rundwahl(self.fein_rahmen, eintraege, '',
                         lambda wert, s=schluessel: self._fein_setzen(s, wert),
                         schrift(10), grund=BG)
            self.fein_felder[schluessel] = w

        self.fein_felder = {}
        # Die Zahl hinter jedem Eintrag sagt, was einen erwartet — und erklärt
        # eine Null, statt sie rätselhaft zu lassen.
        feld('art', [('', t('ff_alle_arten'))]
             + self._mit_zahl(self._arten(),
                              self._anzahl_je('a', katalog_modul.art_kennung)))
        feld('klasse', [('', t('ff_alle_klassen'))]
             + self._mit_zahl(self._klassen(), self._anzahl_je('c')))
        feld('groesse', [('', t('ff_alle_groessen'))]
             + self._mit_zahl(self._groessen(), self._anzahl_je('s')))
        feld('quelle', [('', t('ff_alle_quellen'))] + self._quellen())
        feld('grad', [('', t('ff_alle_grade'))]
             + self._mit_zahl(self._grade(), self._anzahl_je('g')))

        self.zuruecksetzen_lbl = tk.Label(
            reihe, text=t('ff_zuruecksetzen'), bg=BG, fg=SUB,
            font=schrift(9, unterstrichen=True), cursor='hand2', padx=6)
        self.zuruecksetzen_lbl.bind('<Button-1>', lambda e: self._fein_leeren())

        self.treffer_lbl = tk.Label(reihe, text='', bg=BG, fg=SUB,
                                    font=schrift(9))
        self.treffer_lbl.pack(side='right')
        self._reihe_umbrechen(
            self.fein_rahmen,
            [self.fein_felder[k] for k in
             ('art', 'klasse', 'groesse', 'quelle', 'grad')
             if k in self.fein_felder],
            rechts_frei=self.treffer_lbl)

    def _reihe_umbrechen(self, rahmen, elemente, rechts_frei=None):
        """Eine Reihe von Bedienelementen umbrechen lassen, wenn es eng wird.

        ⚠ Tk bricht nicht um, es schneidet ab. Gemeldet für beide Reihen der
        Bauplan-Liste: „rechts ist was abgeschnitten" (das fünfte Auswahlfeld
        stand halb da) und bei Mindestbreite blieben von vier Zähler-Knöpfen
        nur zwei übrig — „und das werden User sicherlich nutzen". Im Entwurf
        macht das `flex-wrap: wrap`; hier ist es von Hand nachgebaut.

        `rechts_frei` ist ein Widget, für das rechts Platz bleiben soll (der
        Trefferzähler).

        ⚠ Angeordnet wird per `grid`, nicht per `pack` mit Zwischenrahmen. Ein
        erster Anlauf hängte die Elemente in neue Halter (`feld.master = …`) —
        den Elternteil eines Tk-Widgets kann man aber nicht nachträglich
        umsetzen, und die fünf Auswahlfelder verschwanden daraufhin
        vollständig aus dem Fenster. Mit `grid` bleibt jedes Element, wo es
        gebaut wurde, und wechselt nur Zeile und Spalte.
        """
        def ordnen(_=None):
            platz = rahmen.winfo_width()
            if platz <= 1:
                return
            if rechts_frei is not None:
                try:
                    platz -= rechts_frei.winfo_reqwidth() + 12
                except tk.TclError:
                    pass
            plaetze, zeile, spalte, breite = [], 0, 0, 0
            for element in elemente:
                braucht = element.winfo_reqwidth() + 6
                if spalte and breite + braucht > platz:
                    zeile, spalte, breite = zeile + 1, 0, 0
                plaetze.append((element, zeile, spalte))
                spalte += 1
                breite += braucht
            if plaetze == getattr(rahmen, 'zuletzt', None):
                return                  # unverändert — nicht neu setzen
            rahmen.zuletzt = plaetze
            for element, z, s in plaetze:
                element.grid(row=z, column=s, sticky='w',
                             padx=(0, 6), pady=(0 if z == 0 else 4, 0))

        rahmen.bind('<Configure>', ordnen, add='+')
        rahmen.after_idle(ordnen)

    # --- Woraus die Auswahlfelder ihre Einträge nehmen ---
    def _kat_werte(self, feld):
        """Alle im Katalog vorkommenden Werte eines Feldes, alphabetisch."""
        werte = set()
        for e in (self.katalog.get('bauplaene') or {}).values():
            wert = e.get(feld)
            if wert:
                werte.add(wert)
        return sorted(werte, key=lambda x: str(x).lower())

    def _arten(self):
        """Die Arten für das Auswahlfeld — zusammengehörende nur einmal.

        ⚠ Über `art_kennung`, nicht über das rohe Feld: Sonst stehen `ammo`
        und `WeaponAttachment` als zwei Einträge in der Liste, beide mit der
        Beschriftung „Magazin" — einer mit 34 Bauplänen, einer mit null.
        """
        arten = {}
        for e in (self.katalog.get('bauplaene') or {}).values():
            roh = katalog_modul.art_kennung(e)
            if roh:
                arten[roh] = katalog_modul.art_lesbar(roh)
        return sorted(arten.items(), key=lambda p: p[1].lower())

    def _anzahl_je(self, feld, kennung=None):
        """Wie viele Baupläne hat jeder Wert dieses Feldes?

        Damit steht in der Auswahlliste, was einen erwartet — und eine Null
        ist erklärt statt rätselhaft. Gemeldet wurde „Competition findet
        nichts": Die Klasse steht zu Recht in der Liste (das Spiel kennt sie),
        nur hat im Katalog 4.9.0 kein einziger Bauplan sie.
        """
        from collections import Counter
        zaehler = Counter()
        nur_echte = feld in ('g', 's')
        for e in (self.katalog.get('bauplaene') or {}).values():
            if nur_echte and not self._feld_zaehlt(e, feld):
                continue          # dort ist die Zahl ohne Bedeutung — nicht mitzählen
            wert = kennung(e) if kennung else e.get(feld)
            if wert is not None and wert != '':
                zaehler[str(wert)] += 1
        return zaehler

    # ------------------------------- Wo Grad und Größe überhaupt etwas bedeuten
    #
    # ⚠ „Grad A" lieferte 603 von 722 Bauplänen — der Filter rechnete richtig, aber
    # die Zahl im Katalog steht nicht überall für etwas. Bei Schiffsteilen ist der
    # Gütegrad echt verteilt (Cooler: 11×A, 15×B, 12×C, 7×D); bei Rüstung steht
    # 314-mal die 1, weil das Feld ausgefüllt sein muss, nicht weil es Grad A wäre.
    # Dasselbe bei der Größe: 445-mal die 1.
    #
    # Deshalb wirken beide Filter nur auf die Arten, bei denen der Wert wirklich
    # unterschiedlich ausfällt. Das wird **aus den Daten abgeleitet**, nicht in eine
    # Liste geschrieben: Gibt CIG der Rüstung eines Tages echte Grade, greift der
    # Filter dort von selbst — und niemand muss daran denken, hier etwas
    # nachzutragen.
    #
    # Die Zehn-Prozent-Schwelle fängt Einzelfälle ab: Bei den Helmen tragen zwei von
    # 82 einen anderen Grad. Zwei Ausreißer machen aus einem bedeutungslosen Feld
    # noch kein Merkmal, nach dem man sinnvoll sucht.
    VERTEILT_MINDESTANTEIL = 0.10

    def _arten_mit_echtem(self, feld):
        """Bei welchen Arten sagt dieses Feld etwas aus? (Menge von Art-Kennungen)"""
        merker = getattr(self, '_verteilt_merker', None)
        if merker is None:
            merker = self._verteilt_merker = {}
        if feld in merker:
            return merker[feld]
        from collections import Counter
        je_art = {}
        for e in (self.katalog.get('bauplaene') or {}).values():
            wert = e.get(feld)
            if wert in (None, ''):
                continue
            je_art.setdefault(katalog_modul.art_kennung(e), Counter())[str(wert)] += 1
        echt = set()
        for art, zaehler in je_art.items():
            gesamt = sum(zaehler.values())
            haeufigste = zaehler.most_common(1)[0][1]
            if gesamt and (gesamt - haeufigste) / float(gesamt) >= self.VERTEILT_MINDESTANTEIL:
                echt.add(art)
        merker[feld] = echt
        return echt

    def _feld_zaehlt(self, eintrag, feld):
        """Zählt dieser Bauplan für den Grad- bzw. Größenfilter überhaupt mit?"""
        return katalog_modul.art_kennung(eintrag) in self._arten_mit_echtem(feld)

    def _mit_zahl(self, eintraege, zaehler):
        """An jede Beschriftung die Anzahl hängen — „Military (38)"."""
        return [(wert, '%s (%d)' % (text, zaehler.get(str(wert), 0)))
                for wert, text in eintraege]

    def _mit_katalog(self, fest, feld):
        """Die feste Liste, ergänzt um alles, was der Katalog sonst noch hat.

        So fehlt nichts, wenn ein Patch etwas Neues bringt — und nichts
        verschwindet, nur weil es gerade keinen Bauplan dazu gibt.
        """
        werte = list(fest)
        for wert in self._kat_werte(feld):
            if str(wert) not in werte:
                werte.append(str(wert))
        return werte

    def _klassen(self):
        return [(k, k) for k in self._mit_katalog(KLASSEN_FEST, 'c')]

    def _groessen(self):
        return [(s, t('ff_groesse') % s)
                for s in self._mit_katalog(GROESSEN_FEST, 's')]

    # (Grad und Größe kommen aus `_mit_katalog`; welche Baupläne dahinter zählen,
    #  entscheidet `_feld_zaehlt` — siehe oben.)

    def _grade(self):
        return [(g, t('ff_grad') % GRAD_BUCHSTABE.get(int(g), g).upper()
                 if g.isdigit() else g)
                for g in self._mit_katalog(GRADE_FEST, 'g')]

    def _quellen(self):
        """Fraktionen und Sonderquellen — beides, wonach man wirklich sucht."""
        fraktionen, sonder = set(), set()
        for e in (self.katalog.get('bauplaene') or {}).values():
            for q in e.get('q') or []:
                if q.get('fraktion'):
                    fraktionen.add(q['fraktion'])
            if e.get('topf'):
                sonder.add(e['topf'])
        eintraege = [('f:' + f, f) for f in sorted(fraktionen, key=str.lower)]
        eintraege += [('t:' + s, s) for s in sorted(sonder, key=str.lower)]
        return eintraege

    def _treffer_zeigen(self, gruppen):
        """Rechts die Zahl, links „zurücksetzen" — beides nur, wenn es zählt.

        Die Zahl beantwortet die Frage, die sich sonst nur durch Scrollen klärt:
        Habe ich gerade alles vor mir oder einen Ausschnitt? Und „zurücksetzen"
        erscheint erst, wenn wirklich etwas gesetzt ist — ein Knopf, der nichts
        tut, ist schlimmer als keiner.
        """
        if not hasattr(self, 'treffer_lbl'):
            return
        gezeigt = sum(len(treffer) for _, treffer in gruppen)
        gesamt = len(self.katalog.get('bauplaene') or {})
        eng = bool(self.suche.get().strip()) or self.filter != 'alle' \
            or any(self.fein.values())
        self.treffer_lbl.configure(
            text=(t('ff_treffer') % (gezeigt, gesamt)) if eng
            else (t('ff_alle_treffer') % gesamt))

        if any(self.fein.values()):
            self.zuruecksetzen_lbl.pack(side='left', padx=(4, 0))
        else:
            self.zuruecksetzen_lbl.pack_forget()

    def _fein_passt(self, e):
        """Kommt dieser Bauplan durch die fünf Auswahlfelder?

        Ein leeres Feld heißt „alle" und lässt alles durch. Die Quelle prüft
        zwei Dinge: `f:` eine Fraktion, die den Bauplan auslobt, `t:` einen
        Belohnungstopf (XenoThreat und Verwandte).
        """
        if self.fein['klasse'] and e.get('c') != self.fein['klasse']:
            return False
        # ⚠ Wer nach „Größe 2" oder „Grad A" sucht, meint Schiffsteile. Arten, bei
        # denen die Zahl nur der Vollständigkeit halber dasteht (Rüstung, FPS-Waffen),
        # fallen deshalb heraus, statt das Ergebnis zu fluten.
        if self.fein['groesse']:
            if not self._feld_zaehlt(e, 's') or str(e.get('s')) != self.fein['groesse']:
                return False
        if self.fein['grad']:
            if not self._feld_zaehlt(e, 'g') or str(e.get('g')) != self.fein['grad']:
                return False
        quelle = self.fein['quelle']
        if quelle:
            if quelle.startswith('f:'):
                gesucht = quelle[2:]
                if not any((q.get('fraktion') or '') == gesucht
                           for q in e.get('q') or []):
                    return False
            elif quelle.startswith('t:'):
                if (e.get('topf') or '') != quelle[2:]:
                    return False
        return True

    def _fein_setzen(self, schluessel, wert):
        self.fein[schluessel] = wert
        self.alle_zeigen = False
        self._zeichnen(nach_oben=True)

    def _fein_leeren(self):
        """Alle Auswahlfelder zurück auf „alle" — und EINMAL neu zeichnen.

        ⚠ `setzen()` der Felder ruft den Rückruf mit auf. Fünf Felder
        nacheinander zurückzustellen hieße fünfmal die ganze Liste neu bauen;
        deshalb wird stumm gesetzt und am Ende einmal gezeichnet.
        """
        for schluessel in self.fein:
            self.fein[schluessel] = ''
        for feld in self.fein_felder.values():
            feld.stumm_setzen('')
        self.alle_zeigen = False
        self._zeichnen(nach_oben=True)

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

    def _herkunftsbereich(self):
        """Der feste Block unter der Liste — Herkunft des gewählten Bauplans.

        ⚠ Muss **vor** der Liste gepackt werden. In tkinter bekommt das zuletzt
        gepackte Element mit `expand=True` den Rest des Platzes; käme dieser
        Block danach, schöbe die Liste ihn aus dem Fenster. Steht so auch in
        der CLAUDE.md des Projekts — und ist dort schon zweimal passiert.

        Warum überhaupt fest: Vorher klappte die Herkunft in der Zeile auf. Ein
        Bauplan hat bis zu zwölf Bezugsquellen, der Block wurde über 700 Pixel
        hoch, sichtbar sind 465 — er schob die ganze Liste weg, und man wusste
        nicht mehr, wo man war. Genau so gemeldet: „dann gehen alle Orte auf …
        ich kann nichts mehr bedienen."
        """
        self.herkunft_rahmen = tk.Frame(self.root, bg=BG)
        self.herkunft_rahmen.pack(side='bottom', fill='x', padx=14,
                                  pady=(0, 10))
        self.gewaehlt = None
        self._herkunft_zeichnen()

    def _liste(self):
        # Anfangswerte für den Blockmodus. Müssen stehen, **bevor** die Leinwand
        # existiert: Ihr `yscrollcommand` feuert schon beim ersten Zeichnen.
        self._blockteile = {}
        self._reihen = []
        self._block_start, self._block_y, self._block_h = [], [], []
        self._gesamthoehe = 0
        self._pflege_laeuft = False

        rahmen = tk.Frame(self.root, bg=BG)
        rahmen.pack(fill='both', expand=True, padx=14, pady=(0, 10))
        self.leinwand = tk.Canvas(rahmen, bg=BG, highlightthickness=0)
        from .hauptfenster import rundleiste
        rolle = rundleiste(rahmen, self.leinwand, grund=BG)
        self.inhalt = tk.Frame(self.leinwand, bg=BG)
        self.inhalt.bind('<Configure>', lambda e: self._rollbereich_anmelden())
        self.fenster = self.leinwand.create_window((0, 0), window=self.inhalt,
                                                   anchor='nw')
        self.leinwand.bind('<Configure>', lambda e: self._leinwand_breit(e.width))
        # ⚠ Zwischen Leinwand und Rollleiste gehängt: Beim Rollen müssen im
        # Blockmodus die Blöcke nachgezogen werden, die neu ins Bild kommen.
        def gerollt(anfang, ende):
            rolle.set(anfang, ende)
            self._bloecke_pflegen()

        self.leinwand.configure(yscrollcommand=gerollt)
        self.leinwand.pack(side='left', fill='both', expand=True)
        rolle.pack(side='right', fill='y')
        # ⚠ Hier stand `bind_all` OHNE `add='+'`. Das ersetzt jede vorher
        # gesetzte Bindung im ganzen Fenster — und weil diese Liste die
        # Startseite ist, war die Bindung aller anderen Seiten sofort wieder
        # weg. Danach rollte das Rad überall nur noch diese Liste, auch wenn
        # sie gar nicht zu sehen war.
        from .hauptfenster import rad_anschliessen
        rad_anschliessen(self.leinwand)

    def _leinwand_breit(self, breite):
        """Der Inhalt ist so breit wie die Leinwand — im Blockmodus auch die Blöcke."""
        try:
            self.leinwand.itemconfigure(self.fenster, width=breite)
            for wid, _rahmen in getattr(self, '_blockteile', {}).values():
                self.leinwand.itemconfigure(wid, width=breite)
        except tk.TclError:
            pass

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
            # Die Art ist ein Merkmal der ganzen Gruppe — einmal prüfen reicht,
            # statt für jede der bis zu 87 Zeilen darin.
            if self.fein['art'] and (liste and katalog_modul.art_kennung(liste[0])
                                     != self.fein['art']):
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
                if not self._fein_passt(e):
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

        # (Hier standen die vier Bereichs-Knöpfe. Sie sind den fünf
        # Auswahlfeldern gewichen — die färben sich selbst, sobald etwas
        # gesetzt ist, und brauchen kein Nachziehen von außen.)
        self._loeschkreuz_zeigen()

        fehler.spur('Liste: zeichnen beginnt')
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

        # Zwei Wege, je nachdem wie lang die Liste wird:
        #
        # * **Kurz** (der Normalfall — beim Start 40 Zeilen, mit Suche oder Filter
        #   fast immer): alles in einen Rahmen packen. Erprobt und einfach.
        # * **Lang** („alle anzeigen" ohne Filter, über 700 Zeilen): in Blöcken,
        #   weil ein einzelner Rahmen sonst höher würde, als X11 Fenster
        #   platzieren kann — siehe „Lange Liste in Blöcken".
        gesamt_zeilen = sum(len(paare) for _, paare in gruppen)
        in_bloecken = self.alle_zeigen and gesamt_zeilen > self._zeilen_deckel()

        if in_bloecken:
            reihen = []
            for art, treffer in gruppen:
                reihen.append(('kopf', art, treffer))
                for eintrag, drin in treffer:
                    reihen.append(('zeile', eintrag, drin))
            self.root.after_idle(lambda r=reihen: self._bloecke_aufbauen(r))
            gezeichnet = gesamt_zeilen
        else:
            self._bloecke_abraeumen()
            deckel = self._zeilen_deckel() if self.alle_zeigen else ZEILEN_ZUERST
            gezeichnet = 0
            for art, treffer in gruppen:
                if gezeichnet >= deckel:
                    break
                self._gruppenkopf(art, treffer, habe)
                for eintrag, drin in treffer:
                    if gezeichnet >= deckel:
                        break
                    self._zeile(eintrag, drin)
                    gezeichnet += 1

            rest = gesamt_zeilen - gezeichnet
            if rest > 0:
                mehr = tk.Label(self.inhalt, text=t('weitere_anzeigen', rest),
                                bg=BG, fg=ACCENT, font=schrift(10),
                                cursor='hand2', pady=10)
                mehr.pack(fill='x')
                mehr.bind('<Button-1>', lambda e: self._alle())
        self._treffer_zeigen(gruppen)
        if not gruppen:
            leer = (t('merkliste_leer') if self.filter == 'merk'
                    else t('nichts_gefunden'))
            tk.Label(self.inhalt, text=leer, bg=BG, fg=SUB, font=schrift(11),
                     pady=20, wraplength=520, justify='center').pack()

        # Die Zeilenhöhe einmal nachmessen — sie bestimmt, wie viele Zeilen in eine
        # Ansicht passen (siehe `_zeilen_deckel`).
        if not getattr(self, '_zeilenhoehe', 0):
            self.root.after_idle(self._zeilenhoehe_merken)

        if nach_oben:
            # Erst wenn Tk die neue Höhe kennt — sonst bezieht sich der Sprung
            # noch auf die Scrollfläche von vorher und landet daneben.
            self.root.after_idle(lambda: self.leinwand.yview_moveto(0))
        elif oben_px is not None:
            # ⚠ ZWEIMAL `after_idle`, und drinnen KEIN `update_idletasks()`.
            # Der erste Durchgang packt die Zeilen, der zweite läuft, wenn Tk
            # sie vermessen hat — dann stimmt `bbox('all')` von selbst.
            #
            # Mit `update_idletasks()` innerhalb des Idle-Handlers dauerte das
            # Zeichnen **29,6 Sekunden** statt einem Sechstel davon: Der Aufruf
            # arbeitet mitten im Zeichnen alle offenen Aufgaben ab und stößt
            # bei 120 Zeilen eine Kaskade an. Gemessen mit cProfile — 29,4 der
            # 29,6 Sekunden steckten in dieser einen Zeile.
            self.root.after_idle(
                lambda: self.root.after_idle(lambda: self._zurueck_zu(oben_px)))

    def _rollbereich_anmelden(self):
        """Die Scrollfläche neu vermessen — aber höchstens einmal je Runde.

        ⚠ Hier lag der Grund, warum die Liste **30 Sekunden** zum Aufbau
        brauchte. Vorher hing am `<Configure>` des Inhalts direkt ein
        `bbox('all')`. Jedes gepackte Widget löst so ein Ereignis aus, und
        `bbox('all')` läuft über **alle** bisherigen — bei 801 Widgets in der
        Liste wird daraus quadratischer Aufwand.

        Gemessen mit dem echten Katalog (722 Baupläne, 400 im Bestand):
        30,0 s vorher. Mit 13 Testbauplänen fiel das nie auf — der Fehler war
        also schon lange da und wurde erst mit echten Daten sichtbar.

        Jetzt wird nur gemerkt, dass etwas zu tun ist, und einmal im Leerlauf
        gerechnet. Hundert Ereignisse ergeben eine Messung.
        """
        if getattr(self, '_rollbereich_faellig', False):
            return
        self._rollbereich_faellig = True

        def rechnen():
            self._rollbereich_faellig = False
            # ⚠ Im Blockmodus NICHT aus `bbox('all')` rechnen: Dort liegen immer
            # nur die Blöcke in der Nähe des Ausschnitts in der Leinwand, die
            # Hülle wäre also viel zu klein und das Rollen bräche zusammen.
            # Dort gilt die vorher gerechnete Gesamthöhe.
            if getattr(self, '_block_start', None):
                return
            try:
                self.leinwand.configure(scrollregion=self.leinwand.bbox('all'))
            except tk.TclError:
                pass

        self.root.after_idle(rechnen)

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
            if getattr(self, '_block_start', None):
                gesamt = float(self._gesamthoehe)
            else:
                bereich = self.leinwand.bbox('all')
                gesamt = float(bereich[3]) if bereich else 0.0
            if gesamt > 1:
                self.leinwand.yview_moveto(max(0.0, min(1.0, oben_px / gesamt)))
        except tk.TclError:
            pass

    def _alle(self):
        self.alle_zeigen = True
        self._zeichnen()

    # ------------------------------------------------- Lange Liste in Blöcken
    #
    # Warum das nötig ist: X11 kann kein Fenster jenseits von 32767 Pixeln
    # platzieren (16-Bit-Koordinaten). Alle 722 Baupläne in **einen** Rahmen zu
    # packen ergibt bei üblicher Schrift gut 33000 Pixel — die letzten Zeilen
    # überlagerten sich. Ein Deckel wäre die einfache Antwort, kostet aber genau
    # das, wofür die Liste da ist.
    #
    # Die Lösung: Die Reihen werden in Blöcke zu je `BLOCK_REIHEN` aufgeteilt.
    # Jeder Block ist ein eigener Rahmen in der Leinwand, und **nur die Blöcke in
    # der Nähe des sichtbaren Ausschnitts liegen wirklich dort**. Was weit weg
    # ist, wird abgeräumt und beim Zurückrollen neu gebaut. Damit bleibt jede
    # Fensterkoordinate klein, egal wie lang die Liste wird.
    #
    # Die Höhen werden **vorher** gerechnet, nicht nachträglich gemessen: Nur so
    # steht jede Position von Anfang an fest und nichts springt beim Rollen.
    # Gemessen wird einmal, wie hoch ein Gruppenkopf und eine Zeile sind (mit und
    # ohne zweite Zeile darunter) — der Rest ist Rechnen.

    def _reihenhoehen_messen(self):
        """Einmal nachsehen, wie hoch Kopf und Zeilen wirklich sind.

        Die Werte hängen an Schriftgröße und Anzeige-Skalierung; raten geht
        schief. Gemessen wird an unsichtbaren Probestücken, damit nichts blinkt.
        """
        if getattr(self, '_hoehen', None):
            return self._hoehen
        probe = tk.Frame(self.leinwand, bg=BG)
        beispiel = {'n': 'Xxxxxxxxxxxxxxxx', 'q': None}
        self._gruppenkopf('PROBE', [(beispiel, False)], set(), eltern=probe)
        self._zeile(beispiel, False, eltern=probe)
        mit_zusatz = dict(beispiel)
        mit_zusatz['m'] = 'Probe'
        self._zeile(mit_zusatz, False, eltern=probe)
        probe.update_idletasks()
        kinder = probe.winfo_children()
        hoehen = [k.winfo_reqheight() + 2 for k in kinder]   # +2 für das pady
        probe.destroy()
        if len(hoehen) < 3 or min(hoehen) < 4:
            self._hoehen = (34, 45, 58)         # Notnagel, falls nichts messbar
        else:
            self._hoehen = (hoehen[0] + 16, hoehen[1], hoehen[2])
        return self._hoehen

    def _reihenhoehe(self, reihe):
        kopf_h, zeile_h, zeile_zusatz_h = self._reihenhoehen_messen()
        if reihe[0] == 'kopf':
            return kopf_h
        eintrag = reihe[1]
        hat_zusatz = bool(kuerzel(eintrag) or eintrag.get('m'))
        return zeile_zusatz_h if hat_zusatz else zeile_h

    def _bloecke_aufbauen(self, reihen):
        """Das Gerüst anlegen: Wo liegt welcher Block, und wie hoch ist alles."""
        self._bloecke_abraeumen()
        self._reihen = reihen
        self._block_start = list(range(0, len(reihen), BLOCK_REIHEN))
        self._block_y, self._block_h = [], []
        y = 0
        for start in self._block_start:
            hoch = sum(self._reihenhoehe(r)
                       for r in reihen[start:start + BLOCK_REIHEN])
            self._block_y.append(y)
            self._block_h.append(hoch)
            y += hoch
        self._gesamthoehe = y
        breite = max(1, self.leinwand.winfo_width())
        self.leinwand.configure(scrollregion=(0, 0, breite, y))
        self._bloecke_pflegen()

    def _bloecke_abraeumen(self):
        """Alle Blöcke aus der Leinwand nehmen — beim Neuzeichnen der Liste."""
        for wid, rahmen in getattr(self, '_blockteile', {}).values():
            try:
                self.leinwand.delete(wid)
                rahmen.destroy()
            except tk.TclError:
                pass
        self._blockteile = {}
        self._reihen = []
        self._block_start, self._block_y, self._block_h = [], [], []
        self._gesamthoehe = 0

    def _block_bauen(self, nummer):
        start = self._block_start[nummer]
        rahmen = tk.Frame(self.leinwand, bg=BG)
        habe = bestand_datei.schluessel(self.bestand)
        for reihe in self._reihen[start:start + BLOCK_REIHEN]:
            if reihe[0] == 'kopf':
                self._gruppenkopf(reihe[1], reihe[2], habe, eltern=rahmen)
            else:
                self._zeile(reihe[1], reihe[2], eltern=rahmen)
        breite = max(1, self.leinwand.winfo_width())
        wid = self.leinwand.create_window((0, self._block_y[nummer]),
                                          window=rahmen, anchor='nw',
                                          width=breite)
        self._blockteile[nummer] = (wid, rahmen)

    def _bloecke_pflegen(self, *_):
        """Blöcke im Sichtfeld bauen, weit entfernte wieder abräumen."""
        if not self._block_start or getattr(self, '_pflege_laeuft', False):
            return
        self._pflege_laeuft = True
        try:
            oben = self.leinwand.canvasy(0)
            unten = oben + max(1, self.leinwand.winfo_height())
            # Ein Block Vorlauf nach oben und unten: So ist beim Rollen schon
            # gezeichnet, was gleich ins Bild kommt.
            rand = max(self._block_h) if self._block_h else 0
            gebraucht = set()
            for nummer, y in enumerate(self._block_y):
                if y + self._block_h[nummer] >= oben - rand and y <= unten + rand:
                    gebraucht.add(nummer)
            for nummer in list(self._blockteile):
                if nummer not in gebraucht:
                    wid, rahmen = self._blockteile.pop(nummer)
                    try:
                        self.leinwand.delete(wid)
                        rahmen.destroy()
                    except tk.TclError:
                        pass
            for nummer in sorted(gebraucht):
                if nummer not in self._blockteile:
                    self._block_bauen(nummer)
        except tk.TclError:
            pass
        finally:
            self._pflege_laeuft = False

    def _zeilen_deckel(self):
        """Wie viele Zeilen in eine Ansicht passen, ohne dass X11 aussteigt.

        Gerechnet wird aus der **gemessenen** Höhe einer echten Zeile: Sie hängt
        an Schriftgröße und Anzeige-Skalierung, ist also auf keinem Rechner gleich.
        Solange noch nichts gemessen wurde, gilt ein vorsichtiger Wert — er wird
        beim ersten Zeichnen sofort durch die echte Zahl ersetzt.
        """
        hoehe = getattr(self, '_zeilenhoehe', 0)
        if not hoehe:
            return 650
        return max(ZEILEN_ZUERST, int(HOECHSTE_INHALTSHOEHE / hoehe))

    def _zeilenhoehe_merken(self):
        """Die Höhe einer Zeile einmal nachmessen, wenn Tk sie gezeichnet hat."""
        try:
            kinder = [k for k in self.inhalt.winfo_children()
                      if k.winfo_height() > 1]
            if len(kinder) >= 4:
                # Der zweite bis vierte Eintrag: der erste ist ein Gruppenkopf
                # und niedriger als eine Bauplan-Zeile.
                hoehen = sorted(k.winfo_height() for k in kinder[1:4])
                self._zeilenhoehe = hoehen[len(hoehen) // 2]
        except tk.TclError:
            pass

    def _hinweis_kein_katalog(self):
        tk.Label(self.inhalt, text=t('kein_katalog'),
                 bg=BG, fg=FG, font=schrift(11), pady=14).pack()
        tk.Label(self.inhalt, bg=BG, fg=SUB, font=schrift(10), justify='left',
                 text=t('kein_katalog_hilfe')).pack()

    def _gruppenkopf(self, art, treffer, habe, eltern=None):
        drin = sum(1 for _, d in treffer if d)
        kopf = tk.Frame(eltern if eltern is not None else self.inhalt, bg=BG)
        kopf.pack(fill='x', pady=(14, 4))
        tk.Label(kopf, text=art.upper(), bg=BG, fg=ACCENT, font=schrift(9, True),
                 anchor='w').pack(side='left')
        tk.Label(kopf, text='  %d/%d' % (drin, len(treffer)), bg=BG, fg=SUB,
                 font=schrift(9), anchor='w').pack(side='left')

    def _zeile(self, eintrag, drin, eltern=None):
        name = eintrag['n']
        zeile = tk.Frame(eltern if eltern is not None else self.inhalt,
                         bg=FLAECHE)
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


    def _herkunft_zeichnen(self):
        """Den festen Block neu füllen — für den gerade gewählten Bauplan."""
        for kind in self.herkunft_rahmen.winfo_children():
            kind.destroy()

        eintrag = self._gewaehlter_eintrag()
        if eintrag is None:
            # Ohne Auswahl nur eine Zeile, damit die Liste den Platz behält.
            tk.Label(self.herkunft_rahmen, text=t('hk_nichts'), bg=BG, fg=SUB,
                     font=schrift(10), anchor='w').pack(fill='x', pady=(6, 2))
            return

        # ⚠ `marke` misst die Textbreite und braucht deshalb ein Font-Objekt.
        # Dieses Fenster reicht Schriften als Tupel weiter — `_als_schrift`
        # wandelt um, sonst gibt es „'tuple' object has no attribute 'metrics'".
        from .hauptfenster import marke as blase, rundrahmen, _als_schrift
        quellen = list(eintrag.get('q') or [])
        farbe = ACCENT if quellen else GELB
        kasten = rundrahmen(self.herkunft_rahmen, FLAECHE, farbe, radius=8,
                            grundfarbe=BG)
        kasten.halter.pack(fill='x')

        kopf = tk.Frame(kasten, bg=FLAECHE)
        kopf.pack(fill='x', padx=14, pady=(10, 2))
        tk.Label(kopf, text=eintrag['n'], bg=FLAECHE, fg=FG, font=schrift(12, True),
                 anchor='w').pack(side='left')
        zu = tk.Label(kopf, text='✕', bg=FLAECHE, fg=SUB, font=schrift(11),
                      cursor='hand2', padx=6)
        zu.pack(side='right')
        zu.bind('<Button-1>', lambda e: self._auswaehlen(None))
        hinweis.anhaengen(zu, lambda: t('hk_zu'))
        if quellen:
            blase(kopf, t('hk_ein_weg') if len(quellen) == 1
                  else t('hk_wege') % len(quellen),
                  ACCENT, _als_schrift(schrift(9))).pack(side='right',
                                                        padx=8)

        # Unterzeile: Art, Klasse, Besitz — und der Hinweis auf die Sortierung.
        teile = [katalog_modul.art_lesbar(eintrag.get('a'))]
        if eintrag.get('c'):
            teile.append(eintrag['c'])
        teile.append(t('hk_hast_du')
                     if bestand_datei.enthaelt(self.bestand, eintrag['n'])
                     else t('hk_fehlt_dir'))
        if len(quellen) > 1:
            teile.append(t('hk_leichtester'))
        tk.Label(kasten, text=' · '.join(teile), bg=FLAECHE, fg=SUB,
                 font=schrift(9), anchor='w').pack(fill='x', padx=14,
                                                   pady=(0, 8))

        if not quellen:
            if eintrag.get('start'):
                text = t('hk_start')
            elif eintrag.get('topf'):
                text = '%s: %s\n%s' % (t('hk_topf'), eintrag['topf'],
                                       t('hk_topf_text'))
            else:
                text = t('hk_keine')
            tk.Label(kasten, text=text, bg=FLAECHE, fg=SUB, font=schrift(10),
                     anchor='w', justify='left', wraplength=620).pack(
                         fill='x', padx=14, pady=(0, 12))
            return

        # Der einfachste Weg steht ausgeschrieben da — den braucht man zuerst.
        self._weg_zeigen(kasten, quellen[0])

        if len(quellen) > 1:
            self._weitere_wege(kasten, quellen[1:])

    def _gewaehlter_eintrag(self):
        """Der Katalogeintrag zum gewählten Namen — oder nichts."""
        if not getattr(self, 'gewaehlt', None):
            return None
        schluessel = katalog_modul._norm(self.gewaehlt)
        return (self.katalog.get('bauplaene') or {}).get(schluessel)

    def _weg_zeigen(self, eltern, q):
        """Eine Bezugsquelle als beschriftete Zeilen — Auftrag, Fraktion, …"""
        gitter = tk.Frame(eltern, bg=FLAECHE)
        gitter.pack(fill='x', padx=14, pady=(0, 10))
        gitter.columnconfigure(1, weight=1)

        rang = q.get('rang') or '—'
        if q.get('rep'):
            rang += '  (%s)' % t('ruf_punkte',
                                 f"{q['rep']:,}".replace(',', '.'))
        zeilen = ((t('hk_auftrag'), q.get('auftrag') or '—'),
                  (t('hk_fraktion'), q.get('fraktion') or '—'),
                  (t('hk_annahme'), ort_text(q.get('wo')) or '—'),
                  (t('hk_rang'), rang),
                  (t('hk_belohnung'),
                   ('%s aUEC' % f"{q['uec']:,}".replace(',', '.'))
                   if q.get('uec') else '—'))
        for nummer, (bez, wert) in enumerate(zeilen):
            tk.Label(gitter, text=bez, bg=FLAECHE, fg=SUB, font=schrift(9),
                     anchor='w').grid(row=nummer, column=0, sticky='w',
                                      padx=(0, 14), pady=1)
            tk.Label(gitter, text=wert, bg=FLAECHE, fg=FG, font=schrift(10),
                     anchor='w', justify='left', wraplength=520).grid(
                         row=nummer, column=1, sticky='w', pady=1)

    def _weitere_wege(self, eltern, weitere):
        """Die übrigen Wege — eingeklappt, damit sie den Block nicht sprengen."""
        rahmen = tk.Frame(eltern, bg=FLAECHE)
        rahmen.pack(fill='x', padx=14, pady=(0, 10))
        tk.Frame(rahmen, bg=LINIE, height=1).pack(fill='x', pady=(0, 8))

        kopf = tk.Label(rahmen, text='▶  ' + t('hk_weitere') % len(weitere),
                        bg=FLAECHE, fg=SUB, font=schrift(10), cursor='hand2',
                        anchor='w')
        kopf.pack(fill='x')
        inhalt = tk.Frame(rahmen, bg=FLAECHE)

        def umschalten(_=None):
            if inhalt.winfo_ismapped():
                inhalt.pack_forget()
                kopf.configure(text='▶  ' + t('hk_weitere') % len(weitere))
            else:
                inhalt.pack(fill='x', pady=(8, 0))
                kopf.configure(text='▼  ' + t('hk_weitere') % len(weitere))

        kopf.bind('<Button-1>', umschalten)
        for q in weitere:
            kopf_text, auftrag, unten, wo = quelle_text(q)
            zeile = tk.Frame(inhalt, bg=FLAECHE)
            zeile.pack(fill='x', pady=3)
            tk.Label(zeile, text=kopf_text, bg=FLAECHE, fg=GELB,
                     font=schrift(9), anchor='w').pack(fill='x')
            if auftrag:
                tk.Label(zeile, text='„%s"' % auftrag, bg=FLAECHE, fg=FG,
                         font=schrift(9), anchor='w', wraplength=600,
                         justify='left').pack(fill='x')
            rest = ' · '.join(x for x in (unten, wo) if x)
            if rest:
                tk.Label(zeile, text=rest, bg=FLAECHE, fg=SUB, font=schrift(9),
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
        """Bauplan wählen — die Herkunft erscheint im festen Block unten.

        ⚠ Hier wird die Liste **nicht** neu gebaut. Vorher tat sie das, weil
        der Herkunftsblock zwischen den Zeilen stand: Jeder Klick baute 700
        Zeilen neu auf, die Ansicht sprang, und der aufgeklappte Block schob
        alles weg. Jetzt ändert sich nur der Block unten — die Liste bleibt
        stehen, wo sie steht.
        """
        self._auswaehlen(None if name == getattr(self, 'gewaehlt', None)
                         else name)

    def _auswaehlen(self, name):
        self.gewaehlt = name
        self._herkunft_zeichnen()

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
