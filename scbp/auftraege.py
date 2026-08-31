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
Angenommene Aufträge — „bringt mir der etwas, das mir fehlt?"

Der Watcher beantwortet seine eigene Frage damit **früher**: Nicht erst wenn der
Bauplan im Spiel auftaucht, sondern schon beim Annehmen des Auftrags.

    Auftrag angenommen: Retake Platforms From Nine Tails
      → 3 Baupläne · dir fehlt: H4-PBF Ammo Carrier

Es ist bewusst **keine Auftragsverwaltung**: keine Liste, kein Reiter, kein
zweites Fenster. Eine Zeile im Overlay, wie ein Bauplanfund auch.

## Der Weg durch die Daten

| Schritt | Woher |
|---|---|
| 1. Auftrag angenommen | `Game.log`, Zeile `Added notification "<Phrase>: <Titel>: "` |
| 2. Welche Phrase | `mobiGlas_ui_MissionEvent_Activated` aus der `global.ini` |
| 3. Titel → Missionsschlüssel | Rückwärtssuche in der `global.ini` |
| 4. Schlüssel → Baupläne | `missionen[<schlüssel>]['bp']` im Katalog |
| 5. Was davon fehlt | der eigene Bestand |

## ⚠ Die Fallen, alle an echten Daten gemessen (29.08.2026)

1. **Auf den SCHLÜSSEL gehen, nie auf die Formulierung.** Auf Deutsch heißen
   `mobiGlas_ui_MissionEvent_Available` **und** `mobiGlas_ui_ObjectiveEvent_Activated`
   beide „Neuer Auftrag" — das sind Zwischenziele. Wer darauf hört, meldet bei
   jedem Etappenziel. Nur `MissionEvent_Activated` ist die Annahme.
2. **Der Titel trägt unsere eigenen Marken.** Im Log steht
   `Retake Platforms From Nine Tails <EM4>[BP!]</EM4>`, in der injizierten
   `global.ini` sogar `…[SCBPW] <EM4>[BP 4/8]</EM4>[/SCBPW]`. Vor jedem
   Vergleich müssen sie weg — auf **beiden** Seiten.
3. **58 von 353 Titeln enthalten Platzhalter** (`~mission(TargetName)`), die das
   Spiel erst zur Laufzeit einsetzt. Ein wörtlicher Vergleich scheitert dort.
   Deshalb wird aus dem Titel ein Muster gebaut: `High-Risk Bounty:
   ~mission(TargetName)` wird zu einem Muster mit `.+` an der Platzhalter-Stelle,
   der Rest woertlich. Damit sind 337 der
   353 erreichbar statt 279.
4. **Ist der Auftrag unbekannt, wird geschwiegen.** Für 16 der 353 findet sich
   kein Titel, und nicht jeder angenommene Auftrag steht überhaupt im Katalog.
   Lieber nichts melden als raten — eine falsche Bauplan-Zusage ist schlimmer
   als keine.

