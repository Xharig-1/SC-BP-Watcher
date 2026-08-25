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
Findet sichtbare Texte, die nicht durch `t()` laufen.

Warum es dieses Werkzeug gibt: `tools/sprachen_pruefen.py` schaut auf README,
CHANGELOG und ROADMAP — also auf die Dokumente. Die Oberfläche selbst hat es
nie geprüft. Deshalb konnte es passieren, dass die englischen Seiten an einem
guten Dutzend Stellen deutschen Text zeigten, ohne dass etwas Alarm schlug.

Gesucht wird im Quelltext (nicht im laufenden Fenster): Jeder Aufruf, der einen
sichtbaren Text bekommt — `text=`, `title=` und die Hausbausteine `rundknopf`,
`marke`, `_feld` und Verwandte — und dort eine feste Zeichenkette stehen hat
statt eines `t('schluessel')`.

Rauschen wird ausgesiebt: reine Platzhalter (`%d / %d`), einzelne Zeichen
(`▶`, `·`), Eigennamen und technische Schlüsselwörter. Was übrig bleibt, ist
ein Satz, den ein Mensch liest — und der damit in `scbp/sprache.py` gehört.

Benutzung:

    python3 tools/texte_pruefen.py            # alle Oberflächen-Dateien
    python3 tools/texte_pruefen.py scbp/seiten.py

