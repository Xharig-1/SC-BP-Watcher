<div align="center">

<img src="docs/icon.png" alt="SC BP Watcher Icon" width="128">

# SC BP Watcher

**Live-Overlay, das neue Star-Citizen-Baupläne anzeigt, sobald du sie freischaltest**

[![Version](https://img.shields.io/badge/Version-1.1.0-5fa522)](CHANGELOG.md)
[![Lizenz](https://img.shields.io/badge/Lizenz-MIT-5fa522)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-0a4a7a?logo=python&logoColor=white)](https://www.python.org/)
[![Star Citizen](https://img.shields.io/badge/Star%20Citizen-kompatibel-0a4a7a)](https://robertsspaceindustries.com/)

</div>

---

Ein kleines, randloses Overlay, das im Hintergrund die Bauplan-Daten des **SC Deutsch Launcher** überwacht und dir **in Echtzeit** meldet, sobald ein neuer Bauplan (Blueprint) dazukommt — inklusive Name, Art und Uhrzeit. Ohne Account, ohne Cloud, ohne Installation.

> ⚠️ **Wichtig:** Dieses Tool funktioniert **ausschließlich** zusammen mit dem **[SC Deutsch Launcher](https://www.sc-deutsch-launcher.de/)** — es liest dessen Bauplan-Datei (`%APPDATA%\sc-deutsch-launcher\…`). Ohne diesen Launcher gibt es **keine Datenquelle** und das Overlay bleibt leer. Der normale RSI-Launcher allein reicht **nicht**.

## Features

| | |
|---|---|
| 🟢 **Live-Erkennung** | Prüft alle 3 Sekunden die Launcher-Datei; neue Baupläne erscheinen sofort oben in der Liste |
| 🏷️ **Size · Grade · Klasse** | Kompakt-Kürzel `Klasse/Grade/Size` je Bauplan, z. B. `M/A/1` (Military · Grade A · Size 1) — gleiche Daten wie die Vault-Liste |
| 🔔 **Signalton** | Kurzer Ton bei jedem Neuzugang — du musst nicht aufs Fenster schauen |
| 🧷 **Immer im Vordergrund** | Randloses, leicht durchscheinendes Overlay über dem Spiel |
| 🖱️ **Verschiebbar & skalierbar** | An der Titelleiste ziehen, Größe am Griff ◢ unten rechts — **Position & Größe werden gemerkt** |
| 🌐 **Zweisprachig** | Zeigt die Art genau so an, wie der Launcher sie liefert (deutsch oder englisch) |
| 🔒 **Nur lesend** | Verändert oder sendet nichts — liest ausschließlich die Launcher-Dateien |

## Voraussetzungen

- **Windows**
- **SC Deutsch Launcher** installiert und mindestens einmal gelaufen (damit die überwachte Datei existiert)
- Zum Start als Skript: **Python 3.8+** (für die fertige `.exe` nicht nötig)

## Start

**Variante A — fertige `.exe` herunterladen (empfohlen, kein Python nötig):**

1. Auf der **[Releases-Seite](../../releases)** die neueste **`SC-BP-Watcher.exe`** herunterladen.
2. Doppelklick — fertig. Eine einzelne Datei, keine Installation, kein Python.

**Variante B — mit Python (zum Testen / Anpassen):**

1. Python 3.8+ installieren (falls nötig): https://www.python.org/downloads/ — beim Setup **„Add Python to PATH"** anhaken.
2. Doppelklick auf **`SC-BP-Watcher starten.bat`**.

Es sind **keine** Zusatzpakete nötig — das Tool nutzt nur die Python-Standardbibliothek (`tkinter`).

**Variante C — `.exe` selbst bauen:**

1. Doppelklick auf **`EXE bauen.bat`** — installiert einmalig PyInstaller und baut die EXE.
2. Ergebnis: **`dist\SC-BP-Watcher.exe`** — eine einzelne Datei.

## Bedienung

| Aktion | Wie |
|---|---|
| Fenster verschieben | Oben an der Leiste ziehen |
| Größe ändern | Griff **◢** unten rechts ziehen |
| Liste leeren | **🗑** in der Titelleiste |
| Schließen | **✕** in der Titelleiste |

## Wie es funktioniert

1. **Beim Start** liest das Tool einmal alle aktuell freigeschalteten Baupläne ein und merkt sie sich als Basis — diese werden **nicht** gemeldet.
2. **Im Hintergrund** (eigener Thread) wird `sc_bp_erledigt.json` alle 3 Sekunden neu eingelesen und mit der Basis verglichen.
3. **Taucht ein neuer Name auf**, wird er oben in die Liste geschoben (🟢 Name · Art · `M/A/1` · Uhrzeit) und ein kurzer Ton gespielt.
4. Die **Art** kommt aus `bp_item_types.json`; **Size/Grade/Klasse** aus dem Launcher-Katalog (`catalog\components.ini` + `items_raw.ini`) plus manuellen Korrekturen aus `bp-overrides.json` (Vorrang) — dieselbe Datenbasis wie der Skill „SC BP", die Anzeige stimmt daher mit der Vault-Liste überein.

Überwachte Datei (Pfad wird automatisch über `%APPDATA%` gefunden):

```text
%APPDATA%\sc-deutsch-launcher\blueprints\sc_bp_erledigt.json
```

## Einstellungen

Oben in `sc_bp_watcher.py` anpassbar:

| Variable | Bedeutung | Standard |
|----------|-----------|----------|
| `POLL_SEC` | Prüf-Intervall in Sekunden | `3` |
| `MAX_ROWS` | max. Einträge in der Liste | `200` |
| `DEFAULT_GEOM` | Start-Position/-Größe beim allerersten Start (danach wird die gemerkte Lage genutzt) | oberer Monitor |
| `CLASS_LETTER` | Kürzel je Klasse (M/S/I/C/K) | Military/Stealth/Industrial/Civilian/Competition |
| `BG / FG / ACCENT / …` | Farben des Overlays | dunkel + Xharig-Grün |

> Position & Größe werden beim Verschieben/Beenden in `%APPDATA%\sc-bp-watcher\watcher.json` gespeichert. Zum Zurücksetzen einfach diese Datei löschen — dann greift wieder `DEFAULT_GEOM`.

## Weitergeben

> 🔒 **Offline & privat** — das Tool arbeitet komplett ohne Internet. Es liest nur die lokale Bauplan-Liste des Launchers, verändert nichts und sendet nichts.

- **Als `.exe` (am einfachsten):** die fertige `SC-BP-Watcher.exe` von der **[Releases-Seite](../../releases)** weitergeben — Empfänger braucht **nur** den SC Deutsch Launcher, kein Python.
- **Als Skript:** `sc_bp_watcher.py` + die `.bat`-Dateien weitergeben (Empfänger braucht Python).

> ℹ️ Windows SmartScreen meldet bei selbstgebauten, unsignierten `.exe` evtl. „unbekannter Herausgeber" → **Weitere Informationen → Trotzdem ausführen**. Wer das vermeiden will, gibt das `.py`-Skript weiter.

## Danksagung & Credits

Dieses Tool nutzt die Bauplan-Daten, die der **[SC Deutsch Launcher](https://www.sc-deutsch-launcher.de/)** ausliest und bereitstellt (`sc_bp_erledigt.json`). Ohne dieses Projekt gäbe es keine Datenquelle — **vielen Dank** an das Team hinter dem SC Deutsch Launcher für die Arbeit! 🙏

SC BP Watcher ist ein eigenständiges, inoffizielles Zusatz-Tool und steht in **keiner** offiziellen Verbindung zum SC Deutsch Launcher oder zu Cloud Imperium Games. Alle Marken- und Projektnamen gehören ihren jeweiligen Eigentümern.

## Author

[![Xharig](https://github.com/der Autor.png?size=40)](https://github.com/der Autor)
**Xharig** — [github.com/der Autor](https://github.com/der Autor)

If you fork this project, please keep the credit in the footer or mention the original source.

## Lizenz

MIT License. Details stehen in [LICENSE](LICENSE).
