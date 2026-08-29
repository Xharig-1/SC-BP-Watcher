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
Zwei Ebenen statt einer langen Liste — Oberkategorie und Unterart.

**Das Problem, das dieses Modul löst.** Die Art-Auswahl hatte dreissig Einträge:
`Rüstung (Arme)`, `Rüstung (Beine)`, `Rüstung (Torso)`, `Helm`, `Rucksack`,
`Unteranzug`, `Kleidung (Jacke)`, `Kleidung (Schuhe)` … Wer eine ganze Rüstung
zusammenstellen will, sucht sich darin einen Wolf — und bei `Schiffswaffe (87)`
stand alles zusammen, ohne dass man sah, was davon ballistisch ist und was
Laser. Am 29.08.2026 gemeldet: *„da gibt es aber viele, und ich weiß grad nicht,
welche Ballistik sind, welche Laser, welche Repeater oder Cannon."*

**Die Gliederung ist nicht erfunden.** Sie folgt der Liste, die Xharig-1 seit
Monaten von Hand in seiner Vault pflegt (`Blueprint-Alle.md`): sieben
Oberkategorien, darunter die feinen Arten. Was sich dort bewährt hat, muss das
Werkzeug nicht neu erfinden.

**Woher die Angaben kommen** — drei Quellen, in dieser Reihenfolge:

1. **Der Tag der Rezeptdaten** ist am genauesten. `BP_CRAFT_APAR_BallisticGatling_S4`
   nennt die Waffenart direkt; so unterscheidet auch das Vault-Skript
   Ballistic Cannon von Ballistic Gatling. Gemessen: 89 Schiffswaffen und
   Werkzeuge tragen sie.
2. **Die Katalog-Art** (`Char_Armor_Helmet`, `Cooler`) für alles, was
   Körperteile oder Bauteilart meint.
3. **Der Rezept-Untertyp** (`pistol`, `sniper`, `shotgun`) für FPS-Waffen.

