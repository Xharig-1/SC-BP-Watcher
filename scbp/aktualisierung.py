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
import errno
import os
import re
import sys
import tempfile
import time
import urllib.request

from . import fehler
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


def neueste(mit_vorab):
    """Die neueste bekannte Freigabe eines Kanals — unabhängig von der eigenen Fassung.

    ⚠ Nicht dasselbe wie `nachsehen()`. Das meldet nur, was **neuer** ist als die
    laufende Fassung — richtig für eine Update-Meldung, unbrauchbar für einen
    Knopf „hol mir die letzte fertige Fassung". Wer eine Testfassung fährt, will
    ja gerade zurück auf die fertige können.
    """
    bester = None
    for f in freigaben():
        if not f.get('version'):
            continue
        if f.get('vorab') and not mit_vorab:
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


# Welche Überschrift im CHANGELOG bedeutet was. Die Zuordnung ist bewusst
# großzügig — englische wie deutsche Fassung, und wer eine neue Überschrift
# erfindet, landet unter „neu" statt im Nichts.
_ARTEN = (
    ('fix',  ('behoben', 'fixed', 'korrigiert', 'bugfix')),
    ('bess', ('geändert', 'changed', 'verbessert', 'improved', 'entfernt',
              'removed', 'bedienung')),
    ('neu',  ('hinzugefügt', 'added', 'neu', 'new')),
)


def einleitung(text):
    """Der Satz, mit dem eine Fassung vorgestellt wird — das Zitat im Changelog.

    Im Markdown steht er als `> …`-Block über den Aufzählungen: „Ein Fenster für
    alles." Er sagt in einem Satz, worum es in der Fassung ging, und war bisher
    nirgends zu sehen — `punkte_nach_art` wirft alles weg, was keine Aufzählung
    ist. Genau dieser Satz gehört aber unter die Version, wenn man sie aufklappt.
    """
    zeilen = []
    for zeile in (text or '').split('\n'):
        blank = zeile.strip()
        if blank.startswith('>'):
            zeilen.append(blank.lstrip('>').strip())
        elif zeilen and not blank:
            break                      # der Block ist zu Ende
        elif zeilen:
            break
    satz = ' '.join(z for z in zeilen if z)
    # Die Auszeichnungen sind im Fenster nur Zeichen — sie stören mehr, als sie
    # helfen.
    return satz.replace('**', '').replace('`', '').strip()


def punkte_nach_art(text):
    """Zerlegt einen Änderungstext in (art, zeile) — für Filter und Marken.

    Der Text ist Markdown mit Zwischenüberschriften (`### Behoben`). Alles
    darunter gilt als diese Art, bis die nächste Überschrift kommt. Ohne
    Überschrift gilt „neu": Lieber falsch einsortiert als unsichtbar.
    """
    art = 'neu'
    heraus = []
    for zeile in (text or '').split('\n'):
        # ⚠ Die Einrückung muss VOR dem Abschneiden geprüft werden — sonst sind
        # Unterpunkte nicht mehr von Hauptpunkten zu unterscheiden.
        eingerueckt = zeile[:1].isspace()
        blank = zeile.strip()
        if blank.startswith('#'):
            klein = blank.lstrip('#').strip().lower()
            for kennung, woerter in _ARTEN:
                if any(w in klein for w in woerter):
                    art = kennung
                    break
            continue
        if not eingerueckt and blank.startswith(('- ', '* ')):
            heraus.append([art, blank[2:].strip()])
        elif eingerueckt and blank and not blank.startswith(('- ', '* ')) and heraus:
            # Eine eingerückte Zeile **ohne** Aufzählungszeichen ist die
            # Fortsetzung des Punktes darüber — im Markdown umgebrochen, im
            # Fenster gehört sie an denselben Satz. Wer sie verwirft, zeigt
            # abgeschnittene Sätze („… ganz unten") und merkt es nicht, weil
            # es wie ein Zeilenumbruch aussieht.
            heraus[-1][1] = (heraus[-1][1] + ' ' + blank).strip()
    return [(a, z) for a, z in heraus]


