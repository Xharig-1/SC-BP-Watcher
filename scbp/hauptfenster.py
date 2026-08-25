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

# Wie viel Streichweg auf dem Trackpad eine Zeile ergibt. Ein Trackpad meldet
# viele kleine Schritte statt Rasten; ohne Teiler säuselt die Liste am Finger
# vorbei. Der Wert ist ein Startwert zum Nachjustieren — größer heißt ruhiger.
TRACKPAD_TEILER = 12

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



def ecken(x1, y1, x2, y2, r):
    """Die Punktfolge eines abgerundeten Rechtecks — für `coords`.

    Wird gebraucht, wenn ein schon gezeichnetes Rechteck seine Größe ändert:
    `create_polygon` legt die Punkte einmal fest, `coords` schiebt sie nach.
    """
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def rundrahmen(eltern, grund, rand, radius=8, grundfarbe=None):
    """Ein Kasten mit runden Ecken, in den beliebiger Inhalt kommt.

    Tk kann Rahmen nur eckig — deshalb liegt hinter dem Inhalt eine Leinwand
    mit einem gemalten Rechteck, und der Inhalt sitzt als Fenster darauf. Die
    Leinwand zieht ihre Höhe nach, sobald der Inhalt steht; sonst bliebe sie
    auf ihrer Anfangsgröße und schnitte alles ab.

    Zurück kommt der innere Rahmen — dort hinein wird gepackt wie gewohnt.
    Am Rückgabewert hängen `.leinwand` und `.form`, falls die Randfarbe später
    wechseln soll (etwa bei einer Auswahl).
    """
    grundfarbe = grundfarbe or eltern.cget('bg')
    halter = tk.Frame(eltern, bg=grundfarbe)
    leinwand = tk.Canvas(halter, bg=grundfarbe, highlightthickness=0, bd=0,
                         height=10)
    leinwand.pack(fill='both', expand=True)
    innen = tk.Frame(leinwand, bg=grund)
    form = _rundes_rechteck(leinwand, 1, 1, 100, 100, radius=radius,
                            fill=grund, outline=rand, width=1)
    # ⚠ Ein per `create_window` eingesetztes Widget liegt in Tk IMMER über
    # allem Gemalten — die Zeichenreihenfolge gilt dafür nicht. Säße der Inhalt
    # bündig in der Ecke, deckte sein rechteckiger Hintergrund die Rundung ab,
    # und der Kasten sähe trotz gemaltem Bogen eckig aus. Deshalb rückt der
    # Inhalt um die halbe Rundung ein; dort bleibt der Bogen frei.
    # Der ganze Radius, nicht die Hälfte: Bei halbem Einzug deckt der Inhalt
    # die obere Hälfte des Bogens ab, und im Kasten sitzt sichtbar eine zweite,
    # eckige Kante — das sah nach doppeltem Rahmen aus.
    einzug = radius
    fenster_id = leinwand.create_window(einzug, einzug, window=innen,
                                        anchor='nw')

    def nachziehen(_=None):
        # ⚠ Solange nichts gezeichnet ist, meldet `winfo_width` eine 1. Dann
        # die gewünschte Breite nehmen — sonst bliebe das Rechteck auf seinen
        # Anfangskoordinaten stehen, seine Rundungen lägen außerhalb der
        # Leinwand, und der Kasten sähe wieder eckig aus. Genau das ist bei den
        # schmalen Zahlenfeldern passiert.
        breite = leinwand.winfo_width()
        if breite < 10:
            breite = leinwand.winfo_reqwidth()
        hoehe = innen.winfo_reqheight()
        if breite < 10:
            return
        leinwand.configure(height=hoehe + einzug * 2)
        leinwand.itemconfigure(fenster_id, width=breite - einzug * 2)
        leinwand.coords(form, *ecken(1, 1, breite - 1,
                                     hoehe + einzug * 2 - 1, radius))

    innen.bind('<Configure>', nachziehen)
    leinwand.bind('<Configure>', nachziehen)
    leinwand.bind('<Map>', nachziehen)
    # Merkmal für die Randprüfung: Dieser Rahmen wird bewusst auf die
    # Kastenbreite gezwungen — sein Wunsch nach mehr Platz ist kein Fehler,
    # der Text darin bricht um. Ohne die Markierung meldet jede Karte einen
    # Fehlalarm.
    innen.auf_mass_gesetzt = True
    innen.nachziehen = nachziehen
    innen.halter = halter
    innen.leinwand = leinwand
    innen.form = form
    return innen


