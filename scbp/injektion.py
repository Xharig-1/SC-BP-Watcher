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
import time
import urllib.request

from . import angaben as angaben_modul
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

# Wie eine Einfügung **ohne** Marke aussieht — der Notnagel beim Entfernen.
#
# Beide Formen sind eindeutig genug: Der Titelzusatz ist ` <EM4>[BP 3/6]</EM4>`,
# der Textblock beginnt mit einer Zeile aus lauter Bindestrichen. So etwas steht
# in keinem Text von CIG. Gesucht wird ab der **letzten** Fundstelle, damit ein
# doppelt eingetragener Block ganz verschwindet und nicht nur zur Hälfte.
# Der Titelzusatz allein — daran erkennt `ist_drin`, dass schon etwas drinsteht.
# ⚠ Das `!?` muss mit: Seit dem Rufzeichen für eingeschränkte Aufträge heißt
# der Zusatz auch `[BP 0/19!]`. Ohne das bliebe er beim Zurücksetzen stehen —
# und zwar genau bei den 332 Aufträgen, die eine Einschränkung haben.
TITELZUSATZ = re.compile(r'<EM4>\[(?:BP|Bauplan)\s+\d+/\d+!?\]</EM4>')

# ⚠ Beim ersten Anlauf stand hier „ab der Bindestrich-Linie alles weg". Das ging
# schief: CIG benutzt solche Linien **selbst** als Gliederung. Im Test auf einer
# Kopie verlor `Battaglia_RPT_BoardShip_01_desc` dadurch 589 seiner 870 Zeichen —
# der ganze Abschnitt „GENEHMIGUNG: Battaglia, Recco" wäre stillschweigend
# verschwunden. Genau die Sorte Schaden, die niemand bemerkt, bis der Text im
# Spiel fehlt.
#
# Geschnitten wird deshalb nur, wenn nach der Linie auch eine **unserer**
# Überschriften steht — die eigene und die der SCDL-Vertragsdaten, je zweisprachig.
#
# ⚠ Es sind **vier** Formen, nicht zwei. Die Vertragsdaten kennen neben der
# Bauplan-Liste noch einen zweiten Blocktyp: den Hinweis „Dieser Missionstyp wird
# vom Spiel dynamisch erzeugt" (84 der 363 Blöcke). Im Test ohne Merkdatei blieben
# genau diese 90 Zeilen halb stehen — der Anfang war weg, der Rest stand noch da.
# Gezählt, nicht geraten: 279 + 84 je Sprache.
_UEBERSCHRIFTEN = (
    'BAUPLÄNE AUS DIESEM AUFTRAG', 'BLUEPRINTS FROM THIS CONTRACT',
    'MÖGLICHE BAUPLÄNE FÜR DIESEN MISSIONSTYP',
    'POSSIBLE BLUEPRINTS FOR THIS MISSION TYPE',
    '<EM4>Dieser Missionstyp wird vom Spiel dynamisch erzeugt',
    '<EM4>This mission type is dynamically generated by the game',
)
OHNE_MARKE = re.compile(
    r'(?:\s*<EM4>\[(?:BP|Bauplan)\s+\d+/\d+!?\]</EM4>\s*$'
    # ⚠ Höchstens **zwei** Umbrüche vor der Linie schlucken, nicht beliebig viele.
    # So viele bringt unser Block selbst mit; alles darüber gehört zu CIGs Text.
    # Mit `*` fehlten am Ende zweier Aufträge je zwei Zeichen — winzig, aber es ist
    # fremder Text, den wir nicht anfassen dürfen.
    # ⚠ Bekannte Ungenauigkeit, gemessen an der echten Datei: Bei **2 von 743**
    # Aufträgen bleibt am Ende ein Umbruch zu wenig stehen, weil CIGs Text selbst
    # mit einem endet und unserer mit einem beginnt — auseinanderhalten lassen die
    # sich nicht. Das betrifft nur diesen Notnagel; der reguläre Weg über die
    # Merkdatei stellt den Wortlaut **auf das Zeichen genau** wieder her (geprüft).
    # Zwei fehlende Umbrüche in zwei Auftragstexten sind der Preis dafür, dass
    # Aufräumen auch ohne Merkdatei funktioniert.
    r'|(?:\\n){1,2}?\s*-{20,}(?:\\n|\s)*(?:%s).*$)'
    % '|'.join(re.escape(u) for u in _UEBERSCHRIFTEN), re.S)

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


