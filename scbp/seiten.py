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
    balken = tk.Scrollbar(aussen, orient='vertical', command=leinwand.yview)
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

    def rollen(e):
        leinwand.yview_scroll(int(-1 * (e.delta or (120 if e.num == 4 else -120)) / 120),
                              'units')
    for ziel in (leinwand, innen, innen_ziel):
        ziel.bind('<MouseWheel>', rollen)
        ziel.bind('<Button-4>', rollen)
        ziel.bind('<Button-5>', rollen)
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


def _status(fenster, eltern, zeichen, fett, rest, farbe=None):
    """Ein Statuskasten mit farbigem Balken links — wie in der Vorschau."""
    farbe = farbe or ACCENT
    innen = _karte(eltern, rand=farbe, pady=(0, 14))
    zeile = tk.Frame(innen, bg=FLAECHE)
    zeile.pack(fill='x', padx=14, pady=12)
    tk.Label(zeile, text=zeichen, bg=FLAECHE, fg=farbe,
             font=fenster.f_grund).pack(side='left', padx=(0, 10), anchor='n')
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
        if erklaerung is not None:
            _umbruch(erklaerung, bezug=zeile)
    else:
        rechts = tk.Frame(zeile, bg=BG)
        rechts.pack(side='right', padx=(16, 0))
        # ⚠ Hier NICHT an `links` messen: Der Rahmen ist in genau dem Moment
        # zu breit, in dem der Text überläuft — er würde den Fehler bestätigen
        # statt ihn zu beheben. Gemessen wird am gemeinsamen Elternrahmen
        # abzüglich des Bedienelements, das rechts steht.
        if erklaerung is not None:
            _umbruch(erklaerung, bezug=zeile, neben=rechts, abzug=16)
        _umbruch(beschriftung, bezug=zeile, neben=rechts, abzug=16)
    tk.Frame(eltern, bg=LINIE, height=1).pack(fill='x', pady=(12, 0))
    return rechts


# --------------------------------------------------------------------- Seiten
def _liste(fenster, rahmen):
    """Die Bauplan-Liste — das vorhandene Fenster, eingebettet."""
    from . import bestandsfenster
    fenster.bestandsseite = bestandsfenster.Bestandsfenster(rahmen=rahmen)


def _fortschritt(fenster, rahmen):
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
    nach_art = {}
    for schluessel, e in bp.items():
        art = katalog_modul.art_lesbar(e.get('a')) if e.get('a') else '—'
        gesamt, meine = nach_art.get(art, (0, 0))
        nach_art[art] = (gesamt + 1, meine + (1 if schluessel in habe else 0))

    gesamt_alle = sum(g for g, _ in nach_art.values()) or 1
    meine_alle = sum(m for _, m in nach_art.values())
    kopf = tk.Frame(innen, bg=BG)
    kopf.pack(fill='x', pady=(0, 4))
    tk.Label(kopf, text=str(meine_alle), bg=BG, fg=ACCENT,
             font=fenster.f_titel).pack(side='left')
    tk.Label(kopf, text=t('s_fo_von')
             % (gesamt_alle, 100.0 * meine_alle / gesamt_alle),
             bg=BG, fg=SUB, font=fenster.f_klein).pack(side='left')

    # Ein Gesamtbalken direkt darunter — die Zahl allein sagt wenig, der Balken
    # zeigt auf einen Blick, wie weit der Weg noch ist.
    from .hauptfenster import rundbalken
    rundbalken(innen, 9, meine_alle / float(gesamt_alle), BG, '#222b3b',
               ACCENT).pack(fill='x', pady=(6, 18))

    for art, (gesamt, meine) in sorted(nach_art.items(),
                                       key=lambda x: -x[1][0]):
        zeile = tk.Frame(innen, bg=BG)
        zeile.pack(fill='x', pady=3)
        tk.Label(zeile, text=art, bg=BG, fg=FG, font=fenster.f_klein,
                 width=22, anchor='w').pack(side='left')
        anteil = max(0.0, min(1.0, meine / float(gesamt or 1)))
        rundbalken(zeile, 7, anteil, BG, '#222b3b', ACCENT,
                   breite=260).pack(side='left', padx=8)
        tk.Label(zeile, text='%d / %d' % (meine, gesamt), bg=BG, fg=SUB,
                 font=fenster.f_klein, width=10, anchor='e').pack(side='right')