def rundes_feld(eltern, textvariable, schrift, grund, rand, akzent, fg,
                breite=None, **kw):
    """Ein Eingabefeld mit runden Ecken — überall im Programm dasselbe.

    Das Feld selbst bleibt ein gewöhnliches `Entry` (nur so lässt sich tippen),
    aber ohne eigenen Rand; den runden Rand malt die Leinwand darunter. Beim
    Hineinklicken wechselt der Rand auf die Akzentfarbe, damit man sieht, wo
    man schreibt.
    """
    schrift = _als_schrift(schrift)
    radius = 8
    polster = 6
    hoehe = schrift.metrics('linespace') + polster * 2
    leinwand = tk.Canvas(eltern, height=hoehe, bg=eltern.cget('bg'),
                         highlightthickness=0, bd=0)
    form = _rundes_rechteck(leinwand, 1, 1, 100, hoehe - 1, radius=radius,
                            fill=grund, outline=rand, width=1)
    if textvariable is not None:
        kw['textvariable'] = textvariable
    feld = tk.Entry(leinwand, bg=grund, fg=fg, font=schrift, relief='flat',
                    bd=0, highlightthickness=0, insertbackground=fg, **kw)
    fenster_id = leinwand.create_window(polster + 2, hoehe / 2.0, window=feld,
                                        anchor='w')

    def nachziehen(_=None):
        b = leinwand.winfo_width()
        if b < 10:
            b = leinwand.winfo_reqwidth()
        if b < 10:
            return
        leinwand.coords(form, *ecken(1, 1, b - 1, hoehe - 1, radius))
        leinwand.itemconfigure(fenster_id, width=b - (polster + 2) * 2)

    leinwand.bind('<Configure>', nachziehen)
    leinwand.bind('<Map>', nachziehen)
    if breite:
        # Feste Breite: so viele Ziffern plus Luft. Ohne das zieht `fill='x'`
        # der Zeile das Feld über die halbe Seite.
        leinwand.configure(width=schrift.measure('0') * breite + polster * 4)
    feld.halter = leinwand
    leinwand.after(0, nachziehen)
    feld.bind('<FocusIn>',
              lambda e: leinwand.itemconfigure(form, outline=akzent), add='+')
    feld.bind('<FocusOut>',
              lambda e: leinwand.itemconfigure(form, outline=rand), add='+')
    return feld



def _als_schrift(schrift):
    """Eine Schrift als messbares Objekt.

    Die älteren Fenster geben ihre Schrift als Tupel `('Helvetica', 10)`
    weiter — damit lässt sich zeichnen, aber nicht messen. Ein gemalter Knopf
    braucht aber die Breite des Wortes, sonst schneidet er es ab. Also hier
    einmal umwandeln, statt an jeder Stelle daran zu denken.
    """
    if isinstance(schrift, (tuple, list)):
        return tkfont.Font(family=schrift[0], size=schrift[1],
                           weight=schrift[2] if len(schrift) > 2 else 'normal')
    return schrift