Was in keine Kategorie fällt, landet unter „Sonstiges" — sichtbar, nicht
verschwunden.
"""
import re

from .sprache import t

# --- Die feinen Arten, wie sie im Tag der Rezeptdaten stehen ---------------
# ⚠ Reihenfolge egal, aber die Schreibweise muss zum Tag passen; verglichen
# wird ohne Rücksicht auf Gross- und Kleinschreibung.
_TAG_ARTEN = (
    # ⚠ Die zusammengesetzten zuerst: `BallisticScatterGun` muss vor
    # `ScatterGun` stehen, sonst schluckt das kürzere Wort den Treffer und
    # sechs von sieben Scatterguns fielen durch — gemessen am 29.08.2026.
    'BallisticScatterGun', 'LaserScatterGun',
    'BallisticCannon', 'BallisticGatling', 'BallisticRepeater',
    'LaserCannon', 'LaserRepeater',
    'DistortionCannon', 'DistortionRepeater',
    'NeutronCannon', 'NeutronRepeater',
    'TachyonCannon', 'ScatterGun', 'MassDriver',
    'MiningLaser', 'SalvageModifier', 'SalvageHead', 'TractorBeam',
)
_TAG_MUSTER = re.compile(r'_(%s)(?:_|$)' % '|'.join(_TAG_ARTEN), re.I)

# --- Oberkategorie je feiner Art ------------------------------------------
# Die sieben Gruppen aus `Blueprint-Alle.md`.
SCHIFFSWAFFE = 'schiffswaffe'
SCHIFFSMODUL = 'schiffsmodul'
SCHIFFSWERKZEUG = 'schiffswerkzeug'
FPS_WAFFE = 'fpswaffe'
AUSRUESTUNG = 'ausruestung'
RUESTUNG = 'ruestung'
KLEIDUNG = 'kleidung'
SONSTIGES = 'sonstiges'

# Reihenfolge im Auswahlfeld — dieselbe wie in der Vault-Notiz.
OBER_REIHE = (SCHIFFSWAFFE, SCHIFFSMODUL, SCHIFFSWERKZEUG, FPS_WAFFE,
              AUSRUESTUNG, RUESTUNG, KLEIDUNG, SONSTIGES)

_AUS_TAG = {
    'ballisticcannon': (SCHIFFSWAFFE, 'ballistic_cannon'),
    'ballisticgatling': (SCHIFFSWAFFE, 'ballistic_gatling'),
    'ballisticrepeater': (SCHIFFSWAFFE, 'ballistic_repeater'),
    'lasercannon': (SCHIFFSWAFFE, 'laser_cannon'),
    'laserrepeater': (SCHIFFSWAFFE, 'laser_repeater'),
    'distortioncannon': (SCHIFFSWAFFE, 'dist_cannon'),
    'distortionrepeater': (SCHIFFSWAFFE, 'dist_repeater'),
    'neutroncannon': (SCHIFFSWAFFE, 'neutron_cannon'),
    'neutronrepeater': (SCHIFFSWAFFE, 'neutron_repeater'),
    'tachyoncannon': (SCHIFFSWAFFE, 'tachyon_cannon'),
    'scattergun': (SCHIFFSWAFFE, 'scatter_gun'),
    'ballisticscattergun': (SCHIFFSWAFFE, 'scatter_gun'),
    'laserscattergun': (SCHIFFSWAFFE, 'scatter_gun'),
    'massdriver': (SCHIFFSWAFFE, 'mass_driver'),
    'mininglaser': (SCHIFFSWERKZEUG, 'mining_laser'),
    'salvagemodifier': (SCHIFFSWERKZEUG, 'salvage_modifier'),
    'salvagehead': (SCHIFFSWERKZEUG, 'salvage_head'),
    'tractorbeam': (SCHIFFSWERKZEUG, 'tractor_beam'),
}

# --- Aus der Katalog-Art --------------------------------------------------
_AUS_ART = {
    'char_armor_helmet': (RUESTUNG, 'helm'),
    'char_armor_torso': (RUESTUNG, 'torso'),
    'char_armor_arms': (RUESTUNG, 'arme'),
    'char_armor_legs': (RUESTUNG, 'beine'),
    'char_armor_undersuit': (RUESTUNG, 'unteranzug'),
    'char_armor_backpack': (AUSRUESTUNG, 'rucksack'),
    'backpack': (AUSRUESTUNG, 'rucksack'),
    'undersuit': (RUESTUNG, 'unteranzug'),
    'char_clothing_torso': (KLEIDUNG, 'oberkoerper'),
    'char_clothing_legs': (KLEIDUNG, 'beine'),
    'char_clothing_feet': (KLEIDUNG, 'schuhe'),
    'char_clothing_jacket': (KLEIDUNG, 'jacke'),
    'cooler': (SCHIFFSMODUL, 'cooler'),
    'powerplant': (SCHIFFSMODUL, 'powerplant'),
    'quantumdrive': (SCHIFFSMODUL, 'quantumdrive'),
    'shield': (SCHIFFSMODUL, 'schild'),
    'radar': (SCHIFFSMODUL, 'radar'),
    'weaponattachment': (AUSRUESTUNG, 'aufsatz'),
    'weaponmagazine': (AUSRUESTUNG, 'magazin'),
    'magazine': (AUSRUESTUNG, 'magazin'),
    'dockingcollar': (SCHIFFSWERKZEUG, 'andockkragen'),
    'fuelnozzle': (SCHIFFSWERKZEUG, 'fuelnozzle'),
    'weaponmining': (SCHIFFSWERKZEUG, 'mining_laser'),
    'container': (AUSRUESTUNG, 'behaelter'),
    'cargomodule': (SCHIFFSWERKZEUG, 'frachtmodul'),
}

# --- Aus dem Rezept-Untertyp (FPS-Waffen) ---------------------------------
_AUS_SUB = {
    'pistol': (FPS_WAFFE, 'pistole'),
    'rifle': (FPS_WAFFE, 'gewehr'),
    'sniper': (FPS_WAFFE, 'sniper'),
    'smg': (FPS_WAFFE, 'smg'),
    'shotgun': (FPS_WAFFE, 'schrotflinte'),
    'lmg': (FPS_WAFFE, 'lmg'),
}


# Magazine tragen keine eigene Katalog-Art — sie stehen unter
# `WeaponAttachment` zwischen Zielfernrohren und Griffen. Ihr Tag endet aber
# immer auf `_mag` (oder `_mag_civilian`). ⚠ Ohne diese Zeile lagen 18 Magazine
# unter „Waffenaufsatz", während sie andernorts als
# eigene Gruppe führt.
_MAGAZIN = re.compile(r'_mag(?:_|$)', re.I)


def _aus_tag(tag):
    tag = tag or ''
    if _MAGAZIN.search(tag):
        return (AUSRUESTUNG, 'magazin')
    m = _TAG_MUSTER.search(tag)
    if not m:
        return None
    return _AUS_TAG.get(m.group(1).lower())


def einordnen(art='', tag='', unterart='', rezeptart=''):
    """Ober- und Unterkategorie eines Bauplans — `(ober, unter)`.

    Die Reihenfolge der Quellen ist Absicht: Der Tag ist am genauesten, die
    Katalog-Art am verlässlichsten, der Untertyp am gröbsten. Wer sie anders
    herum abfragt, bekommt bei einer ballistischen Gatling nur „Waffe".
    """
    treffer = _aus_tag(tag)
    if treffer:
        return treffer
    treffer = _AUS_ART.get((art or '').lower())
    if treffer:
        return treffer
    treffer = _AUS_SUB.get((unterart or '').lower())
    if treffer:
        return treffer
    # Munition zählt zur Ausrüstung — sie gehört zur Waffe, nicht zum Schiff.
    if (rezeptart or '').lower() == 'ammo':
        return (AUSRUESTUNG, 'munition')
    if (art or '').lower().startswith('weapongun'):
        return (SCHIFFSWAFFE, '')
    if (art or '').lower().startswith('weapon'):
        return (FPS_WAFFE, '')
    if (art or '').lower().startswith('char_armor'):
        return (RUESTUNG, '')
    if (art or '').lower().startswith('char_clothing'):
        return (KLEIDUNG, '')
    # ⚠ Was sich nicht bündeln lässt, bleibt **allein stehen** — mit seinem
    # eigenen Namen, nicht in einem Sammeltopf „Sonstiges". Xharig-1:
    # „nur was man nicht bündeln kann, sollte noch alleine stehen bleiben."
    # Ein Andockkragen gehört in keine der sieben Gruppen, ist aber eine klare
    # Sache — er verschwindet nicht, er steht für sich.
    if art:
        return ('art:' + art, '')
    return (SONSTIGES, '')


def ist_gruppe(schluessel):
    """Ist das eine der sieben Gruppen — oder ein Einzelgänger?"""
    return bool(schluessel) and not str(schluessel).startswith('art:')


def rohe_art(schluessel):
    """Die Katalog-Art hinter einem Einzelgänger (`art:Cooler` → `Cooler`)."""
    s = str(schluessel or '')
    return s[4:] if s.startswith('art:') else ''


def obername(schluessel):
    """Wie eine Oberkategorie im Fenster heisst.

    Einzelgänger tragen ihren Katalognamen — den kennt der Aufrufer besser als
    dieses Modul, deshalb gibt es hier den Rohwert zurück.
    """
    if not schluessel:
        return ''
    if not ist_gruppe(schluessel):
        return rohe_art(schluessel)
    return t('kat_ober_%s' % schluessel)


def untername(schluessel):
    """Wie eine Unterart im Fenster heisst."""
    return t('kat_unter_%s' % schluessel) if schluessel else ''
