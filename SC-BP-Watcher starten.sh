#!/usr/bin/env bash
# Startet den SC BP Watcher aus dem Quellcode — das Linux-Gegenstück zur .bat.
#
# Warum direkt das .py und nicht das fertige Paket: So läuft immer der aktuelle
# Stand, ohne vorher bauen zu müssen. Das AppImage ist nur die Verpackung für
# alle, die kein Python installiert haben.
#
# Fehlt tkinter, sagt Python das leider nur kryptisch — deshalb der Hinweis unten.
cd "$(dirname "$0")" || exit 1

# Welches Python zeichnet wirklich ein Fenster?
#
# ⚠ Auf dem Mac ist das nicht egal: Dort liegt ein System-Python mit **Tk 8.5**
# im Pfad. Damit startet das Programm ohne jede Fehlermeldung, das Fenster
# bleibt aber leer — es sieht aus, als würde es gar nicht starten. Genau das ist
# passiert. Deshalb wird hier nach einem Python mit Tk 8.6 oder neuer gesucht,
# statt blind `python3` zu nehmen.
tk_fassung() {
    "$1" -c 'import tkinter; print(tkinter.TkVersion)' 2>/dev/null
}

taugt() {
    local v
    v=$(tk_fassung "$1") || return 1
    [ -n "$v" ] || return 1
    # 8.5 ist zu alt; alles ab 8.6 zeichnet.
    awk -v v="$v" 'BEGIN { exit !(v + 0 >= 8.6) }'
}

PY=""
for kandidat in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if command -v "$kandidat" >/dev/null 2>&1 && taugt "$kandidat"; then
        PY="$kandidat"
        break
    fi
done

if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1 && python3 -c 'import tkinter' 2>/dev/null; then
        # tkinter ist da, aber zu alt — der Fall Mac mit System-Python.
        echo "Gefunden wurde nur Tk $(tk_fassung python3). Damit bleibt das"
        echo "Fenster leer (bekanntes Verhalten auf dem Mac)."
        echo
        echo "  Mac : brew install python-tk    → danach /opt/homebrew/bin/python3"
        exit 1
    fi
    echo "Es fehlt das Paket 'tk' (die Fenster-Bibliothek von Python)."
    echo
    echo "  Arch / EndeavourOS :  sudo pacman -S tk"
    echo "  Debian / Ubuntu    :  sudo apt install python3-tk"
    echo "  Fedora             :  sudo dnf install python3-tkinter"
    echo "  Mac                :  brew install python-tk"
    exit 1
fi

# Die Warnung des Systems über sein altes Tk hilft niemandem weiter — wir
# haben oben schon geprüft, dass die Fassung taugt.
export TK_SILENCE_DEPRECATION=1

exec "$PY" sc_bp_watcher.py "$@"
