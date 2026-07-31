# Roadmap

Aktuelle Version: `v1.3.0`

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
| Phase 6 | Abgeschlossen | Katalog-Wache: meldet, was im Spiel **neu craftbar** wurde (🔵), Wunsch-Gegenstände aus der Beobachtungsliste auffällig (⭐) |
| Phase 7 | **Als Nächstes** | **Umbau zur App** — Einstellungs-/Status-Fenster, `settings.json`, automatisch gebaute `.exe` je Release, Verteilweg ohne Quellcode. Strukturiert das Projekt komplett um → Start **immer mit „grill mich"**, Vorarbeit in [`docs/app-konzept.md`](docs/app-konzept.md) |
| Phase 8 | **Als Nächstes** | **Unabhängigkeit vom SC Deutsch Launcher**, Schritt 1: Name/Art/Size/Grade/Klasse aus der `global.ini` statt aus dem Launcher-Katalog → [`docs/datenquellen-ohne-launcher.md`](docs/datenquellen-ohne-launcher.md) |
| Phase 9 | Geplant | Autostart + System-Tray (sinnvoll erst zusammen: dauerhaft laufendes Overlay ohne Tray nervt) |
| Phase 10 | Geplant | **Zweisprachig (de/en)** — Oberfläche umschaltbar + Doku in beiden Sprachen. Dazu: Spielsprache automatisch erkennen, Log-Phrase aus `global.ini` ableiten (`crafting_hud_notification_received_blueprint`) statt fest verdrahteter `LOG_PHRASES`. ⚠️ Oberflächensprache und Spielsprache **nicht** koppeln |
| Phase 11 | Idee | **Bauplan-Anzeige im Spiel** — Häkchen `[x]`/`[  ]` in den Missions-Beschreibungen der `global.ini`, so wie es der SC Deutsch Launcher macht (Daten liegen im scmdb-Dump bereit). Kein Alleinstellungsmerkmal: Der Launcher bietet die Anzeige auch mit **englischen** Originaltexten an — ohne seine Sprachverwaltung gibt es sie aber gar nicht. Nutzen wäre also „ohne zweites Werkzeug". Hängt an der p4k-Extraktion, weil die Localization-Datei vollständig geschrieben werden muss; Konflikt mit dem Launcher abfangen |
| Phase 12 | Idee | Optional: Toast-Benachrichtigung + Verlauf der letzten Session speichern |

## Bewusst nicht geplant

- **Vollständiger Ersatz des Launchers.** Der **Freischalt-Bestand** ist kontospezifisch — keine externe Quelle kann ihn liefern, `sc_bp_erledigt.json` bleibt dafür konkurrenzlos. Ein eigener Bestand ließe sich nur „ab heute" fortschreiben und driftet still, sobald jemand ohne laufenden Watcher spielt. **Ziel ist deshalb nicht Ersatz, sondern Wahlfreiheit:** ohne Launcher soll das Tool nutzbar sein (Phase 8), mit Launcher bleibt es genauer.

- **Standalone ohne den SC Deutsch Launcher:** weiterhin **nicht umgesetzt**, aber die Begründung von damals ist überholt. Die BP-Namen **stehen** im Klartext im `Game.log` — seit v1.2.0 liest der Watcher sie für die **Sofort-Meldung** selbst mit. Am 19.07.2026 wurde eine komplette Loslösung verworfen, weil eine eigene Werte-Datenbank (Typ/Size/Grade/Klasse) jeden Patch nachgezogen werden müsste. **Das stimmt nicht:** Diese Werte stehen vollständig und patchaktuell in der `global.ini` des Spiels (`Data.p4k → Data/Localization/english/global.ini`), zusammen mit den Item-Namen und sogar der Log-Erkennungsphrase je Sprache. Was wirklich im Weg steht, ist das **Extrahieren aus dem p4k** (Fremdwerkzeug wie `unp4k` oder eigener Parser — kollidiert mit „reine Standardbibliothek") und der **nicht rekonstruierbare Altbestand** (die Log-Backups reichen nur ein paar Wochen zurück, den vollen Freischalt-Stand liefert nur `sc_bp_erledigt.json`). Vollständige Quellen-Recherche mit Belegen: [`docs/datenquellen-ohne-launcher.md`](docs/datenquellen-ohne-launcher.md).
