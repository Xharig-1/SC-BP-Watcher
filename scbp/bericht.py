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
Verpackung, welche Tk-Version, welcher Bildschirmaufbau, ist das Spiel
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
from .sprache import t


def _sicher(f, standard='—'):
    """Eine Angabe holen und dabei nichts riskieren.

    ⚠ Ein leerer Wert ist normal (kein Spiel installiert, keine Merkliste) —
    eine **Ausnahme** ist es nicht. Die wurde hier bisher stillschweigend
    verschluckt, und im Bericht stand nur ein Strich. So blieb der Fehler bei
    der Spielsprache drei Übergaben lang unentdeckt: Er sah aus wie „nichts
    gefunden", war aber ein TypeError.
    """
    try:
        wert = f()
        if wert is None or wert == '':
            return standard
        return wert
    except Exception as ausnahme:
        try:
            from . import fehler
            fehler.merken('bericht.angabe', ausnahme)
        except Exception:
            pass              # das Melden darf den Bericht nie umwerfen
        return standard


def _spielsprache():
    """Wonach im Log gesucht wird — und woher die Formulierung stammt."""
    from . import phrasen as phrasen_modul
    gefunden, herkunft = phrasen_modul.sammeln()
    if not gefunden:
        return None
    woher = {'ini': t('b_woher_ini'),
             'eigen': t('b_woher_eigen'),
             'tabelle': t('b_woher_tabelle')}.get(herkunft, herkunft)
    return '%s (%s)' % (', '.join(gefunden), woher)


def _json_groesse(pfad_, schluessel):
    """Wie viele Einträge stehen in einer unserer JSON-Dateien?

    ⚠ Hier stand `daten.get(schluessel, daten)` — fehlte der Schlüssel, wurde
    also das **ganze** Wörterbuch gezählt. Der Bericht meldete damit „3
    Baupläne", weil die Datei drei Felder oben hat (version, stand, bauplaene),
    während darin 394 Baupläne standen. Eine falsche Zahl, die völlig plausibel
    aussieht — genau die Sorte, die niemand nachprüft.

    Fehlt der Schlüssel, steht jetzt `—` da. Lieber keine Angabe als eine
    erfundene, gerade in einem Bericht, mit dem jemand einen Fehler sucht.
    ⚠ Und: Eine Datei, die **es gar nicht gibt**, ist hier kein Fehler, sondern
    der Normalfall. Wer noch nichts auf die Merkliste gesetzt hat, hat keine
    `watchlist.json` — bis rc42 flog dabei ein `FileNotFoundError`, den `_sicher`
    zwar auffing, aber als Fehler in den Bericht schrieb. Im Bericht vom
    26.08.2026 stand er ganz oben, direkt über den echten Altlasten:

        bericht.angabe  FileNotFoundError: .../Bauplaene/watchlist.json

    Wer einen Fehler sucht, soll in dieser Liste keine Zeilen finden, die gar
    keine sind. Der Docstring von `_sicher` sagt es schon: „Ein leerer Wert ist
    normal (kein Spiel installiert, keine Merkliste) — eine Ausnahme ist es
    nicht."
    """
    if not os.path.exists(pfad_):
        return '—'
    with open(pfad_, encoding='utf-8') as f:
        daten = json.load(f)
    if schluessel not in daten:
        return '—'
    wert = daten[schluessel]
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


def _verpackung_lesbar():
    """Die Kennung aus `aktualisierung` in einen lesbaren Namen übersetzen.

    ⚠ Nur hier, nur für die Anzeige: Die Kennung selbst wird anderswo
    verglichen (`art == 'quellcode'`) und bleibt deshalb, wie sie ist.
    """
    art = __import__('scbp.aktualisierung',
                     fromlist=['verpackung']).verpackung()
    return {'quellcode': t('b_v_quellcode'),
            'exe': t('b_v_exe'),
            'appimage': t('b_v_appimage')}.get(art, art)


