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
    """Die Überschriften der obersten Aufzählungsebene — ohne Unterpunkte.

    ⚠⚠ **Erst den Punkt zusammensetzen, dann kürzen.** Im CHANGELOG ist jeder
    Punkt über mehrere Zeilen umgebrochen; die fette Überschrift reicht oft bis
    in die zweite. Wer nur die erste Zeile nimmt, findet das schließende `**`
    nicht, fällt auf „erster Satz" zurück — und der endet dann mitten im Wort.
    Genau so sah die Meldung zu v3.3.0 aus: „Ins Lager kommt nur noch, was es
    im Spiel wirklich gibt — Rohstoff", „Die Suche findet auch die Zutat. »ric«
    brachte". Sechs von sechs Punkten abgeschnitten, in einer Nachricht, die an
    mehrere hundert Leute geht (30.08.2026 aufgefallen).
    """
    gefunden = []
    puffer = [None]

    def ablegen():
        text = puffer[0]
        puffer[0] = None
        if not text:
            return
        # „**Titel.** Erklärung …" -> nur der Titel; sonst der erste Satz.
        fett = re.match(r'\*\*(.+?)\*\*', text, re.S)
        kurz = fett.group(1) if fett else text
        kurz = re.sub(r'[`*_]', '', kurz)
        kurz = re.sub(r'\s+', ' ', kurz).strip()
        # ⚠ Auch eine fette Überschrift kann zwei Sätze lang sein. Für Discord
        # zählt der erste — der Rest steht im Änderungsprotokoll. Aber nur,
        # wenn dabei noch ein Satz übrig bleibt und kein Stummel.
        erster = re.split(r'(?<=[.!?])\s', kurz)[0]
        if len(erster) >= 25:
            kurz = erster
        kurz = kurz.strip(' .—-')
        if kurz:
            gefunden.append(kurz)

    for zeile in block.split('\n'):
        if zeile.startswith('- '):
            ablegen()
            puffer[0] = zeile[2:].strip()
            continue
        if puffer[0] is None:
            continue
        inhalt = zeile.strip()
        # Leerzeile, Überschrift oder ein neuer Block: der Punkt ist zu Ende.
        # Unterpunkte und Tabellenzeilen gehören nicht in die Kurzfassung.
        if (not inhalt or not zeile.startswith((' ', '\t'))
                or inhalt.startswith(('- ', '* ', '|', '>', '#'))):
            ablegen()
            continue
        puffer[0] += ' ' + inhalt
    ablegen()
    return gefunden


def bauen(tag, sprache='de'):
    import release_text

    datei = release_text.DATEIEN['de' if sprache == 'de' else 'en']
    block = release_text.abschnitt(os.path.join(WURZEL, datei), tag)
    if not block:
        return ''

    punkte = punkte_aus(block)[:PUNKTE]
    # ⚠ Eine reine Fehlerbehebung anzukündigen mit „Was diese Version bringt"
    # liest sich schief: Darunter stehen dann Sätze wie „Der eingetippte Name
    # kam nicht mit" — also das Problem, nicht die Neuerung. Bei einer Fassung
    # ohne neue Funktionen sagt die Zeile deshalb, was sie ist.
    nur_behoben = bool(re.search(r'(?m)^### (Behoben|Fixed)\s*$', block)) and \
        not re.search(r'(?m)^### (Neu|Added|Geändert|Changed)\s*$', block)
    if sprache == 'de':
        kopf = '## SC BP Watcher %s ist da' % tag
        rest = (('Behoben in dieser Fassung:' if nur_behoben
                 else 'Was diese Version bringt:') if punkte else '')
        fuss = ('\n**Herunterladen:** <%s/releases/latest>\n'
                'Fehler gefunden oder eine Frage? Ab damit in die passenden Kanäle — '
                'hier bleibt es bei den Versionsmeldungen.' % REPO)
    else:
        kopf = '## SC BP Watcher %s is out' % tag
        rest = (('Fixed in this build:' if nur_behoben
                 else 'What this version brings:') if punkte else '')
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
