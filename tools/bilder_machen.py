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
Die Bildschirmfotos für die Anleitung machen — **ohne** den Bildschirm zu belegen.

## Warum es dieses Werkzeug gibt

Die Bilder in der Anleitung entstanden bisher von Hand: Fenster aufziehen, Seite
anklicken, Ausschnitt fotografieren, zuschneiden, benennen — je Bild ein
Arbeitsgang, und das siebzehnmal. Entsprechend sahen sie aus: Am 31.08.2026
waren **elf von sechzehn** Bildern vom 27.08. und zeigten eine Oberfläche, die es
so nicht mehr gibt (die Seitenleiste hatte damals keine Gruppen, Werkstatt und
Handel gab es noch gar nicht). Dazu zwei verschiedene Auflösungen im selben
Dokument — 2282×1666 neben 1180×820.

Was von Hand gemacht wird, verrottet. Also macht es jetzt ein Skript.

## ⚠⚠ Es reisst den Bildschirm NICHT an sich

Das ist die eigentliche Schwierigkeit. Ein Bildschirmfoto braucht normalerweise
ein sichtbares Fenster im Vordergrund — und genau das ist hier verboten: Wer
gerade Star Citizen fliegt, landet sonst mitten im Kampf auf dem Desktop (siehe
`tools/unsichtbar.py`, am 29.08.2026 rund zwanzig Mal passiert).

Der Ausweg ist `PrintWindow` aus der Windows-API: Es lässt ein Fenster **sich
selbst neu zeichnen**, in einen Speicherbereich statt auf den Schirm. Mit dem
Kennzeichen `PW_RENDERFULLCONTENT` (2) gilt das auch für Fenster, die niemand
sieht. Das Fenster wird deshalb weit ausserhalb des sichtbaren Bereichs
aufgebaut und nie nach vorn geholt.

⚠ **`SetProcessDpiAwareness` muss VOR dem ersten Tk-Fenster stehen.** Ohne das
rechnet Windows die Angaben um, und man greift am Fenster vorbei — bei 125 %
Skalierung fehlt rechts und unten ein Fünftel. Das hat schon einmal fünf Anläufe
gekostet.

## Womit gearbeitet wird

Mit einer **Kopie** des echten Datenstands, nicht mit ihm selbst. Die Bilder
sollen gefüllte Listen zeigen — ein leeres Lager erklärt niemandem, wozu die
Seite gut ist. Aber ein Werkzeug, das für ein Bild den eigenen Bestand anfasst,
ist ein Werkzeug zu viel: Beim Start schreibt der Watcher Lesestand,
Katalog-Zwischenspeicher und Einstellungen.

## Aufruf

    python tools/bilder_machen.py             # alle Seiten, deutsch
    python tools/bilder_machen.py --en        # alle Seiten, englisch
    python tools/bilder_machen.py liste lager # nur diese beiden