def protokoll():
    """Die Versionsgeschichte als Liste, neueste zuerst.

    Zusammengesetzt aus zwei Quellen: der **mitgelieferten** `CHANGELOG.de.md`
    bzw. `CHANGELOG.md` — je nach eingestellter Sprache — und den Release-Texten
    von GitHub, die auch Fassungen kennen, die neuer sind als die eigene.

    ⚠ Der mitgelieferte Changelog hat Vorrang, **weil nur er die Sprache kennt**.
    Der Release-Text auf GitHub ist bewusst zweisprachig aufgebaut: Englisch oben,
    Deutsch in einem aufklappbaren Block darunter. Auf der Release-Seite ist das
    richtig — im Fenster wurde daraus eine englische Liste für jemanden, der die
    Oberfläche auf Deutsch stehen hat. Genau so gemeldet.

    GitHub springt nur dort ein, wo der Changelog nichts hat: bei Fassungen, die
    neuer sind als die eigene.
    """
    eintraege, gesehen = [], {}
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
            datum = ''
            m = re.search(r'(\d{4}-\d{2}-\d{2})', kopf)
            if m:
                datum = m.group(1)
            if schluessel in gesehen:
                continue
            eintrag = {'version': version, 'datum': datum,
                       'text': rest.strip(), 'quelle': 'changelog'}
            gesehen[schluessel] = eintrag
            eintraege.append(eintrag)

    # Und nun alles, was der mitgelieferte Changelog noch nicht kennt — das sind
    # die Fassungen, die nach dieser hier erschienen sind.
    for f in freigaben():
        schluessel = _teile(f.get('version'))
        if schluessel in gesehen or not f.get('version'):
            continue
        eintrag = {'version': f.get('version'),
                   'datum': f.get('datum') or '',
                   'text': (f.get('text') or '').strip(),
                   'quelle': 'github'}
        gesehen[schluessel] = eintrag
        eintraege.append(eintrag)

    eintraege.sort(key=lambda e: (_teile(e['version']), e['datum']), reverse=True)
    return eintraege


# ------------------------------------------------------------------- Holen
def eigenes_appimage():
    """Der Pfad **unseres** AppImage — oder None.

    ⚠ `APPIMAGE` allein genügt nicht. Die Variable steht in der Umgebung
    **jedes** Programms, das aus einem AppImage heraus gestartet wurde — auch in
    einem Terminal, das man daraus öffnet, und in allem, was von dort aus läuft.
    Wer nur auf sie schaut, hält jedes beliebige Programm für sich selbst.

    Das ist am 25.08.2026 teuer geworden: Ein Testlauf des Selbst-Updates lief in
    einer Umgebung, in der `APPIMAGE` auf eine **fremde** Anwendung zeigte — und
    das Update hat prompt diese fremde Datei überschrieben (234 MB durch 12 MB
    ersetzt). Zurückzuholen war sie nur, weil das fremde Programm noch lief und
    die alte Inode über `/proc/<pid>/exe` offen hielt.

    Verlässlich ist erst der zweite Teil: Zu einem AppImage gehört `APPDIR`, der
    Ort, an dem es entpackt eingehängt ist. Nur wenn **unser eigener Code** von
    dort kommt, laufen wir wirklich in diesem AppImage.
    """
    pfad = os.environ.get('APPIMAGE')
    if not pfad or not os.path.isfile(pfad):
        return None
    # ⚠ Der erste Anlauf verglich den eigenen Code mit `APPDIR`. Das ging schief:
    # PyInstaller entpackt sich in ein **eigenes** Verzeichnis (`sys._MEIPASS`,
    # etwa `/tmp/_MEIabc123`), nicht in den AppImage-Einhängepunkt. Der Vergleich
    # schlug also **immer** fehl — das Programm hielt sich für eine `.exe`, ging in
    # den Windows-Zweig und meldete „[Errno 2] No such file or directory: 'cmd'".
    #
    # Maßgeblich ist stattdessen der Dateiname: Zeigt `APPIMAGE` auf eine Datei,
    # die nach diesem Programm heißt, ist es unsere. Ein fremdes AppImage — der
    # Unfall, um den es hier geht — heißt anders und fällt durch.
    if 'sc-bp-watcher' not in os.path.basename(pfad).lower():
        return None
    return pfad


def verpackung():
    """Wie läuft dieses Programm gerade? 'exe', 'appimage' oder 'quellcode'."""
    if eigenes_appimage():
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


