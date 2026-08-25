# Roadmap

[English](ROADMAP.md) · **Deutsch**

## Zielbild

SC BP Watcher ist ein kleines Overlay, das beim Spielen von Star Citizen live anzeigt, sobald ein neuer Bauplan freigeschaltet wird — unter **Windows und Linux**, aus einer gemeinsamen Codebasis.

Vier Dinge sind Absicht und bleiben so:

- **Leichtgewichtig.** Reine Python-Standardbibliothek, keine Zusatzpakete. Was keine Abhängigkeit hat, kann auch keine verlieren.
- **Es gehört dir.** Kein Konto, keine Anmeldung, keine Cloud. Was das Werkzeug weiß, steht in Dateien auf deiner Platte.
- **Es liest, es schreibt nicht.** An der Spielinstallation wird nichts verändert.
- **Ehrlich statt hübsch.** Wenn etwas fehlen könnte, sagt es das — lieber eine unbequeme Auskunft als eine schöne Zahl, auf die kein Verlass ist.

## Was es kann

| | Inhalt |
|---|---|
| ✅ | Live-Erkennung neuer Baupläne aus der Spiel-Log, Anzeige im Overlay |
| ✅ | **Eigener Bauplan-Bestand** — der SC Deutsch Launcher ist nicht nötig |
| ✅ | **Nachlese**: beim Start werden frühere Spielsitzungen ausgewertet |
| ✅ | **Bauplan-Liste** zum Nachschlagen, Filtern und Abhaken, mit Fortschritt |
| ✅ | **Herkunft je Bauplan** — Fraktion, Auftrag, nötiger Ruf, Belohnung |
| ✅ | Katalog-Wache: meldet, was im Spiel **neu craftbar** wird, dazu eine Merkliste |
| ✅ | Kürzel für Klasse, Größe und Gütegrad (`M/1/A`) |
| ✅ | Einrichtungsassistent, jederzeit wiederholbar |
| ✅ | Deutsch und Englisch, umschaltbar |
| ✅ | Windows und Linux, mit Autostart auf beiden |
| ✅ | Bestand ausgeben — für das KRT Profit Basetool, für scmdb.net und als vollständige Sicherung |
| ✅ | Overlay einklappen, für alle mit einem Bildschirm |

## Woran gearbeitet wird

Ohne Zeitplan und ohne feste Reihenfolge — Stand der Dinge steht im [`CHANGELOG.de.md`](CHANGELOG.de.md), und im Fenster „Was ist neu" lässt sich nachlesen, was jede Fassung gebracht hat.

Gerade in Arbeit sind mehr Komfort beim Einrichten und ein Ablage-Symbol.

## Verhältnis zum SC Deutsch Launcher

**Wahlfreiheit, nicht Ersatz.**

Hier stand lange, ein selbst geführter Bestand sei zwangsläufig ungenau, weil er nur „ab heute" fortgeschrieben werden könne. Zwei Messungen haben das widerlegt:

- Der Watcher liest beim Start die **aufgehobenen Logs** nach. Ohne laufenden Watcher gespielt zu haben, reißt also kein Loch, solange Star Citizen die Sicherung noch hat. Bleibt doch eine Lücke, wird sie **gesagt** statt verschwiegen.
- Der Launcher selbst zählt **zu niedrig**: Ihm fehlt die P4-AR Rifle, obwohl sie im Fabricator als „im Besitz" steht. Startbaupläne wurden nie „erhalten" und stehen in keinem Log. Seine Zahl ist eine Untergrenze, kein Bestand.

Der Launcher bleibt trotzdem nützlich: Er bestätigt Funde und pflegt einen Katalog mit deutschen Bezeichnungen. Ist er da, wird er genutzt. Ist er nicht da — unter Linux immer —, läuft der Watcher trotzdem.

## Mitreden

Wünsche, Fehlermeldungen und Ideen gern als [Issue](../../issues).