Die Auftrags-Herkunft stammt aus dem Katalog von scmdb.net und wird **nicht
mitgeliefert** (CC BY-NC-ND). Fehlt sie, tut dieses Modul nichts und der Watcher
läuft unverändert weiter.
"""
import os
import re

from . import fehler, katalog, pfade

# Der sprachneutrale Schlüssel für „Auftrag angenommen" — in jeder Sprache derselbe.
# Dazu das Teilen in der Gruppe: Wer einen Auftrag geteilt **bekommt**, soll
# genauso erfahren, dass darin Baupläne stecken.
#
# Gemessen an Logs, in denen **beide** Rollen vorkamen — geteilt und
# geteilt bekommen: Auf jedes „geteilt" folgt eine Annahme. Streng genommen
# genuegte also die Annahme allein. Das Teilen bleibt trotzdem drin, weil es
# nichts kostet: Steht der Titel schon in der Liste, bleibt es bei einem
# Eintrag. Faellt die Annahme in einer kuenftigen Spielfassung einmal weg,
# steht der Auftrag trotzdem da.
INI_SCHLUESSEL = ('mobiGlas_ui_MissionEvent_Activated',
                  'mobiGlas_ui_Mission_Shared')

# Und die drei Arten, wie ein Auftrag endet. ⚠ Ohne sie hielte der Watcher
# jeden Auftrag für ewig offen: Wer zehn hintereinander macht, haette zehn
# Zeilen stehen, von denen neun erledigt sind.
#
# `Deactivate` heisst im Spiel „zurückgezogen" — das ist der Abbruch von Hand.
INI_ENDE = (
    'mobiGlas_ui_MissionEvent_Complete',      # abgeschlossen
    'mobiGlas_ui_MissionEvent_Deactivate',    # zurückgezogen (abgebrochen)
    'mobiGlas_ui_MissionEvent_Fail',          # fehlgeschlagen
)

# Rückfall, falls die `global.ini` nicht vorliegt. Beide an echten Logs gemessen
# (aus echten Log-Sicherungen, 29.08.2026: 701 Annahmen, 303 Abschluesse, 112
# Ruecknahmen, 57 Fehlschlaege).
TABELLE = {
    # ⚠ Schweizerdeutsch ist eine **eigene Fassung** derselben Übersetzung
    # (`live-CH`) und schreibt „Uftrag" statt „Auftrag". Am 30.08.2026 direkt
    # in der Quelle nachgesehen (`rjcncpt/StarCitizen-Deutsch-INI`, Ordner
    # `live-CH`) — nicht geraten:
    #
    #     mobiGlas_ui_MissionEvent_Activated=Uftrag angenommen: %s
    #     mobiGlas_ui_MissionEvent_Complete=Uftrag abgschlosse: %s
    #
    # Ohne diese Einträge erkennt der Watcher dort **keinen einzigen Auftrag** —
    # still, ohne Fehlermeldung. Greift nur als Rückfall: Liegt eine lesbare
    # `global.ini` vor, gewinnt die immer.
    'de': ['Auftrag angenommen', 'Auftrag geteilt',
           'Uftrag angenommen', 'Uftrag geteilt'],          # live-CH
    'en': ['Contract Accepted', 'Contract Shared'],
}

# ⚠ „Auftrag geteilt" gehoert NICHT hierher — das ist ein Anfang, kein Ende.
TABELLE_ENDE = {
    # ⚠ Auch hier die Schweizer Fassung — und die weicht bei JEDEM der drei
    # Enden ab: „abgschlosse", „fehlgschlage". Nur „zurückgezogen" ist gleich.
    'de': ['Auftrag abgeschlossen', 'Auftrag zurückgezogen',
           'Auftrag fehlgeschlagen',
           'Uftrag abgschlosse', 'Uftrag zurückgezogen',
           'Uftrag fehlgschlage'],                          # live-CH
    'en': ['Contract Complete', 'Contract Withdrawn', 'Contract Failed'],
}

# Dieselbe Zeilenform wie bei den Bauplänen — sie ist zu eigen, als dass sie
# zufällig entstünde.
RAHMEN = r'Added notification "(?:%s):\s*(.+?)\s*:\s*"'

# Unsere eigenen Marken im Titel. `injektion.py` schreibt sie, hier müssen sie
# vor jedem Vergleich wieder weg.
_MARKEN = re.compile(
    r'\[SCBPW\].*?\[/SCBPW\]'                       # der ganze eingefügte Block
    r'|<EM4>\[(?:BP|Bauplan)(?:\s+\d+/\d+)?!?\]</EM4>'   # nur die Blase
)
_PLATZHALTER = re.compile(r'~mission\([^)]*\)')

_index = None            # {sauberer Titel: schluessel}
_muster_index = None     # [(kompiliertes Muster, schluessel)] für Platzhalter-Titel
_missionen = None        # Zwischenspeicher: der Katalog ist rund 1 MB gross


def missionen():
    """Die Missionen aus dem Katalog — einmal lesen, dann gemerkt.

    `katalog.laden()` liest jedes Mal die ganze Datei. Bei einem Auftrag alle
    paar Minuten faellt das nicht auf, aber es waere unnoetige Arbeit.
    """
    global _missionen
    if _missionen is None:
        try:
            _missionen = katalog.laden().get('missionen') or {}
        except Exception as ausnahme:
            fehler.merken('auftraege.katalog', ausnahme)
            _missionen = {}
    return _missionen


def vergessen():
    """Zwischenspeicher leeren — nach einem Katalog-Update aufzurufen."""
    global _missionen, _index, _muster_index
    _missionen, _index, _muster_index = None, None, None


# Die `global.ini` schreibt die Meldung mit Platzhalter: `Auftrag angenommen: %s`.
# Fuer die Suche zaehlt nur der Wortlaut davor — mit dem Platzhalter passt die
# Zeile nie, weil im Log der echte Titel steht.
_PLATZHALTER_ENDE = re.compile(r'\s*:?\s*%[sd]\s*$')


def sauber(titel):
    """Titel ohne unsere Marken und ohne doppelte Leerzeichen."""
    return ' '.join(_MARKEN.sub(' ', str(titel)).split())


def _phrase_kuerzen(wert):
    """Aus `Auftrag angenommen: %s` wird `Auftrag angenommen`."""
    return _PLATZHALTER_ENDE.sub('', sauber(wert)).strip()


def _phrasen_zu(schluessel, rueckfall):
    """Den Wortlaut zu einem oder mehreren `global.ini`-Schlüsseln holen.

    Erst aus der `global.ini` des Spiels — die ist immer richtig, auch in
    Sprachen, die wir nie gesehen haben. Sonst die mitgelieferte Tabelle.
    """
    schluessel = (schluessel,) if isinstance(schluessel, str) else tuple(schluessel)
    anfaenge = tuple(s + '=' for s in schluessel)
    gefunden = []
    for pfad in _ini_dateien():
        try:
            with open(pfad, encoding='utf-8', errors='ignore') as f:
                for zeile in f:
                    # ⚠ Kein `break` nach dem ersten Treffer mehr — es sind
                    # jetzt mehrere Schlüssel je Datei zu holen.
                    if zeile.startswith(anfaenge):
                        wert = _phrase_kuerzen(zeile.split('=', 1)[1])
                        if wert and wert not in gefunden:
                            gefunden.append(wert)
        except OSError:
            continue
    for liste in rueckfall.values():
        for p in liste:
            if p not in gefunden:
                gefunden.append(p)
    return gefunden


def phrasen():
    """Womit ein Auftrag bei mir anfaengt — angenommen oder geteilt bekommen."""
    return _phrasen_zu(INI_SCHLUESSEL, TABELLE)


def ende_phrasen():
    """Wie die drei Enden heißen — abgeschlossen, zurückgezogen, gescheitert.

    ⚠ Der Watcher braucht sie nicht, um etwas zu melden, sondern um etwas
    **wegzunehmen**. Ein erledigter Auftrag, der stehen bleibt, ist schlimmer
    als gar keine Anzeige: Nach einem Abend mit zehn Auftraegen stuende dort
    eine Liste, von der nichts mehr stimmt.
    """
    return _phrasen_zu(INI_ENDE, TABELLE_ENDE)


def _ini_dateien():
    """Alle vorhandenen `global.ini` der Installation."""
    try:
        basis = os.path.join(pfade.spiel_ordner() or '', 'data', 'Localization')
    except Exception:
        return []
    if not os.path.isdir(basis):
        return []
    gefunden = []
    try:
        for name in sorted(os.listdir(basis)):
            p = os.path.join(basis, name, 'global.ini')
            if os.path.isfile(p):
                gefunden.append(p)
    except OSError:
        pass
    return gefunden


def muster():
    """Das fertige Suchmuster für die Log-Zeile — angenommene Auftraege."""
    teile = '|'.join(re.escape(p) for p in phrasen())
    return re.compile(RAHMEN % teile)


def ende_muster():
    """Dasselbe für die drei Enden — abgeschlossen, zurückgezogen, gescheitert.

    Bewusst ein zweites Muster statt eines gemeinsamen mit Gruppen: Die beiden
    Listen kommen aus verschiedenen Schlüsseln, und ein Fehlgriff hiesse, dass
    ein abgeschlossener Auftrag als neu angenommen gilt.
    """
    teile = '|'.join(re.escape(p) for p in ende_phrasen())
    return re.compile(RAHMEN % teile)


def offene_aus_text(text, muster_an=None, muster_aus=None):
    """Welche Auftraege laut diesem Log-Text noch offen sind.

    Geht den Text **in seiner Reihenfolge** durch und führt Buch: Eine Annahme
    legt den Titel ab, ein Ende nimmt ihn wieder weg. Was am Schluss übrig
    bleibt, lief zu diesem Zeitpunkt noch.

    ⚠ Verglichen wird über `sauber()`, also ohne unsere eingefügten Marken —
    im Log steht der Titel mit `[SCBPW]…[/SCBPW]` darin, und beim Abschluss
    kann die Bauplan-Blase eine andere Zahl tragen als bei der Annahme.

    Gibt die Titel in der Reihenfolge der Annahme zurück.
    """
    muster_an = muster_an or muster()
    muster_aus = muster_aus or ende_muster()

    ereignisse = []
    for m in muster_an.finditer(text):
        ereignisse.append((m.start(), True, m.group(1)))
    for m in muster_aus.finditer(text):
        ereignisse.append((m.start(), False, m.group(1)))
    ereignisse.sort(key=lambda e: e[0])

    offen = {}
    for _stelle, ist_annahme, titel in ereignisse:
        rein = sauber(titel)
        if not rein:
            continue
        if ist_annahme:
            offen.setdefault(rein, titel)
        elif rein in offen:
            del offen[rein]
        else:
            # ⚠⚠ **Ein Ende, das zu keinem offenen Auftrag passt, wirft alles
            # um.** Das ist kein Notnagel, sondern die einzige ehrliche Antwort
            # — und der Grund steht im Spiel selbst:
            #
            # **Beim Zurückziehen meldet Star Citizen nicht den Auftrag,
            # sondern das gerade aktive Ziel.** Angenommen wird „Secure Our
            # Airspace", zurückgezogen wird „der Außenbereich eines
            # Asteroidenstützpunkts aufsuchen und Target finden". Über 152
            # Protokolle gemessen (31.08.2026): von 112 Rücknahmen tragen
            # **2** einen Titel, der auch als Annahme vorkommt.
            #
            # Damit lief der Auftrag hier ewig weiter: Der Watcher fand nichts
            # zum Streichen, und weil er beim Start die laufende `Game.log`
            # durchgeht, stand der abgebrochene Auftrag nach **jedem** Start
            # wieder da. Gemeldet von Morkhan (KRT) am 31.08.2026.
            #
            # ⚠ **Warum nicht raten, welcher gemeint war?** Weil es nicht
            # aufgeht. Gemessen an denselben Protokollen war bei einem nicht
            # zuzuordnenden Ende nur in 36 von 172 Fällen genau **ein** Auftrag
            # offen; meist waren es drei bis acht. „Den zuletzt angenommenen
            # streichen" läge also oft daneben — dann verschwände ein Auftrag,
            # den man noch hat, und der abgebrochene bliebe stehen. Auch die
            # Missions-Kennung hilft nicht: Beim Ende steht sie im Log
            # (`EndMission MissionId[…]`), bei der Annahme in 26 von 28 Fällen
            # nicht.
            #
            # Also: Ab hier stimmt die Buchführung nicht mehr, und was davor
            # gezählt wurde, ist wertlos. Alles Spätere zählt wieder normal —
            # der nächste angenommene Auftrag steht sofort wieder da. Das
            # kostet in seltenen Fällen eine Zeile, die noch gestimmt hätte;
            # dafür steht nie etwas da, das erledigt ist. **Lieber nichts
            # zeigen als etwas Falsches behaupten** — dieselbe Linie wie
            # überall sonst im Werkzeug.
            #
            # Wirkung, an allen 152 Protokollen nachgerechnet: von 174
            # scheinbar offenen Auftraegen bleiben 105 — 40 % weniger, ohne
            # eine einzige geratene Zuordnung.
            offen.clear()
    return list(offen.values())


def _index_bauen():
    """Titel → Missionsschlüssel, aus der `global.ini` und dem Katalog.

    Es werden nur die Schlüssel aufgenommen, die der Katalog überhaupt kennt —
    die `global.ini` hat über 9.000 Einträge, davon sind 353 für uns relevant.
    """
    global _index, _muster_index
    _index, _muster_index = {}, []
    bekannt = set(missionen())
    if not bekannt:
        return
    for pfad in _ini_dateien():
        try:
            with open(pfad, encoding='utf-8', errors='ignore') as f:
                for zeile in f:
                    trenner = zeile.find('=')
                    if trenner < 1:
                        continue
                    schluessel = zeile[:trenner]
                    if schluessel not in bekannt:
                        continue
                    titel = sauber(zeile[trenner + 1:])
                    if not titel:
                        continue
                    if '~mission(' in titel:
                        # Platzhalter -> Muster. Der Rest wird woertlich
                        # genommen, damit „High-Risk Bounty: X" nicht auf
                        # „Low-Risk Bounty: X" passt.
                        roh = '^' + '.+'.join(
                            re.escape(t) for t in _PLATZHALTER.split(titel)) + '$'
                        try:
                            _muster_index.append((re.compile(roh), schluessel))
                        except re.error:
                            pass
                    else:
                        _index.setdefault(titel.lower(), schluessel)
        except OSError:
            continue


def schluessel_zu(titel):
    """Der Missionsschlüssel zu einem angezeigten Titel, oder None."""
    if _index is None:
        _index_bauen()
    rein = sauber(titel)
    treffer = _index.get(rein.lower())
    if treffer:
        return treffer
    for mst, schluessel in _muster_index:
        if mst.match(rein):
            return schluessel
    return None


def pruefen(titel, hat_bereits):
    """Was bringt dieser Auftrag — und was davon fehlt noch?

    `hat_bereits` ist eine Funktion `name -> bool`. Rückgabe ist `None`, wenn
    der Auftrag unbekannt ist oder keine Baupläne bringt; sonst
    `(gesamtzahl, [fehlende Namen])`.
    """
    schluessel = schluessel_zu(titel)
    if not schluessel:
        return None
    eintrag = missionen().get(schluessel) or {}
    namen = [n for n in (eintrag.get('bp') or []) if n]
    if not namen:
        return None
    fehlend = [n for n in namen if not hat_bereits(n)]
    return len(namen), fehlend