def rundbalken(eltern, hoehe, anteil, grund, leer, voll, breite=None):
    """Ein Fortschrittsbalken mit runden Enden.

    Zwei ineinandergeschobene Rahmen wären einfacher, hätten aber scharfe
    Kanten — im Rest des Programms ist nichts scharfkantig. Also wieder eine
    Leinwand: eine Rille in ganzer Länge, darüber der gefüllte Teil.

    Der gefüllte Teil zieht mit, wenn sich die Breite ändert (Fenster größer,
    Seitenleiste ein- oder ausgeklappt) — deshalb `<Configure>` statt einer
    einmal ausgerechneten Pixelzahl.
    """
    r = hoehe / 2.0
    c = tk.Canvas(eltern, height=hoehe, bg=grund, highlightthickness=0, bd=0)
    if breite:
        c.configure(width=breite)
    rille = _rundes_rechteck(c, 0, 0, 100, hoehe, radius=r, fill=leer,
                             outline='')
    fuellung = _rundes_rechteck(c, 0, 0, 10, hoehe, radius=r, fill=voll,
                                outline='')

    def nachziehen(_=None):
        b = c.winfo_width()
        if b < 4:
            return
        c.coords(rille, *ecken(0, 0, b, hoehe, r))
        if anteil <= 0:
            c.itemconfigure(fuellung, state='hidden')
            return
        c.itemconfigure(fuellung, state='normal')
        # Mindestens so breit wie hoch: Ein Balken bei 1 % wäre sonst ein
        # Strich, den man für einen Zeichenfehler hält.
        voll_breite = max(hoehe, b * anteil)
        c.coords(fuellung, *ecken(0, 0, voll_breite, hoehe, r))

    c.bind('<Configure>', nachziehen)
    return c


