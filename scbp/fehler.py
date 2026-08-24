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
Fehler mitschreiben, damit aus „geht nicht" ein Befund wird.

**Das Problem, das dieses Modul löst:** Im Programm stehen über 60 Stellen, die
`except Exception` abfangen und weitermachen. Das ist richtig so — ein Overlay
darf nicht abstürzen, weil eine Netzabfrage klemmt. Nur war der Fehler danach
**spurlos weg**: Wer „bei mir kommt nichts an" meldet, hatte nichts zu schicken,
und hier war nichts nachzustellen.

Ab jetzt landet jeder unerwartete Fehler in `fehler.json` im eigenen Ordner —
mit Zeitpunkt, Stelle, Art und Meldung. Aufgehoben werden die **letzten 50**;
alles ältere fällt hinten heraus, damit die Datei nicht wächst.

Drei Wege hinein:

  1. **Zentrale Haken** (`haken_setzen`) — fangen, was sonst niemand fängt:
     Fehler im Hauptstrang, im Watcher-Thread und in den Rückrufen der
     Oberfläche. Gerade der letzte Fall ist bei `tkinter` der übliche Weg, auf
     dem Fehler verschwinden: Tk schreibt sie auf die Standardausgabe, und die
     sieht in einer `.exe` oder einem AppImage **niemand**.
  2. **`with gefangen('stelle'):`** — für Abschnitte, die weiterlaufen sollen,
     deren Scheitern aber etwas bedeutet.
  3. **`merken(stelle, ausnahme)`** — von Hand in einem vorhandenen `except`.

**Dieses Modul darf niemals selbst etwas kaputt machen.** Jede Funktion fängt
ihre eigenen Fehler ab: Ein Protokoll, das den Programmstart verhindert, wäre
schlimmer als gar keines.

Geschrieben wird **nur lokal**. Verschickt wird nichts — was in einen
Fehlerbericht wandert, entscheidet der Spieler in `scbp/bericht.py`.
"""
import json
import os
import sys
import threading
import traceback
from datetime import datetime

from . import pfade

DATEI = 'fehler.json'
HOECHSTENS = 50          # so viele Einträge bleiben aufgehoben
SPUR_ZEILEN = 6          # so viele Zeilen Rückverfolgung je Eintrag

_schloss = threading.Lock()


def _pfad():
    return pfade.app_datei(DATEI)


def _lesen():
    try:
        with open(_pfad(), encoding='utf-8') as f:
            daten = json.load(f)
        eintraege = daten.get('eintraege')
        return eintraege if isinstance(eintraege, list) else []
    except Exception:
        return []


def merken(stelle, ausnahme=None, hinweis=''):
    """Einen Fehler festhalten. Gibt True zurück, wenn es geklappt hat.

    `stelle` ist der Ort im Programm ('katalog.aktualisieren') — er sagt beim
    Lesen mehr als jede Fehlermeldung. `hinweis` ist Platz für eine Angabe, die
    aus der Ausnahme nicht hervorgeht (welche Datei, welche Adresse).
    """
    try:
        if ausnahme is None:
            ausnahme = sys.exc_info()[1]

        eintrag = {
            'zeit': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stelle': str(stelle),
            'art': type(ausnahme).__name__ if ausnahme else 'Hinweis',
            'meldung': pfade.kuerzen(str(ausnahme) if ausnahme else hinweis),
        }
        if hinweis and ausnahme is not None:
            eintrag['hinweis'] = pfade.kuerzen(str(hinweis))

        if ausnahme is not None:
            spur = traceback.format_exception(type(ausnahme), ausnahme,
                                              ausnahme.__traceback__)
            # Nur der Schwanz der Rückverfolgung — dort steht, wo es knallte.
            # Die Zeilen davor sind bei einem Overlay fast immer dieselben.
            eintrag['spur'] = pfade.kuerzen(''.join(spur[-SPUR_ZEILEN:]).strip())

        with _schloss:
            eintraege = _lesen()
            eintraege.append(eintrag)
            eintraege = eintraege[-HOECHSTENS:]
            with open(_pfad(), 'w', encoding='utf-8') as f:
                json.dump({'eintraege': eintraege}, f, ensure_ascii=False, indent=1)
        return True
    except Exception:
        return False          # ein Protokoll darf nie das Programm mitreißen


def letzte(anzahl=10):
    """Die jüngsten Einträge, neueste zuerst."""
    try:
        return list(reversed(_lesen()))[:max(0, int(anzahl))]
    except Exception:
        return []


def anzahl():
    """Wie viele Einträge liegen vor?"""
    return len(_lesen())


def leeren():
    """Alles vergessen — z. B. nachdem ein Problem behoben wurde."""
    try:
        with _schloss:
            with open(_pfad(), 'w', encoding='utf-8') as f:
                json.dump({'eintraege': []}, f)
        return True
    except Exception:
        return False


class gefangen(object):
    """Kontextmanager: Der Abschnitt darf scheitern, aber nicht schweigen.

        with fehler.gefangen('katalog.aktualisieren'):
            katalog.holen()

    Der Fehler wird festgehalten und **verschluckt** — der Aufrufer läuft
    weiter, so wie es die vorhandenen `except Exception`-Stellen tun. Wer den
    Fehler weiterreichen will, nimmt `gefangen(..., weiterreichen=True)`.
    """

    def __init__(self, stelle, hinweis='', weiterreichen=False):
        self.stelle = stelle
        self.hinweis = hinweis
        self.weiterreichen = weiterreichen

    def __enter__(self):
        return self

    def __exit__(self, art, wert, spur):
        if wert is None:
            return False
        merken(self.stelle, wert, self.hinweis)
        return not self.weiterreichen


def haken_setzen(wurzel=None):
    """Die drei Wege abfangen, auf denen Fehler sonst unbemerkt verschwinden.

    `wurzel` ist das Tk-Hauptfenster, falls schon eines da ist. Ohne Oberfläche
    (Selbsttest, Werkzeuge) werden nur die ersten beiden Haken gesetzt.
    """
    try:
        frueher = sys.excepthook

        def haupt(art, wert, spur):
            merken('unbehandelt', wert)
            frueher(art, wert, spur)

        sys.excepthook = haupt
    except Exception:
        pass

    try:
        # Ohne diesen Haken stirbt der Watcher-Thread still, und das Overlay
        # steht danach da, als liefe alles — es kommt nur nie wieder etwas an.
        def im_thread(angaben):
            merken('thread:%s' % getattr(angaben.thread, 'name', '?'),
                   angaben.exc_value)

        threading.excepthook = im_thread
    except Exception:
        pass

    if wurzel is not None:
        try:
            def in_der_oberflaeche(art, wert, spur):
                merken('oberflaeche', wert)

            wurzel.report_callback_exception = in_der_oberflaeche
        except Exception:
            pass


if __name__ == '__main__':
    print('Protokoll:', _pfad())
    with gefangen('probe'):
        raise ValueError('nur ein Versuch')
    for e in letzte(3):
        print('  %s  %-22s %s: %s' % (e['zeit'], e['stelle'], e['art'], e['meldung']))
