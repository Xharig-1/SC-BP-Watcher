# Roadmap

Aktuelle Version: `v1.1.0`

## Zielbild

SC BP Watcher ist ein kleines Windows-Overlay, das beim Spielen von Star Citizen live anzeigt, sobald ein neuer Bauplan freigeschaltet wird. Datenquelle ist die Bauplan-Liste des SC Deutsch Launcher. Fokus: zuverlässig, leichtgewichtig, ohne Abhängigkeiten, einfach weitergebbar.

## Phasen

| Phase | Status | Inhalt |
|---|---|---|
| Phase 1 | Abgeschlossen | Live-Erkennung neuer BPs aus der Launcher-Datei + Overlay-Anzeige |
| Phase 2 | Abgeschlossen | Signalton, verschiebbares/skalierbares Fenster, Liste leeren |
| Phase 3 | Abgeschlossen | Weitergabe als `.exe` (PyInstaller) + Doku + GitHub-Release |
| Phase 4 | Abgeschlossen | Size/Grade/Klasse-Kürzel (M/A/1) + gemerkte Fensterposition/-größe |
| Phase 5 | Geplant | Optional: System-Tray-Icon statt/zusätzlich zum Overlay |
| Phase 6 | Idee | Optional: Toast-Benachrichtigung + Verlauf der letzten Session speichern |

## Bewusst nicht geplant

- **Standalone ohne den SC Deutsch Launcher:** Die BP-Namen **stehen** im Klartext im `Game.log` (`Added notification "Bauplan erhalten: <Name>: "`), Selbst-Auslesen wäre also machbar. Verworfen (Prüfung 19.07.2026): Eine eigene Werte-Datenbank (Typ/Size/Grade/Klasse) müsste jede SC-Patch nachgezogen werden — diese Pflege übernimmt der Launcher, darum bleibt seine Datei `sc_bp_erledigt.json` die Quelle. (Früher stand hier fälschlich, der Log enthalte keine lesbaren Namen.)