def rad_anschliessen(leinwand):
    """Das Mausrad an eine Rollfläche hängen — für das ganze Fenster.

    ⚠ Zwei Fehler steckten hier, und beide zusammen ließen das Rad wirkungslos
    aussehen, während der Rollbalken von Hand funktionierte:

    1. **Die Rechnung.** Vorher stand hier `int(-1 * e.delta / 120)`. Windows
       meldet ±120, Linux meldet sich über Button-4/5 — beides ging auf.
       macOS meldet aber **±1**, und `int(-1/120)` ist **0**: kein Ausschlag.
       Deshalb zählt jetzt nur die Richtung, nie der Betrag.

    2. **Die Bindung.** Vorher hingen die Ereignisse an drei Widgets
       (Leinwand, Innenrahmen, Polster). Tk schickt das Rad aber an das
       Element **unter dem Zeiger**, und das ist fast immer eine Beschriftung
       oder ein Kasten darin — dort war nichts gebunden. Also greift die
       Bindung jetzt am ganzen Fenster, und der Griff sucht sich die
       Rollfläche unter dem Zeiger.

    3. **Und der Grund, warum das trotzdem nicht wirkte:** Die Bauplan-Liste
       rief `bind_all` **ohne** `add='+'` auf. Das ersetzt jede vorher
       gesetzte Bindung im ganzen Fenster — und weil die Liste die Startseite
       ist, war die Bindung der Seiten sofort wieder weg. Danach rollte das
       Rad überall nur noch die Liste, auch wenn die gar nicht zu sehen war.
       Deshalb hängen jetzt **alle** Rollflächen an dieser einen Stelle.

    4. **Trackpad.** Gemessen mit `tools/rad_messen.py`: Vom Trackpad kommt
       **kein einziges** `<MouseWheel>` an — nicht etwa ein zu kleiner Wert,
       sondern gar nichts. Seit Tk 8.7 gibt es dafür ein eigenes Ereignis,
       `<TouchpadScroll>`, und erst das liefert die Streichgesten. Es feuert
       viel häufiger als eine Radraste und trägt beide Richtungen in **einer**
       Zahl: untere 16 Bit waagerecht, obere 16 Bit senkrecht.

       Ältere Tk-Fassungen (8.6, verbreitet unter Linux) kennen das Ereignis
       nicht — dort wirft das Binden einen Fehler, der abgefangen wird. Dort
       melden sich Trackpads ohnehin als Button-4/5.

       Weil beide Wege kleine Beträge liefern, werden sie **aufaddiert**, bis
       eine ganze Zeile zusammenkommt; der Rest bleibt für das nächste
       Ereignis stehen.
    """
    wurzel = leinwand.winfo_toplevel()
    if not hasattr(wurzel, 'rollflaechen'):
        wurzel.rollflaechen = []
        # Was noch keine ganze Zeile ergeben hat, wartet hier auf den Rest.
        angesammelt = {'wert': 0.0}

        def schritte_aus(e):
            """Wie viele Zeilen sollen es sein? Negativ heißt nach oben."""
            nummer = getattr(e, 'num', 0)
            if nummer == 4:                      # Linux: Rad nach oben
                return -1
            if nummer == 5:                      # Linux: Rad nach unten
                return 1
            betrag = float(getattr(e, 'delta', 0) or 0)
            if betrag == 0:
                return 0
            if abs(betrag) >= 120:               # Windows: eine Raste = 120
                betrag /= 120.0
            angesammelt['wert'] += betrag
            ganze = int(angesammelt['wert'])     # schneidet Richtung null ab
            angesammelt['wert'] -= ganze
            return -ganze                        # nach oben = negativ

        def flaeche_unter(e):
            """Die registrierte Rollfläche unter dem Mauszeiger — oder nichts."""
            unter = wurzel.winfo_containing(e.x_root, e.y_root)
            while unter is not None:
                if unter in wurzel.rollflaechen:
                    return unter
                unter = getattr(unter, 'master', None)
            return None

        def rollen(e):
            ziel = flaeche_unter(e)
            if ziel is None:
                return
            schritte = schritte_aus(e)
            if not schritte:
                return
            try:
                ziel.yview_scroll(schritte, 'units')
            except tk.TclError:
                pass

        def streichen(e):
            """Trackpad: beide Richtungen stecken gepackt in einer Zahl."""
            ziel = flaeche_unter(e)
            if ziel is None:
                return
            roh = int(getattr(e, 'delta', 0) or 0)
            senkrecht = (roh >> 16) & 0xFFFF
            if senkrecht >= 0x8000:          # als vorzeichenbehaftet lesen
                senkrecht -= 0x10000
            if not senkrecht:
                return
            # Ein Streich meldet viele kleine Schritte. `TEILER` bestimmt, wie
            # weit eine Geste trägt — kleiner heißt schneller.
            angesammelt['wert'] += senkrecht / float(TRACKPAD_TEILER)
            ganze = int(angesammelt['wert'])
            angesammelt['wert'] -= ganze
            if not ganze:
                return
            # ⚠ Kein Minus wie beim Rad: `<TouchpadScroll>` zählt andersherum
            # als `<MouseWheel>`. Mit dem Vorzeichen des Rades rollte die Liste
            # genau falsch herum. Die vom Nutzer eingestellte Richtung
            # („natürliches Scrollen") hat das System da schon eingerechnet.
            try:
                ziel.yview_scroll(ganze, 'units')
            except tk.TclError:
                pass

        for ereignis in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            wurzel.bind_all(ereignis, rollen, add='+')
        try:
            wurzel.bind_all('<TouchpadScroll>', streichen, add='+')
        except tk.TclError:
            # Tk 8.6 und älter kennen das Ereignis nicht. Dort melden sich
            # Trackpads als Button-4/5, also fehlt nichts.
            pass

    if leinwand not in wurzel.rollflaechen:
        wurzel.rollflaechen.append(leinwand)



