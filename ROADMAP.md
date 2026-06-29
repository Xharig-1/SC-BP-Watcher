# Roadmap

Aktuelle Version: `v1.0.3`

## Zielbild

SC BP Watcher ist ein kleines Windows-Overlay, das beim Spielen von Star Citizen live anzeigt, sobald ein neuer Bauplan freigeschaltet wird. Datenquelle ist die Bauplan-Liste des SC Deutsch Launcher. Fokus: zuverlässig, leichtgewichtig, ohne Abhängigkeiten, einfach weitergebbar.

## Phasen

| Phase | Status | Inhalt |
|---|---|---|
| Phase 1 | Abgeschlossen | Live-Erkennung neuer BPs aus der Launcher-Datei + Overlay-Anzeige |
| Phase 2 | Abgeschlossen | Signalton, verschiebbares/skalierbares Fenster, Liste leeren |
| Phase 3 | Abgeschlossen | Weitergabe als `.exe` (PyInstaller) + Doku + GitHub-Release |
| Phase 4 | Geplant | Optional: System-Tray-Icon statt/zusätzlich zum Overlay |
| Phase 5 | Idee | Optional: Toast-Benachrichtigung + Verlauf der letzten Session speichern |

## Bewusst nicht geplant

- **Direktes Auslesen der SC `Game.log`:** Die Baupläne laufen über eine binäre gRPC-API (`BlueprintLibraryService`) und stehen **nicht** als Klartext im Log. Die Launcher-Datei `sc_bp_erledigt.json` ist die einzige saubere Quelle und wird daher genutzt.
