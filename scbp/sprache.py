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
Deutsch und Englisch — die Texte der Oberfläche.

Warum von Anfang an und nicht später: Unter Linux fahren die meisten
Star-Citizen-Spieler den englischen Client, und Windows-Spieler ohne den
SC Deutsch Launcher ebenso. Eine nur deutsche Oberfläche würde einen großen
Teil derer aussperren, für die dieses Werkzeug überhaupt gebaut wird. Und je
später man anfängt, desto mehr Textstellen sind es — hier waren es rund 40,
das ist ein Nachmittag; bei dreimal so vielen wäre es eine Plage.

**Der Spieler kann umschalten.** Standard ist `auto` (nach Systemsprache), aber
in `einstellungen.json` steht das Feld `sprache` — `de`, `en` oder `auto`.
Automatik allein reicht nicht: Wer ein englisches Windows fährt und trotzdem
Deutsch lesen will, soll das dürfen.

Benutzung:

    from .sprache import t
    t('bauplaene')                 -> 'Baupläne'  bzw.  'Blueprints'
    t('von_gesamt', 3, 714, 0)     -> '3 von 714 (0 %)'

Ein fehlender Schlüssel liefert den Schlüssel selbst zurück, statt abzustürzen —
eine vergessene Übersetzung soll auffallen, aber nichts kaputtmachen.
`python3 -m scbp.sprache` listet, was in einer Sprache fehlt.
"""
import locale
import os

from . import pfade

SPRACHEN = ('de', 'en')
STANDARD = 'de'

# Alle Texte, beide Sprachen nebeneinander. Bewusst in einer Tabelle statt in
# getrennten Dateien: So sieht man beim Nachtragen sofort, ob etwas fehlt.
TEXTE = {
    # -- Verwaltungsfenster --
    'titel_bauplaene':   ('SC BP Watcher — Baupläne', 'SC BP Watcher — Blueprints'),
    'bauplaene':         ('Baupläne', 'Blueprints'),
    'suchen':            ('Suchen …', 'Search …'),
    'filter_alle':       ('alle', 'all'),
    'filter_habe':       ('habe ich', 'owned'),
    'filter_fehlt':      ('fehlt mir', 'missing'),
    'nichts_gefunden':   ('Nichts gefunden.', 'Nothing found.'),
    'weitere_anzeigen':  ('… %d weitere anzeigen', '… show %d more'),
    'von_gesamt':        ('· %d von %d (%d %%)', '· %d of %d (%d %%)'),
    'kein_katalog':      ('Noch kein Bauplan-Katalog vorhanden.',
                          'No blueprint catalogue yet.'),
    'kein_katalog_hilfe': (
        'Er wird beim Start von scmdb.net geholt (etwa 12 MB,\n'
        'einmal je Spielversion). Ohne ihn läuft die Erkennung\n'
        'weiter, es fehlt nur diese Liste.',
        'It is fetched from scmdb.net on startup (about 12 MB,\n'
        'once per game version). Without it detection still works,\n'
        'only this list is missing.'),
    'katalog_holt':      ('Bauplan-Katalog wird geholt …',
                          'Fetching blueprint catalogue …'),
    'katalog_geholt':    ('Bauplan-Katalog geholt: %d Baupläne (%s)',
                          'Blueprint catalogue fetched: %d blueprints (%s)'),
    'ab_rang':           ('ab %s', 'from %s'),
    'annehmen_in':       ('Annehmen in', 'Available in'),
    'und_weitere':       (' und %d weiteren', ' and %d more'),
    'ruf_punkte':        ('(%s Ruf)', '(%s rep)'),
    'ruf_gewinn':        ('+%d Ruf', '+%d rep'),

    'export_ablage':     ('In die Ablage', 'To the export folder'),
    'export_einzeln':    ('Datei speichern …', 'Save file …'),
    'export_ablage_fertig': ('%d Dateien in der Ablage', '%d files in the folder'),
    'hinweis_export':    ('Bauplan-Bestand ausgeben — fürs Profit Basetool, für scmdb.net und als vollständige Sicherung',
                          'Export your blueprints — for the Profit Basetool, for scmdb.net and as a full backup'),
    'export_basetool':   ('Export fürs Basetool', 'Export for Basetool'),
    'export_alles':      ('Alles sichern', 'Export everything'),
    'export_fertig':     ('%s Baupläne gesichert', '%s blueprints saved'),
    'export_fehler':     ('Export fehlgeschlagen: %s', 'Export failed: %s'),
    'alle_dateien':      ('Alle Dateien', 'All files'),
    'filter_merk':       ('beobachtet', 'watching'),
    'merken':            ('Auf die Merkliste', 'Add to watchlist'),
    'nicht_mehr_merken': ('Von der Merkliste nehmen', 'Remove from watchlist'),
    'merkliste_leer':    ('Du beobachtest noch nichts. Tippe oben einen Namen '
                          'ein und klick auf den Stern.',
                          'You are not watching anything yet. Type a name above '
                          'and click the star.'),
    'merk_erledigt':     ('%s ist da — von der Merkliste genommen.',
                          '%s has arrived — removed from your watchlist.'),
    'merkliste':         ('Merkliste', 'Watchlist'),

    # -- Einstellungen --
    'einstellungen':     ('Einstellungen', 'Settings'),
    'status':            ('Status', 'Status'),
    'pfade':             ('Pfade', 'Paths'),
    'verhalten':         ('Verhalten', 'Behaviour'),
    'sprache':           ('Sprache', 'Language'),
    'sprache_auto':      ('automatisch (Systemsprache)', 'automatic (system language)'),
    'spielordner':       ('Spielordner (mit der Game.log darin)',
                          'Game folder (the one containing Game.log)'),
    'launcher_optional': ('SC Deutsch Launcher (optional)',
                          'SC Deutsch Launcher (optional)'),
    'durchsuchen':       ('Durchsuchen …', 'Browse …'),
    'leer_automatisch':  ('leer lassen = automatisch suchen. Gesucht wird hier:',
                          'leave empty = search automatically. Searched here:'),
    'gefunden':          ('● gefunden', '● found'),
    'nicht_gefunden':    ('● nicht gefunden', '● not found'),
    'ohne_ihn_laeuft':   ('ohne ihn läuft der Watcher trotzdem',
                          'the watcher runs without it'),
    'pruefintervall':    ('Prüfintervall', 'Check interval'),
    'pruefintervall_hilfe': ('Wie oft die Game.log angesehen wird',
                             'How often Game.log is checked'),
    'sekunden':          ('Sek.', 'sec'),
    'signalton':         ('Signalton bei neuem Bauplan',
                          'Sound on new blueprint'),
    'signalton_hilfe':   ('Kurzer Ton, wenn etwas erscheint',
                          'Short beep when something appears'),
    'autostart_win':     ('Mit Windows starten', 'Start with Windows'),
    'autostart_linux':   ('Beim Anmelden starten', 'Start on login'),
    'autostart_hilfe':   ('Trägt den Watcher in den Autostart ein',
                          'Adds the watcher to autostart'),
    'netz_holen':        ('Craftdaten aus dem Netz holen',
                          'Fetch crafting data from the internet'),
    'netz_holen_hilfe':  ('Nur bei neuer Spielversion',
                          'Only when the game version changes'),
    'lage_zuruecksetzen': ('Fensterlage zurücksetzen', 'Reset window position'),
    'speichern':         ('Speichern', 'Save'),
    'abbrechen':         ('Abbrechen', 'Cancel'),

    # -- Erster Start --
    'einrichtung_erklaerung': (
        'Der Watcher liest die Game.log von Star Citizen — dort steht jeder '
        'freigeschaltete Bauplan. Ohne diese Datei kann er nichts anzeigen. '
        'Bitte such den Ordner heraus, in dem sie liegt (meist „LIVE"). Der '
        'Ordner darüber genügt auch, der Rest wird gefunden.',
        'The watcher reads Star Citizen\'s Game.log — every unlocked blueprint '
        'is written there. Without that file it cannot show anything. Please '
        'pick the folder it lives in (usually "LIVE"). The folder above works '
        'too, the rest is found automatically.'),
    'log_gefunden':      ('✔ Game.log gefunden', '✔ Game.log found'),
    'keine_log_darin':   ('Dort liegt keine Game.log — auch nicht in den '
                          'Unterordnern.',
                          'No Game.log there — not in the subfolders either.'),
    'ordner_gedeutet':   ('Genommen wird: %s', 'Using: %s'),
    'weiter':            ('Weiter', 'Continue'),
    'willkommen':        ('Willkommen', 'Welcome'),
    'sprache_erkannt':   ('Spielsprache erkannt — Baupläne werden an „%s" '
                          'erkannt.',
                          'Game language detected — blueprints are recognised '
                          'by „%s".'),
    'lese_logs_n':       ('%d aufgehobene Spielsitzungen werden gelesen …',
                          'Reading %d stored play sessions …'),
    'lese_logs':         ('Deine bisherigen Spielsitzungen werden gelesen …',
                          'Reading your previous play sessions …'),
    'nachgelesen_gross': ('%d Baupläne aus %d früheren Sitzungen übernommen.',
                          '%d blueprints taken from %d earlier sessions.'),
    'nachtragen_hinweis': (
        'Was älter ist, kannst du in der Liste von Hand abhaken — '
        'alles andere hat der Watcher schon erledigt.',
        'Anything older can be ticked off by hand in the list — '
        'the watcher has already done the rest.'),
    'liste_oeffnen':     ('Liste öffnen', 'Open list'),
    'loslegen':          ('Los geht\'s', 'Get started'),

    # -- Einrichtungsassistent --
    'assistent':         ('Einrichtung', 'Setup'),
    'schritt_von':       ('Schritt %d von %d', 'Step %d of %d'),
    'zurueck':           ('Zurück', 'Back'),
    'fertig':            ('Fertig', 'Done'),
    'ueberspringen':     ('Überspringen', 'Skip'),
    'assistent_erneut':  ('Einrichtung erneut durchgehen',
                          'Run setup again'),

    'schritt_sprache':   ('Sprache', 'Language'),
    'schritt_sprache_text': (
        'In welcher Sprache soll das Fenster mit dir reden?',
        'Which language should this window speak?'),

    'schritt_spiel':     ('Star Citizen finden', 'Find Star Citizen'),
    'schritt_spiel_ok':  ('Star Citizen wurde gefunden. Passt das?',
                          'Star Citizen was found. Is this right?'),
    'schritt_spiel_text': (
        'Der Watcher liest die Game.log von Star Citizen — dort schreibt das '
        'Spiel jeden freigeschalteten Bauplan hinein. Ohne diese Datei kann er '
        'nichts anzeigen.',
        'The watcher reads Star Citizen\'s Game.log — the game writes every '
        'unlocked blueprint into it. Without that file it cannot show anything.'),
    'schritt_spiel_hilfe': (
        'Such den Ordner heraus, in dem die Game.log liegt (meist „LIVE"). '
        'Der Ordner darüber genügt auch — der Rest wird gefunden.',
        'Pick the folder containing Game.log (usually "LIVE"). The folder above '
        'works too — the rest is found automatically.'),

    'schritt_lesen':     ('Bisherige Baupläne holen', 'Collect past blueprints'),
    'schritt_lesen_text': (
        'Star Citizen hebt die Protokolle vergangener Spielsitzungen auf. Daraus '
        'holt sich der Watcher deinen bisherigen Bestand — du musst nichts '
        'eintippen.',
        'Star Citizen keeps logs of past play sessions. The watcher collects '
        'your existing blueprints from them — nothing to type in.'),

    'schritt_fertig':    ('Fertig', 'All set'),
    'schritt_fertig_text': (
        'Der Watcher läuft jetzt mit. Neue Baupläne erscheinen in der schmalen '
        'Leiste, sobald du sie im Spiel freischaltest.',
        'The watcher is running. New blueprints appear in the narrow bar as soon '
        'as you unlock them in the game.'),
    'tipp_liste':        ('Mit ☰ öffnest du jederzeit die Bauplan-Liste.',
                          'Use ☰ to open the blueprint list at any time.'),
    'tipp_erneut':       ('Diese Einrichtung kannst du jederzeit wiederholen — '
                          'du musst dich durch keine Menüs klicken.',
                          'You can run this setup again at any time — no need to '
                          'dig through menus.'),

    # -- Neue Fassungen --
    'was_ist_neu':       ('Was ist neu', 'What\'s new'),
    'neue_version_da':   ('Version %s ist da', 'Version %s is available'),
    'du_hast':           ('Du hast %s', 'You have %s'),
    'jetzt_holen':       ('Jetzt holen', 'Get it now'),
    'spaeter':           ('Später', 'Later'),
    'wird_geladen':      ('Wird geladen … %d %%', 'Downloading … %d %%'),
    'neustart_noetig':   ('Fertig. Beim nächsten Start läuft die neue Fassung.',
                          'Done. The new version runs on next start.'),
    'jetzt_neustarten':  ('Jetzt neu starten', 'Restart now'),
    'update_fehler':     ('Das hat nicht geklappt: %s',
                          'That did not work: %s'),
    'selbst_holen':      ('Bitte hol die neue Fassung selbst von der '
                          'Releases-Seite.',
                          'Please download the new version yourself from the '
                          'releases page.'),
    'update_quellcode':  ('Du startest aus dem Quellcode — hier ist „git pull" '
                          'der richtige Weg, sonst gingen deine Änderungen '
                          'verloren.',
                          'You are running from source — use "git pull" here, '
                          'otherwise your changes would be overwritten.'),
    'keine_versionen':   ('Noch keine Versionsangaben vorhanden.',
                          'No version information yet.'),
    'aktuelle_fassung':  ('Du hast die neueste Fassung.',
                          'You have the latest version.'),
    'suche_neue':        ('Nach neuer Fassung sehen', 'Check for updates'),

    # -- Statuszeilen und Meldungen --
    'ueberwache':        ('%d Baupläne · Log %s · %s · geprüft %s',
                          '%d blueprints · log %s · %s · checked %s'),
    'mit_launcher':      ('Launcher ✓', 'launcher ✓'),
    'ohne_launcher':     ('ohne Launcher', 'no launcher'),
    'nachgelesen':       ('Nachgelesen: %d Baupläne aus %d früheren Sitzungen '
                          'übernommen.',
                          'Caught up: %d blueprints from %d earlier sessions.'),
    'vorlaeufig':        ('vorläufig', 'provisional'),
    'neu_craftbar':      ('neu im Spiel craftbar', 'newly craftable in game'),
    'jetzt_craftbar':    ('%s — jetzt craftbar!', '%s — now craftable!'),
    'liste_leeren':      ('Liste leeren', 'Clear list'),
    # -- Erklärtexte beim Überfahren mit der Maus --
    # Kurz halten: Sie stehen über dem Spiel und werden im Vorbeigehen gelesen.
    'hinweis_ziehen':    ('Ziehen verschiebt das Fenster',
                          'Drag to move the window'),
    'hinweis_groesse':   ('Ziehen ändert die Größe',
                          'Drag to resize'),
    'hinweis_einklappen': ('Auf die Titelleiste einklappen — gibt die Sicht frei',
                           'Collapse to the title bar — frees up the view'),
    'hinweis_ausklappen': ('Wieder aufklappen', 'Expand again'),
    'hinweis_schliessen': ('Watcher beenden', 'Quit the watcher'),
    'hinweis_leeren':    ('Angezeigte Meldungen wegräumen — die Baupläne bleiben',
                          'Clear the messages shown — your blueprints stay'),
    'hinweis_liste':     ('Alle Baupläne: suchen, filtern, abhaken',
                          'All blueprints: search, filter, tick off'),
    'hinweis_assistent': ('Einrichtung noch einmal durchgehen',
                          'Run through setup again'),
    'hinweis_versionen': ('Was ist neu — die Versionsgeschichte',
                          'What is new — the version history'),
    'hinweis_neue_version': ('Eine neuere Fassung ist da — hier steht, was sie bringt',
                             'A newer version is available — see what it brings'),
    'hinweis_autostart_an': ('Läuft beim Anmelden mit — Klick schaltet es aus',
                             'Starts on login — click to turn off'),
    'hinweis_autostart_aus': ('Startet nicht von selbst — Klick schaltet es ein',
                              'Does not start by itself — click to turn on'),
    'hinweis_quellen':   ('Zeigt, woher es diesen Bauplan gibt',
                          'Shows where this blueprint comes from'),
    'start_eingetragen': ('%d Startbaupläne ergänzt — die hat jeder von Anfang an',
                          '%d starter blueprints added — everyone has these'),
    'hinweis_startbauplan': ('Startbauplan — den hat jeder Spieler von Anfang an',
                             'Starter blueprint — every player has this from the start'),
    'hinweis_ohne_quelle': ('Kein Auftrag bekannt, der diesen Bauplan gibt — meist eine Event-Belohnung',
                            'No known contract awards this blueprint — usually an event reward'),
    'hinweis_suche_leeren': ('Sucheingabe löschen', 'Clear the search'),
    'hinweis_bereich':   ('Diesen Bereich ein- und ausblenden',
                          'Show or hide this section'),

    # -- Einstellungsfenster --
    'titel_einstellungen': ('SC BP Watcher — Einstellungen',
                            'SC BP Watcher — Settings'),
    'einstellungen':     ('Einstellungen', 'Settings'),
    'hinweis_einstellungen': ('Einstellungen öffnen', 'Open settings'),
    'e_sprache':         ('Sprache', 'Language'),
    'e_sprache_hilfe':   ('Sprache dieses Fensters und aller Meldungen. Nicht zu '
                          'verwechseln mit der Sprache im Spiel — die findet der '
                          'Watcher selbst heraus.',
                          'Language of this window and all messages. Not the same '
                          'as your game language — the watcher works that one out '
                          'by itself.'),
    'e_sprache_auto':    ('Wie das System', 'Follow the system'),
    'e_spiel':           ('Star-Citizen-Ordner', 'Star Citizen folder'),
    'e_spiel_hilfe':     ('Der Ordner, in dem die Game.log liegt — meist „LIVE". '
                          'Leer lassen heißt: selbst suchen.',
                          'The folder holding Game.log — usually "LIVE". Leave '
                          'empty to search automatically.'),
    'e_launcher':        ('SC Deutsch Launcher', 'SC Deutsch Launcher'),
    'e_launcher_hilfe':  ('Optional, nur für Nutzer des Launchers: dessen Ordner '
                          '„blueprints". Ohne ihn läuft der Watcher genauso.',
                          'Optional, only for launcher users: its "blueprints" '
                          'folder. The watcher works just as well without it.'),
    'e_intervall':       ('Wie oft nachsehen', 'How often to check'),
    'e_intervall_hilfe': ('Sekunden zwischen zwei Blicken in die Game.log. '
                          'Erlaubt 1 bis 60.',
                          'Seconds between two looks at Game.log. 1 to 60 allowed.'),
    'e_deckkraft':       ('Durchsichtigkeit des Fensters', 'Window opacity'),
    'e_deckkraft_hilfe': ('100 = blickdicht, 30 = stark durchscheinend. Wer nur '
                          'einen Bildschirm hat, sieht so hindurch aufs Spiel. '
                          'Wirkt sofort.',
                          '100 = solid, 30 = strongly see-through. With a single '
                          'screen this lets you see the game underneath. Takes '
                          'effect immediately.'),
    'umzug_fertig':      ('%s Dateien in den neuen Ordner kopiert: %s',
                          '%s files copied to the new folder: %s'),
    'umzug_hinweis':     ('Deine Dateien liegen jetzt hier — der alte Ordner bleibt '
                          'als Sicherheitsnetz liegen.',
                          'Your files now live here — the old folder stays as a '
                          'safety net.'),
    # --- Seiten: alle sichtbaren Texte (ab v3.0.0) ---
    's_allg_lead':     ('Was fast jeder einmal einstellt und danach nie wieder anfasst.',
                          'What most people set once and never touch again.'),
    's_sprache_h':     ('Betrifft nur die Anzeige des Werkzeugs. Welche Sprache Star Citizen spricht, erkennt der Watcher selbst.',
                          'Affects only this tool. Which language Star Citizen speaks is detected on its own.'),
    's_ton_h':         ('Kurzer Ton, wenn ein Bauplan hereinkommt — hilfreich, wenn das Overlay verdeckt ist.',
                          'A short sound when a blueprint arrives — useful when the overlay is covered.'),
    's_autostart_h':   ('Der Watcher startet mit angemeldetem Benutzer und wartet im Hintergrund auf das Spiel.',
                          'The watcher starts with your session and waits in the background for the game.'),
    's_tray':          ('Symbol in der Ablage neben der Uhr',
                          'Icon in the tray next to the clock'),
    's_tray_h':        ('Beim Schließen verschwindet das Fenster in die Ablage statt zu beenden. Ein Klick holt es zurück.',
                          'Closing hides the window in the tray instead of quitting. One click brings it back.'),
    's_nur_win':       ('nur unter Windows',
                          'Windows only'),
    's_nicht_moegl':   ('hier nicht möglich',
                          'not available here'),
    's_anz_lead':      ('Wie das Overlay über dem Spiel liegt. Wer nur einen Bildschirm hat, findet hier das Wichtigste.',
                          'How the overlay sits above the game. If you only have one screen, this is where it matters.'),
    's_deck_h':        ('Weniger heißt durchsichtiger. Wird sofort vorgeführt, während du ziehst.',
                          'Less means more see-through. Shown live while you drag.'),
    's_klapp':         ('Eingeklappt starten',
                          'Start collapsed'),
    's_klapp_h':       ('Das Overlay schiebt sich beim Start auf die Titelleiste zusammen und gibt die Sicht frei. Der Pfeil ▾ klappt es jederzeit wieder auf.',
                          'The overlay folds into its title bar on start and frees the view. The ▾ arrow unfolds it any time.'),
    's_vorne':         ('Immer im Vordergrund',
                          'Always on top'),
    's_vorne_h':       ('Bleibt über dem Spiel sichtbar. Ausschalten, wenn das Overlay im Weg ist.',
                          'Stays visible above the game. Turn off if the overlay gets in the way.'),
    's_zeilen':        ('Zeilen im Overlay',
                          'Rows in the overlay'),
    's_zeilen_h':      ('So viele Neuzugänge bleiben stehen, ältere rutschen heraus. Die vollständige Liste steht ohnehin im Bauplan-Fenster.',
                          'This many new entries stay; older ones drop off. The full list is in the blueprint window anyway.'),
    's_lage':          ('Fensterlage vergessen',
                          'Forget window position'),
    's_lage_h':        ('Setzt Größe und Position zurück, falls das Overlay einmal außerhalb des Bildschirms gelandet ist.',
                          'Resets size and position in case the overlay ended up off-screen.'),
    's_zuruecksetzen': ('Zurücksetzen',
                          'Reset'),
    's_ordner_lead':   ('Wo Star Citizen liegt und wohin das Werkzeug seine eigenen Dateien schreibt. Leer heißt: selbst suchen.',
                          'Where Star Citizen lives and where this tool writes its own files. Empty means: search automatically.'),
    's_sc_da':         ('Star Citizen gefunden.',
                          'Star Citizen found.'),
    's_sc_weg':        ('Star Citizen nicht gefunden.',
                          'Star Citizen not found.'),
    's_sc_weg_h':      ('Trag den Ordner unten ein — der LIVE-Ordner reicht, auch der darüber oder das Wine-Präfix.',
                          'Enter the folder below — the LIVE folder is enough, as is the one above it or the Wine prefix.'),
    's_eigene':        ('Eigene Dateien',
                          'Your files'),
    's_eigene_h':      ('Hier liegen dein Bauplan-Bestand, die Merkliste und die ausgegebenen Dateien — in getrennten Unterordnern.',
                          'This holds your blueprint inventory, the watchlist and exported files — in separate subfolders.'),
    's_optional':      ('optional',
                          'optional'),
    's_durchsuchen':   ('Durchsuchen …',
                          'Browse …'),
    's_oeffnen':       ('Öffnen',
                          'Open'),
    's_vorschau_leer': ('Noch keine Datei gewählt',
                        'No file chosen yet'),
    's_vorschau_leer_h': ('Sobald du eine Datei wählst, steht hier, was der Import '
                          'täte: wie viele Baupläne dazukämen, wie viele du schon '
                          'hast und ob welche im Katalog fehlen. Übernommen wird '
                          'erst auf Knopfdruck.',
                          'As soon as you pick a file, this shows what the import '
                          'would do: how many blueprints would be added, how many '
                          'you already have, and whether any are missing from the '
                          'catalogue. Nothing is taken over until you press the '
                          'button.'),
    # -- Seite „Angaben im Spiel" --
    's_sp_lead':       ('Der Watcher schreibt zu jedem Auftrag, welche Baupläne er ausschüttet — mit Haken für das, was du schon hast. Sichtbar direkt im Missionstext.',
                          'The watcher notes on every mission which blueprints it hands out — with a tick for the ones you already have. Visible right in the mission text.'),
    's_sp_drin':       ('%d Textstellen eingetragen.',
                          '%d text passages written.'),
    's_sp_quelle_ist': ('Quelle: %s', 'Source: %s'),
    's_sp_nichts':     ('Zurzeit stehen keine Angaben im Spiel.',
                          'No details in the game at the moment.'),
    's_sp_nichts_h':   ('Wähle unten eine Textquelle — der Rest passiert von selbst.',
                          'Pick a text source below — the rest happens on its own.'),
    's_sp_quelle':     ('Textquelle', 'Text source'),
    's_sp_quelle_h':   ('Woher die Grundlage kommt, in die geschrieben wird. Ohne Übersetzung nimmt der Watcher die englischen Originaltexte aus deiner Installation. Übersetzung und StarStrings sind fremde Projekte — sie werden beim Klick von deren eigener Adresse geladen, nicht mitgeliefert.',
                          'Where the base text comes from that gets written into. Without a translation the watcher uses the original English text from your installation. The translation and StarStrings are other projects — they are fetched from their own address when you click, not shipped along.'),
    's_sp_q_de':       ('Deutsch', 'German'),
    's_sp_q_ss':       ('StarStrings', 'StarStrings'),
    's_sp_q_or':       ('Original', 'Original'),
    's_sp_auto':       ('Selbst aktuell halten', 'Keep up to date'),
    's_sp_auto_h':     ('Prüft beim Start und alle sechs Stunden. Ohne das sind die Angaben nach jedem Spiel-Patch still verschwunden — jedes Update schreibt die Textdatei neu.',
                          'Checks on start and every six hours. Without it the details are silently gone after every game patch — each update rewrites the text file.'),
    's_sp_auto_sagen': ('Selbst aktuell halten: %s', 'Keep up to date: %s'),
    's_sp_hand':       ('Von Hand', 'By hand'),
    's_sp_hand_h':     ('Alles Eingefügte steht zwischen Marken und lässt sich auf den Buchstaben genau wieder entfernen.',
                          'Everything inserted sits between markers and can be removed again to the letter.'),
    's_sp_jetzt':      ('Jetzt auffrischen', 'Refresh now'),
    's_sp_frisch':     ('Angaben aufgefrischt', 'Details refreshed'),
    's_sp_pruefen':    ('Prüfen, ob noch drin', 'Check whether still there'),
    's_sp_weg':        ('Wieder entfernen', 'Remove again'),
    's_sp_weg_ok':     ('Angaben entfernt', 'Details removed'),
    's_sp_warn':       ('Jedes Übersetzungs-Update und jeder Spiel-Patch löscht die Angaben.',
                          'Every translation update and every game patch wipes the details.'),
    's_sp_warn_h':     ('Beide schreiben die Textdatei neu. Deshalb gibt es „Jetzt auffrischen" und die Prüfung — ohne das denkt man, es funktioniere, und es ist längst weg.',
                          'Both rewrite the text file. That is why there is "Refresh now" and the check — without them you believe it works while it has long been gone.'),

    # -- Seite „Bestand" (ausgeben und einlesen) --
    's_be_lead':       ('Deinen Bauplan-Stand ausgeben — oder einen vorhandenen einlesen.',
                          'Export your blueprint inventory — or import an existing one.'),
    's_be_aus':        ('Bestand ausgeben', 'Export inventory'),
    's_be_aus_h':      ('Zum Hochladen oder als eigene Sicherung. Hochgeladen wird nichts — das machst du selbst.',
                          'For uploading or as your own backup. Nothing is uploaded — you do that yourself.'),
    's_be_n_bp':       ('%s Baupläne', '%s blueprints'),
    's_be_voll':       ('Vollständige Sicherung', 'Full backup'),
    's_be_voll_h':     ('mit Art, Klasse, Größe, Gütegrad',
                          'with type, class, size and grade'),
    's_be_alle_drei':  ('Alle drei in die Ablage', 'All three to the folder'),
    's_be_einzeln':    ('Einzeln speichern …', 'Save individually …'),
    's_be_ablage':     ('Ablage öffnen', 'Open folder'),
    's_be_geschrieben': ('%s Dateien in die Ablage geschrieben',
                          '%s files written to the folder'),
    's_be_schiefging': ('Ausgeben hat nicht geklappt', 'Export did not work'),
    's_be_speichern':  ('Bestand speichern', 'Save inventory'),
    's_be_gespeichert': ('Gespeichert: %s', 'Saved: %s'),
    's_be_ein':        ('Bestand einlesen', 'Import inventory'),
    's_be_ein_h':      ('Du hast deinen Stand schon woanders — im Basetool, bei scmdb, im SC Deutsch Launcher oder als Sicherung? Datei wählen, der Rest geht von selbst.',
                          'Already have your inventory elsewhere — in the Basetool, at scmdb, in the SC Deutsch Launcher or as a backup? Pick the file, the rest happens on its own.'),
    's_be_waehlen':    ('Datei wählen …', 'Choose file …'),
    's_be_erkannt':    ('Erkannt werden: eigene Sicherung · KRT Profit Basetool · scmdb.net · sc_bp_erledigt.json des Launchers. Welches Format vorliegt, findet das Werkzeug selbst heraus.',
                          'Recognised: your own backup · KRT Profit Basetool · scmdb.net · the launcher’s sc_bp_erledigt.json. Which format it is, the tool works out by itself.'),
    's_be_unbekannt':  ('Diese Datei kenne ich nicht.',
                          'I do not recognise this file.'),
    's_be_unbekannt_h': ('Erwartet werden: eigene Sicherung, KRT Profit Basetool, scmdb.net oder sc_bp_erledigt.json des Launchers.',
                          'Expected: your own backup, KRT Profit Basetool, scmdb.net or the launcher’s sc_bp_erledigt.json.'),
    's_be_vorschau':   ('Vorschau — nichts ist bisher übernommen',
                          'Preview — nothing has been taken over yet'),
    's_be_eigen':      ('Eigene Sicherung', 'Your own backup'),
    's_be_dazu':       ('kommen dazu', 'will be added'),
    's_be_schon':      ('hast du schon', 'you already have'),
    's_be_nicht_kat':  ('nicht im Katalog', 'not in the catalogue'),
    's_be_nicht_kat_h': ('Nicht im Katalog — kommen trotzdem mit:  ',
                          'Not in the catalogue — coming along anyway:  '),
    's_be_merge':      ('Vorhandenes bleibt unangetastet — es wird zusammengeführt, nie ersetzt.',
                          'What you already have stays untouched — it is merged, never replaced.'),
    's_be_nimm':       ('%d Baupläne übernehmen', 'Take over %d blueprints'),
    's_be_genommen':   ('%d Baupläne übernommen', '%d blueprints taken over'),

    # -- Seite „Erkennung" --
    's_er_lead':       ('Wie der Watcher merkt, dass ein Bauplan hereingekommen ist. Die Standardwerte passen für fast jeden — hier nur ändern, wenn etwas klemmt.',
                          'How the watcher notices that a blueprint has arrived. The defaults suit almost everyone — only change things here if something is stuck.'),
    's_er_takt':       ('Wie oft nachsehen', 'How often to look'),
    's_er_takt_h':     ('Sekunden zwischen zwei Blicken in die Protokolldatei. Kleiner heißt schneller und kostet etwas mehr Rechenzeit.',
                          'Seconds between two looks at the log file. Smaller means faster and costs a little more processing time.'),
    's_er_sek':        (' Sek.', ' sec.'),
    's_er_takt_sagen': ('Takt: %s Sekunden', 'Interval: %s seconds'),
    's_er_satz':       ('Erkannte Meldung', 'Detected message'),
    's_er_satz_h':     ('Der Satz, den das Spiel schreibt. Der Watcher leitet ihn selbst aus deinen Protokollen ab — hier steht, was gefunden wurde.',
                          'The sentence the game writes. The watcher derives it from your logs by itself — this is what it found.'),
    's_er_kat':        ('Katalog auffrischen', 'Refresh catalogue'),
    's_er_kat_h':      ('Welche Baupläne es gibt und woher sie kommen. Wird beim Start geholt, wenn eine neue Spielversion erschienen ist.',
                          'Which blueprints exist and where they come from. Fetched on start whenever a new game version has appeared.'),
    's_er_kat_holt':   ('Katalog wird geholt …', 'Fetching catalogue …'),
    's_er_kat_da':     ('Katalog aufgefrischt: %s Baupläne',
                          'Catalogue refreshed: %s blueprints'),
    's_er_kat_weg':    ('Katalog holen ging nicht', 'Could not fetch catalogue'),
    's_er_kat_jetzt':  ('Jetzt neu holen', 'Fetch again now'),
    's_er_alt':        ('Frühere Protokolle nachlesen', 'Re-read earlier logs'),
    's_er_alt_h':      ('Liest die aufgehobenen Spielprotokolle noch einmal von vorn. Nützlich nach einem Umzug oder wenn der Bestand Lücken hat.',
                          'Reads the kept game logs from the beginning once more. Useful after a move or when the inventory has gaps.'),
    's_er_alt_ok':     ('Beim nächsten Start werden die Protokolle neu gelesen',
                          'The logs will be read afresh on the next start'),
    's_er_alt_knopf':  ('Von vorn lesen', 'Read from the start'),

    # -- Seite „Diagnose" --
    's_di_lead':       ('Wenn etwas klemmt: Dieser Block sagt in einem Rutsch, woran es liegen könnte. Kopieren, in ein Issue einfügen, fertig.',
                          'When something is stuck: this block says in one go what it might be. Copy it, paste it into an issue, done.'),
    's_di_melden':     ('Fehler melden …', 'Report a problem …'),
    's_di_kopieren':   ('Angaben kopieren', 'Copy details'),
    's_di_speichern':  ('Als Datei speichern …', 'Save as a file …'),
    's_di_ordner':     ('Eigenen Ordner öffnen', 'Open own folder'),
    's_di_browser_ok': ('Formular im Browser geöffnet', 'Form opened in the browser'),
    's_di_browser_weg': ('Browser ließ sich nicht öffnen', 'The browser would not open'),
    's_di_kopiert':    ('Angaben kopiert', 'Details copied'),
    's_di_gespeichert': ('Gespeichert: %s', 'Saved: %s'),
    's_di_speich_weg': ('Speichern ging nicht', 'Saving did not work'),
    's_di_sicher':     ('Du siehst vorher genau, was du verschickst.',
                          'You see exactly what you send before you send it.'),
    's_di_sicher_h':   ('Der Block oben ist der ganze Inhalt — nichts wird im Hintergrund übertragen, und Pfade sind gekürzt, damit kein Benutzername in einem öffentlichen Issue landet.',
                          'The block above is the entire content — nothing is transmitted in the background, and paths are shortened so no user name ends up in a public issue.'),
    's_di_mit':        ('Fehler mitschreiben', 'Record errors'),
    's_di_mit_h':      ('Hält die letzten 50 unerwarteten Fehler mit Zeitpunkt und Stelle fest. Kostet nichts und ist der Unterschied zwischen „geht nicht" und einer Behebung.',
                          'Keeps the last 50 unexpected errors with time and place. Costs nothing and is the difference between "it does not work" and a fix.'),
    's_di_reset':      ('Bestand zurücksetzen', 'Reset inventory'),
    's_di_reset_h':    ('Baut den Bauplan-Bestand aus den vorhandenen Spielprotokollen neu auf.',
                          'Rebuilds the blueprint inventory from the game logs you still have.'),
    's_di_reset_frage': ('Dein Bauplan-Stand wird gelöscht und aus den vorhandenen Protokollen neu aufgebaut.\n\nWas älter ist als deine Protokolle, kommt nicht zurück. Fortfahren?',
                          'Your blueprint inventory will be deleted and rebuilt from the logs you still have.\n\nAnything older than your logs will not come back. Continue?'),
    's_di_reset_ok':   ('Bestand zurückgesetzt — beim nächsten Start neu gelesen',
                          'Inventory reset — read afresh on the next start'),
    's_di_reset_warn': ('Zurücksetzen löscht deinen Bauplan-Stand.',
                          'Resetting deletes your blueprint inventory.'),
    's_di_reset_warn_h': ('Der Watcher liest ihn danach aus den noch vorhandenen Protokollen neu auf — was älter ist, ist weg. Vorher unter „Bestand" ausgeben.',
                          'The watcher then rebuilds it from the logs that remain — anything older is gone. Export it under "Inventory" first.'),

    # -- Seiten „Fortschritt", „Allgemein", „Anzeige", „Ordner" (Reste) --
    's_fo_lead':       ('Wie weit du je Art bist.', 'How far along you are per type.'),
    's_fo_von':        ('  von %d Bauplänen · %.0f %%',
                          '  of %d blueprints · %.0f %%'),
    's_al_autostart':  ('Autostart: %s', 'Autostart: %s'),
    's_an_vorne':      ('Immer im Vordergrund: %s', 'Always on top: %s'),
    's_an_zeilen':     ('Zeilen im Overlay: %s', 'Rows in the overlay: %s'),
    's_an_lage_weg':   ('Fensterlage zurückgesetzt — gilt ab dem nächsten Start',
                          'Window position reset — takes effect on the next start'),
    's_or_mitlesen':   ('Die Game.log wird mitgelesen: %s',
                          'The Game.log is being read along: %s'),
    's_or_geoeffnet':  ('Ordner geöffnet', 'Folder opened'),
    's_or_eigener_ort': ('Ein eigener Ort lässt sich in den Einstellungen hinterlegen',
                          'A location of your own can be set in the settings'),
    's_or_leer':       ('leer — wird selbst gesucht',
                          'empty — found automatically'),

    # -- Seite „Was ist neu" --
    's_wn_lead':       ('Neu ist dazugekommen · Verbessert kann jetzt mehr · Behoben hat vorher geklemmt.',
                          'New was added · Improved can do more now · Fixed used to be broken.'),
    's_wn_nichts':     ('Nichts in dieser Auswahl.', 'Nothing in this selection.'),
    's_wn_aenderungen': ('  %d Änderungen', '  %d changes'),

    # -- Seite „Über" --
    's_ub_lead':       ('Welche Fassung läuft, wer sie gebaut hat — und ob du Neues vor allen anderen bekommen willst.',
                          'Which version is running, who built it — and whether you want new things before everyone else.'),
    's_ub_nachsehen':  ('Jetzt nachsehen', 'Check now'),
    's_ub_sucht':      ('Suche nach einer neuen Fassung …',
                          'Looking for a new version …'),
    's_ub_einrichtung': ('Einrichtung wiederholen', 'Run setup again'),
    's_ub_taeglich':   ('Täglich nach neuen Fassungen sehen',
                          'Check daily for new versions'),
    's_ub_taeglich_h': ('Höchstens einmal am Tag, ausschließlich bei GitHub. Ist etwas da, färbt sich ⓘ in der Titelleiste.',
                          'At most once a day, only at GitHub. If there is something, the ⓘ in the title bar changes colour.'),
    's_ub_kanal':      ('Welche Fassungen willst du bekommen?',
                          'Which versions do you want to get?'),
    's_ub_kanal_h':    ('Beim Testen mithelfen oder lieber Ruhe haben — beides ist in Ordnung, und du kannst jederzeit wechseln.',
                          'Help with testing or rather have some quiet — both are fine, and you can switch at any time.'),
    's_ub_wer_h':      ('Und woher die Daten kommen, ohne die es das Werkzeug nicht gäbe.',
                          'And where the data comes from, without which this tool would not exist.'),
    's_ub_fertig':     ('Nur fertige Fassungen', 'Finished versions only'),
    's_ub_fertig_h':   ('Das Übliche. Du bekommst eine Meldung, wenn eine geprüfte Fassung erscheint — samstags, höchstens einmal die Woche.',
                          'The usual. You get a notice when a tested version appears — on Saturdays, at most once a week.'),
    's_ub_test':       ('Auch Testfassungen', 'Test versions too'),
    's_ub_test_h':     ('Du siehst Neues als Erster und hilfst beim Prüfen. Testfassungen sind fertig gebaut und lauffähig, aber noch nicht lange erprobt — es kann etwas klemmen.',
                          'You see new things first and help with testing. Test versions are fully built and run, but have not been tried for long — something may be stuck.'),
    # Die Herkunftsangaben im Dank-Block. ⚠ Sie standen als Datentabelle im
    # Code und liefen über Variablen ins Fenster — `tools/texte_pruefen.py`
    # sieht so etwas nicht, weil dort kein fester Text an einem Bausteinargument
    # steht. Gefunden nur durch Hinsehen auf der englischen Seite.
    's_ub_q_katalog':  ('Bauplan-Katalog und Herkunft',
                          'blueprint catalogue and origins'),
    's_ub_q_uebersetzung': ('Übersetzung und Vertragsdaten',
                          'translation and mission data'),
    's_ub_q_vorbild':  ('Vorbild für die Einspielung ins Spiel',
                          'the model for writing into the game'),

    # -- Fehlerbericht (bericht.py) --
    # Der Bericht steht im Fenster und wird von dort in ein öffentliches Issue
    # kopiert. Er MUSS der Oberflächensprache folgen: Die Diagnose-Seite
    # verspricht „Du siehst vorher genau, was du verschickst" — auf Englisch
    # gilt das nur, wenn der Block darüber auch englisch ist.
    'b_kopf':          ('SC BP Watcher %s · Bericht vom %s',
                          'SC BP Watcher %s · report from %s'),
    'b_datum':         ('%d.%m.%Y, %H:%M', '%Y-%m-%d, %H:%M'),
    'b_system':        ('System', 'System'),
    'b_verpackung':    ('Verpackung', 'Packaging'),
    # ⚠ Nur für die Anzeige. Die Kennung selbst („quellcode", „exe",
    # „appimage") bleibt unübersetzt — `aktualisierung.py` vergleicht darauf,
    # und eine übersetzte Kennung würde die Update-Prüfung stillschweigend
    # ins Leere laufen lassen.
    'b_v_quellcode':   ('Quellcode', 'source code'),
    'b_v_exe':         ('exe', 'exe'),
    'b_v_appimage':    ('AppImage', 'AppImage'),
    'b_python':        ('Python / Tk', 'Python / Tk'),
    'b_bildschirm':    ('Bildschirm', 'Screen'),
    'b_skalierung':    ('%d×%d · Skalierung %d %%', '%d×%d · scaling %d %%'),
    'b_spiel':         ('Spiel', 'Game'),
    'b_gamelog':       ('Game.log', 'Game.log'),
    'b_sicherungen':   ('Sicherungen', 'Kept logs'),
    'b_protokolle':    ('%s Protokolle', '%s logs'),
    'b_launcher':      ('Launcher', 'Launcher'),
    'b_spielsprache':  ('Spielsprache', 'Game language'),
    'b_bestand':       ('Bestand', 'Inventory'),
    'b_n_bauplaene':   ('%s Baupläne', '%s blueprints'),
    'b_merkliste':     ('Merkliste', 'Watchlist'),
    'b_n_eintraege':   ('%s Einträge', '%s entries'),
    'b_katalog':       ('Katalogstand', 'Catalogue state'),
    'b_ordner':        ('Eigener Ordner', 'Own folder'),
    'b_einstellungen': ('Einstellungen', 'Settings'),
    'b_standard':      ('alle auf Standard', 'all at default'),
    'b_nicht_gefunden': ('nicht gefunden', 'not found'),
    'b_nicht_da':      ('nicht vorhanden', 'not present'),
    'b_fehler':        ('Letzte Fehler (%s von %s aufgehoben)',
                          'Recent errors (%s of %s kept)'),
    'b_fehler_keine':  ('Letzte Fehler        keine aufgezeichnet',
                          'Recent errors       none recorded'),
    'b_fuss':          ('Pfade gekürzt (<heim>, <benutzer>) · keine Namen, keine Zugangsdaten',
                          'Paths shortened (<home>, <user>) · no names, no credentials'),

    # -- Kurzmeldungen aus den Bausteinen (Injektion, Übersetzung, Logs) --
    # Sie kommen als Rückgabewert aus einem Modul und landen über
    # `fenster.sagen()` in der Statuszeile — also sichtbar für den Nutzer.
    'm_keine_scdl':    ('keine SCDL-Bauplan-Daten', 'no SCDL blueprint data'),
    'm_keine_ini':     ('global.ini nicht gefunden', 'global.ini not found'),
    'm_keine_missionen': ('Katalog kennt keine Missionen',
                          'the catalogue knows no missions'),
    'm_kein_p4k':      ('Data.p4k nicht gefunden', 'Data.p4k not found'),
    'm_keine_ini_archiv': ('global.ini im Archiv nicht gefunden',
                          'global.ini not found in the archive'),
    'm_keine_fassung': ('Fassung nicht gefunden', 'version not found'),
    'm_kein_zertifikat': ('Sichere Verbindung fehlgeschlagen — die Zertifikate des Systems wurden nicht gefunden',
                          'Secure connection failed — the system certificates were not found'),
    'm_keine_logs':    ('Keine Log-Sicherungen gefunden — der bisherige Bestand lässt sich nicht nachlesen.',
                          'No kept logs found — the earlier inventory cannot be recovered.'),
    'm_erster_lauf':   ('Erster Lauf: nachgelesen wurde ab %s. Was davor freigeschaltet wurde, muss von Hand abgehakt werden.',
                          'First run: read back from %s. Anything unlocked before that has to be ticked off by hand.'),
    'm_erster_datum':  ('%d.%m.%Y', '%Y-%m-%d'),
    'm_bericht_gekuerzt': ('\n\n… gekürzt. Der vollständige Bericht liegt unter "Als Datei speichern" und kann angehängt werden.',
                          '\n\n… shortened. The full report is available under "Save as a file" and can be attached.'),

    # -- Zwischenmeldungen beim Holen (Katalog, Spieltexte, Übersetzung) --
    # Sie stehen im Fenster, während etwas dauert. Ein stummes Programm sieht
    # aus wie ein hängendes — ein deutsch sprechendes auf einer englischen
    # Oberfläche aber auch wie ein halbfertiges.
    'z_werte':         ('Werte werden geholt …', 'Fetching values …'),
    'z_herkunft_datei': ('Bauplan-Herkunft wird aus %s gelesen …',
                          'Reading blueprint origins from %s …'),
    'z_herkunft_netz': ('Bauplan-Herkunft wird geholt (etwa 12 MB) …',
                          'Fetching blueprint origins (about 12 MB) …'),
    'z_auswerten':     ('Wird ausgewertet …', 'Evaluating …'),
    'z_startbp':       ('Startbaupläne werden geholt …',
                          'Fetching starting blueprints …'),
    'z_originaltexte': ('Originaltexte werden aus dem Spiel geholt …',
                          'Fetching the original texts from the game …'),
    'z_entpackt':      ('entpackt mit %s', 'unpacked with %s'),
    'z_laedt':         ('%s wird geladen (%.1f MB) …',
                          'Loading %s (%.1f MB) …'),
    'z_einsetzen':     ('wird eingesetzt …', 'installing …'),

    # -- Kennzahlen auf der Über-Seite --
    's_ub_fassung':    ('Fassung', 'Version'),
    's_ub_bekannt':    ('Baupläne bekannt', 'Blueprints known'),
    's_ub_davon':      ('Davon deine', 'Of those yours'),

    # -- Einrichtung ohne Spielordner --
    # Ohne diesen Ausweg sitzt fest, wer Star Citizen (noch) nicht auf diesem
    # Rechner hat: Der Weiter-Knopf blieb grau, und der Assistent kam bei jedem
    # Start wieder. Das Werkzeug kann auch ohne Spiel etwas — Liste ansehen,
    # Bestand einlesen, Merkliste pflegen.
    'ohne_spiel':      ('Erst mal ohne — ich richte das später ein',
                          'Continue without it — I will set this up later'),
    'ohne_spiel_titel': ('Ohne Spielordner eingerichtet',
                          'Set up without a game folder'),
    'ohne_spiel_text': ('Der Watcher kann jetzt nicht mitlesen, wenn ein Bauplan hereinkommt — dafür braucht er die Game.log. Alles andere geht: die Bauplan-Liste durchsehen, einen vorhandenen Bestand einlesen und die Merkliste pflegen.',
                          'The watcher cannot follow along when a blueprint arrives — that needs the Game.log. Everything else works: browsing the blueprint list, importing an existing inventory and keeping the watchlist.'),
    'ohne_spiel_wo':   ('Nachtragen kannst du den Ordner jederzeit unter Einstellungen → Ordner.',
                          'You can add the folder any time under Settings → Folders.'),

    # -- Herkunftsblock an fester Stelle unter der Liste --
    # Vorher hing er an jeder Zeile und klappte dort auf. Ein Bauplan hat bis
    # zu zwölf Bezugsquellen; der Block wurde über 700 Pixel hoch, während nur
    # 465 sichtbar sind — er schob die Liste komplett weg. Jetzt steht er fest
    # unten, zeigt den einfachsten Weg, und der Rest kommt auf Klick.
    'hk_ein_weg':      ('1 Weg', '1 way'),
    'hk_wege':         ('%d Wege', '%d ways'),
    'hk_leichtester':  ('leichtester Weg zuerst', 'easiest way first'),
    'hk_hast_du':      ('hast du', 'you have it'),
    'hk_fehlt_dir':    ('fehlt dir', 'you are missing it'),
    'hk_auftrag':      ('Auftrag', 'Mission'),
    'hk_fraktion':     ('Fraktion', 'Faction'),
    'hk_annahme':      ('Annahme', 'Pick up at'),
    'hk_rang':         ('Rang', 'Rank'),
    'hk_belohnung':    ('Belohnung', 'Reward'),
    'hk_weitere':      ('%d weitere Wege zu diesem Bauplan',
                          '%d more ways to this blueprint'),
    'hk_zu':           ('Schließen', 'Close'),
    'hk_nichts':       ('Klick auf eine Zeile — hier steht dann, woher der Bauplan kommt.',
                          'Click a row — this shows where the blueprint comes from.'),
    'hk_start':        ('Den hat jeder von Anfang an — es gibt keinen Auftrag, der ihn ausschüttet.',
                          'Everyone has this from the start — no mission hands it out.'),
    'hk_topf':         ('Sonderquelle', 'Special source'),
    'hk_topf_text':    ('Kein regulärer Auftrag schüttet ihn aus — er stammt aus diesem Belohnungstopf. Wann der wieder läuft, entscheidet CIG.',
                          'No regular mission hands it out — it comes from this reward pool. When that runs again is up to CIG.'),
    'hk_keine':        ('Zu diesem Bauplan ist keine Bezugsquelle bekannt.',
                          'No source is known for this blueprint.'),

    # --- Hauptfenster: Reiter und Rahmen (ab v3.0.0) ---
    'hf_titel':          ('SC BP Watcher', 'SC BP Watcher'),
    'hf_gruppe_bp':      ('Baupläne', 'Blueprints'),
    'hf_gruppe_einst':   ('Einstellungen', 'Settings'),
    'hf_fortgeschritten':('Für Fortgeschrittene', 'For advanced users'),
    'hf_gruppe_info':    ('Info', 'Info'),
    'hf_liste':          ('Bauplan-Liste', 'Blueprint list'),
    'hf_fortschritt':    ('Fortschritt', 'Progress'),
    'hf_allgemein':      ('Allgemein', 'General'),
    'hf_anzeige':        ('Anzeige', 'Display'),
    'hf_ordner':         ('Ordner', 'Folders'),
    'hf_spiel':          ('Angaben im Spiel', 'In-game details'),
    'hf_bestand':        ('Bestand', 'Inventory'),
    'hf_ueber':          ('Über', 'About'),
    'hf_erkennung':      ('Erkennung', 'Detection'),
    'hf_diagnose':       ('Diagnose', 'Diagnostics'),
    'hf_neu':            ('neu', 'new'),
    'hf_sofort':         ('Änderungen werden sofort gespeichert',
                          'Changes are saved right away'),
    'hf_schliessen':     ('Schließen', 'Close'),
    'hf_einrichtung':    ('Einrichtung', 'Setup'),
    'hf_wasistneu':      ('Was ist neu', "What's new"),
    'hf_hinweis_einr':   ('Einrichtung wiederholen — führt dich noch einmal durch '
                          'Sprache, Spielordner und Bestand',
                          'Repeat setup — walks you through language, game folder '
                          'and inventory again'),
    'hf_hinweis_neu':    ('Was ist neu — die Änderungen dieser und älterer Fassungen',
                          "What's new — the changes in this and earlier versions"),
    'hf_schrift':        ('Schriftgröße', 'Text size'),
    'hf_schrift_hilfe':  ('Vergrößert Schrift, Symbole und Knöpfe im ganzen Fenster. '
                          'Wirkt sofort.',
                          'Enlarges text, icons and buttons throughout the window. '
                          'Takes effect immediately.'),
    'hf_s_klein':        ('Klein', 'Small'),
    'hf_s_normal':       ('Normal', 'Normal'),
    'hf_s_gross':        ('Groß', 'Large'),
    'hf_s_sehrgross':    ('Sehr groß', 'Very large'),
    'hf_wer':            ('Wer das gebaut hat', 'Who built this'),
    'hf_dank':           ('Ohne diese Daten gäbe es das Werkzeug nicht',
                          'Without this data the tool would not exist'),
    'hf_nichts_dabei':   ('Alles wird zur Laufzeit von der Originaladresse geholt — '
                          'mitgeliefert wird nichts.',
                          'Everything is fetched from the original address at '
                          'runtime — nothing is bundled.'),
    'hf_fancontent':     ('Dies ist ein inoffizielles Star-Citizen-Fanprojekt und steht '
                          'in keiner Verbindung zur Cloud Imperium Games Corporation '
                          'oder ihren Tochterunternehmen. Alle Inhalte dieses '
                          'Werkzeugs, die nicht von Xharig stammen, sind Eigentum '
                          'ihrer jeweiligen Inhaber.',
                          'This is an unofficial Star Citizen fan project, not '
                          'affiliated with the Cloud Imperium Games Corporation or '
                          'its subsidiaries. All content of this tool that is not '
                          'by Xharig belongs to its respective owners.'),
    'e_vorab':           ('Auch Testfassungen anbieten',
                          'Offer test versions too'),
    'e_vorab_hilfe':     ('Testfassungen (rc) kommen vor den fertigen Fassungen und '
                          'enthalten Neues, das noch nicht lange erprobt ist. '
                          'Wer mithelfen will, schaltet das ein und bekommt sie als '
                          'Erster angeboten; ausgeschaltet siehst du nur fertige '
                          'Fassungen. Umschalten geht jederzeit — die fertige Fassung '
                          'gilt immer als neuer als jede Testfassung derselben Nummer.',
                          'Test versions (rc) arrive before the finished ones and '
                          'contain changes that have not been proven for long. Turn '
                          'this on to help out and get them first; left off, you only '
                          'see finished versions. You can switch back at any time — a '
                          'finished version always counts as newer than any test '
                          'version of the same number.'),
    'e_ton':             ('Signalton', 'Sound'),
    'e_ton_hilfe':       ('Kurzer Ton, wenn ein Bauplan erscheint.',
                          'A short sound when a blueprint shows up.'),
    'e_an':              ('an', 'on'),
    'e_aus':             ('aus', 'off'),
    'e_durchsuchen':     ('Suchen …', 'Browse …'),
    'e_speichern':       ('Speichern', 'Save'),
    'e_gespeichert':     ('Gespeichert.', 'Saved.'),
    'e_neustart_noetig': ('Gespeichert — für Ordner und Prüfintervall den Watcher '
                          'einmal neu starten.',
                          'Saved — restart the watcher for folder and interval '
                          'changes to take effect.'),
    'e_pfad_fehlt':      ('Diesen Ordner gibt es nicht — bitte prüfen.',
                          'That folder does not exist — please check.'),

    # -- Bauplan-Angaben im Spiel (Injektion) --
    'schritt_spiel_texte': ('Bauplan-Angaben im Spiel', 'Blueprint notes in game'),
    'inj_text':          ('Der Watcher kann die Bauplan-Angaben direkt in die '
                          'Missionstexte des Spiels schreiben: welche Baupläne '
                          'ein Auftrag ausschüttet, mit Kästchen für die, die du '
                          'schon hast.',
                          'The watcher can write blueprint details straight into '
                          'the game\'s mission texts: which blueprints a contract '
                          'awards, with a tick box for the ones you already have.'),
    'inj_wie':           ('Dafür wird die Textdatei des Spiels verändert '
                          '(`global.ini`). Am Spiel selbst ändert sich sonst '
                          'nichts, und der Schritt lässt sich jederzeit '
                          'zurücknehmen.',
                          'This modifies the game\'s text file (`global.ini`). '
                          'Nothing else about the game changes, and it can be '
                          'undone at any time.'),
    'inj_quelle_de':     ('Deutsch — Übersetzung von rjcncpt laden',
                          'German — fetch the rjcncpt translation'),
    'inj_quelle_ss':     ('Englisch — StarStrings von MrKraken laden',
                          'English — fetch StarStrings by MrKraken'),
    'inj_quelle_orig':   ('Englisch — Originaltexte aus dem Spiel',
                          'English — original texts from the game'),
    'inj_quelle_aus':    ('Jetzt nicht', 'Not now'),
    'inj_fremd':         ('Übersetzung und StarStrings sind fremde Projekte. Sie '
                          'werden beim Klick von deren eigener Adresse geladen, '
                          'nicht mitgeliefert.',
                          'The translation and StarStrings are separate projects. '
                          'They are fetched from their own pages on click, not '
                          'bundled with this tool.'),
    'inj_laeuft':        ('wird eingerichtet …', 'setting up …'),
    'inj_fertig':        ('Fertig: %s', 'Done: %s'),
    'inj_fehler':        ('Hat nicht geklappt: %s', 'Did not work: %s'),
    'inj_aktiv':         ('Bauplan-Angaben sind eingetragen (%d Stellen)',
                          'Blueprint notes are in place (%d spots)'),
    'inj_steht':         ('Bauplan-Angaben sind eingetragen',
                          'Blueprint notes are in place'),
    'inj_steht_nicht':   ('Bauplan-Angaben sind nicht eingetragen',
                          'Blueprint notes are not in place'),
    'inj_entfernen':     ('Angaben wieder entfernen', 'Remove the notes again'),
    'inj_erneuern':      ('Angaben auffrischen', 'Refresh the notes'),
    'inj_update_da':     ('Neue Fassung verfügbar: %s', 'New version available: %s'),
    'inj_aktuell':       ('Ist auf dem neuesten Stand', 'Up to date'),
    'inj_pruefen':       ('Auf Updates prüfen', 'Check for updates'),
    'texte_erneuert':    ('Übersetzung aktualisiert (%s)',
                          'Translation updated (%s)'),
    'bpdaten_erneuert':  ('Neue Bauplan-Daten (%s)',
                          'New blueprint data (%s)'),

    # -- Bereiche (Obergruppen der Kategorien) --
    'gruppe_schiff':     ('Schiffsteile', 'Ship parts'),
    'gruppe_fps':        ('FPS-Waffen', 'FPS weapons'),
    'gruppe_ruestung':   ('Rüstung & Kleidung', 'Armor & clothing'),
    'gruppe_sonstiges':  ('Sonstiges', 'Other'),
    'hinweis_schliessen_liste': ('Liste schließen — der Watcher läuft weiter',
                                 'Close the list — the watcher keeps running'),
    'sc_nicht_gefunden': ('Star Citizen wurde nicht gefunden.',
                          'Star Citizen was not found.'),
    'gesucht_wurde_hier': ('Gesucht wurde hier:', 'Searched here:'),

    # -- Bauplan-Arten (kommen als Rohbegriffe von scmdb) --
    'art_Char_Armor_Helmet':    ('Helm', 'Helmet'),
    'art_Char_Armor_Torso':     ('Rüstung (Torso)', 'Armor (torso)'),
    'art_Char_Armor_Legs':      ('Rüstung (Beine)', 'Armor (legs)'),
    'art_Char_Armor_Arms':      ('Rüstung (Arme)', 'Armor (arms)'),
    'art_Char_Armor_Backpack':  ('Rucksack', 'Backpack'),
    'art_Char_Armor_Undersuit': ('Unteranzug', 'Undersuit'),
    'art_QuantumDrive':         ('Quantum Drive', 'Quantum Drive'),
    'art_PowerPlant':           ('Power Plant', 'Power Plant'),
    'art_WeaponGun':            ('Schiffswaffe', 'Ship weapon'),
    'art_WeaponPersonal':       ('FPS-Waffe', 'FPS weapon'),
    'art_WeaponMining':         ('Mining-Laser', 'Mining laser'),
    'art_WeaponAttachment':     ('Waffenaufsatz', 'Weapon attachment'),
    'art_SalvageModifier':      ('Salvage-Modifikator', 'Salvage modifier'),
    'art_SalvageHead':          ('Salvage-Kopf', 'Salvage head'),
    'art_TractorBeam':          ('Traktorstrahl', 'Tractor beam'),
    'art_DockingCollar':        ('Andockkragen', 'Docking collar'),
    'art_Cooler':               ('Cooler', 'Cooler'),
    'art_Shield':               ('Schild', 'Shield'),
    'art_Radar':                ('Radar', 'Radar'),
    'art_Misc':                 ('Sonstiges', 'Other'),
    # scmdb führt einige Baupläne unter kleingeschriebenen Sammelbegriffen.
    # Ohne diese drei Zeilen stünde in der Liste wörtlich „weapons".
    'art_weapons':              ('Handfeuerwaffe', 'Personal weapon'),
    'art_ammo':                 ('Magazin', 'Magazine'),
    'art_armour':               ('Anzug', 'Suit'),
    'art_Cargo':                ('Frachtmodul', 'Cargo module'),
    'art_Char_Clothing_Torso_0': ('Kleidung (Oberkörper)', 'Clothing (torso)'),
    'art_Char_Clothing_Torso_1': ('Kleidung (Jacke)', 'Clothing (jacket)'),
    'art_Char_Clothing_Legs':   ('Kleidung (Beine)', 'Clothing (legs)'),
    'art_Char_Clothing_Feet':   ('Kleidung (Schuhe)', 'Clothing (shoes)'),
    'art_unbekannt':            ('Sonstiges', 'Other'),
}

_aktuell = [None]


def systemsprache():
    """Was das Betriebssystem sagt. Alles außer Deutsch gilt als Englisch."""
    for quelle in (os.environ.get('SC_BP_SPRACHE'),
                   os.environ.get('LANG'), os.environ.get('LC_ALL')):
        if quelle:
            return 'de' if quelle.lower().startswith('de') else 'en'
    try:
        kennung = locale.getdefaultlocale()[0] or ''
    except Exception:
        kennung = ''
    return 'de' if kennung.lower().startswith('de') else 'en'


def gewaehlt():
    """Was der Nutzer eingestellt hat: 'de', 'en' oder 'auto'."""
    wert = (pfade.einstellungen().get('sprache') or 'auto').strip().lower()
    return wert if wert in SPRACHEN + ('auto',) else 'auto'


def aktuelle():
    """Die Sprache, in der gerade geschrieben wird."""
    if _aktuell[0] is None:
        wahl = gewaehlt()
        _aktuell[0] = systemsprache() if wahl == 'auto' else wahl
    return _aktuell[0]


def setzen(sprache):
    """Sprache für diesen Lauf umstellen (ohne die Einstellung zu ändern).

    Das Speichern macht das Einstellungsfenster; hier geht es nur darum, dass
    ein Umschalten sofort sichtbar wird, ohne das Programm neu zu starten."""
    if sprache in SPRACHEN:
        _aktuell[0] = sprache
    elif sprache == 'auto':
        _aktuell[0] = systemsprache()


def t(schluessel, *werte):
    """Ein Text in der aktuellen Sprache, wahlweise mit eingesetzten Werten."""
    eintrag = TEXTE.get(schluessel)
    if not eintrag:
        return schluessel                       # fehlt: fällt auf, stürzt nicht ab
    text = eintrag[SPRACHEN.index(aktuelle())] or eintrag[0]
    return (text % werte) if werte else text


def art(roh):
    """Rohbegriff von scmdb -> Bezeichnung in der aktuellen Sprache."""
    return t('art_%s' % roh) if ('art_%s' % roh) in TEXTE else (roh or t('art_unbekannt'))


if __name__ == '__main__':
    print('Systemsprache:', systemsprache(), '· eingestellt:', gewaehlt(),
          '· aktiv:', aktuelle())
    luecken = [k for k, v in TEXTE.items() if len(v) != 2 or not all(v)]
    print('Einträge:', len(TEXTE), '· unvollständig:', len(luecken))
    for k in luecken:
        print('   fehlt:', k)
    for s in SPRACHEN:
        setzen(s)
        print('\n[%s] %s | %s | %s' % (s, t('bauplaene'), t('filter_fehlt'),
                                       t('von_gesamt', 3, 714, 0)))
