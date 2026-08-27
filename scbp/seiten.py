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
Was in den einzelnen Reitern des Hauptfensters steht.

Getrennt von `hauptfenster.py`, weil das zwei verschiedene Fragen sind: Dort
geht es um den **Rahmen** (Reiterleiste, Umschalten, Größe), hier um den
**Inhalt**. So bleibt jede Datei überschaubar, und eine neue Seite ist eine
Funktion, kein Eingriff in den Rahmen.

Die großen Seiten leihen sich die vorhandenen Fenster: `bestandsfenster` und
`einstellungsfenster` können seit v3.0.0 auch in einen übergebenen Rahmen
zeichnen, statt ein eigenes Fenster aufzumachen.
"""
import os
import sys
import tkinter as tk

from . import bericht, bestand as bestand_datei, fehler, katalog as katalog_modul
from . import zeichen
from .sprache import t

BG      = '#10141c'
FLAECHE = '#161c28'
BAR     = '#1b2230'
FG      = '#e6edf3'
SUB     = '#8b98a5'
ACCENT  = '#9ce430'
LINIE   = '#232c3d'
GOLD    = '#e8c353'
ROT     = '#e05252'


def bauen(fenster, kennung, rahmen):
    """Eine Seite füllen. `fenster` ist das Hauptfenster (Schriften, Meldungen)."""
    bauer = {
        'liste':       _liste,
        'fortschritt': _fortschritt,
        'allgemein':   _allgemein,
        'anzeige':     _anzeige,
        'ordner':      _ordner,
        'spiel':       _spiel,
        'bestand':     _bestand,
        'wasistneu':   _wasistneu,
        'ueber':       _ueber,
        'serverstatus': _serverstatus,
        'danke':       _danke,
        'erkennung':   _erkennung,
        'diagnose':    _diagnose,
    }.get(kennung)
    if bauer:
        bauer(fenster, rahmen)


# ------------------------------------------------------------------ Bausteine
def _ueberschrift(fenster, rahmen, titel, lead=''):
    tk.Label(rahmen, text=titel, bg=BG, fg=FG, font=fenster.f_titel,
             anchor='w').pack(fill='x', padx=24, pady=(20, 2))
    if lead:
        # `abzug=48` sind die beiden Ränder von je 24 — ohne sie rechnet der
        # Umbruch mit Platz, den es nicht gibt, und die letzten Wörter fallen
        # trotzdem heraus.
        einleitung = tk.Label(rahmen, text=lead, bg=BG, fg=SUB,
                              font=fenster.f_klein, anchor='w', justify='left')
        einleitung.pack(fill='x', padx=24, pady=(0, 14))
        _umbruch(einleitung, abzug=48)


def _rollflaeche(rahmen, rand=24):
    """Ein Bereich, der rollt. Leinwand + Balken, wie im Einstellungsfenster.

    ⚠ Die Fläche wird **zuletzt** gepackt und bekommt `expand=True` — alles,
    was fest bleiben soll, muss vorher gepackt sein.

    `rand` rückt den Inhalt ein. Das gehört hierher und nicht in jeden Baustein:
    Die Bausteine stammen aus dem alten Einstellungsfenster und packen sich ohne
    Rand — neben eingerückten Überschriften sahen sie aus, als wären sie
    verrutscht.
    """
    aussen = tk.Frame(rahmen, bg=BG)
    aussen.pack(fill='both', expand=True)
    leinwand = tk.Canvas(aussen, bg=BG, highlightthickness=0)
    from .hauptfenster import rundleiste
    balken = rundleiste(aussen, leinwand, grund=BG)
    innen = tk.Frame(leinwand, bg=BG)
    innen.bind('<Configure>',
               lambda e: leinwand.configure(scrollregion=leinwand.bbox('all')))
    fenster_id = leinwand.create_window((0, 0), window=innen, anchor='nw')
    leinwand.bind('<Configure>',
                  lambda e: leinwand.itemconfigure(fenster_id, width=e.width))
    leinwand.configure(yscrollcommand=balken.set)
    balken.pack(side='right', fill='y')
    leinwand.pack(side='left', fill='both', expand=True)

    if rand:
        polster = tk.Frame(innen, bg=BG)
        polster.pack(fill='both', expand=True, padx=rand)
        innen_ziel = polster
    else:
        innen_ziel = innen

    from .hauptfenster import rad_anschliessen
    rad_anschliessen(leinwand)
    return innen_ziel


def _knopf(fenster, eltern, text, tat, stark=False, gefahr=False):
    """Ein Knopf im Stil der Vorschau — Rand, Farbe beim Überfahren."""
    from .hauptfenster import _rundes_rechteck
    schrift = fenster.f_klein
    hoehe = schrift.metrics('linespace') + 16
    breite = schrift.measure(text) + 30
    farbe = ACCENT if stark else FG
    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=BG,
                  highlightthickness=0, bd=0, cursor='hand2')
    flaeche = _rundes_rechteck(c, 1, 1, breite - 1, hoehe - 1, radius=5,
                               fill='#1d2a14' if stark else FLAECHE,
                               outline=ACCENT if stark else LINIE, width=1)
    beschriftung = c.create_text(breite / 2.0, hoehe / 2.0, text=text,
                                 fill=farbe, font=schrift, anchor='center')

    def rein(_=None):
        c.itemconfigure(flaeche, outline=ROT if gefahr else ACCENT)
        c.itemconfigure(beschriftung, fill=ROT if gefahr else ACCENT)

    def raus(_=None):
        c.itemconfigure(flaeche, outline=ACCENT if stark else LINIE)
        c.itemconfigure(beschriftung, fill=farbe)

    def mitwachsen(_=None):
        """Wird der Knopf gestreckt, muss das gezeichnete Rechteck mit.

        ⚠ Ein Canvas hat eine feste Wunschbreite. `pack(fill='x')` streckt zwar
        die Leinwand, aber das darauf gezeichnete Rechteck bleibt schmal — der
        Knopf sah dann aus, als füllte er nur die halbe Kastenbreite. Genau so
        am 26.08.2026 gemeldet: „der Button füllt nur die hälfte unter den
        versionen".

        Deshalb bei jeder Größenänderung Rechteck und Text neu setzen. Knöpfe,
        die nicht gestreckt werden, behalten ihre Breite von selbst.
        """
        neue_breite = c.winfo_width()
        if neue_breite <= 10 or abs(neue_breite - breite) < 2:
            return
        punkte = _rundes_rechteck(c, 1, 1, neue_breite - 1, hoehe - 1,
                                  radius=5, fill='', outline='')
        c.coords(flaeche, *c.coords(punkte))
        c.delete(punkte)
        c.coords(beschriftung, neue_breite / 2.0, hoehe / 2.0)

    c.bind('<Configure>', mitwachsen, add='+')
    c.bind('<Enter>', rein)
    c.bind('<Leave>', raus)
    c.bind('<Button-1>', lambda e: tat())
    c.ist_knopf = True          # damit tools/randpruefung.py ihn prüft
    return c


def _wahl(fenster, eltern, eintraege, aktiv, tat):
    """Mehrere Möglichkeiten nebeneinander — die gewählte trägt den Akzentrand."""
    from .hauptfenster import _rundes_rechteck
    reihe = tk.Frame(eltern, bg=BG)
    knoepfe = {}
    schrift = fenster.f_klein
    for kennung, text in eintraege:
        an = (kennung == aktiv)
        hoehe = schrift.metrics('linespace') + 14
        breite = schrift.measure(text) + 26
        c = tk.Canvas(reihe, width=breite, height=hoehe, bg=BG,
                      highlightthickness=0, bd=0, cursor='hand2')
        c.pack(side='left', padx=(0, 6))
        flaeche = _rundes_rechteck(c, 1, 1, breite - 1, hoehe - 1, radius=5,
                                   fill=FLAECHE, outline=ACCENT if an else LINIE,
                                   width=1)
        beschr = c.create_text(breite / 2.0, hoehe / 2.0, text=text,
                               fill=ACCENT if an else SUB, font=schrift)
        c.teile = (flaeche, beschr)
        c.bind('<Button-1>', lambda e, k=kennung: tat(k))
        c.ist_knopf = True      # damit tools/randpruefung.py ihn prüft
        knoepfe[kennung] = c

    def setzen(gewaehlt):
        for kennung, c in knoepfe.items():
            an = (kennung == gewaehlt)
            flaeche, beschr = c.teile
            c.itemconfigure(flaeche, outline=ACCENT if an else LINIE)
            c.itemconfigure(beschr, fill=ACCENT if an else SUB)

    reihe.setzen = setzen
    return reihe


def _status(fenster, eltern, symbol, fett, rest, farbe=None):
    """Ein Statuskasten mit farbigem Balken links — wie in der Vorschau.

    ⚠ `symbol` ist ein Name aus `scbp/zeichen.py` („haken", „offen"), kein
    Schriftzeichen mehr. Der Parameter hieß bis v3.0.0-rc55 `zeichen` und hätte
    das gleichnamige Modul verdeckt.
    """
    farbe = farbe or ACCENT
    innen = _karte(eltern, rand=farbe, pady=(0, 14))
    zeile = tk.Frame(innen, bg=FLAECHE)
    zeile.pack(fill='x', padx=14, pady=12)
    zeichen.zeile(zeile, symbol, grund=FLAECHE, schrift=fenster.f_grund,
                  farbe=zeichen.GRAU if farbe == SUB else zeichen.GRUEN
                  ).pack(side='left', padx=(0, 10), anchor='n')
    text = tk.Frame(zeile, bg=FLAECHE)
    text.pack(side='left', fill='x', expand=True)
    oben = tk.Label(text, text=fett, bg=FLAECHE, fg=FG, font=fenster.f_fett,
                    anchor='w', justify='left')
    oben.pack(fill='x')
    _umbruch(oben)
    if rest:
        unten = tk.Label(text, text=rest, bg=FLAECHE, fg=SUB,
                         font=fenster.f_klein, anchor='w', justify='left')
        unten.pack(fill='x')
        _umbruch(unten)
    return innen


def _pfadfeld(fenster, eltern, wert, waehlen, oeffnen=None, platzhalter=''):
    """Ein Pfad mit Knopf daneben."""
    reihe = tk.Frame(eltern, bg=BG)
    reihe.pack(fill='x', pady=(8, 0))
    from .hauptfenster import rundes_feld
    feld = rundes_feld(reihe, wert, fenster.f_klein, '#0c1017', LINIE, ACCENT, FG)
    feld.halter.pack(side='left', fill='x', expand=True, padx=(0, 8))
    if platzhalter and not wert.get():
        feld.configure(fg=SUB)
    _knopf(fenster, reihe, t('s_durchsuchen'), waehlen).pack(side='left')
    if oeffnen:
        _knopf(fenster, reihe, t('s_oeffnen'), oeffnen).pack(side='left', padx=(8, 0))
    return reihe



def _umbruch(label, anteil=1.0, abzug=0, bezug=None, neben=None):
    """Den Zeilenumbruch an die tatsächliche Breite hängen.

    ⚠ Feste Werte wie `wraplength=560` sind der Grund, warum Text bei kleinem
    Fenster abgeschnitten statt umgebrochen wurde: Sie stimmen genau für die
    eine Fenstergröße, bei der sie eingetragen wurden. Wer das Fenster auf die
    Mindestgröße zieht oder auf Englisch umstellt, sieht Stümpfe.

    `anteil` ist für nebeneinanderliegende Kästen (zwei Spalten → 0.5).

    `bezug` ist der Rahmen, an dem gemessen wird — normalerweise der eigene
    Elternrahmen. ⚠ Er taugt nicht immer: Steht rechts noch ein Bedienelement,
    hat der linke Rahmen bereits die **zu große** Breite, die den Überlauf
    überhaupt erst verursacht. Dann wird am gemeinsamen Elternrahmen gemessen.

    `neben` ist genau dieses Bedienelement. Seine gebrauchte Breite wird
    abgezogen, denn diesen Platz gibt es für den Text nicht.
    """
    ziel = bezug if bezug is not None else label.master

    def nachziehen(_=None):
        breite = ziel.winfo_width()
        if neben is not None:
            try:
                breite -= neben.winfo_reqwidth()
            except tk.TclError:
                pass
        if breite > 40:
            label.configure(wraplength=max(160, int(breite * anteil) - abzug))

    ziel.bind('<Configure>', nachziehen, add='+')
    # ⚠ `<Configure>` allein reicht nicht. Seiten werden gebaut, während sie
    # noch versteckt sind — dort meldet Tk Breite 1, und wenn beim späteren
    # Einblenden die Fenstergröße zufällig gleich bleibt, kommt nie ein
    # `<Configure>` mehr. Der Umbruch bliebe dann auf dem Notwert stehen.
    # `<Map>` feuert genau dann, wenn das Element wirklich sichtbar wird.
    label.bind('<Map>', nachziehen, add='+')
    label.after(0, nachziehen)
    return label


def _knopfreihe(eltern, knoepfe, abstand=8):
    """Knöpfe nebeneinander — und untereinander, sobald der Platz nicht reicht.

    ⚠ Tk bricht eine Knopfreihe nicht um. Passt sie nicht, schneidet es den
    letzten Knopf einfach ab: Auf der Über-Seite stand bei Mindestbreite
    sichtbar „Einrichtung wiederho…". Aufgefallen ist das erst auf einem
    Bildschirmfoto — die Randprüfung hatte Knöpfe als Rollflächen ausgenommen,
    weil jeder Knopf hier ein `Canvas` ist.
    """
    def ordnen(_=None):
        platz = eltern.winfo_width()
        gebraucht = sum(k.winfo_reqwidth() for k in knoepfe) \
            + abstand * (len(knoepfe) - 1)
        nebeneinander = platz <= 1 or gebraucht <= platz
        if nebeneinander == getattr(eltern, 'zuletzt_nebeneinander', None):
            return
        eltern.zuletzt_nebeneinander = nebeneinander
        for nummer, knopf in enumerate(knoepfe):
            knopf.pack_forget()
            if nebeneinander:
                knopf.pack(side='left', padx=(0 if nummer == 0 else abstand, 0))
            else:
                knopf.pack(side='top', anchor='w',
                           pady=(0 if nummer == 0 else 6, 0))

    eltern.bind('<Configure>', ordnen, add='+')
    eltern.after(0, ordnen)
    return eltern


def _fliesstext(eltern, text, schrift, farbe=SUB, grund=BG, abzug=0, **pack):
    """Ein Absatz, der mit dem Fenster mitgeht.

    Der Regelweg für jeden mehrzeiligen Text. Wer stattdessen `wraplength=600`
    schreibt, baut den Fehler wieder ein, den diese Funktion behebt: Der Wert
    passt für die eine Fenstergröße, bei der er entstanden ist.

    `abzug` ist der waagerechte Rand, den der Text nicht benutzen darf —
    üblicherweise das Doppelte des `padx` beim Packen.
    """
    label = tk.Label(eltern, text=text, bg=grund, fg=farbe, font=schrift,
                     anchor='w', justify='left')
    label.pack(**pack)
    return _umbruch(label, abzug=abzug)


def _feld(fenster, eltern, bezeichnung, hilfe, breit=False):
    """Eine Einstellungszeile: Bezeichnung, Erklärung, Platz für das Bedienelement."""
    zeile = tk.Frame(eltern, bg=BG)
    zeile.pack(fill='x', pady=(12, 0))
    links = tk.Frame(zeile, bg=BG)
    links.pack(side='left', fill='x', expand=True)
    beschriftung = tk.Label(links, text=bezeichnung, bg=BG, fg=FG,
                            font=fenster.f_fett, anchor='w')
    beschriftung.pack(fill='x')
    erklaerung = None
    if hilfe:
        erklaerung = tk.Label(links, text=hilfe, bg=BG, fg=SUB,
                              font=fenster.f_klein, anchor='w', justify='left')
        erklaerung.pack(fill='x')
    if breit:
        # Breite Bedienelemente unter die Beschreibung statt daneben: Auf
        # Englisch sind die Wörter länger, und rechts wurde der letzte Knopf
        # abgeschnitten („Ve…" statt „Very large").
        rechts = tk.Frame(links, bg=BG)
        rechts.pack(fill='x', anchor='w', pady=(8, 0))
        # ⚠ Auch hier braucht es einen Abzug. Ohne ihn bekommt der Text die
        # **volle** Breite der Zeile — die Ränder der Rollfläche darum sind
        # damit nicht eingerechnet, und die letzten Pixel fallen weg
        # (gemessen: 5, tools/randpruefung.py).
        #
        # Die Beschriftung braucht denselben Umbruch: Auf Englisch sind die
        # Wörter länger, und bisher hatte sie in diesem Zweig gar keinen.
        if erklaerung is not None:
            _umbruch(erklaerung, bezug=zeile, abzug=10)
        _umbruch(beschriftung, bezug=zeile, abzug=10)
    else:
        rechts = tk.Frame(zeile, bg=BG)
        rechts.pack(side='right', padx=(16, 0))
        # ⚠ Hier NICHT an `links` messen: Der Rahmen ist in genau dem Moment
        # zu breit, in dem der Text überläuft — er würde den Fehler bestätigen
        # statt ihn zu beheben. Gemessen wird am gemeinsamen Elternrahmen
        # abzüglich des Bedienelements, das rechts steht.
        # ⚠ `abzug` deckt mehr ab als nur `padx=(16, 0)`: `winfo_reqwidth()`
        # liefert die **gewünschte** Breite des Bedienelements, nicht die
        # tatsächliche. Bei Schiebeschaltern und Zahlenfeldern liegen ein paar
        # Pixel dazwischen — gemessen fehlten 5 (tools/randpruefung.py). Mit
        # Luft bricht der Text minimal früher um, statt abgeschnitten zu werden.
        if erklaerung is not None:
            _umbruch(erklaerung, bezug=zeile, neben=rechts, abzug=26)
        _umbruch(beschriftung, bezug=zeile, neben=rechts, abzug=26)
    tk.Frame(eltern, bg=LINIE, height=1).pack(fill='x', pady=(12, 0))
    return rechts


# --------------------------------------------------------------------- Seiten
def _liste(fenster, rahmen):
    """Die Bauplan-Liste — das vorhandene Fenster, eingebettet."""
    from . import bestandsfenster
    fenster.bestandsseite = bestandsfenster.Bestandsfenster(rahmen=rahmen)


def _fortschritt(fenster, rahmen):
    """Wie weit bin ich? — nach Bereichen gegliedert, jeder Bereich aufklappbar.

    ⚠ Vorher standen hier alle 25 Kategorien in einer einzigen langen Liste. Bei
    722 Bauplänen sucht man darin ewig, und der eine Wert, der einen gerade
    interessiert, steht irgendwo in der Mitte. Jetzt zuerst die vier Bereiche mit
    ihrem Gesamtstand — und die Einzelheiten erst auf Klick. Eingeklappt zu
    starten ist Absicht: Der Überblick ist die Antwort auf „wie weit bin ich",
    die Kategorien sind die Antwort auf „und wo genau".
    """
    _ueberschrift(fenster, rahmen, t('hf_fortschritt'), t('s_fo_lead'))
    innen = _rollflaeche(rahmen)
    try:
        bestand = bestand_datei.laden()
        katalog = katalog_modul.laden()
    except Exception as ausnahme:
        fehler.merken('seiten.fortschritt', ausnahme)
        return

    bp = katalog.get('bauplaene') or {}
    habe = set(bestand.get('bauplaene') or {})
    # Je Bereich: Liste von (Kategorie, gesamt, meine)
    nach_bereich = {}
    for schluessel, e in bp.items():
        roh = katalog_modul.art_kennung(e)
        bereich = katalog_modul.obergruppe(roh)
        art = katalog_modul.art_lesbar(roh) if roh else '—'
        zaehler = nach_bereich.setdefault(bereich, {})
        gesamt, meine = zaehler.get(art, (0, 0))
        zaehler[art] = (gesamt + 1, meine + (1 if schluessel in habe else 0))

    gesamt_alle = sum(g for z in nach_bereich.values() for g, _ in z.values()) or 1
    meine_alle = sum(m for z in nach_bereich.values() for _, m in z.values())

    kopf = tk.Frame(innen, bg=BG)
    kopf.pack(fill='x', pady=(0, 4))
    tk.Label(kopf, text=str(meine_alle), bg=BG, fg=ACCENT,
             font=fenster.f_titel).pack(side='left')
    tk.Label(kopf, text=t('s_fo_von')
             % (gesamt_alle, 100.0 * meine_alle / gesamt_alle),
             bg=BG, fg=SUB, font=fenster.f_klein).pack(side='left')

    from .hauptfenster import rundbalken
    rundbalken(innen, 9, meine_alle / float(gesamt_alle), BG, '#222b3b',
               ACCENT).pack(fill='x', pady=(6, 18))

    for bereich in katalog_modul.OBERGRUPPEN:
        zaehler = nach_bereich.get(bereich)
        if not zaehler:
            continue
        gesamt = sum(g for g, _ in zaehler.values())
        meine = sum(m for _, m in zaehler.values())
        _fortschritt_bereich(fenster, innen, t('gruppe_' + bereich), gesamt,
                             meine, zaehler)


def _fortschritt_bereich(fenster, eltern, titel, gesamt, meine, kategorien):
    """Ein Bereich mit Gesamtbalken — die Kategorien darin klappen auf."""
    from .hauptfenster import rundbalken
    zustand = {'offen': False}

    kopf = tk.Frame(eltern, bg=BG, cursor='hand2')
    kopf.pack(fill='x', pady=(10, 2))
    pfeil = zeichen.zeile(kopf, 'aufklappen', grund=BG,
                          schrift=fenster.f_klein)
    pfeil.pack(side='left')
    tk.Label(kopf, text=titel, bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(side='left')
    tk.Label(kopf, text='  %d / %d' % (meine, gesamt), bg=BG, fg=SUB,
             font=fenster.f_klein, anchor='w').pack(side='left')

    anteil = max(0.0, min(1.0, meine / float(gesamt or 1)))
    rundbalken(eltern, 9, anteil, BG, '#222b3b', ACCENT).pack(fill='x',
                                                              pady=(2, 0))

    koerper = tk.Frame(eltern, bg=BG)

    def zeichnen():
        if koerper.winfo_children():
            return
        for art, (art_gesamt, art_meine) in sorted(kategorien.items(),
                                                   key=lambda x: -x[1][0]):
            zeile = tk.Frame(koerper, bg=BG)
            zeile.pack(fill='x', pady=3)
            tk.Label(zeile, text=art, bg=BG, fg=SUB, font=fenster.f_klein,
                     width=22, anchor='w').pack(side='left')
            teil = max(0.0, min(1.0, art_meine / float(art_gesamt or 1)))
            rundbalken(zeile, 7, teil, BG, '#222b3b', ACCENT,
                       breite=260).pack(side='left', padx=8)
            tk.Label(zeile, text='%d / %d' % (art_meine, art_gesamt), bg=BG,
                     fg=SUB, font=fenster.f_klein, width=10,
                     anchor='e').pack(side='right')

    def umschalten(*_):
        zustand['offen'] = not zustand['offen']
        pfeil.symbol_tauschen('zuklappen' if zustand['offen']
                             else 'aufklappen')
        if zustand['offen']:
            zeichnen()
            koerper.pack(fill='x', padx=(18, 0), pady=(6, 0))
        else:
            koerper.pack_forget()

    # Der ganze Kopf ist die Schaltfläche, nicht nur der Pfeil.
    for teil in [kopf] + list(kopf.winfo_children()):
        teil.bind('<Button-1>', umschalten)
        try:
            teil.configure(cursor='hand2')
        except tk.TclError:
            pass


def _einstellungen(fenster):
    """Die Bausteine des Einstellungsfensters — einmal erzeugt, mehrfach genutzt."""
    if getattr(fenster, '_einst', None) is None:
        from . import einstellungsfenster
        leer = tk.Frame(fenster.root, bg=BG)     # nur als Halter, wird nie gepackt
        fenster._einst = einstellungsfenster.Einstellungsfenster(rahmen=leer)
        # Ohne diesen Rückruf öffnet ein Sprachwechsel ein zweites Fenster.
        fenster._einst.beim_sprachwechsel = fenster.neu_aufbauen
        # ⚠ Und ohne diesen laufen alle Rückmeldungen ins Leere: Eingebettet gibt
        # es den Fuß des Einstellungsfensters nicht, also auch sein Meldungs-Label
        # nicht. Jeder Klick auf „Jetzt auffrischen", „Übersetzung prüfen" oder eine
        # Textquelle brach deshalb mit `AttributeError` ab, **bevor** überhaupt
        # etwas passierte — die Seite sah fertig aus und tat nichts.
        fenster._einst.melder = fenster.sagen
    return fenster._einst


def _allgemein(fenster, rahmen):
    from . import autostart, pfade
    from .hauptfenster import schiebeschalter
    _ueberschrift(fenster, rahmen, t('hf_allgemein'),
                  t('s_allg_lead'))
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)

    ziel = _feld(fenster, innen, t('e_sprache'), t('s_sprache_h'),
                 breit=True)
    wahl = _wahl(fenster, ziel,
                 [('auto', t('sprache_auto')), ('de', 'Deutsch'), ('en', 'English')],
                 pfade.einstellungen().get('sprache') or 'auto',
                 lambda k: (wahl.setzen(k), e._sprache_waehlen(k)))
    wahl.pack()

    ziel = _feld(fenster, innen, t('e_ton'),
                 t('s_ton_h'))

    def ton_um():
        neu_wert = not pfade.einstellung_wahrheit('signalton', True)
        pfade.einstellung_setzen('signalton', neu_wert)
        fenster.sagen('%s: %s' % (t('e_ton'), t('e_an') if neu_wert else t('e_aus')))
        return neu_wert

    schiebeschalter(ziel, pfade.einstellung_wahrheit('signalton', True),
                    ton_um).pack()

    ziel = _feld(fenster, innen,
                 t('autostart_win') if sys.platform.startswith('win')
                 else t('autostart_linux'),
                 t('s_autostart_h'))
    if autostart.moeglich():
        def autostart_um():
            neu_wert = not autostart.ist_an()
            autostart.setzen(neu_wert)
            fenster.sagen(t('s_al_autostart')
                          % (t('e_an') if neu_wert else t('e_aus')))
            return autostart.ist_an()

        schalter = schiebeschalter(ziel, autostart.ist_an(), autostart_um)
        schalter.pack()
        # Mitschalten, wenn der Autostart woanders umgestellt wird — etwa am
        # Symbol im Overlay, das ja gleichzeitig sichtbar ist.
        autostart.anzeige_anmelden(
            lambda: schalter.zeichnen(autostart.ist_an()))
    else:
        tk.Label(ziel, text=t('s_nicht_moegl'), bg=BG, fg=SUB,
                 font=fenster.f_klein).pack()

    _menueeintrag_feld(fenster, innen)

    ziel = _feld(fenster, innen, t('s_tray'),
                 t('s_tray_h'))
    if sys.platform.startswith('win'):
        def tray_um():
            neu_wert = not pfade.einstellung_wahrheit('tray', True)
            pfade.einstellung_setzen('tray', neu_wert)
            return neu_wert

        schiebeschalter(ziel, pfade.einstellung_wahrheit('tray', True),
                        tray_um).pack()
    else:
        tk.Label(ziel, text=t('s_nur_win'), bg=BG, fg=SUB,
                 font=fenster.f_klein).pack()


def _anzeige(fenster, rahmen):
    from . import pfade
    from .hauptfenster import schiebeschalter
    _ueberschrift(fenster, rahmen, t('hf_anzeige'),
                  t('s_anz_lead'))
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)

    # --- Wie sich das Overlay im Spiel verhält -------------------------------
    # Angestoßen von einer Rückmeldung von Haldjas (pr0citizen): „Das Overlay ist permanent
    # zu sehen und nicht durchklickbar. Wenn ich im Kampf mit der Maus
    # hineinkomme, wird das unangenehm."
    ziel = _feld(fenster, innen, t('s_ov_modus'), t('s_ov_modus_h'), breit=True)
    modus = _wahl(fenster, ziel,
                  [('immer', t('s_ov_immer')), ('popup', t('s_ov_popup'))],
                  pfade.einstellung('overlay_modus') or 'immer',
                  lambda k: _overlay_modus(fenster, modus, k))
    modus.pack()

    ziel = _feld(fenster, innen, t('s_ov_dauer'), t('s_ov_dauer_h'))
    from .hauptfenster import rundes_feld as _zahlfeld
    dauer = _zahlfeld(ziel, None, fenster.f_klein, '#0c1017', LINIE, ACCENT, FG,
                      breite=6, justify='right')
    dauer.insert(0, str(pfade.einstellung_zahl('popup_sekunden', 6, 2, 60)))
    dauer.halter.pack()

    def dauer_merken(_=None):
        try:
            wert = max(2, min(60, int(dauer.get())))
            pfade.einstellung_setzen('popup_sekunden', wert)
            fenster.sagen(t('s_ov_dauer_sagen') % wert)
        except ValueError:
            pass

    dauer.bind('<FocusOut>', dauer_merken)
    dauer.bind('<Return>', dauer_merken)

    ziel = _feld(fenster, innen, t('s_ov_durch'), t('s_ov_durch_h'), breit=True)
    if _durchklick_moeglich():
        schiebeschalter(ziel, pfade.einstellung_wahrheit('durchklickbar', False),
                        lambda: _durchklick_um(fenster)).pack()
    else:
        # Ehrlich statt still: Unter nativem Wayland kann ein gewöhnliches Fenster
        # keine Klicks weiterreichen. Ein Schalter, der nichts bewirkt, wäre
        # schlimmer als gar keiner.
        tk.Label(ziel, text=t('s_ov_durch_nein'), bg=BG, fg=SUB,
                 font=fenster.f_klein, anchor='w', justify='left').pack(fill='x')

    ziel = _feld(fenster, innen, t('hf_schrift'), t('hf_schrift_hilfe'),
                 breit=True)
    wahl = _wahl(fenster, ziel,
                 [(s, t('hf_s_' + s))
                  for s in ('klein', 'normal', 'gross', 'sehrgross')],
                 pfade.einstellung('schriftgroesse') or 'normal',
                 lambda k: (wahl.setzen(k),
                            fenster.schriftgroesse_setzen(k),
                            fenster.sagen('%s: %s' % (t('hf_schrift'),
                                                      t('hf_s_' + k)))))
    wahl.pack()

    ziel = _feld(fenster, innen, t('e_deckkraft'),
                 t('s_deck_h'))
    from .hauptfenster import regler as schieberegler
    reihe = tk.Frame(ziel, bg=BG)
    reihe.pack()
    wertlabel = tk.Label(reihe, text='%d %%' % e.deckkraft.get(), bg=BG,
                         fg=ACCENT, font=fenster.f_klein, width=6, anchor='e')

    def deckkraft_setzen(w):
        e.deckkraft.set(w)
        wertlabel.configure(text='%d %%' % w)
        try:
            e._deckkraft_vorfuehren(w)
        except Exception:
            pass
        pfade.einstellung_setzen('deckkraft_prozent', w)

    schieberegler(reihe, 30, 100, e.deckkraft.get(),
                  deckkraft_setzen).pack(side='left')
    wertlabel.pack(side='left', padx=(8, 0))

    ziel = _feld(fenster, innen, t('s_klapp'),
                 t('s_klapp_h'))

    def klapp_um():
        neu_wert = not pfade.einstellung_wahrheit('eingeklappt', False)
        pfade.einstellung_setzen('eingeklappt', neu_wert)
        return neu_wert

    schiebeschalter(ziel, pfade.einstellung_wahrheit('eingeklappt', False),
                    klapp_um).pack()

    ziel = _feld(fenster, innen, t('s_vorne'),
                 t('s_vorne_h'))

    def vorne_um():
        neu_wert = not pfade.einstellung_wahrheit('immer_vorne', True)
        pfade.einstellung_setzen('immer_vorne', neu_wert)
        fenster.sagen(t('s_an_vorne')
                      % (t('e_an') if neu_wert else t('e_aus')))
        return neu_wert

    schiebeschalter(ziel, pfade.einstellung_wahrheit('immer_vorne', True),
                    vorne_um).pack()

    ziel = _feld(fenster, innen, t('s_zeilen'),
                 t('s_zeilen_h'))
    from .hauptfenster import rundes_feld
    zahl = rundes_feld(ziel, None, fenster.f_klein, '#0c1017', LINIE, ACCENT, FG,
                       breite=6, justify='right')
    zahl.insert(0, str(pfade.einstellung_zahl('max_zeilen', 20, 5, 100)))
    zahl.halter.pack()

    def zahl_merken(_=None):
        try:
            pfade.einstellung_setzen('max_zeilen',
                                     max(5, min(100, int(zahl.get()))))
            fenster.sagen(t('s_an_zeilen') % zahl.get())
        except ValueError:
            pass

    zahl.bind('<FocusOut>', zahl_merken)
    zahl.bind('<Return>', zahl_merken)

    ziel = _feld(fenster, innen, t('s_lage'),
                 t('s_lage_h'))

    def lage_weg():
        # Die gemerkte Lage wegwerfen reicht nicht: Ohne Positionsangabe stellt Tk
        # das Fenster nach `+0+0`, und bei einem hochkant stehenden Monitor links
        # außen liegt dort gar kein Bild — der Knopf hätte das Overlay also wieder
        # dorthin geschickt, wo man es sucht. Deshalb wird aktiv die Standardlage
        # gesetzt: mittig auf dem Hauptbildschirm. Wie viele Bildschirme jemand hat,
        # wissen wir nicht; die Mitte des Hauptbildschirms passt überall.
        from . import bildschirm
        try:
            os.remove(pfade.app_datei('watcher.json'))
        except OSError:
            pass
        overlay = bildschirm.OVERLAY[0]
        if overlay is not None:
            try:
                overlay.geometry(bildschirm.mittig(overlay, 440, 1000))
            except Exception as ausnahme:
                fehler.merken('seiten.lage_weg', ausnahme)
        fenster.sagen(t('s_an_lage_weg'))

    _knopf(fenster, ziel, t('s_zuruecksetzen'), lage_weg).pack()


def _ordner(fenster, rahmen):
    from . import pfade
    _ueberschrift(fenster, rahmen, t('hf_ordner'),
                  t('s_ordner_lead'))
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)

    gefunden = None
    try:
        gefunden = pfade.spiel_ordner()
    except Exception:
        pass
    if gefunden:
        _status(fenster, innen, 'haken', t('s_sc_da'),
                t('s_or_mitlesen') % gefunden)
    else:
        _status(fenster, innen, '!', t('s_sc_weg'),
                t('s_sc_weg_h'), farbe=GOLD)

    tk.Label(innen, text=t('e_spiel'), bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(fill='x', pady=(6, 0))
    _fliesstext(innen, t('e_spiel_hilfe'), fenster.f_klein, fill='x')

    def spiel_waehlen():
        # ⚠ Vorher lief das über `e._waehlen(...)`, und das übergibt
        # `parent=self.root` — eingebettet ist das ein Rahmen, der nie gepackt
        # wird. Der Dialog erschien deshalb nicht: „beim Klick passiert nichts".
        gewaehlt = ordner_waehlen(t('e_spiel'), e.spiel.get())
        if gewaehlt:
            e.spiel.set(gewaehlt)
            e._speichern()
            fenster.sagen(t('e_neustart_noetig'))

    _pfadfeld(fenster, innen, e.spiel, spiel_waehlen,
              oeffnen=lambda: fenster.sagen(
                  t('s_or_geoeffnet') if _ordner_zeigen(e.spiel.get())
                  else t('s_or_nicht_auf')))

    tk.Label(innen, text=t('s_eigene'), bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(fill='x', pady=(20, 0))
    _fliesstext(innen, t('s_eigene_h'), fenster.f_klein, fill='x')
    ablage = tk.StringVar(value=pfade.app_ordner())

    def ablage_oeffnen():
        # Nur melden, was auch stimmt: „Ordner geöffnet" zu sagen, während gar
        # nichts aufgeht, ist schlimmer als eine ehrliche Fehlanzeige.
        fenster.sagen(t('s_or_geoeffnet') if _ordner_zeigen(pfade.app_ordner())
                      else t('s_or_nicht_auf'))

    def ablage_waehlen():
        # ⚠ Hier stand nur ein Hinweis in der Fußzeile („lässt sich in den
        # Einstellungen hinterlegen") — auf der Seite, die genau diese Einstellung
        # IST. Für den Nutzer sah es aus, als täte der Knopf nichts.
        gewaehlt = ordner_waehlen(t('s_eigene'), ablage.get())
        if not gewaehlt:
            return
        pfade.einstellung_setzen('ablage_ordner', gewaehlt)
        ablage.set(gewaehlt)
        fenster.sagen(t('e_neustart_noetig'))

    _pfadfeld(fenster, innen, ablage, ablage_waehlen, oeffnen=ablage_oeffnen)

    tk.Label(innen, text='%s  —  %s' % (t('e_launcher'), t('s_optional')), bg=BG, fg=FG,
             font=fenster.f_fett, anchor='w').pack(fill='x', pady=(20, 0))
    _fliesstext(innen, t('e_launcher_hilfe'), fenster.f_klein, fill='x')
    def launcher_waehlen():
        gewaehlt = ordner_waehlen(t('e_launcher'), e.launcher.get())
        if gewaehlt:
            e.launcher.set(gewaehlt)
            e._speichern()
            fenster.sagen(t('e_neustart_noetig'))

    _pfadfeld(fenster, innen, e.launcher, launcher_waehlen,
              platzhalter=t('s_or_leer'))


def _menueeintrag_feld(fenster, innen):
    """Startmenü-Eintrag anlegen oder entfernen — nur unter Linux sinnvoll.

    Unter Windows erledigt das der Installer; dort wäre der Punkt nur Ballast.
    """
    from . import verknuepfung
    if not verknuepfung.moeglich():
        return
    ziel = _feld(fenster, innen, t('s_menue'), t('s_menue_h'), breit=True)
    reihe = tk.Frame(ziel, bg=BG)
    reihe.pack()
    stand = tk.Label(reihe, text='', bg=BG, fg=SUB, font=fenster.f_klein)

    def zeigen():
        stand.configure(text=t('s_menue_steht') if verknuepfung.vorhanden() else '')

    def anlegen():
        geklappt, wohin = verknuepfung.anlegen()
        fenster.sagen((t('as_menue_da') % wohin) if geklappt
                      else t('as_menue_nein') % wohin)
        zeigen()

    def weg():
        verknuepfung.entfernen()
        fenster.sagen(t('s_menue_weg_ok'))
        zeigen()

    _knopf(fenster, reihe, t('s_menue_anlegen'), anlegen).pack(side='left')
    _knopf(fenster, reihe, t('s_menue_weg'), weg).pack(side='left', padx=8)
    stand.pack(side='left', padx=(10, 0))
    zeigen()


def _durchklick_moeglich():
    from . import overlay
    try:
        return overlay.durchklickbar_moeglich()
    except Exception:
        return False


def _durchklick_um(fenster):
    """Klicks durchreichen ein- oder ausschalten — und sofort anwenden."""
    from . import overlay, pfade
    neu_wert = not pfade.einstellung_wahrheit('durchklickbar', False)
    pfade.einstellung_setzen('durchklickbar', neu_wert)
    geklappt = True
    wurzel = overlay.OVERLAY_FENSTER[0] if overlay.OVERLAY_FENSTER else None
    if wurzel is not None:
        try:
            geklappt = overlay.durchklickbar_setzen(wurzel, neu_wert)
        except Exception as ausnahme:
            fehler.merken('seiten.durchklick', ausnahme)
            geklappt = False
    if neu_wert and not geklappt:
        fenster.sagen(t('ov_durchklick_geht_nicht'))
        pfade.einstellung_setzen('durchklickbar', False)
        return False
    fenster.sagen(t('s_ov_durch_sagen')
                  % (t('e_an') if neu_wert else t('e_aus')))
    return neu_wert


def _overlay_modus(fenster, wahl, kennung):
    """Zwischen „immer sichtbar" und „nur bei Neuzugang" umstellen."""
    from . import overlay, pfade
    wahl.setzen(kennung)
    pfade.einstellung_setzen('overlay_modus', kennung)
    wurzel = overlay.OVERLAY_FENSTER[0] if overlay.OVERLAY_FENSTER else None
    if wurzel is not None:
        try:
            if kennung == 'popup':
                # Nicht sofort verstecken — sonst ist das Fenster weg, während
                # man noch in den Einstellungen steht. Es verschwindet beim
                # nächsten Mal von selbst.
                pass
            else:
                wurzel.deiconify()
        except Exception as ausnahme:
            fehler.merken('seiten.overlay_modus', ausnahme)
    if kennung == 'popup':
        fenster.sagen(t('s_ov_popup_gleich'))
    else:
        fenster.sagen(t('s_ov_modus_sagen') % t('s_ov_immer'))


def saubere_umgebung():
    """Umgebung für fremde Programme — ohne unsere eigenen Bibliothekspfade.

    ⚠ Das ist im AppImage entscheidend. Dort zeigen `LD_LIBRARY_PATH`, `PYTHONHOME`
    und `PYTHONPATH` in das entpackte Paket. Startet man daraus ein Systemprogramm
    wie `zenity`, lädt es unsere mitgelieferten Bibliotheken statt seiner eigenen
    und stirbt sofort — der Dialog erscheint nicht, und für den Nutzer sieht es
    aus, als täte der Knopf nichts. AppImage setzt die ursprünglichen Werte unter
    `*_ORIG` ab; die gelten hier wieder.
    """
    import os
    umgebung = dict(os.environ)
    for name in ('LD_LIBRARY_PATH', 'PYTHONHOME', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE',
                 'QT_PLUGIN_PATH', 'GTK_PATH', 'GDK_PIXBUF_MODULE_FILE',
                 'GI_TYPELIB_PATH', 'XDG_DATA_DIRS', 'PERLLIB', 'GSETTINGS_SCHEMA_DIR'):
        urspruenglich = umgebung.pop(name + '_ORIG', None)
        if urspruenglich:
            umgebung[name] = urspruenglich
        else:
            umgebung.pop(name, None)
    return umgebung


def ordner_waehlen(titel, start=None):
    """Einen Ordner auswählen lassen — möglichst mit dem Dialog des Systems.

    ⚠ Tk bringt unter Linux einen eigenen Dialog mit, und der stammt optisch aus
    den Neunzigern: graue Motif-Knöpfe, eigene Schrift, nichts davon passt zum
    Rest des Fensters. Unter Windows und macOS ruft Tk dagegen den **echten**
    Systemdialog auf — dort ist alles in Ordnung.

    Deshalb wird unter Linux zuerst nach `kdialog` (KDE) und `zenity` (GNOME und
    fast überall vorhanden) gesucht. Beide sehen aus wie der Rest des Systems.
    Gibt es keines von beiden, bleibt der Tk-Dialog als Rückfall — hässlich, aber
    funktionierend ist besser als gar nichts.

    ⚠ Rückgabecodes auseinanderhalten: **1 heißt „abgebrochen"** und ist eine
    gültige Antwort — dann ist der Nutzer fertig und wir hören auf. Jeder andere
    Code heißt, das Werkzeug selbst ist gescheitert; dann wird das nächste
    versucht und am Ende der Tk-Dialog. Vorher galt beides als Abbruch, und ein
    im AppImage abgestürztes `zenity` sah aus wie ein Knopf ohne Funktion.
    """
    import subprocess
    if not sys.platform.startswith(('win', 'darwin')):
        umgebung = saubere_umgebung()
        befehle = [
            ['kdialog', '--getexistingdirectory',
             start or os.path.expanduser('~'), '--title', titel],
            ['zenity', '--file-selection', '--directory', '--title', titel]
            + (['--filename', start.rstrip('/') + '/'] if start else []),
        ]
        for befehl in befehle:
            if not _im_pfad(befehl[0]):
                continue
            try:
                fertig = subprocess.run(befehl, capture_output=True, text=True,
                                        timeout=600, env=umgebung)
            except Exception as ausnahme:
                fehler.merken('seiten.ordner_waehlen:%s' % befehl[0], ausnahme)
                continue
            gewaehlt = (fertig.stdout or '').strip()
            if fertig.returncode == 0 and gewaehlt:
                return gewaehlt
            if fertig.returncode == 1:
                return ''                      # bewusst abgebrochen
            fehler.merken('seiten.ordner_waehlen:%s' % befehl[0],
                          RuntimeError('Code %s: %s' % (fertig.returncode,
                                                        (fertig.stderr or '')[:200])))
    from tkinter import filedialog
    return filedialog.askdirectory(title=titel, initialdir=start or None) or ''


def _im_pfad(name):
    """Gibt es dieses Programm auf dem Rechner?"""
    import shutil
    return bool(shutil.which(name))


def _ordner_zeigen(pfad):
    """Den Ordner im Dateiverwalter öffnen — auf jedem System anders.

    ⚠ Auch hier die saubere Umgebung: Im AppImage würde `xdg-open` sonst unsere
    mitgelieferten Bibliotheken laden und sofort sterben — der Dateiverwalter
    ginge nicht auf, ohne dass irgendetwas darauf hinweist.
    """
    import subprocess
    if not pfad or not os.path.isdir(pfad):
        return False
    try:
        if sys.platform.startswith('win'):
            os.startfile(pfad)                      # noqa: S606
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', pfad])
        else:
            subprocess.Popen(['xdg-open', pfad], env=saubere_umgebung())
        return True
    except Exception as ausnahme:
        fehler.merken('seiten.ordner_zeigen', ausnahme, pfad)
        return False


def _spiel(fenster, rahmen):
    """Auftragstexte — Textquelle wählen und die Bauplan-Angaben eintragen."""
    from . import pfade
    from .hauptfenster import schiebeschalter
    _ueberschrift(fenster, rahmen, t('hf_spiel'), t('s_sp_lead'))
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)

    # --- Spiel starten -------------------------------------------------------
    # Wunsch von Morkhan (KRT), 25.08.2026: „so wie beim sc deutsch
    # launcher das man spiel von dort aus starten kann".
    #
    # Der Knopf erscheint nur, wenn wirklich ein Weg gefunden wurde — unter
    # Windows der RSI Launcher, unter Linux der lug-helper. Ein Knopf, der
    # nichts tut, wäre schlimmer als keiner.
    if pfade.spielstarter():
        ziel_start = _feld(fenster, innen, t('s_sp_start'), t('s_sp_start_h'),
                           breit=True)

        def spiel_starten():
            fenster.sagen(t('s_sp_start_lauft'))
            ok, grund = pfade.spiel_starten()
            if not ok:
                fenster.sagen(t('s_sp_start_nein', grund))

        _knopf(fenster, ziel_start, t('s_sp_start_knopf'), spiel_starten,
               stark=True).pack()

    # Der Zustandskasten sitzt in einem eigenen Rahmen, damit er nach jeder
    # Aktion neu gefüllt werden kann, ohne die ganze Seite anzufassen.
    kasten = tk.Frame(innen, bg=BG)
    kasten.pack(fill='x')

    def lage_zeigen():
        for kind in kasten.winfo_children():
            kind.destroy()
        try:
            lage = e.inj_lage()
        except Exception as ausnahme:
            fehler.merken('seiten.spiel.lage', ausnahme)
            return
        if not pfade.einstellung_wahrheit('inj_an', True):
            _status(fenster, kasten, 'offen', t('s_sp_aus_hinweis'), '', farbe=SUB)
            return
        if lage['drin']:
            zusatz = []
            if lage['quelle']:
                zusatz.append(t('s_sp_quelle_ist')
                              % t(_QUELLTEXT.get(lage['quelle'], 's_sp_q_or')))
            if lage['stand']:
                zusatz.append(str(lage['stand']))
            _status(fenster, kasten, 'haken', t('s_sp_steht'), ' · '.join(zusatz))
        else:
            _status(fenster, kasten, 'offen', t('s_sp_nichts'), t('s_sp_nichts_h'),
                    farbe=SUB)

    # Damit auch Aktionen im Einstellungsobjekt den Kasten auffrischen.
    e.lage_melder = lage_zeigen
    lage_zeigen()

    # --- An oder aus ---------------------------------------------------------
    # ⚠ Der Schalter fehlte ganz. Wer auf PTU spielt oder die Textdatei in Ruhe
    # lassen will, hatte keine Möglichkeit außer „Wieder entfernen" — und beim
    # nächsten Start schrieb das Werkzeug wieder hinein.
    ziel = _feld(fenster, innen, t('s_sp_an'), t('s_sp_an_h'), breit=True)

    def inj_an_um():
        neu_wert = not pfade.einstellung_wahrheit('inj_an', True)
        pfade.einstellung_setzen('inj_an', neu_wert)
        fenster.sagen(t('s_sp_an_sagen')
                      % (t('e_an') if neu_wert else t('e_aus')))
        lage_zeigen()
        return neu_wert

    schiebeschalter(ziel, pfade.einstellung_wahrheit('inj_an', True),
                    inj_an_um).pack()

    # --- Textquelle ----------------------------------------------------------
    ziel = _feld(fenster, innen, t('s_sp_quelle'), t('s_sp_quelle_h'),
                 breit=True)
    wahl = _wahl(fenster, ziel,
                 [('deutsch', t('s_sp_q_de')), ('starstrings', t('s_sp_q_ss')),
                  ('original', t('s_sp_q_or'))],
                 pfade.einstellung('inj_quelle') or '',
                 lambda k: _quelle_waehlen(fenster, e, wahl, k, lage_zeigen))
    wahl.pack()

    ziel = _feld(fenster, innen, t('s_sp_auto'), t('s_sp_auto_h'))

    def inj_auto_um():
        neu_wert = not pfade.einstellung_wahrheit('inj_auto', True)
        pfade.einstellung_setzen('inj_auto', neu_wert)
        fenster.sagen(t('s_sp_auto_sagen')
                      % (t('e_an') if neu_wert else t('e_aus')))
        return neu_wert

    schiebeschalter(ziel, pfade.einstellung_wahrheit('inj_auto', True),
                    inj_auto_um).pack()

    ziel = _feld(fenster, innen, t('s_sp_hand'), t('s_sp_hand_h'), breit=True)
    reihe = tk.Frame(ziel, bg=BG)
    reihe.pack()
    _knopf(fenster, reihe, t('s_sp_jetzt'),
           lambda: (e._inj_erneuern(), lage_zeigen()),
           stark=True).pack(side='left')
    _knopf(fenster, reihe, t('s_sp_pruefen'),
           lambda: (e._inj_pruefen(), lage_zeigen())).pack(side='left', padx=8)
    _knopf(fenster, reihe, t('s_sp_weg'),
           lambda: (e._inj_entfernen(), lage_zeigen()),
           gefahr=True).pack(side='left')

    _status(fenster, innen, '!', t('s_sp_warn'), t('s_sp_warn_h'), farbe=GOLD)


# Welche Beschriftung zu welcher Quelle gehört — für den Zustandskasten.
_QUELLTEXT = {'deutsch': 's_sp_q_de', 'starstrings': 's_sp_q_ss',
              'original': 's_sp_q_or'}


def _quelle_waehlen(fenster, e, wahl, kennung, danach):
    """Eine Textquelle einrichten — das dauert, also erst ansagen.

    ⚠ Ohne Ansage sieht es aus, als sei nichts passiert: Das Herunterladen und
    Einsetzen braucht mehrere Sekunden, und in dieser Zeit stand vorher nichts
    im Fenster.
    """
    from . import pfade
    wahl.setzen(kennung)
    # ⚠ Die Wahl wird **vor** dem Einrichten gemerkt. Sie stand vorher dahinter,
    # und wenn das Herunterladen schiefging (kein Netz, Zertifikat, Server weg),
    # blieb die alte Quelle eingetragen — das Feld zeigte die neue, der Rest des
    # Programms rechnete mit der alten. Erst gilt, was gewählt wurde; ob es auch
    # eingerichtet werden konnte, sagt der Kasten darüber.
    pfade.einstellung_setzen('inj_quelle', kennung)
    fenster.sagen(t('s_sp_hole') % t(_QUELLTEXT.get(kennung, 's_sp_q_or')))
    try:
        e._inj_wechseln(kennung)
    except Exception as ausnahme:
        fehler.merken('seiten.spiel.quelle', ausnahme)
        fenster.sagen(t('inj_fehler', ausnahme))
    danach()


def _bestand(fenster, rahmen):
    from . import export, importieren
    _ueberschrift(fenster, rahmen, t('hf_bestand'), t('s_be_lead'))
    innen = _rollflaeche(rahmen)

    anzahl = _zahl_bestand()
    tk.Label(innen, text=t('s_be_aus'), bg=BG, fg=FG,
             font=fenster.f_titel, anchor='w').pack(fill='x', pady=(0, 2))
    _fliesstext(innen, t('s_be_aus_h'), fenster.f_klein,
                fill='x', pady=(0, 12))

    karte = _karte(innen)
    for name, wofuer in (('KRT Profit Basetool', t('s_be_n_bp') % anzahl),
                         ('scmdb.net', t('s_be_n_bp') % anzahl),
                         (t('s_be_voll'), t('s_be_voll_h'))):
        z = tk.Frame(karte, bg=FLAECHE)
        z.pack(fill='x', padx=16, pady=5)
        tk.Label(z, text=name, bg=FLAECHE, fg=FG, font=fenster.f_klein,
                 width=26, anchor='w').pack(side='left')
        tk.Label(z, text=wofuer, bg=FLAECHE, fg=SUB,
                 font=fenster.f_klein).pack(side='left')

    reihe = tk.Frame(innen, bg=BG)
    reihe.pack(fill='x', pady=(12, 0))

    def in_ablage():
        try:
            ergebnis = export.ablegen()
            wieviele = ergebnis[1] if isinstance(ergebnis, tuple) else ergebnis
            fenster.sagen(t('s_be_geschrieben') % wieviele)
            _ordner_zeigen(export.ablage_ordner())
        except Exception as ausnahme:
            fehler.merken('seiten.bestand.ablegen', ausnahme)
            fenster.sagen(t('s_be_schiefging'))

    def einzeln():
        from tkinter import filedialog
        ziel = filedialog.asksaveasfilename(
            title=t('s_be_speichern'), defaultextension='.json',
            initialfile=export.vorschlag('basetool'))
        if not ziel:
            return
        try:
            export.schreiben(ziel, art='basetool')
            fenster.sagen(t('s_be_gespeichert') % os.path.basename(ziel))
        except Exception as ausnahme:
            fehler.merken('seiten.bestand.einzeln', ausnahme)

    _knopf(fenster, reihe, t('s_be_alle_drei'), in_ablage,
           stark=True).pack(side='left')
    _knopf(fenster, reihe, t('s_be_einzeln'), einzeln).pack(side='left',
                                                            padx=8)
    _knopf(fenster, reihe, t('s_be_ablage'),
           lambda: _ordner_zeigen(export.ablage_ordner())).pack(side='left')

    tk.Label(innen, text=t('s_be_ein'), bg=BG, fg=FG,
             font=fenster.f_titel, anchor='w').pack(fill='x', pady=(28, 2))
    _fliesstext(innen, t('s_be_ein_h'), fenster.f_klein,
                fill='x', pady=(0, 12))

    vorschau_platz = tk.Frame(innen, bg=BG)

    def einlesen():
        from tkinter import filedialog
        pfad = filedialog.askopenfilename(
            title=t('s_be_ein'),
            filetypes=[('JSON', '*.json'), (t('alle_dateien'), '*.*')])
        if not pfad:
            return
        art, eintraege = importieren.lesen(pfad)
        for kind in vorschau_platz.winfo_children():
            kind.destroy()
        if not art:
            _status(fenster, vorschau_platz, '!', t('s_be_unbekannt'),
                    t('s_be_unbekannt_h'), farbe=ROT)
            return
        v = importieren.vorschau(eintraege)
        _vorschau_zeigen(fenster, vorschau_platz, art, eintraege, v)

    _knopf(fenster, innen, t('s_be_waehlen'), einlesen,
           stark=True).pack(anchor='w')
    _fliesstext(innen, t('s_be_erkannt'), fenster.f_klein,
                fill='x', pady=(10, 0))
    vorschau_platz.pack(fill='x', pady=(14, 20))
    # Der Kasten steht von Anfang an da — sonst wirkt die Seite unfertig, und
    # niemand weiß, dass vor dem Übernehmen noch eine Vorschau kommt.
    _leere_vorschau(fenster, vorschau_platz)


def _leere_vorschau(fenster, eltern):
    """Der Vorschau-Kasten, bevor eine Datei gewählt wurde."""
    innen = _karte(eltern, rand=SUB)
    tk.Label(innen, text=t('s_vorschau_leer'), bg=FLAECHE, fg=FG,
             font=fenster.f_fett, anchor='w').pack(fill='x', padx=16,
                                                   pady=(12, 2))
    _fliesstext(innen, t('s_vorschau_leer_h'), fenster.f_klein,
                grund=FLAECHE, abzug=32, fill='x', padx=16, pady=(0, 12))
    return innen


def _vorschau_zeigen(fenster, eltern, art, eintraege, v):
    """Was der Import täte — erst nach dem Knopf passiert wirklich etwas."""
    from . import importieren
    from .hauptfenster import marke as blase
    innen = _karte(eltern, rand=ACCENT)

    kopf = tk.Frame(innen, bg=FLAECHE)
    kopf.pack(fill='x', padx=16, pady=(12, 10))
    tk.Label(kopf, text=t('s_be_vorschau'), bg=FLAECHE,
             fg=FG, font=fenster.f_fett).pack(side='left')
    blase(kopf, {'eigen': t('s_be_eigen'), 'basetool': 'KRT Profit Basetool',
                 'scmdb': 'scmdb.net',
                 'launcher': 'SC Deutsch Launcher'}.get(art, art),
          ACCENT, fenster.f_klein).pack(side='right')

    zahlen = tk.Frame(innen, bg=FLAECHE)
    zahlen.pack(fill='x', padx=16, pady=(0, 10))
    for wert, wofuer, farbe in ((len(v['neu']), t('s_be_dazu'), ACCENT),
                                (len(v['schon_da']), t('s_be_schon'), FG),
                                (len(v['unbekannt']), t('s_be_nicht_kat'), GOLD)):
        s = tk.Frame(zahlen, bg=FLAECHE)
        s.pack(side='left', padx=(0, 30))
        tk.Label(s, text=str(wert), bg=FLAECHE, fg=farbe,
                 font=fenster.f_titel).pack(anchor='w')
        tk.Label(s, text=wofuer, bg=FLAECHE, fg=SUB,
                 font=fenster.f_klein).pack(anchor='w')

    if v['unbekannt']:
        tk.Label(innen, text=t('s_be_nicht_kat_h')
                             + ' · '.join(v['unbekannt'][:6])
                             + (' …' if len(v['unbekannt']) > 6 else ''),
                 bg=FLAECHE, fg=SUB, font=fenster.f_klein, anchor='w',
                 justify='left', wraplength=560).pack(fill='x', padx=16,
                                                      pady=(0, 8))

    _fliesstext(innen, t('s_be_merge'), fenster.f_klein,
                grund=FLAECHE, abzug=32, fill='x', padx=16, pady=(0, 10))

    reihe = tk.Frame(innen, bg=FLAECHE)
    reihe.pack(fill='x', padx=16, pady=(0, 14))

    def uebernehmen():
        dazu = importieren.uebernehmen(eintraege)
        fenster.sagen(t('s_be_genommen') % dazu)
        innen.halter.destroy()

    k = _knopf(fenster, reihe, t('s_be_nimm') % len(v['neu']),
               uebernehmen, stark=True)
    k.configure(bg=FLAECHE)
    k.pack(side='left')
    k2 = _knopf(fenster, reihe, t('abbrechen'), innen.halter.destroy)
    k2.configure(bg=FLAECHE)
    k2.pack(side='left', padx=8)


def _wasistneu(fenster, rahmen):
    """Die Änderungen — als Reiter, nicht als Fenster über dem Fenster.

    Zwei Dinge halten die Seite kurz, auch wenn zwanzig Fassungen zusammenkommen:
    Nur die **neueste** ist aufgeklappt, und ein Filter zeigt bei Bedarf nur
    Behobenes. Wer einen Fehler gemeldet hat, sucht genau danach.
    """
    _ueberschrift(fenster, rahmen, t('hf_wasistneu'), t('s_wn_lead'))

    from . import aktualisierung
    try:
        eintraege = aktualisierung.protokoll()
    except Exception as ausnahme:
        fehler.merken('seiten.wasistneu', ausnahme)
        eintraege = []

    stand = {'art': 'alle'}
    chips = {}
    leiste = tk.Frame(rahmen, bg=BG)
    leiste.pack(fill='x', pady=(0, 10))
    innen = _rollflaeche(rahmen)
    behaelter = tk.Frame(innen, bg=BG)
    behaelter.pack(fill='both', expand=True)

    def zeichnen():
        for kind in behaelter.winfo_children():
            kind.destroy()
        gezeigt = 0
        for nummer, e in enumerate(eintraege[:15]):
            punkte = aktualisierung.punkte_nach_art(e.get('text') or '')
            if stand['art'] != 'alle':
                punkte = [p for p in punkte if p[0] == stand['art']]
            if not punkte:
                continue
            gezeigt += 1
            # Nur die neueste Fassung offen; ältere sind einen Klick entfernt.
            offen = (nummer == 0) or stand['art'] != 'alle'
            _fassung(fenster, behaelter, e, punkte, offen)
        if not gezeigt:
            tk.Label(behaelter, text=t('s_wn_nichts'), bg=BG, fg=SUB,
                     font=fenster.f_klein).pack(anchor='w', pady=12)

    def waehlen(art):
        stand['art'] = art
        for kennung, k in chips.items():
            k.setzen(kennung == art)
        zeichnen()

    for kennung, text in (('alle', 'Alles'), ('neu', 'Neu'),
                          ('bess', 'Verbessert'), ('fix', 'Behoben')):
        an = (kennung == 'alle')
        k = _chip(fenster, leiste, text, an)
        k.pack(side='left', padx=(0, 6))
        k.bind('<Button-1>', lambda ev, s=kennung: waehlen(s))
        chips[kennung] = k

    zeichnen()


def _chip(fenster, eltern, text, an):
    """Ein anklickbarer Filter — abgerundet, Rand in Akzentfarbe wenn gewählt."""
    from .hauptfenster import _rundes_rechteck
    schrift = fenster.f_klein
    hoehe = schrift.metrics('linespace') + 12
    breite = schrift.measure(text) + 26
    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=BG,
                  highlightthickness=0, bd=0, cursor='hand2')
    blase = _rundes_rechteck(c, 1, 1, breite - 1, hoehe - 1,
                             radius=max(5, hoehe // 3),
                             fill=FLAECHE, outline=ACCENT if an else LINIE, width=1)
    beschriftung = c.create_text(breite / 2.0, hoehe / 2.0 + 1, text=text,
                                 fill=ACCENT if an else SUB, font=schrift)

    def setzen(gewaehlt):
        c.itemconfigure(blase, outline=ACCENT if gewaehlt else LINIE)
        c.itemconfigure(beschriftung, fill=ACCENT if gewaehlt else SUB)

    c.setzen = setzen
    return c


_ART_FARBE = {'neu': ACCENT, 'bess': '#7db8e8', 'fix': GOLD}
_ART_WORT = {'neu': 'Neu', 'bess': 'Verbessert', 'fix': 'Behoben'}


def _fassung(fenster, eltern, eintrag, punkte, offen):
    """Eine Fassung mit Kopfzeile zum Auf- und Zuklappen."""
    zustand = {'offen': offen}
    kopf = tk.Frame(eltern, bg=BG, cursor='hand2')
    kopf.pack(fill='x', padx=24, pady=(12, 2))
    pfeil = zeichen.zeile(kopf, 'zuklappen' if offen else 'aufklappen',
                          grund=BG, schrift=fenster.f_klein)
    pfeil.pack(side='left', padx=(0, 8))
    tk.Label(kopf, text=eintrag.get('version') or '—', bg=BG, fg=ACCENT,
             font=fenster.f_fett).pack(side='left')
    if eintrag.get('datum'):
        tk.Label(kopf, text='  ' + eintrag['datum'], bg=BG, fg=SUB,
                 font=fenster.f_klein).pack(side='left')
    tk.Label(kopf, text=t('s_wn_aenderungen') % len(punkte), bg=BG, fg=SUB,
             font=fenster.f_klein).pack(side='right')

    koerper = tk.Frame(eltern, bg=BG)
    if offen:
        koerper.pack(fill='x')

    from .hauptfenster import marke
    # Der Vorstellungssatz der Fassung steht **hier**, unter ihrer Überschrift —
    # nicht irgendwo am Seitenende. Wer eine Version aufklappt, will zuerst wissen,
    # worum es ging, und dann die Einzelheiten.
    from . import aktualisierung as _akt
    lead = _akt.einleitung(eintrag.get('text') or '')
    if lead:
        satz = tk.Label(koerper, text=lead, bg=BG, fg=SUB, font=fenster.f_klein,
                        anchor='w', justify='left', wraplength=600)
        satz.pack(fill='x', padx=24, pady=(2, 8))

        # Denselben Weg wie bei den Punkten: nicht rechnen, sondern nehmen, was
        # das Label wirklich bekommt — sonst ragt der Satz bei jeder
        # Fenstergröße heraus.
        def lead_umbruch(ereignis, lab=satz):
            passend = max(200, ereignis.width - 8)
            try:
                if abs(int(lab.cget('wraplength')) - passend) > 4:
                    lab.configure(wraplength=passend)
            except tk.TclError:
                pass

        satz.bind('<Configure>', lead_umbruch)

    # Alle Blasen so breit wie die längste Beschriftung — sonst flattern sie
    # und die Texte daneben fangen an unterschiedlichen Stellen an.
    breiteste = max(fenster.f_klein.measure(w) for w in _ART_WORT.values()) + 20
    for art, zeile in punkte:
        z = tk.Frame(koerper, bg=BG)
        z.pack(fill='x', pady=3)
        marke(z, _ART_WORT.get(art, ''), _ART_FARBE.get(art, SUB),
              fenster.f_klein, grund=BG,
              mindestbreite=breiteste).pack(side='left', anchor='n', padx=(0, 14))
        # ⚠ `wraplength` muss zur wirklichen Breite passen. Steht er zu hoch, bricht
        # der Text zu spät um und der Rest wird stumm abgeschnitten.
        #
        # Vorher stand hier „Fensterbreite minus 340" — ein geschätzter Abzug für
        # Seitenleiste, Ränder und die Art-Blase davor. Die Schätzung ging schief,
        # sobald sich eines davon änderte: Seit die Seitenleiste ihre Breite selbst
        # misst, fehlten rund 50 Pixel, und `tools/randpruefung.py` meldete die
        # Zeilen bei **jeder** Fenstergröße als beschnitten.
        #
        # Jetzt wird nicht mehr gerechnet, sondern genommen, was das Label
        # tatsächlich bekommt — und bei jeder Größenänderung neu. Damit stimmt es
        # auch, wenn jemand das Fenster zieht.
        etikett = tk.Label(z, text=_saubere_zeile(zeile), bg=BG, fg=FG,
                           font=fenster.f_klein, anchor='w', justify='left',
                           wraplength=max(360, (fenster.root.winfo_width()
                                                or 980) - 340))
        etikett.pack(side='left', fill='x', expand=True)

        def umbruch_anpassen(ereignis, lab=etikett):
            # Die Abfrage verhindert eine Schleife: Ein neuer Umbruch ändert die
            # Höhe, das löst wieder ein <Configure> aus.
            passend = max(200, ereignis.width - 8)
            try:
                if abs(int(lab.cget('wraplength')) - passend) > 4:
                    lab.configure(wraplength=passend)
            except tk.TclError:
                pass

        etikett.bind('<Configure>', umbruch_anpassen)

    def umschalten(*_):
        zustand['offen'] = not zustand['offen']
        pfeil.symbol_tauschen('zuklappen' if zustand['offen']
                             else 'aufklappen')
        if zustand['offen']:
            # ⚠ `after=kopf` ist der ganze Witz. Ohne das packt Tk den Inhalt ans
            # **Ende** der Fläche — also unter alle anderen Versionen. Bei elf
            # Fassungen klappte man v3.0.0 auf und der Text erschien unterhalb von
            # v1.0.0; wer nicht weit genug rollt, hält die Fassung für leer. Beim
            # ersten Zeichnen fiel das nicht auf, weil dort Kopf und Inhalt
            # ohnehin nacheinander gepackt werden.
            koerper.pack(fill='x', after=kopf)
        else:
            koerper.pack_forget()

    # ⚠ **Alle** Teile des Kopfes binden, nicht nur Rahmen und Pfeil. Die
    # Versionsnummer, das Datum und die Anzahl sind eigene Labels — ein Klick
    # darauf erreichte den Rahmen nie. Genau dorthin zielt man aber: Gemeldet als
    # „die alten Versionen sind gar nicht aufklappbar".
    for teil in [kopf, pfeil] + list(kopf.winfo_children()):
        teil.bind('<Button-1>', umschalten)
        try:
            teil.configure(cursor='hand2')
        except tk.TclError:
            pass


def _saubere_zeile(zeile):
    """Markdown-Auszeichnung raus — Tk zeigt sie sonst als Sternchen."""
    import re
    zeile = re.sub(r'\*\*(.+?)\*\*', r'\1', zeile)
    zeile = re.sub(r'`([^`]+)`', r'\1', zeile)
    zeile = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', zeile)
    return zeile.strip()


def _karte(eltern, rand=None, **kw):
    """Ein abgesetzter Kasten mit runden Ecken (siehe `hauptfenster.rundrahmen`)."""
    from .hauptfenster import rundrahmen
    innen = rundrahmen(eltern, FLAECHE, rand or LINIE, radius=8, grundfarbe=BG)
    innen.halter.pack(fill='x', **kw)
    return innen


def _wertzeile(fenster, eltern, bez, wert, farbe=None):
    z = tk.Frame(eltern, bg=FLAECHE)
    z.pack(fill='x', padx=16, pady=3)
    tk.Label(z, text=bez, bg=FLAECHE, fg=SUB, font=fenster.f_klein,
             width=24, anchor='w').pack(side='left')
    tk.Label(z, text=str(wert), bg=FLAECHE, fg=farbe or FG,
             font=fenster.f_klein, anchor='w').pack(side='left')


def _jetzt_nachsehen(fenster):
    """Wirklich bei GitHub nachfragen und sagen, was dabei herauskam.

    ⚠ Hier stand nur `fenster.sagen(t('s_ub_sucht'))` — der Knopf **meldete**, dass
    er sucht, und suchte nicht. Ein Nutzer (Bomb20, 25.08.2026) hatte deshalb auf
    rc18 weiterhin rc12 als neueste Fassung angeboten bekommen: Sein
    Zwischenspeicher blieb auf dem alten Stand, und der einzige Knopf, der ihn
    hätte auffrischen können, tat nichts.

    Läuft im eigenen Faden — die Abfrage geht ins Netz. Gezeichnet wird nur im
    Tk-Faden.
    """
    import threading
    from . import aktualisierung
    fenster.sagen(t('s_ub_sucht'))

    def einspielen_und_gehen(ziel):
        """Einspielen — und vorher sagen, was gleich passiert.

        ⚠ Der Hinweis kommt **vor** dem Start des Setups, nicht danach. Sonst
        liefe im Hintergrund schon der Restart Manager und zählte seine dreißig
        Sekunden herunter, während der Nutzer noch liest — und beendete den
        Watcher mitten im Dialog.

        ⚠ Läuft im Tk-Faden, nicht im Ladefaden: `messagebox` gehört dorthin,
        wo die Oberfläche lebt.
        """
        if aktualisierung.verpackung() == 'exe':
            from tkinter import messagebox
            messagebox.showinfo(t('s_ub_hinweis_titel'),
                                t('s_ub_hinweis_neustart'))
        geklappt, grund = aktualisierung.einspielen(ziel)
        if not geklappt:
            fenster.sagen(t('update_fehler', grund))
            return
        _BEREIT[0] = freigabe.get('version') or ''

        # ⚠ Unter Windows ist hier **Schluss** — kein zweiter Klick mehr.
        #
        # Der Ablauf mit „erst holen, dann auf ‚Jetzt neu starten' drücken"
        # stammt aus der Zeit des Dateitauschs: Damals lag die neue Datei nur
        # bereit, getauscht wurde beim Beenden. Der Installer dagegen **läuft
        # schon** — und wartet darauf, dass wir endlich gehen. Genau das hat am
        # 26.08.2026 die lange Pause verursacht, die der Autor gemeldet hat
        # („wieso es solange dauert bis er alles geschlossen hat, das wirkt
        # komisch auf user"). Im Inno-Protokoll stand sie auf die Millisekunde:
        # 31,4 Sekunden, der Standard-Timeout des Restart Managers.
        #
        # Gestartet wird danach **nichts** mehr von allein — deshalb der Hinweis
        # oben. Fünf Versuche, den Selbststart zum Laufen zu bringen, sind an
        # einer Sicherheitsprüfung von Inno 6.7 gescheitert; ein Doppelklick des
        # Nutzers ist der ehrlichere Weg als ein Fehler, dessen Ursache in der
        # Werkzeugkette liegt.
        if aktualisierung.verpackung() == 'exe':
            _abtreten(fenster)
            return

        # Linux: Das AppImage ist getauscht, laufen tut aber noch die alte
        # Fassung. Hier bleibt der zweite Klick sinnvoll — er beendet und
        # startet neu.
        fenster.sagen(t('s_ub_bereit'))
        fenster.root.after(50, fenster.neu_aufbauen)

    def arbeit():
        try:
            ziel = aktualisierung.herunterladen(
                datei, fortschritt=lambda p: fenster.root.after(
                    0, lambda: fenster.sagen(t('wird_geladen', p))))
            # Weiter im Tk-Faden — dort darf ein Dialog stehen.
            fenster.root.after(0, lambda: einspielen_und_gehen(ziel))
        except Exception as ausnahme:
            grund = str(ausnahme)
            fehler.merken('seiten.fassung_holen', ausnahme)
            fenster.root.after(0, lambda: fenster.sagen(
                t('update_fehler', grund)))

    threading.Thread(target=arbeit, daemon=True).start()


def _kanaele_auffrischen(fenster, kaesten, neu_zeichnen):
    """Im Hintergrund nachsehen und die Knöpfe nachziehen — höchstens einmal.

    Läuft in einem eigenen Faden: Die Abfrage geht ins Netz und darf die Seite
    nicht aufhalten. Gezeichnet wird ausschließlich im Tk-Faden (`after`) — alles
    andere endet früher oder später in einem Absturz.
    """
    import threading
    from . import aktualisierung
    if getattr(kaesten, 'schon_gefragt', False):
        return
    kaesten.schon_gefragt = True
    vorher = (_holen_text(False, fenster.version),
              _holen_text(True, fenster.version))

    def arbeit():
        try:
            # ⚠ `erzwingen=True` ist hier nötig. Ohne das fragt `nachsehen()` nur,
            # wenn der letzte Blick länger als einen Tag her ist — und dann bleibt
            # die Beschriftung auf dem Stand von heute früh stehen. Genau so ist es
            # passiert: Der Knopf bot „v3.0.0-rc13 holen" an, während rc15 lief.
            # Wer draufdrückt, geht **zurück**. Einmal je Seitenaufbau nachfragen
            # ist der Preis dafür, dass draufsteht, was drin ist.
            aktualisierung.nachsehen(fenster.version or '0.0.0', erzwingen=True)
        except Exception as ausnahme:
            fehler.merken('seiten.kanaele_auffrischen', ausnahme)
            return

        def nachziehen():
            try:
                if not kaesten.winfo_exists():
                    return
                if (_holen_text(False, fenster.version),
                        _holen_text(True, fenster.version)) == vorher:
                    return              # nichts Neues, kein Flackern
                for kind in kaesten.winfo_children():
                    kind.destroy()
                neu_zeichnen()
            except tk.TclError:
                pass

        try:
            fenster.root.after(0, nachziehen)
        except Exception:
            pass

    threading.Thread(target=arbeit, daemon=True).start()


def _holen_moeglich(mit_vorab, eigene=''):
    """Steckt hinter dem Knopf ueberhaupt eine Tat? Sonst ist er keiner.

    ⚠ `_holen_text` liefert **nur** die Beschriftung, und zwei ihrer Ergebnisse
    sind gar keine Aufforderung, sondern eine Zustandsmeldung: „v3.0.0-rc41 ist
    schon da" und „Erst oben auf ‚Jetzt nachsehen' druecken". Der Knopf blieb
    trotzdem ein Knopf — wer auf „ist schon da" drueckte, bekam die laufende
    Fassung noch einmal installiert. der Autor am 26.08.2026: „in dem gruenen
    kasten steht aber rc41 ist schon da, wenn man klickt will er auch direkt
    installieren."

    Was aussieht wie ein Knopf, muss etwas tun. Sonst wird daraus ein ruhiger
    Hinweis (siehe `_kanalkasten`).
    """
    from . import aktualisierung
    try:
        freigabe = aktualisierung.neueste(mit_vorab)
    except Exception:
        return False
    if not freigabe:
        return False                     # „Erst oben auf ... druecken"
    fassung = freigabe.get('version') or ''
    # Nach einem geglueckten Update steht dort „Jetzt neu starten" — das ist
    # sehr wohl eine Tat.
    if _BEREIT[0] and _BEREIT[0] == fassung:
        return True
    if eigene and fassung.lstrip('v') == eigene.lstrip('v'):
        return False                     # laeuft schon, nichts zu holen
    return True



def _holen_text(mit_vorab, eigene=''):
    """Die Beschriftung des Knopfes — mit der Fassung, die dahinter steckt.

    Aus dem Zwischenspeicher, ohne ins Netz zu gehen: Die Seite soll sofort
    stehen. Kurz darauf frischt `_kanaele_auffrischen` sie auf.

    ⚠ Und sie sagt, **wohin** es geht. „v2.0.0 holen" neben einer laufenden
    v3.0.0-rc15 sieht aus wie ein Update und ist ein Rückschritt — der Autor ist
    am 25.08.2026 genau darauf hereingefallen und stand danach wieder auf rc13.
    Ist die angebotene Fassung älter, steht das jetzt dabei; ist es dieselbe,
    steht das auch da.
    """
    from . import aktualisierung
    try:
        freigabe = aktualisierung.neueste(mit_vorab)
    except Exception:
        freigabe = None
    if not freigabe:
        return t('s_ub_holen_keine')
    fassung = freigabe.get('version') or ''
    # Nach einem geglückten Update ist die neue Fassung auf der Platte, aber der
    # laufende Prozess hält noch die alte. Statt „beim nächsten Start" zu sagen,
    # wird der Knopf zum Neustart-Knopf.
    if _BEREIT[0] and _BEREIT[0] == fassung:
        return t('s_ub_neustart')
    if eigene:
        sauber = fassung.lstrip('v')
        if sauber == eigene.lstrip('v'):
            return t('s_ub_holen_gleich') % fassung
        if aktualisierung.ist_neuer(eigene, fassung):
            return t('s_ub_holen_zurueck') % fassung
    return t('s_ub_holen') % fassung


# Welche Fassung geholt und eingespielt wurde und nur noch einen Neustart braucht.
_BEREIT = [None]


def _abtreten(fenster, notausgang=2.0, gleich=400):
    """Den Prozess beenden — verlaesslich, auch wenn Tk schon haengt.

    ⚠ `quit()` allein reicht nicht: Es beendet die Ereignisschleife, nicht den
    Prozess. Gemeldet als „er schliesst das fenster nicht selbst" (Haldjas,
    25.08.2026) — die neue Fassung lief, die alte stand daneben. Also der Reihe
    nach: Fenster zu, Schleife beenden, und wenn nach zwei Sekunden immer noch
    etwas haengt (ein Faden, ein Overlay), hart raus.

    ⚠ Der Notausgang wird **sofort** scharf gestellt, nicht erst im
    `after`-Rueckruf. Stand er dort, hing er an Tk: Feuert der Rueckruf nicht,
    weil die Ereignisschleife schon endete oder das Fenster weg ist, wurde der
    Faden nie gestartet und der Prozess lief weiter — „als haette er nur das
    symbol von der taskleiste gekillt", mit einem halb aufgeraeumten Rest, der
    danach „No such file or directory: ...base_library.zip" meldete.

    Ein eigener Faden haengt an nichts und laeuft in jedem Fall ab.
    """
    import threading
    threading.Timer(notausgang, lambda: os._exit(0)).start()

    def _weg():
        try:
            fenster.root.quit()
            fenster.root.destroy()
        except Exception:
            pass

    try:
        fenster.root.after(gleich, _weg)
    except Exception:
        pass



def _fassung_holen(fenster, mit_vorab):
    """Die neueste Fassung dieses Kanals holen und einspielen.

    ⚠ Nicht `nachsehen()` benutzen: Das meldet nur, was **neuer** ist als die
    laufende Fassung. Wer eine Testfassung fährt und zurück auf die letzte
    fertige will, bekäme damit nichts. `neueste()` fragt den Kanal, nicht den
    Abstand zur eigenen Fassung.

    Heruntergeladen wird in einem eigenen Faden — es sind zwölf Megabyte, und
    das Fenster darf so lange nicht einfrieren.
    """
    import threading
    from . import aktualisierung
    # ⚠ Erst nachsehen, dann greifen. Die Liste der Freigaben steht im
    # Zwischenspeicher und frischt sich nur einmal am Tag auf — ohne diesen
    # Schritt holt der Knopf die Fassung von gestern, obwohl heute eine neuere
    # da ist. Gemessen: Der Knopf bot v3.0.0-rc2 an, während rc7 längst
    # veröffentlicht war.
    try:
        aktualisierung.nachsehen(fenster.version or '0.0.0')
    except Exception as ausnahme:
        fehler.merken('seiten.fassung_holen.nachsehen', ausnahme)
    freigabe = aktualisierung.neueste(mit_vorab)
    if not freigabe:
        fenster.sagen(t('s_ub_holen_keine'))
        return
    # Schon geholt? Dann ist der Knopf jetzt der Neustart-Knopf.
    if _BEREIT[0] and _BEREIT[0] == (freigabe.get('version') or ''):
        fenster.sagen(t('s_ub_startet_neu'))
        if not aktualisierung.neu_starten():
            fenster.sagen(t('s_ub_neustart_nein'))
            return
        _abtreten(fenster)
        return
    art = aktualisierung.verpackung()
    if art == 'quellcode':
        fenster.sagen(t('update_quellcode'))
        return
    datei = aktualisierung.passende_datei(freigabe)
    if not datei:
        fenster.sagen(t('selbst_holen'))
        return

    fenster.sagen(t('s_ub_holen_laeuft') % freigabe.get('version'))

    def arbeit():
        try:
            ziel = aktualisierung.herunterladen(
                datei, fortschritt=lambda p: fenster.root.after(
                    0, lambda: fenster.sagen(t('wird_geladen', p))))
            geklappt, grund = aktualisierung.einspielen(ziel)
            if not geklappt:
                fenster.root.after(0, lambda: fenster.sagen(
                    t('update_fehler', grund)))
                return
            _BEREIT[0] = freigabe.get('version') or ''

            # ⚠ Unter Windows ist hier **Schluss** — kein zweiter Klick mehr.
            #
            # Der Ablauf mit „erst holen, dann auf ‚Jetzt neu starten' druecken"
            # stammt aus der Zeit des Dateitauschs: Damals lag die neue Datei
            # nur bereit, und getauscht wurde beim Beenden. Der Installer
            # dagegen **laeuft schon** — und wartet darauf, dass wir endlich
            # gehen.
            #
            # Genau das hat am 26.08.2026 die lange Pause verursacht, die
            # der Autor gemeldet hat („wieso es solange dauert bis er alles
            # geschlossen hat, das wirkt komisch auf user"). Im Inno-Protokoll
            # steht sie auf die Millisekunde:
            #
            #     09:50:07.869  Shutting down applications using our files.
            #     09:50:39.243  Directory for uninstall files: ...
            #
            # 31,4 Sekunden — der Standard-Timeout des Restart Managers. Er
            # bittet erst hoeflich ums Schliessen und raeumt erst nach Ablauf
            # hart ab. Wer waehrenddessen auf den Knopf schaut, sieht ein
            # Programm, das nichts tut.
            #
            # Treten wir gleich ab, entfaellt das Warten vollstaendig, und der
            # `[Run]`-Abschnitt des Installers faehrt uns danach wieder hoch.
            if art == 'exe':
                fenster.root.after(0, lambda: fenster.sagen(
                    t('s_ub_startet_neu')))
                _abtreten(fenster)
                return

            # Linux: Das AppImage ist getauscht, laufen tut aber noch die alte
            # Fassung. Hier bleibt der zweite Klick sinnvoll — er beendet und
            # startet neu.
            fenster.root.after(0, lambda: fenster.sagen(t('s_ub_bereit')))
            # Den Kasten neu zeichnen, damit aus „holen" ein „Jetzt neu
            # starten" wird — sonst muesste man raten, wie es weitergeht.
            fenster.root.after(50, fenster.neu_aufbauen)
        except Exception as ausnahme:
            grund = str(ausnahme)
            fehler.merken('seiten.fassung_holen', ausnahme)
            fenster.root.after(0, lambda: fenster.sagen(
                t('update_fehler', grund)))

    threading.Thread(target=arbeit, daemon=True).start()


def _kanalkasten(fenster, eltern, titel, text, gewaehlt, tat, marke_text='',
                 untereinander=False, holen=None, holen_text='',
                 holen_aktiv=True):
    """Eine Wahlmöglichkeit als Kasten — wie in der Vorschau.

    Ein Schalter mit „an/aus" beantwortet die Frage nicht, die der Spieler hat:
    *Was bedeutet das für mich?* Zwei Kästen mit je zwei Sätzen tun das.

    ⚠ `untereinander` ist kein Schönheitsgriff. Nebeneinander brauchen die
    beiden Kästen mehr Platz, als die Mindestfensterbreite hergibt — Tk
    verteilt dann nicht etwa gerecht, sondern gibt dem ersten seine volle
    Wunschbreite und quetscht den zweiten auf 49 Pixel zusammen. Gemessen bei
    720×520: 329 Pixel fehlten.
    """
    from .hauptfenster import marke as blase
    from .hauptfenster import rundrahmen
    innen = rundrahmen(eltern, FLAECHE, ACCENT if gewaehlt else LINIE,
                       radius=8, grundfarbe=BG)
    rand = innen.halter
    if untereinander:
        rand.pack(side='top', fill='x', expand=False, pady=(0, 10))
    else:
        rand.pack(side='left', fill='both', expand=True, padx=(0, 10))
    rand.configure(cursor='hand2')
    innen.configure(cursor='hand2')
    innen.leinwand.configure(cursor='hand2')
    leinwand = innen.leinwand

    kopf = tk.Frame(innen, bg=FLAECHE)
    kopf.pack(fill='x', padx=14, pady=(12, 2))
    zeichen.zeile(kopf, 'punkt',
                  farbe=zeichen.GRUEN if gewaehlt else zeichen.GRAU,
                  grund=FLAECHE, schrift=fenster.f_klein
                  ).pack(side='left', padx=(0, 7))
    tk.Label(kopf, text=titel, bg=FLAECHE, fg=FG,
             font=fenster.f_fett).pack(side='left')
    if marke_text:
        blase(kopf, marke_text, GOLD, fenster.f_klein).pack(side='left', padx=8)

    beschreibung = tk.Label(innen, text=text, bg=FLAECHE, fg=SUB,
                            font=fenster.f_klein, anchor='w', justify='left')
    beschreibung.pack(fill='x', padx=14, pady=(0, 12))
    # ⚠ 28 gleicht nur `padx=14` links und rechts aus. Rahmen und Leinwand
    # brauchen darüber hinaus ein paar Pixel, die niemand mitgerechnet hat —
    # gemessen fehlten 5 (tools/randpruefung.py). Mit etwas Luft bricht der Text
    # ein paar Pixel früher um, was niemand sieht, statt abgeschnitten zu
    # werden, was jeder sieht.
    _umbruch(beschreibung, abzug=36)

    for teil in (rand, leinwand, innen, kopf):
        teil.bind('<Button-1>', lambda e: tat())
    for kind in innen.winfo_children() + kopf.winfo_children():
        try:
            kind.bind('<Button-1>', lambda e: tat())
        except Exception:
            pass

    # Der Holen-Knopf ganz unten im Kasten, über die volle Breite. ⚠ **Nach** den
    # Bindungen oben angelegt: Sonst würde ihn die Schleife mit „Kanal wählen"
    # belegen, und ein Klick darauf täte etwas anderes als draufsteht.
    if holen is not None and holen_aktiv:
        knopf = _knopf(fenster, innen, holen_text, holen, stark=gewaehlt)
        knopf.pack(fill='x', padx=14, pady=(0, 12))
    elif holen is not None:
        # Kein Knopf, sondern eine Auskunft: Es gibt gerade nichts zu holen.
        # Gleiche Stelle, gleiche Breite, nur ohne Rahmen und ohne Handzeiger —
        # damit niemand darauf drueckt und sich fragt, warum nichts passiert.
        auskunft = tk.Label(innen, text=holen_text, bg=FLAECHE, fg=SUB,
                            font=fenster.f_klein, anchor='center')
        auskunft.pack(fill='x', padx=14, pady=(4, 16))
        # Ein Klick darauf soll dasselbe tun wie ein Klick auf den Kasten:
        # den Kanal waehlen. Sonst waere hier ein totes Loch im Kasten.
        auskunft.bind('<Button-1>', lambda e: tat())
        auskunft.configure(cursor='hand2')
    return rand


def _serverstatus(fenster, rahmen):
    """Läuft Star Citizen gerade? — was CIG auf seiner Statusseite meldet.

    ⚠ **Erst zeigen, dann holen.** Beim Öffnen steht sofort der letzte bekannte
    Stand da, das Auffrischen läuft im Hintergrund. Wer die Seite öffnet und
    fünfzehn Sekunden auf eine leere Fläche sieht, hält sie für kaputt — und
    genau so lange darf ein Abruf dauern, bevor er aufgibt.

    ⚠ **Der Abruf läuft nie im Tk-Faden.** Ein hängendes Netz würde sonst das
    ganze Fenster einfrieren, Overlay eingeschlossen.
    """
    import threading
    from . import serverstatus

    _ueberschrift(fenster, rahmen, t('hf_serverstatus'), t('s_st_lead'))
    innen = _rollflaeche(rahmen)

    # ⚠ Der Behälter wird hier nur **erzeugt**, gepackt wird er weiter unten —
    # nach dem Knopf. Über `before` einzufügen ging schief: Die Knöpfe sind
    # Leinwände, die ihre Höhe erst über ein Ereignis nachziehen, und der Knopf
    # blieb als leerer grüner Streifen stehen. Die Packreihenfolge einzuhalten
    # ist der ruhigere Weg als sie nachträglich zu drehen.
    behaelter = tk.Frame(innen, bg=BG)

    def zeichnen(lage):
        for kind in behaelter.winfo_children():
            kind.destroy()
        if not lage:
            _fliesstext(behaelter, t('s_st_leer'), fenster.f_klein, pady=(4, 8))
            return

        # --- Kopfzeile, wie oben auf der Statusseite ---
        # Links „Zuletzt aktualisiert vor …", rechts die Zusammenfassung. Die
        # Seite hinterlegt diesen Streifen in der Ampelfarbe; das ist ihr
        # auffälligstes Element und die Antwort auf die eigentliche Frage.
        _kopfstreifen(fenster, behaelter, lage)

        karte = _karte(behaelter, pady=(0, 6))
        tk.Frame(karte, bg=FLAECHE, height=8).pack()
        for sys_ in lage.get('systeme') or []:
            _systemzeile(fenster, karte, sys_)
        tk.Frame(karte, bg=FLAECHE, height=10).pack()

        fuss = _karte(behaelter, pady=(8, 6))
        tk.Frame(fuss, bg=FLAECHE, height=8).pack()
        if lage.get('stand'):
            _wertzeile(fenster, fuss, t('s_st_stand'), _uhrzeit(lage['stand']))
        _wertzeile(fenster, fuss, t('s_st_geholt'), _uhrzeit(lage.get('geholt')))
        _quellzeile(fenster, fuss, t('s_st_quelle'), lage.get('quelle') or '')
        tk.Frame(fuss, bg=FLAECHE, height=10).pack()

        _fliesstext(behaelter, t('s_st_hinweis'), fenster.f_klein, pady=(10, 4))

        # --- „Letzte Meldungen", wie unten auf der Statusseite ---
        # Auch **erledigte**: Wer abends nicht ins Spiel kommt, will sehen, ob
        # es nachmittags eine Wartung gab — nicht nur, ob gerade eine läuft.
        tk.Label(behaelter, text=t('s_st_letzte'), bg=BG, fg=FG,
                 font=fenster.f_titel, anchor='w').pack(fill='x', pady=(22, 6))
        meldungsraum = tk.Frame(behaelter, bg=BG)
        meldungsraum.pack(fill='x')
        _fliesstext(meldungsraum, t('s_st_laedt'), fenster.f_klein, pady=(2, 4))
        _meldungen_laden(fenster, meldungsraum, lage.get('quelle') or '')

    def auffrischen(erzwingen=False):
        if erzwingen:
            fenster.sagen(t('s_st_laedt'))

        def arbeit():
            try:
                lage = serverstatus.lage(erzwingen=erzwingen)
            except Exception as ausnahme:
                fehler.merken('seiten.serverstatus', ausnahme)
                fenster.root.after(0, lambda: fenster.sagen(t('s_st_fehler')))
                return
            fenster.root.after(0, lambda: zeichnen(lage))

        threading.Thread(target=arbeit, daemon=True).start()

    # ⚠ Der Knopf gehört **über** den Inhalt, nicht darunter. Unter der
    # Meldungsliste läge er nach mehreren Bildschirmhöhen Text — niemand rollt
    # nach unten, um eine Schaltfläche zu suchen, die er sofort erwartet.
    # `before` setzt ihn vor den Behälter, obwohl er später erzeugt wird.
    # Der Knopf gehört über den Inhalt: Unter der Meldungsliste läge er nach
    # mehreren Bildschirmhöhen Text, und niemand rollt nach unten, um eine
    # Schaltfläche zu suchen, die er sofort erwartet.
    _knopf(fenster, innen, t('s_st_nachsehen'),
           lambda: auffrischen(True), stark=True).pack(fill='x', pady=(0, 12))
    behaelter.pack(fill='x')

    # --- Der laufende Takt ---
    #
    # Jede Minute ein Blick, ob sich etwas geändert hat. Das ist billig, weil
    # mit ETag gefragt wird: Hat CIG nichts angefasst, kommt ein 304 ohne
    # Inhalt zurück.
    #
    # ⚠ **Neu gezeichnet wird nur, wenn sich wirklich etwas geändert hat.**
    # Sonst würde die Anzeige jede Minute zerlegt und neu aufgebaut — wer
    # gerade eine Meldung liest, verlöre dabei seine Rollposition.
    #
    # ⚠ Der Takt hört auf, sobald die Seite weg ist. Ohne die Prüfung auf
    # `winfo_exists` liefe er weiter, wenn der Nutzer längst woanders ist, und
    # jeder Seitenwechsel legte einen weiteren Takt obendrauf.
    def takt():
        if not behaelter.winfo_exists():
            return

        def arbeit():
            try:
                lage, veraendert = serverstatus.nachfragen()
            except Exception:
                lage, veraendert = None, False
            if veraendert and lage:
                fenster.root.after(0, lambda: behaelter.winfo_exists()
                                   and zeichnen(lage))
            fenster.root.after(TAKT_MS, takt)

        threading.Thread(target=arbeit, daemon=True).start()

    zeichnen(serverstatus.gespeicherte_lage())   # sofort, ohne Netz
    auffrischen()                                # und im Hintergrund nachziehen
    fenster.root.after(TAKT_MS, takt)            # danach im Takt weiter


# Wie oft nachgefragt wird, solange die Seite offen ist. Eine Minute ist
# vertretbar, weil mit ETag gefragt wird und der unveränderte Fall den Server
# fast nichts kostet.
TAKT_MS = 60_000


def _relative_zeit(stempel):
    """„gerade eben", „vor 7 Std.", „vor 2 Monaten" — wie auf der Statusseite.

    Die Seite schreibt das Alter, nicht das Datum („Last updated just now",
    „7h ago"). Das ist die Angabe, die man beim Überfliegen wirklich braucht:
    Ob eine Wartung heute Nachmittag war oder im Juli, sieht man so sofort.
    Das genaue Datum steht daneben in der Fußzeile."""
    import time as _t
    if not stempel:
        return '—'
    alter = max(0, _t.time() - stempel)
    if alter < 90:
        return t('s_st_gerade')
    def form(anzahl, schluessel):
        """Einzahl und Mehrzahl auseinanderhalten — „vor 1 Tagen" ist falsch."""
        if anzahl == 1:
            return t(schluessel + '_1')
        return t(schluessel) % anzahl

    if alter < 3600:
        return form(int(alter // 60), 's_st_vor_min')
    if alter < 86400:
        return form(int(alter // 3600), 's_st_vor_std')
    if alter < 60 * 86400:
        return form(int(alter // 86400), 's_st_vor_tag')
    return form(max(1, int(alter // (30 * 86400))), 's_st_vor_monat')


def _kopfstreifen(fenster, eltern, lage):
    """Der Streifen ganz oben: links das Alter, rechts die Zusammenfassung.

    Bildet nach, was die Statusseite dort zeigt („Last updated just now" /
    „No issues detected"). Es ist die Antwort auf die Frage, wegen der jemand
    die Seite überhaupt öffnet — deshalb steht sie oben und nicht in einer
    Werteliste.

    ⚠ **Kein `rundrahmen`.** Dessen Leinwand bleibt auf ihrer Anfangshöhe,
    wenn der Inhalt nicht mitgemessen wird — der Streifen erschien als leerer
    grüner Rahmen. Ein schlichter Frame mit farbigem Balken am linken Rand
    trägt dieselbe Aussage und kann nicht einklappen.
    """
    farbe = _ampelfarbe(lage)
    streifen = tk.Frame(eltern, bg=FLAECHE)
    streifen.pack(fill='x', pady=(0, 10))
    tk.Frame(streifen, bg=farbe, width=4).pack(side='left', fill='y')

    inhalt = tk.Frame(streifen, bg=FLAECHE)
    inhalt.pack(side='left', fill='x', expand=True, padx=12, pady=10)
    alter = _relative_zeit(lage.get('geholt'))
    tk.Label(inhalt, text=t('s_st_zuletzt') % alter,
             bg=FLAECHE, fg=SUB, font=fenster.f_klein,
             anchor='w').pack(side='left')
    alles_gut = (lage.get('gesamt') or '').lower() == 'operational'
    tk.Label(inhalt, text=t('s_st_ok') if alles_gut else t('s_st_stoerung'),
             bg=FLAECHE, fg=farbe, font=fenster.f_fett,
             anchor='e').pack(side='right')


def _meldungen_laden(fenster, raum, quelle):
    """Die letzten Meldungen holen und einsetzen — im eigenen Faden.

    ⚠ Jeder Volltext ist ein eigener Abruf; beim ersten Mal dauert das ein paar
    Sekunden. Deshalb steht solange „wird geholt" da, statt das Fenster
    festzuhalten."""
    import threading
    from . import serverstatus

    def einsetzen(liste):
        if not raum.winfo_exists():
            return
        for kind in raum.winfo_children():
            kind.destroy()
        if not liste:
            _fliesstext(raum, t('s_st_keine'), fenster.f_klein, pady=(2, 4))
        else:
            for meldung in liste:
                _meldungskarte(fenster, raum, meldung)
        if quelle:
            _quellink(fenster, raum, t('s_st_alle_zeigen'), quelle)

    def arbeit():
        try:
            liste = serverstatus.meldungen(2)
        except Exception as ausnahme:
            fehler.merken('seiten.serverstatus_meldungen', ausnahme)
            liste = []
        fenster.root.after(0, lambda: einsetzen(liste))

    threading.Thread(target=arbeit, daemon=True).start()


def _quellink(fenster, eltern, text, adresse):
    """Ein anklickbarer Verweis als eigene Zeile."""
    link = tk.Label(eltern, text=text, bg=BG, fg=ACCENT, font=fenster.f_klein,
                    anchor='w', cursor='hand2')
    link.pack(fill='x', pady=(10, 4))

    def oeffnen(_=None):
        import webbrowser
        try:
            webbrowser.open(adresse)
        except Exception as ausnahme:
            fehler.merken('seiten.quelle_oeffnen', ausnahme)

    link.bind('<Button-1>', oeffnen)
    link.bind('<Enter>', lambda e: link.configure(fg=FG))
    link.bind('<Leave>', lambda e: link.configure(fg=ACCENT))


def _quellzeile(fenster, eltern, bez, adresse):
    """Wie `_wertzeile`, aber die Adresse lässt sich anklicken.

    Eine Quelle, die man nur ablesen und abtippen kann, ist keine Quelle —
    besonders bei einer Angabe, die man im Zweifel selbst nachprüfen soll."""
    z = tk.Frame(eltern, bg=FLAECHE)
    z.pack(fill='x', padx=16, pady=3)
    tk.Label(z, text=bez, bg=FLAECHE, fg=SUB, font=fenster.f_klein,
             width=24, anchor='w').pack(side='left')
    if not adresse:
        tk.Label(z, text='—', bg=FLAECHE, fg=FG, font=fenster.f_klein,
                 anchor='w').pack(side='left')
        return
    link = tk.Label(z, text=adresse, bg=FLAECHE, fg=ACCENT,
                    font=fenster.f_klein, anchor='w', cursor='hand2')
    link.pack(side='left')

    def oeffnen(_=None):
        import webbrowser
        try:
            webbrowser.open(adresse)
        except Exception as ausnahme:
            fehler.merken('seiten.quelle_oeffnen', ausnahme)

    link.bind('<Button-1>', oeffnen)

    # Rückmeldung beim Darüberfahren über die **Farbe**, nicht über die Schrift.
    #
    # ⚠ `fenster.f_klein` ist ein `tkfont.Font`-Objekt, kein Tupel — `font[0]`
    # wirft. Und ein eigenes, unterstrichenes Font-Objekt anzulegen wäre die
    # zweite Falle: „Schrift größer" stellt zentral genau diese gemeinsamen
    # Objekte um, ein eigenes bliebe stehen und der Link wäre der einzige
    # Text, der nicht mitwächst.
    link.bind('<Enter>', lambda e: link.configure(fg=FG))
    link.bind('<Leave>', lambda e: link.configure(fg=ACCENT))


def _ampelfarbe(lage):
    """Die Farbe der Gesamtlage — die schlechteste, die vorkommt.

    „Alles grün außer einem" ist nicht grün. Wer nur die Zusammenfassung liest,
    soll denselben Eindruck bekommen wie jemand, der die Liste durchgeht."""
    rang = {'ok': 0, 'hinweis': 1, 'gestoert': 2, 'aus': 3}
    schlimmste = None
    for s_ in lage.get('systeme') or []:
        if schlimmste is None or rang.get(s_.get('ampel'), 2) > rang.get(schlimmste.get('ampel'), 2):
            schlimmste = s_
    return (schlimmste or {}).get('farbe') or FG


def _systemzeile(fenster, eltern, sys_):
    """Ein System: Farbbalken, Name, Zustand im Wortlaut von CIG."""
    z = tk.Frame(eltern, bg=FLAECHE)
    z.pack(fill='x', padx=16, pady=3)
    # Der Balken trägt die Aussage für alle, die Farben schlecht unterscheiden,
    # zusammen mit dem ausgeschriebenen Zustand daneben — nie die Farbe allein.
    tk.Frame(z, bg=sys_.get('farbe') or FG, width=4, height=18).pack(
        side='left', padx=(0, 10))
    # ⚠ Beides sind **Daten von CIG**, kein Oberflächentext: Systemname und
    # Zustand stehen so auf der Statusseite und dürfen nicht übersetzt werden.
    # Vorher entnommen, damit die Textprüfung die Schlüssel nicht für Sätze hält.
    name = sys_.get('name') or '?'
    zustand = sys_.get('status') or '—'
    tk.Label(z, text=name, bg=FLAECHE, fg=FG,
             font=fenster.f_klein, width=22, anchor='w').pack(side='left')
    tk.Label(z, text=zustand, bg=FLAECHE,
             fg=sys_.get('farbe') or FG, font=fenster.f_klein,
             anchor='w').pack(side='left')


def _meldungskarte(fenster, eltern, meldung):
    """Eine Meldung im Aufbau der Statusseite.

        Live Deployment                              ✔ Erledigt
        vor 7 Std.
        maintenance          Persistent Universe · Arena Commander
        <Meldungstext, Update-Zeilen im Original>

    ⚠ Der Text bleibt im **Wortlaut von CIG**, auch die Update-Zeilen
    (`1415 UTC - Initial Notice, Matchmaking disabled.`). Übersetzt wäre es eine
    Aussage, die RSI nie gemacht hat — und bei einer Störungsmeldung ist genau
    das gefährlich."""
    karte = _karte(eltern, pady=(6, 2))
    tk.Frame(karte, bg=FLAECHE, height=10).pack()

    # Kopf: Titel links, Zustand rechts
    kopf = tk.Frame(karte, bg=FLAECHE)
    kopf.pack(fill='x', padx=16)
    # Der Titel kommt von CIG und bleibt, wie er dort steht.
    titel = meldung.get('titel') or '—'
    tk.Label(kopf, text=titel, bg=FLAECHE, fg=FG,
             font=fenster.f_fett, anchor='w').pack(side='left')
    erledigt = bool(meldung.get('erledigt'))
    tk.Label(kopf, text=(t('s_st_erledigt_kurz')) if erledigt
             else t('s_st_offen'),
             bg=FLAECHE,
             # Erledigt grün wie auf der Statusseite; offen in Gold, damit es
             # auffällt — eine laufende Störung ist der Grund, warum jemand
             # überhaupt hier nachsieht.
             fg=(ACCENT if erledigt else GOLD),
             font=fenster.f_klein, anchor='e').pack(side='right')

    # Alter — wie auf der Seite („7h ago"), nicht das Datum
    wann = _relative_zeit(meldung.get('begonnen'))
    tk.Label(karte, text=wann, bg=FLAECHE,
             fg=SUB, font=fenster.f_klein, anchor='w').pack(
                 fill='x', padx=16, pady=(2, 6))

    # Etiketten: Schweregrad links, betroffene Systeme rechts — wie auf der Seite
    _etikettenreihe(fenster, karte, meldung.get('schwere'),
                    meldung.get('betroffen') or [])

    # ⚠ `fill='x'` ist Pflicht. Das Label ist zwar linksbündig gesetzt, aber
    # ohne Füllung zentriert Tk es als Ganzes im Kasten — der Meldungstext
    # stand mittig statt links und sah dadurch nicht aus wie auf der Seite.
    # ⚠ `fill='x'` ist Pflicht. Das Label ist zwar linksbündig gesetzt, aber
    # ohne Füllung zentriert Tk es als Ganzes im Kasten — der Meldungstext
    # stand mittig statt links.
    #
    # Die Hervorhebung kommt aus dem Quelltext von CIG mit: Dort steht fett,
    # was man tun soll („Fahrzeuge sichern"). Ältere Zwischenspeicher führen
    # noch reine Zeichenketten — die werden weiter vertragen, statt beim ersten
    # Start nach dem Update eine Ausnahme zu werfen.
    for eintrag in (meldung.get('zeilen') or []):
        if isinstance(eintrag, (list, tuple)):
            zeile, fett = eintrag[0], bool(eintrag[1])
        else:
            zeile, fett = eintrag, False
        _fliesstext(karte, zeile,
                    fenster.f_fett if fett else fenster.f_klein,
                    farbe=FG if fett else SUB, grund=FLAECHE,
                    fill='x', padx=16, pady=(0, 3), abzug=48)
    tk.Frame(karte, bg=FLAECHE, height=10).pack()


def _etikett(fenster, eltern, text):
    """Ein kleines graues Schild, wie die Marken auf der Statusseite.

    ⚠ **Bewusst kein `rundrahmen`.** Der setzt seinen Inhalt per
    `create_window` auf eine Leinwand — dadurch trägt der Inhalt nicht zur
    Wunschgröße bei, das Schild hat keine eigene Breite und dehnt sich über
    die halbe Karte. Bei großen Kästen fällt das nicht auf, hier schon: Aus
    kompakten Marken wurden Balken. Ein schlichtes Label kennt seine Größe.
    """
    return tk.Label(eltern, text=text, bg=LINIE, fg=FG, font=fenster.f_klein,
                    padx=8, pady=3)


def _etikettenreihe(fenster, eltern, schwere, betroffen):
    """Die Etiketten einer Meldung — **warum** links, **was betroffen ist** rechts.

    Die Trennung ist keine Kosmetik, sie trägt die Aussage: Links steht der
    Grund (`Maintenance`, `Degraded Performance`), rechts stehen die Systeme,
    die es trifft. Stehen alle drei gleichrangig nebeneinander, ist es
    Einheitsbrei und man muss raten, was wovon abhängt.

    ⚠ **Zwei Fallen, beide schon zugeschnappt:**

      Nebeneinander gepackt fällt heraus, wofür der Platz nicht reicht — auf
      der Seite standen drei Marken, im Werkzeug nur zwei. Tk warnt dabei nicht.

      Und ein reiner Fließumbruch behebt zwar das, ebnet aber die Trennung ein.

    Deshalb zwei Ebenen: Grund und Systemblock rücken untereinander, sobald sie
    nicht mehr nebeneinander passen — die Trennung bleibt dann als *oben und
    unten* erhalten. Innerhalb des Systemblocks bricht `grid` die Systeme
    weiter um, sodass auch bei sehr schmalem Fenster keines verschwindet.
    """
    reihe = tk.Frame(eltern, bg=FLAECHE)
    reihe.pack(fill='x', padx=16, pady=(0, 6))

    ABSTAND = 6

    grund = _etikett(fenster, reihe, schwere) if schwere else None

    systeme = tk.Frame(reihe, bg=FLAECHE)
    schilder = [_etikett(fenster, systeme, name) for name in (betroffen or [])]
    if not grund and not schilder:
        return

    def systeme_ordnen(platz):
        """Die Systeme fließend umbrechen — keines darf herausfallen."""
        zeile, spalte, belegt = 0, 0, 0
        for schild in schilder:
            breite = schild.winfo_reqwidth() + ABSTAND
            # Das erste Schild einer Zeile bleibt immer stehen, auch wenn es
            # allein schon zu breit ist. Abschneiden wäre genau der Fehler,
            # den diese Funktion behebt.
            if spalte and belegt + breite > max(platz, 1):
                zeile, spalte, belegt = zeile + 1, 0, 0
            schild.grid(row=zeile, column=spalte, sticky='w',
                        padx=(0, ABSTAND), pady=2)
            spalte += 1
            belegt += breite

    def ordnen(_=None):
        platz = reihe.winfo_width()
        if platz <= 1:
            platz = reihe.winfo_toplevel().winfo_width()
        breite_grund = (grund.winfo_reqwidth() + ABSTAND * 2) if grund else 0
        breite_systeme = sum(s.winfo_reqwidth() + ABSTAND for s in schilder)
        nebeneinander = breite_grund + breite_systeme <= platz

        if nebeneinander == getattr(reihe, 'zuletzt_nebeneinander', None):
            return
        reihe.zuletzt_nebeneinander = nebeneinander

        if grund:
            grund.pack_forget()
        systeme.pack_forget()

        if nebeneinander:
            if grund:
                grund.pack(side='left', padx=(0, ABSTAND))
            systeme.pack(side='right')
            systeme_ordnen(breite_systeme)          # alles in eine Zeile
        else:
            if grund:
                grund.pack(side='top', anchor='w', pady=(0, 4))
            systeme.pack(side='top', anchor='w', fill='x')
            systeme_ordnen(platz)

    reihe.bind('<Configure>', ordnen, add='+')
    reihe.after(0, ordnen)


def _uhrzeit(stempel):
    """Ein Zeitpunkt als Ortszeit. Die Quelle rechnet in UTC — hier steht,
    was die Uhr des Nutzers zeigt, sonst rechnet jeder selbst um."""
    import time as _t
    if not stempel:
        return '—'
    return _t.strftime('%d.%m.%Y %H:%M', _t.localtime(stempel))


def _dankblock(fenster, eltern, name, lizenz, was, adresse=None):
    """Ein Beitrag: wer, unter welcher Lizenz, wofür — und wo er zu finden ist."""
    kasten = tk.Frame(eltern, bg=FLAECHE)
    kasten.pack(fill='x', pady=(0, 8))

    from .hauptfenster import marke as blase
    kopf = tk.Frame(kasten, bg=FLAECHE)
    kopf.pack(fill='x', padx=16, pady=(12, 2))
    tk.Label(kopf, text=name, bg=FLAECHE, fg=FG, font=fenster.f_fett,
             anchor='w').pack(side='left')
    # Die Lizenz als Blase daneben — sie gehört zum Namen, nicht in den Fließtext.
    blase(kopf, lizenz, ACCENT, fenster.f_klein).pack(side='left', padx=8)

    text = tk.Label(kasten, text=was, bg=FLAECHE, fg=SUB, font=fenster.f_klein,
                    anchor='w', justify='left')
    text.pack(fill='x', padx=16, pady=(0, 10))
    _umbruch(text)

    if adresse:
        # ⚠ Nicht `_quellzeile`: die reserviert 24 Zeichen für eine
        # Beschriftung, und ohne Beschriftung stünde der Verweis eingerückt
        # mitten in der Karte statt am linken Rand wie der Text darüber.
        link = tk.Label(kasten, text=adresse, bg=FLAECHE, fg=ACCENT,
                        font=fenster.f_klein, anchor='w', cursor='hand2')
        link.pack(fill='x', padx=16, pady=(0, 12))

        def oeffnen(_=None):
            import webbrowser
            try:
                webbrowser.open(adresse)
            except Exception as ausnahme:
                fehler.merken('seiten.danke_link', ausnahme)

        link.bind('<Button-1>', oeffnen)
        link.bind('<Enter>', lambda e: link.configure(fg=FG))
        link.bind('<Leave>', lambda e: link.configure(fg=ACCENT))


def _danke(fenster, rahmen):
    """Wem was gehört — und Dank an die, ohne die es das Werkzeug nicht gäbe.

    ⚠ Diese Seite gibt es seit v3.0.0-rc58. Vorher stand im ganzen Programm
    **keine** Lizenzangabe: weder die eigene (GPL-3.0) noch die der Symbole. Bei
    einem GPL-Programm gehört die eigene Lizenz sichtbar hin, und die
    ISC-Lizenz von Lucide verlangt, dass ihr Hinweis mitgeliefert wird — eine
    Datei tief in der entpackten `.exe` erfüllt das formal, findet aber niemand.

    Ein **eigener Reiter** statt eines Abschnitts auf „Update & Über": Die Seite
    dort ist mit Fassung, Katalogzahlen, Update-Kanal und Holen-Knopf schon voll,
    und wem was gehört, hat mit Updates nichts zu tun. der Autor am 27.08.2026:
    „fremdleistungen gehören doch als eigener tab ehr in info oder?"
    """
    _ueberschrift(fenster, rahmen, t('hf_danke'), t('s_dk_lead'))
    innen = _rollflaeche(rahmen)

    # --- Das Programm selbst ---
    tk.Label(innen, text=t('s_dk_selbst'), bg=BG, fg=FG, font=fenster.f_titel,
             anchor='w').pack(fill='x', pady=(0, 2))
    _fliesstext(innen, t('s_dk_selbst_h'), fenster.f_klein, fill='x',
                pady=(0, 10))
    _dankblock(fenster, innen, 'SC BP Watcher', 'GPL-3.0-only',
               'der Autor', 'https://github.com/Xharig-1/SC-BP-Watcher')

    # --- Mitgeliefert ---
    tk.Label(innen, text=t('s_dk_dabei'), bg=BG, fg=FG, font=fenster.f_titel,
             anchor='w').pack(fill='x', pady=(18, 2))
    _fliesstext(innen, t('s_dk_dabei_h'), fenster.f_klein, fill='x',
                pady=(0, 10))
    _dankblock(fenster, innen, 'Lucide', 'ISC', t('s_dk_symbole'),
               'https://lucide.dev')

    # --- Wird geladen, nicht mitgeliefert ---
    tk.Label(innen, text=t('s_dk_extern'), bg=BG, fg=FG, font=fenster.f_titel,
             anchor='w').pack(fill='x', pady=(18, 2))
    _fliesstext(innen, t('s_dk_extern_h'), fenster.f_klein, fill='x',
                pady=(0, 10))
    _dankblock(fenster, innen, 'Star Citizen Mission DataBase',
               'CC BY-NC-ND 4.0', t('s_dk_scmdb'), 'https://scmdb.net')
    _dankblock(fenster, innen, 'StarStrings (MrKraken)', 'CC BY-NC-SA 4.0',
               t('s_dk_ss'), 'https://starstrings.app')
    _dankblock(fenster, innen, 'SC Deutsch Launcher', t('s_dk_freiwillig'),
               t('s_dk_scdl'), 'https://www.sc-deutsch-launcher.de/')

    # --- Menschen ---
    tk.Label(innen, text=t('s_dk_leute'), bg=BG, fg=FG, font=fenster.f_titel,
             anchor='w').pack(fill='x', pady=(18, 2))
    _fliesstext(innen, t('s_dk_leute_h'), fenster.f_klein, fill='x',
                pady=(0, 10))
    _dankblock(fenster, innen, 'Haldjas', 'pr0citizen', t('s_dk_haldjas'))
    _dankblock(fenster, innen, 'Morkhan', t('s_dk_tester'), t('s_dk_morkhan'))

    # --- Marken ---
    _fliesstext(innen, t('s_dk_marken'), fenster.f_klein, fill='x',
                pady=(18, 20))


def _ueber(fenster, rahmen):
    from . import pfade
    _ueberschrift(fenster, rahmen, t('hf_ueber'), t('s_ub_lead'))
    innen = _rollflaeche(rahmen)

    # --- Zustand ---
    karte = _karte(innen, pady=(0, 6))
    tk.Frame(karte, bg=FLAECHE, height=8).pack()
    _wertzeile(fenster, karte, t('s_ub_fassung'), fenster.version or '—', ACCENT)
    _wertzeile(fenster, karte, t('s_ub_bekannt'), _zahl_katalog())
    _wertzeile(fenster, karte, t('s_ub_davon'), _zahl_bestand())
    uebersicht = {}
    try:
        uebersicht = pfade.uebersicht() or {}
    except Exception:
        pass
    _wertzeile(fenster, karte, t('b_ordner'),
               uebersicht.get('app_ordner') or '—')
    tk.Frame(karte, bg=FLAECHE, height=10).pack()

    reihe = tk.Frame(innen, bg=BG)
    reihe.pack(fill='x', pady=(10, 4))
    _knopfreihe(reihe, [
        _knopf(fenster, reihe, t('s_ub_nachsehen'),
               lambda: _jetzt_nachsehen(fenster), stark=True),
        _knopf(fenster, reihe, t('hf_wasistneu'),
               lambda: fenster.oeffnen('wasistneu')),
        _knopf(fenster, reihe, t('s_ub_einrichtung'), fenster._einrichtung),
    ])

    ziel = _feld(fenster, innen, t('s_ub_taeglich'), t('s_ub_taeglich_h'))
    _schalter(fenster, ziel, 'update_pruefen', True)

    # --- Einmal holen, ohne etwas umzustellen ---
    #
    # ⚠ Der häufigste Wunsch ist der einfachste: „gib mir die neueste, egal
    # welche". Bisher musste man dafür erst verstehen, was ein Kanal ist, und
    # den richtigen Kasten anklicken. Morkhan am 26.08.2026 dazu: „das ist
    # verwirrend" — er hatte den falschen gewählt und bekam gar nichts.
    #
    # Dieser Knopf beantwortet den Wunsch direkt, ohne dass jemand eine
    # Entscheidung treffen muss, die er nicht treffen will. Die Kästen darunter
    # bleiben für alle, die es genauer steuern wollen.
    _fliesstext(innen, t('s_up_sofort_h'), fenster.f_klein,
                pady=(14, 6))
    _knopf(fenster, innen, t('s_up_sofort'),
           lambda: _fassung_holen(fenster, True),
           stark=True).pack(fill='x', pady=(0, 6))

    # --- Testkanal: zwei Kästen statt eines Schalters ---
    tk.Label(innen, text=t('s_ub_kanal'), bg=BG, fg=FG,
             font=fenster.f_titel, anchor='w').pack(fill='x', pady=(24, 2))
    _fliesstext(innen, t('s_ub_kanal_h'), fenster.f_klein,
                fill='x', pady=(0, 12))

    kaesten = tk.Frame(innen, bg=BG)
    kaesten.pack(fill='x')

    def kanal_setzen(wert):
        pfade.einstellung_setzen('vorabversionen', wert)
        fenster.sagen(t('e_vorab') + ': ' + (t('e_an') if wert else t('e_aus')))
        for kind in kaesten.winfo_children():
            kind.destroy()
        kanal_zeichnen()

    # Unterhalb dieser Breite stehen die beiden Kästen untereinander. 620 ist
    # gemessen, nicht geschätzt: Darunter reicht der Platz nicht mehr für zwei
    # nebeneinander, und Tk quetscht den zweiten zusammen, statt umzubrechen.
    SCHMAL = 620

    def kanal_zeichnen():
        an = pfade.einstellung_wahrheit('vorabversionen', False)
        breite = kaesten.winfo_width()
        # Vor dem ersten Zeichnen meldet Tk eine 1 — dann entscheidet das
        # Fenster, nicht der Platzhalter.
        if breite <= 1:
            breite = kaesten.winfo_toplevel().winfo_width()
        eng = breite < SCHMAL
        kaesten.zuletzt_eng = eng
        _kanalkasten(fenster, kaesten, t('s_ub_fertig'), t('s_ub_fertig_h'),
                     not an, lambda: kanal_setzen(False), untereinander=eng,
                     holen=lambda: _fassung_holen(fenster, False),
                     holen_text=_holen_text(False, fenster.version),
                     holen_aktiv=_holen_moeglich(False, fenster.version))
        _kanalkasten(fenster, kaesten, t('s_ub_test'), t('s_ub_test_h'),
                     an, lambda: kanal_setzen(True), marke_text='rc',
                     untereinander=eng,
                     holen=lambda: _fassung_holen(fenster, True),
                     holen_text=_holen_text(True, fenster.version),
                     holen_aktiv=_holen_moeglich(True, fenster.version))
        # ⚠ Die Beschriftungen kommen aus dem Zwischenspeicher, damit die Seite
        # sofort steht. Der frischt sich aber nur einmal am Tag auf — auf einem
        # Bildschirmfoto vom 25.08.2026 bot der Knopf „v3.0.0-rc9 holen" an,
        # während rc12 lief und rc13 schon draußen war. Der Knopf holt zwar die
        # richtige Fassung (er sieht vorher nach), aber was draufsteht, führt in
        # die Irre. Deshalb einmal im Hintergrund nachsehen und die Kästen neu
        # zeichnen, wenn sich etwas geändert hat.
        _kanaele_auffrischen(fenster, kaesten, kanal_zeichnen)

    def kanal_pruefen(_=None):
        """Nur neu bauen, wenn die Anordnung wirklich kippt — sonst flackert es."""
        eng = kaesten.winfo_width() < SCHMAL
        if eng != getattr(kaesten, 'zuletzt_eng', None):
            for kind in kaesten.winfo_children():
                kind.destroy()
            kanal_zeichnen()

    kanal_zeichnen()
    kaesten.bind('<Configure>', kanal_pruefen, add='+')

    # --- Wer das gebaut hat ---
    tk.Label(innen, text=t('hf_wer'), bg=BG, fg=FG, font=fenster.f_titel,
             anchor='w').pack(fill='x', pady=(28, 2))
    tk.Label(innen, text=t('s_ub_wer_h'), bg=BG, fg=SUB, font=fenster.f_klein,
             anchor='w').pack(fill='x', pady=(0, 12))

    autor = _karte(innen)
    zeile = tk.Frame(autor, bg=FLAECHE)
    zeile.pack(fill='x', padx=16, pady=14)
    from .hauptfenster import _mitgeliefert
    logo = _mitgeliefert(os.path.join('assets', 'xharig.png'))
    if logo and os.path.exists(logo):
        try:
            voll = tk.PhotoImage(file=logo)
            teiler = max(1, voll.width() // 64)
            fenster._autorlogo = voll.subsample(teiler, teiler)
            tk.Label(zeile, image=fenster._autorlogo, bg=FLAECHE).pack(
                side='left', padx=(0, 16))
        except Exception as ausnahme:
            fehler.merken('seiten.ueber.logo', ausnahme)
    rechts = tk.Frame(zeile, bg=FLAECHE)
    rechts.pack(side='left', fill='x', expand=True)
    tk.Label(rechts, text='Xharig', bg=FLAECHE, fg=ACCENT, font=fenster.f_titel,
             anchor='w').pack(fill='x')
    tk.Label(rechts, text='SC BP Watcher %s · GPL-3.0-only'
             % (fenster.version or ''), bg=FLAECHE, fg=SUB,
             font=fenster.f_klein, anchor='w').pack(fill='x')
    _adresse(fenster, rechts, 'github.com/Xharig-1/SC-BP-Watcher',
             'https://github.com/Xharig-1/SC-BP-Watcher')

    dank = _karte(innen, pady=(10, 0))
    tk.Label(dank, text=t('hf_dank'), bg=FLAECHE, fg=FG, font=fenster.f_klein,
             anchor='w').pack(fill='x', padx=16, pady=(12, 6))
    for quelle, wofuer in (('scmdb.net', t('s_ub_q_katalog')),
                           ('rjcncpt / SC Deutsch Launcher',
                            t('s_ub_q_uebersetzung')),
                           ('MrKraken · StarStrings',
                            t('s_ub_q_vorbild'))):
        z = tk.Frame(dank, bg=FLAECHE)
        z.pack(fill='x', padx=16, pady=1)
        tk.Label(z, text='·', bg=FLAECHE, fg=SUB,
                 font=fenster.f_klein).pack(side='left', padx=(0, 6))
        tk.Label(z, text=quelle, bg=FLAECHE, fg=FG,
                 font=fenster.f_klein).pack(side='left')
        tk.Label(z, text=' — ' + wofuer, bg=FLAECHE, fg=SUB,
                 font=fenster.f_klein).pack(side='left')
    _fliesstext(dank, t('hf_nichts_dabei'), fenster.f_klein,
                grund=FLAECHE, abzug=32, fill='x', padx=16, pady=(8, 12))

    _fliesstext(innen, t('hf_fancontent'), fenster.f_klein,
                fill='x', pady=(14, 24))


def _adresse(fenster, eltern, text, ziel, grund=None):
    """Eine anklickbare Adresse — öffnet den Browser.

    ⚠ Vorher war das ein gewöhnliches Label in der Akzentfarbe: Es **sah aus wie
    ein Link** und tat nichts. Das ist schlimmer als schwarzer Text, weil es zum
    Klicken einlädt. Jetzt ist der Mauszeiger eine Hand, die Adresse unterstreicht
    sich beim Überfahren, und ein Klick öffnet sie.
    """
    grund = grund or FLAECHE
    lbl = tk.Label(eltern, text=text, bg=grund, fg=ACCENT, font=fenster.f_klein,
                   anchor='w', cursor='hand2')
    lbl.pack(fill='x', pady=(4, 0))

    def oeffnen(_=None):
        import webbrowser
        try:
            # Im AppImage zeigen unsere eigenen Bibliothekspfade auf das entpackte
            # Paket; ein daraus gestarteter Browser stirbt sofort. Deshalb dieselbe
            # saubere Umgebung wie beim Ordner-Öffnen.
            umgebung_alt = dict(os.environ)
            os.environ.clear()
            os.environ.update(saubere_umgebung())
            try:
                geklappt = webbrowser.open(ziel)
            finally:
                os.environ.clear()
                os.environ.update(umgebung_alt)
        except Exception as ausnahme:
            fehler.merken('seiten.adresse', ausnahme, ziel)
            geklappt = False
        fenster.sagen(t('s_ub_auf') % ziel if geklappt else t('s_ub_auf_nein') % ziel)

    def rein(_=None):
        lbl.configure(font=_unterstrichen(fenster.f_klein))

    def raus(_=None):
        lbl.configure(font=fenster.f_klein)

    lbl.bind('<Button-1>', oeffnen)
    lbl.bind('<Enter>', rein)
    lbl.bind('<Leave>', raus)
    return lbl


def _unterstrichen(schrift):
    """Dieselbe Schrift, nur unterstrichen — für die Maus-über-Anzeige."""
    import tkinter.font as tkfont
    try:
        kopie = tkfont.Font(font=schrift)
        kopie.configure(underline=True)
        return kopie
    except tk.TclError:
        return schrift


def _schalter(fenster, eltern, schluessel, standard):
    """Ein An/Aus-Schalter, der sofort schreibt — es gibt keinen Speichern-Knopf."""
    from . import pfade
    k = tk.Label(eltern, text='', bg=FLAECHE, font=fenster.f_klein,
                 cursor='hand2', padx=10, pady=4)
    k.pack()

    def zeichnen():
        an = pfade.einstellung_wahrheit(schluessel, standard)
        k.configure(text=' %s ' % (t('e_an') if an else t('e_aus')),
                    fg=ACCENT if an else SUB)

    def umschalten():
        neu = not pfade.einstellung_wahrheit(schluessel, standard)
        pfade.einstellung_setzen(schluessel, neu)
        zeichnen()
        fenster.sagen(t('e_an') if neu else t('e_aus'))

    k.bind('<Button-1>', lambda e: umschalten())
    zeichnen()
    return k


def _erkennung(fenster, rahmen):
    from . import katalog as katalog_modul, pfade, phrasen
    _ueberschrift(fenster, rahmen, t('hf_erkennung'), t('s_er_lead'))
    innen = _rollflaeche(rahmen)

    ziel = _feld(fenster, innen, t('s_er_takt'), t('s_er_takt_h'))
    reihe = tk.Frame(ziel, bg=BG)
    reihe.pack()
    from .hauptfenster import rundes_feld
    zahl = rundes_feld(reihe, None, fenster.f_klein, '#0c1017', LINIE, ACCENT, FG,
                       breite=5, justify='right')
    zahl.insert(0, str(pfade.einstellung_zahl('pruefintervall_sekunden', 3, 1, 60)))
    zahl.halter.pack(side='left')
    tk.Label(reihe, text=t('s_er_sek'), bg=BG, fg=SUB,
             font=fenster.f_klein).pack(side='left')

    def takt_merken(_=None):
        try:
            pfade.einstellung_setzen('pruefintervall_sekunden',
                                     max(1, min(60, int(zahl.get()))))
            fenster.sagen(t('s_er_takt_sagen') % zahl.get())
        except ValueError:
            pass

    zahl.bind('<FocusOut>', takt_merken)
    zahl.bind('<Return>', takt_merken)

    # ⚠ `breit=True`: Die gefundenen Sätze sind lang. Rechts neben der
    # Beschreibung lief der Kasten über die Fensterkante hinaus und war an
    # beiden Enden abgeschnitten — lesbar war weder Anfang noch Ende.
    ziel = _feld(fenster, innen, t('s_er_satz'), t('s_er_satz_h'),
                 breit=True)
    # ⚠ `sammeln()` gibt ein Paar zurueck: die Liste der Saetze und woher sie
    # stammt. Wer das Paar einfach zusammenschreibt, bekommt rohe
    # Python-Schreibweise ins Fenster — eckige Klammern, Anfuehrungszeichen,
    # am Ende ein loses „tabelle". Genau so stand es dort.
    gefunden = '—'
    try:
        saetze, woher = phrasen.sammeln()
        gefunden = ' · '.join(str(x) for x in (saetze or [])) or '—'
    except Exception as ausnahme:
        fehler.merken('seiten.erkennung.phrasen', ausnahme)
    kasten = _karte(ziel)
    _fliesstext(kasten, gefunden, fenster.f_klein, farbe=FG,
                grund=FLAECHE, abzug=24, fill='x', padx=12, pady=8)

    ziel = _feld(fenster, innen, t('s_er_kat'), t('s_er_kat_h'))

    def katalog_neu():
        fenster.sagen(t('s_er_kat_holt'))
        try:
            katalog_modul.aktualisieren()
            fenster.sagen(t('s_er_kat_da') % _zahl_katalog())
        except Exception as ausnahme:
            fehler.merken('seiten.erkennung.katalog', ausnahme)
            fenster.sagen(t('s_er_kat_weg'))

    _knopf(fenster, ziel, t('s_er_kat_jetzt'), katalog_neu).pack()

    ziel = _feld(fenster, innen, t('s_er_alt'), t('s_er_alt_h'))

    def nachlesen():
        try:
            os.remove(pfade.app_datei('logstand.json'))
        except OSError:
            pass
        fenster.sagen(t('s_er_alt_ok'))

    _knopf(fenster, ziel, t('s_er_alt_knopf'), nachlesen).pack()


def _diagnose(fenster, rahmen):
    from . import pfade
    from .hauptfenster import schiebeschalter
    _ueberschrift(fenster, rahmen, t('hf_diagnose'), t('s_di_lead'))
    innen = _rollflaeche(rahmen)

    text = ''
    try:
        text = bericht.bauen(version=fenster.version, wurzel=fenster.root)
    except Exception as ausnahme:
        fehler.merken('seiten.diagnose', ausnahme)

    from .hauptfenster import rundrahmen
    kasten = rundrahmen(innen, '#0c1017', LINIE, radius=8, grundfarbe=BG)
    kasten.halter.pack(fill='both', expand=True)
    # ⚠ `highlightthickness` steht bei Text und Entry auf 1 und wird auf dem
    # Mac als helle Linie gezeichnet — im runden Kasten sah das aus wie ein
    # zweiter, eckiger Rahmen. `relief='flat'` und `bd=0` schalten das NICHT ab.
    feld = tk.Text(kasten, bg='#0c1017', fg=FG, font=('Consolas', 10),
                   height=16, wrap='none', relief='flat', bd=0,
                   highlightthickness=0, insertbackground=FG, padx=14, pady=12)
    feld.pack(fill='both', expand=True)
    feld.insert('1.0', text)
    feld.configure(state='disabled')

    reihe = tk.Frame(innen, bg=BG)
    reihe.pack(fill='x', pady=(12, 0))

    def melden():
        if bericht.issue_oeffnen(text):
            fenster.sagen(t('s_di_browser_ok'))
        else:
            fenster.sagen(t('s_di_browser_weg'))

    def kopieren():
        if bericht.in_die_ablage(text, fenster.root):
            fenster.sagen(t('s_di_kopiert'))

    def speichern():
        ziel_datei = bericht.speichern(text)
        fenster.sagen(t('s_di_gespeichert') % os.path.basename(ziel_datei)
                      if ziel_datei else t('s_di_speich_weg'))

    _knopfreihe(reihe, [
        _knopf(fenster, reihe, t('s_di_melden'), melden, stark=True),
        _knopf(fenster, reihe, t('s_di_kopieren'), kopieren),
        _knopf(fenster, reihe, t('s_di_speichern'), speichern),
        _knopf(fenster, reihe, t('s_di_ordner'),
               lambda: _ordner_zeigen(pfade.app_ordner())),
    ])

    _status(fenster, innen, 'haken', t('s_di_sicher'), t('s_di_sicher_h'))

    ziel = _feld(fenster, innen, t('s_di_mit'), t('s_di_mit_h'))

    def mitschreiben_um():
        neu_wert = not pfade.einstellung_wahrheit('fehler_mitschreiben', True)
        pfade.einstellung_setzen('fehler_mitschreiben', neu_wert)
        return neu_wert

    schiebeschalter(ziel, pfade.einstellung_wahrheit('fehler_mitschreiben', True),
                    mitschreiben_um).pack()

    ziel = _feld(fenster, innen, t('s_di_reset'), t('s_di_reset_h'))

    def zuruecksetzen():
        from tkinter import messagebox
        if not messagebox.askyesno(t('s_di_reset'), t('s_di_reset_frage')):
            return
        try:
            os.remove(pfade.app_datei('bestand.json'))
            fenster.sagen(t('s_di_reset_ok'))
        except OSError as ausnahme:
            fehler.merken('seiten.diagnose.zuruecksetzen', ausnahme)

    _knopf(fenster, ziel, t('s_zuruecksetzen'), zuruecksetzen, gefahr=True).pack()

    _status(fenster, innen, '!', t('s_di_reset_warn'), t('s_di_reset_warn_h'),
            farbe=GOLD)


def _zahl_katalog():
    try:
        return len((katalog_modul.laden().get('bauplaene') or {}))
    except Exception:
        return '—'


def _zahl_bestand():
    try:
        return len((bestand_datei.laden().get('bauplaene') or {}))
    except Exception:
        return '—'
