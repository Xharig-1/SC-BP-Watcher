# -*- coding: utf-8 -*-
"""Datei- und Ordnerauswahl, die nach dem System aussieht, auf dem sie läuft.

⚠ **Warum es dieses Modul gibt.** `tkinter.filedialog` zeichnet unter Linux
seinen **eigenen** Dialog — den alten Motif-Kasten: eine Spaltenliste mit jedem
versteckten Ordner (`.cache`, `.pki`, `.var`), kein Sortieren, keine Vorschau,
kein „zuletzt benutzt". Unter **Windows und macOS** reicht Tk dagegen den echten
Systemdialog durch; dort ist alles in Ordnung und dieses Modul greift nicht ein.

Unter Linux gibt es zwei verbreitete Helfer, die den **echten** Dialog des
Schreibtischs öffnen: `kdialog` (KDE Plasma) und `zenity` (GNOME, liegt aber auf
fast jedem System). Ist keiner da, bleibt der Tk-Dialog als Rückfall — hässlich,
aber funktionierend ist besser als gar nichts. **Nichts hängt davon ab.**

⚠ **Warum dieses Modul überhaupt entstand, obwohl es die Ordnerwahl schon gab:**
Für Ordner stand der ganze Ablauf bereits in `seiten.py` — für das Öffnen und
Speichern von **Dateien** aber nicht, dort lief weiterhin `filedialog`. Beim
Vorführen des Werkzeugs fiel es auf (gemeldet 27.08.2026: „bei Datei wählen
kommt auch diese hässliche unübersichtliche Ordner-Auswahl"). Die drei Wege
gehören zusammen und stehen deshalb jetzt an **einer** Stelle statt an dreien.
"""

import os
import shutil
import subprocess
import sys

from . import fehler

# Wie lange ein Dialog offen stehen darf, bevor aufgegeben wird. Großzügig: Es
# sitzt ein Mensch davor, der sucht.
GEDULD = 600

# Auf diesen Systemen ruft Tk den echten Systemdialog auf — Finger weg.
TK_IST_GUT = sys.platform.startswith(('win', 'darwin'))


def saubere_umgebung():
    """Weiterleitung — die Wahrheit steht in `pfade`.

    ⚠ Sie stand hier, weil die Dateiauswahl sie zuerst brauchte. Am 27.08.2026
    stellte sich heraus, dass der **Neustart nach einem Update** dieselbe Wäsche
    braucht und eine eigene, unvollständige Version mitführte — mit dem Ergebnis,
    dass sich das Werkzeug unter Linux nicht selbst neu starten konnte. Eine
    Wäsche an einer Stelle, benutzt von allen.
    """
    from . import pfade
    return pfade.saubere_umgebung()


def _im_pfad(name):
    """Gibt es dieses Programm auf dem Rechner?"""
    return bool(shutil.which(name))


def _versuchen(befehle, woher):
    """Die Helfer der Reihe nach fragen. Gibt den Pfad, '' oder None zurück.

    * **Pfad** — der Nutzer hat etwas gewählt.
    * **`''`** — er hat bewusst abgebrochen; damit ist die Sache erledigt.
    * **`None`** — kein Helfer kam durch; der Aufrufer nimmt den Tk-Dialog.

    ⚠ Rückgabecodes auseinanderhalten: **1 heißt „abgebrochen"** und ist eine
    gültige Antwort. Jeder andere Code heißt, das Werkzeug selbst ist
    gescheitert — dann wird der nächste versucht. Vorher galt beides als
    Abbruch, und ein im AppImage abgestürztes `zenity` sah aus wie ein Knopf
    ohne Funktion.
    """
    if TK_IST_GUT:
        return None
    umgebung = saubere_umgebung()
    for befehl in befehle:
        if not _im_pfad(befehl[0]):
            continue
        try:
            fertig = subprocess.run(befehl, capture_output=True, text=True,
                                    timeout=GEDULD, env=umgebung)
        except Exception as ausnahme:
            fehler.merken('%s:%s' % (woher, befehl[0]), ausnahme)
            continue
        gewaehlt = (fertig.stdout or '').strip()
        if fertig.returncode == 0 and gewaehlt:
            return gewaehlt
        if fertig.returncode == 1:
            return ''                      # bewusst abgebrochen
        fehler.merken('%s:%s' % (woher, befehl[0]),
                      RuntimeError('Code %s: %s' % (fertig.returncode,
                                                    (fertig.stderr or '')[:200])))
    return None


def _kdialog_filter(muster):
    """Tk-Muster `(('JSON', '*.json'), …)` in die Schreibweise von kdialog."""
    return ' '.join(m for _n, m in muster) + '|' + \
           ' '.join(n for n, _m in muster)


def ordner_waehlen(titel, start=None):
    """Einen Ordner auswählen lassen. Gibt den Pfad oder '' zurück."""
    antwort = _versuchen([
        ['kdialog', '--getexistingdirectory',
         start or os.path.expanduser('~'), '--title', titel],
        ['zenity', '--file-selection', '--directory', '--title', titel]
        + (['--filename', start.rstrip('/') + '/'] if start else []),
    ], 'dateiwahl.ordner')
    if antwort is not None:
        return antwort
    from tkinter import filedialog
    return filedialog.askdirectory(title=titel, initialdir=start or None) or ''


def datei_oeffnen(titel, muster=(('JSON', '*.json'),), start=None):
    """Eine vorhandene Datei auswählen lassen. Gibt den Pfad oder '' zurück."""
    zenity = ['zenity', '--file-selection', '--title', titel]
    for name, m in muster:
        zenity.append('--file-filter=%s | %s' % (name, m))
    if start:
        zenity += ['--filename', start.rstrip('/') + '/']
    antwort = _versuchen([
        ['kdialog', '--getopenfilename', start or os.path.expanduser('~'),
         _kdialog_filter(muster), '--title', titel],
        zenity,
    ], 'dateiwahl.oeffnen')
    if antwort is not None:
        return antwort
    from tkinter import filedialog
    return filedialog.askopenfilename(title=titel,
                                      filetypes=list(muster)) or ''


def datei_speichern(titel, vorschlag='', endung='.json', start=None,
                    muster=(('JSON', '*.json'),)):
    """Einen Speicherort auswählen lassen. Gibt den Pfad oder '' zurück.

    ⚠ Die Endung wird **nachgetragen**, wenn der Nutzer keine tippt. Tk erledigt
    das über `defaultextension` von allein, `kdialog` und `zenity` nicht — ohne
    diesen Schritt entstünde eine Datei ohne Endung, die hinterher kein Programm
    mehr als JSON erkennt.
    """
    ort = os.path.join(start or os.path.expanduser('~'), vorschlag) \
        if vorschlag else (start or os.path.expanduser('~'))
    antwort = _versuchen([
        ['kdialog', '--getsavefilename', ort, _kdialog_filter(muster),
         '--title', titel],
        ['zenity', '--file-selection', '--save', '--confirm-overwrite',
         '--title', titel, '--filename', ort],
    ], 'dateiwahl.speichern')
    if antwort is None:
        from tkinter import filedialog
        antwort = filedialog.asksaveasfilename(
            title=titel, initialfile=vorschlag, defaultextension=endung,
            filetypes=list(muster)) or ''
    if antwort and endung and not antwort.lower().endswith(endung.lower()):
        antwort += endung
    return antwort