Rückgabe 0, wenn nichts gefunden wurde — damit taugt es für den Selbsttest.
"""
import ast
import io
import os
import re
import sys

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Benannte Argumente, deren Wert auf dem Bildschirm landet.
SICHTBAR = ('text', 'title', 'label', 'placeholder', 'platzhalter', 'lead')

# Hausbausteine, die ihren Text an fester Stelle bekommen (nicht als `text=`).
# Dahinter steht, das wievielte Argument der Mensch liest — gezählt ab null.
# Ein Blick in die Signatur genügt, um hier etwas nachzutragen; wer das
# vergisst, bekommt eine grüne Prüfung trotz deutscher Brocken im Englischen.
BAUSTEINE = {
    '_ueberschrift': (2, 3),      # (fenster, rahmen, titel, lead)
    '_knopf':        (2,),        # (fenster, eltern, text, tat, …)
    '_status':       (3, 4),      # (fenster, eltern, zeichen, fett, rest, …)
    '_feld':         (2, 3),      # (fenster, eltern, bezeichnung, hilfe, …)
    'rundknopf':     (1,),        # (eltern, text, tat, …)
    'marke':         (1,),
    '_chip':         (1,),
}

# Methoden, die eine Meldung in die Statuszeile schreiben.
MELDER = ('sagen',)

# `_wahl(fenster, eltern, eintraege, …)` bekommt Paare (Schlüssel, Anzeige).
# Nur die zweite Hälfte steht auf dem Bildschirm.
WAHL = '_wahl'

# Wörter, die zwar wie Text aussehen, aber keiner sind: technische Schlüssel,
# Eigennamen, Dateiendungen.
KEINE_TEXTE = (
    'win', 'darwin', 'linux', 'version', 'datum', 'offen', 'unbekannt',
    'Xharig', 'SC BP Watcher', 'normal', 'bold', 'center', 'left', 'right',
    # Der Sprachumschalter selbst: Jede Sprache steht dort in ihrer eigenen
    # Schreibweise, sonst findet sich niemand wieder. Wer Englisch spricht und
    # versehentlich auf Deutsch gelandet ist, sucht „English" — nicht
    # „Englisch". Diese beiden gehören deshalb NICHT durch t().
    'Deutsch', 'English',
)

# Bausteine, die in jeder Sprache gleich bleiben: der Name des Werkzeugs, das
# Lizenzkürzel, Adressen. Bleibt nach ihrem Abzug nichts übrig, ist die Zeile
# kein zu übersetzender Satz.
UNVERAENDERLICH = re.compile(
    r'(https?://\S+|(?:www\.|github\.com/)\S+|SC BP Watcher|GPL-[\d.]+-only'
    r'|Xharig(?:-1)?|scmdb\.net|KRT Profit Basetool)', re.I)


def _ist_t(knoten):
    """Steht hier ein t('…')-Aufruf?"""
    return (isinstance(knoten, ast.Call)
            and isinstance(knoten.func, ast.Name)
            and knoten.func.id == 't')


def _literale(knoten):
    """Alle festen Zeichenketten eines Ausdrucks — ohne die in t()-Aufrufen."""
    if _ist_t(knoten):
        return []
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
        return [(knoten.lineno, knoten.value)]
    treffer = []
    for kind in ast.iter_child_nodes(knoten):
        # `bericht['grund']` liest ein Wörterbuch aus — der Schlüssel dazwischen
        # steht nie auf dem Bildschirm, nur der Wert. Also nicht mitzählen.
        if isinstance(knoten, ast.Subscript) and kind is knoten.slice:
            continue
        treffer += _literale(kind)
    return treffer


def _ist_satz(text):
    """Liest ein Mensch das, oder ist es Technik?"""
    ohne = re.sub(r'%[sd%.0-9]*', '', text)
    ohne = UNVERAENDERLICH.sub('', ohne).strip(' ·—…\n\t')
    if len(ohne) < 3:
        return False
    # Mindestens drei Buchstaben am Stück — sonst ist es ein Symbol.
    if not re.search(r'[A-Za-zÄÖÜäöüß]{3}', ohne):
        return False
    if ohne in KEINE_TEXTE:
        return False
    return True


def pruefe(pfad):
    """Liefert die Fundstellen einer Datei als (Zeile, Stelle, Text)."""
    quelle = io.open(pfad, encoding='utf-8').read()
    baum = ast.parse(quelle)
    funde = set()

    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call):
            continue

        for arg in knoten.keywords:
            if arg.arg in SICHTBAR:
                for zeile, text in _literale(arg.value):
                    if _ist_satz(text):
                        funde.add((zeile, arg.arg, text))

        name = getattr(knoten.func, 'id', None)
        methode = getattr(knoten.func, 'attr', None)

        if name in BAUSTEINE:
            for stelle in BAUSTEINE[name]:
                if stelle < len(knoten.args):
                    for zeile, text in _literale(knoten.args[stelle]):
                        if _ist_satz(text):
                            funde.add((zeile, name, text))

        if methode in MELDER and knoten.args:
            for zeile, text in _literale(knoten.args[0]):
                if _ist_satz(text):
                    funde.add((zeile, methode + '()', text))

        if name == WAHL and len(knoten.args) > 2:
            eintraege = knoten.args[2]
            if isinstance(eintraege, (ast.List, ast.Tuple)):
                for paar in eintraege.elts:
                    if isinstance(paar, (ast.List, ast.Tuple)) and len(paar.elts) > 1:
                        for zeile, text in _literale(paar.elts[1]):
                            if _ist_satz(text):
                                funde.add((zeile, WAHL, text))

    return sorted(funde)


def main(argumente):
    if argumente:
        dateien = argumente
    else:
        ordner = os.path.join(HIER, 'scbp')
        dateien = [os.path.join(ordner, n) for n in sorted(os.listdir(ordner))
                   if n.endswith('.py')]

    gesamt = 0
    for pfad in dateien:
        funde = pruefe(pfad)
        if not funde:
            continue
        kurz = os.path.relpath(pfad, HIER)
        print('\n%s — %d Stellen:' % (kurz, len(funde)))
        for zeile, wo, text in funde:
            einzeilig = text.replace('\n', ' ')
            if len(einzeilig) > 62:
                einzeilig = einzeilig[:62] + '…'
            print('  %4d  %-10s %s' % (zeile, wo, einzeilig))
        gesamt += len(funde)

    print('')
    if gesamt:
        print('%d feste Texte. Sie gehören nach scbp/sprache.py und dann als' % gesamt)
        print("t('schluessel') an ihre Stelle — sonst zeigt die englische")
        print('Oberfläche deutschen Text.')
        return 1

    print('Alle sichtbaren Texte laufen durch t(). Zweisprachig ist vollständig.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
