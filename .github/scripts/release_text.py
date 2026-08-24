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


def zweisprachig(text):
    """Englisch nach oben, Deutsch darunter.

    Der CHANGELOG ist auf Deutsch geschrieben und enthält je Version einen
    Abschnitt `### English`. Auf der Release-Seite lesen aber überwiegend
    Menschen, die kein Deutsch können — also steht dort Englisch zuerst. Ohne
    englischen Abschnitt bleibt alles, wie es ist."""
    m = re.search(r'^### English\s*$', text, flags=re.M)
    if not m:
        return text
    rest = text[m.end():]
    # Der englische Block endet bei der nächsten deutschen Abschnittsüberschrift.
    # Ohne diese Grenze rutschen „### Hinzugefügt" & Co. mit in den englischen
    # Teil, und der Text kippt mittendrin die Sprache — genau das ist einmal
    # veröffentlicht worden.
    ende = re.search(r'^### (?!English)', rest, flags=re.M)
    englisch = (rest[:ende.start()] if ende else rest).strip()
    deutsch = (text[:m.start()] + (rest[ende.start():] if ende else '')).strip()
    return ('%s\n\n---\n\n<details>\n<summary><b>Deutsch</b></summary>\n\n%s\n\n</details>'
            % (englisch, deutsch))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GITHUB_REF_NAME', '')
    try:
        with open('CHANGELOG.md', encoding='utf-8') as f:
            changelog = f.read()
    except OSError:
        changelog = ''
    text = zweisprachig(abschnitt(changelog, tag))
    if not text:
        text = ('Was diese Fassung bringt, steht im '
                '[CHANGELOG](../blob/main/CHANGELOG.md).')
    print(text)


if __name__ == '__main__':
    main()
