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
Das Handelslager — was zum Verkauf im Laderaum liegt.

Getrennt vom Werkstatt-Lager (`rohstoffe.py`), und zwar mit Absicht: Das dort
ist Baumaterial, das man **behält**. Was hier steht, will man **loswerden**.
Wer 500 SCU Gold für einen Handelsflug bunkert, will sie nicht in der
Herstellungs-Rechnung als Vorrat auftauchen sehen.

## Was hier anders ist als im Werkstatt-Lager

| | Werkstatt (`rohstoffe.py`) | Handel (hier) |
|---|---|---|
| Waren | die 26 aus Rezepten | alle rund 150 verkäuflichen |
| Güte | wichtig (Q 500 ist der Nullpunkt) | **gibt es nicht** |
| Menge | cSCU-genau, mit Raffinerie-Zeilen | ganze SCU |
| stattdessen | — | Kennzeichen **als gestohlen markiert** |

⚠ **Keine Qualität.** Zwei Gründe: Der Ankaufpreis am Terminal hängt nicht
daran (im ganzen UEX-Abzug steht `quality` auf 0), und erbeutete Ware hat
ohnehin immer Q 0. Ein Feld, das nie etwas ändert, ist nur ein Feld, das man
falsch ausfüllen kann.

⚠⚠ **Geschlossene Listen, kein Freitext** — dieselbe Regel wie beim Lagerort in
`orte.py`, aus demselben Grund: Jemand tippt etwas Beleidigendes hinein, macht
ein Bildschirmfoto und verbreitet es. Am Ende fragt niemand, wer getippt hat;
es steht in diesem Werkzeug. Die Warennamen kommen deshalb aus `verkauf.py`,
die Orte aus `orte.py`.

## Als gestohlen markiert

Erbeutete Ladung nimmt nicht jedes Terminal an. Ist der Haken gesetzt, blendet
der Verkaufs-Reiter auf die Stellen ein, die keine Fragen stellen (`is_nqa` bei
UEX) — 15 Terminals, davon 7 mit Ankaufgeboten.

