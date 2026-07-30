# Roadmap

Aktuelle Version: `v1.2.0`

## Zielbild

SC BP Watcher ist ein kleines Windows-Overlay, das beim Spielen von Star Citizen live anzeigt, sobald ein neuer Bauplan freigeschaltet wird. Datenquelle ist die Bauplan-Liste des SC Deutsch Launcher. Fokus: zuverlässig, leichtgewichtig, ohne Abhängigkeiten, einfach weitergebbar.

## Phasen

| Phase | Status | Inhalt |
|---|---|---|
| Phase 1 | Abgeschlossen | Live-Erkennung neuer BPs aus der Launcher-Datei + Overlay-Anzeige |
| Phase 2 | Abgeschlossen | Signalton, verschiebbares/skalierbares Fenster, Liste leeren |
| Phase 3 | Abgeschlossen | Weitergabe als `.exe` (PyInstaller) + Doku + GitHub-Release |
| Phase 4 | Abgeschlossen | Size/Grade/Klasse-Kürzel (M/A/1) + gemerkte Fensterposition/-größe |
| Phase 5 | Abgeschlossen | Sofort-Meldung aus der `Game.log` (🟡 vorläufig → 🟢 bestätigt durch den Launcher) |
| Phase 6 | Geplant | Optional: System-Tray-Icon statt/zusätzlich zum Overlay |
| Phase 7 | Idee | Optional: Toast-Benachrichtigung + Verlauf der letzten Session speichern |
| Phase 8 | Idee | Weitere Spielsprachen in `LOG_PHRASES` (bisher nur die deutsche Meldung verifiziert) |

## Bewusst nicht geplant

- **Standalone ohne den SC Deutsch Launcher:** Die BP-Namen **stehen** im Klartext im `Game.log` (`Added notification "Bauplan erhalten: <Name>: "`) — seit v1.2.0 liest der Watcher sie für die **Sofort-Meldung** auch selbst mit. Eine *komplette* Loslösung bleibt trotzdem verworfen (Prüfung 19.07.2026): Eine eigene Werte-Datenbank (Typ/Size/Grade/Klasse) müsste jeden SC-Patch nachgezogen werden — diese Pflege übernimmt der Launcher, darum bleibt seine Datei `sc_bp_erledigt.json` die verbindliche Quelle. (Früher stand hier fälschlich, der Log enthalte keine lesbaren Namen.)
