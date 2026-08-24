<div align="center">

<img src="assets/icon.png" alt="SC BP Watcher Icon" width="128">

# SC BP Watcher

**Live-Overlay, das neue Star-Citizen-Baupläne anzeigt, sobald du sie freischaltest**

[![Version](https://img.shields.io/badge/Version-1.5.0-5fa522)](CHANGELOG.md)
[![Lizenz](https://img.shields.io/badge/Lizenz-GPL--3.0-5fa522)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-0a4a7a?logo=python&logoColor=white)](https://www.python.org/)
[![Star Citizen](https://img.shields.io/badge/Star%20Citizen-kompatibel-0a4a7a)](https://robertsspaceindustries.com/)

</div>

---

Ein kleines, randloses Overlay, das beim Spielen **in Echtzeit** meldet, sobald ein neuer Bauplan (Blueprint) dazukommt — inklusive Name, Art und Uhrzeit. Ohne Account, ohne Cloud, ohne Installation. Läuft unter **Windows und Linux**.

> ℹ️ **Der SC Deutsch Launcher ist nicht mehr Voraussetzung.** Die eigentliche Quelle ist die `Game.log` von Star Citizen — dort steht jeder freigeschaltete Bauplan im Klartext. Ist der Launcher da, wird er weiter genutzt: Er bestätigt die Funde und liefert deutsche Bezeichnungen. Ist er nicht da (unter Linux immer), läuft der Watcher trotzdem.

## Warum dieses Tool

Bauplan-Listen gibt es mehrere. Vier Dinge machen den Unterschied im Alltag:

- **Du musst nicht aus dem Spiel.** Das Overlay liegt über Star Citizen. Kein zweites Fenster, kein Alt-Tab, kein Nachschlagen im Browser — der neue Bauplan steht einfach da, während du weiterspielst.
- **Sofort *und* verlässlich.** Zwei Quellen laufen parallel: die Spiel-Log meldet den Fund in **Sekunden** (🟡), die Launcher-Datei bestätigt ihn kurz darauf mit den vollständigen Daten (🟢). Du wartest weder auf den nächsten Export, noch musst du dich auf eine Momentaufnahme verlassen.
- **Es meldet auch, was du noch gar nicht haben kannst.** Die Katalog-Wache erkennt, wenn CIG mit einem Patch etwas **neu craftbar** macht — unabhängig von deinem eigenen Freischalt-Stand (🔵). Wer auf ein bestimmtes Teil wartet, trägt es in die Beobachtungsliste ein und wird beim Auftauchen auffällig darauf gestoßen (⭐).
- **Nichts verlässt deinen Rechner.** Kein Konto, keine Anmeldung, keine Cloud, keine Installation. Das Tool liest ausschließlich Dateien, die ohnehin auf deiner Platte liegen, und schreibt nichts zurück ins Spiel.

Dazu: Klasse, Gütegrad und Größe stehen direkt in der Zeile (`M/A/1`), und das Ganze läuft mit reiner Python-Standardbibliothek — keine Zusatzpakete, keine Abhängigkeiten, die morgen zerbrechen.

## Features

| | |
|---|---|
| ⚡ **Sofort-Meldung** | Liest die Star-Citizen-`Game.log` mit → der Bauplan steht **in Sekunden** in der Liste, statt erst nach dem nächsten Launcher-Export (das dauert mehrere Minuten) |
| 🟡 → 🟢 **Zwei Stufen** | Frisch aus der Log gelesen = 🟡 *vorläufig*; sobald der Launcher nachzieht = 🟢 bestätigt und mit dessen Daten aufgefrischt |
| 🟢 **Live-Erkennung** | Prüft alle 3 Sekunden die Launcher-Datei; neue Baupläne erscheinen oben in der Liste |
| 🔵 **Katalog-Wache** | Meldet auch, wenn im **Spiel** etwas neu craftbar wird — also wenn CIG einen Bauplan nachreicht, den es vorher gar nicht gab (nicht nur, was du selbst freischaltest) |
| ⭐ **Beobachtungsliste** | Gegenstände, auf die du wartest, werden bei ihrem Auftauchen auffällig in Gold gemeldet — optionale `watchlist.json` |
| 🏷️ **Size · Grade · Klasse** | Kompakt-Kürzel `Klasse/Grade/Size` je Bauplan, z. B. `M/A/1` (Military · Grade A · Size 1) |
| 🔔 **Signalton** | Kurzer Ton bei jedem Neuzugang — du musst nicht aufs Fenster schauen |
| 🧷 **Immer im Vordergrund** | Randloses, leicht durchscheinendes Overlay über dem Spiel |
| 🖱️ **Verschiebbar & skalierbar** | An der Titelleiste ziehen, Größe am Griff ◢ unten rechts — **Position & Größe werden gemerkt** |
| 🌐 **Zweisprachig** | Zeigt die Art genau so an, wie der Launcher sie liefert (deutsch oder englisch) |
| 🔒 **Nur lesend** | Verändert am Spiel nichts — liest die `Game.log` und, falls vorhanden, die Launcher-Dateien |
| 📒 **Eigener Bestand** | Führt selbst Buch, welche Baupläne du hast — auch ohne den SC Deutsch Launcher |
| 🕓 **Nachlese** | Liest beim Start die aufgehobenen Logs früherer Sitzungen und holt nach, was ohne laufenden Watcher freigeschaltet wurde |
| 🐧 **Windows und Linux** | Eine Fassung für beide Systeme, inklusive Autostart und Spracherkennung im Log |

## Voraussetzungen

- **Windows oder Linux**
- **Star Citizen** installiert — gesucht wird der Ordner mit der `Game.log` darin. Unter Linux werden die üblichen Wine-Präfixe abgesucht (lug-helper, Lutris, Bottles, Heroic). Liegt das Spiel woanders, hilft die Umgebungsvariable `SC_INSTALL_DIR`.
- Zum Start als Skript: **Python 3.8+** (für die fertigen Pakete nicht nötig). Unter Linux zusätzlich das Paket `tk` — `SC-BP-Watcher starten.sh` sagt dir, wie es heißt, falls es fehlt.

**Optional, aber nützlich:** der **[SC Deutsch Launcher](https://www.sc-deutsch-launcher.de/)** (nur Windows). Mit ihm werden Funde zusätzlich bestätigt und die Bezeichnungen kommen auf Deutsch.

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

1. **Beim Start** sieht das Tool die aufgehobenen Logs vergangener Sitzungen durch (`logbackups/`) und übernimmt alles Gefundene still in deinen Bestand — wer ohne laufenden Watcher gespielt hat, verliert nichts. Diese Baupläne werden **nicht** als neu gemeldet. Reichen die Sicherungen nicht weit genug zurück, sagt der Watcher das als ℹ-Zeile, statt eine unvollständige Liste als vollständig auszugeben.
2. **Im Hintergrund** (eigener Thread) laufen alle 3 Sekunden zwei Prüfungen:
   - **`Game.log`** — schreibt das Spiel beim Freischalten `Added notification "Bauplan erhalten: <Name>: "`, erscheint der Bauplan **sofort** als 🟡 *vorläufig*.
   - **`sc_bp_erledigt.json`** — *sofern der SC Deutsch Launcher vorhanden ist.* Taucht der Name dort auf, wird die Zeile auf 🟢 bestätigt. Baupläne, die nur dort stehen, landen direkt als 🟢 in der Liste. Ohne Launcher entfällt dieser Schritt und die Meldung aus dem Log ist endgültig.
3. Jede neue Zeile wird oben eingefügt (Name · Art · `M/A/1` · Uhrzeit) und ein kurzer Ton gespielt.
   - **Einmal pro Minute** kommt eine dritte Prüfung dazu: Ist `bp_item_types.json` gewachsen, ist im Spiel etwas **neu craftbar** geworden → 🔵-Zeile. Das hat nichts mit deinem Freischalt-Stand zu tun; solche Zeilen werden deshalb nie auf 🟢 bestätigt. Der Vergleichsstand liegt in `%APPDATA%\sc-bp-watcher\catalog-seen.json` und überlebt Neustarts; beim allerersten Start wird nur die Basis gesetzt.
4. Die **Art** kommt aus `bp_item_types.json` (oder von scmdb, wenn kein Launcher da ist); **Size/Grade/Klasse** aus dem Launcher-Katalog (`catalog\components.ini` + `items_raw.ini`), bei Bedarf überschrieben durch die eigene `bp-overrides.json`.
5. **Dein Bestand** wächst dabei mit und bleibt in `bestand.json` erhalten — mit Vermerk, woher jeder Bauplan stammt (Log, Nachlese, Launcher). Das ist die Liste „welche habe ich", die bisher allein vom Launcher kam.

> **Warum zwei Quellen?** Der Launcher liest dieselbe `Game.log`, exportiert seine Datei aber nur alle paar Minuten. Gemessen am 30.07.2026: Freischaltung im Spiel **21:23:49** → Launcher-Export **21:26:24** = **2,5 Minuten** Verzug. Die Log-Mitlesung schließt diese Lücke, die gepflegten Werte kommen weiter vom Launcher.

Überwachte Dateien:

```text
…\StarCitizen\LIVE\Game.log                 (Spiel — die eigentliche Quelle)
…\StarCitizen\LIVE\logbackups\             (frühere Sitzungen, beim Start nachgelesen)
…\sc-deutsch-launcher\blueprints\           (optional: bestätigt und liefert deutsche Namen)
```

Eigene Dateien (Bestand, Einstellungen, Zwischenspeicher) liegen hier:

| System | Ordner |
|---|---|
| Windows | `%APPDATA%\sc-bp-watcher\` |
| Linux | `~/.config/sc-bp-watcher/` |

Beides lässt sich mit der Umgebungsvariablen `SC_BP_HOME` verlegen.

### Eigene Pfade eintragen

Liegt Star Citizen (oder der SC Deutsch Launcher) nicht an einer der üblichen Stellen, trägst du den Ordner selbst ein — in `einstellungen.json` im Ordner oben:

```json
{
  "spiel_ordner": "D:\\Spiele\\StarCitizen\\LIVE",
  "launcher_ordner": ""
}
```

In `spiel_ordner` gehört der Ordner, in dem die `Game.log` liegt (meist `LIVE`). Ein leeres Feld heißt „bitte suchen". Nach dem Ändern den Watcher neu starten.

> Findet der Watcher das Spiel nicht, legt er diese Datei beim Start **von selbst** an und sagt dir, wo sie liegt — du musst sie nicht von Hand erzeugen. In der Datei stehen bei jedem Feld die Orte, an denen gesucht wurde; dieselben nennt auch das Fenster. So siehst du, wie so ein Pfad auf deinem System aussieht, statt ihn raten zu müssen.

### Auf bestimmte Gegenstände warten

Wartest du auf einen ganz bestimmten Bauplan, den es noch gar nicht gibt, leg dir
`%APPDATA%\sc-bp-watcher\watchlist.json` an:

```json
{
  "eintraege": [
    { "titel": "Helm für den schweren Anzug", "muster": ["manticore helmet"] },
    { "titel": "Kühler, egal welcher", "muster": ["cooler"] }
  ]
}
```

Ein Eintrag besteht aus einem frei gewählten **Titel** (der steht später in der Meldung) und
beliebig vielen **Mustern**. Die Muster werden **kleingeschrieben** als Teilstring gegen jeden
neuen Katalog-Eintrag geprüft — `cooler` trifft also auf jeden Kühler, `manticore helmet` nur
auf diesen einen. Ein Treffer wird auffällig in Gold mit ⭐ und eigenem Signalton gemeldet
(`<Titel> — jetzt craftbar!`).

Ohne die Datei meldet der Watcher einfach jeden Zuwachs — sie ist rein optional.

> 🔜 Das von Hand zu schreiben ist umständlich, das ist uns bewusst. Geplant ist ein Fenster, in
> dem man den gewünschten Gegenstand sucht und per Klick auf die Merkliste setzt — die Liste
> aller craftbaren Dinge kennt das Tool ohnehin schon.

Der Launcher-Pfad wird über `%APPDATA%` gefunden, der Spiel-Pfad über den `Installfolder` aus `scdl-settings.json` (ersatzweise `scan-state.json` oder der Standard-Installationspfad). Ein Spiel-Neustart (neue, kürzere Log) wird erkannt.

> ℹ️ **Spielsprache:** Die Meldung im Log ist übersetzt. Der Watcher sucht nach deutschen und englischen Formulierungen; liegt eine entpackte `global.ini` deiner Installation vor, nimmt er den Wortlaut exakt daraus. Fehlt deine Formulierung, trag sie in `phrasen.json` im eigenen Ordner ein: `{"phrasen": ["Blueprint Received"]}`.

## Einstellungen

Oben in `sc_bp_watcher.py` anpassbar:

| Variable | Bedeutung | Standard |
|----------|-----------|----------|
| `POLL_SEC` | Prüf-Intervall in Sekunden (Launcher-Datei **und** Game.log) | `3` |
| `CAT_POLL` | Prüf-Intervall in Sekunden für den Craftbar-Katalog (ändert sich nur bei Patches) | `60` |
| `MAX_ROWS` | max. Einträge in der Liste (ältere fliegen unten raus) | `200` |
| `LOG_PHRASES` | Spielmeldung(en), an denen ein neuer Bauplan erkannt wird | `Bauplan erhalten` |
| `DEFAULT_GEOM` | Start-Position/-Größe beim allerersten Start (danach wird die gemerkte Lage genutzt) | `440x1098`, oberer Monitor |
| `CLASS_LETTER` | Kürzel je Klasse (M/S/I/C/K) | Military/Stealth/Industrial/Civilian/Competition |
| `BG / FG / ACCENT / …` | Farben des Overlays | dunkel + Xharig-Grün |

> Position & Größe merkt sich der Watcher beim Verschieben und Beenden (`watcher.json` im eigenen Ordner) — zieh das Fenster einfach dorthin, wo du es haben willst. Eine feste Startposition gibt das Programm bewusst **nicht** vor: Wo ein Overlay gut sitzt, hängt am Monitoraufbau. Zum Zurücksetzen die Datei löschen.
>
> Im selben Ordner liegen `catalog-seen.json` (Vergleichsstand der Katalog-Wache) und optional `watchlist.json`. Löschst du `catalog-seen.json`, wird beim nächsten Start nur die Basis neu gesetzt — es kommt also keine Meldungsflut.
>
> **Eigene Korrekturen (ab v1.4.0):** Stimmt bei einem Bauplan die Angabe zu Klasse, Größe oder Gütegrad nicht, kannst du sie in `%APPDATA%\sc-bp-watcher\bp-overrides.json` überschreiben — sie hat Vorrang vor dem Launcher-Katalog. Liegt die Datei woanders, gib den Pfad über die Umgebungsvariable `SC_BP_OVERRIDES` an. Ohne die Datei ändert sich nichts.

> **Werte aus dem Netz (ab v1.5.0):** Kennt der Launcher-Katalog einen Bauplan nicht, holt der Watcher Art, Größe, Gütegrad und Klasse von [scmdb.net](https://scmdb.net). Nachgeladen wird nur bei einer **neuen Spielversion**; der Stand liegt in `%APPDATA%\sc-bp-watcher\scmdb-items.json`. Ohne Internet gilt der letzte Stand — der Watcher läuft normal weiter. Wer gar keine Netzabfrage möchte, setzt die Umgebungsvariable `SC_BP_NO_NET=1`.
>
> Die Rangfolge ist bewusst so: **eigene Korrekturen → Launcher-Katalog → scmdb**. scmdb füllt nur Lücken und überschreibt nie — ein Abgleich gegen 56 Meldungen aus der Spiel-Log ergab 55 exakte Treffer und eine Abweichung.

> **Mit dem Rechner starten (ab v1.5.0):** Der Schalter `⏻` in der Titelleiste schaltet den Autostart ein und aus — grün heißt an, grau aus. Er ist standardmäßig **aus**; der Watcher trägt sich nie von selbst ein. Unter Windows ist es ein Eintrag unter `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, unter Linux die Datei `~/.config/autostart/sc-bp-watcher.desktop` — beides kannst du auch von Hand wieder löschen.

## Weitergeben

> 🔒 **Offline & privat** — das Tool arbeitet komplett ohne Internet. Es liest nur die lokale Bauplan-Liste des Launchers, verändert nichts und sendet nichts.

- **Als `.exe` (am einfachsten):** die fertige `SC-BP-Watcher.exe` von der **[Releases-Seite](../../releases)** weitergeben — Empfänger braucht **nur** den SC Deutsch Launcher, kein Python.
- **Als Skript:** `sc_bp_watcher.py` + die `.bat`-Dateien weitergeben (Empfänger braucht Python).

> ℹ️ Windows SmartScreen meldet bei selbstgebauten, unsignierten `.exe` evtl. „unbekannter Herausgeber" → **Weitere Informationen → Trotzdem ausführen**. Wer das vermeiden will, gibt das `.py`-Skript weiter.

## Danksagung & Credits

Dieses Tool nutzt die Bauplan-Daten, die der **[SC Deutsch Launcher](https://www.sc-deutsch-launcher.de/)** ausliest und bereitstellt (`sc_bp_erledigt.json`). Ohne dieses Projekt gäbe es keine Datenquelle — **vielen Dank** an das Team hinter dem SC Deutsch Launcher für die Arbeit! 🙏

Die Werte zu Art, Größe, Gütegrad und Klasse stammen ab v1.5.0 aus der **[Star Citizen Mission DataBase (scmdb.net)](https://scmdb.net)** — ein Hobbyprojekt, das die Spieldaten aufbereitet und frei zugänglich macht. **Herzlichen Dank** dafür! 🙏

> Der Watcher **liefert diese Daten nicht mit**, sondern lädt sie auf deinem Rechner direkt bei scmdb.net — so wie es ein Browser täte. scmdb steht unter [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/); eine mitgelieferte Kopie wäre eine Weitergabe und würde sowohl dieser Lizenz als auch der GPL dieses Projekts widersprechen. Abgerufen wird sparsam: nur, wenn eine **neue Spielversion** vorliegt.

SC BP Watcher ist ein eigenständiges, inoffizielles Zusatz-Tool und steht in **keiner** offiziellen Verbindung zum SC Deutsch Launcher oder zu Cloud Imperium Games. Alle Marken- und Projektnamen gehören ihren jeweiligen Eigentümern.

## Author

[![Xharig](https://github.com/der Autor.png?size=40)](https://github.com/der Autor)
**Xharig** — [github.com/der Autor](https://github.com/der Autor)

If you fork this project, please keep the credit in the footer or mention the original source.

## Was noch kommt

Ideen für die nächsten Fassungen — **ohne Zeitplan**, in loser Reihenfolge:

- **Einstellungsfenster** statt Werte im Code: Prüfintervall, Signalton, Pfade, Fensterlage
- **Beobachtungsliste im Fenster pflegen**, statt die `watchlist.json` von Hand zu bearbeiten
- **Export des eigenen Bauplan-Bestands** als Datei — zum Hochladen bei Diensten, die Baupläne verwalten (scmdb.net, KRT Profit Basetool)
- **Autostart und Ablage-Symbol** (Tray), damit das Overlay nicht dauernd im Weg ist
- **Englische Oberfläche** und englischsprachige Anleitung
- **Weniger Abhängigkeit vom SC Deutsch Launcher** — Typ, Größe, Gütegrad und Klasse direkt aus den Spieldateien lesen

Ausführlich mit Begründungen: [`ROADMAP.md`](ROADMAP.md). Wünsche und Fehlermeldungen gern als [Issue](../../issues).

## Star Citizen Fan Content

> This is an unofficial Star Citizen fan site, not affiliated with the Cloud Imperium group of
> companies. All content on this site not authored by its host or users are property of their
> respective owners.

SC BP Watcher ist ein inoffizielles, nicht-kommerzielles Fan-Projekt für die Star-Citizen-Gemeinschaft.
Star Citizen®, Roberts Space Industries® und Cloud Imperium® sind eingetragene Marken der
Cloud Imperium Rights LLC. Alle übrigen Star-Citizen-Inhalte, Grafiken, Namen, Logos und Marken
gehören ihren jeweiligen Eigentümern. © Cloud Imperium Rights LLC und Cloud Imperium Rights Ltd.

Offizielle Seite: **[robertsspaceindustries.com](https://robertsspaceindustries.com)**

## Lizenz

**GNU General Public License v3.0** — Volltext in [LICENSE](LICENSE).

Kurz: Du darfst das Programm nutzen, verändern und weitergeben. Wer es weitergibt — verändert
oder nicht —, muss den Quellcode unter derselben Lizenz mitliefern. Es gibt keine Garantie.
