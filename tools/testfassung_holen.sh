#!/usr/bin/env bash
#
# Holt die neueste **unveroeffentlichte** Fassung als AppImage und setzt sie ein.
#
# Wozu: Zum Ausprobieren braucht es keinen Release. Ein Tag ist fuer Nutzer da —
# er loest bei allen die Update-Meldung aus. Wer selbst testen will, nimmt das
# AppImage, das GitHub bei jedem Bau-Lauf ohnehin anhaengt.
#
# Voraussetzung: die GitHub-Kommandozeile `gh`, einmal angemeldet.
#   Arch/EndeavourOS:  sudo pacman -S github-cli && gh auth login
#
# Der Zielpfad laesst sich mit SC_BP_APPIMAGE ueberschreiben.
#
#   bash tools/testfassung_holen.sh
#
set -euo pipefail

ZIEL="${SC_BP_APPIMAGE:-$HOME/Programme/SC-BP-Watcher.AppImage}"
ABLAUF='release.yml'
WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v gh >/dev/null 2>&1; then
  echo "Die GitHub-Kommandozeile 'gh' fehlt." >&2
  echo "  sudo pacman -S github-cli   (danach einmal: gh auth login)" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "'gh' ist noch nicht angemeldet — bitte einmal 'gh auth login' ausfuehren." >&2
  exit 1
fi

cd "$WURZEL"

echo "Suche den letzten erfolgreichen Bau …"
LAUF="$(gh run list --workflow "$ABLAUF" --status success --limit 1 --json databaseId \
        --jq '.[0].databaseId')"
if [ -z "${LAUF:-}" ]; then
  echo "Kein erfolgreicher Bau gefunden. Zuerst einen anstossen:" >&2
  echo "  gh workflow run $ABLAUF" >&2
  exit 1
fi
echo "  Lauf $LAUF"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Lade das AppImage …"
gh run download "$LAUF" --name linux --dir "$TMP"

NEU="$(find "$TMP" -name '*.AppImage' -print -quit)"
[ -n "$NEU" ] || { echo "Im Anhang war kein AppImage." >&2; exit 1; }

mkdir -p "$(dirname "$ZIEL")"

# Die bisherige Fassung bleibt als .vorher liegen — falls die neue klemmt,
# ist der Rueckweg ein Umbenennen und kein neuer Download.
if [ -f "$ZIEL" ]; then
  cp -f "$ZIEL" "$ZIEL.vorher"
  echo "Bisherige Fassung gesichert: $ZIEL.vorher"
fi

install -m 755 "$NEU" "$ZIEL"
echo "Eingesetzt: $ZIEL"

VER="$(grep -m1 '^__version__' "$WURZEL/sc_bp_watcher.py" | cut -d"'" -f2 || true)"
echo "Quellstand dieser Fassung: ${VER:-unbekannt} (unveroeffentlicht)"
echo
echo "Starten:  \"$ZIEL\""
