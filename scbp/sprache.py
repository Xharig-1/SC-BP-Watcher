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
später man anfängt, desto mehr Textstellen sind es — beim Bauen von Phase 2
waren es rund 40, das ist ein Nachmittag; bei dreimal so vielen eine Plage.

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
    'ab_rang':           ('ab %s', 'from %s'),
    'ruf_punkte':        ('(%s Ruf)', '(%s rep)'),
    'ruf_gewinn':        ('+%d Ruf', '+%d rep'),

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
