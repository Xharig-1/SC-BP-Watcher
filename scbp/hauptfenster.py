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
Ein Fenster für alles — Reiter links, Inhalt rechts.

**Warum der Umbau:** Bisher gab es zwei getrennte Fenster (Bauplan-Liste und
Einstellungen), und man musste wissen, in welchem etwas steckt. Jetzt liegen
beide zusammen: oben die Baupläne, darunter die Einstellungen, ganz unten
eingeklappt, was nur Fortgeschrittene brauchen.

**Aufbau des Rahmens** — die Reihenfolge beim Packen ist entscheidend:

    1. Titelleiste      oben, fest
    2. Fußzeile         unten, fest
    3. Reiterleiste     links, fest
    4. Inhaltsbereich   zuletzt, `expand=True` → bekommt den Rest

Wer den Inhalt vor der Fußzeile packt, schiebt sie aus dem Fenster — das ist
hier schon einmal passiert (der unsichtbare Speichern-Knopf). Steht auch in der
`CLAUDE.md` des Projekts.

**Seiten werden erst gezeichnet, wenn man sie öffnet.** Der Katalog hat über 700
Einträge; alles beim Start aufzubauen kostet Sekunden, die niemand hergibt, um
danach eine einzige Seite anzusehen.

**Kein Speichern-Knopf.** Jede Änderung greift sofort und wird sofort geschrieben.
Die Begründung: „Vergisst ein Nutzer das Speichern, ist der Ärger größer als
der Nutzen des Knopfes."
"""
import os
import sys
import tkinter as tk
import tkinter.font as tkfont

from . import fehler, hinweis, neuheiten, pfade
from .sprache import t

BG      = '#10141c'
FLAECHE = '#161c28'
BAR     = '#1b2230'
FG      = '#e6edf3'
SUB     = '#8b98a5'
ACCENT  = '#9ce430'
LINIE   = '#232c3d'
GOLD    = '#e8c353'

# Mindestgröße: Darunter bricht die Bedienung, und keine Layout-Regel hilft mehr.
MIN_BREITE, MIN_HOEHE = 720, 520

# Schriftgrößen als **eine** Stellschraube. Anlass: Das ⟳ in der Titelleiste war
# mit Brille kaum zu erkennen. Alle Widgets teilen sich diese Font-Objekte —
# `configure(size=…)` zieht damit die ganze Oberfläche mit, statt dass jede
# Stelle einzeln angefasst werden müsste.
STUFEN = {'klein': 0, 'normal': 1, 'gross': 3, 'sehrgross': 5}


def _rundes_rechteck(leinwand, x1, y1, x2, y2, radius, **kw):
    """Ein Rechteck mit runden Ecken.

    Tk kennt so etwas nicht — aber ein Vieleck mit `smooth=True` rundet genau
    dort ab, wo Punkte dicht beieinander liegen. Deshalb sitzt an jeder Ecke ein
    Punktepaar im Abstand des Radius.
    """
    punkte = [
        x1 + radius, y1, x2 - radius, y1, x2, y1,
        x2, y1 + radius, x2, y2 - radius, x2, y2,
        x2 - radius, y2, x1 + radius, y2, x1, y2,
        x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return leinwand.create_polygon(punkte, smooth=True, **kw)


def schiebeschalter(eltern, an, umschalten, grund=None):
    """Ein runder Schiebeschalter — an oder aus, auf einen Blick.

    Tk kennt nur Kästchen zum Ankreuzen, und die sehen auf jedem System anders
    aus. Auf einer kleinen Leinwand lässt sich dagegen genau das zeichnen, was
    heute jeder erwartet: eine Kapsel, in der ein Punkt nach rechts wandert.

    `umschalten()` wird beim Klick aufgerufen und muss den neuen Zustand
    zurückgeben — gezeichnet wird erst danach, damit nichts leuchtet, was gar
    nicht gespeichert wurde.
    """
    grund = grund or BG
    breite, hoehe = 44, 24
    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=grund,
                  highlightthickness=0, bd=0, cursor='hand2')
    kapsel = _rundes_rechteck(c, 2, 3, breite - 2, hoehe - 3, radius=9,
                              fill='#2b3547', outline='')
    punkt = c.create_oval(5, 6, 19, 20, fill=SUB, outline='')

    def zeichnen(zustand):
        c.itemconfigure(kapsel, fill='#2a3a1c' if zustand else '#2b3547')
        c.itemconfigure(punkt, fill=ACCENT if zustand else SUB)
        x = (breite - 24) if zustand else 0
        c.coords(punkt, 5 + x, 6, 19 + x, 20)

    def klick(_=None):
        zeichnen(bool(umschalten()))

    c.bind('<Button-1>', klick)
    zeichnen(bool(an))
    c.zeichnen = zeichnen
    return c


def regler(eltern, von, bis, wert, beim_ziehen, breite=190, grund=None):
    """Ein Schieberegler in der Machart des Fensters.

    Tk bringt zwar `Scale` mit, aber das ist ein Systemelement: Auf dem Mac ein
    graues Kästchen, unter Windows ein anderes, unter Linux je nach Oberfläche
    wieder anders. Selbst gezeichnet sieht es überall gleich aus — und passt zu
    den Schaltern daneben.
    """
    grund = grund or BG
    hoehe = 26
    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=grund,
                  highlightthickness=0, bd=0, cursor='hand2')
    y = hoehe // 2
    _rundes_rechteck(c, 0, y - 3, breite, y + 3, radius=3,
                     fill='#2b3547', outline='')
    gefuellt = _rundes_rechteck(c, 0, y - 3, 10, y + 3, radius=3,
                                fill=ACCENT, outline='')
    knopf = c.create_oval(0, y - 8, 16, y + 8, fill=ACCENT, outline='')

    spanne = float(max(1, bis - von))

    def zeichnen(w):
        anteil = max(0.0, min(1.0, (w - von) / spanne))
        x = 8 + anteil * (breite - 16)
        c.coords(gefuellt, *([0, y - 3, x, y - 3, x, y - 3, x, y + 3,
                              x, y + 3, 0, y + 3, 0, y + 3, 0, y - 3]))
        c.coords(knopf, x - 8, y - 8, x + 8, y + 8)

    def aus_x(ereignis):
        anteil = max(0.0, min(1.0, (ereignis.x - 8) / float(breite - 16)))
        return int(round(von + anteil * spanne))

    def ziehen(ereignis):
        neuer = aus_x(ereignis)
        zeichnen(neuer)
        beim_ziehen(neuer)

    c.bind('<Button-1>', ziehen)
    c.bind('<B1-Motion>', ziehen)
    zeichnen(wert)
    c.zeichnen = zeichnen
    return c


def marke(eltern, text, farbe, schrift, grund=None, mindestbreite=0):
    """Eine abgerundete Blase mit farbigem Rand — „neu", „behoben" und Verwandte.

    Ein farbiges Wort geht in einer Liste unter; eine umrandete Blase liest man
    als Auszeichnung.

    ⚠ Mit einem Label geht das nicht: `highlightthickness` zeichnet Tk je nach
    System nur bei Fokus (auf dem Mac blieb der Rand unsichtbar), und
    `relief='solid'` malt eine Systemlinie statt einer eigenen Farbe. Runde
    Ecken kann ein Label ohnehin nicht. Deshalb eine kleine Leinwand: Sie kostet
    ein paar Zeilen mehr und sieht auf allen drei Systemen gleich aus.
    """
    grund = grund or FLAECHE
    hoehe = schrift.metrics('linespace') + 8
    # ⚠ Genug Luft, und alle Blasen einer Gruppe gleich breit: Sonst wird die
    # längste abgeschnitten, sobald der Platz feststeht — und die Wörter
    # flattern, weil jede Blase anders breit ist.
    breite = max(mindestbreite, schrift.measure(text) + 20)
    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=grund,
                  highlightthickness=0, bd=0)
    c.blase = _rundes_rechteck(c, 1, 1, breite - 1, hoehe - 1,
                               radius=max(4, hoehe // 3),
                               fill=grund, outline=farbe, width=1)
    c.create_text(breite / 2.0, hoehe / 2.0, text=text, fill=farbe,
                  font=schrift, anchor='center')

    def hintergrund(neuer):
        """Beim Einfärben der Zeile mitziehen — Leinwand und Blasenfüllung."""
        c.configure(bg=neuer)
        c.itemconfigure(c.blase, fill=neuer)

    c.hintergrund = hintergrund
    return c


class Hauptfenster:
    """Der Rahmen mit der Reiterleiste. Die Seiten liefern andere Module."""

    def __init__(self, eltern=None, beim_schliessen=None, version=''):
        self.beim_schliessen = beim_schliessen
        self.version = version
        self.root = tk.Toplevel(eltern) if eltern else tk.Tk()
        self.root.title(t('hf_titel'))
        self.root.configure(bg=BG)
        self.root.geometry('980x700')
        self.root.minsize(MIN_BREITE, MIN_HOEHE)

        self._schriften_anlegen()

        self.seiten = {}          # kennung -> Frame
        self.gezeichnet = set()   # welche Seiten schon Inhalt haben
        self.knoepfe = {}         # kennung -> Reiter-Label
        self.aktuell = None
        self.fortgeschritten_offen = False

        self._titelleiste()
        self._fusszeile()         # ⚠ vor dem Inhalt — sonst rutscht sie hinaus
        self._korpus()

        self.oeffnen('liste')
        self.root.protocol('WM_DELETE_WINDOW', self.schliessen)

    # ------------------------------------------------------------- Schriften
    def _schriften_anlegen(self):
        stufe = STUFEN.get(pfade.einstellung('schriftgroesse') or 'normal', 1)
        self.f_grund  = tkfont.Font(family='Segoe UI', size=10 + stufe)
        self.f_fett   = tkfont.Font(family='Segoe UI', size=10 + stufe, weight='bold')
        self.f_klein  = tkfont.Font(family='Segoe UI', size=9 + stufe)
        self.f_titel  = tkfont.Font(family='Segoe UI', size=12 + stufe, weight='bold')
        self.f_zeichen = tkfont.Font(family='Segoe UI', size=13 + stufe)

    def schriftgroesse_setzen(self, stufe):
        """Die ganze Oberfläche wächst oder schrumpft — sofort, ohne Neustart."""
        n = STUFEN.get(stufe, 1)
        for schrift, grund in ((self.f_grund, 10), (self.f_fett, 10),
                               (self.f_klein, 9), (self.f_titel, 12),
                               (self.f_zeichen, 13)):
            schrift.configure(size=grund + n)
        pfade.einstellung_setzen('schriftgroesse', stufe)

    # ------------------------------------------------------------ Titelleiste
    def _titelleiste(self):
        bar = tk.Frame(self.root, bg=BAR)
        bar.pack(side='top', fill='x')

        # Das Programm-Icon gehört hierhin — dort sucht man es.
        self._icon_bild = None
        png = _mitgeliefert(os.path.join('assets', 'icon.png'))
        if png and os.path.exists(png):
            try:
                voll = tk.PhotoImage(file=png)
                teiler = max(1, voll.width() // 22)
                self._icon_bild = voll.subsample(teiler, teiler)
                tk.Label(bar, image=self._icon_bild, bg=BAR).pack(side='left',
                                                                 padx=(12, 8), pady=8)
            except Exception as ausnahme:
                fehler.merken('hauptfenster.icon', ausnahme)

        tk.Label(bar, text=t('hf_titel'), bg=BAR, fg=FG,
                 font=self.f_fett).pack(side='left')
        tk.Label(bar, text='v%s' % (self.version or '—'), bg=BAR, fg=SUB,
                 font=self.f_klein).pack(side='left', padx=(6, 0))

        # Symbol UND Wort: Ein Symbol allein erklärt sich nur dem, der es gebaut
        # hat — hier war selbst der Autor unsicher, was ⟳ bedeutet.
        self.knopf_neu = self._titelknopf(bar, 'ⓘ', t('hf_wasistneu'),
                                          t('hf_hinweis_neu'), self._was_ist_neu)
        self._titelknopf(bar, '⟳', t('hf_einrichtung'),
                         t('hf_hinweis_einr'), self._einrichtung)

    def _titelknopf(self, eltern, zeichen, wort, erklaerung, tat):
        rahmen = tk.Frame(eltern, bg=BAR, cursor='hand2')
        rahmen.pack(side='right', padx=(0, 10), pady=6)
        z = tk.Label(rahmen, text=zeichen, bg=BAR, fg=SUB, font=self.f_zeichen)
        z.pack(side='left')
        w = tk.Label(rahmen, text=' ' + wort, bg=BAR, fg=SUB, font=self.f_klein)
        w.pack(side='left')
        for teil in (rahmen, z, w):
            teil.bind('<Button-1>', lambda e, f=tat: f())
        hinweis.anhaengen(rahmen, lambda: erklaerung)
        rahmen.teile = (z, w)
        return rahmen

    # --------------------------------------------------------------- Fußzeile
    def _fusszeile(self):
        fuss = tk.Frame(self.root, bg=BAR)
        fuss.pack(side='bottom', fill='x')
        self.meldung = tk.Label(fuss, text=t('hf_sofort'), bg=BAR, fg=SUB,
                                font=self.f_klein)
        self.meldung.pack(side='left', padx=14, pady=9)
        k = tk.Label(fuss, text=' %s ' % t('hf_schliessen'), bg=FLAECHE, fg=FG,
                     font=self.f_klein, cursor='hand2', padx=10, pady=4)
        k.pack(side='right', padx=12)
        k.bind('<Button-1>', lambda e: self.schliessen())

    def sagen(self, text):
        """Kurze Rückmeldung in der Fußzeile — statt eines Speichern-Knopfes."""
        try:
            self.meldung.configure(text=text, fg=ACCENT)
            self.root.after(4000, lambda: self.meldung.configure(
                text=t('hf_sofort'), fg=SUB))
        except Exception:
            pass

    # ----------------------------------------------------------------- Korpus
    def _korpus(self):
        self.leiste = tk.Frame(self.root, bg=FLAECHE, width=210)
        self.leiste.pack(side='left', fill='y')
        self.leiste.pack_propagate(False)

        self.inhalt = tk.Frame(self.root, bg=BG)
        self.inhalt.pack(side='right', fill='both', expand=True)

        self._gruppe(t('hf_gruppe_bp'))
        self._reiter('liste', '▤', t('hf_liste'))
        self._reiter('fortschritt', '◧', t('hf_fortschritt'))

        self._gruppe(t('hf_gruppe_einst'))
        self._reiter('allgemein', '⚙', t('hf_allgemein'))
        self._reiter('anzeige', '▭', t('hf_anzeige'))
        self._reiter('ordner', '❒', t('hf_ordner'))
        self._reiter('spiel', '✎', t('hf_spiel'))
        self._reiter('bestand', '↕', t('hf_bestand'))

        # „Was ist neu" und „Über" stellen nichts ein — sie erzählen etwas.
        # Unter der Überschrift „Einstellungen" waren sie falsch einsortiert.
        self._gruppe(t('hf_gruppe_info'))
        self._reiter('wasistneu', '✦', t('hf_wasistneu'))
        self._reiter('ueber', 'ⓘ', t('hf_ueber'))

        # Fortgeschrittenes sitzt unten und ist zugeklappt — sichtbar, aber
        # nicht im Weg. Wer es sucht, findet es; wer es nicht kennt, wird nicht
        # erschlagen.
        self.klapp = tk.Frame(self.leiste, bg=FLAECHE)
        self.klapp.pack(side='bottom', fill='x', pady=(8, 6))
        self.klappknopf = tk.Label(self.klapp, text='▶ ' + t('hf_fortgeschritten'),
                                   bg=FLAECHE, fg=SUB, font=self.f_klein,
                                   cursor='hand2', anchor='w', padx=16, pady=8)
        self.klappknopf.pack(fill='x')
        self.klappknopf.bind('<Button-1>', lambda e: self._klapp_umschalten())
        self.klappinhalt = tk.Frame(self.klapp, bg=FLAECHE)

    def _gruppe(self, text):
        tk.Label(self.leiste, text=text.upper(), bg=FLAECHE, fg=SUB,
                 font=self.f_klein, anchor='w', padx=16,
                 pady=6).pack(fill='x', pady=(10, 0))

    # ⚠ Nur Zeichen aus der Grundebene benutzen. `🗀` und `⇅` liegen darüber und
    # fehlen in der Oberflächenschrift — im Fenster stand statt des Symbols ein
    # Fragezeichen. Auffallen tut das erst im laufenden Fenster, nicht im Code.
    # Prüfen lässt es sich mit `tkfont.Font.measure`: Ein fehlendes Zeichen ist
    # genauso breit wie das amtliche Ersatzzeichen `￿`.
    def _reiter(self, kennung, zeichen, text, wohin=None):
        ziel = wohin if wohin is not None else self.leiste
        zeile = tk.Frame(ziel, bg=FLAECHE, cursor='hand2')
        zeile.pack(fill='x')
        strich = tk.Frame(zeile, bg=FLAECHE, width=3)
        strich.pack(side='left', fill='y')
        z = tk.Label(zeile, text=zeichen, bg=FLAECHE, fg=SUB, font=self.f_zeichen,
                     width=2)
        z.pack(side='left', padx=(10, 4), pady=7)
        b = tk.Label(zeile, text=text, bg=FLAECHE, fg=SUB, font=self.f_grund,
                     anchor='w')
        b.pack(side='left', fill='x', expand=True)

        marke_widget = None
        if neuheiten.ist_neu(kennung, self.version):
            marke_widget = marke(zeile, t('hf_neu'), ACCENT, self.f_klein)
            marke_widget.pack(side='right', padx=10)

        for teil in (zeile, z, b):
            teil.bind('<Button-1>', lambda e, k=kennung: self.oeffnen(k))
        self.knoepfe[kennung] = (zeile, strich, z, b, marke_widget)

    def _klapp_umschalten(self):
        self.fortgeschritten_offen = not self.fortgeschritten_offen
        if self.fortgeschritten_offen:
            self.klappinhalt.pack(fill='x')
            if not self.klappinhalt.winfo_children():
                self._reiter('erkennung', '◎', t('hf_erkennung'), self.klappinhalt)
                self._reiter('diagnose', '⚕', t('hf_diagnose'), self.klappinhalt)
            self.klappknopf.configure(text='▼ ' + t('hf_fortgeschritten'))
        else:
            self.klappinhalt.pack_forget()
            self.klappknopf.configure(text='▶ ' + t('hf_fortgeschritten'))

    # ------------------------------------------------------------ Seitenwahl
    def oeffnen(self, kennung):
        """Eine Seite zeigen — und beim ersten Mal ihren Inhalt bauen."""
        if kennung not in self.seiten:
            self.seiten[kennung] = tk.Frame(self.inhalt, bg=BG)
        if kennung not in self.gezeichnet:
            self.gezeichnet.add(kennung)
            try:
                self._seite_fuellen(kennung, self.seiten[kennung])
            except Exception as ausnahme:
                fehler.merken('hauptfenster.seite:%s' % kennung, ausnahme)
                tk.Label(self.seiten[kennung], text='—', bg=BG, fg=SUB,
                         font=self.f_grund).pack(padx=20, pady=20)

        if self.aktuell:
            self.seiten[self.aktuell].pack_forget()
        self.seiten[kennung].pack(fill='both', expand=True)
        self.aktuell = kennung
        self._reiter_faerben()

        # Die „neu"-Marke hat ihren Zweck erfüllt, sobald man drin war.
        if neuheiten.ist_neu(kennung, self.version):
            neuheiten.gesehen(kennung, self.version)
            eintrag = self.knoepfe.get(kennung)
            if eintrag and eintrag[4] is not None:
                eintrag[4].destroy()
                # ⚠ Und aus der Liste nehmen! Ein zerstörtes Widget bleibt sonst
                # im Tupel stehen, und das nächste Einfärben greift ins Leere
                # (`invalid command name`). Das schlug beim zweiten Reiterwechsel
                # zu — also bei jedem Nutzer sofort.
                zeile, strich, z, b, _ = eintrag
                self.knoepfe[kennung] = (zeile, strich, z, b, None)

    def _reiter_faerben(self):
        for kennung, (zeile, strich, z, b, marke) in self.knoepfe.items():
            an = (kennung == self.aktuell)
            grund = '#1d2634' if an else FLAECHE
            for teil in (zeile, z, b):
                teil.configure(bg=grund)
            if marke is not None:
                marke.hintergrund(grund)
            z.configure(fg=FG if an else SUB)
            b.configure(fg=FG if an else SUB, font=self.f_fett if an else self.f_grund)
            strich.configure(bg=ACCENT if an else FLAECHE)

    def neu_aufbauen(self):
        """Alles neu zeichnen — nach einem Sprachwechsel.

        Texte stehen in der Reiterleiste, in der Titelleiste, in der Fußzeile
        und auf jeder Seite. Einzeln nachzuziehen wäre zwanzig Stellen, die man
        vergessen kann; einmal neu aufbauen ist verlässlicher.
        """
        merker = self.aktuell
        offen = self.fortgeschritten_offen
        for kind in self.root.winfo_children():
            kind.destroy()
        self.seiten, self.gezeichnet, self.knoepfe = {}, set(), {}
        self.aktuell = None
        self._einst = None            # das geliehene Einstellungsfenster ist weg
        self.fortgeschritten_offen = False

        self._titelleiste()
        self._fusszeile()
        self._korpus()
        if offen:
            self._klapp_umschalten()
        self.oeffnen(merker or 'liste')

    def _seite_fuellen(self, kennung, rahmen):
        """Hier hängen die Seiten ein — geliefert von `seiten.py`."""
        from . import seiten
        seiten.bauen(self, kennung, rahmen)

    # ------------------------------------------------------------------ Tat
    def _was_ist_neu(self):
        """Kein eigenes Fenster mehr — die Änderungen sind ein Reiter.

        Ein Fenster über dem Fenster verdeckt genau das, was man gerade
        vergleichen will, und es gibt keinen Grund dafür: Der Platz ist da.
        """
        self.oeffnen('wasistneu')

    def _einrichtung(self):
        from . import assistent
        try:
            assistent.starten(self.root)
        except Exception as ausnahme:
            fehler.merken('hauptfenster.assistent', ausnahme)

    def schliessen(self):
        try:
            if self.beim_schliessen:
                self.beim_schliessen()
        finally:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def _mitgeliefert(name):
    """Pfad zu einer mitgelieferten Datei — im Quellcode wie im fertigen Paket."""
    try:
        basis = getattr(sys, '_MEIPASS', None) or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(basis, name)
    except Exception:
        return None
