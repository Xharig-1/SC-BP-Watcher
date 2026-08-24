# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

Das Projekt nutzt SemVer: `MAJOR.MINOR.PATCH`.

## Unveröffentlicht — Phase 1 des Neubaus („läuft ohne Launcher")

> Der Umbau nach dem Plan vom 23.08.2026. Diese Phase macht den Watcher vom
> SC Deutsch Launcher unabhängig und bringt ihn auf Linux. Noch **kein**
> Release — die erste öffentliche Fassung wird `v2.0.0` nach Phase 3.

### Hinzugefügt

- **Läuft unter Linux.** Eine Codebasis für beide Systeme, keine zweite Fassung. Wo die Dateien liegen, entscheidet der neue Baustein `scbp/pfade.py`: unter Windows `%APPDATA%` und `C:\Program Files`, unter Linux `~/.config` und das Wine-Präfix (gesucht wird an den Stellen, an denen lug-helper, Lutris, Bottles und Heroic ihre Installationen ablegen). Eigene Wege gehen über `SC_BP_HOME`, `SC_INSTALL_DIR` und `SC_BP_LAUNCHER`.
- **Eigener Bauplan-Bestand** (`bestand.json` im eigenen Ordner). Jeder Fund wird dauerhaft festgehalten, mit Herkunft (Log, Nachlese, Launcher, von Hand). Geschrieben wird über eine Nebendatei und Umbenennen, damit ein Absturz mitten im Speichern nichts zerreißt; die Vorgängerfassung bleibt als `bestand.bak.json` liegen.
- **Nachlese beim Start.** Die aufgehobenen Logs vergangener Sitzungen (`logbackups/`) werden durchgesehen und still in den Bestand übernommen — wer ohne laufenden Watcher gespielt hat, verliert nichts mehr. Beim allerersten Start wird auch die **laufende** Game.log von vorn gelesen, sonst wäre ausgerechnet die gerade laufende Sitzung ein Loch.
- **Ehrlicher Lückenhinweis.** Reichen die vorhandenen Sicherungen nicht bis zum letzten bekannten Stand zurück, sagt der Watcher das als eigene Zeile (ℹ) — statt eine unvollständige Liste als Bestand auszugeben. Das ist der Grund, warum es in Phase 2 die Liste zum Abhaken gibt.
- **Lesestand übersteht Neustarts** (`logstand.json`). Wer den Watcher neu startet, während Star Citizen läuft, verliert die Baupläne dieser Sitzung nicht mehr.
- **Spracherkennung statt fester deutscher Phrase** (`scbp/phrasen.py`). Gesucht wird nach einer Tabelle deutscher und englischer Formulierungen; liegt eine entpackte `global.ini` vor, wird der Wortlaut daraus exakt übernommen (Schlüssel `crafting_hud_notification_received_blueprint`). Eigene Ergänzungen gehen in `phrasen.json`. Bis v1.5.0 griff die Sofort-Meldung bei englischem Client gar nicht — unter Linux spielen die meisten auf Englisch.
- **Autostart auf beiden Systemen** (`scbp/autostart.py`): unter Windows wie bisher der Registry-Wert, unter Linux eine `.desktop`-Datei in `~/.config/autostart/`.
- **Startskript für Linux** (`SC-BP-Watcher starten.sh`) als Gegenstück zur `.bat` — prüft vorher, ob `tkinter` da ist, und nennt sonst den passenden Paketbefehl je Distribution.
- **Eigene Pfade eintragbar** (`einstellungen.json` im eigenen Ordner). Wer Star Citizen oder den Launcher woanders liegen hat, trägt den Ordner dort ein, statt auf die Suche angewiesen zu sein. Findet der Watcher das Spiel nicht, legt er die Datei beim Start selbst an und nennt sie in der Fehlermeldung. Rangfolge: Umgebungsvariable → Einstellungsdatei → Suche an den üblichen Stellen.
  - **Die durchsuchten Orte werden genannt** — ausgegraut im Fenster und als Zeile direkt unter dem jeweiligen Feld in der Datei. Ohne dieses Vorbild müsste man den einzutragenden Pfad raten; gerade wenn nichts gefunden wurde, hat man ja keinen zum Abschauen. Findet der Rechner keinen einzigen Wine-Präfix, werden trotzdem die typischen Orte gezeigt statt einer leeren Liste.