⚠ **Hinweis, keine Behauptung** — dieselbe Haltung wie im Werkstatt-Lager: Wer
zwei Zugänge zu buchen vergisst, hat ein lückenhaftes Lager. Das Werkzeug sagt
deshalb nie „das hast du nicht", sondern rechnet nur mit dem, was eingetragen
ist.
"""
import json
import os

from . import fehler, pfade

DATEI = 'handelslager.json'
FORMAT = 1

# ⭐ Zahleingabe **und Rechner** sind dieselben wie im Werkstatt-Lager: Komma
# und Punkt gelten gleich, das lange Minus vom Ziffernblock wird angenommen,
# und `100+5` ergibt 105. Wiederverwendet statt nachgebaut — zwei Fassungen
# derselben Regel gehen irgendwann auseinander, und das Bedienkonzept darf
# sich zwischen zwei Lagern nicht unterscheiden.
from .rohstoffe import rechnen, zahl_lesen                   # noqa: E402


def _menge_pruefen(menge, vorher=0.0):
    """Was im Mengenfeld steht, als geprüfte Zahl — oder `None`.

    ⚠ **Kein negatives Ergebnis und keine Null.** Der Rechner lässt Minus
    ausdrücklich zu (`100-40` ergibt 60, und im Werkstatt-Lager wird damit
    abgebucht) — aber ein Laderaum mit „−40 SCU" ergibt keinen Sinn. Geprüft
    wird deshalb das **Ergebnis**, nicht die Eingabe.
    """
    zahl = rechnen(menge, vorher) if isinstance(menge, str) else menge
    if zahl is None or zahl <= 0:
        return None
    return float(zahl)


def laden():
    """Alle Posten — oder eine leere Liste."""
    try:
        with open(pfade.app_datei(DATEI), encoding='utf-8') as f:
            daten = json.load(f)
        if daten.get('format') == FORMAT:
            return daten.get('posten') or []
    except Exception:
        pass
    return []


def sichern(posten):
    """Die Posten schreiben. Meldet einen Fehlschlag, statt ihn zu schlucken."""
    ziel = pfade.app_datei(DATEI)
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel + '.tmp', 'w', encoding='utf-8') as f:
            json.dump({'format': FORMAT, 'posten': posten}, f,
                      ensure_ascii=False, indent=1)
        os.replace(ziel + '.tmp', ziel)
        return True
    except Exception as ausnahme:
        fehler.merken('handelslager.sichern', ausnahme)
        return False


def gleicher_posten(a_ware, a_ort, a_gestohlen, b):
    """Sind das zwei Eintragungen für **denselben** Stapel?

    Gleich heisst: gleiche Ware, gleicher Lagerort, gleiches Kennzeichen. Nur
    dann darf zusammengezählt werden.

    ⚠ **Das Kennzeichen gehört dazu.** Saubere und als gestohlen markierte Ware
    derselben Sorte sind zwei Stapel — sie lassen sich nicht an denselben
    Stellen verkaufen. Wer sie zusammenzählt, schickt jemanden mit heißer Ware
    an ein Terminal, das Fragen stellt.
    """
    return (b.get('ware') == a_ware
            and (b.get('ort') or '') == (a_ort or '')
            and bool(b.get('gestohlen')) == bool(a_gestohlen))


def eintragen(ware, menge, ort='', gestohlen=False):
    """Einen Zugang buchen. Gleiche Stapel werden zusammengezählt.

    Gibt `(Erfolg, Grund)` zurück; `Grund` ist eine Kennung für die Oberfläche
    (`'ware'`, `'menge'`, `'schreiben'`) oder `''`.
    """
    ware = (ware or '').strip()
    if not ware:
        return False, 'ware'
    zahl = _menge_pruefen(menge)
    if zahl is None:
        return False, 'menge'
    posten = laden()
    for p in posten:
        if gleicher_posten(ware, ort, gestohlen, p):
            p['menge'] = float(p.get('menge') or 0) + float(zahl)
            return (True, '') if sichern(posten) else (False, 'schreiben')
    posten.append({'ware': ware, 'menge': float(zahl),
                   'ort': ort or '', 'gestohlen': bool(gestohlen)})
    return (True, '') if sichern(posten) else (False, 'schreiben')


def aendern(nummer, ware, menge, ort='', gestohlen=False):
    """Einen Posten überschreiben. `nummer` ist die Stelle in `laden()`."""
    posten = laden()
    if not 0 <= nummer < len(posten):
        return False, 'weg'
    ware = (ware or '').strip()
    if not ware:
        return False, 'ware'
    # Beim Ändern zählt die bisherige Menge als Ausgangswert — wer `+5`
    # tippt, bucht dazu, statt die Menge auf 5 zu setzen.
    zahl = _menge_pruefen(menge, float(posten[nummer].get('menge') or 0))
    if zahl is None:
        return False, 'menge'
    posten[nummer] = {'ware': ware, 'menge': float(zahl),
                      'ort': ort or '', 'gestohlen': bool(gestohlen)}
    return (True, '') if sichern(posten) else (False, 'schreiben')


def entfernen(nummer):
    """Einen Posten löschen."""
    posten = laden()
    if not 0 <= nummer < len(posten):
        return False
    posten.pop(nummer)
    return sichern(posten)


def leeren():
    """Alles löschen — nach dem Verkauf der ganzen Ladung."""
    return sichern([])


def mengen(nur_gestohlen=None):
    """Wie viel von welcher Ware im Lager liegt: `{Ware: SCU}`.

    `nur_gestohlen=True` zählt nur die markierte Ware, `False` nur die saubere,
    `None` alles.
    """
    zusammen = {}
    for p in laden():
        if nur_gestohlen is not None and bool(p.get('gestohlen')) != nur_gestohlen:
            continue
        ware = p.get('ware')
        if not ware:
            continue
        zusammen[ware] = zusammen.get(ware, 0.0) + float(p.get('menge') or 0)
    return zusammen


def waren_im_lager(nur_gestohlen=None):
    """Die Warennamen im Lager, alphabetisch — die Vorauswahl für den Verkauf."""
    return sorted(mengen(nur_gestohlen))


def hat_gestohlenes():
    """Liegt markierte Ware im Lager? Schaltet den Filter im Reiter vor."""
    return any(p.get('gestohlen') for p in laden())
