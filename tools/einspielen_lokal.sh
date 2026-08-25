#!/usr/bin/env bash
#
# Eine Fassung von GitHub holen und hier einsetzen — beenden, tauschen, starten.
#
# Wozu ein eigenes Skript: Beim Einsetzen von Hand ist mehrfach schiefgegangen,
# dass die alte Fassung noch lief. Auf dem Bildschirm stand dann weiter die alte
# Nummer, obwohl die neue Datei längst auf der Platte lag — und beim Suchen des
# Fehlers sucht man an der falschen Stelle.
#
# ⚠ Das Beenden braucht ein Muster, das sich nicht selbst trifft: `pkill -f
# SC-BP-Watcher` erwischt auch die Shell, in der dieser Befehl steht (der Name
# steht ja in ihrer Kommandozeile), und bricht damit den eigenen Ablauf ab.
# Deshalb `[S]C-BP` — im laufenden Kommando steht die Klammer, im Prozessnamen
# nicht.
#
#   bash tools/einspielen_lokal.sh v3.0.0-rc9
#
set -euo pipefail

TAG="${1:-}"
ZIEL="${SC_BP_APPIMAGE:-$HOME/Programme/SC-BP-Watcher.AppImage}"
[ -n "$TAG" ] || { echo "Aufruf: bash tools/einspielen_lokal.sh v3.0.0-rc9" >&2; exit 1; }

echo "1/4  Laufende Fassung beenden …"
for pid in $(ps -eo pid,args | awk '/[S]C-BP-Watcher/ && !/awk/ {print $1}'); do
  kill "$pid" 2>/dev/null || true
done
sleep 2

echo "2/4  $TAG holen …"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
gh release download "$TAG" --pattern '*.AppImage' --dir "$TMP" >/dev/null

echo "3/4  Einsetzen …"
[ -f "$ZIEL" ] && cp -f "$ZIEL" "$ZIEL.vorher"
install -m 755 "$TMP"/*.AppImage "$ZIEL"

echo "4/4  Starten …"
setsid nohup "$ZIEL" >/dev/null 2>&1 < /dev/null &
sleep 8

ANZAHL="$(ps -eo args | grep -c '[S]C-BP-Watcher' || true)"
if [ "$ANZAHL" -ge 1 ]; then
  echo "Läuft: $TAG   ($ZIEL)"
else
  echo "FEHLER: startet nicht. Von Hand versuchen: \"$ZIEL\"" >&2
  exit 1
fi