def _einstellungen(fenster):
    """Die Bausteine des Einstellungsfensters — einmal erzeugt, mehrfach genutzt."""
    if getattr(fenster, '_einst', None) is None:
        from . import einstellungsfenster
        leer = tk.Frame(fenster.root, bg=BG)     # nur als Halter, wird nie gepackt
        fenster._einst = einstellungsfenster.Einstellungsfenster(rahmen=leer)
        # Ohne diesen Rückruf öffnet ein Sprachwechsel ein zweites Fenster.
        fenster._einst.beim_sprachwechsel = fenster.neu_aufbauen
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
                 lambda k: e._sprache_waehlen(k))
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

        schiebeschalter(ziel, autostart.ist_an(), autostart_um).pack()
    else:
        tk.Label(ziel, text=t('s_nicht_moegl'), bg=BG, fg=SUB,
                 font=fenster.f_klein).pack()

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

    ziel = _feld(fenster, innen, t('hf_schrift'), t('hf_schrift_hilfe'),
                 breit=True)
    wahl = _wahl(fenster, ziel,
                 [(s, t('hf_s_' + s))
                  for s in ('klein', 'normal', 'gross', 'sehrgross')],
                 pfade.einstellung('schriftgroesse') or 'normal',
                 lambda k: (fenster.schriftgroesse_setzen(k),
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
    zahl.insert(0, str(pfade.einstellung_zahl('max_zeilen', 200, 10, 2000)))
    zahl.halter.pack()

    def zahl_merken(_=None):
        try:
            pfade.einstellung_setzen('max_zeilen',
                                     max(10, min(2000, int(zahl.get()))))
            fenster.sagen(t('s_an_zeilen') % zahl.get())
        except ValueError:
            pass

    zahl.bind('<FocusOut>', zahl_merken)
    zahl.bind('<Return>', zahl_merken)

    ziel = _feld(fenster, innen, t('s_lage'),
                 t('s_lage_h'))

    def lage_weg():
        try:
            os.remove(pfade.app_datei('watcher.json'))
        except OSError:
            pass
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
        _status(fenster, innen, '✓', t('s_sc_da'),
                t('s_or_mitlesen') % gefunden)
    else:
        _status(fenster, innen, '!', t('s_sc_weg'),
                t('s_sc_weg_h'), farbe=GOLD)

    tk.Label(innen, text=t('e_spiel'), bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(fill='x', pady=(6, 0))
    _fliesstext(innen, t('e_spiel_hilfe'), fenster.f_klein, fill='x')
    _pfadfeld(fenster, innen, e.spiel,
              lambda: e._waehlen(e.spiel, t('e_spiel')))

    tk.Label(innen, text=t('s_eigene'), bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(fill='x', pady=(20, 0))
    _fliesstext(innen, t('s_eigene_h'), fenster.f_klein, fill='x')
    ablage = tk.StringVar(value=pfade.app_ordner())

    def ablage_oeffnen():
        _ordner_zeigen(pfade.app_ordner())
        fenster.sagen(t('s_or_geoeffnet'))

    _pfadfeld(fenster, innen, ablage,
              lambda: fenster.sagen(t('s_or_eigener_ort')),
              oeffnen=ablage_oeffnen)

    tk.Label(innen, text='%s  —  %s' % (t('e_launcher'), t('s_optional')), bg=BG, fg=FG,
             font=fenster.f_fett, anchor='w').pack(fill='x', pady=(20, 0))
    _fliesstext(innen, t('e_launcher_hilfe'), fenster.f_klein, fill='x')
    _pfadfeld(fenster, innen, e.launcher,
              lambda: e._waehlen(e.launcher, t('e_launcher')),
              platzhalter=t('s_or_leer'))


def _ordner_zeigen(pfad):
    """Den Ordner im Dateiverwalter öffnen — auf jedem System anders."""
    import subprocess
    try:
        if sys.platform.startswith('win'):
            os.startfile(pfad)                      # noqa: S606
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', pfad])
        else:
            subprocess.Popen(['xdg-open', pfad])
        return True
    except Exception as ausnahme:
        fehler.merken('seiten.ordner_zeigen', ausnahme, pfad)
        return False


def _spiel(fenster, rahmen):
    from . import injektion, pfade
    from .hauptfenster import schiebeschalter
    _ueberschrift(fenster, rahmen, t('hf_spiel'), t('s_sp_lead'))
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)

    # Zustand: steht etwas im Spiel, und woher stammt es?
    stellen, quelle = 0, ''
    try:
        lage = injektion.lage() if hasattr(injektion, 'lage') else None
        if isinstance(lage, dict):
            stellen = lage.get('stellen') or 0
            quelle = lage.get('quelle') or ''
    except Exception:
        pass
    if stellen:
        _status(fenster, innen, '✓', t('s_sp_drin') % stellen,
                (t('s_sp_quelle_ist') % quelle) if quelle else '')
    else:
        _status(fenster, innen, '○', t('s_sp_nichts'), t('s_sp_nichts_h'),
                farbe=SUB)

    ziel = _feld(fenster, innen, t('s_sp_quelle'), t('s_sp_quelle_h'),
                 breit=True)
    wahl = _wahl(fenster, ziel,
                 [('deutsch', t('s_sp_q_de')), ('starstrings', t('s_sp_q_ss')),
                  ('original', t('s_sp_q_or'))],
                 pfade.einstellung('inj_quelle') or '',
                 lambda k: (e._inj_wechseln(k),
                            pfade.einstellung_setzen('inj_quelle', k),
                            fenster.sagen(t('s_sp_quelle_ist') % k)))
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
           lambda: (e._inj_erneuern(), fenster.sagen(t('s_sp_frisch'))),
           stark=True).pack(side='left')
    _knopf(fenster, reihe, t('s_sp_pruefen'),
           lambda: e._inj_pruefen()).pack(side='left', padx=8)
    _knopf(fenster, reihe, t('s_sp_weg'),
           lambda: (e._inj_entfernen(), fenster.sagen(t('s_sp_weg_ok'))),
           gefahr=True).pack(side='left')

    _status(fenster, innen, '!', t('s_sp_warn'), t('s_sp_warn_h'), farbe=GOLD)


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
    pfeil = tk.Label(kopf, text='▼' if offen else '▶', bg=BG, fg=SUB,
                     font=fenster.f_klein)
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
    # Alle Blasen so breit wie die längste Beschriftung — sonst flattern sie
    # und die Texte daneben fangen an unterschiedlichen Stellen an.
    breiteste = max(fenster.f_klein.measure(w) for w in _ART_WORT.values()) + 20
    for art, zeile in punkte:
        z = tk.Frame(koerper, bg=BG)
        z.pack(fill='x', pady=3)
        marke(z, _ART_WORT.get(art, ''), _ART_FARBE.get(art, SUB),
              fenster.f_klein, grund=BG,
              mindestbreite=breiteste).pack(side='left', anchor='n', padx=(0, 14))
        # ⚠ `wraplength` muss zur wirklichen Breite passen. Stand er zu niedrig,
        # brach der Text zwar um — die Zeile blieb aber einzeilig hoch, und der
        # Rest war schlicht abgeschnitten. Deshalb wird die Breite beim Zeichnen
        # aus dem Fenster genommen statt geraten.
        breite = max(360, (fenster.root.winfo_width() or 980) - 340)
        tk.Label(z, text=_saubere_zeile(zeile), bg=BG, fg=FG,
                 font=fenster.f_klein, anchor='w', justify='left',
                 wraplength=breite).pack(side='left', fill='x', expand=True)

    def umschalten(*_):
        zustand['offen'] = not zustand['offen']
        pfeil.configure(text='▼' if zustand['offen'] else '▶')
        if zustand['offen']:
            koerper.pack(fill='x')
        else:
            koerper.pack_forget()

    for teil in (kopf, pfeil):
        teil.bind('<Button-1>', umschalten)


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


def _kanalkasten(fenster, eltern, titel, text, gewaehlt, tat, marke_text='',
                 untereinander=False):
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
    tk.Label(kopf, text='●', bg=FLAECHE, fg=ACCENT if gewaehlt else '#3a4658',
             font=fenster.f_klein).pack(side='left', padx=(0, 7))
    tk.Label(kopf, text=titel, bg=FLAECHE, fg=FG,
             font=fenster.f_fett).pack(side='left')
    if marke_text:
        blase(kopf, marke_text, GOLD, fenster.f_klein).pack(side='left', padx=8)

    beschreibung = tk.Label(innen, text=text, bg=FLAECHE, fg=SUB,
                            font=fenster.f_klein, anchor='w', justify='left')
    beschreibung.pack(fill='x', padx=14, pady=(0, 12))
    _umbruch(beschreibung, abzug=28)

    for teil in (rand, leinwand, innen, kopf):
        teil.bind('<Button-1>', lambda e: tat())
    for kind in innen.winfo_children() + kopf.winfo_children():
        try:
            kind.bind('<Button-1>', lambda e: tat())
        except Exception:
            pass
    return rand


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
               lambda: fenster.sagen(t('s_ub_sucht')), stark=True),
        _knopf(fenster, reihe, t('hf_wasistneu'),
               lambda: fenster.oeffnen('wasistneu')),
        _knopf(fenster, reihe, t('s_ub_einrichtung'), fenster._einrichtung),
    ])

    ziel = _feld(fenster, innen, t('s_ub_taeglich'), t('s_ub_taeglich_h'))
    _schalter(fenster, ziel, 'update_pruefen', True)

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
                     not an, lambda: kanal_setzen(False), untereinander=eng)
        _kanalkasten(fenster, kaesten, t('s_ub_test'), t('s_ub_test_h'),
                     an, lambda: kanal_setzen(True), marke_text='rc',
                     untereinander=eng)

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
    tk.Label(rechts, text='github.com/Xharig-1/SC-BP-Watcher', bg=FLAECHE,
             fg=ACCENT, font=fenster.f_klein, anchor='w').pack(fill='x',
                                                               pady=(4, 0))

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

    _status(fenster, innen, '✓', t('s_di_sicher'), t('s_di_sicher_h'))

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
