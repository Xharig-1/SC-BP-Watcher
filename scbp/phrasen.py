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
Die Bauplan-Meldung in der Game.log erkennen — in jeder Spielsprache.

Beim Freischalten schreibt Star Citizen eine Zeile wie

    <SHUDEvent_OnNotification> Added notification "Bauplan erhalten: Attrition-5 Repeater: " [136] …

Der Text davor ist **übersetzt**. Bis v1.5.0 stand die deutsche Formulierung fest
im Code — bei englischem Client griff die Sofort-Meldung deshalb gar nicht. Das
ist unter Linux keine Randerscheinung mehr, dort spielen die meisten auf Englisch.

Drei Quellen, in dieser Rangfolge:

  1. **Eigene Ergänzung** — `phrasen.json` im App-Ordner. Wer eine Formulierung
     findet, die hier fehlt, trägt sie ein, ohne auf eine neue Fassung zu warten.
  2. **Die `global.ini` der eigenen Installation** — die genaueste Quelle, denn
     sie ist die Datei, aus der das Spiel den Text selbst nimmt. Dort steht

         crafting_hud_notification_received_blueprint,P=Bauplan erhalten: %s

     Daraus lässt sich das Suchmuster exakt bauen. Sie liegt aber nur entpackt
     vor, wenn jemand sie ausgepackt hat (beim deutschen Client tut das der
     SC Deutsch Launcher) — sonst steckt sie in `Data.p4k`.
  3. **Die mitgelieferte Tabelle** unten — greift immer.

