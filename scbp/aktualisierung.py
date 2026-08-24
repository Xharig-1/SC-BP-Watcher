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
Neue Fassungen bemerken, nachlesen und holen.

Niemand geht regelmäßig auf GitHub nachsehen, ob es etwas Neues gibt. Also
schaut das Programm selbst nach, sagt Bescheid und holt die neue Fassung auf
Knopfdruck. Und weil „es gibt eine neue Version" allein nichts wert ist, kann
man **nachlesen, was sich geändert hat** — auch bei älteren Fassungen.

Drei Teile:

  **Nachsehen.** Einmal am Tag gegen die GitHub-API, im Hintergrund. Ohne Netz
  passiert nichts und es wird auch nichts gemeldet.
  **Nachlesen.** Das Änderungsprotokoll liegt als `CHANGELOG.md` bei; neuere
  Einträge kommen aus den Release-Texten. Beides zusammen ergibt die Historie.
  **Holen.** Die zur eigenen Verpackung passende Datei (`.exe` oder AppImage)
  wird geladen und ersetzt die laufende.

> ⚠️ **Das Ersetzen ist heikel und je System verschieden.** Unter Windows kann
> sich eine laufende `.exe` nicht selbst überschreiben — die neue Datei wird
> daneben abgelegt und ein winziges Hilfsskript tauscht sie nach dem Beenden.
> Ein AppImage darf sich ersetzen, solange man die Datei austauscht statt in sie
> hineinzuschreiben. Wer aus dem Quellcode startet, bekommt keinen Selbstersatz
> angeboten — dort ist `git pull` der richtige Weg, und alles andere würde
> lokale Änderungen überfahren.

