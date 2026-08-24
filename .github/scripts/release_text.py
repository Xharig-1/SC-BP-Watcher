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


# Fester Anhang unter jeder Release-Notiz.
#
# Warum bei **jedem** Release und nicht nur einmal: Die SmartScreen-Meldung
# kommt bei jeder neuen Fassung wieder — jede Datei ist neu und damit wieder
# „unbekannt". Auch beim Selbst-Update aus dem Werkzeug heraus. Ohne den Hinweis
# an der Stelle, wo die Leute die Datei holen, ist das jede Woche dieselbe Frage.
#
# Ein Tester hielt die Meldung für einen Virenfund und schickte ein
# „Downloading Virus"-Bild in den Discord — verständlich, wenn Windows sagt
# „Der Computer wurde durch Windows geschützt".
HINWEIS = """
---

### ⚠️ Windows: "Windows protected your PC" / „Der Computer wurde durch Windows geschützt"

**This is not a virus detection.** Click **More info → Run anyway** — it will not ask again.

SmartScreen does not check whether a program is harmful, only whether it is *known*. That
takes a paid code-signing certificate or a great many downloads; a free fan tool has
neither, and every new version starts from zero. The source is open, the file is built by
**GitHub Actions** from exactly that source, and every asset above carries its SHA-256
checksum. On Linux this message does not exist.

<details>
<summary><b>Deutsch</b></summary>

**Das ist kein Virenfund.** **Weitere Informationen → Trotzdem ausführen** — danach kommt
die Meldung nicht wieder.

SmartScreen prüft nicht, *ob* ein Programm schädlich ist, sondern ob es **bekannt** ist.
Bekannt wird eine Datei durch eine gekaufte Code-Signatur oder sehr viele Downloads — ein
kostenloses Fan-Werkzeug hat beides nicht, und jede neue Fassung fängt wieder bei null an.
Der Quellcode ist offen, die Datei wird **nicht von mir** gebaut, sondern von GitHub
Actions aus genau diesem Quellcode, und jede Datei oben trägt ihre SHA-256-Prüfsumme.
Unter Linux gibt es diese Meldung nicht.

</details>"""


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GITHUB_REF_NAME', '')
    text = zusammensetzen(abschnitt(DATEIEN['en'], tag),
                          abschnitt(DATEIEN['de'], tag))
    if not text:
        text = ('See the [changelog](../blob/main/CHANGELOG.md) for what this '
                'release brought.')
    print(text + HINWEIS)


if __name__ == '__main__':
    main()
