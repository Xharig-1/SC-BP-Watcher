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
Bauplan-Angaben in die Texte des Spiels schreiben.

An jede Mission, die Baupläne ausschüttet, kommt die Liste dessen, was sie
geben kann — mit einem **Kästchen** davor: angehakt, was man schon hat, leer,
was fehlt. Dazu ein Kürzel im Missionstitel, damit man es schon in der
Auftragsliste sieht, ohne jede Mission aufzuklappen.

Das Vorbild ist der SC Deutsch Launcher, der genau das seit Langem macht
(`bp_contractInfo`, `bp_erledigt`). Zwei Gründe, es hier trotzdem zu haben:
Er läuft nur unter Windows und nur auf Deutsch — unter Linux gibt es ihn
schlicht nicht, und englische Clients bekommen von ihm gar nichts.

**Womit gearbeitet wird**

  * die `global.ini` des Spielers — gleich welcher Herkunft: die deutsche
    Übersetzung, StarStrings oder das Original aus dem `Data.p4k`
  * `katalog-cache.json` → welche Mission welche Baupläne gibt
  * `bestand.json` → was man selbst schon hat

Angehängt wird am **Textschlüssel** (`titleLocKey`, `descriptionLocKey`), und
der ist in jeder Sprache derselbe. Dieselbe Injektion greift deshalb für
Deutsch, Englisch und die neun weiteren Sprachen im Spiel.

**Zeilenformat der global.ini**

    SCHLUESSEL=Text mit \\n als Zeilenumbruch
    SCHLUESSEL,P=Text            (Zweitfassung, wird genauso behandelt)

Der Umbruch ist die **Zeichenfolge** `\\n`, kein echter Zeilenumbruch — eine
Zeile der Datei ist immer ein Eintrag. Wer hier ein echtes Newline einfügt,
zerreißt die Datei.

**Wiederholbar und rückgängig**