def rundleiste(eltern, leinwand, grund=None, breite=10):
    """Eine Rollleiste mit runden Enden — statt der des Betriebssystems.

    ⚠ `tk.Scrollbar` ist das einzige Bedienelement, das sich nicht einfärben
    lässt: Tk reicht es an das System durch. Unter Linux ist sie grau, auf dem
    Mac hellweiß — und damit der einzige Fleck im Fenster, der aus dem Bild
    fällt. Die Entwurfsvorschau hatte dort eine schmale, abgerundete Leiste in
    `#2b3547`; genau die wird hier nachgebaut.

    Bedienung wie gewohnt: ziehen, und ein Klick daneben springt eine Seite
    weiter. `leinwand` ist die Rollfläche, an der sie hängt.
    """
    grund = grund or BG
    rille_farbe, griff_farbe, griff_hell = BG, '#2b3547', '#3a4658'
    r = breite / 2.0

    c = tk.Canvas(eltern, width=breite, bg=grund, highlightthickness=0, bd=0)
    rille = c.create_rectangle(0, 0, breite, 10, fill=rille_farbe, outline='')
    griff = _rundes_rechteck(c, 0, 0, breite, 30, radius=r,
                             fill=griff_farbe, outline='')
    c.auf_mass_gesetzt = True        # die Randprüfung soll sie nicht melden

    lage = {'anfang': 0.0, 'ende': 1.0, 'griff_ab': 0, 'zieht': False}

    def nachziehen(*_):
        hoehe = c.winfo_height()
        if hoehe < 4:
            return
        c.coords(rille, 0, 0, breite, hoehe)
        anfang, ende = lage['anfang'], lage['ende']
        if ende - anfang >= 0.999:   # nichts zu rollen — Griff verschwindet
            c.itemconfigure(griff, state='hidden')
            return
        c.itemconfigure(griff, state='normal')
        oben = anfang * hoehe
        # Der Griff bleibt greifbar, auch wenn 700 Baupläne in der Liste
        # stehen und er rechnerisch drei Pixel hoch wäre.
        unten = max(oben + breite * 2.4, ende * hoehe)
        c.coords(griff, *ecken(0, oben, breite, min(unten, hoehe), r))

    def setzen(anfang, ende):
        """Ruft Tk auf, wenn sich der sichtbare Ausschnitt ändert."""
        lage['anfang'], lage['ende'] = float(anfang), float(ende)
        nachziehen()

    def springen(e):
        hoehe = c.winfo_height() or 1
        spanne = lage['ende'] - lage['anfang']
        oben, unten = lage['anfang'] * hoehe, lage['ende'] * hoehe
        if oben <= e.y <= unten:                  # auf dem Griff: ziehen
            lage['zieht'] = True
            lage['griff_ab'] = e.y - oben
            return
        ziel = max(0.0, min(1.0, (e.y / hoehe) - spanne / 2.0))
        leinwand.yview_moveto(ziel)

    def ziehen(e):
        if not lage['zieht']:
            return
        hoehe = c.winfo_height() or 1
        leinwand.yview_moveto(max(0.0, min(1.0, (e.y - lage['griff_ab']) / hoehe)))

    def loslassen(_=None):
        lage['zieht'] = False

    def rein(_=None):
        c.itemconfigure(griff, fill=griff_hell)

    def raus(_=None):
        if not lage['zieht']:
            c.itemconfigure(griff, fill=griff_farbe)

    c.bind('<Configure>', nachziehen)
    c.bind('<Button-1>', springen)
    c.bind('<B1-Motion>', ziehen)
    c.bind('<ButtonRelease-1>', loslassen)
    c.bind('<Enter>', rein)
    c.bind('<Leave>', raus)
    # ⚠ `set` heißt hier englisch, weil Tk selbst diesen Namen aufruft:
    # `leinwand.configure(yscrollcommand=leiste.set)`. `setzen` steht daneben,
    # damit der Rest des Programms bei seiner Sprache bleiben kann.
    c.set = setzen
    c.setzen = setzen
    return c


