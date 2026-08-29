# -*- coding: utf-8 -*-
"""Baut die Oberfläche auf **Englisch** auf und sucht deutschen Text darin.

**Warum es das gibt.** `texte_pruefen.py` liest den Quelltext und sucht Sätze in
Funktionsaufrufen. Das findet viel, aber nicht alles: Steht eine Beschriftung als
Tupelpaar in einer Schleife oder in einem Wörterbuch, ist sie für eine
Quelltext-Prüfung unsichtbar. Genau so blieben die Filterknöpfe auf „Was ist neu"
(*Alles · Neu · Verbessert · Behoben*) monatelang auch in der englischen
Oberfläche deutsch — direkt neben einem sauber übersetzten Änderungstext.
Aufgefallen ist es erst auf einem Bildschirmfoto (gemeldet, 27.08.2026).

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
    """Deutsche Version -> (Schlüssel, englische Version).

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
    # ⚠ Zweite Ernte aus demselben Durchgang: sichtbarer Text, in dem noch die
    # Auszeichnung `**fett**` steht. Tk-Labels können kein Mischformat, also
    # muss sie vor der Anzeige heraus — sonst liest der Nutzer die Sternchen
    # mit. Genau das stand am 28.08.2026 unter rc85 auf "Texte im Spiel":
    # »danach ist das **ganze Spiel** in dieser Sprache«. Gefunden hat es
    # der Autor auf einem Bildschirmfoto, nicht diese Prüfung — die sah nur
    # nach deutschem Text. Jetzt sieht sie auch das.
    marken = set()

    def merken(text):
        if not isinstance(text, str):
            return
        if '**' in text:
            marken.add(text.strip())
        if text.strip() in tabelle:
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
    return tabelle, treffer, marken


def main():
    fehlend = symbole_pruefen()
    if fehlend:
        print('Symbolbilder fehlen:')
        for symbol, art, px in fehlend:
            print('  · %s als %s — %s/%d/%s-*.png fehlt'
                  % (symbol, art, 'assets/symbole', px, symbol))
        print('  → in tools/symbole_bauen.py eintragen und neu bauen.\n')
    else:
        print('Symbolbilder: alle da.\n')

    print('Oberfläche auf Englisch:')
    tabelle, treffer, marken = pruefe()
    print('  %d Textpaare, die sich unterscheiden' % len(tabelle))

    if marken:
        print('\n%d sichtbare(r) Text(e) mit **-Auszeichnung — Tk zeigt die '
              'Sternchen mit:' % len(marken))
        for text in sorted(marken):
            print('  · %s' % (text[:100] + ('…' if len(text) > 100 else '')))
        print('\n  → durch _ohne_marken() schicken, bevor der Text ins Label '
              'geht (scbp/seiten.py).')
    else:
        print('  keine **-Auszeichnung im sichtbaren Text')

    if not treffer:
        print('\nKein deutscher Text in der englischen Oberfläche.')
        return 1 if (fehlend or marken) else 0
    print('\n%d deutsche Stelle(n) — sie stehen fest im Code statt in '
          'sprache.py:' % len(treffer))
    for deutsch, (schluessel, englisch) in sorted(treffer.items()):
        print('  · "%s"  →  %s sagt "%s"' % (deutsch, schluessel, englisch))
    print('\nDie Stelle im Code suchen und durch t(\'schluessel\') ersetzen.')
    return 1




# ---------------------------------------------------------------------------
# Zweite Prüfung: fehlen Symbolbilder?
#
# ⚠ `zeichen.bild()` gibt bei einer fehlenden Datei still `None` zurück — mit
# Absicht: Ein fehlendes Symbol ist ein Schönheitsfehler, kein Grund, das
# Programm anzuhalten. Genau diese Nachsicht macht den Fehler aber unsichtbar.
#
# Am 27.08.2026 aufgeschlagen: `schliessen` stand nur unter KNOPF_SYMBOLE, wurde
# aber mit `zeichen.zeile()` benutzt. In Zeilengröße gab es die Datei nicht, und
# im Herkunftskasten der Bauplan-Liste blieb statt des Kreuzes eine leere Lücke.
# Aufgefallen ist es einem Nutzer, nicht dem Selbsttest.

import re                                                    # noqa: E402


def symbole_pruefen():
    """Jedes im Code angeforderte Symbol muss es in seiner Größe auch geben."""
    from scbp import zeichen

    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    verlangt = set()
    for ordner, _, dateien in os.walk(os.path.join(wurzel, 'scbp')):
        for name in dateien:
            if not name.endswith('.py'):
                continue
            text = io_lesen(os.path.join(ordner, name))
            for art, symbol in re.findall(
                    r"zeichen\.(knopf|zeile)\(\s*[^,]+,\s*'([a-z_]+)'", text):
                verlangt.add((symbol, art))
            # ⚠ `symbol_tauschen('name')` wird **schwächer** geprüft: nur, ob es
            # das Symbol überhaupt gibt. Ob an der Stelle ein Knopf oder eine
            # Zeile steht, verrät der Text allein nicht — beide Größen zu
            # verlangen brächte Fehlalarme (`zuklappen` hängt nur an Zeilen und
            # braucht keine Knopfgrößen). Das fängt Tippfehler, keine
            # Größenfehler.
            for symbol in re.findall(r"symbol_tauschen\('([a-z_]+)'\)", text):
                verlangt.add((symbol, 'irgendeine'))

    fehlt = []
    for symbol, art in sorted(verlangt):
        if art == 'irgendeine':
            alle = set(zeichen.KNOPF.values()) | set(zeichen.ZEILE.values())
            if not any(os.path.exists(os.path.join(
                    wurzel, 'assets', 'symbole', str(px), '%s-grau.png' % symbol))
                    for px in alle):
                fehlt.append((symbol, art, 0))
            continue
        satz = zeichen.KNOPF if art == 'knopf' else zeichen.ZEILE
        for stufe, px in sorted(satz.items()):
            pfad = os.path.join(wurzel, 'assets', 'symbole', str(px),
                                '%s-grau.png' % symbol)
            if not os.path.exists(pfad):
                fehlt.append((symbol, art, px))
    return sorted(set(fehlt))


def io_lesen(pfad):
    with open(pfad, encoding='utf-8') as f:
        return f.read()


if __name__ == '__main__':
    sys.exit(main())
