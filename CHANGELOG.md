# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

Das Projekt nutzt SemVer: `MAJOR.MINOR.PATCH`.

## v1.2.0 - 2026-07-30

### Hinzugefügt

- **Sofort-Meldung aus der `Game.log`:** Der Watcher liest die Star-Citizen-Log jetzt zusätzlich selbst mit und zeigt einen neuen Bauplan **in Sekunden** an, statt auf den Export des Launchers zu warten. Hintergrund: Der SC Deutsch Launcher schreibt `sc_bp_erledigt.json` nur alle paar Minuten neu — gemessen am 30.07.2026 lagen zwischen Freischaltung im Spiel (21:23:49) und Launcher-Export (21:26:24) **2,5 Minuten**. Genau diese Lücke schließt die Log-Mitlesung.
- **Zwei-Stufen-Anzeige:** Frisch aus der Log gemeldete Baupläne stehen als 🟡 **vorläufig** in der Liste; sobald der Launcher nachzieht, wird die Zeile auf 🟢 bestätigt und mit dessen Daten aufgefrischt. Die Launcher-Datei bleibt die verbindliche Quelle — Art, Size/Grade/Klasse kommen weiterhin aus dem Launcher-Katalog.
- **Namens-Abgleich Log ↔ Launcher:** Schiffskomponenten stehen im Log mit Zusatz (`7CA 'Nargun' (Civ/3/A)`), beim Launcher ohne — der Zusatz wird abgeschnitten (und dient als Rückfall fürs `M/A/1`-Kürzel, falls ein Item nach einem SC-Patch noch nicht im Katalog steht). Echte Namens-Klammern wie `(30 cap)` oder `Singe Cannon (S2)` bleiben unangetastet. Weichen die Übersetzungen ab (gesehen: `(12 Schuss)` im Log vs. `(12 cap)` beim Launcher), greift ein Notfall-Abgleich ohne Klammer-Zusatz — aber nur, wenn er eindeutig ist. Geprüft gegen alle 127 vorhandenen Log-Backups: 148 Bauplan-Meldungen, 147 exakte Treffer, der eine Rest über den Notfall-Abgleich.
- **Automatische Log-Findung** über den `Installfolder` aus `scdl-settings.json`, ersatzweise über den Lesestand des Launchers (`scan-state.json`) oder den Standard-Installationspfad. Spiel-Neustart (rotierte Log) wird erkannt.
- **Statuszeile** zeigt jetzt auch, ob die Log mitgelesen wird: `Überwache 377 BPs · Log ✓ · geprüft 21:26:27`.

### Behoben

- **„Neueste oben" hat nie funktioniert:** Neue Zeilen wurden per `winfo_children()` einsortiert — das ist die Reihenfolge der *Erzeugung*, nicht die im Fenster. Dadurch landete jeder Neuzugang ab dem dritten **unter** den älteren. Jetzt wird `pack_slaves()` genutzt.
- **`MAX_ROWS` war wirkungslos:** Die Einstellung stand in der README, wurde im Code aber nie angewendet — die Liste wuchs unbegrenzt. Jetzt fliegen die ältesten Zeilen über `MAX_ROWS` (Standard 200) raus.
- **Art-Nachschlag frischt sich auf:** Ist ein gerade freigeschaltetes Item noch nicht in `bp_item_types.json`, wird die Datei einmal neu geladen, statt sofort `—` anzuzeigen.

### Hinweise

- Die Log-Mitlesung erkennt die **deutsche** Spielmeldung (`Bauplan erhalten: <Name>: `). Bei anderer Spielsprache greift sie nicht — dann verhält sich das Tool wie bisher (Meldung, sobald der Launcher exportiert hat). Weitere Sprachen lassen sich in `LOG_PHRASES` ergänzen.
- Weiterhin nur lesend: die `Game.log` wird ausschließlich gelesen, nie verändert.

## v1.1.0 - 2026-07-19

### Hinzugefügt

