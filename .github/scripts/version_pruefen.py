# -*- coding: utf-8 -*-
"""Prüft, ob der Git-Tag und `__version__` im Code zusammenpassen.

Grund: Es ist schon vorgekommen, dass die veröffentlichte Datei vier Versionen
hinter dem Quellcode herhinkte. Wer „v2.0.0" herunterlädt und im Fenster etwas
anderes liest, verliert das Vertrauen in jede weitere Angabe.

Aufruf:  python3 .github/scripts/version_pruefen.py v2.0.0
"""
import re
import sys


def version_im_code(pfad='sc_bp_watcher.py'):
    with open(pfad, encoding='utf-8') as f:
        m = re.search(r"__version__\s*=\s*'([^']+)'", f.read())
    return m.group(1) if m else ''


def main():
    tag = (sys.argv[1] if len(sys.argv) > 1 else '').lstrip('v')
    code = version_im_code()
    print('Tag: %s · im Code: %s' % (tag or '(keiner)', code))
    if tag and tag != code:
        print('::error::Tag (%s) und __version__ (%s) stimmen nicht überein. '
              'Erst die Versionskonstante anpassen, dann taggen.' % (tag, code))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