- **Selbsttest** (`tools/selbsttest.py`). Baut eine Spielinstallation im Wegwerf-Ordner nach und prüft die Erkennung samt ihrer bekannten Fallstricke.

### Behoben

- **Der Watcher wäre unter Linux beim Start abgestürzt.** Der Mauszeiger `size_nw_se` am Größengriff gibt es nur unter Windows; auf anderen Systemen wirft Tk dafür einen Fehler, bevor das Fenster überhaupt erscheint.
- **Fensterlage vom fremden Rechner.** Die gemerkte Position wurde ungeprüft übernommen. Auf einem Rechner mit anderem Monitoraufbau stand das Fenster damit außerhalb jedes Bildschirms — unsichtbar, unter macOS mit Absturz. Sie wird jetzt auf Plausibilität geprüft; die Vorgabe im Code enthält **gar keine Position** mehr, sondern nur noch eine Größe. Wo das Fenster stehen soll, zieht sich jeder selbst hin.
- **Endlosschleife ohne Launcher.** Beim Start wartete der Watcher, bis die Launcher-Datei lesbar war — ohne Launcher also ewig. Unter Linux wäre er nie hochgekommen.
- **Katalog-Wache lief ohne Launcher ins Leere.** „Was ist im Spiel neu craftbar" hing an einer Launcher-Datei. Fehlt sie, treten jetzt die scmdb-Craftdaten an ihre Stelle, die ohnehin schon vorliegen.
- **Signalton ohne `winsound`.** Unter Linux gibt es das Modul nicht; dort klingelt jetzt tkinter selbst.

### Geändert

- **Die Statuszeile zeigt den eigenen Bestand**, nicht mehr die Launcher-Zahl, und dazu, ob mit oder ohne Launcher gearbeitet wird. Grund: Der Launcher zählt nachweislich zu niedrig — ihm fehlt die P4-AR Rifle, obwohl sie im Fabricator als „im Besitz" steht (gemessen 11.08.2026). Startbaupläne wurden nie „erhalten" und stehen in keinem Log.
- **Der SC Deutsch Launcher ist optional.** Ist er da, wird er weiter genutzt: Er bestätigt die Funde (🟡 → 🟢) und liefert den gepflegten Katalog. Fehlt er, entfällt nur das — gemeldet wird trotzdem, denn die Game.log ist die eigentliche Quelle.
- **Startbedingung.** Der Watcher verlangt beim Start nicht mehr die Launcher-Datei, sondern nur noch, dass Star Citizen selbst gefunden wird.

## v1.5.0 - 2026-08-11

### Hinzugefügt

- **Werte-Rückfall über scmdb.net.** Kennt der Launcher-Katalog einen Gegenstand nicht, holt der Watcher Art, Größe, Gütegrad, Klasse und Hersteller jetzt aus den Craftdaten von scmdb (`versions.json` → `crafting_items-<version>.json`). Damit bekommen auch Baupläne ein Kürzel, die im Katalog fehlen — z. B. **QuadraCell**, **FR-66** und die Skin-Varianten. Reines `urllib` aus der Standardbibliothek, kein Zusatzpaket.
  - Zwischenspeicher: `%APPDATA%\sc-bp-watcher\scmdb-items.json`; neu geholt wird nur bei einer **neuen Spielversion** (Prüfung alle 6 Stunden).
  - Ohne Netz gilt der letzte Stand, ohne Zwischenspeicher läuft alles wie vor v1.5.0 — der Watcher bricht nie deswegen ab.
  - Abschaltbar über die Umgebungsvariable `SC_BP_NO_NET=1`.