Geladen wird ausschließlich von `github.com`; eine Datei von woanders wird
abgelehnt, selbst wenn die API sie nennen würde.
"""
import json
import os
import re
import sys
import tempfile
import time
import urllib.request

from . import pfade

REPO = 'Xharig-1/SC-BP-Watcher'
API = 'https://api.github.com/repos/%s/releases' % REPO
SEITE = 'https://github.com/%s/releases/latest' % REPO
KENNUNG = 'SC-BP-Watcher (+https://github.com/%s)' % REPO
CACHE = 'versionen.json'
# Wie lange ein Blick auf GitHub gilt. Früher standen hier 24 Stunden — „einmal
# am Tag reicht". Tut es nicht: Wer das Programm mehrmals startet, bekam beim
# zweiten Mal nichts mehr zu sehen, obwohl inzwischen eine neue Fassung
# vorlag. Gemeldet am 24.08.2026, an einem Tag mit zehn Vorabversionen.
#
# Eine Stunde ist der Kompromiss: Beim Starten wird praktisch immer nachgesehen,
# im Dauerbetrieb bleibt es bei ein paar Abfragen am Tag.
ABSTAND = 3600
AUS = os.environ.get('SC_BP_NO_NET', '') not in ('', '0')
ERLAUBTE_HOSTS = ('github.com', 'objects.githubusercontent.com')


# ------------------------------------------------------------ Versionsvergleich
def _teile(version):
    """'v2.0.1-fork.3' -> (2, 0, 1). Vorspann und Zusatz werden ignoriert."""
    m = re.search(r'(\d+)\.(\d+)\.(\d+)', str(version or ''))
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _vorab(version):
    """Trägt die Version einen Vorab-Zusatz (-dev, -rc1, -beta, -alpha)?"""
    return bool(re.search(r'-(rc|beta|alpha|dev)', str(version or '')))


def _vorab_nummer(version):
    """Die Zahl hinter dem Zusatz: aus '2.0.0-rc2' wird 2, aus '-dev' wird 0."""
    m = re.search(r'-(?:rc|beta|alpha|dev)\.?(\d*)', str(version or ''))
    if not m:
        return 0
    return int(m.group(1)) if m.group(1) else 0


def ist_neuer(fremd, eigen):
    """Ist `fremd` eine höhere Version als `eigen`?

    Ein `-dev`-Zusatz gilt als **älter** als dieselbe Zahl ohne Zusatz: Wer eine
    Entwicklerfassung von 1.6.0 fährt, soll das fertige 1.6.0 angeboten bekommen."""
    a, b = _teile(fremd), _teile(eigen)
    if a != b:
        return a > b
    # Gleiche Zahl: Eine Fassung mit Zusatz (-dev, -rc1, -beta) gilt als älter
    # als dieselbe Zahl ohne. Wer 2.0.0-rc1 fährt, soll 2.0.0 angeboten bekommen.
    va, vb = _vorab(fremd), _vorab(eigen)
    if va != vb:
        return vb           # nur die fertige Fassung ist neuer
    if not va:
        return False        # beide fertig und gleiche Zahl
    # Beide Vorabversionen: nach der Nummer dahinter (rc1 < rc2 < rc10)
    return _vorab_nummer(fremd) > _vorab_nummer(eigen)


# ------------------------------------------------------------------- Nachsehen
def _hole(url, zeitlimit=20):
    req = urllib.request.Request(url, headers={
        'User-Agent': KENNUNG, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=zeitlimit) as r:
        return json.loads(r.read().decode('utf-8'))


def _cache_lesen():
    try:
        with open(pfade.app_datei(CACHE), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _cache_schreiben(daten):
    try:
        with open(pfade.app_datei(CACHE), 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False)
    except OSError:
        pass


def nachsehen(eigene_version, erzwingen=False):
    """Gibt es etwas Neues? Rückgabe: dict mit Angaben oder None.

    Gefragt wird höchstens einmal am Tag; dazwischen gilt der gemerkte Stand.
    Fehler sind kein Drama — ohne Netz meldet sich das Programm einfach nicht."""
    zwischen = _cache_lesen()
    # `SC_BP_NO_NET` verbietet das **Abfragen**, nicht das Wissen: Was schon
    # bekannt ist, darf weiter gemeldet werden — das ist keine Netzverbindung.
    alt_genug = time.time() - zwischen.get('geprueft', 0) > ABSTAND
    if not AUS and (erzwingen or alt_genug):
        try:
            freigaben = _hole(API + '?per_page=20')
            zwischen = {
                'geprueft': time.time(),
                'freigaben': [{
                    'version': f.get('tag_name'),
                    'name': f.get('name'),
                    'datum': (f.get('published_at') or '')[:10],
                    'text': f.get('body') or '',
                    'vorab': bool(f.get('prerelease')),
                    'dateien': [{'name': a.get('name'), 'url':
                                 a.get('browser_download_url'),
                                 'groesse': a.get('size')}
                                for a in (f.get('assets') or [])],
                } for f in freigaben if not f.get('draft')],
            }
            _cache_schreiben(zwischen)
        except Exception:
            pass                      # ohne Netz bleibt der letzte Stand

    # Vorabversionen bekommt **niemand ungefragt** angeboten — eine Vorabfassung
    # ist zum Prüfen da, nicht zum Verteilen. Angeboten werden sie in drei Fällen:
    #
    #   1. Der Spieler hat es in den Einstellungen ausdrücklich verlangt
    #      (`vorabversionen`, Standard aus). Das ist der Testkanal: Wer mithelfen
    #      will, bekommt die Fassungen vor allen anderen — wer Ruhe will, merkt
    #      von ihnen nichts und bleibt auf den fertigen Fassungen.
    #   2. Er fährt selbst schon eine Vorabfassung; dann wäre es unsinnig, ihm
    #      die nächste zu verschweigen.
    #   3. Die fertige Fassung zur selben Nummer erscheint — die ist ohnehin
    #      "neuer" als jede Vorabfassung (siehe `ist_neuer`), also endet der
    #      Testkanal nie in einer Sackgasse.
    eigene_ist_vorab = (_vorab(eigene_version)
                        or pfade.einstellung_wahrheit('vorabversionen', False))
    # ⚠ **Nicht** den ersten Treffer nehmen, sondern den höchsten.
    # GitHub gibt die Freigaben nach Erstellungszeit des Tags zurück, nicht nach
    # Versionsnummer — und das ist nicht dasselbe: In der Liste stand `rc10`
    # hinter `rc9`, weshalb Nutzern die **vorletzte** Fassung als „neu" gemeldet
    # wurde. Gemeldet am 24.08.2026.
    bester = None
    for f in zwischen.get('freigaben') or []:
        if not f.get('version'):
            continue
        if f.get('vorab') and not eigene_ist_vorab:
            continue
        if not ist_neuer(f['version'], eigene_version):
            continue
        if bester is None or ist_neuer(f['version'], bester['version']):
            bester = f
    return bester


def freigaben():
    """Alle bekannten Freigaben, neueste zuerst — für das Änderungsprotokoll."""
    return _cache_lesen().get('freigaben') or []


# --------------------------------------------------------- Änderungsprotokoll
def _changelog_datei():
    """Die mitgelieferte Änderungsliste in der Sprache des Nutzers finden.

    Es gibt zwei: `CHANGELOG.md` (englisch) und `CHANGELOG.de.md` (deutsch).
    Wer die Oberfläche auf Deutsch stehen hat, soll auch die Einträge auf
    Deutsch lesen — sonst wäre die Zweisprachigkeit an der Stelle nur behauptet.
    Fehlt die eigene Sprache, gilt die andere: eine fremdsprachige Auskunft ist
    besser als gar keine."""
    from . import sprache
    namen = (['CHANGELOG.de.md', 'CHANGELOG.md'] if sprache.aktuelle() == 'de'
             else ['CHANGELOG.md', 'CHANGELOG.de.md'])
    ordner = []
    if getattr(sys, 'frozen', False):        # PyInstaller legt Beigaben hierhin
        ordner.append(getattr(sys, '_MEIPASS', ''))
        ordner.append(os.path.dirname(sys.executable))
    ordner.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for name in namen:
        for ordner_p in ordner:
            if not ordner_p:
                continue
            voll = os.path.join(ordner_p, name)
            if os.path.isfile(voll):
                return voll
    return None


def protokoll():
    """Die Versionsgeschichte als Liste, neueste zuerst.

    Zusammengesetzt aus zwei Quellen: den Release-Texten von GitHub (die auch
    Fassungen kennen, die neuer sind als die eigene) und der mitgelieferten
    `CHANGELOG.md` (die auch ohne Netz da ist). Doppeltes wird zusammengeführt,
    die GitHub-Fassung hat Vorrang — sie ist die veröffentlichte Wahrheit."""
    eintraege, gesehen = [], set()
    for f in freigaben():
        schluessel = _teile(f.get('version'))
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        eintraege.append({'version': f.get('version') or '',
                          'datum': f.get('datum') or '',
                          'text': (f.get('text') or '').strip(),
                          'quelle': 'github'})

    datei = _changelog_datei()
    if datei:
        try:
            with open(datei, encoding='utf-8') as f:
                roh = f.read()
        except OSError:
            roh = ''
        for block in re.split(r'^## ', roh, flags=re.M)[1:]:
            kopf, _, rest = block.partition('\n')
            version = kopf.split('—')[0].split(' - ')[0].strip()
            schluessel = _teile(version)
            if schluessel == (0, 0, 0):
                continue        # „Unveröffentlicht" ist nichts für Nutzer
            if schluessel in gesehen:
                continue
            gesehen.add(schluessel)
            datum = ''
            m = re.search(r'(\d{4}-\d{2}-\d{2})', kopf)
            if m:
                datum = m.group(1)
            eintraege.append({'version': version, 'datum': datum,
                              'text': rest.strip(), 'quelle': 'changelog'})

    eintraege.sort(key=lambda e: (_teile(e['version']), e['datum']), reverse=True)
    return eintraege


# ------------------------------------------------------------------- Holen
def verpackung():
    """Wie läuft dieses Programm gerade? 'exe', 'appimage' oder 'quellcode'."""
    if os.environ.get('APPIMAGE'):
        return 'appimage'
    if getattr(sys, 'frozen', False):
        return 'exe'
    return 'quellcode'


def passende_datei(freigabe, art=None):
    """Die zur eigenen Verpackung passende Datei aus einer Freigabe — oder None."""
    art = art or verpackung()
    if art == 'quellcode':
        return None                      # dort ist `git pull` der richtige Weg
    endung = '.appimage' if art == 'appimage' else '.exe'
    for datei in freigabe.get('dateien') or []:
        name = (datei.get('name') or '').lower()
        url = datei.get('url') or ''
        if name.endswith(endung) and _url_ok(url):
            return datei
    return None


def _url_ok(url):
    """Nur Dateien von GitHub — egal, was die Antwort sonst behauptet."""
    try:
        from urllib.parse import urlparse
        teile = urlparse(url)
        return teile.scheme == 'https' and (
            teile.hostname in ERLAUBTE_HOSTS
            or (teile.hostname or '').endswith('.github.com'))
    except Exception:
        return False


def herunterladen(datei, fortschritt=None):
    """Lädt die neue Fassung in eine Nebendatei. Gibt deren Pfad zurück.

    Geladen wird **neben** das laufende Programm, nicht darüber: Bricht die
    Leitung ab, ist die alte Fassung noch vollständig da."""
    url = datei.get('url')
    if not _url_ok(url):
        raise ValueError('Datei kommt nicht von GitHub')
    ziel = os.path.join(tempfile.gettempdir(), datei.get('name') or 'update.bin')
    req = urllib.request.Request(url, headers={'User-Agent': KENNUNG})
    with urllib.request.urlopen(req, timeout=120) as r, open(ziel, 'wb') as f:
        gesamt = int(r.headers.get('Content-Length') or 0)
        geladen = 0
        while True:
            block = r.read(256 * 1024)
            if not block:
                break
            f.write(block)
            geladen += len(block)
            if fortschritt and gesamt:
                fortschritt(round(100 * geladen / gesamt))
    return ziel


def einspielen(neue_datei):
    """Die laufende Fassung durch die neue ersetzen.

    Gibt (True, '') zurück, wenn danach ein Neustart genügt — bei Windows
    übernimmt ein Hilfsskript nach dem Beenden. Bei (False, Grund) muss der
    Nutzer selbst ran."""
    art = verpackung()
    if art == 'quellcode':
        return False, 'quellcode'
    ziel = os.environ.get('APPIMAGE') or sys.executable
    try:
        if art == 'appimage':
            # Unter Linux darf die laufende Datei ersetzt werden, solange man sie
            # austauscht statt hineinzuschreiben: Der laufende Prozess hält die
            # alte Inode, die neue liegt sofort am Platz.
            os.replace(neue_datei, ziel)
            os.chmod(ziel, 0o755)
            return True, ''
        # Windows: die laufende .exe ist gesperrt. Also ein Hilfsskript, das
        # wartet, bis wir weg sind, dann tauscht und neu startet.
        skript = os.path.join(tempfile.gettempdir(), 'sc-bp-watcher-update.cmd')
        with open(skript, 'w', encoding='ascii', errors='ignore') as f:
            f.write('@echo off\r\n'
                    ':warten\r\n'
                    'timeout /t 1 /nobreak >nul\r\n'
                    'move /y "%s" "%s" >nul 2>&1 || goto warten\r\n'
                    'start "" "%s"\r\n'
                    'del "%%~f0"\r\n' % (neue_datei, ziel, ziel))
        import subprocess
        subprocess.Popen(['cmd', '/c', skript],
                         creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0))
        return True, ''
    except Exception as fehler:
        return False, str(fehler)


if __name__ == '__main__':
    eigene = '1.6.0-dev'
    print('Verpackung:', verpackung())
    neu = nachsehen(eigene, erzwingen='--jetzt' in sys.argv)
    print('Neuere Fassung:', (neu or {}).get('version') or 'keine')
    print('\nÄnderungsprotokoll:')
    for e in protokoll()[:6]:
        kopf = '%s %s' % (e['version'], ('(%s)' % e['datum']) if e['datum'] else '')
        print('  %-28s %s  %d Zeichen' % (kopf, e['quelle'], len(e['text'])))
