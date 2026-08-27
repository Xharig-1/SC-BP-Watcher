# -*- coding: utf-8 -*-
"""
Baut aus dem CHANGELOG die **Versionsmeldung fürs Discord**.

Zum Projekt gehoert ein eigenes Discord, das wie ein Forum aufgebaut ist: ein Kanal
nur für Versionsmeldungen, daneben Kanäle für Fragen und Fehlermeldungen. Der
Meldungs-Kanal soll sauber bleiben — eine Nachricht je Version, immer gleich
aufgebaut, ohne Diskussion dazwischen.

Warum ein Skript und keine Handarbeit: Der CHANGELOG-Eintrag ist zu lang und zu
technisch für Discord (dort gibt es **keine Tabellen**, und bei 2000 Zeichen ist
Schluss). Von Hand kürzen heißt: jedes Mal neu entscheiden, was wegfällt — und
irgendwann bleibt die Meldung ganz aus.

    python3 tools/discord_post.py v2.1.0          # deutsch
    python3 tools/discord_post.py v2.1.0 --en     # englisch

Was herauskommt, ist zum **Kopieren** gedacht. Automatisch posten könnte man über
einen Discord-Webhook — das wäre ein Zugangsschlüssel mehr und eine Nachricht,
die ohne zweiten Blick rausgeht. Beides bewusst nicht.
"""
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(WURZEL, '.github', 'scripts'))

GRENZE = 2000            # Discord nimmt nicht mehr je Nachricht
PUNKTE = 6               # mehr liest im Vorbeiscrollen niemand
REPO = 'https://github.com/Xharig-1/SC-BP-Watcher'


def punkte_aus(block):
    """Die Überschriften der obersten Aufzählungsebene — ohne Unterpunkte."""
    gefunden = []
    for zeile in block.split('\n'):
        if not zeile.startswith('- '):
            continue                     # eingerückte Unterpunkte fallen weg
        text = zeile[2:].strip()
        # „**Titel.** Erklärung …" -> nur der Titel; sonst der erste Satz.
        fett = re.match(r'\*\*(.+?)\*\*', text)
        kurz = fett.group(1) if fett else text.split('. ')[0]
        kurz = re.sub(r'[`*_]', '', kurz).strip(' .—-')
        kurz = re.sub(r'\s+', ' ', kurz)
        if kurz:
            gefunden.append(kurz)
    return gefunden


def bauen(tag, sprache='de'):
    import release_text

    datei = release_text.DATEIEN['de' if sprache == 'de' else 'en']
    block = release_text.abschnitt(os.path.join(WURZEL, datei), tag)
    if not block:
        return ''

    punkte = punkte_aus(block)[:PUNKTE]
    if sprache == 'de':
        kopf = '## SC BP Watcher %s ist da' % tag
        rest = ('Was diese Version bringt:' if punkte else '')
        fuss = ('\n**Herunterladen:** <%s/releases/latest>\n'
                'Fehler gefunden oder eine Frage? Ab damit in die passenden Kanäle — '
                'hier bleibt es bei den Versionsmeldungen.' % REPO)
    else:
        kopf = '## SC BP Watcher %s is out' % tag
        rest = ('What this version brings:' if punkte else '')
        fuss = ('\n**Download:** <%s/releases/latest>\n'
                'Found a bug or have a question? Please use the matching channels — '
                'this one stays version announcements only.' % REPO)

    text = kopf + '\n\n' + (rest + '\n' if rest else '')
    for p in punkte:
        text += '· %s\n' % p
    text += fuss

    if len(text) > GRENZE:
        # Lieber einen Punkt weniger als eine abgeschnittene Nachricht.
        while punkte and len(text) > GRENZE:
            punkte.pop()
            text = kopf + '\n\n' + (rest + '\n' if rest else '')
            for p in punkte:
                text += '· %s\n' % p
            text += fuss
    return text


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        return 2
    tag = sys.argv[1]
    sprache = 'en' if '--en' in sys.argv else 'de'
    text = bauen(tag, sprache)
    if not text:
        print('Kein CHANGELOG-Abschnitt zu %s gefunden.' % tag, file=sys.stderr)
        return 1
    print(text)
    print('\n---\n%d von %d Zeichen' % (len(text), GRENZE), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