Alles Eingefügte steht zwischen zwei Marken. Vor dem Schreiben wird zuerst
alles zwischen den Marken entfernt — dadurch kann man beliebig oft injizieren,
ohne dass sich die Angaben stapeln, und `entfernen()` stellt den Ursprungstext
wieder her, ohne die Datei neu laden zu müssen.
"""
import json
import os
import re
import urllib.request

from . import fehler, bestand as bestand_datei
from . import katalog as katalog_modul
from . import pfade
from .sprache import t

# ---------------------------------------------------------------------------
# Zweite, bessere Datenquelle: das SCDL-Team veröffentlicht seine aufbereiteten
# Vertragsdaten offen im Übersetzungs-Repo — **813 Verträge** mit fertigen
# Texten, deutsch und englisch, samt Angaben, die scmdb so nicht hat (Region,
# Gefahrenstufe, Wartezeit in Worten). Aus scmdb allein kämen 349 zusammen.
#
# Die Arbeitsteilung, die sich daraus ergibt, ist die sinnvolle: Das SCDL-Team
# pflegt, was es ohnehin pflegt. Dieses Werkzeug steuert das bei, was nur es
# kann — das **Kästchen**, also den Abgleich mit dem eigenen Bauplan-Bestand.
# In den Rohdaten stehen die Baupläne neutral als „    - Name".
#
# Lizenz CC-BY-NC-SA-4.0: geholt wird zur Laufzeit von der Original-Adresse,
# nichts davon liegt in diesem Repo. Die Herkunft wird im eingefügten Text
# genannt.
SCDL_ROH = ('https://raw.githubusercontent.com/rjcncpt/'
            'StarCitizen-Deutsch-INI/master/blueprints/Data/%s')
SCDL_DATEI = {'de': 'bp-contracts_short.json',
              'en': 'bp-contracts_short_en.json'}
SCDL_CACHE = 'bp-contracts-%s.json'
BP_ZEILE = re.compile(r'^(\s*)- (.+)$')

# Die Marken. Bewusst unauffällig und ohne Sonderzeichen, damit sie das Spiel
# nicht stören, aber eindeutig genug, um sie sicher wiederzufinden.
AUF = '[SCBPW]'
ZU = '[/SCBPW]'
MARKE = re.compile(re.escape(AUF) + '.*?' + re.escape(ZU))

# Aufbau nach dem Vorbild des SC Deutsch Launchers — die **Gliederung** ist die
# nützliche Erkenntnis (was ein Spieler vor dem Annehmen wissen will), die
# Formulierungen sind eigene. Alle Angaben stammen aus scmdb.
TEXTE = {
    'de': {
        'kurz':      'BP',
        'ueberschr': 'BAUPLÄNE AUS DIESEM AUFTRAG',
        'chance':    'Chance auf Bauplan',
        'rep_min':   'Min. Reputation',
        'rep_max':   'Max. Reputation',
        'lohn':      'Belohnung',
        'ruf':       'Rufpunkte',
        'cooldown':  'Wartezeit',
        'minuten':   'Minuten',
        'teilbar':   'Mission teilbar',
        'ja':        'Ja', 'nein': 'Nein',
        'liste':     'Baupläne (%d von %d hast du)',
        'quelle':    'Angaben von scmdb.net · eingefügt vom SC BP Watcher',
        'trenner':   '.',
    },
    'en': {
        'kurz':      'BP',
        'ueberschr': 'BLUEPRINTS FROM THIS CONTRACT',
        'chance':    'Blueprint chance',
        'rep_min':   'Min. reputation',
        'rep_max':   'Max. reputation',
        'lohn':      'Payout',
        'ruf':       'Reputation gain',
        'cooldown':  'Cooldown',
        'minuten':   'minutes',
        'teilbar':   'Shareable',
        'ja':        'Yes', 'nein': 'No',
        'liste':     'Blueprints (you have %d of %d)',
        'quelle':    'Data from scmdb.net · added by SC BP Watcher',
        'trenner':   ',',
    },
}

# Kästchen wie beim Launcher: leer, wenn der Bauplan fehlt — hervorgehoben,
# wenn man ihn hat. Das Auge findet dadurch sofort, was noch offen ist.
KASTEN_HAB = '<EM4>[x]</EM4>'
KASTEN_FEHLT = '[  ]'
LINIE = '-' * 57


def _sprachkuerzel(sprache):
    """`german_(germany)` -> 'de', alles andere -> 'en'."""
    return 'de' if str(sprache).lower().startswith('german') else 'en'


def _zeile_zerlegen(zeile):
    """'SCHLUESSEL,P=Text' -> ('SCHLUESSEL', ',P', 'Text'). Sonst None."""
    trenner = zeile.find('=')
    if trenner < 1:
        return None
    kopf, text = zeile[:trenner], zeile[trenner + 1:]
    if ',' in kopf:
        schluessel, _, zusatz = kopf.partition(',')
        return schluessel, ',' + zusatz, text
    return kopf, '', text


def _saeubern(text):
    """Frühere Einfügungen entfernen — damit sich nichts stapelt.

    ⚠ Nur anfassen, wenn wirklich eine Marke drin war. Ein `rstrip()` auf jeder
    Zeile hätte auch Leerzeichen entfernt, die CIG **absichtlich** gesetzt hat
    (`ASD_FluffText_Eng_5,P=HIGH LEVELS OF\\nRADIATION DETECTED `). Beim ersten
    Vergleichslauf waren das über 3 KB stiller Textschaden an Stellen, mit denen
    dieses Werkzeug nichts zu tun hat."""
    if AUF not in text:
        return text
    return MARKE.sub('', text).rstrip()


def _zahl(wert, worte):
    """1234567 -> '1.234.567' bzw. '1,234,567' — je nach Sprache."""
    return format(int(wert), ',d').replace(',', worte['trenner'])


def _block(eintrag, habe, worte):
    """Der Textblock, der an die Beschreibung gehängt wird.

    Erst die Eckdaten als kurze Liste, dann die Baupläne mit Kästchen. Die
    Reihenfolge ist Absicht: Ob sich der Auftrag überhaupt lohnt, entscheidet
    man an Chance und Reputation — die Namensliste liest man erst danach."""
    meine = sum(1 for n in eintrag['bp'] if katalog_modul._norm(n) in habe)
    z = ['', LINIE, '', '<EM4>%s</EM4>' % worte['ueberschr'], '']

    chance = eintrag.get('chance')
    if chance:
        z.append('# %s: %d%%' % (worte['chance'], round(chance * 100)))
    if eintrag.get('rang'):
        z.append('# %s: %s (%s XP)' % (worte['rep_min'], eintrag['rang'],
                                       _zahl(eintrag.get('rep') or 0, worte)))
    if eintrag.get('rang_max'):
        z.append('# %s: %s (%s XP)' % (worte['rep_max'], eintrag['rang_max'],
                                       _zahl(eintrag.get('rep_max') or 0, worte)))
    if eintrag.get('uec'):
        z.append('# %s: %s aUEC' % (worte['lohn'], _zahl(eintrag['uec'], worte)))
    if eintrag.get('ruf'):
        z.append('# %s: %s XP' % (worte['ruf'], _zahl(eintrag['ruf'], worte)))
    if eintrag.get('cooldown'):
        z.append('# %s: %s %s' % (worte['cooldown'],
                                  _zahl(eintrag['cooldown'], worte),
                                  worte['minuten']))
    if 'teilbar' in eintrag:
        z.append('# %s: %s' % (worte['teilbar'],
                               worte['ja'] if eintrag['teilbar'] else worte['nein']))

    z += ['', '# ' + (worte['liste'] % (meine, len(eintrag['bp']))) + ':']
    for name in eintrag['bp']:
        drin = katalog_modul._norm(name) in habe
        z.append('   %s %s' % (KASTEN_HAB if drin else KASTEN_FEHLT, name))
    z += ['', worte['quelle']]
    return AUF + '\\n' + '\\n'.join(z) + ZU


def _titel_zusatz(eintrag, habe, worte):
    """Kürzel für die Auftragsliste: sieht man, ohne aufzuklappen."""
    meine = sum(1 for n in eintrag['bp'] if katalog_modul._norm(n) in habe)
    return '%s <EM4>[%s %d/%d]</EM4>%s' % (AUF, worte['kurz'], meine,
                                           len(eintrag['bp']), ZU)


def scdl_holen(sprachkuerzel, fortschritt=None):
    """Die Vertragsdaten des SCDL-Teams holen und ablegen. (Erfolg, Anzahl)."""
    datei = SCDL_DATEI.get(sprachkuerzel)
    if not datei:
        return False, 0
    try:
        if fortschritt:
            fortschritt('Bauplan-Daten werden geladen …')
        req = urllib.request.Request(
            SCDL_ROH % datei,
            headers={'User-Agent': 'SC-BP-Watcher'})
        with urllib.request.urlopen(req, timeout=60) as r:
            roh = json.loads(r.read().decode('utf-8'))
        eintraege = roh.get('entries') or []
        if not eintraege:
            return False, 0
        ziel = pfade.app_datei(SCDL_CACHE % sprachkuerzel)
        with open(ziel + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(roh, f, ensure_ascii=False)
        os.replace(ziel + '.tmp', ziel)
        return True, len(eintraege)
    except Exception:
        return False, 0


def scdl_laden(sprachkuerzel):
    """Die abgelegten Vertragsdaten — oder None."""
    try:
        with open(pfade.app_datei(SCDL_CACHE % sprachkuerzel),
                  encoding='utf-8') as f:
            roh = json.load(f)
        return roh if roh.get('entries') else None
    except Exception:
        return None


def _kaestchen_setzen(text, habe):
    """In einem fertigen SCDL-Block die Bauplan-Zeilen ankreuzen.

    Aus `    - Atzkav Sniper Rifle` wird `    [x] Atzkav Sniper Rifle`, wenn er
    im Bestand liegt — sonst `    [  ] …`. Der übrige Text bleibt unangetastet;
    er gehört dem SCDL-Team, wir hängen nur das Häkchen dran.

    Gezählt wird nebenbei, damit das Titel-Kürzel dieselbe Zahl zeigt."""
    zeilen = text.split('\\n')
    meine = gesamt = 0
    for i, zeile in enumerate(zeilen):
        m = BP_ZEILE.match(zeile)
        if not m:
            continue
        einzug, name = m.group(1), m.group(2).strip()
        if name.startswith('#') or not name:
            continue
        gesamt += 1
        drin = katalog_modul._norm(name) in habe
        if drin:
            meine += 1
        zeilen[i] = '%s%s %s' % (einzug, KASTEN_HAB if drin else KASTEN_FEHLT, name)
    return '\\n'.join(zeilen), meine, gesamt


def _stamm(schluessel):
    """Der Namensanfang, den Titel und Beschreibungen eines Auftrags teilen.

    Aus `Covalex_HaulCargo_AToB_title` und `Covalex_HaulCargo_AtoB_desc_ToRuinStation`
    wird beide Male `covalex_haulcargo_atob`. Alles ab `_title` bzw. `_desc` fällt
    weg, der Rest wird kleingeschrieben — in den Spieldaten wechselt die
    Schreibweise mitten im Wort.
    """
    klein = (schluessel or '').lower()
    for trenner in ('_title', '_desc'):
        stelle = klein.find(trenner)
        if stelle > 0:
            return klein[:stelle]
    return ''


def einspielen_scdl(ini_pfad, sprachkuerzel, bestand=None):
    """Injektion aus den SCDL-Vertragsdaten — der vollständigere Weg.

    Gibt (Erfolg, Anzahl, Meldung) zurück wie `einspielen()`."""
    daten = scdl_laden(sprachkuerzel)
    if not daten:
        return False, 0, t('m_keine_scdl')
    if not ini_pfad or not os.path.isfile(ini_pfad):
        return False, 0, t('m_keine_ini')

    habe = bestand_datei.schluessel(bestand if bestand is not None
                                    else bestand_datei.laden())
    worte = TEXTE[sprachkuerzel]

    titel_an, text_an = {}, {}
    for e in daten['entries']:
        block = e.get('description') or ''
        if not block:
            continue
        block, meine, gesamt = _kaestchen_setzen(block, habe)
        if e.get('descriptionLocKey'):
            text_an[e['descriptionLocKey']] = block
        if e.get('titleLocKey'):
            # Statt des schlichten [BP] die eigene Zählung — das ist der
            # Mehrwert gegenüber der reinen Fremdfassung.
            titel_an[e['titleLocKey']] = (' <EM4>[%s %d/%d]</EM4>'
                                          % (worte['kurz'], meine, gesamt))

    geaendert = 0
    try:
        with open(ini_pfad, encoding='utf-8', errors='ignore') as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return False, 0, 'Lesen fehlgeschlagen: %s' % e

    # ⚠ Ein Auftrag hat EINEN Titel, aber oft ein Dutzend Beschreibungen: je eine
    # für „zur Ruinenstation", „zum Verteilzentrum", „von A nach B" und so weiter.
    # Die Vertragsdaten nennen dazu immer nur **eine** — die übrigen blieben leer.
    # Im Spiel stand dann im Titel „[BP 0/12]", und wer die Beschreibung öffnete,
    # um zu sehen *welche* zwölf, fand nichts. Genau so gemeldet.
    #
    # Gemessen an einer echten Installation: allein bei Covalex 51 Beschreibungen im
    # Spiel, davon 7 mit Angaben.
    #
    # Deshalb ein zweiter Weg über den gemeinsamen Namensanfang: Zu jedem Titel,
    # der Angaben bekommt, werden alle Beschreibungen desselben Auftrags mit
    # demselben Block versehen. Groß- und Kleinschreibung zählt dabei nicht —
    # in den Spieldaten steht `Covalex_HaulCargo_AToB_title` neben
    # `Covalex_HaulCargo_AtoB_desc_ToRuinStation`, mit unterschiedlichem „to".
    stamm_an = {}
    for e in daten['entries']:
        block = text_an.get(e.get('descriptionLocKey') or '')
        stamm = _stamm(e.get('titleLocKey') or e.get('descriptionLocKey') or '')
        if block and stamm and stamm not in stamm_an:
            stamm_an[stamm] = block

    neu = []
    for zeile in zeilen:
        teile = _zeile_zerlegen(zeile)
        if not teile:
            neu.append(zeile)
            continue
        schluessel, zusatz, text = teile
        sauber = _saeubern(text)
        if schluessel in titel_an:
            sauber += AUF + titel_an[schluessel] + ZU
            geaendert += 1
        elif schluessel in text_an:
            sauber += AUF + text_an[schluessel] + ZU
            geaendert += 1
        elif '_desc' in schluessel.lower():
            # Keine eigene Angabe — aber vielleicht gehört die Beschreibung zu
            # einem Auftrag, für den wir welche haben.
            block = stamm_an.get(_stamm(schluessel))
            if block:
                sauber += AUF + block + ZU
                geaendert += 1
        neu.append('%s%s=%s' % (schluessel, zusatz, sauber))

    try:
        with open(ini_pfad + '.tmp', 'w', encoding='utf-8') as f:
            f.write('\n'.join(neu) + '\n')
        os.replace(ini_pfad + '.tmp', ini_pfad)
    except OSError as e:
        return False, 0, 'Schreiben fehlgeschlagen: %s' % e
    meta = daten.get('_meta') or {}
    return True, geaendert, '%d Textstellen (SCDL %s)' % (geaendert,
                                                          meta.get('version', '?'))


def einspielen(ini_pfad, sprache, katalog=None, bestand=None, nur_entfernen=False):
    """Die Angaben in eine `global.ini` schreiben.

    Gibt (Erfolg, Anzahl geänderter Zeilen, Meldung) zurück. Die Datei wird
    erst vollständig neu geschrieben und dann umbenannt — bricht etwas ab,
    bleibt die alte Fassung unversehrt."""
    if not ini_pfad or not os.path.isfile(ini_pfad):
        return False, 0, t('m_keine_ini')

    katalog = katalog if katalog is not None else katalog_modul.laden()
    missionen = katalog.get('missionen') or {}
    if not missionen and not nur_entfernen:
        return False, 0, t('m_keine_missionen')

    habe = bestand_datei.schluessel(bestand if bestand is not None
                                    else bestand_datei.laden())
    worte = TEXTE[_sprachkuerzel(sprache)]

    # Beide Schlüssel-Arten in eine Tabelle: Titel bekommen das Kürzel,
    # Beschreibungen die Liste.
    titel_keys, text_keys = {}, {}
    for eintrag in missionen.values():
        if eintrag.get('titel_key'):
            titel_keys[eintrag['titel_key']] = eintrag
        if eintrag.get('text_key'):
            text_keys[eintrag['text_key']] = eintrag

    geaendert = 0
    try:
        with open(ini_pfad, encoding='utf-8', errors='ignore') as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return False, 0, 'Lesen fehlgeschlagen: %s' % e

    neu = []
    for zeile in zeilen:
        teile = _zeile_zerlegen(zeile)
        if not teile:
            neu.append(zeile)
            continue
        schluessel, zusatz, text = teile
        sauber = _saeubern(text)
        if sauber != text:
            geaendert += 1
        if not nur_entfernen:
            if schluessel in titel_keys:
                sauber += _titel_zusatz(titel_keys[schluessel], habe, worte)
                geaendert += 1
            elif schluessel in text_keys:
                sauber += _block(text_keys[schluessel], habe, worte)
                geaendert += 1
        neu.append('%s%s=%s' % (schluessel, zusatz, sauber))

    try:
        with open(ini_pfad + '.tmp', 'w', encoding='utf-8') as f:
            f.write('\n'.join(neu) + '\n')
        os.replace(ini_pfad + '.tmp', ini_pfad)
    except OSError as e:
        return False, 0, 'Schreiben fehlgeschlagen: %s' % e

    return True, geaendert, '%d Textstellen' % geaendert


def einrichten(ini_pfad, sprache, fortschritt=None, bestand=None):
    """Die Bauplan-Angaben eintragen — auf dem jeweils besten Weg.

    Zuerst die Vertragsdaten des SCDL-Teams: 813 Verträge mit gepflegten
    Texten. Sind sie nicht erreichbar, tut es der eigene Aufbau aus den
    scmdb-Daten (349 Verträge) — dann fehlen Feinheiten wie Region und
    Gefahrenstufe, aber die Baupläne stehen da, und darum geht es."""
    kuerzel = _sprachkuerzel(sprache)
    if not scdl_laden(kuerzel):
        scdl_holen(kuerzel, fortschritt)
    if scdl_laden(kuerzel):
        ok, n, meldung = einspielen_scdl(ini_pfad, kuerzel, bestand)
        if ok:
            return ok, n, meldung
    return einspielen(ini_pfad, sprache, bestand=bestand)


def aktualisieren(ini_pfad, sprache, fortschritt=None, bestand=None):
    """Frische Vertragsdaten holen und neu eintragen.

    Gebraucht nach jedem Übersetzungs-Update und nach jedem Spiel-Patch: Beide
    schreiben die `global.ini` neu, die Angaben sind dann stillschweigend weg."""
    scdl_holen(_sprachkuerzel(sprache), fortschritt)
    return einrichten(ini_pfad, sprache, fortschritt, bestand)


def scdl_update_da(sprachkuerzel):
    """Gibt es bei den Vertragsdaten etwas Neueres? (ja/nein, neue Kennung).

    Verglichen wird die Kennung aus `_meta.version` (z. B. „LIVE 20.08.2026").
    Geholt wird dafür die ganze Datei — sie hat keine eigene Versionsauskunft,
    und 2,4 MB einmal am Tag sind kein Grund, dafür etwas zu bauen."""
    alt = scdl_stand(sprachkuerzel)
    datei = SCDL_DATEI.get(sprachkuerzel)
    if not datei:
        return False, None
    try:
        req = urllib.request.Request(SCDL_ROH % datei,
                                     headers={'User-Agent': 'SC-BP-Watcher'})
        with urllib.request.urlopen(req, timeout=60) as r:
            roh = json.loads(r.read().decode('utf-8'))
    except Exception as ausnahme:
        fehler.merken('injektion.scdl_holen', ausnahme, datei)
        return False, None
    neu_kennung = (roh.get('_meta') or {}).get('version')
    if not roh.get('entries') or neu_kennung == alt:
        return False, alt
    # Schon mal ablegen — der Abruf ist gelaufen, ein zweiter wäre Verschwendung.
    try:
        ziel = pfade.app_datei(SCDL_CACHE % sprachkuerzel)
        with open(ziel + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(roh, f, ensure_ascii=False)
        os.replace(ziel + '.tmp', ziel)
    except Exception:
        return False, alt
    return True, neu_kennung


def scdl_stand(sprachkuerzel):
    """Welche Fassung der Vertragsdaten liegt hier? Oder None."""
    d = scdl_laden(sprachkuerzel)
    return (d.get('_meta') or {}).get('version') if d else None


def entfernen(ini_pfad, sprache='english'):
    """Alle Einfügungen zurücknehmen — die Datei bleibt sonst unverändert."""
    return einspielen(ini_pfad, sprache, nur_entfernen=True)


def ist_drin(ini_pfad):
    """Steckt in dieser Datei schon eine Injektion?"""
    try:
        with open(ini_pfad, encoding='utf-8', errors='ignore') as f:
            for zeile in f:
                if AUF in zeile:
                    return True
    except OSError:
        pass
    return False
