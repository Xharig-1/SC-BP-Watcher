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
Wo liegt was — je nach Betriebssystem.

Das ist die einzige Stelle im Programm, die Windows- und Linux-Pfade kennt.
Alles andere fragt hier nach und muss nicht wissen, auf welchem System es läuft.

Drei Sorten Pfade:

  1. **Eigene Dateien** (Einstellungen, Bestand, Lesestand)
     Windows:  %APPDATA%\\sc-bp-watcher\\
     Linux:    ~/.config/sc-bp-watcher/     (bzw. $XDG_CONFIG_HOME)

  2. **Star Citizen selbst** (Game.log und die Sicherungen)
     Windows:  C:\\Program Files\\Roberts Space Industries\\StarCitizen\\LIVE\\
     Linux:    im Wine-Präfix, z. B. ~/Games/star-citizen/drive_c/Program Files/…

  3. **SC Deutsch Launcher** (optional, nur wenn vorhanden)
     Er ist kein Muss — wenn er da ist, wird er weiter genutzt,
     weil er den vollständigen Bestand und einen gepflegten Katalog liefert.

**Wer die Sachen woanders liegen hat, trägt die Pfade selbst ein.** Dafür gibt es
`einstellungen.json` im eigenen Ordner:

    {
      "spiel_ordner":    "/mnt/spiele/StarCitizen/LIVE",
      "launcher_ordner": "D:\\SCDL\\blueprints"
    }

Die Datei wird angelegt, sobald das Spiel nicht gefunden wird — mit Kommentar
und leeren Feldern zum Ausfüllen. Ein leeres Feld heißt „bitte suchen".

Rangfolge, wenn mehrere Angaben da sind:

  1. Umgebungsvariable — `SC_BP_HOME`, `SC_INSTALL_DIR`, `SC_BP_LAUNCHER`
     (für einen einmaligen Sonderfall, ohne etwas zu ändern)
  2. `einstellungen.json` — der normale Weg für einen dauerhaft eigenen Pfad
  3. die Suche an den üblichen Stellen