- **Mit Windows starten — freiwillig.** Neuer Schalter `⏻` in der Titelleiste (grün = an, grau = aus). Er trägt den Watcher unter `HKCU\…\CurrentVersion\Run` ein bzw. wieder aus. Nichts wird ungefragt aktiviert, und der Zustand steht ausschließlich in der Registry — es gibt keine zweite Wahrheit, die damit auseinanderlaufen könnte.
  - Aus dem Quellcode heraus wird `pythonw.exe` eingetragen, nicht `python.exe`: Sonst stünde bei jedem Anmelden ein Konsolenfenster offen, das im Spiel den Fokus klaut.

- **Neues App-Icon.** Dunkles Rundemblem im Xharig-Grün: segmentierter Scanner-Ring, Blaupausen-Blatt mit Würfel, waagerechter Scanstrahl. Gebaut von `tools/make_icon_from_art.py` aus zwei Vorlagen — einer detaillierten ab 40 Pixel und einer **vereinfachten für 16–32 Pixel** (massiver Würfel statt Drahtgitter, keine Eckklammern). Ein einziges Motiv über alle Größen wäre klein zu Matsch zerfallen.

### Wissenswert

- **Rangfolge der Quellen:** `bp-overrides.json` → Launcher-Katalog/Spieldaten → scmdb. scmdb füllt nur Lücken und überschreibt nie. Grund: Ein Abgleich am 11.08.2026 gegen 56 Meldungen aus der Spiel-Log ergab **55 exakte Treffer** bei Größe, Gütegrad und Klasse — beim Kühler **Elsen** nennt scmdb aber Grad A, während die Spiel-Log *und* `components.ini` übereinstimmend B sagen (auch der Hersteller stimmt dort nicht). Sehr gute Quelle, aber keine unfehlbare.
- **Die scmdb-Daten werden bewusst NICHT mitgeliefert**, sondern auf dem Rechner des Nutzers direkt bei scmdb.net geholt — so wie es ein Browser täte. scmdb steht unter CC BY-NC-ND 4.0; eine mitgelieferte Kopie wäre eine Weitergabe und würde sowohl dieser Lizenz als auch der GPL dieses Projekts widersprechen. Der Abruf trägt eine ehrliche Kennung (`SC-BP-Watcher/<Version>` mit Projektadresse), damit der Betreiber sieht, wer abruft. Dank an scmdb steht in der `README.md`.
- **Rüstung und FPS-Waffen bekommen weiterhin kein Kürzel.** scmdb vergibt `size` und `grade` an jeden Gegenstand, auch an Helme — ungefiltert übernommen stünde hinter jedem Rüstungsteil ein erfundenes „Grade A, Size 1". Klasse und Gütegrad werden deshalb nur übernommen, wenn scmdb eine `componentClass` führt (echte Schiffskomponenten); Schiffswaffen bekommen nur die Größe.

## v1.4.0 - 2026-08-02

### Geändert

- **Lizenzwechsel von MIT auf GNU GPL v3.0** (nur Version 3, `SPDX-License-Identifier: GPL-3.0-only`). Der Quellcode wird offengelegt: ein einziges öffentliches Repo statt der geplanten Trennung in privates Quell- und öffentliches Auslieferungs-Repo. Die GPL erlaubt Nutzung und Änderung durch jeden, verlangt bei Weitergabe aber die Offenlegung des Quellcodes unter derselben Lizenz.
- `README.md`: neuer Abschnitt **„Star Citizen Fan Content"** mit dem von RSI vorgeschriebenen Wortlaut und dem Link zur offiziellen Seite — Voraussetzung für eine öffentliche Weitergabe.

### Behoben

