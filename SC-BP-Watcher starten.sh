#!/usr/bin/env bash
# Startet den SC BP Watcher aus dem Quellcode — das Linux-Gegenstück zur .bat.
#
# Warum direkt das .py und nicht das fertige Paket: So läuft immer der aktuelle
# Stand, ohne vorher bauen zu müssen. Das AppImage ist nur die Verpackung für
# alle, die kein Python installiert haben.
#
# Fehlt tkinter, sagt Python das leider nur kryptisch — deshalb der Hinweis unten.
cd "$(dirname "$0")" || exit 1

if ! python3 -c 'import tkinter' 2>/dev/null; then
    echo "Es fehlt das Paket 'tk' (die Fenster-Bibliothek von Python)."
    echo
    echo "  Arch / EndeavourOS :  sudo pacman -S tk"
    echo "  Debian / Ubuntu    :  sudo apt install python3-tk"
    echo "  Fedora             :  sudo dnf install python3-tkinter"
    exit 1
fi

exec python3 sc_bp_watcher.py "$@"
