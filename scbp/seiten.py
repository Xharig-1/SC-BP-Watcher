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
        tk.Label(rahmen, text=lead, bg=BG, fg=SUB, font=fenster.f_klein,
                 anchor='w', justify='left', wraplength=620).pack(
                     fill='x', padx=24, pady=(0, 14))


def _rollflaeche(rahmen):
    """Ein Bereich, der rollt. Leinwand + Balken, wie im Einstellungsfenster.

    ⚠ Die Fläche wird **zuletzt** gepackt und bekommt `expand=True` — alles,
    was fest bleiben soll, muss vorher gepackt sein.
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

    def rollen(e):
        leinwand.yview_scroll(int(-1 * (e.delta or (120 if e.num == 4 else -120)) / 120),
                              'units')
    for ziel in (leinwand, innen):
        ziel.bind('<MouseWheel>', rollen)
        ziel.bind('<Button-4>', rollen)
        ziel.bind('<Button-5>', rollen)
    return innen


def _knopf(fenster, eltern, text, tat, stark=False):
    k = tk.Label(eltern, text=' %s ' % text, bg=FLAECHE,
                 fg=ACCENT if stark else FG, font=fenster.f_klein,
                 cursor='hand2', padx=10, pady=5)
    k.bind('<Button-1>', lambda e: tat())
    return k


def _feld(fenster, eltern, bezeichnung, hilfe):
    """Eine Einstellungszeile: Bezeichnung, Erklärung, Platz für das Bedienelement."""
    zeile = tk.Frame(eltern, bg=BG)
    zeile.pack(fill='x', padx=24, pady=(12, 0))
    links = tk.Frame(zeile, bg=BG)
    links.pack(side='left', fill='x', expand=True)
    tk.Label(links, text=bezeichnung, bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(fill='x')
    if hilfe:
        tk.Label(links, text=hilfe, bg=BG, fg=SUB, font=fenster.f_klein,
                 anchor='w', justify='left', wraplength=520).pack(fill='x')
    rechts = tk.Frame(zeile, bg=BG)
    rechts.pack(side='right', padx=(16, 0))
    tk.Frame(eltern, bg=LINIE, height=1).pack(fill='x', padx=24, pady=(12, 0))
    return rechts


# --------------------------------------------------------------------- Seiten
def _liste(fenster, rahmen):
    """Die Bauplan-Liste — das vorhandene Fenster, eingebettet."""
    from . import bestandsfenster
    fenster.bestandsseite = bestandsfenster.Bestandsfenster(rahmen=rahmen)


def _fortschritt(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_fortschritt'),
                  'Wie weit du je Art bist.')
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
    kopf.pack(fill='x', padx=24, pady=(0, 4))
    tk.Label(kopf, text=str(meine_alle), bg=BG, fg=ACCENT,
             font=fenster.f_titel).pack(side='left')
    tk.Label(kopf, text='  von %d Bauplänen · %.0f %%'
             % (gesamt_alle, 100.0 * meine_alle / gesamt_alle),
             bg=BG, fg=SUB, font=fenster.f_klein).pack(side='left')

    for art, (gesamt, meine) in sorted(nach_art.items(),
                                       key=lambda x: -x[1][0]):
        zeile = tk.Frame(innen, bg=BG)
        zeile.pack(fill='x', padx=24, pady=3)
        tk.Label(zeile, text=art, bg=BG, fg=FG, font=fenster.f_klein,
                 width=22, anchor='w').pack(side='left')
        balken = tk.Frame(zeile, bg='#222b3b', height=7, width=260)
        balken.pack(side='left', padx=8)
        balken.pack_propagate(False)
        anteil = max(0.0, min(1.0, meine / float(gesamt or 1)))
        if anteil > 0:
            tk.Frame(balken, bg=ACCENT, height=7,
                     width=max(2, int(260 * anteil))).pack(side='left')
        tk.Label(zeile, text='%d / %d' % (meine, gesamt), bg=BG, fg=SUB,
                 font=fenster.f_klein, width=10, anchor='e').pack(side='right')


def _einstellungen(fenster):
    """Die Bausteine des Einstellungsfensters — einmal erzeugt, mehrfach genutzt."""
    if getattr(fenster, '_einst', None) is None:
        from . import einstellungsfenster
        leer = tk.Frame(fenster.root, bg=BG)     # nur als Halter, wird nie gepackt
        fenster._einst = einstellungsfenster.Einstellungsfenster(rahmen=leer)
    return fenster._einst


def _allgemein(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_allgemein'),
                  'Was fast jeder einmal einstellt und danach nie wieder anfasst.')
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)
    for baustein in ('_sprachwahl', '_tonfeld'):
        try:
            getattr(e, baustein)(innen)
        except Exception as ausnahme:
            fehler.merken('seiten.allgemein:%s' % baustein, ausnahme)


def _anzeige(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_anzeige'),
                  'Wie das Overlay über dem Spiel liegt.')
    innen = _rollflaeche(rahmen)

    # Schriftgröße zuerst — sie betrifft alles andere auf dieser Seite.
    ziel = _feld(fenster, innen, t('hf_schrift'), t('hf_schrift_hilfe'))
    reihe = tk.Frame(ziel, bg=BG)
    reihe.pack()
    aktuell = {'wert': None}
    knoepfe = {}

    def waehlen(stufe):
        fenster.schriftgroesse_setzen(stufe)
        aktuell['wert'] = stufe
        for s, k in knoepfe.items():
            k.configure(fg=ACCENT if s == stufe else SUB)
        fenster.sagen('%s: %s' % (t('hf_schrift'), t('hf_s_' + stufe)))

    for stufe in ('klein', 'normal', 'gross', 'sehrgross'):
        k = tk.Label(reihe, text=' %s ' % t('hf_s_' + stufe), bg=FLAECHE, fg=SUB,
                     font=fenster.f_klein, cursor='hand2', padx=8, pady=4)
        k.pack(side='left', padx=2)
        k.bind('<Button-1>', lambda ev, s=stufe: waehlen(s))
        knoepfe[stufe] = k
    from . import pfade
    jetzt = pfade.einstellung('schriftgroesse') or 'normal'
    if jetzt in knoepfe:
        knoepfe[jetzt].configure(fg=ACCENT)

    e = _einstellungen(fenster)
    try:
        e._deckkraftfeld(innen)
    except Exception as ausnahme:
        fehler.merken('seiten.anzeige.deckkraft', ausnahme)


def _ordner(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_ordner'),
                  'Wo Star Citizen liegt und wohin das Werkzeug schreibt.')
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)
    try:
        e._ordnerfeld(innen, t('e_spiel'), t('e_spiel_hilfe'), e.spiel)
        e._ordnerfeld(innen, t('e_launcher'), t('e_launcher_hilfe'), e.launcher)
    except Exception as ausnahme:
        fehler.merken('seiten.ordner', ausnahme)


def _spiel(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_spiel'),
                  'Bauplan-Angaben in den Missionstexten.')
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)
    try:
        e._injektionsfeld(innen)
    except Exception as ausnahme:
        fehler.merken('seiten.spiel', ausnahme)


def _bestand(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_bestand'),
                  'Deinen Bauplan-Stand ausgeben — oder einen vorhandenen einlesen.')
    innen = _rollflaeche(rahmen)

    from . import export, importieren
    ziel = _feld(fenster, innen, 'Bestand ausgeben',
                 'Drei Formate: KRT Profit Basetool, scmdb.net und eine vollständige '
                 'Sicherung. Hochgeladen wird nichts.')
    reihe = tk.Frame(ziel, bg=BG)
    reihe.pack()

    def in_ablage():
        try:
            ordner, wieviele = export.ablegen()
            fenster.sagen('%d Dateien abgelegt' % wieviele if wieviele else '—')
        except Exception as ausnahme:
            fehler.merken('seiten.bestand.ablegen', ausnahme)
            fenster.sagen('Ausgeben hat nicht geklappt')

    _knopf(fenster, reihe, 'In die Ablage', in_ablage, stark=True).pack(side='left')

    ziel2 = _feld(fenster, innen, 'Bestand einlesen',
                  'Aus dem Basetool, von scmdb, aus der Launcher-Datei oder einer '
                  'Sicherung. Das Format wird selbst erkannt, zusammengeführt statt '
                  'ersetzt.')
    reihe2 = tk.Frame(ziel2, bg=BG)
    reihe2.pack()

    def einlesen():
        from tkinter import filedialog
        pfad = filedialog.askopenfilename(
            title='Bestand einlesen', filetypes=[('JSON', '*.json'), ('Alle', '*.*')])
        if not pfad:
            return
        art, eintraege = importieren.lesen(pfad)
        if not art:
            fenster.sagen('Diese Datei kenne ich nicht')
            return
        vorschau = importieren.vorschau(eintraege)
        dazu = importieren.uebernehmen(eintraege)
        fenster.sagen('%s: %d neu, %d schon da%s'
                      % (art, dazu, len(vorschau['schon_da']),
                         (', %d nicht im Katalog' % len(vorschau['unbekannt']))
                         if vorschau['unbekannt'] else ''))

    _knopf(fenster, reihe2, 'Datei wählen …', einlesen, stark=True).pack(side='left')


def _wasistneu(fenster, rahmen):
    """Die Änderungen — als Reiter, nicht als Fenster über dem Fenster."""
    _ueberschrift(fenster, rahmen, t('hf_wasistneu'),
                  'Was diese und ältere Fassungen gebracht haben.')
    innen = _rollflaeche(rahmen)
    from . import aktualisierung
    try:
        eintraege = aktualisierung.protokoll()
    except Exception as ausnahme:
        fehler.merken('seiten.wasistneu', ausnahme)
        eintraege = []
    if not eintraege:
        tk.Label(innen, text='—', bg=BG, fg=SUB, font=fenster.f_grund).pack(
            padx=24, pady=10, anchor='w')
        return
    for e in eintraege[:12]:
        kopf = tk.Frame(innen, bg=BG)
        kopf.pack(fill='x', padx=24, pady=(14, 2))
        tk.Label(kopf, text=e.get('version') or '—', bg=BG, fg=ACCENT,
                 font=fenster.f_fett).pack(side='left')
        if e.get('datum'):
            tk.Label(kopf, text='  ' + e['datum'], bg=BG, fg=SUB,
                     font=fenster.f_klein).pack(side='left')
        tk.Label(innen, text=(e.get('text') or '').strip(), bg=BG, fg=SUB,
                 font=fenster.f_klein, anchor='w', justify='left',
                 wraplength=640).pack(fill='x', padx=24)


def _ueber(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_ueber'),
                  'Welche Fassung läuft, und wer sie gebaut hat.')
    innen = _rollflaeche(rahmen)

    from . import pfade
    uebersicht = {}
    try:
        uebersicht = pfade.uebersicht() or {}
    except Exception:
        pass
    for bez, wert in (('Fassung', fenster.version or '—'),
                      ('Baupläne bekannt', _zahl_katalog()),
                      ('Davon deine', _zahl_bestand()),
                      ('Eigener Ordner', uebersicht.get('app_ordner') or '—')):
        z = tk.Frame(innen, bg=BG)
        z.pack(fill='x', padx=24, pady=2)
        tk.Label(z, text=bez, bg=BG, fg=SUB, font=fenster.f_klein, width=22,
                 anchor='w').pack(side='left')
        tk.Label(z, text=str(wert), bg=BG, fg=FG, font=fenster.f_klein,
                 anchor='w').pack(side='left')

    ziel = _feld(fenster, innen, t('e_vorab'), t('e_vorab_hilfe'))
    schalter = tk.Label(ziel, text='', bg=FLAECHE, font=fenster.f_klein,
                        cursor='hand2', padx=10, pady=4)
    schalter.pack()

    def zeichnen():
        an = pfade.einstellung_wahrheit('vorabversionen', False)
        schalter.configure(text=' %s ' % (t('e_an') if an else t('e_aus')),
                           fg=ACCENT if an else SUB)

    def umschalten():
        neu = not pfade.einstellung_wahrheit('vorabversionen', False)
        pfade.einstellung_setzen('vorabversionen', neu)
        zeichnen()
        fenster.sagen(t('e_vorab') + ': ' + (t('e_an') if neu else t('e_aus')))

    schalter.bind('<Button-1>', lambda e: umschalten())
    zeichnen()

    tk.Label(innen, text=t('hf_wer'), bg=BG, fg=FG, font=fenster.f_fett,
             anchor='w').pack(fill='x', padx=24, pady=(22, 6))
    tk.Label(innen, text='Xharig', bg=BG, fg=ACCENT, font=fenster.f_titel,
             anchor='w').pack(fill='x', padx=24)
    tk.Label(innen, text='SC BP Watcher · GPL-3.0-only\n'
                         'github.com/Xharig-1/SC-BP-Watcher',
             bg=BG, fg=SUB, font=fenster.f_klein, anchor='w',
             justify='left').pack(fill='x', padx=24, pady=(2, 12))

    tk.Label(innen, text=t('hf_dank'), bg=BG, fg=FG, font=fenster.f_klein,
             anchor='w').pack(fill='x', padx=24)
    tk.Label(innen, text='· scmdb.net — Bauplan-Katalog und Herkunft\n'
                         '· rjcncpt / SC Deutsch Launcher — Übersetzung und Verträge\n'
                         '· MrKraken · StarStrings — Vorbild für die Einspielung',
             bg=BG, fg=SUB, font=fenster.f_klein, anchor='w',
             justify='left').pack(fill='x', padx=24, pady=(2, 8))
    tk.Label(innen, text=t('hf_nichts_dabei'), bg=BG, fg=SUB,
             font=fenster.f_klein, anchor='w', justify='left',
             wraplength=620).pack(fill='x', padx=24)
    tk.Label(innen, text=t('hf_fancontent'), bg=BG, fg=SUB, font=fenster.f_klein,
             anchor='w', justify='left', wraplength=620).pack(
                 fill='x', padx=24, pady=(14, 20))


def _erkennung(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_erkennung'),
                  'Wie der Watcher merkt, dass ein Bauplan hereingekommen ist. '
                  'Die Standardwerte passen für fast jeden.')
    innen = _rollflaeche(rahmen)
    e = _einstellungen(fenster)
    try:
        e._intervallfeld(innen)
    except Exception as ausnahme:
        fehler.merken('seiten.erkennung', ausnahme)


def _diagnose(fenster, rahmen):
    _ueberschrift(fenster, rahmen, t('hf_diagnose'),
                  'Wenn etwas klemmt: Dieser Block sagt in einem Rutsch, woran es '
                  'liegen könnte.')
    innen = _rollflaeche(rahmen)

    text = ''
    try:
        text = bericht.bauen(version=fenster.version, wurzel=fenster.root)
    except Exception as ausnahme:
        fehler.merken('seiten.diagnose', ausnahme)

    kasten = tk.Text(innen, bg='#0c1017', fg=FG, font=('Consolas', 9),
                     height=18, wrap='none', relief='flat',
                     insertbackground=FG, padx=12, pady=10)
    kasten.pack(fill='both', expand=True, padx=24, pady=(0, 10))
    kasten.insert('1.0', text)
    kasten.configure(state='disabled')

    reihe = tk.Frame(innen, bg=BG)
    reihe.pack(fill='x', padx=24, pady=(0, 16))

    def melden():
        if bericht.issue_oeffnen(text):
            fenster.sagen('Formular im Browser geöffnet')
        else:
            fenster.sagen('Browser ließ sich nicht öffnen')

    def kopieren():
        if bericht.in_die_ablage(text, fenster.root):
            fenster.sagen('Angaben kopiert')

    def speichern():
        ziel = bericht.speichern(text)
        fenster.sagen('Gespeichert: %s' % ziel if ziel else 'Speichern ging nicht')

    _knopf(fenster, reihe, 'Fehler melden …', melden, stark=True).pack(side='left')
    _knopf(fenster, reihe, 'Angaben kopieren', kopieren).pack(side='left', padx=8)
    _knopf(fenster, reihe, 'Als Datei speichern …', speichern).pack(side='left')


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