Die Bilder landen in `assets/` unter `screenshot-<seite>.png`; auf Englisch
hängt `-en` an. Vorhandene werden überschrieben.
"""
import ctypes
import os
import shutil
import sys
import tempfile
import time

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

# ⚠⚠ **Vor jedem Tk-Import und vor jedem Fenster.** Siehe oben.
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Fenstergrösse der Bilder. Dieselbe für **alle** — zwei Auflösungen im selben
# Dokument sehen nach Zufall aus, und die Anleitung ist die Visitenkarte.
#
# ⚠ **Bewusst über der Mindestbreite (1160).** Bei genau der Mindestbreite
# wächst die Seitenleiste beim Seitenwechsel noch einmal nach, und der Abgriff
# erwischt den Moment dazwischen: Auf dem Bild fehlten rechts der Knopf „In die
# Ablage" und ein Stück der Kopfzeile. Gemessen ragt bei 1160 zwar nichts über
# den Rand (siehe die Messung vom 31.08.2026) — aber ein Bild, das in dieser
# Sekunde entsteht, zeigt es trotzdem. Mit Luft passiert das nicht, und die
# Bilder zeigen nebenbei mehr Inhalt.
BREITE, HOEHE = 1400, 860

# Weit weg vom sichtbaren Bereich. Nicht „hinter" anderen Fenstern: dort würde
# jemand es beim Umschalten sehen.
WEIT_WEG = (9000, 9000)

# Welche Seite unter welchem Namen abgelegt wird. Die Kennungen sind die aus
# `scbp/seiten.py`.
SEITEN = {
    'liste':        'screenshot-liste',
    'fortschritt':  'screenshot-fortschritt',
    'herstellung':  'screenshot-herstellung',
    'bergbau':      'screenshot-bergbau',
    'lager':        'screenshot-lager',
    'handelslager': 'screenshot-handelslager',
    'verkauf':      'screenshot-verkauf',
    'bestand':      'screenshot-bestand',
    'allgemein':    'screenshot-allgemein',
    'anzeige':      'screenshot-anzeige',
    'spiel':        'screenshot-auftragstexte',
    'serverstatus': 'screenshot-serverstatus',
    'wasistneu':    'screenshot-wasistneu',
    'ueber':        'screenshot-ueber',
    'danke':        'screenshot-danke',
}


def io_lesen(pfad):
    with open(pfad, encoding='utf-8') as f:
        return f.read()


def _version():
    """Die echte Versionsnummer — sie steht auf dem Bild neben dem Namen.

    Gelesen statt importiert: `sc_bp_watcher` zu importieren zoege den ganzen
    Watcher samt Ueberwachungs-Thread hoch.
    """
    import re
    treffer = re.search(r"__version__ = '([^']+)'",
                        io_lesen(os.path.join(HIER, 'sc_bp_watcher.py')))
    return treffer.group(1) if treffer else ''


def datenstand_kopieren():
    """Eine Wegwerf-Kopie des echten Datenstands anlegen und `SC_BP_HOME` setzen.

    Gibt den Pfad zurück. Der echte Ordner wird **nur gelesen**.
    """
    from scbp import pfade
    # ⚠⚠ **`app_ordner()`, nicht `app_datei('')`.** Der zweite Weg landet im
    # Unterordner „Intern" — dort liegen Zwischenspeicher, aber weder Bestand
    # (`Bauplaene/`) noch Einstellungen (`Einstellungen/`). Die ersten Bilder
    # zeigten deshalb „0 von 738 (0 %)": ein Werkzeug, das aussieht, als könne
    # es nichts.
    #
    # ⚠ Mit `SC_BP_HOME` legt der Watcher alles **flach** ab (siehe
    # `app_datei`) — die Unterordner der Vorlage werden deshalb eingeebnet.
    quelle = pfade.app_ordner()
    ziel = tempfile.mkdtemp(prefix='sc-bp-bilder-')
    for wurzel_, _unter, dateien in os.walk(quelle):
        for name in dateien:
            if not name.endswith(('.json', '.txt')):
                continue
            try:
                shutil.copy2(os.path.join(wurzel_, name),
                             os.path.join(ziel, name))
            except Exception:
                pass
    return ziel


def marken_loeschen():
    """Die „Neu"-Marken in der Wegwerf-Kopie auf „gesehen" setzen.

    ⚠ **Sie gehören nicht in die Anleitung.** Eine Marke ist eine Nachricht an
    *einen* Nutzer („diesen Bereich gab es beim letzten Mal noch nicht") — auf
    einem Bild in der Anleitung behauptet sie dasselbe gegenüber jedem Leser,
    für immer. Ausserdem verbreitern sie die Seitenleiste, wodurch die Bilder
    unterschiedlich breit würden.
    """
    import json
    from scbp import neuheiten
    stand = {'bereiche': {b: '999.0.0' for b in neuheiten.NEU_SEIT},
             'zuletzt': '999.0.0'}
    ziel = os.path.join(os.environ['SC_BP_HOME'], neuheiten.DATEI)
    try:
        with open(ziel, 'w', encoding='utf-8') as f:
            json.dump(stand, f)
    except Exception as ausnahme:
        print('  Hinweis: Marken liessen sich nicht abschalten (%s)' % ausnahme)


def fenster_richten(fenster, wurzel):
    """Fenstergrösse setzen und wirklich fertig zeichnen lassen.

    ⚠⚠ **Nach jedem Seitenwechsel nötig, nicht nur einmal am Anfang.** Die
    Seitenleiste misst sich je Seite neu, und mit ihr wächst `minsize` — das
    Fenster wird dabei breiter, ohne dass der Inhalt schon neu gezeichnet
    wäre. Der erste Versuch griff genau in diesem Moment ab: Rechts standen
    schwarze Blöcke, wo der Inhalt hätte sein sollen.

    Deshalb wird die Grösse **nach** dem Seitenwechsel gesetzt (mindestens so
    breit, wie `minsize` verlangt) und danach mehrfach durchgezeichnet.
    """
    breite = hoehe = 0
    # ⚠⚠ **Mehrere Runden, bis sich nichts mehr rührt.** Einmal richten reicht
    # nicht: Die Seitenleiste misst sich nach dem Seitenwechsel noch einmal
    # nach und schiebt `minsize` dabei hoch — das Fenster wird also NACH dem
    # Richten breiter, und gezeichnet ist der Inhalt noch in der alten Breite.
    # Genau so entstand das erste Listenbild, bei dem rechts „In die Ablage"
    # und „Was ist neu" abgeschnitten waren.
    for _runde in range(4):
        try:
            min_b, min_h = (int(x) for x in fenster.root.minsize())
        except Exception:
            min_b, min_h = BREITE, HOEHE
        neu_b, neu_h = max(BREITE, min_b), max(HOEHE, min_h)
        if (neu_b, neu_h) == (breite, hoehe):
            break
        breite, hoehe = neu_b, neu_h
        fenster.root.geometry('%dx%d+%d+%d'
                              % (breite, hoehe, WEIT_WEG[0], WEIT_WEG[1]))
        for _ in range(14):
            wurzel.update()
            wurzel.update_idletasks()
    return breite, hoehe


def puffer_leeren(fenster, wurzel):
    """Das Fenster zu einem vollstaendigen Neuaufbau zwingen.

    ⚠⚠ **Ein `update()` genuegt nicht.** Tk tauscht die Seiten mit
    `pack_forget`/`pack`; das Fenster ausserhalb des Bildschirms bekommt
    danach keinen Zeichen-Auftrag von Windows, und `PrintWindow` gibt heraus,
    was zuletzt im Puffer stand — die alte Seite also.

    Der Griff, der wirklich hilft: die Fenstergroesse kurz veraendern und
    zuruecksetzen. Das erzeugt echte `<Configure>`-Ereignisse fuer **alle**
    Kinder, und Tk baut die Flaeche neu auf.
    """
    breite, hoehe = fenster.root.winfo_width(), fenster.root.winfo_height()
    for masse in ((breite - 40, hoehe - 30), (breite, hoehe)):
        fenster.root.geometry('%dx%d+%d+%d'
                              % (masse[0], masse[1], WEIT_WEG[0], WEIT_WEG[1]))
        for _ in range(8):
            wurzel.update()
            wurzel.update_idletasks()
    neu_zeichnen(fenster.root)
    for _ in range(6):
        wurzel.update()
        wurzel.update_idletasks()


def neu_zeichnen(fenster):
    """Windows anweisen, das Fenster samt aller Kinder frisch zu zeichnen."""
    if sys.platform != 'win32':
        return
    try:
        hwnd = int(fenster.wm_frame(), 16)
        ctypes.windll.user32.RedrawWindow(
            hwnd, None, None, 0x0001 | 0x0004 | 0x0080 | 0x0100 | 0x0400)
    except Exception:
        pass


def abgreifen(fenster, ziel):
    """Das Fenster in eine PNG-Datei zeichnen lassen. Gibt True bei Erfolg.

    ⚠ Abgegriffen wird **das Fenster**, nicht ein Bildschirmausschnitt — sonst
    landet dort, was gerade davor liegt.
    """
    from PIL import Image

    hwnd = int(fenster.wm_frame(), 16) if sys.platform == 'win32' else None
    if hwnd is None:
        raise RuntimeError('Dieses Werkzeug braucht Windows (PrintWindow).')

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32

    class RECT(ctypes.Structure):
        _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                    ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    breite, hoehe = rect.right - rect.left, rect.bottom - rect.top
    if breite < 100 or hoehe < 100:
        return False

    # ⚠⚠ **Das Fenster zum vollstaendigen Neuzeichnen zwingen.** Ein Fenster
    # ausserhalb des Bildschirms bekommt von Windows keine Zeichen-Auftraege
    # mehr; `PrintWindow` liefert dann, was zuletzt im Puffer stand. Beim
    # Handelslager lagen dadurch **vier Seiten uebereinander** — Liste, Lager,
    # Handelslager und Verkauf gleichzeitig, unlesbar.
    #
    # RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW | RDW_FRAME
    user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0004 | 0x0080 | 0x0100 | 0x0400)

    fenster_dc = user32.GetWindowDC(hwnd)
    speicher_dc = gdi32.CreateCompatibleDC(fenster_dc)
    bitmap = gdi32.CreateCompatibleBitmap(fenster_dc, breite, hoehe)
    gdi32.SelectObject(speicher_dc, bitmap)

    # 2 = PW_RENDERFULLCONTENT — lässt auch ein unsichtbares Fenster zeichnen.
    geglueckt = user32.PrintWindow(hwnd, speicher_dc, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_long),
                    ('biHeight', ctypes.c_long), ('biPlanes', ctypes.c_uint16),
                    ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
                    ('biSizeImage', ctypes.c_uint32), ('biXPelsPerMeter', ctypes.c_long),
                    ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', ctypes.c_uint32),
                    ('biClrImportant', ctypes.c_uint32)]

    kopf = BITMAPINFOHEADER()
    kopf.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    kopf.biWidth, kopf.biHeight = breite, -hoehe      # negativ = von oben nach unten
    kopf.biPlanes, kopf.biBitCount = 1, 32
    kopf.biCompression = 0

    puffer = ctypes.create_string_buffer(breite * hoehe * 4)
    gdi32.GetDIBits(speicher_dc, bitmap, 0, hoehe, puffer,
                    ctypes.byref(kopf), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(speicher_dc)
    user32.ReleaseDC(hwnd, fenster_dc)

    bild = Image.frombuffer('RGB', (breite, hoehe), puffer, 'raw', 'BGRX', 0, 1)
    # ⚠ Ein völlig schwarzes Bild heisst: das Fenster hat nicht gezeichnet.
    # Lieber nichts ablegen als ein schwarzes Rechteck in die Anleitung.
    if not bild.getbbox():
        return False
    bild.save(ziel)
    return bool(geglueckt)


def main():
    argumente = [a for a in sys.argv[1:] if not a.startswith('--')]
    englisch = '--en' in sys.argv
    gewuenscht = argumente or list(SEITEN)

    unbekannt = [s for s in gewuenscht if s not in SEITEN]
    if unbekannt:
        print('Unbekannte Seite(n): %s' % ', '.join(unbekannt))
        print('Bekannt sind: %s' % ', '.join(SEITEN))
        return 2

    os.environ['SC_BP_HOME'] = datenstand_kopieren()
    os.environ['SC_BP_NO_NET'] = '1'
    marken_loeschen()

    import tkinter as tk
    from scbp import sprache
    from scbp.hauptfenster import Hauptfenster

    sprache.setzen('en' if englisch else 'de')

    wurzel = tk.Tk()
    wurzel.withdraw()

    # ⚠⚠ **EIN Fenster fuer alle Seiten — nicht je Seite ein frisches.**
    # Beides wurde am 31.08.2026 durchprobiert:
    #
    # | Weg | was dabei herauskam |
    # |---|---|
    # | ein Fenster, Seiten nacheinander | saubere Flaechen, aber die alte Seite blieb im Puffer stehen — auf einem Bild lagen **vier Seiten uebereinander** |
    # | je Seite ein frisches Fenster | keine Ueberlagerung mehr, dafuer **halb gezeichnete Flaechen**: helle Rechtecke der Bedienelemente auf ungezeichnetem Grund |
    #
    # Ein frisch erzeugtes Fenster ausserhalb des Bildschirms zeichnet seine
    # Flaechen nie fertig; eines, das schon ein paar Runden gelaufen ist, tut
    # es. Also: ein Fenster, und der Puffer wird vor jedem Bild durch
    # `puffer_leeren` wirklich geraeumt.
    ziel_ordner = os.path.join(HIER, 'assets')
    gemacht, misslungen = [], []

    for kennung in gewuenscht:
        name = SEITEN[kennung] + ('-en' if englisch else '') + '.png'
        ziel = os.path.join(ziel_ordner, name)
        fenster = None
        try:
            # Frisches Fenster **und** Puffer raeumen — erst beides zusammen
            # liefert brauchbare Bilder (siehe die Tabelle oben).
            fenster = Hauptfenster(wurzel, version=_version())
            fenster_richten(fenster, wurzel)
            fenster.oeffnen(kennung)
            for _ in range(12):
                wurzel.update()
                wurzel.update_idletasks()
            fenster_richten(fenster, wurzel)
            puffer_leeren(fenster, wurzel)
            # Die Seiten holen ihre Daten ueber `after`-Rueckrufe nach — wer zu
            # frueh abgreift, fotografiert eine halbfertige Seite.
            ende_zeit = time.time() + 1.0
            while time.time() < ende_zeit:
                wurzel.update()
                wurzel.update_idletasks()
                time.sleep(0.02)
            neu_zeichnen(fenster.root)
            wurzel.update()
            if abgreifen(fenster.root, ziel):
                gemacht.append(name)
                print('  [ok]   %s' % name)
            else:
                misslungen.append(name)
                print('  [leer] %s — das Fenster hat nichts gezeichnet' % name)
        except Exception as ausnahme:
            misslungen.append(name)
            print('  [FEHL] %s — %s' % (name, ausnahme))
        finally:
            try:
                if fenster is not None:
                    fenster.root.destroy()
            except Exception:
                pass

    try:
        wurzel.destroy()
    except Exception:
        pass

    print()
    print('%d Bild(er) in assets/ — %d misslungen' % (len(gemacht), len(misslungen)))
    return 1 if misslungen else 0


if __name__ == '__main__':
    sys.exit(main())