# Wo die Originaltexte liegen, bevor etwas eingefügt wird.
#
# ⚠ Warum es diese Datei gibt: Bis v3.0.0 stand um jede Einfügung ein Marken-Paar
# `[SCBPW] … [/SCBPW]`, damit sie sich auf den Buchstaben genau wieder entfernen
# lässt. Das funktionierte — nur **sieht man die Marken im Spiel**. Im
# Auftragstitel stand „Security Patrol[SCBPW] [BP 3/6][/SCBPW]", und das ist
# nichts, was jemand in seinem Spiel haben will.
#
# Der Ausweg ist nicht ein unsichtbareres Zeichen — was die Spiel-Engine mit
# unbekannten Zeichen macht, weiß man erst, wenn es zu spät ist. Stattdessen wird
# der **Originaltext** jeder angefassten Zeile hier festgehalten. Damit braucht es
# im Spieltext gar keine Marke mehr, und das Zurücksetzen ist genauer als vorher:
# Es stellt den Wortlaut wieder her, statt eine Einfügung herauszuschneiden.
URTEXT_DATEI = 'injektion-urtext.json'


def urtext_laden():
    """Die gemerkten Originaltexte — leer, wenn es noch keine gibt."""
    try:
        with open(pfade.app_datei(URTEXT_DATEI), encoding='utf-8') as f:
            daten = json.load(f)
        return daten.get('texte') or {}
    except Exception:
        return {}


def urtext_sichern(texte, ini_pfad):
    """Die Originaltexte festhalten. Fehlschlag ist kein Grund abzubrechen."""
    try:
        ziel = pfade.app_datei(URTEXT_DATEI)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, 'w', encoding='utf-8') as f:
            json.dump({'datei': ini_pfad, 'stand': time.strftime('%Y-%m-%d %H:%M:%S'),
                       'texte': texte}, f, ensure_ascii=False)
        return True
    except Exception as ausnahme:
        fehler.merken('injektion.urtext_sichern', ausnahme)
        return False


def _saeubern(text, schluessel='', urtext=None):
    """Frühere Einfügungen entfernen — damit sich nichts stapelt.

    Drei Wege, in dieser Reihenfolge:

      1. **Der gemerkte Originaltext.** Der genaueste: Er stellt den Wortlaut
         wieder her, statt etwas herauszuschneiden.
      2. **Das alte Marken-Paar.** Für alles, was frühere Versionen eingetragen
         haben — die stehen ja noch in der Datei von jemandem, der aktualisiert.
      3. **Der eingefügte Block an seiner Form erkannt.** Der Notnagel, wenn die
         Merkdatei fehlt (anderer Rechner, aufgeräumt) und keine Marke dasteht.

    ⚠ Nur anfassen, wenn wirklich etwas gefunden wurde. Ein `rstrip()` auf jeder
    Zeile hätte auch Leerzeichen entfernt, die CIG **absichtlich** gesetzt hat
    (`ASD_FluffText_Eng_5,P=HIGH LEVELS OF\\nRADIATION DETECTED `). Beim ersten
    Vergleichslauf waren das über 3 KB stiller Textschaden an Stellen, mit denen
    dieses Werkzeug nichts zu tun hat."""
    if urtext and schluessel in urtext:
        return urtext[schluessel]
    if AUF in text:
        return MARKE.sub('', text).rstrip()
    treffer = OHNE_MARKE.search(text)
    if treffer:
        return text[:treffer.start()].rstrip()
    return text


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
    # Ohne Marken — sie standen sichtbar im Spiel. Zurückgesetzt wird über die
    # gemerkten Originaltexte (siehe `URTEXT_DATEI`).
    return '\\n' + '\\n'.join(z)


def _titel_zusatz(eintrag, habe, worte):
    """Kürzel für die Auftragsliste: sieht man, ohne aufzuklappen."""
    meine = sum(1 for n in eintrag['bp'] if katalog_modul._norm(n) in habe)
    return ' <EM4>[%s %d/%d]</EM4>' % (worte['kurz'], meine, len(eintrag['bp']))


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


# Name der Einstellung, mit der sich die Angaben am Gegenstand abschalten
# lassen. Standard ist **an**: Wer die Injektion einschaltet, will Angaben im
# Spiel sehen — und genau dafür ist dieses Werkzeug da.
EINSTELLUNG_ANGABEN = 'angaben_am_gegenstand'


