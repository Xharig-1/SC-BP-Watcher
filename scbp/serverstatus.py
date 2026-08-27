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
Läuft Star Citizen gerade? — der Serverstatus von CIG.

**Wozu.** Wer craften will und das Spiel lässt ihn nicht hinein, sucht den Fehler
zuerst bei sich: Neu starten, Ordner leeren, Anmeldung prüfen. Ein Blick ins
Werkzeug beantwortet die Frage vorher.

⚠️ **Das hier ist eine Meldung von CIG, keine Messung.** Die Statusseite wird von
Hand gepflegt. Vergisst jemand, eine Meldung zu schließen, steht dort weiter
„Wartung"; stürzen die Server ab, bevor jemand schreibt, steht dort „läuft".
Deshalb gehört an die Anzeige **immer** die Uhrzeit des Abrufs und die Quelle —
und sie darf nie als eigene Feststellung auftreten.

⚠️ **Die Zustände bleiben im Wortlaut von CIG** (`operational`, `maintenance`,
`major_outage`). Eine Übersetzung wäre eine Aussage, die RSI nie gemacht hat —
und im Zweifel eine falsche.

Die Quelle (geprüft 26.08.2026):

    index.json                       Lage aller Systeme, rund 3 KB
    issues/<datei>/index.json        ein Vorfall im Volltext
    issues/index.json                die Historie, rund 145 KB

Es ist eine **statische Seite** (cState auf S3) — kein Schlüssel, keine Anmeldung.

⚠️ **Sackgasse, die Zeit kostet:** Die üblichen Atlassian-Pfade
(`/api/v2/status.json`, `/api/v2/summary.json`) antworten mit **403**. Wer dort
sucht, hält die Seite für unlesbar und gibt auf, obwohl die Daten offen liegen.

