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
Wohin ein Fehlerbericht geht, wenn der Nutzer „Absenden" drückt.

⚠ **Diese Datei steht im Repo bewusst leer.** Die Adresse ist ein Geheimnis:
Wer sie hat, kann in den Kanal schreiben. Beim Bau schreibt
`.github/workflows/release.yml` sie aus dem GitHub-Secret `BERICHT_WEBHOOK`
hinein — im Quellcode taucht sie nie auf.

**Warum es diesen Weg überhaupt gibt.** Den Bericht zu kopieren und in Discord
einzufügen scheitert an drei Stellen: Er steckt unter „Fortgeschritten", er ist
zu lang für eine Nachricht, und man muss wissen, wohin damit. der Autor am
28.08.2026: „ich will nicht jedem eine Stunde erklären, wie ich zu dem Bericht
komme, das ist nervenaufreibend." Und sein Bruder, um den es ging: „weil ich
kein Nerd bin … ich installiere und es funktioniert, wenn nicht, unbrauchbar."

Ein Knopf ist die einzige Fassung, die bei so jemandem ankommt.

⚠ **Auslesbar bleibt die Adresse trotzdem.** Sie steckt in der gebauten Datei,
und wer dort sucht, findet sie. Deshalb: ein **eigener Kanal** nur für Berichte,
und wenn jemand Unfug treibt, wird der Webhook gelöscht und ein neuer angelegt.
Der Schaden ist damit auf „ein Kanal muss aufgeräumt werden" begrenzt.
"""

# Wird beim Bau ersetzt. Leer heißt: Der Knopf wird gar nicht erst angeboten —
# ein Knopf, der nichts tun kann, ist schlimmer als keiner.
WEBHOOK = ''


def ziel():
    """Die Adresse — oder `''`, wenn keine vorliegt.

    ⚠ **`SC_BP_BERICHT_ZIEL` schlägt die eingebaute Adresse.** Damit lässt sich
    der Weg aus dem Quellcode heraus ausprobieren, ohne erst eine Fassung zu
    bauen — und ohne die Adresse irgendwo hinzuschreiben, wo sie liegen bleibt:

        SC_BP_BERICHT_ZIEL="https://…" bash "SC-BP-Watcher starten.sh"

    Gedacht ist das zum Prüfen. Für Nutzer bleibt es bei dem, was der Bau
    einsetzt; wer die Variable nicht kennt, merkt von ihr nichts.
    """
    import os
    return (os.environ.get('SC_BP_BERICHT_ZIEL') or WEBHOOK or '').strip()


def moeglich():
    """Kann überhaupt gesendet werden? Nur dann gibt es den Knopf."""
    return ziel().startswith('https://')