"""
import glob
import json
import os
import re
import sys

WINDOWS = sys.platform.startswith('win')

# Spielkanäle in der Reihenfolge, in der gesucht wird. LIVE zuerst — wer PTU
# spielt, hat meist beides installiert, gemeint ist aber fast immer LIVE.
KANAELE = ('LIVE', 'PTU', 'EPTU', 'TECH-PREVIEW')

# Unterpfad ab dem Wurzelverzeichnis eines Laufwerks bis zum Spielkanal.
SC_UNTERPFAD = os.path.join('Roberts Space Industries', 'StarCitizen')


# ------------------------------------------------------------ 1. Eigene Dateien
# Wohin welche Datei gehört. Zweck: Wer den Ordner öffnet, soll sehen, was
# seins ist — Baupläne und Ausgaben getrennt vom technischen Kleinkram.
# Was hier nicht steht, landet in „Intern"; das sind Zwischenspeicher und
# Lesestände, die niemanden interessieren.
UNTERORDNER = {
    'bestand.json':      'Bauplaene',
    'bestand.bak.json':  'Bauplaene',
    'merkliste.json':    'Bauplaene',
    'watchlist.json':    'Bauplaene',
    'catalog-seen.json': 'Bauplaene',
    'bp-overrides.json': 'Bauplaene',
    'einstellungen.json': 'Einstellungen',
    'phrasen.json':       'Einstellungen',
    'gesehen.json':       'Einstellungen',
    'fehler.json':        'Diagnose',
    'bericht.txt':        'Diagnose',
}
ORDNERNAME = 'SC BP Watcher'
EINSTELLUNGEN = 'einstellungen.json'


def _dokumente():
    """Der Dokumente-Ordner des Nutzers — oder das Heimatverzeichnis."""
    heim = os.path.expanduser('~')
    if WINDOWS:
        # Der Ordner kann umbenannt oder verschoben sein; die Registry weiß es.
        try:
            import winreg
            schluessel = (r'Software\Microsoft\Windows\CurrentVersion'
                          r'\Explorer\Shell Folders')
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, schluessel) as k:
                wert = winreg.QueryValueEx(k, 'Personal')[0]
                if wert and os.path.isdir(os.path.expandvars(wert)):
                    return os.path.expandvars(wert)
        except Exception:
            pass
    else:
        # Unter Linux sagt es die XDG-Angabe; sie ist übersetzt („Dokumente“).
        try:
            konfig = os.path.join(os.environ.get('XDG_CONFIG_HOME')
                                  or os.path.join(heim, '.config'),
                                  'user-dirs.dirs')
            with open(konfig, encoding='utf-8') as f:
                for zeile in f:
                    if zeile.startswith('XDG_DOCUMENTS_DIR'):
                        wert = zeile.split('=', 1)[1].strip().strip('"')
                        wert = wert.replace('$HOME', heim)
                        if os.path.isdir(wert):
                            return wert
        except Exception:
            pass
    for name in ('Documents', 'Dokumente'):
        p = os.path.join(heim, name)
        if os.path.isdir(p):
            return p
    return heim


def alter_app_ordner():
    """Wo die Dateien bis v2.x lagen — Rückfall und Quelle für den Umzug."""
    if WINDOWS:
        return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')),
                            'sc-bp-watcher')
    basis = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(basis, 'sc-bp-watcher')


def _ablage_aus_datei():
    """Einen selbst gewählten Ablage-Ort lesen — **ohne** `einstellung()`.

    ⚠ Hier lauert eine Schleife: `einstellung()` liest ihre Datei über
    `app_datei()`, und das fragt wieder `app_ordner()`. Wer an dieser Stelle die
    normale Einstellungs-Funktion benutzt, baut eine Endlosrekursion — die
    obendrein unsichtbar bleibt, weil ringsherum `try/except` steht. Deshalb
    wird die Datei hier am Standardort direkt gelesen.
    """
    try:
        standard = os.path.join(_dokumente(), ORDNERNAME, 'Einstellungen',
                                EINSTELLUNGEN)
        if not os.path.isfile(standard):
            return None
        with open(standard, encoding='utf-8') as f:
            wert = json.load(f).get('ablage_ordner')
        return wert.strip() if isinstance(wert, str) and wert.strip() else None
    except Exception:
        return None


def app_ordner():
    """Ordner für unsere eigenen Dateien. Wird bei Bedarf angelegt.

    Seit v3.0.0 liegt er **sichtbar** unter Dokumente statt versteckt in
    `%APPDATA%` bzw. `~/.config` — dort sucht kein normaler Spieler, und seinen
    Bauplan-Bestand sollte er finden können. Ein eigener Ort geht weiterhin über
    `SC_BP_HOME` oder die Einstellung `ablage_ordner`.
    """
    eigen = os.environ.get('SC_BP_HOME') or _ablage_aus_datei()
    p = (os.path.expanduser(eigen) if eigen
         else os.path.join(_dokumente(), ORDNERNAME))
    try:
        os.makedirs(p, exist_ok=True)
    except OSError:
        pass
    return p


def app_datei(name):
    """Voller Pfad zu einer eigenen Datei, z. B. app_datei('bestand.json').

    Sortiert nach `UNTERORDNER` in Unterordner ein. Wer ein `SC_BP_HOME` gesetzt
    hat (Selbsttest, Sonderfälle), bekommt den flachen Ordner von früher — dort
    geht es um Wegwerf-Ordner, nicht um Übersicht.
    """
    basis = app_ordner()
    if os.environ.get('SC_BP_HOME'):
        return os.path.join(basis, name)
    unter = UNTERORDNER.get(name, 'Intern')
    ziel = os.path.join(basis, unter)
    try:
        os.makedirs(ziel, exist_ok=True)
    except OSError:
        return os.path.join(basis, name)
    return os.path.join(ziel, name)


def umzug_noetig():
    """Liegen im alten Ordner Dateien, die im neuen fehlen?"""
    alt = alter_app_ordner()
    if not os.path.isdir(alt) or os.environ.get('SC_BP_HOME'):
        return False
    try:
        vorhanden = [n for n in os.listdir(alt) if n.endswith(('.json', '.txt'))]
    except OSError:
        return False
    if not vorhanden:
        return False
    # Schon umgezogen? Dann liegt der Bestand am neuen Ort.
    return not os.path.exists(app_datei('bestand.json'))


def umziehen():
    """Die Dateien aus dem alten Ordner in den neuen **kopieren**.

    Kopieren, nicht verschieben: Geht beim Umzug etwas schief — Rechte, ein
    Virenscanner, ein abgebrochener Start — ist der mühsam gesammelte
    Bauplan-Bestand sonst weg. Der alte Ordner bleibt unangetastet liegen; er
    kostet ein paar Kilobyte und ist der Rückweg.

    Gibt die Zahl der kopierten Dateien zurück.
    """
    import shutil
    alt = alter_app_ordner()
    kopiert = 0
    try:
        namen = sorted(os.listdir(alt))
    except OSError:
        return 0
    for name in namen:
        quelle = os.path.join(alt, name)
        if not os.path.isfile(quelle):
            continue
        ziel = app_datei(name)
        if os.path.exists(ziel):
            continue                     # nichts überschreiben
        try:
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            shutil.copy2(quelle, ziel)
            kopiert += 1
        except OSError:
            pass
    return kopiert


# ------------------------------------------------------- Selbst gesetzte Pfade

def gesuchte_spielorte(hoechstens=6):
    """Die Orte, an denen tatsächlich nach Star Citizen gesucht wird.

    Wird dem Nutzer angezeigt, wenn nichts gefunden wurde. Ohne diese Angabe
    weiß er nicht, wonach er suchen soll — und ein Pfad, den er selbst eintragen
    soll, ist ohne Vorbild schwer zu erraten. Vorhandene Ordner kommen zuerst:
    Wer seine Installation dort halb wiederfindet, sieht sofort, wie der Rest
    aussehen muss."""
    kandidaten = []
    for wurzel in _spiel_wurzeln():
        p = os.path.join(wurzel, SC_UNTERPFAD, KANAELE[0])
        if p not in kandidaten:
            kandidaten.append(p)
    # Wenn gar nichts zusammenkommt, sind auf diesem Rechner weder Wine-Präfixe
    # noch Programmordner da — und ausgerechnet dann braucht der Nutzer das
    # Vorbild am dringendsten. Also die typischen Orte zeigen, auch wenn es sie
    # hier nicht gibt.
    if not kandidaten:
        heim = os.path.expanduser('~')
        if WINDOWS:
            kandidaten = [os.path.join('C:\\Program Files', SC_UNTERPFAD,
                                       KANAELE[0])]
        else:
            for praefix in (os.path.join(heim, 'Games', 'star-citizen'),
                            os.path.join(heim, '.wine')):
                kandidaten.append(os.path.join(praefix, 'drive_c', 'Program Files',
                                               SC_UNTERPFAD, KANAELE[0]))
            kandidaten.append(os.path.join(
                heim, '.local', 'share', 'lutris', 'prefixes', '<Name>', 'drive_c',
                'Program Files', SC_UNTERPFAD, KANAELE[0]))
    # existierende zuerst, Reihenfolge sonst beibehalten
    da = [p for p in kandidaten if os.path.isdir(os.path.dirname(p))]
    rest = [p for p in kandidaten if p not in da]
    return (da + rest)[:hoechstens]


def gesuchte_launcherorte(hoechstens=3):
    """Dasselbe für den Blueprint-Ordner des SC Deutsch Launchers."""
    if WINDOWS:
        return [os.path.join(os.environ.get('APPDATA', '%APPDATA%'),
                             'sc-deutsch-launcher', 'blueprints')]
    orte = list(_windows_launcher())
    for praefix in _wine_praefixe()[:hoechstens]:
        orte.append(os.path.join(praefix, 'drive_c', 'users', '<Benutzer>',
                                 'AppData', 'Roaming', 'sc-deutsch-launcher',
                                 'blueprints'))
    return orte[:hoechstens]


def _vorlage():
    """Der Inhalt der Einstellungsdatei — mit den echten Suchorten dieses Rechners.

    Die Hinweiszeilen stehen bewusst **direkt unter** dem jeweiligen Feld: In
    einer JSON-Datei gibt es keine ausgegraute Beschriftung, das Nächstliegende
    ist ein Feld daneben, das man beim Ausfüllen zwangsläufig liest. Sie werden
    nicht ausgewertet — was drinsteht, ändert nichts."""
    return {
        '_hinweis': 'Eigene Pfade eintragen, wenn Star Citizen oder der '
                    'SC Deutsch Launcher nicht an den ueblichen Stellen liegen. '
                    'Leeres Feld = automatisch suchen. Nach dem Aendern den '
                    'Watcher neu starten. Zeilen mit _ sind nur Erklaerung.',
        'spiel_ordner': '',
        '_spiel_ordner_gemeint_ist': 'Der Ordner, in dem die Game.log liegt — '
                                     'meist "LIVE".',
        '_spiel_ordner_gesucht_wird_hier': gesuchte_spielorte(),
        'sprache': 'auto',
        '_sprache_moeglich': 'auto (Systemsprache), de, en',
        'pruefintervall_sekunden': 3,
        '_pruefintervall_gemeint_ist': 'Wie oft die Game.log angesehen wird. '
                                       'Erlaubt 1 bis 60.',
        'signalton': True,
        '_signalton_gemeint_ist': 'Kurzer Ton, wenn ein Bauplan erscheint.',
        'deckkraft_prozent': 93,
        '_deckkraft_gemeint_ist': 'Wie undurchsichtig das Fenster ist. 100 = '
                                  'blickdicht, 30 = stark durchscheinend. '
                                  'Erlaubt 30 bis 100.',
        'launcher_ordner': '',
        '_launcher_ordner_gemeint_ist': 'Optional. Der Ordner "blueprints" des '
                                        'SC Deutsch Launchers. Ohne ihn laeuft '
                                        'der Watcher trotzdem.',
        '_launcher_ordner_gesucht_wird_hier': gesuchte_launcherorte(),
    }


def einstellungen():
    """Die selbst eingetragenen Pfade. Fehlt die Datei, ist sie leer."""
    try:
        with open(app_datei(EINSTELLUNGEN), encoding='utf-8') as f:
            daten = json.load(f)
        return daten if isinstance(daten, dict) else {}
    except Exception:
        return {}


def einstellung(name):
    """Ein einzelner selbst gesetzter Pfad — oder None, wenn nichts eingetragen ist."""
    wert = (einstellungen().get(name) or '').strip()
    return os.path.expanduser(wert) if wert else None


def einstellung_setzen(name, wert):
    """Einen Pfad dauerhaft merken — ohne die Erklärzeilen zu verlieren.

    Gelesen wird die vorhandene Datei (oder die Vorlage), geändert nur das eine
    Feld. So bleiben die Hinweise mit den Suchorten stehen, auch wenn das
    Programm die Datei schreibt."""
    daten = einstellungen() or _vorlage()
    daten[name] = wert
    ziel = app_datei(EINSTELLUNGEN)
    temp = ziel + '.tmp'
    try:
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(daten, f, ensure_ascii=False, indent=2)
        os.replace(temp, ziel)
        return True
    except OSError:
        return False


def einstellung_zahl(name, standard, kleinstes=None, groesstes=None):
    """Eine Zahl aus den Einstellungen, mit Grenzen.

    Unsinnige Werte werden auf den erlaubten Bereich gezogen statt abgelehnt:
    Wer 0 einträgt, meint „so oft wie möglich" und soll kein Programm bekommen,
    das die Platte durchdreht — aber auch keine Fehlermeldung."""
    wert = einstellungen().get(name)
    try:
        zahl = int(wert)
    except (TypeError, ValueError):
        return standard
    if kleinstes is not None:
        zahl = max(kleinstes, zahl)
    if groesstes is not None:
        zahl = min(groesstes, zahl)
    return zahl


def einstellung_wahrheit(name, standard):
    """Ein Ja/Nein aus den Einstellungen. Fehlt es, gilt der Standard."""
    wert = einstellungen().get(name)
    if isinstance(wert, bool):
        return wert
    if isinstance(wert, str):
        return wert.strip().lower() in ('ja', 'yes', 'true', '1', 'an', 'on')
    return standard


def vorlage_anlegen():
    """Legt `einstellungen.json` zum Ausfüllen an, falls sie noch fehlt.

    Passiert genau dann, wenn das Spiel nicht gefunden wurde: Dann braucht der
    Nutzer die Datei, und sie soll schon dastehen, statt dass er sie nach
    Anleitung selbst erzeugen muss."""
    ziel = app_datei(EINSTELLUNGEN)
    if os.path.exists(ziel):
        return ziel
    try:
        with open(ziel, 'w', encoding='utf-8') as f:
            json.dump(_vorlage(), f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return ziel


# --------------------------------------------------------- 2. Star Citizen selbst
def _wine_praefixe():
    """Mögliche Wine-Präfixe unter Linux — die Orte, an denen die verbreiteten
    Installationswege (lug-helper, Lutris, Bottles, Heroic) landen. Reihenfolge
    ist Absicht: der lug-helper-Standard zuerst, er ist unter Linux der übliche Weg."""
    heim = os.path.expanduser('~')
    fest = [
        os.path.join(heim, 'Games', 'star-citizen'),
        os.path.join(heim, '.wine'),
        os.path.join(heim, 'Games', 'star-citizen-live'),
    ]
    muster = [
        os.path.join(heim, '.local', 'share', 'lutris', 'prefixes', '*'),
        os.path.join(heim, '.var', 'app', 'net.lutris.Lutris', 'data', 'lutris',
                     'prefixes', '*'),
        os.path.join(heim, '.local', 'share', 'bottles', 'bottles', '*'),
        os.path.join(heim, 'Games', '*'),
    ]
    gefunden = list(fest)
    for m in muster:
        gefunden.extend(sorted(glob.glob(m)))
    # Doppelte raus, Reihenfolge behalten
    gesehen, ergebnis = set(), []
    for p in gefunden:
        if p not in gesehen:
            gesehen.add(p)
            ergebnis.append(p)
    return ergebnis


def _spiel_wurzeln():
    """Verzeichnisse, unter denen `Roberts Space Industries\\StarCitizen` liegen kann."""
    if WINDOWS:
        wurzeln = []
        for laufwerk in 'CDEFGH':
            for programme in ('Program Files', 'Program Files (x86)'):
                wurzeln.append('%s:\\%s' % (laufwerk, programme))
        return wurzeln
    wurzeln = []
    for praefix in _wine_praefixe():
        c = os.path.join(praefix, 'drive_c')
        if not os.path.isdir(c):
            continue
        wurzeln.append(os.path.join(c, 'Program Files'))
        wurzeln.append(os.path.join(c, 'Program Files (x86)'))
        wurzeln.append(c)                      # manche installieren direkt nach C:\
    return wurzeln


def spiel_ordner():
    """Ordner des Spielkanals (enthält die Game.log) oder None.

    Erst die Umgebungsvariable, dann die üblichen Orte. Es wird nur nachgesehen,
    ob die Game.log dort liegt — geraten wird nicht."""
    for eigen in (os.environ.get('SC_INSTALL_DIR'), einstellung('spiel_ordner')):
        if not eigen:
            continue
        eigen = os.path.expanduser(eigen)
        if os.path.isfile(os.path.join(eigen, 'Game.log')):
            return eigen
        for k in KANAELE:                      # auch der Ordner darüber ist erlaubt
            p = os.path.join(eigen, k)
            if os.path.isfile(os.path.join(p, 'Game.log')):
                return p
    for wurzel in _spiel_wurzeln():
        basis = os.path.join(wurzel, SC_UNTERPFAD)
        if not os.path.isdir(basis):
            continue
        for k in KANAELE:
            p = os.path.join(basis, k)
            if os.path.isfile(os.path.join(p, 'Game.log')):
                return p
    return None


def spielordner_deuten(gewaehlt):
    """Aus einem vom Nutzer gewählten Ordner den tatsächlichen Spielordner machen.

    Nimmt ihm die Sucherei ab: Er darf den LIVE-Ordner treffen, den darüber
    (`StarCitizen`), den Programme-Ordner oder gleich das ganze Wine-Präfix —
    solange irgendwo darunter eine `Game.log` liegt, wird sie gefunden.
    Gibt den Ordner mit der Game.log zurück oder None."""
    if not gewaehlt:
        return None
    gewaehlt = os.path.expanduser(gewaehlt.strip().rstrip(os.sep)) or os.sep
    if os.path.isfile(gewaehlt):                 # jemand hat die Game.log selbst gewählt
        gewaehlt = os.path.dirname(gewaehlt)
    if os.path.isfile(os.path.join(gewaehlt, 'Game.log')):
        return gewaehlt
    # Eine Ebene tiefer: der Kanal (LIVE/PTU/…)
    for k in KANAELE:
        p = os.path.join(gewaehlt, k)
        if os.path.isfile(os.path.join(p, 'Game.log')):
            return p
    # Tiefer suchen, aber begrenzt — ein ganzes Laufwerk durchzugehen wäre
    # unhöflich. Vier Ebenen decken Wine-Präfix -> drive_c -> Programme ->
    # Roberts Space Industries -> StarCitizen -> LIVE ab.
    wurzel_tiefe = gewaehlt.rstrip(os.sep).count(os.sep)
    for basis, ordner, dateien in os.walk(gewaehlt):
        if basis.count(os.sep) - wurzel_tiefe > 5:
            ordner[:] = []
            continue
        if 'Game.log' in dateien:
            return basis
    return None


def game_log(ordner=None):
    """Pfad zur aktiven Game.log oder None."""
    ordner = ordner or spiel_ordner()
    if not ordner:
        return None
    p = os.path.join(ordner, 'Game.log')
    return p if os.path.isfile(p) else None


def log_sicherungen(ordner=None):
    """Die aufgehobenen Logs vergangener Sitzungen, älteste zuerst.

    Star Citizen legt bei jedem Spielstart die vorige Game.log unter
    `logbackups/` ab. Daraus lässt sich nachlesen, was ohne laufenden
    Watcher freigeschaltet wurde."""
    ordner = ordner or spiel_ordner()
    if not ordner:
        return []
    # Bewusst alles nehmen, was dort liegt: Star Citizen hat die Benennung der
    # Sicherungen über die Jahre mehrfach geändert (mal `Game.log.<Datum>`, mal
    # mit Endung dahinter). Ein Muster auf `*.log` verpasst dann die Hälfte.
    # Ausgenommen sind nur Dinge, die sicher kein Text sind.
    ausser = ('.zip', '.7z', '.gz', '.rar', '.dmp', '.mdmp', '.png', '.jpg')
    treffer = []
    for p in glob.glob(os.path.join(ordner, 'logbackups', '*')):
        if os.path.isfile(p) and not p.lower().endswith(ausser):
            treffer.append(p)
    return sorted(treffer, key=lambda p: (_mtime(p), p))


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return 0.0


def lokalisierung_ordner(ordner=None):
    """`data/Localization` im Spielordner — dort liegen die entpackten `global.ini`,
    sofern welche vorhanden sind (der SC Deutsch Launcher legt die deutsche dort ab)."""
    ordner = ordner or spiel_ordner()
    if not ordner:
        return None
    p = os.path.join(ordner, 'data', 'Localization')
    return p if os.path.isdir(p) else None


# ---------------------------------------------------- 3. SC Deutsch Launcher (optional)
def launcher_ordner():
    """Blueprint-Ordner des SC Deutsch Launchers oder None.

    Unter Windows liegt er in %APPDATA%. Unter Linux nur dann, wenn jemand den
    Launcher unter Wine betreibt — dann steckt dasselbe AppData im Wine-Präfix."""
    # Eine **gesetzte** Angabe gilt allein — auch wenn der Ordner dort nicht
    # existiert. Wer einen Pfad einträgt, will keine Suche woanders; sonst
    # nimmt das Programm klammheimlich einen anderen Launcher-Stand her als den
    # angegebenen. (Fiel im Selbsttest auf: Der baut eine Installation ohne
    # Launcher nach, bekam aber den echten von der Windows-Platte untergeschoben.)
    for eigen in (os.environ.get('SC_BP_LAUNCHER'), einstellung('launcher_ordner')):
        if eigen is not None and eigen != '':
            eigen = os.path.expanduser(eigen)
            return eigen if os.path.isdir(eigen) else None
    if os.environ.get('SC_BP_LAUNCHER') == '':
        return None                    # ausdrücklich abgeschaltet
    if WINDOWS:
        p = os.path.join(os.environ.get('APPDATA', ''), 'sc-deutsch-launcher',
                         'blueprints')
        return p if os.path.isdir(p) else None
    for praefix in _wine_praefixe():
        muster = os.path.join(praefix, 'drive_c', 'users', '*', 'AppData',
                              'Roaming', 'sc-deutsch-launcher', 'blueprints')
        for p in sorted(glob.glob(muster)):
            if os.path.isdir(p):
                return p
    # Dual-Boot: Der Launcher läuft unter Windows, seine Daten liegen auf der
    # Windows-Platte — die unter Linux meist eingehängt ist. Ohne diesen Blick
    # steht ein umgestiegener Spieler ohne seinen alten Bauplan-Stand da,
    # obwohl der zwei Ordner weiter vollständig vorliegt. Genau so passiert.
    for p in _windows_launcher():
        return p
    return None


def _windows_launcher():
    """Launcher-Daten auf einer eingehängten Windows-Platte."""
    heim = os.path.expanduser('~')
    orte = ['/run/media/*/*', '/media/*/*', '/mnt/*',
            os.path.join(heim, '.local', 'share', '*')]
    for ort in orte:
        muster = os.path.join(ort, 'Users', '*', 'AppData', 'Roaming',
                              'sc-deutsch-launcher', 'blueprints')
        for p in sorted(glob.glob(muster)):
            if os.path.isdir(p):
                yield p


def launcher_datei(name, ordner=None):
    """Pfad zu einer Launcher-Datei, auch wenn es den Launcher nicht gibt.

    Gibt immer einen Pfad zurück (nie None), damit die aufrufende Stelle wie
    bisher einfach versuchen kann, ihn zu öffnen. Ohne Launcher zeigt er ins
    Leere und das Öffnen scheitert — genau das ist gewollt."""
    ordner = ordner if ordner is not None else (launcher_ordner() or '')
    return os.path.join(ordner, name)


# ------------------------------------------------------------------ Übersicht
def kuerzen(text):
    """Persönliches aus einem Text nehmen — für Fehlerprotokoll und Bericht.

    Pfade verraten den Benutzernamen (`C:\\Users\\Spieler\\…`,
    `/home/spieler/…`), und genau solche Texte landen in einem **öffentlichen**
    Issue. Ersetzt werden das Heimatverzeichnis und danach jedes weitere
    Vorkommen des Benutzernamens.

    Lieber einmal zu viel ersetzt als ein Name zu viel im Netz.
    """
    try:
        text = str(text)
        heim = os.path.expanduser('~')
        name = os.path.basename(heim.rstrip('\\/'))

        for was in (heim, heim.replace('\\', '/'), heim.replace('/', '\\')):
            if was and len(was) > 3:
                text = text.replace(was, '<heim>')

        if name and len(name) > 2:
            text = re.sub(re.escape(name), '<benutzer>', text, flags=re.I)
        return text
    except Exception:
        return str(text)


def uebersicht():
    """Was wurde gefunden — für Statusanzeige und Fehlersuche."""
    spiel = spiel_ordner()
    return {
        'system': 'Windows' if WINDOWS else sys.platform,
        'app_ordner': app_ordner(),
        'spiel_ordner': spiel,
        'game_log': game_log(spiel),
        'sicherungen': len(log_sicherungen(spiel)),
        'launcher': launcher_ordner(),
        'einstellungen': app_datei(EINSTELLUNGEN),
        'selbst_gesetzt': {k: v for k, v in einstellungen().items()
                           if not k.startswith('_') and v},
    }


if __name__ == '__main__':
    for k, v in uebersicht().items():
        print('%-14s %s' % (k, v))
