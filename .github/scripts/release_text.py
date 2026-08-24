# -*- coding: utf-8 -*-
"""Holt den Abschnitt zur getaggten Version aus dem CHANGELOG.

Wird beim Bauen eines Releases aufgerufen und liefert den Text, der auf der
GitHub-Release-Seite steht. Dadurch zeigt das Fenster „Was ist neu" im
Werkzeug dasselbe wie GitHub — beides speist sich aus derselben Quelle.

Bewusst eine eigene Datei statt eines Heredocs im Workflow: Eingerückter
Python-Code in YAML ist brüchig, und Fehler fallen erst beim Bauen auf.

Aufruf:  python3 .github/scripts/release_text.py v2.0.0 > release-text.md
"""
import os
import re
import sys


def abschnitt(changelog, tag):
    zahl = tag.lstrip('v')
    for block in re.split(r'^## ', changelog, flags=re.M)[1:]:
        kopf, _, rest = block.partition('\n')
        if zahl in kopf:
            return rest.strip()
    return ''


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GITHUB_REF_NAME', '')
    try:
        with open('CHANGELOG.md', encoding='utf-8') as f:
            changelog = f.read()
    except OSError:
        changelog = ''
    text = abschnitt(changelog, tag)
    if not text:
        text = ('Was diese Fassung bringt, steht im '
                '[CHANGELOG](../blob/main/CHANGELOG.md).')
    print(text)


if __name__ == '__main__':
    main()