> Stand: **Deutsch und Englisch sind beide gemessen.** Deutsch an 127
> Log-Sicherungen gegengeprüft; Englisch am 24.08.2026 an einem echten
> englischen Client bestätigt — der Client schreibt:
>
>     Added notification "Received Blueprint: Aves Shrike Helmet: "
>
> Damit ist die Rateliste erledigt: `Received Blueprint` steht vorn, die vier
> übrigen Kandidaten bleiben als Rückfall stehen. Andere Sprachen erschließt
> der Watcher sich selbst aus den Logs (siehe `selbst_finden`); wer nachhelfen
> will, holt den Wortlaut mit `tools/extract_global_ini.py --sprache <name>`
> aus der eigenen Installation.
"""
import json
import os
import re

from . import pfade

# Der sprachneutrale Schlüssel — er ist in allen Sprachen derselbe.
INI_SCHLUESSEL = 'crafting_hud_notification_received_blueprint'

# Mitgelieferte Formulierungen. Alle werden gleichzeitig gesucht: Eine Phrase, die
# es in der eigenen Sprache nicht gibt, kann keinen Fehltreffer erzeugen — die
# Zeilenform drumherum ist zu eigen, als dass sie zufällig entstünde.
TABELLE = {
    'de': ['Bauplan erhalten'],                     # gemessen
    # 'Received Blueprint' ist seit 24.08.2026 **gemessen** — an einem echten
    # englischen Client, Zeile:
    #   Added notification "Received Blueprint: Aves Shrike Helmet: "
    # Deshalb steht es vorn. Die vier dahinter waren die übrigen Kandidaten und
    # bleiben stehen: Sie kosten nichts, und sollte CIG die Formulierung einmal
    # ändern, ist die Chance nicht schlecht, dass eine davon dann zutrifft.
    'en': ['Received Blueprint',                    # gemessen
           'Blueprint Received', 'Blueprint Acquired',
           'Blueprint Obtained', 'Blueprint Unlocked'],   # weitere Kandidaten
}

# Nur diese Zeilen zählen. Die anderen Notification-Zeilen sind Ein- und
# Ausblende-Ereignisse — wer sie mitzählt, meldet jeden Bauplan mehrfach.
RAHMEN = r'Added notification "(?:%s):\s*(.+?)\s*:\s*"'

# Dasselbe ohne feste Phrase: Damit lässt sich herausfinden, WIE die Meldung in
# einer unbekannten Sprache lautet — siehe `selbst_finden()`.
RAHMEN_OFFEN = re.compile(r'Added notification "([^":]{3,60}):\s*(.+?)\s*:\s*"')


def _ini_dateien():
    """Alle entpackten `global.ini` der Installation (kann leer sein)."""
    ordner = pfade.lokalisierung_ordner()
    if not ordner:
        return []
    gefunden = []
    try:
        for sprache in sorted(os.listdir(ordner)):
            p = os.path.join(ordner, sprache, 'global.ini')
            if os.path.isfile(p):
                gefunden.append(p)
    except OSError:
        pass
    return gefunden


def _aus_ini(pfad):
    """Die Formulierung aus einer `global.ini` — oder None.

    Gelesen wird zeilenweise und nur bis zum Treffer: Die Datei ist mehrere
    Megabyte groß, sie komplett in den Speicher zu holen wäre unnötig."""
    try:
        with open(pfad, encoding='utf-8-sig', errors='ignore') as f:
            for zeile in f:
                if not zeile.startswith(INI_SCHLUESSEL):
                    continue
                # Format: schluessel,P=Text mit %s   (das ,P ist optional)
                wert = zeile.split('=', 1)[1].strip() if '=' in zeile else ''
                vorne = wert.split('%s', 1)[0].strip()
                # Ein abschließender Doppelpunkt gehört zum Rahmen, nicht zur Phrase
                vorne = vorne.rstrip(':').strip()
                return vorne or None
    except OSError:
        return None
    return None


def _eigene():
    """Selbst ergänzte Formulierungen aus `phrasen.json` im App-Ordner.

    Format:  {"phrasen": ["Blueprint Received"]}"""
    try:
        with open(pfade.app_datei('phrasen.json'), encoding='utf-8') as f:
            werte = json.load(f).get('phrasen') or []
        return [str(p).strip() for p in werte if str(p).strip()]
    except Exception:
        return []


def selbst_finden(katalog_namen, sicherungen, hoechstens=40):
    """Die Bauplan-Phrase aus den eigenen Logs erschließen — in jeder Sprache.

    Der Kniff: Wir kennen alle 714 Bauplan-Namen. Steht in einer Logzeile

        Added notification "IRGENDWAS: Attrition-5 Repeater: "

    und ist „Attrition-5 Repeater" ein bekannter Bauplan, dann ist IRGENDWAS die
    gesuchte Formulierung. Das funktioniert für Französisch und Spanisch genauso
    wie für Englisch — ohne dass jemand die Sprache vorher kennen muss.

    Verlangt werden **mindestens zwei** verschiedene Treffer für dieselbe Phrase.
    Bei nur einem könnte es Zufall sein: Ein Bauplan-Name taucht auch in anderen
    Meldungen auf („Auftrag abgeschlossen: Attrition-5 Repeater geliefert").

    Rückgabe: die gefundene Phrase oder None.
    """
    if not katalog_namen or not sicherungen:
        return None
    bekannt = {str(n).lower().strip() for n in katalog_namen}
    zaehler = {}
    for datei in sicherungen[-hoechstens:]:
        try:
            with open(datei, 'rb') as f:
                text = f.read().decode('utf-8', 'ignore')
        except OSError:
            continue
        for m in RAHMEN_OFFEN.finditer(text):
            phrase, name = m.group(1).strip(), m.group(2).strip()
            # Klassen-Zusatz abschneiden, sonst passt kein Name auf den Katalog
            name = re.sub(r'\s*\((?:Civ|Mil|Ind|Sth|Cmp)/\d+/[A-D]\)\s*$', '',
                          name, flags=re.I).strip()
            if name.lower() in bekannt:
                zaehler.setdefault(phrase, set()).add(name.lower())
    treffer = [(len(namen), p) for p, namen in zaehler.items() if len(namen) >= 2]
    if not treffer:
        return None
    treffer.sort(reverse=True)
    return treffer[0][1]


def merken(phrase):
    """Eine gefundene Formulierung dauerhaft festhalten.

    Sie landet in derselben `phrasen.json`, die auch von Hand gepflegt werden
    kann — es gibt keine zweite, versteckte Wahrheit."""
    if not phrase:
        return False
    vorhandene = _eigene()
    if phrase in vorhandene:
        return False
    try:
        with open(pfade.app_datei('phrasen.json'), 'w', encoding='utf-8') as f:
            json.dump({'phrasen': vorhandene + [phrase],
                       '_hinweis': 'Formulierungen, an denen ein neuer Bauplan '
                                   'im Spiel-Log erkannt wird. Selbst gefundene '
                                   'stehen hier mit drin.'},
                      f, ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


def sammeln():
    """Alle Formulierungen, nach denen gesucht wird — samt Herkunft.

    Rückgabe: (liste_der_phrasen, herkunft) — Herkunft ist 'ini', 'eigen'
    oder 'tabelle', je nachdem, was den genauesten Beitrag geliefert hat."""
    phrasen, herkunft = [], 'tabelle'
    for p in _eigene():
        if p not in phrasen:
            phrasen.append(p)
            herkunft = 'eigen'
    for datei in _ini_dateien():
        p = _aus_ini(datei)
        if p and p not in phrasen:
            phrasen.append(p)
            herkunft = 'ini'
    for sprache in TABELLE.values():
        for p in sprache:
            if p not in phrasen:
                phrasen.append(p)
    return phrasen, herkunft


def muster(phrasen=None):
    """Fertiger regulärer Ausdruck für die Log-Zeilen."""
    if phrasen is None:
        phrasen, _ = sammeln()
    return re.compile(RAHMEN % '|'.join(re.escape(p) for p in phrasen))


def bestaetigt():
    """Steht die Formulierung fest — oder wird geraten?

    True, sobald sie aus der eigenen `global.ini` oder aus `phrasen.json` stammt.
    Bei einem deutschen Client ist sie auch aus der Tabelle heraus verlässlich,
    weil genau diese gemessen wurde."""
    _, herkunft = sammeln()
    return herkunft in ('ini', 'eigen')


if __name__ == '__main__':
    ps, woher = sammeln()
    print('Herkunft:', woher, '· bestätigt:', bestaetigt())
    for p in ps:
        print(' ·', p)
