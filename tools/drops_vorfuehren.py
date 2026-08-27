# -*- coding: utf-8 -*-
"""Lässt Bauplan-Funde einlaufen — zum Vorführen und für die Bildschirmfotos.

**Wozu.** Für die Bilder in der Anleitung muss man dem Werkzeug bei der Arbeit
zusehen können. Ohne laufendes Star Citizen passiert aber nichts: Die Melde-Leiste
bleibt leer, und ein leeres Overlay erklärt niemandem, wozu es gut ist.

Dieses Skript schreibt echte Fund-Zeilen in eine Wegwerf-`Game.log`, so wie das
Spiel es täte. Der Watcher liest sie im selben Moment und meldet sie — es gibt
keinen Sonderweg und keinen Testmodus im Programm selbst. Was hier zu sehen ist,
ist genau das, was auch beim Spielen passiert.

**Alle vier Zustände auf einmal**, damit das Bild die Zeichen-Erklärung in der
Anleitung vollständig bebildert:

| Zeichen | Zustand | Wie es hier entsteht |
|---|---|---|
| gelb | vorläufig, nur aus der Log | ein Fund ohne Launcher-Bestätigung |
| grün | bestätigt | ein Fund, den der Launcher-Export kennt |
| Stern | von der Merkliste | ein Fund, der vorher vorgemerkt wurde |
| blau | neu im Spiel craftbar | kommt vom Katalog selbst, echte Patch-Daten |

**Die Namen sind echt** und stammen aus dem Katalog — und zwar aus dem, was
der Autor *nicht* hat. Ausgedachte Namen wären hier schädlich: Am Bildschirmfoto
sähe man ihnen nichts an, aber ein Leser, der sie nachschlägt, findet nichts.

**Aufruf** — in dieser Reihenfolge:

    python3 tools/drops_vorfuehren.py --vorbereiten   # Merkliste, Wegwerf-Ordner
    #  … jetzt den Watcher starten …
    python3 tools/drops_vorfuehren.py                 # die Funde laufen ein

Der erste Schritt muss **vor** dem Watcher-Start laufen: Die Merkliste wird
beim Start eingelesen, eine spätere Änderung sieht er nicht mehr.

Zum Aufräumen hinterher:

    python3 tools/drops_vorfuehren.py --aufraeumen
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scbp import merkliste, pfade                      # noqa: E402

# Ein Wegwerf-Spielordner neben der Ablage des Testlaufs — nicht im Projekt,
# damit nichts davon je in einen Commit rutscht.
ORDNER = os.path.join(os.path.expanduser('~'), 'Documents',
                      'SC BP Watcher Test', 'Spiel-Vorfuehrung')

# Die Zeile, die Star Citizen beim Freischalten schreibt. Wortlaut aus
# `scbp/phrasen.py` — wird der dort geändert, muss er hier mitziehen.
ZEILE = ('<%s> [Notice] <SHUDEvent_OnNotification> Added notification '
         '"Bauplan erhalten: %s: " [136]\n')

# Echte Baupläne aus dem Katalog, die der Autor noch nicht hat.
# Bewusst verschiedene Arten — eine Liste aus lauter Schilden sieht aus wie ein
# Fehler, nicht wie ein Spielabend.
FUNDE = [
    ('Aufeis', 'Cooler'),
    ('CF-337 Panther Repeater', 'Schiffswaffe'),
    ('Durango', 'Power Plant'),
]
# Der hier wird vorher auf die Merkliste gesetzt und kommt deshalb in Gold
# mit Stern — der vierte Zustand.
GEMERKT = ('Arclight "Midnight" Pistol', 'FPS-Waffe')


def _stempel():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())


def einrichten():
    """Wegwerf-Spielordner anlegen und dem Watcher als Spielordner geben."""
    os.makedirs(os.path.join(ORDNER, 'logbackups'), exist_ok=True)
    log = os.path.join(ORDNER, 'Game.log')
    if not os.path.exists(log):
        with open(log, 'w', encoding='utf-8') as f:
            f.write('<%s> [Notice] <Legacy> Spiel gestartet\n' % _stempel())
    vorher = pfade.einstellung('spiel_ordner')
    if vorher != ORDNER:
        pfade.einstellung_setzen('spiel_ordner', ORDNER)
        print('  Spielordner eingetragen: %s' % ORDNER)
    return log


def vorbereiten():
    """Alles, was **vor** dem Watcher-Start passieren muss.

    ⚠ Die Merkliste liest der Watcher beim Start ein. Wer sie ändert, während er
    schon läuft, ändert nichts an dem, was er sieht — der vorgemerkte Fund käme
    dann ohne Stern durch. Deshalb dieser eigene Schritt.
    """
    einrichten()
    if not merkliste.enthaelt(GEMERKT[0]):
        # ⚠ `hinzufuegen()` gibt die geänderten Daten nur **zurück**, es
        # speichert sie nicht — das steht so in seinem Docstring. Ohne
        # `speichern()` dahinter passiert nichts, und der Fund käme ohne Stern.
        merkliste.speichern(merkliste.hinzufuegen(GEMERKT[0]))
        print('  Auf die Merkliste gesetzt: %s' % GEMERKT[0])
    else:
        print('  Steht schon auf der Merkliste: %s' % GEMERKT[0])
    print('\n  Jetzt den Watcher starten, dann:')
    print('    python3 tools/drops_vorfuehren.py')


def vorfuehren():
    log = einrichten()

    if not merkliste.enthaelt(GEMERKT[0]):
        print('  ⚠ %s steht nicht auf der Merkliste.' % GEMERKT[0])
        print('    Der Fund kommt dann ohne Stern. Erst vorbereiten:')
        print('      python3 tools/drops_vorfuehren.py --vorbereiten')
        print('    (und den Watcher danach neu starten)\n')

    print('\n  ⚠ Der Watcher muss jetzt laufen — sonst schreibt das hier ins Leere.')
    print('  Die Funde kommen einzeln, mit Pause dazwischen.\n')
    time.sleep(3)

    reihe = FUNDE + [GEMERKT]
    with open(log, 'a', encoding='utf-8') as f:
        for i, (name, art) in enumerate(reihe, 1):
            f.write(ZEILE % (_stempel(), name))
            f.flush()
            os.fsync(f.fileno())          # sonst hängt die Zeile im Puffer
            print('  %d/%d  %-30s %s' % (i, len(reihe), name, art))
            time.sleep(4)

    print('\n  Fertig. In der Melde-Leiste stehen jetzt %d Funde,'
          % len(reihe))
    print('  darunter einer in Gold mit Stern (%s).' % GEMERKT[0])
    print('\n  Hinterher aufräumen:')
    print('    python3 tools/drops_vorfuehren.py --aufraeumen')


def aufraeumen():
    """Den Vorführ-Stand zurücknehmen — Merkliste, Spielordner, Log."""
    if merkliste.enthaelt(GEMERKT[0]):
        merkliste.speichern(merkliste.entfernen(GEMERKT[0]))
        print('  Von der Merkliste genommen: %s' % GEMERKT[0])
    if pfade.einstellung('spiel_ordner') == ORDNER:
        pfade.einstellung_setzen('spiel_ordner', '')
        print('  Spielordner-Eintrag zurückgenommen')
    log = os.path.join(ORDNER, 'Game.log')
    if os.path.exists(log):
        os.remove(log)
        print('  Wegwerf-Log gelöscht')
    # ⚠ Die vorgeführten Funde **aus dem Bestand nehmen**. Sonst meldet der
    # Watcher sie beim nächsten Durchlauf nicht mehr — er kennt sie ja bereits,
    # und die Vorführung liefe ins Leere, ohne dass man den Grund sähe.
    from scbp import bestand as bd
    daten = bd.laden()
    weg = []
    for name, _ in FUNDE + [GEMERKT]:
        if bd.enthaelt(daten, name):
            bd.entfernen(daten, name)
            weg.append(name)
    if weg:
        bd.speichern(daten)
        print('  Aus dem Bestand genommen: %d (%s)'
              % (len(weg), ', '.join(w[:18] for w in weg)))

    # ⚠ Und den Lesestand zurücksetzen. Er merkt sich, bis wohin die Log gelesen
    # wurde — ohne das würden dieselben Zeilen beim nächsten Mal übersprungen.
    stand = pfade.app_datei('logstand.json')
    if os.path.exists(stand):
        os.remove(stand)
        print('  Lesestand zurückgesetzt')

    print('\n  Wiederholbar: --vorbereiten, Watcher starten, dann ohne Schalter.')


if __name__ == '__main__':
    if '--aufraeumen' in sys.argv:
        aufraeumen()
    elif '--vorbereiten' in sys.argv:
        vorbereiten()
    else:
        vorfuehren()
