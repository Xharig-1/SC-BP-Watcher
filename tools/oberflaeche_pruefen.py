# -*- coding: utf-8 -*-
"""Baut die Oberfläche auf **Englisch** auf und sucht deutschen Text darin.

**Warum es das gibt.** `texte_pruefen.py` liest den Quelltext und sucht Sätze in
Funktionsaufrufen. Das findet viel, aber nicht alles: Steht eine Beschriftung als
Tupelpaar in einer Schleife oder in einem Wörterbuch, ist sie für eine
Quelltext-Prüfung unsichtbar. Genau so blieben die Filterknöpfe auf „Was ist neu"
(*Alles · Neu · Verbessert · Behoben*) monatelang auch in der englischen
Oberfläche deutsch — direkt neben einem sauber übersetzten Änderungstext.
Aufgefallen ist es erst auf einem Bildschirmfoto (der Autor, 27.08.2026).

**Der andere Weg.** Nicht den Code fragen, sondern das fertige Fenster: Sprache
auf Englisch stellen, alle Seiten aufbauen, jeden sichtbaren Text einsammeln —
und nachsehen, ob einer davon **wörtlich** in der deutschen Spalte von
`sprache.py` steht. Ein solcher Text kann nur fest im Code stehen.

Das ist zielsicher, weil es nichts raten muss:

* Keine Fehlalarme durch Bauplan-Namen, Pfade oder Zahlen — die stehen nicht in
  `sprache.py`.
* Keine Fehlalarme durch Texte, die in beiden Sprachen gleich lauten — die
  werden vorher aussortiert.
* Nachgemessen am 27.08.2026: 541 unterscheidbare Textpaare, **0** Beanstandungen
  am sauberen Stand — und alle 4 Stellen gefunden, sobald der Fehler wieder
  eingebaut wurde.

⚠ **Die Leinwand nicht vergessen.** Chips und Marken sind *gezeichnet*, nicht
beschriftet; ihr Text hängt an einem Canvas-Element und ist über `cget('text')`
nicht zu erreichen. Ohne den Canvas-Teil unten findet diese Prüfung ausgerechnet
den Fall nicht, für den sie gebaut wurde — erst der zweite Anlauf hat gegriffen.

    python3 tools/oberflaeche_pruefen.py
"""

import os
import sys
import tkinter as tk

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

# Eine Wegwerf-Ablage, damit die Prüfung nichts am eigenen Stand ändert.
os.environ.setdefault('SC_BP_HOME', '/tmp/sc-bp-oberflaechenpruefung')
os.environ.setdefault('SC_BP_NO_NET', '1')

from scbp import sprache                                  # noqa: E402
from scbp.hauptfenster import Hauptfenster                 # noqa: E402

SEITEN = ('liste', 'fortschritt', 'allgemein', 'anzeige', 'spiel', 'bestand',
          'wasistneu', 'ueber', 'serverstatus', 'danke',
          'ordner', 'erkennung', 'diagnose')


def _sollbestand():
    """Deutsche Fassung -> (Schlüssel, englische Fassung).

    Nur Paare, die sich **unterscheiden**: Was in beiden Sprachen gleich heißt
    („Discord", „Star Citizen"), darf in der englischen Oberfläche stehen.
    """
    tabelle = {}
    for schluessel, paar in sprache.TEXTE.items():
        if (isinstance(paar, tuple) and len(paar) == 2
                and all(isinstance(t, str) for t in paar)
                and paar[0].strip() != paar[1].strip()):
            tabelle[paar[0].strip()] = (schluessel, paar[1].strip())
    return tabelle


def pruefe():
    tabelle = _sollbestand()
    sprache.setzen('en')

    wurzel = tk.Tk()
    wurzel.withdraw()
    fenster = Hauptfenster(wurzel, version='pruefung')
    treffer = {}

    def merken(text):
        if isinstance(text, str) and text.strip() in tabelle:
            treffer[text.strip()] = tabelle[text.strip()]

    def sammeln(widget):
        try:
            merken(widget.cget('text'))
        except Exception:
            pass
        if isinstance(widget, tk.Canvas):
            for teil in widget.find_all():
                try:
                    merken(widget.itemcget(teil, 'text'))
                except Exception:
                    pass
        for kind in widget.winfo_children():
            sammeln(kind)

    for seite in SEITEN:
        try:
            fenster.oeffnen(seite)
            fenster.root.update()
            sammeln(fenster.root)
        except Exception as ausnahme:
            print('  ! Seite %s ließ sich nicht aufbauen: %s' % (seite, ausnahme))

    try:
        wurzel.destroy()
    except Exception:
        pass
    return tabelle, treffer


def main():
    print('Oberfläche auf Englisch:')
    tabelle, treffer = pruefe()
    print('  %d Textpaare, die sich unterscheiden' % len(tabelle))
    if not treffer:
        print('\nKein deutscher Text in der englischen Oberfläche.')
        return 0
    print('\n%d deutsche Stelle(n) — sie stehen fest im Code statt in '
          'sprache.py:' % len(treffer))
    for deutsch, (schluessel, englisch) in sorted(treffer.items()):
        print('  · "%s"  →  %s sagt "%s"' % (deutsch, schluessel, englisch))
    print('\nDie Stelle im Code suchen und durch t(\'schluessel\') ersetzen.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