- **Size / Grade / Klasse je Bauplan** als Kompakt-Kürzel `Klasse/Grade/Size`, z. B. `M/A/1` (Military · Grade A · Size 1). Kürzel: **M** Military, **S** Stealth, **I** Industrial, **C** Civilian, **K** Competition. Schiffswaffen haben nur Size → `–/–/2`; FPS-Waffen und Rüstung haben nichts davon → kein Kürzel. Datenbasis identisch zum Skill „SC BP" (Launcher-Katalog `catalog\components.ini` + `items_raw.ini`, plus manuelle Korrekturen aus `bp-overrides.json` mit Vorrang) — die Anzeige stimmt damit 1:1 mit der Vault-Liste überein.
- **Fenster merkt sich Position & Größe:** beim Verschieben, Skalieren und Beenden wird die Lage in `%APPDATA%\sc-bp-watcher\watcher.json` gespeichert und beim nächsten Start wiederhergestellt.

### Geändert

- **Standard-Startposition** ist jetzt der obere Monitor (nicht der Spiel-Monitor) → man tabbt nicht mehr versehentlich aus Star Citizen. Wird über `DEFAULT_GEOM` gesetzt (nur beim allerersten Start relevant, danach greift die gemerkte Position).

## v1.0.3 - 2026-06-29

### Hinzugefügt

- **GitHub-Release** mit der fertigen `SC-BP-Watcher.exe` als Anhang — herunterladen, Doppelklick, läuft (kein Python, kein Selbst-Bauen nötig)

### Geändert

- README: „Fertige `.exe` herunterladen" ist jetzt die **empfohlene** Start-Variante (A); Python (B) und Selbst-Bauen (C) dahinter

## v1.0.2 - 2026-06-29

### Hinzugefügt

- **App-Icon** im Xharig-Stil (dunkler Grund, Xharig-Grün, Scope-Ring mit „neu"-Punkt) — `icon.ico` für die EXE, `docs/icon.png` als Vorschau
- EXE wird jetzt mit dem Icon gebaut (`EXE bauen.bat` → `--icon`)
- Fenster-/Taskleisten-Icon wird auch beim Start als Skript gesetzt (falls `icon.ico` daneben liegt)
- Icon-Generator `make_icon.py` (reproduzierbar; braucht nur Pillow, nicht fürs Tool selbst)

## v1.0.1 - 2026-06-29

### Hinzugefügt

- **Danksagung & Credits** an den SC Deutsch Launcher (Datenquelle des Tools) inkl. Hinweis, dass SC BP Watcher ein eigenständiges, inoffizielles Zusatz-Tool ist
- Offizieller Link zum **[SC Deutsch Launcher](https://www.sc-deutsch-launcher.de/)** im Pflicht-Hinweis und in den Credits

### Geändert

- Pflicht-Voraussetzung (SC Deutsch Launcher) prominent ganz oben in der README hervorgehoben

## v1.0.0 - 2026-06-29

Erstveröffentlichung.

### Hinzugefügt

- Live-Overlay (randlos, immer im Vordergrund, durchscheinend), das neue Star-Citizen-Baupläne in Echtzeit anzeigt
- Hintergrund-Überwachung von `sc_bp_erledigt.json` (Prüf-Intervall 3 s, eigener Thread)
- Anzeige je Neuzugang: 🟢 Name · Art · Uhrzeit, neueste oben
- Signalton bei jedem neuen Bauplan
- Fenster verschiebbar (Titelleiste) und skalierbar (Griff ◢), Liste leeren (🗑), schließen (✕)
- Art-Anzeige zweisprachig — übernimmt den Wert direkt aus `bp_item_types.json` (deutsch oder englisch)
- Automatische Pfad-Findung über `%APPDATA%`
- Start per `SC-BP-Watcher starten.bat` (ohne Konsolenfenster) oder als eigenständige `.exe` via `EXE bauen.bat`

### Hinweise

- Reines Python-Standardbibliothek-Tool (`tkinter`) — keine Zusatzpakete nötig
- Nur lesend: verändert oder sendet keine Daten