def rundknopf(eltern, text, tat, schrift, grund, fuellung, rand, fg,
              radius=6, polster=(10, 5), cursor='hand2'):
    """Ein klickbarer Knopf mit runden Ecken — der Standard im ganzen Programm.

    Ein `Label` mit Hintergrundfarbe wäre einfacher, sähe aber überall eckig
    aus; das Programm hat aber genau eine Formensprache. Deshalb wieder eine
    kleine Leinwand mit gemaltem Rechteck.

    Am Rückgabewert hängt `.setzen(fuellung, rand, fg)` — damit lässt sich der
    Knopf später umfärben (an/aus, ausgewählt/nicht), ohne ihn neu zu bauen.
    """
    schrift = _als_schrift(schrift)
    breite = schrift.measure(text) + polster[0] * 2
    hoehe = schrift.metrics('linespace') + polster[1] * 2
    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=grund,
                  highlightthickness=0, bd=0, cursor=cursor)
    form = _rundes_rechteck(c, 1, 1, breite - 1, hoehe - 1, radius=radius,
                            fill=fuellung, outline=rand, width=1)
    beschriftung = c.create_text(breite / 2.0, hoehe / 2.0, text=text,
                                 fill=fg, font=schrift, anchor='center')

    def setzen(fuellung=None, neuer_rand=None, neues_fg=None):
        neue_fuellung = fuellung
        if neue_fuellung:
            c.itemconfigure(form, fill=neue_fuellung)
        if neuer_rand:
            c.itemconfigure(form, outline=neuer_rand)
        if neues_fg:
            c.itemconfigure(beschriftung, fill=neues_fg)

    c.setzen = setzen
    c.form = form
    c.beschriftung = beschriftung
    c.ist_knopf = True          # damit tools/randpruefung.py ihn prüft
    if tat:
        c.bind('<Button-1>', lambda e: tat())
    return c