def _namens_tabelle(zeilen, nur_entfernen=False):
    """Tabelle *Namensschlüssel → Kürzel* — oder leer, wenn abgeschaltet.

    Beim reinen Entfernen bleibt sie leer: Dann stellt der Urtext-Weg die
    ursprünglichen Namen wieder her, und es soll nichts Neues dazukommen."""
    if nur_entfernen or not pfade.einstellung_wahrheit(EINSTELLUNG_ANGABEN, True):
        return {}
    try:
        return angaben_modul.tabelle_bauen(zeilen)
    except Exception as ausnahme:
        fehler.merken('injektion._namens_tabelle', ausnahme)
        return {}


def _name_mit_angabe(text, kuerzel):
    """Den Zusatz an einen Namen hängen — vorhandene Klammer vorher abschneiden.

    Der SC Deutsch Launcher hängt seinerseits `(CS1)` an. Ohne das Abschneiden
    stünde danach `Spark I-G Missile (CS1) (IR1)` im Spiel."""
    return '%s %s' % (angaben_modul.zusatz_entfernen(text).rstrip(), kuerzel)


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
            #
            # ⚠ Und ein **Rufzeichen**, wenn die Baupläne an Bedingungen hängen.
            # Gemessen an den Vertragsdaten: **332 von 818** Aufträgen (41 %)
            # geben ihre Baupläne nur in bestimmten Preisstufen oder ab einem
            # Rang — „Baupläne nur für 256.500 / 264.000 aUEC Mission", „nur ab
            # Meister-Rang". Das steht zwar im Beschreibungstext, aber in der
            # **Auftragsliste** sah man bisher nur `[BP 0/19]`, und genau danach
            # entscheidet man, ob man annimmt.
            #
            # Morkhan am 28.08.2026 genau so hereingefallen: Auftrag angenommen
            # (Neuling, 49.750 aUEC), Bauplan-Zähler im Titel gesehen — geben
            # konnte die Stufe nie einen. Ein Zeichen im Titel kostet nichts und
            # erspart die vergebliche Mission.
            zeichen = '!' if (e.get('bpnote') or '').strip() else ''
            titel_an[e['titleLocKey']] = (' <EM4>[%s %d/%d%s]</EM4>'
                                          % (worte['kurz'], meine, gesamt,
                                             zeichen))

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

    # ⚠ Ohne Marken im Text: Was hier angefasst wird, kommt vorher in die
    # Merkdatei. Siehe `URTEXT_DATEI` — die Marken waren im Spiel sichtbar.
    urtext_alt = urtext_laden()
    urtext_neu = {}
    namens_zusatz = _namens_tabelle(zeilen)

    neu = []
    for zeile in zeilen:
        teile = _zeile_zerlegen(zeile)
        if not teile:
            neu.append(zeile)
            continue
        schluessel, zusatz, text = teile
        sauber = _saeubern(text, schluessel, urtext_alt)
        angefasst = False
        if schluessel in namens_zusatz:
            sauber = _name_mit_angabe(sauber, namens_zusatz[schluessel])
            angefasst = True
        elif schluessel in titel_an:
            sauber, angefasst = sauber + titel_an[schluessel], True
        elif schluessel in text_an:
            sauber, angefasst = sauber + text_an[schluessel], True
        elif '_desc' in schluessel.lower():
            # Keine eigene Angabe — aber vielleicht gehört die Beschreibung zu
            # einem Auftrag, für den wir welche haben.
            block = stamm_an.get(_stamm(schluessel))
            if block:
                sauber, angefasst = sauber + block, True
        if angefasst:
            # Den Wortlaut VOR der Einfügung merken, nicht danach.
            urtext_neu[schluessel] = _saeubern(text, schluessel, urtext_alt)
            geaendert += 1
        neu.append('%s%s=%s' % (schluessel, zusatz, sauber))

    try:
        with open(ini_pfad + '.tmp', 'w', encoding='utf-8') as f:
            f.write('\n'.join(neu) + '\n')
        os.replace(ini_pfad + '.tmp', ini_pfad)
    except OSError as e:
        return False, 0, 'Schreiben fehlgeschlagen: %s' % e
    urtext_sichern(urtext_neu, ini_pfad)
    meta = daten.get('_meta') or {}
    return True, geaendert, '%d Textstellen (SCDL %s)' % (geaendert,
                                                          meta.get('version', '?'))