**Sparsam fragen.** Die Seite liefert `ETag` und `Last-Modified`. Gefragt wird mit
`If-None-Match`; hat sich nichts geändert, antwortet der Server mit **304** und
ohne Inhalt. Das kostet fast nichts und darf deshalb oft passieren.
"""
import calendar
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

from . import pfade

BASIS = 'https://status.robertsspaceindustries.com'
CACHE = 'serverstatus.json'
ZEITLIMIT = 15
AUS = os.environ.get('SC_BP_NO_NET', '') not in ('', '0')

# Wie alt die gespeicherte Lage werden darf, bevor erneut gefragt wird.
FRISCHE_SEK = 300

# Die Ampelfarben stehen in der Seite selbst (`colorOk` und Geschwister). Sie
# hier noch einmal zu führen wäre doppelt — geholt werden sie beim Abruf und
# mit gespeichert. Diese hier greifen nur, wenn noch nie etwas geholt wurde.
FARBEN = {'ok': '#008000', 'gestoert': '#cc4400',
          'aus': '#e60000', 'hinweis': '#24478f'}

# Welcher Zustand welche Ampel bekommt. cState kennt mehr Namen als die drei
# Farben; alles Unbekannte gilt als Störung — lieber einmal zu viel gewarnt.
AMPEL = {
    'operational': 'ok',
    'monitoring': 'hinweis',
    'maintenance': 'hinweis',
    'degraded_performance': 'gestoert',
    'partial_outage': 'gestoert',
    'major_outage': 'aus',
}


def _kennung():
    from sc_bp_watcher import __version__ as v
    return 'SC-BP-Watcher/%s (+https://github.com/Xharig-1/SC-BP-Watcher)' % v


def _hole(pfad, etag=None):
    """Eine Datei der Statusseite holen.

    Gibt `(daten, etag)` zurück. Bei **304** (nichts geändert) kommt
    `(None, etag)` — das ist kein Fehler, sondern der Normalfall."""
    if AUS:
        return None, etag
    kopf = {'User-Agent': _kennung(), 'Accept': 'application/json'}
    if etag:
        kopf['If-None-Match'] = etag
    anfrage = urllib.request.Request(BASIS + pfad, headers=kopf)
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            roh = antwort.read().decode('utf-8', 'replace')
            return json.loads(roh), antwort.headers.get('ETag') or etag
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None, etag
        raise


def _text_aus_html(roh):
    """Aus dem Meldungstext lesbare Zeilen machen — **mit** der Hervorhebung.

    Rückgabe: `[(text, fett), …]`.

    Der Text kommt als HTML, jede Zeile ein Absatz. CIG hebt darin genau das
    hervor, was man tun soll: „**Players are strongly advised to safely stow
    their vehicles**". Wer das Fett wegwirft, macht aus einer Warnung einen
    Satz unter vielen — deshalb wird `<strong>`/`<b>` mitgenommen und in der
    Anzeige wieder fett gesetzt.

    Bewusst kein HTML-Parser: Es geht um Absätze, Zeilenumbrüche, Fettung und
    Entities, nicht um verschachtelte Auszeichnung. `<!-- raw HTML omitted -->`
    steht als Kommentar drin und fällt beim Entfernen der Tags von selbst weg.
    """
    if not roh:
        return []
    text = re.sub(r'(?i)<!--.*?-->', '', roh, flags=re.S)
    text = re.sub(r'(?i)<br\s*/?>', '\n', text)
    text = re.sub(r'(?i)</p\s*>', '\n\n', text)

    zeilen = []
    for stueck in text.split('\n'):
        if not stueck.strip():
            continue
        # Fett ist die Zeile, wenn ihr sichtbarer Text vollständig in einer
        # Hervorhebung steckt. Ein einzelnes fettes Wort mitten im Satz
        # bekäme sonst die ganze Zeile fett — falsch gewichtet.
        ohne_tags = re.sub(r'<[^>]+>', '', stueck).strip()
        # Verglichen wird der Text **innerhalb** der Hervorhebung mit dem
        # gesamten sichtbaren Text. Nur wenn beide gleich sind, ist die ganze
        # Zeile hervorgehoben.
        hervor = ' '.join(
            re.sub(r'<[^>]+>', '', treffer)
            for treffer in re.findall(r'(?is)<(?:strong|b)\s*>(.*?)</(?:strong|b)\s*>',
                                      stueck)).strip()
        fett = bool(hervor) and hervor == ohne_tags
        sauber = html.unescape(ohne_tags)
        if sauber:
            zeilen.append((sauber, fett))
    return zeilen


def _zeitstempel(roh):
    """'2026-08-26 14:15:00 +0000 UTC' -> Sekunden seit 1970, oder None.

    ⚠ **Die Seite rechnet in UTC**, auch wo keine Zone dabeisteht (`buildTimezone`
    sagt es für die ganze Datei). Wer das mit `time.mktime` liest, verschiebt
    jede Angabe um den eigenen Zeitunterschied — in Deutschland um ein bis zwei
    Stunden. Ein Vorfall von vor zehn Minuten stünde dann als „in zwei Stunden"
    da. Deshalb `calendar.timegm`, das ausdrücklich UTC liest.

    cState schreibt außerdem mehrere Formate in dieselbe Datei: mit Zone
    (`+0000 UTC`), mit doppelter Zone, ganz ohne — und `buildTime` sogar **ohne
    Sekunden** (`18:30`). Deshalb sind die Sekunden im Muster wahlfrei.
    Scheitert das Lesen, gibt es lieber **keine** Zeit als eine falsche."""
    if not roh:
        return None
    m = re.match(r'(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::(\d{2}))?',
                 str(roh).strip())
    if not m:
        return None
    tag, stunde, sekunde = m.group(1), m.group(2), m.group(3) or '00'
    try:
        return calendar.timegm(
            time.strptime('%s %s:%s' % (tag, stunde, sekunde), '%Y-%m-%d %H:%M:%S'))
    except Exception:
        return None


# ------------------------------------------------------------------- Abruf
def _cache_lesen():
    try:
        with open(pfade.app_datei(CACHE), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _cache_schreiben(daten):
    ziel = pfade.app_datei(CACHE)
    try:
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        temp = ziel + '.tmp'
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False)
        os.replace(temp, ziel)
    except Exception:
        pass


def gespeicherte_lage():
    """Der zuletzt geholte Stand — **ohne** ins Netz zu gehen.

    Damit steht beim Öffnen der Seite sofort etwas da, während der frische
    Abruf noch läuft. Gab es nie einen Abruf, kommt `{}` zurück."""
    return (_cache_lesen().get('lage') or {})


def lage(erzwingen=False, frist=None):
    """Die Lage aller Systeme — aus dem Netz oder aus dem Zwischenspeicher.

    Rückgabe:

        {'gesamt': 'operational',
         'systeme': [{'name': 'Platform', 'status': 'operational',
                      'ampel': 'ok', 'farbe': '#008000', 'meldungen': [...]}, …],
         'geholt': 1756240000.0,      # wann zuletzt gefragt wurde
         'stand': 1756238000.0,       # wann CIG die Seite zuletzt geändert hat
         'quelle': 'https://status.robertsspaceindustries.com/'}

    Wirft nie. Ohne Netz gilt der letzte Stand; gab es nie einen, kommt
    `{}` zurück — dann zeigt die Oberfläche nichts an, statt zu raten."""
    gespeichert = _cache_lesen()
    alt = gespeichert.get('lage') or {}
    # `frist` sagt, wie alt der gespeicherte Stand sein darf, bevor überhaupt
    # gefragt wird. Der Live-Takt setzt sie auf 0: Er fragt jede Minute, aber
    # **mit** ETag — unverändert antwortet der Server mit 304 und ohne Inhalt.
    # Das ist der billige Fall und darf deshalb oft passieren.
    grenze = FRISCHE_SEK if frist is None else frist
    frisch = (time.time() - (alt.get('geholt') or 0)) < grenze
    if alt and frisch and not erzwingen:
        return alt

    try:
        # ⚠ Beim erzwungenen Abruf **ohne** ETag fragen. Sonst antwortet der
        # Server mit 304, und „jetzt nachsehen" liefert genau die Daten zurück,
        # die schon dastanden — der Knopf wirkt kaputt, obwohl alles läuft.
        daten, etag = _hole('/index.json',
                            None if erzwingen else gespeichert.get('etag'))
    except Exception:
        return alt                      # Netz weg: der letzte Stand gilt weiter

    if daten is None:                   # 304 — unverändert, nur die Uhr stellen
        if alt:
            alt['geholt'] = time.time()
            gespeichert['lage'] = alt
            _cache_schreiben(gespeichert)
        return alt

    farben = {
        'ok': daten.get('colorOk') or FARBEN['ok'],
        'gestoert': daten.get('colorDisrupted') or FARBEN['gestoert'],
        'aus': daten.get('colorDown') or FARBEN['aus'],
        'hinweis': daten.get('colorNotice') or FARBEN['hinweis'],
    }
    systeme = []
    for s in daten.get('systems') or []:
        zustand = (s.get('status') or '').strip()
        ampel = AMPEL.get(zustand, 'gestoert')
        systeme.append({
            'name': s.get('name') or '?',
            'status': zustand,          # im Wortlaut von CIG, nie übersetzt
            'ampel': ampel,
            'farbe': farben[ampel],
            'meldungen': [_vorfall_kurz(i) for i in (s.get('unresolvedIssues') or [])],
        })

    neu = {
        'gesamt': (daten.get('summaryStatus') or '').strip(),
        'systeme': systeme,
        'geholt': time.time(),
        'stand': _zeitstempel('%s %s' % (daten.get('buildDate') or '',
                                         daten.get('buildTime') or '')),
        'quelle': BASIS + '/',
    }
    _cache_schreiben({'etag': etag, 'lage': neu})
    return neu


def nachfragen():
    """Ein Blick, ob sich etwas geändert hat — für den laufenden Takt.

    Fragt **mit** ETag. Hat CIG nichts angefasst, kommt ein 304 ohne Inhalt
    zurück; das kostet kaum etwas und darf deshalb jede Minute passieren. Nur
    wenn sich wirklich etwas geändert hat, wird gelesen und gespeichert.

    Gibt `(lage, veraendert)` zurück — `veraendert` sagt der Oberfläche, ob sie
    überhaupt neu zeichnen muss. Ohne das würde die Anzeige jede Minute
    zerlegt und neu aufgebaut, obwohl sich nichts getan hat: Wer gerade eine
    Meldung liest, verlöre dabei seine Rollposition."""
    vorher = gespeicherte_lage()
    neu = lage(frist=0)
    return neu, _kern(neu) != _kern(vorher)


def _kern(lage_):
    """Woran man erkennt, ob sich inhaltlich etwas geändert hat.

    Bewusst **ohne** `geholt` — das ändert sich bei jedem Blick und würde jede
    Nachfrage als Änderung ausgeben."""
    if not lage_:
        return None
    return (lage_.get('gesamt'),
            tuple((s.get('name'), s.get('status'),
                   tuple(sorted(m.get('titel') or '' for m in s.get('meldungen') or [])))
                  for s in lage_.get('systeme') or []))


def _vorfall_kurz(roh):
    """Die Angaben zu einem Vorfall, wie sie in der Systemliste mitkommen."""
    return {
        'titel': roh.get('title') or '',
        'schwere': (roh.get('severity') or '').strip(),
        'betroffen': list(roh.get('affected') or []),
        'begonnen': _zeitstempel(roh.get('createdAt')),
        'erledigt': _zeitstempel(roh.get('resolvedAt')),
        'datei': roh.get('filename') or '',
        'adresse': roh.get('permalink') or '',
    }


def vorfall(datei):
    """Ein Vorfall im Volltext — Meldung samt Update-Zeilen.

    `datei` ist der Dateiname aus der Übersicht (`2026-08-26_live-deployment.md`).
    Die Endung fällt weg, der Rest ist der Ordner unter `/issues/`."""
    name = re.sub(r'\.md$', '', (datei or '').strip())
    if not name:
        return {}
    try:
        daten, _ = _hole('/issues/%s/index.json' % name)
    except Exception:
        return {}
    if not daten:
        return {}
    e = _vorfall_kurz(daten)
    e['zeilen'] = _text_aus_html(daten.get('body'))
    return e


def meldungen(monate=2, hoechstens=12):
    """Die Meldungen der letzten Monate — im Volltext, wie auf der Statusseite.

    Die Seite zeigt unter „Latest incidents" **auch erledigte** Vorfälle. Das ist
    der eigentliche Nutzen: Wer abends nicht ins Spiel kommt, will sehen, ob es
    heute Nachmittag eine Wartung gab — nicht nur, ob gerade eine läuft.

    ⚠ **Jeder Volltext ist ein eigener Abruf.** Deshalb werden sie
    zwischengespeichert und nur einmal geholt: Eine erledigte Meldung von
    vorletzter Woche ändert sich nicht mehr. Ohne den Zwischenspeicher liefen
    bei jedem Öffnen des Reiters ein Dutzend Abrufe los.

    Zwei Monate sind Absicht, nicht die ganze Historie: Sie liegt vollständig
    unter der verlinkten Adresse, und 265 Vorfälle im Fenster hülfen niemandem."""
    grenze = time.time() - monate * 30 * 86400
    zwischen = _cache_lesen()
    volltexte = zwischen.get('volltexte') or {}
    ergebnis, neu_geholt = [], False

    for kurz in historie(60):
        wann = kurz.get('begonnen') or 0
        if wann and wann < grenze:
            break                      # die Liste ist nach Datum sortiert
        datei = kurz.get('datei') or ''
        if datei in volltexte:
            voll = volltexte[datei]
        else:
            voll = vorfall(datei)
            if voll:
                # Nur Erledigtes darf dauerhaft liegen bleiben. Eine offene
                # Meldung bekommt weitere Update-Zeilen — die würden wir sonst
                # nie wieder sehen.
                if voll.get('erledigt'):
                    volltexte[datei] = voll
                    neu_geholt = True
        if voll:
            ergebnis.append(voll)
        if len(ergebnis) >= hoechstens:
            break

    if neu_geholt:
        zwischen['volltexte'] = volltexte
        _cache_schreiben(zwischen)
    return ergebnis


def historie(hoechstens=20):
    """Die letzten Vorfälle — neueste zuerst.

    Gedacht zum Nachsehen („war gestern etwas?") und als Prüfstoff: Solange
    alles läuft, gibt es keine offene Meldung, mit der sich die Anzeige testen
    ließe. Ein alter Vorfall füllt diese Lücke."""
    try:
        daten, _ = _hole('/issues/index.json')
    except Exception:
        return []
    seiten = (daten or {}).get('pages') or []
    return [_vorfall_kurz(s) for s in seiten[:hoechstens]]
