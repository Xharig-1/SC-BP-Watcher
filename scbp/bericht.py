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
Ein Fehlerbericht, mit dem sich arbeiten lässt.

„Bei mir geht es nicht" ist keine Fehlermeldung. Dieses Modul baut daraus einen
Textblock, den der Spieler in ein Issue einfügt — und der die Fragen schon
beantwortet, die man sonst einzeln stellen müsste: Welches System, welche
Verpackung, welche Tk-Fassung, welcher Bildschirmaufbau, ist das Spiel
gefunden, welche Sprache wurde erkannt, wie weit ist das Protokoll gelesen,
was steht im Katalog — und was ist zuletzt schiefgegangen.

Drei Regeln, die nicht verhandelbar sind:

  1. **Keine Namen.** Jeder Wert läuft durch `pfade.kuerzen()`; aus
     `/home/spieler/…` wird `<heim>/…`. Ein Bericht landet in einem
     **öffentlichen** Issue.
  2. **Nichts wird verschickt.** Das Modul gibt Text zurück, mehr nicht. Ob er
     jemanden erreicht, entscheidet allein der Spieler.
  3. **Der Bericht darf nie scheitern.** Jede Angabe wird einzeln geholt; was
     nicht zu ermitteln ist, steht als `—` da. Ein Bericht, der abbricht, weil
     eine Kleinigkeit fehlt, ist genau dann nutzlos, wenn man ihn braucht.
