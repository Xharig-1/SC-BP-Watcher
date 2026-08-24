# Roadmap

Aktuelle Version: `v1.5.0` · in Arbeit: **Phase 1 des Neubaus** (läuft ohne Launcher, läuft unter Linux) — erste öffentliche Fassung wird `v2.0.0`

## Zielbild

SC BP Watcher ist ein kleines Overlay, das beim Spielen von Star Citizen live anzeigt, sobald ein neuer Bauplan freigeschaltet wird — unter **Windows und Linux**, aus einer gemeinsamen Codebasis. Fokus: zuverlässig, leichtgewichtig, ohne Zusatzpakete, einfach weiterzugeben.

Reihenfolge und Umfang können sich ändern — **Termine gibt es hier bewusst keine.**

## Was schon läuft

| | Inhalt |
|---|---|
| ✅ | Live-Erkennung neuer Baupläne aus der Launcher-Datei, Anzeige im Overlay |
| ✅ | Signalton, verschiebbares und skalierbares Fenster, Liste leeren |
| ✅ | Weitergabe als `.exe` (kein Python beim Empfänger nötig) |
| ✅ | Kürzel für Klasse, Gütegrad und Größe (`M/A/1`), gemerkte Fensterlage |
| ✅ | Sofort-Meldung aus der Spiel-Log (🟡 vorläufig → 🟢 bestätigt) |
| ✅ | Katalog-Wache: meldet, was im Spiel **neu craftbar** wird (🔵) — dazu die Beobachtungsliste für Wunsch-Gegenstände (⭐) |
| ✅ | **Werte ohne den Launcher-Katalog** — Art, Größe, Gütegrad und Klasse kommen bei Bedarf von scmdb.net (v1.5.0) |
| ✅ | **Läuft ohne den SC Deutsch Launcher** — eigener Bauplan-Bestand, aus der Game.log fortgeschrieben, mit Nachlese der aufgehobenen Sitzungen (Phase 1) |
| ✅ | **Läuft unter Linux** — dieselbe Fassung wie unter Windows, inklusive Autostart und Spracherkennung im Log (Phase 1) |

## Was noch kommt

| | Inhalt |
|---|---|
| Als Nächstes | **Einstellungs- und Statusfenster** — Prüfintervall, Signalton, Pfade und Fensterlage im Fenster einstellen statt im Code |
| Als Nächstes | **Merkliste per Klick pflegen** — gewünschten Gegenstand suchen und auswählen, statt die `watchlist.json` von Hand zu schreiben. Die Liste aller craftbaren Dinge liegt dem Tool bereits vor |
| Als Nächstes | **Export des eigenen Bauplan-Bestands** als Datei, zum Hochladen bei Diensten, die Baupläne verwalten (scmdb.net, KRT Profit Basetool) |
| Als Nächstes | **Bauplan-Liste im Fenster** (Phase 2) — den eigenen Bestand durchsuchen, nach Art gruppieren und filtern (alle / habe ich / fehlt mir), Häkchen von Hand setzen. Damit lässt sich auch der Grundstock nachtragen, den keine Log-Sicherung mehr hergibt |
| Als Nächstes | **Herkunft je Bauplan** (Phase 2) — Fraktion, Auftrag, Mindest-Ruf, Belohnung und Annahmeort. Die Daten liegen bei scmdb vollständig vor (719 Einträge, geprüft 23.08.2026). Das kann der SC Deutsch Launcher nicht |
| Als Nächstes | **Fortschrittsanzeige** — „392 von 716 (55 %)", je Art aufgeschlüsselt |
| Geplant | **Ablage-Symbol (Tray)** — der Autostart selbst steht seit Phase 1 auf beiden Systemen |
| Geplant | **Englische Oberfläche** und englischsprachige Anleitung (Phase 3). Die Erkennung im Log berücksichtigt die Spielsprache seit Phase 1 bereits |
| Geplant | **AppImage und portable `.exe`** aus demselben Tag, gebaut von GitHub Actions (Phase 3) |
| Idee | **Bauplan-Häkchen direkt im Spiel**, in den Missions-Beschreibungen |
| Idee | **Herkunft je Bauplan einblendbar** — ein Klick zeigt Fraktion, Auftrag, Belohnung, Annahmeort und nötigen Ruf. Bewusst **nicht** dauerhaft in der Zeile und **nicht** als Einspielung in die Spieldateien: Die `global.ini` gehört dem SC Deutsch Launcher, und der Watcher soll lesen statt die Installation zu verändern |
| Idee | Kurzmeldung über die Windows-Benachrichtigungen, Verlauf der letzten Sitzung speichern |

## Verhältnis zum SC Deutsch Launcher

**Wahlfreiheit, nicht Ersatz** — aber anders begründet als früher.

Hier stand lange, ein selbst geführter Bestand sei zwangsläufig ungenau, weil er nur „ab heute" fortgeschrieben werden könne. Zwei Messungen haben das widerlegt:

- Der Watcher liest beim Start die **aufgehobenen Logs** nach. Ohne laufenden Watcher gespielt zu haben, reißt also kein Loch, solange Star Citizen die Sicherung noch hat. Bleibt doch eine Lücke, wird sie **gesagt** statt verschwiegen.
- Der Launcher selbst zählt **zu niedrig**: Ihm fehlt die P4-AR Rifle, obwohl sie im Fabricator als „im Besitz" steht (11.08.2026). Startbaupläne wurden nie „erhalten" und stehen in keinem Log. Seine Zahl ist eine Untergrenze, kein Bestand.

Der Launcher bleibt trotzdem nützlich: Er bestätigt Funde und pflegt einen Katalog mit deutschen Bezeichnungen. Ist er da, wird er genutzt. Ist er nicht da — unter Linux immer —, läuft der Watcher trotzdem.

## Mitreden

Wünsche, Fehlermeldungen und Ideen gern als [Issue](../../issues).
