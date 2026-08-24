# -*- coding: utf-8 -*-
"""Baut den Release-Text aus den beiden CHANGELOG-Dateien.

Englisch steht oben, Deutsch in einem aufklappbaren Block darunter: Auf der
Release-Seite lesen überwiegend Menschen, die kein Deutsch können, aber die
deutschsprachige Community soll ihre Fassung auch bekommen.

Dieselben Texte zeigt das Werkzeug unter „Was ist neu" — dort allerdings jedem
nur in seiner Sprache.

Bewusst eine eigene Datei statt eines Heredocs im Workflow: Eingerückter
Python-Code in YAML ist brüchig, und Fehler fallen erst beim Bauen auf.

Aufruf:  python3 .github/scripts/release_text.py v2.0.0 > release-text.md
"""
import os
import re
import sys

DATEIEN = {'en': 'CHANGELOG.md', 'de': 'CHANGELOG.de.md'}


def abschnitt(pfad, tag):
    """Der Block zur getaggten Version aus einer CHANGELOG-Datei."""
    try:
        with open(pfad, encoding='utf-8') as f:
            text = f.read()
    except OSError:
        return ''
    zahl = tag.lstrip('v')
    for block in re.split(r'^## ', text, flags=re.M)[1:]:
        kopf, _, rest = block.partition('\n')
        if zahl in kopf:
            return rest.strip()
    return ''


def zusammensetzen(englisch, deutsch):
    """Englisch oben, Deutsch aufklappbar darunter."""
    if not englisch:
        return deutsch or ''
    if not deutsch:
        return englisch
    return ('%s\n\n---\n\n<details>\n<summary><b>Deutsch</b></summary>\n\n%s\n\n</details>'
            % (englisch, deutsch))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GITHUB_REF_NAME', '')
    text = zusammensetzen(abschnitt(DATEIEN['en'], tag),
                          abschnitt(DATEIEN['de'], tag))
    if not text:
        text = ('See the [changelog](../blob/main/CHANGELOG.md) for what this '
                'release brought.')
    print(text)


if __name__ == '__main__':
    main()