def _bildschirme(wurzel):
    """Größe und Skalierung — hier lagen schon zwei Fehler begraben."""
    if wurzel is None:
        return '—'
    breite = wurzel.winfo_screenwidth()
    hoehe = wurzel.winfo_screenheight()
    # 72 Punkte je Zoll ist Tks Bezug; daraus wird die Skalierung lesbar.
    skalierung = round(float(wurzel.tk.call('tk', 'scaling')) * 72 / 96 * 100)
    return t('b_skalierung') % (breite, hoehe, skalierung)


def _spielstarter():
    """Der Weg, auf dem Star Citizen gestartet würde — gekürzt und eingeordnet.

    Drei Auskünfte in einer Zeile: **ob** etwas gefunden wurde, **was**, und ob
    es der selbst eingetragene Startbefehl ist. Genau diese drei Fragen standen
    am 27.08.2026 zwei Stunden lang im Raum.
    """
    from . import pfade as pfade_modul
    from . import sprache as sprache_modul
    starter = pfade_modul.spielstarter()
    if not starter:
        return sprache_modul.t('b_starter_kein')
    kurz = pfade_modul.kuerzen(str(starter))
    eigen = (pfade_modul.einstellung('spielstarter') or '').strip()
    if eigen:
        return sprache_modul.t('b_starter_eigen', kurz)
    return kurz