def _ablageort_fuer_update(name):
    """Wohin die neue Fassung geladen wird — **neben** die laufende.

    ⚠ Hier lag ein Fehler, der jedes Selbst-Update unter Linux scheitern ließ:
    Geladen wurde nach `/tmp`, eingespielt mit `os.replace()`. Auf so gut wie jedem
    Linux ist `/tmp` ein eigenes Dateisystem (tmpfs), und `os.replace` kann nicht
    über Dateisystemgrenzen verschieben — es endet mit
    „[Errno 18] Invalid cross-device link". Gemeldet am 25.08.2026 direkt aus dem
    Fenster.

    Der Docstring versprach schon immer „neben das laufende Programm"; jetzt tut es
    der Code auch. Nebenbei ist das Einspielen dadurch **atomar**: Innerhalb eines
    Dateisystems ist `os.replace` unteilbar, es gibt keinen Moment, in dem die Datei
    halb da ist.

    Ist der Zielordner nicht beschreibbar, bleibt `/tmp` als Rückfall — dann greift
    beim Einspielen der Umweg über `shutil.move`.
    """
    laufende = eigenes_appimage() or sys.executable
    ordner = os.path.dirname(os.path.abspath(laufende))
    if os.access(ordner, os.W_OK):
        return os.path.join(ordner, '.' + (name or 'update.bin') + '.neu')
    return os.path.join(tempfile.gettempdir(), name or 'update.bin')


def herunterladen(datei, fortschritt=None):
    """Lädt die neue Fassung in eine Nebendatei. Gibt deren Pfad zurück.

    Geladen wird **neben** das laufende Programm, nicht darüber: Bricht die
    Leitung ab, ist die alte Fassung noch vollständig da."""
    url = datei.get('url')
    if not _url_ok(url):
        raise ValueError('Datei kommt nicht von GitHub')
    ziel = _ablageort_fuer_update(datei.get('name'))
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


# Wie lange das Windows-Hilfsskript auf die Freigabe der .exe wartet (Sekunden).
#
# ⚠ Es MUSS eine Grenze geben. Vorher lief die Schleife ewig — und weil die
# .exe erst frei wird, wenn der Nutzer das Programm beendet, lief sie bei jedem
# Klick auf „holen" ein weiteres Mal. Beim Testen kamen so mehrere Fenster
# zusammen, die nur der Task-Manager wieder losgeworden ist.
#
# 120 Sekunden sind großzügig: Wer nach zwei Minuten nicht beendet hat, macht
# gerade etwas anderes. Das Update geht dabei nicht verloren — die neue Datei
# bleibt liegen und wird beim nächsten Versuch genommen.
VERSUCHE_TAUSCH = 120


# ⚠ Unter Windows tauscht ein Hilfsskript die Datei, NACHDEM wir weg sind — und
# startet die neue Fassung gleich selbst (`start "" …` am Ende des Skripts).
# `neu_starten()` darf dann NICHT auch noch starten: Zu dem Zeitpunkt liegt auf
# der Platte noch die **alte** `.exe`, der Tausch kommt ja erst nach unserem
# Ende. Ein eigener Start fährt also die alte Fassung erneut hoch — und die
# hält dann den Temp-Ordner fest und blockiert den Tausch endgültig.
#
# Genau das hat Haldjas am 25.08.2026 gesehen: „der watcher ist irgendwie noch
# am leben als rc25", dazu „Failed to remove temporary directory". Zwei
# Symptome, eine Ursache — der doppelte Start.
_TAUSCH_LAEUFT = [False]