def einspielen(ini_pfad, sprache, katalog=None, bestand=None, nur_entfernen=False):
    """Die Angaben in eine `global.ini` schreiben.

    Gibt (Erfolg, Anzahl geänderter Zeilen, Meldung) zurück. Die Datei wird
    erst vollständig neu geschrieben und dann umbenannt — bricht etwas ab,
    bleibt die alte Version unversehrt."""
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

    urtext_alt = urtext_laden()
    urtext_neu = {}
    namens_zusatz = _namens_tabelle(zeilen, nur_entfernen)

    # ⚠ Eine Mission hat im Spiel **mehr** Beschreibungen, als der Katalog
    # kennt. Gemessen am 28.08.2026: `Covalex_HaulCargo_SingleToMulti` führt
    # drei Beschreibungs-Schlüssel, in der `global.ini` stehen **acht** —
    # verschiedene Zielorte und Waren derselben Mission. Wer eine der fünf
    # übrigen erwischt, sah `[BP 0/12]` im Titel und darunter **nichts**.
    #
    # Genau so gemeldet von Morkhan: „bei ner anderen mission steht, dass man
    # 12 Pläne bekommen kann, aber da werden keine angezeigt."
    #
    # `einspielen_scdl()` löst das seit Langem über den gemeinsamen
    # Namensanfang; hier fehlte es. Deshalb derselbe Weg auch für den eigenen
    # Katalog: Zu jedem Titel, der Angaben bekommt, bekommen **alle**
    # Beschreibungen desselben Auftrags denselben Block.
    stamm_block = {}
    if not nur_entfernen:
        for eintrag in missionen.values():
            stamm = _stamm(eintrag.get('titel_key')
                           or eintrag.get('text_key') or '')
            if stamm and stamm not in stamm_block:
                stamm_block[stamm] = eintrag

    neu = []
    for zeile in zeilen:
        teile = _zeile_zerlegen(zeile)
        if not teile:
            neu.append(zeile)
            continue
        schluessel, zusatz, text = teile
        sauber = _saeubern(text, schluessel, urtext_alt)
        if sauber != text:
            geaendert += 1
        if not nur_entfernen:
            vorher = sauber
            angefasst = False
            if schluessel in namens_zusatz:
                sauber = _name_mit_angabe(vorher, namens_zusatz[schluessel])
                angefasst = True
            elif schluessel in titel_keys:
                sauber = vorher + _titel_zusatz(titel_keys[schluessel], habe, worte)
                angefasst = True
            elif schluessel in text_keys:
                sauber = vorher + _block(text_keys[schluessel], habe, worte)
                angefasst = True
            elif '_desc' in schluessel.lower():
                # Keine eigene Angabe — aber vielleicht gehört die Beschreibung
                # zu einem Auftrag, für den wir welche haben (siehe oben).
                eintrag = stamm_block.get(_stamm(schluessel))
                if eintrag:
                    sauber = vorher + _block(eintrag, habe, worte)
                    angefasst = True
            if angefasst:
                urtext_neu[schluessel] = vorher
                geaendert += 1
        neu.append('%s%s=%s' % (schluessel, zusatz, sauber))

    try:
        with open(ini_pfad + '.tmp', 'w', encoding='utf-8') as f:
            f.write('\n'.join(neu) + '\n')
        os.replace(ini_pfad + '.tmp', ini_pfad)
    except OSError as e:
        return False, 0, 'Schreiben fehlgeschlagen: %s' % e
    # Beim reinen Entfernen ist nichts mehr zu merken — die Datei wird geleert,
    # damit ein späterer Lauf nicht auf einen überholten Stand zurücksetzt.
    urtext_sichern(urtext_neu, ini_pfad)

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
    """Welche Version der Vertragsdaten liegt hier? Oder None."""
    d = scdl_laden(sprachkuerzel)
    return (d.get('_meta') or {}).get('version') if d else None


def entfernen(ini_pfad, sprache='english'):
    """Alle Einfügungen zurücknehmen — die Datei bleibt sonst unverändert."""
    return einspielen(ini_pfad, sprache, nur_entfernen=True)


def ist_drin(ini_pfad):
    """Steckt in dieser Datei schon eine Injektion?

    Seit v3.0.0 stehen keine Marken mehr im Text (sie waren im Spiel sichtbar),
    also wird nach der **Form** der Einfügung gesucht: dem Titelzusatz
    `<EM4>[BP 3/6]</EM4>`. Die alte Marke gilt weiter — in der Datei von jemandem,
    der von einer früheren Version kommt, steht sie noch.

    Nur die ersten Zeilen zu lesen genügt nicht: Die Auftragstexte liegen mitten
    in einer Datei mit über hunderttausend Zeilen.
    """
    try:
        with open(ini_pfad, encoding='utf-8', errors='ignore') as f:
            for zeile in f:
                if AUF in zeile or TITELZUSATZ.search(zeile):
                    return True
    except OSError:
        pass
    return False
