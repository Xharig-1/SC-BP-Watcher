# Roadmap

Aktuelle Version: `v1.5.0`

## Zielbild

SC BP Watcher ist ein kleines Windows-Overlay, das beim Spielen von Star Citizen live anzeigt, sobald ein neuer Bauplan freigeschaltet wird. Fokus: zuverlässig, leichtgewichtig, ohne Zusatzpakete, einfach weiterzugeben.

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

## Was noch kommt

| | Inhalt |
|---|---|
| Als Nächstes | **Einstellungs- und Statusfenster** — Prüfintervall, Signalton, Pfade und Fensterlage im Fenster einstellen statt im Code |
| Als Nächstes | **Merkliste per Klick pflegen** — gewünschten Gegenstand suchen und auswählen, statt die `watchlist.json` von Hand zu schreiben. Die Liste aller craftbaren Dinge liegt dem Tool bereits vor |
| Als Nächstes | **Export des eigenen Bauplan-Bestands** als Datei, zum Hochladen bei Diensten, die Baupläne verwalten (scmdb.net, KRT Profit Basetool) |
| Als Nächstes | **Eigener Bauplan-Bestand** — die verbliebene Launcher-Abhängigkeit. Die Werte sind seit v1.5.0 gelöst; offen ist die Liste „welche habe ich", die aus der Spiel-Log fortgeschrieben und gespeichert wird (Grundstock einmalig übernehmen) |
| Als Nächstes | **Bauplan-Liste im Fenster** — den eigenen Bestand nachschlagen und sortieren, statt ihn nur als Meldung vorbeiziehen zu sehen |
| Geplant | **Autostart und Ablage-Symbol** (Tray) — sinnvoll nur zusammen: ein dauerhaft laufendes Overlay ohne Ablage nervt |
| Geplant | **Englische Oberfläche** und englischsprachige Anleitung. Die Erkennung im Log soll dabei die Spielsprache automatisch berücksichtigen |
| Idee | **Bauplan-Häkchen direkt im Spiel**, in den Missions-Beschreibungen |
| Idee | Kurzmeldung über die Windows-Benachrichtigungen, Verlauf der letzten Sitzung speichern |

## Bewusst nicht geplant

**Kein Ersatz für den SC Deutsch Launcher.** Welche Baupläne *du* freigeschaltet hast, hängt an deinem Konto — diese Liste kann kein externes Werkzeug herbeizaubern, sie kommt vom Launcher. Ein selbst geführter Bestand ließe sich nur „ab heute" fortschreiben und würde still ungenau, sobald jemand ohne laufenden Watcher spielt.

Das Ziel ist deshalb **Wahlfreiheit, nicht Ersatz**: ohne Launcher soll der Watcher benutzbar sein, mit Launcher bleibt er genauer.

## Mitreden

Wünsche, Fehlermeldungen und Ideen gern als [Issue](../../issues).