- **Fest verdrahteter lokaler Pfad entfernt.** `OVERRIDES_FILE` zeigte auf ein Verzeichnis, das es nur auf dem Rechner des Entwicklers gibt — bei allen anderen lief die Datei ins Leere, und mit der Offenlegung wäre der Pfad öffentlich geworden. Die optionale Overrides-Datei wird jetzt unter `%APPDATA%\sc-bp-watcher\bp-overrides.json` gesucht; ein abweichender Ort lässt sich über die Umgebungsvariable `SC_BP_OVERRIDES` angeben. Fehlt beides, gilt der Launcher-Katalog unverändert.

## v1.3.0 - 2026-07-31

### Hinzugefügt

- **Katalog-Wache — meldet, was im Spiel NEU craftbar geworden ist.** Bisher meldete der Watcher nur, was *du* freischaltest. Jetzt behält er zusätzlich `bp_item_types.json` im Auge — die Liste dessen, was überhaupt einen Bauplan hat. Der SC Deutsch Launcher frischt sie mit den Patches auf; kommt etwas dazu, erscheint es als 🔵 **neu im Spiel craftbar**. So bekommt man mit, wenn CIG einen Gegenstand nachreicht, den es vorher schlicht nicht als Bauplan gab.
- **Beobachtungsliste für Wunsch-Gegenstände:** Liegt `%APPDATA%\sc-bp-watcher\watchlist.json`, werden Treffer daraus auffällig in Gold mit ⭐ und eigenem Signalton gemeldet (`<Titel> — jetzt craftbar!`). Format: `{"eintraege": [{"titel": "…", "muster": ["teilstring", …]}]}`, Muster kleingeschrieben, Treffer per Teilstring. Ohne die Datei meldet der Watcher einfach jeden Zuwachs.
- Der Vergleichsstand liegt in `%APPDATA%\sc-bp-watcher\catalog-seen.json` und **überlebt Neustarts** — sonst käme nach jedem Programmstart der halbe Katalog als „neu". Beim allerersten Start wird nur die Basis gesetzt, es wird nichts gemeldet.

### Behoben

- **Breiterziehen brachte nichts:** Die Breite der Liste war mit `312` Pixeln fest verdrahtet (`create_window(..., width=312)`). Wer das Fenster breiter zog, bekam trotzdem denselben schmalen Inhalt — lange Bauplan-Namen blieben abgeschnitten. Die Liste zieht jetzt bei jeder Größenänderung mit; lange Untertitel brechen um, statt am Rand zu verschwinden.
- **Standardgröße** von `341x1098` auf `440x1098` erhöht (rechte Fensterkante bleibt gleich), damit die längeren Meldungen der Katalog-Wache ohne Umbruch passen.

### Hinweise

- Die Katalogdatei wird nur **einmal pro Minute** und auch dann nur bei geändertem Zeitstempel gelesen (`CAT_POLL`) — sie ändert sich ohnehin nur bei Patches.
- Katalog-Zeilen sind reine Meldungen: Sie werden nie auf 🟢 „bestätigt", weil sie nichts mit dem eigenen Freischalt-Stand zu tun haben.
- Der Watcher führt seinen Katalogstand in einer **eigenen** Datei — so nimmt ein zweites Werkzeug auf denselben Daten ihm nicht die Meldung weg.

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

- **Size / Grade / Klasse je Bauplan** als Kompakt-Kürzel `Klasse/Grade/Size`, z. B. `M/A/1` (Military · Grade A · Size 1). Kürzel: **M** Military, **S** Stealth, **I** Industrial, **C** Civilian, **K** Competition. Schiffswaffen haben nur Size → `–/–/2`; FPS-Waffen und Rüstung haben nichts davon → kein Kürzel. Datenbasis: Launcher-Katalog `catalog\components.ini` + `items_raw.ini`, plus manuelle Korrekturen aus `bp-overrides.json` (Vorrang).
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

- **App-Icon** im Xharig-Stil (dunkler Grund, Xharig-Grün, Scope-Ring mit „neu"-Punkt) — `icon.ico` für die EXE, `assets/icon.png` als Vorschau
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