def einspielen(neue_datei):
    """Die laufende Fassung durch die neue ersetzen.

    Gibt (True, '') zurück, wenn danach ein Neustart genügt — bei Windows
    übernimmt ein Hilfsskript nach dem Beenden. Bei (False, Grund) muss der
    Nutzer selbst ran."""
    art = verpackung()
    if art == 'quellcode':
        return False, 'quellcode'
    ziel = eigenes_appimage() or sys.executable

    # ⚠ Letzter Riegel vor dem Überschreiben: Der Dateiname muss zu uns gehören.
    # Selbst wenn die Erkennung oben irgendwann wieder danebenliegt, wird dadurch
    # keine fremde Datei ersetzt. Genau dieser Riegel hätte den Unfall vom
    # 25.08.2026 verhindert, bei dem ein fremdes AppImage überschrieben wurde,
    # weil `APPIMAGE` auf ein anderes Programm zeigte.
    if 'sc-bp-watcher' not in os.path.basename(ziel).lower():
        return False, ('Zieldatei gehört nicht zu diesem Programm: %s'
                       % os.path.basename(ziel))
    try:
        if art == 'appimage':
            # Unter Linux darf die laufende Datei ersetzt werden, solange man sie
            # austauscht statt hineinzuschreiben: Der laufende Prozess hält die
            # alte Inode, die neue liegt sofort am Platz.
            #
            # ⚠ `os.replace` schafft das nur **innerhalb eines Dateisystems**.
            # Deshalb wird gleich daneben geladen (siehe `_ablageort_fuer_update`).
            # Liegt die Datei doch woanders — Zielordner schreibgeschützt, eigener
            # Pfad über `SC_BP_APPIMAGE` —, tut es `shutil.move`: Das kopiert bei
            # Bedarf und räumt danach auf. Langsamer, aber es funktioniert.
            try:
                os.replace(neue_datei, ziel)
            except OSError as grund:
                if getattr(grund, 'errno', None) != errno.EXDEV:
                    raise
                import shutil
                shutil.move(neue_datei, ziel)
            os.chmod(ziel, 0o755)
            return True, ''
        # Windows: die laufende .exe ist gesperrt. Also ein Hilfsskript, das
        # wartet, bis wir weg sind, dann tauscht und neu startet.
        #
        # ⚠ Drei Fehler steckten hier, und zusammen ergaben sie das, was Haldjas
        # beim Testen erlebt hat: „hat er mir erstmal nen haufen terminals
        # ausgespuckt bis ich den prozess mit dem task manager gekillt hab".
        #
        # 1. **Das Fenster.** `DETACHED_PROCESS` gibt dem `cmd` eine eigene
        #    Konsole — sichtbar. `CREATE_NO_WINDOW` nicht.
        # 2. **Die Endlosschleife.** `|| goto warten` lief ewig weiter, solange
        #    die `.exe` gesperrt blieb. Sie bleibt es aber, bis der Nutzer das
        #    Programm beendet — und wer stattdessen nochmal auf „holen" klickt,
        #    bekommt ein zweites ewig laufendes Fenster. Jetzt ist nach
        #    VERSUCHE_TAUSCH Sekunden Schluss.
        # 3. **Mehrfachstart.** Jeder Klick schrieb dieselbe Datei neu und
        #    startete noch ein `cmd`. Jetzt wird ein laufendes vorher beendet.
        import subprocess
        skript = os.path.join(tempfile.gettempdir(), 'sc-bp-watcher-update.cmd')

        # Ein schon laufendes Update-Skript aus dem Weg räumen, bevor ein
        # neues startet — sonst tauschen zwei gleichzeitig dieselbe Datei.
        try:
            # ⚠ Auch DIESER Aufruf braucht `CREATE_NO_WINDOW`. In rc22 wurde
            # das Hilfsskript unsichtbar gemacht, der `taskkill` davor aber
            # übersehen — er ist ein Konsolenprogramm und reißt aus einer
            # Fensteranwendung heraus eine eigene Konsole auf. Morkhan hat es
            # am 26.08.2026 gesehen: „öffnet sich ein fenster für ne
            # milisekunde und nachdem es zugeht passiert nix".
            subprocess.run(['taskkill', '/f', '/im', 'cmd.exe', '/fi',
                            'WINDOWTITLE eq sc-bp-watcher-update*'],
                           capture_output=True, timeout=5,
                           creationflags=getattr(subprocess,
                                                 'CREATE_NO_WINDOW', 0))
        except Exception:
            pass                      # kein laufendes da, oder taskkill fehlt

        with open(skript, 'w', encoding='ascii', errors='ignore') as f:
            f.write('@echo off\r\n'
                    'title sc-bp-watcher-update\r\n'
                    'set /a versuche=0\r\n'
                    ':warten\r\n'
                    'set /a versuche+=1\r\n'
                    'if %%versuche%% gtr %d goto aufgeben\r\n'
                    'timeout /t 1 /nobreak >nul\r\n'
                    'move /y "%s" "%s" >nul 2>&1 || goto warten\r\n'
                    'start "" "%s"\r\n'
                    'del "%%~f0"\r\n'
                    'exit /b 0\r\n'
                    ':aufgeben\r\n'
                    'del "%%~f0"\r\n'
                    'exit /b 1\r\n'
                    % (VERSUCHE_TAUSCH, neue_datei, ziel, ziel))
        _TAUSCH_LAEUFT[0] = True
        subprocess.Popen(['cmd', '/c', skript],
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
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


# --------------------------------------------------- Eintrag in "Apps & Features"
# Der Installer trägt die Fassung dort ein. Ersetzt sich das Programm danach
# selbst, bleibt der Eintrag auf dem alten Stand stehen — Windows zeigt dann
# eine Nummer, die es gar nicht mehr gibt. Dazu: „Die Versionsanzeige
# wäre schon wichtig, da User ja sonst nicht sehen ob sie aktuell sind."
#
# Der Schlüssel liegt unter HKCU (der Installer schreibt in den Benutzerzweig),
# deshalb braucht das **keine Administratorrechte**.
INNO_KENNUNG = '{7C4B1E93-2A6F-4D58-B0E1-9F3A5C8D2461}_is1'


def neu_starten():
    """Das Programm durch die frisch eingespielte Fassung ersetzen.

    Nach einem Update läuft weiter die alte Fassung — der Prozess hält seine alte
    Inode. „Beim nächsten Start läuft die neue" stimmt zwar, heißt aber: selbst
    beenden und selbst wieder starten. Das nimmt dieser Weg ab.

    ⚠ Reihenfolge: erst den Einzelinstanz-Wächter schließen, dann starten. Sonst
    sieht die neue Fassung den belegten Port, hält sich für die zweite Instanz und
    beendet sich sofort wieder.
    """
    import subprocess
    from . import overlay as overlay_modul
    ziel = eigenes_appimage() or sys.executable
    if verpackung() == 'quellcode':
        return False
    try:
        overlay_modul.waechter_stoppen()

        # Wartet ein Hilfsskript darauf, die Datei zu tauschen, ist unser Teil
        # hier **erledigt** — es startet die neue Fassung selbst. Siehe die
        # Erklärung über `_TAUSCH_LAEUFT`.
        if _TAUSCH_LAEUFT[0]:
            return True

        umgebung = dict(os.environ)
        # Die Variablen des laufenden AppImage gehören der **alten** Fassung.
        for name in ('APPIMAGE', 'APPDIR', 'OWD', 'ARGV0'):
            umgebung.pop(name, None)

        # ⚠ Dasselbe gilt unter Windows für die Variablen von PyInstaller — und
        # dort ist es schlimmer, weil das Programm gar nicht mehr startet.
        #
        # Eine mit PyInstaller gebaute `.exe` entpackt sich beim Start nach
        # `%TEMP%\_MEIxxxxxx` und zeigt mit `TCL_LIBRARY` und `TK_LIBRARY`
        # dorthin. Erbt die neue Fassung diese Variablen, sucht sie ihre
        # Tcl-Dateien im Ordner der **alten** — den die alte beim Beenden
        # gerade aufräumt. Ergebnis, so beim Testen gemeldet (Haldjas,
        # 25.08.2026):
        #
        #     Failed to execute script 'sc_bp_watcher' due to unhandled
        #     exception: Can't find a usable init.tcl in the following
        #     directories: C:\Users\…\AppData\Local\Temp\_MEI000067b42…
        #
        # Und gleich hinterher die Gegenseite: „Failed to remove temporary
        # directory" — die alte Fassung kommt an ihren eigenen Ordner nicht
        # mehr heran, weil die neue darin liest.
        for name in ('_MEIPASS', '_MEIPASS2', 'TCL_LIBRARY', 'TK_LIBRARY',
                     'TIX_LIBRARY', 'MATPLOTLIBDATA'):
            umgebung.pop(name, None)
        subprocess.Popen([ziel], env=umgebung, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as ausnahme:
        fehler.merken('aktualisierung.neu_starten', ausnahme)
        return False


def windows_eintrag_pflegen(eigene_version):
    """Die angezeigte Fassung in Windows nachziehen. True, wenn geändert."""
    if not sys.platform.startswith('win') or not eigene_version:
        return False
    try:
        import winreg
        pfad = (r'Software\Microsoft\Windows\CurrentVersion\Uninstall\%s'
                % INNO_KENNUNG)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, pfad, 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as schluessel:
            try:
                steht_da = winreg.QueryValueEx(schluessel, 'DisplayVersion')[0]
            except FileNotFoundError:
                steht_da = ''
            if str(steht_da) == str(eigene_version):
                return False
            winreg.SetValueEx(schluessel, 'DisplayVersion', 0, winreg.REG_SZ,
                              str(eigene_version))
            return True
    except FileNotFoundError:
        return False          # nicht über den Installer installiert — in Ordnung
    except Exception as ausnahme:
        from . import fehler
        fehler.merken('aktualisierung.windows_eintrag', ausnahme)
        return False