def rundwahl(eltern, eintraege, gewaehlt, beim_waehlen, schrift, grund=None,
             breite=None):
    """Ein Auswahlfeld im Hausstil — Knopf mit ▾, der eine Liste aufklappt.

    ⚠ Warum selbst gebaut: Tk bringt `OptionMenu` und `ttk.Combobox` mit, und
    beide sind Systemelemente — auf dem Mac ein graues Aqua-Feld, unter Windows
    ein anderes, unter Linux je nach Oberfläche wieder anders. Das Programm hat
    aber genau eine Formensprache, und ein Auswahlfeld ist zu auffällig, um
    davon ausgenommen zu werden.

    `eintraege` sind Paare `(wert, beschriftung)`. Ein Eintrag mit dem Wert `''`
    ist der „alle"-Fall; ist etwas anderes gewählt, färbt sich das Feld in der
    Akzentfarbe — so sieht man auf einen Blick, dass ein Filter greift, ohne
    jede Liste aufklappen zu müssen.

    Die aufgeklappte Liste ist ein rahmenloses Fenster: Nur so kann sie über
    den Rand ihres Elternrahmens hinausragen, und genau das muss sie, wenn
    zwanzig Arten zur Wahl stehen.
    """
    grund = grund or BG
    s = _als_schrift(schrift)
    zustand = {'wert': gewaehlt, 'liste': None}

    def beschriftung_zu(wert):
        for w, text in eintraege:
            if w == wert:
                return text
        return eintraege[0][1] if eintraege else ''

    if breite is None:
        breite = max(s.measure(text) for _, text in eintraege) + 42
    hoehe = s.metrics('linespace') + 14

    c = tk.Canvas(eltern, width=breite, height=hoehe, bg=grund,
                  highlightthickness=0, bd=0, cursor='hand2')
    form = _rundes_rechteck(c, 1, 1, breite - 1, hoehe - 1, radius=5,
                            fill='#0c1017', outline=LINIE, width=1)
    text_id = c.create_text(11, hoehe / 2.0, text=beschriftung_zu(gewaehlt),
                            fill=FG, font=s, anchor='w')
    pfeil = c.create_text(breite - 12, hoehe / 2.0, text='▾', fill=SUB,
                          font=s, anchor='e')
    c.ist_knopf = True          # die Randprüfung soll ihn messen

    def faerben():
        gesetzt = bool(zustand['wert'])
        c.itemconfigure(form, outline=ACCENT if gesetzt else LINIE)
        c.itemconfigure(text_id, fill=ACCENT if gesetzt else FG)
        c.itemconfigure(pfeil, fill=ACCENT if gesetzt else SUB)

    def zuklappen(_=None):
        if zustand['liste'] is not None:
            try:
                zustand['liste'].destroy()
            except tk.TclError:
                pass
            zustand['liste'] = None

    def waehlen(wert):
        zuklappen()
        zustand['wert'] = wert
        c.itemconfigure(text_id, text=beschriftung_zu(wert))
        faerben()
        beim_waehlen(wert)

    def aufklappen(_=None):
        if zustand['liste'] is not None:
            zuklappen()
            return
        fenster = tk.Toplevel(c)
        fenster.overrideredirect(True)        # kein Titelbalken, kein Rahmen
        fenster.configure(bg=LINIE)
        zustand['liste'] = fenster

        # ⚠ Die Liste muss rollen können. Bei 25 Arten ist sie höher als der
        # Platz unter dem Feld — steht das Fenster weit unten, waren die
        # letzten Einträge unerreichbar. Also: Höhe begrenzen, eigene
        # Rollfläche, und wenn unten kein Platz ist, klappt sie nach oben.
        aussen = tk.Frame(fenster, bg=FLAECHE)
        aussen.pack(fill='both', expand=True, padx=1, pady=1)
        leinwand = tk.Canvas(aussen, bg=FLAECHE, highlightthickness=0, bd=0)
        innen = tk.Frame(leinwand, bg=FLAECHE)
        fenster_id = leinwand.create_window((0, 0), window=innen, anchor='nw')

        for wert, text in eintraege:
            an = (wert == zustand['wert'])
            zeile = tk.Label(innen, text=text, bg=FLAECHE,
                             fg=ACCENT if an else FG, font=s, anchor='w',
                             padx=11, pady=4, cursor='hand2')
            zeile.pack(fill='x')
            zeile.bind('<Button-1>', lambda e, w=wert: waehlen(w))
            zeile.bind('<Enter>', lambda e, z=zeile: z.configure(bg=BAR))
            zeile.bind('<Leave>', lambda e, z=zeile: z.configure(bg=FLAECHE))

        c.update_idletasks()
        innen.update_idletasks()
        gebraucht_hoehe = innen.winfo_reqheight()
        gebraucht_breite = max(breite, innen.winfo_reqwidth() + 2)

        x = c.winfo_rootx()
        unten = c.winfo_rooty() + hoehe + 2
        schirm = c.winfo_screenheight()
        # So viel Platz ist nach unten bzw. nach oben — mit etwas Luft zum Rand.
        platz_unten = schirm - unten - 20
        platz_oben = c.winfo_rooty() - 20
        nach_oben = gebraucht_hoehe > platz_unten and platz_oben > platz_unten
        sicht = min(gebraucht_hoehe, max(platz_oben if nach_oben
                                         else platz_unten, 120))
        y = (c.winfo_rooty() - sicht - 2) if nach_oben else unten

        leinwand.configure(width=gebraucht_breite - 2, height=sicht)
        leinwand.pack(side='left', fill='both', expand=True)
        if gebraucht_hoehe > sicht:
            leiste = rundleiste(aussen, leinwand, grund=FLAECHE, breite=8)
            leiste.pack(side='right', fill='y')
            leinwand.configure(yscrollcommand=leiste.set)
        leinwand.configure(scrollregion=(0, 0, gebraucht_breite,
                                         gebraucht_hoehe))
        leinwand.itemconfigure(fenster_id, width=gebraucht_breite - 2)
        rad_anschliessen(leinwand)

        fenster.geometry('%dx%d+%d+%d' % (gebraucht_breite, sicht + 2, x, y))
        fenster.lift()
        # Ein Klick irgendwo anders schließt die Liste — sonst bleibt sie
        # stehen, sobald man es sich anders überlegt.
        fenster.bind('<FocusOut>', zuklappen)
        fenster.focus_set()

    def stumm_setzen(wert):
        """Anzeige umstellen, ohne den Rückruf auszulösen.

        Gebraucht beim Zurücksetzen mehrerer Felder auf einmal: Sonst löst
        jedes einzelne einen vollen Neuaufbau der Liste aus.
        """
        zuklappen()
        zustand['wert'] = wert
        c.itemconfigure(text_id, text=beschriftung_zu(wert))
        faerben()

    c.bind('<Button-1>', aufklappen)
    faerben()
    c.setzen = waehlen
    c.stumm_setzen = stumm_setzen
    c.wert = lambda: zustand['wert']
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