"""
import json
import os
import platform
import sys
from datetime import datetime

from . import fehler, pfade


def _sicher(f, standard='—'):
    """Eine Angabe holen und dabei nichts riskieren."""
    try:
        wert = f()
        if wert is None or wert == '':
            return standard
        return wert
    except Exception:
        return standard


def _json_groesse(pfad_, schluessel):
    """Wie viele Einträge stehen in einer unserer JSON-Dateien?"""
    with open(pfad_, encoding='utf-8') as f:
        daten = json.load(f)
    wert = daten.get(schluessel, daten)
    return len(wert) if hasattr(wert, '__len__') else '—'


def _system():
    name = platform.system()
    if name == 'Linux':
        kennung = _sicher(lambda: platform.freedesktop_os_release().get('PRETTY_NAME'), '')
        sitzung = os.environ.get('XDG_SESSION_TYPE', '')
        return ' · '.join(x for x in ('Linux', kennung, platform.release(), sitzung) if x)
    if name == 'Windows':
        return 'Windows %s · Build %s' % (platform.release(), platform.version())
    return '%s %s' % (name, platform.release())


def _tk_fassung():
    import tkinter
    return str(tkinter.TkVersion)


def _bildschirme(wurzel):
    """Größe und Skalierung — hier lagen schon zwei Fehler begraben."""
    if wurzel is None:
        return '—'
    breite = wurzel.winfo_screenwidth()
    hoehe = wurzel.winfo_screenheight()
    # 72 Punkte je Zoll ist Tks Bezug; daraus wird die Skalierung lesbar.
    skalierung = round(float(wurzel.tk.call('tk', 'scaling')) * 72 / 96 * 100)
    return '%d×%d · Skalierung %d %%' % (breite, hoehe, skalierung)


def bauen(version='', wurzel=None, fehleranzahl=8):
    """Den Bericht als Text zusammensetzen."""
    zeilen = []

    def zeile(bez, wert):
        zeilen.append('%-18s%s' % (bez, pfade.kuerzen(wert)))

    zeilen.append('SC BP Watcher %s · Bericht vom %s'
                  % (version or '—', datetime.now().strftime('%d.%m.%Y, %H:%M')))
    zeilen.append('')

    uebersicht = _sicher(pfade.uebersicht, {})
    if not isinstance(uebersicht, dict):
        uebersicht = {}

    zeile('System', _sicher(_system))
    zeile('Verpackung', _sicher(lambda: __import__(
        'scbp.aktualisierung', fromlist=['verpackung']).verpackung()))
    zeile('Python / Tk', '%s / %s' % (platform.python_version(), _sicher(_tk_fassung)))
    zeile('Bildschirm', _sicher(lambda: _bildschirme(wurzel)))
    zeilen.append('')

    zeile('Spiel', _sicher(lambda: uebersicht.get('spiel_ordner') or 'nicht gefunden'))
    zeile('Game.log', _sicher(lambda: uebersicht.get('game_log') or 'nicht gefunden'))
    zeile('Sicherungen', _sicher(lambda: '%s Protokolle' % uebersicht.get('sicherungen')))
    zeile('Launcher', _sicher(lambda: uebersicht.get('launcher') or 'nicht vorhanden'))
    zeile('Spielsprache', _sicher(lambda: ', '.join(
        __import__('scbp.phrasen', fromlist=['sammeln']).sammeln()) or '—'))
    zeilen.append('')

    zeile('Bestand', _sicher(lambda: '%s Baupläne' % _json_groesse(
        __import__('scbp.bestand', fromlist=['pfad']).pfad(), 'blueprints')))
    zeile('Merkliste', _sicher(lambda: '%s Einträge' % _json_groesse(
        __import__('scbp.merkliste', fromlist=['pfad']).pfad(), 'eintraege')))
    zeile('Katalogstand', _sicher(lambda: __import__(
        'scbp.katalog', fromlist=['aktuelle_version']).aktuelle_version()))
    zeilen.append('')

    zeile('Eigener Ordner', _sicher(lambda: uebersicht.get('app_ordner')))
    zeile('Einstellungen', _sicher(lambda: ', '.join(
        '%s=%s' % (k, v) for k, v in sorted(
            (uebersicht.get('selbst_gesetzt') or {}).items())) or 'alle auf Standard'))

    letzte = _sicher(lambda: fehler.letzte(fehleranzahl), [])
    gesamt = _sicher(fehler.anzahl, 0)
    zeilen.append('')
    if letzte:
        zeilen.append('Letzte Fehler (%s von %s aufgehoben)' % (len(letzte), gesamt))
        for e in letzte:
            zeilen.append('  %s  %-24s %s: %s'
                          % (e.get('zeit', '—'), e.get('stelle', '—'),
                             e.get('art', '—'), e.get('meldung', '—')))
    else:
        zeilen.append('Letzte Fehler        keine aufgezeichnet')

    zeilen.append('')
    zeilen.append('Pfade gekürzt (<heim>, <benutzer>) · keine Namen, keine Zugangsdaten')
    return '\n'.join(zeilen)


def in_die_ablage(text, wurzel=None):
    """Den Bericht in die Zwischenablage legen. True, wenn es geklappt hat."""
    try:
        if wurzel is None:
            return False
        wurzel.clipboard_clear()
        wurzel.clipboard_append(text)
        wurzel.update()          # ohne das ist die Ablage nach dem Beenden leer
        return True
    except Exception:
        return False


# GitHub schneidet sehr lange Adressen ab. Der Bericht ist normalerweise gut
# 1 KB groß; die Grenze greift erst, wenn jemand mit 50 Fehlern im Gepäck meldet.
URL_GRENZE = 6000
ISSUE_ADRESSE = 'https://github.com/Xharig-1/SC-BP-Watcher/issues/new'


def _vorlage_zur_sprache():
    """Deutsche Oberfläche → deutsches Formular, sonst das englische."""
    try:
        from . import sprache
        return 'fehler.yml' if sprache.aktuelle() == 'de' else 'bug.yml'
    except Exception:
        return 'bug.yml'


def issue_adresse(text, titel='', vorlage=None):
    """Eine Adresse, die bei GitHub ein **vorausgefülltes** Formular öffnet.

    Warum dieser Weg und kein Absenden aus dem Programm heraus: Ein Issue
    anzulegen verlangt einen Zugangsschlüssel. Einen eigenen mitzuliefern hieße,
    ihn zu verschenken — in einer `.exe` ist nichts geheim, und jeder könnte
    damit im Namen des Projekts schreiben. Den Spieler nach seinem zu fragen ist
    ihm nicht zuzumuten.

    Über die Adresse ist beides gelöst: Der Browser öffnet das Formular fertig
    ausgefüllt, der Spieler liest es und drückt selbst auf Abschicken. Er sieht
    also genau, was er weitergibt — und angemeldet ist er dort ohnehin.
    """
    from urllib.parse import urlencode

    koerper = text or ''
    if len(koerper) > URL_GRENZE:
        koerper = (koerper[:URL_GRENZE]
                   + '\n\n… gekürzt. Der vollständige Bericht liegt unter '
                     '"Als Datei speichern" und kann angehängt werden.')

    werte = {'template': vorlage or _vorlage_zur_sprache(), 'bericht': koerper}
    if titel:
        werte['title'] = titel
    return ISSUE_ADRESSE + '?' + urlencode(werte)


def issue_oeffnen(text, titel=''):
    """Das vorausgefüllte Formular im Browser öffnen. True, wenn es startete."""
    try:
        import webbrowser
        return bool(webbrowser.open(issue_adresse(text, titel)))
    except Exception:
        return False


def speichern(text, pfad_=None):
    """Den Bericht als Datei ablegen; gibt den Pfad zurück oder None."""
    try:
        pfad_ = pfad_ or pfade.app_datei('bericht.txt')
        with open(pfad_, 'w', encoding='utf-8') as f:
            f.write(text)
        return pfad_
    except Exception:
        return None


if __name__ == '__main__':
    sys.stdout.write(bauen(version='2.2.0-dev') + '\n')