def bauen(version='', wurzel=None, fehleranzahl=8):
    """Den Bericht als Text zusammensetzen."""
    zeilen = []

    def zeile(bez, wert):
        zeilen.append('%-18s%s' % (bez, pfade.kuerzen(wert)))

    zeilen.append(t('b_kopf')
                  % (version or '—', datetime.now().strftime(t('b_datum'))))
    zeilen.append('')

    uebersicht = _sicher(pfade.uebersicht, {})
    if not isinstance(uebersicht, dict):
        uebersicht = {}

    zeile(t('b_system'), _sicher(_system))
    zeile(t('b_verpackung'), _sicher(_verpackung_lesbar))
    zeile(t('b_python'), '%s / %s' % (platform.python_version(),
                                      _sicher(_tk_fassung)))
    zeile(t('b_bildschirm'), _sicher(lambda: _bildschirme(wurzel)))
    zeilen.append('')

    zeile(t('b_spiel'), _sicher(lambda: uebersicht.get('spiel_ordner')
                                 or t('b_nicht_gefunden')))
    zeile(t('b_gamelog'), _sicher(lambda: uebersicht.get('game_log')
                                   or t('b_nicht_gefunden')))
    zeile(t('b_sicherungen'), _sicher(
        lambda: t('b_protokolle') % uebersicht.get('sicherungen')))
    zeile(t('b_launcher'), _sicher(lambda: uebersicht.get('launcher')
                                    or t('b_nicht_da')))
    # ⚠ **Womit sich das Spiel starten ließe — und ob das jemand von Hand
    # eingetragen hat.** Ohne diese Zeile ist „der Startknopf tut nichts" nicht
    # zu beantworten, ohne den Nutzer auszufragen. Siehe die Regel: Was einen
    # Fehler erklären würde, gehört in den Bericht, bevor er das nächste Mal
    # gemeldet wird.
    zeile(t('b_starter'), _sicher(_spielstarter))
    # ⚠ `sammeln()` gibt ein **Tupel** zurück — (phrasen, herkunft). Hier stand
    # `', '.join(sammeln())`, was eine Liste mit einem String zusammenfügen
    # wollte und mit einem TypeError abbrach. `_sicher()` verschluckte den, und
    # im Bericht stand nur ein Strich. Drei Übergaben lang galt das als
    # ungeklärter Punkt; in Wahrheit war es diese eine fehlende `[0]`.
    #
    # Die Herkunft wird gleich mit ausgegeben: Sie sagt, ob die Formulierung aus
    # der echten `global.ini` des Spielers stammt oder nur aus unserer Tabelle
    # geraten ist — genau die Auskunft, die man bei „er erkennt meine Baupläne
    # nicht" als Erstes braucht.
    zeile(t('b_spielsprache'), _sicher(_spielsprache))
    zeilen.append('')

    zeile(t('b_bestand'), _sicher(lambda: t('b_n_bauplaene') % _json_groesse(
        __import__('scbp.bestand', fromlist=['pfad']).pfad(), 'bauplaene')))
    zeile(t('b_merkliste'), _sicher(lambda: t('b_n_eintraege') % _json_groesse(
        __import__('scbp.merkliste', fromlist=['pfad']).pfad(), 'eintraege')))
    zeile(t('b_katalog'), _sicher(lambda: __import__(
        'scbp.katalog', fromlist=['aktuelle_version']).aktuelle_version()))
    zeilen.append('')

    zeile(t('b_ordner'), _sicher(lambda: uebersicht.get('app_ordner')))
    zeile(t('b_einstellungen'), _sicher(lambda: ', '.join(
        '%s=%s' % (k, v) for k, v in sorted(
            (uebersicht.get('selbst_gesetzt') or {}).items()))
        or t('b_standard')))

    # ⚠ Die Startspur zuerst — bei einem Absturz ist sie das Einzige, was bleibt.
    # Ein `SIGSEGV` beendet den Prozess sofort: kein `except`, kein Fehlerbericht,
    # nur „es stürzt ab". Die letzte Zeile hier sagt, wie weit der Start kam.
    spur = _sicher(fehler.letzte_spur, [])
    if spur:
        zeilen.append('')
        zeilen.append(t('b_spur'))
        for eintrag in spur[-12:]:
            zeilen.append('  ' + eintrag)

    # ⚠ Und danach der harte Abbruch, falls es einen gab. Er steht **vor** den
    # Fehlern, weil er der schwerere Befund ist: Ein Eintrag in der Fehlerliste
    # heißt, das Programm hat weitergelebt; hier war es mitten im Befehl weg.
    # Nur die erste Handvoll Zeilen — der volle Aufrufweg aller Fäden füllt
    # Seiten, und der Melder soll den Bericht noch verschicken können.
    absturz = _sicher(fehler.letzter_absturz, [])
    if absturz:
        zeilen.append('')
        zeilen.append(t('b_absturz'))
        for eintrag in absturz[:14]:
            zeilen.append('  ' + eintrag)
        if len(absturz) > 14:
            zeilen.append('  … (%d)' % (len(absturz) - 14))

    letzte = _sicher(lambda: fehler.letzte(fehleranzahl), [])
    gesamt = _sicher(fehler.anzahl, 0)
    zeilen.append('')
    if letzte:
        zeilen.append(t('b_fehler') % (len(letzte), gesamt))
        for e in letzte:
            # ⚠ Die Version dazuschreiben und Altlasten kennzeichnen. Der Speicher
            # hebt die letzten zehn Einträge über Programmstarts hinweg auf; nach
            # einem Update stehen dort Fehler, die längst behoben sind. Ohne
            # Kennzeichnung sucht der Nächste nach einem Fehler, den es nicht mehr
            # gibt.
            fassung = e.get('fassung') or '?'
            alt_marke = ''
            if version and fassung not in ('?', '') and fassung != version:
                alt_marke = '  ' + t('b_fehler_alt')
            zeilen.append('  %s  %-10s %-24s %s: %s%s'
                          % (e.get('zeit', '—'), fassung, e.get('stelle', '—'),
                             e.get('art', '—'), e.get('meldung', '—'), alt_marke))
    else:
        zeilen.append(t('b_fehler_keine'))

    zeilen.append('')
    zeilen.append(t('b_fuss'))
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
        koerper = koerper[:URL_GRENZE] + t('m_bericht_gekuerzt')

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
    except Exception as ausnahme:
        try:
            from . import fehler
            fehler.merken('bericht.speichern', ausnahme)
        except Exception:
            pass
        return None


if __name__ == '__main__':
    sys.stdout.write(bauen(version='3.0.0-dev') + '\n')
