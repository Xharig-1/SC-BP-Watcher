# Changelog

[English](CHANGELOG.md) · **Deutsch**

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

Das Projekt nutzt SemVer: `MAJOR.MINOR.PATCH`.

## Unveröffentlicht

> Sammelt sich bis zum nächsten Veröffentlichungstag (samstags).

## v3.0.0-rc93 - 2026-08-28

### Behoben

- **Im Aufblend-Betrieb schwebte das Schloss neben dem Overlay.** Der Fix aus
  rc92 griff für alle, die das Overlay dauerhaft sehen — im Betrieb „nur bei
  einem Neuzugang" blieb es beim alten Verhalten.

  Der Grund: Dort wird das Overlay beim Start **versteckt**, bevor es je
  gezeichnet wurde. Damit gibt es keine Leiste, an der sich das Schloss
  ausrichten könnte, und die Ersatzrechnung nahm die Lage eines unsichtbaren
  Fensters — nachgemessen meldet ein nie gezeichnetes Fenster Breite 1 und
  Position 0. Das Schloss landete irgendwo neben dem Overlay.

  Es hängt jetzt an derselben gemerkten Position wie der Anfasser-Streifen, der
  im Aufblend-Betrieb ohnehin zeigt, wo das Overlay wartet — und rückt auf die
  Leiste, sobald das Overlay aufblendet.

  Gemeldet von **Haldjas (pr0)** am 28.08.2026. Sein Fehlerbericht hat es
  entschieden: Ohne die Zeile `overlay_modus=popup` darin wäre weiter geraten
  worden, warum es bei ihm auftritt und bei anderen nicht.

## v3.0.0-rc92 - 2026-08-28

### Behoben

- **Nach dem Start stand das Schloss neben dem Overlay statt darauf.** Wer das
  Durchreichen eingeschaltet gespeichert hatte, sah nach jedem Start **zwei**
  Schlösser: eines an der falschen Stelle neben dem Fenster, eines in der
  Leiste. Erst das erste Umschalten rückte es an seinen Platz — und beim
  nächsten Start ging es wieder von vorn los.

  Die Ursache ist eine alte `tkinter`-Falle: Der Zustand wird unmittelbar vor
  dem Start der Fensterschleife angewendet. Die Leiste steht da zwar schon im
  Baum, aber Tk hat noch nichts gezeichnet — weder „ist sichtbar" noch die Maße
  stimmen zu diesem Zeitpunkt. Das Schloss wurde also an einen geratenen Platz
  gesetzt.

  Jetzt wird **gewartet statt geraten**: Solange die Leiste noch nicht steht,
  wird gar kein Schloss gebaut, sondern nachgefasst, bis sie da ist. Ein kurz
  aufblitzendes falsches Schloss wäre nur die halbe Reparatur gewesen.

  Gemeldet von **Haldjas (pr0)** am 28.08.2026, mit dem vollständigen Ablauf zum
  Nachstellen: „Starte Watcher — Schloss ist an 2 Positionen … position bleibt so
  bis man den watcher neu startet".

## v3.0.0-rc91 - 2026-08-28

### Verbessert

- **Ein Schloss statt zwei.** Bisher saß das grüne Schloss in der Ecke des
  Overlays, während in der Leiste weiter ein offenes stand — zwei Schlösser,
  von denen eines das Gegenteil des wahren Zustands zeigte.

  Jetzt liegt das grüne Schloss **passgenau über** dem in der Leiste: gleiche
  Stelle, gleiche Größe, gleiches Bauteil. Für den Spieler ist es ein Schloss,
  das die Farbe wechselt — zu und grün heißt „Klicks gehen ins Spiel", offen
  und grau heißt „das Overlay fängt sie ab". Entsperrt wird an derselben Stelle,
  an der man zugesperrt hat.

  Ein **eigenes Fenster** bleibt es trotzdem, und das lässt sich nicht ändern:
  Wer Klicks durchreicht, reicht sie für das ganze Fenster durch — ein Knopf in
  der Leiste wäre in dem Moment genauso wenig zu treffen wie der Rest. Ist die
  Leiste eingeklappt oder das Overlay im Pop-up-Betrieb versteckt, fällt das
  Schloss auf seinen alten Platz in der Ecke zurück.

## v3.0.0-rc90 - 2026-08-28

### Verbessert

- **Das Schloss steht jetzt fest in der Leiste des Overlays.** Klicks ins Spiel
  durchreichen ging bisher nur über Einstellungen → Overlay; zurück kam man
  bequem über das Schloss, das dabei erscheint.

  Ein Weg hin und her gehört an dieselbe Stelle. In der Titelleiste steht
  deshalb ein **offenes** Schloss — es heißt „das Overlay fängt Klicks ab". Ein
  Klick sperrt zu, und ab dann übernimmt das schwebende Schloss oben rechts, wie
  bisher. Kein Umweg über die Einstellungen mehr.

  Der Knopf erscheint nur dort, wo das System Klicks überhaupt durchreichen kann
  — unter nativem Wayland wäre er wirkungslos. Klappt es wider Erwarten nicht,
  wird die Einstellung zurückgenommen, statt ein „an" zu speichern, das nichts
  bewirkt.

  Vorgeschlagen von **Haldjas (pr0)** am 28.08.2026: „man kann das durckclicken
  entfernen, aber eventuell kann der button zum locken stehen bleiben? sonst
  muss man ja erst wieder in die einstellungen".

## v3.0.0-rc89 - 2026-08-28

### Behoben

- **Das Auswahlfeld versprach mehr, als die Liste zeigte.** Nach dem Fix an
  der Patch-Historie stand im Feld „4.10.0 (24)" — darunter drei Zeilen.

  Zwei Ursachen, beide dieselbe Art Fehler:

  **Zwei Quellen für dieselbe Frage.** Das Feld zählte die Historie, der Filter
  prüft den Stempel `seit` im Katalog. Die Zahl in Klammern ist aber eine
  Zusage, wie viele Zeilen kommen. Gezählt wird jetzt der Katalog — was nicht
  gestempelt ist, kann die Liste ohnehin nicht zeigen.

  **Und der Stempel kam zu spät.** Nachgezogen wurde er nur im Netz-Takt, der
  irgendwann nach dem Start in einem eigenen Faden läuft. Gemessen am
  28.08.2026: Fenster um 10:44:02 gebaut, Katalog um 10:44:03 fertig gestempelt
  — eine Sekunde zu spät, und die Liste blieb bis zum nächsten Öffnen falsch.
  Das Fenster stempelt jetzt selbst nach, **bevor** es den Katalog liest. Das
  trifft jeden Nutzer beim ersten Start nach einer Fassung mit neuer Historie.

## v3.0.0-rc88 - 2026-08-28

### Behoben

- **Der Patch-Filter verlor fast den ganzen Patch.** Im Auswahlfeld stand
  „4.10.0 (3)", und die Liste zeigte drei Schiffswaffen. In Wahrheit hat 4.10.0
  **24** Baupläne gebracht — die 21 mitgelieferten waren aus der Anzeige
  verschwunden.

  Ursache: Das Programm legte die selbst beobachtete Historie über die
  mitgelieferte. Bei gleicher Spielversion gewann die eigene komplett. Nur:
  Was das Programm selbst einträgt, ist immer bloß der **Zuwachs seit dem
  letzten Lauf** — hier drei Waffen, die die Quelle zwei Tage später
  nachreichte. Als vollständige Patch-Liste gelesen ist das zwangsläufig falsch.

  Beide Listen werden jetzt **vereinigt** statt ersetzt, und beim Datum gilt
  das frühere. Das gleiche galt für zwei eigene Funde nacheinander: Der zweite
  löschte den ersten. Auch das ist behoben.

### Verbessert

- **Der Diagnosebericht nennt jetzt die Patch-Historie.** Eine neue Zeile
  unter dem Katalogstand: welche Spielversionen die Historie führt und mit
  wie vielen Bauplänen — zum Beispiel `4.10.0 (24)`.

  Der Fehler oben konnte sich verstecken, weil der Bericht nur den Katalogstand
  zeigte. Der war völlig in Ordnung, die Historie darunter nicht. Wer jetzt
  „der Patch-Filter zeigt fast nichts" meldet, hat die Zahlen im Bericht
  stehen, ohne dass jemand erst eine Datei aufmachen muss.

## v3.0.0-rc87 - 2026-08-28

### Verbessert

- **Die Sicherheitsabfragen sehen jetzt aus wie der Rest des Programms.**
  Bisher kam an drei Stellen der graue System-Kasten von Tk: heller Hintergrund
  im dunklen Fenster, fremde Schrift — und schmal und hoch, sodass ein längerer
  Satz zu einer Säule wurde.

  Jetzt ist es ein eigener Dialog in denselben Farben und mit denselben Knöpfen
  wie überall sonst, **breit statt hoch** (620 px), mittig über dem Fenster.
  Eingabetaste heißt ja, Escape heißt nein.

  Betrifft: Textquelle wechseln · Fehlerbericht absenden · Bestand zurücksetzen.

  Die Vorgabe dahinter: Die Abfrage soll das Design des Programms tragen — und
  eher breit als hoch sein.


- **„Texte im Spiel" steht jetzt in der Reihenfolge, in der man es liest.**
  Zuerst die Textquelle — woher die Grundlage kommt —, dann was hineingeschrieben
  wird: erst die Bauplan-Angaben, dann die Angaben am Gegenstand. Vorher stand
  der Schreib-Schalter über der Quelle, auf die er sich bezieht.

### Behoben

- **Abfragen hatten deutschen Text, aber englische Knöpfe.** Beim Umstellen
  der Textquelle stand „Einsetzen?" über den Knöpfen **Yes** und **No**.

  Diese Knöpfe kommen nicht aus der Sprachdatei des Programms, sondern aus
  Tks eigener Tabelle — und die ist auf vielen Linux-Systemen unvollständig.
  Nachgemessen am 28.08.2026: Die Tk-Sprache stand bereits richtig auf
  `de_de`, die deutschen Wörter fehlten der Installation trotzdem. Unter
  Windows bringt Tk sie mit, deshalb ist es dort nie aufgefallen.

  Das Programm trägt die Wörter jetzt selbst ein — und zieht sie beim
  Sprachwechsel mit, statt sie beim Start einmal zu setzen.

## v3.0.0-rc86 - 2026-08-28

### Behoben

- **Auf „Texte im Spiel" standen Sternchen im Klartext.** In der Erklärung
  zur Textquelle war »danach ist das `**ganze Spiel**` in dieser Sprache« zu
  lesen — mit den Sternchen.

  Die Auszeichnung `**fett**` in der Sprachdatei ist für den gedacht, der die
  Datei liest; ein Tk-Label kann kein Mischformat und zeigt sie deshalb
  einfach mit an. Die Danke-Seite nahm sie schon heraus, die
  Einstellungszeilen nicht — dieselbe Aufgabe an zwei Stellen, eine davon
  vergessen. Beide gehen jetzt durch dieselbe Funktion.

  Aufgefallen auf einem Bildschirmfoto von rc85. Der Selbsttest hatte es nicht
  gesehen: Er suchte nach deutschem Text in der
  englischen Oberfläche, nicht nach Auszeichnung. **Er prüft es jetzt mit** —
  und die Prüfung wurde gegengeprobt, indem der Fehler noch einmal eingebaut
  wurde.

## v3.0.0-rc85 - 2026-08-28

### Behoben

- **Unter Linux wurden Beschreibungstexte abgeschnitten statt umgebrochen — und
  drückten die Schalter aus dem Fenster.** Betroffen war jede Seite mit
  Fließtext neben einem Bedienelement: „Texte im Spiel“, „Bestand“, „Fehler
  melden“. Bei kleiner Fenstergröße endeten die Sätze mitten im Wort, und die
  Schalter rechts waren gar nicht erreichbar.

  Der Grund lag eine Ebene tiefer, als es aussieht. Die Funktion, die den
  Zeilenumbruch an die Fensterbreite hängt, fragt beim Label nach seinem
  eigenen Rand. Tk gibt so eine Maßangabe je nach Aufbau als Zahl, als Text
  **oder als Tcl-Objekt** zurück — und auf Letzteres wirft `int()` einen
  `TypeError`. Aufgefangen wurden aber nur `TclError` und `ValueError`, und ein
  `TypeError` ist keins von beiden. Der Fehler flog also durch und beendete die
  Funktion, **bevor** sie den Umbruch setzen konnte. Der Text blieb einzeilig
  und breit — genau der Zustand, den diese Funktion verhindern soll.

  Warum es erst jetzt auffiel: Das Tk im Windows-Bau liefert diese Angaben als
  Zahl, das Tk im Linux-AppImage als Tcl-Objekt. Unter Windows konnte der
  Fehler nicht auftreten.

  Aufgefallen in der ersten Linux-Testrunde nach dem Update auf rc84 — zuerst am
  abgeschnittenen Text, dann bestätigt im Fehlerbericht: **50 von 50** aufgehobenen Fehlern kamen aus dieser
  einen Zeile.

  Maßangaben werden jetzt mit Tks eigenem Umwandler gelesen, der alle drei
  Formen versteht. Dieselbe Falle steckte an zwei weiteren Stellen im
  Zeilenumbruch und wurde dort gleich mit beseitigt.

- **Deinstallieren ließ den Autostart-Eintrag liegen.** Danach stand in der
  Registry weiter ein Verweis auf eine Datei, die es nicht mehr gab — Windows
  versuchte sie bei jeder Anmeldung zu starten und scheiterte still.

  Der Grund: Der Eintrag wird an **zwei** Stellen gesetzt. Der Installer legt ihn
  an, wenn man beim Installieren „Mit Windows starten“ wählt, und räumt genau
  diesen Fall auch wieder weg. Schaltet man den Autostart aber **im Programm**
  ein, schreibt das Programm denselben Wert — und davon wusste der Deinstaller
  nichts.

  Aufgefallen beim Aufräumen nach einem Testlauf. Es ist derselbe Autostart, der am selben Morgen das Update scheitern ließ
  (Code 5) — er war an beiden Enden nur halb geregelt.

  Der Deinstaller entfernt den Wert jetzt immer, unabhängig davon, wer ihn
  gesetzt hat. Nur diesen einen Wert — die Autostart-Einträge anderer Programme
  bleiben unangetastet.

## v3.0.0-rc84 - 2026-08-28

### Behoben

- **Das Update scheiterte, wenn der Autostart mitten hineinfuhr.**
  Gemessen beim Update rc75 → rc83: Der Installer lief bis zur Hälfte und brach dann ab mit

      Fehler beim Ersetzen einer vorhandenen Datei:
      DeleteFile schlug fehl; Code 5. Zugriff verweigert.

  Der Windows-Restart-Manager war **nicht** schuld — er hatte sauber gearbeitet.
  Das Setup-Protokoll zeigt die ganze Kette:

      05:43:47  Shutting down applications using our files. (forced)
      05:43:55  << der Watcher läuft wieder — Elternprozess explorer.exe >>
      05:44:17  DeleteFile: The existing file appears to be in use (5).

  Acht Sekunden nach dem Schließen hat der **Autostart** das Programm wieder
  hochgefahren. Windows arbeitet die Autostart-Einträge verzögert nach dem Start
  von `explorer.exe` ab; war die Bedienoberfläche kurz vorher neu gestartet
  (Absturz, frische Anmeldung), fällt diese Verzögerung genau in die laufende
  Installation. Bewiesen ist es über den **Elternprozess**: `explorer.exe` —
  hätte sich der Watcher selbst neu gestartet, stünde dort etwas anderes.

  Das Löschen des laufenden Programms ist damit chancenlos: Der Installer
  schließt **einmal**, und was danach hochkommt, sieht er nicht mehr. Von sich
  aus wiederholt er nur viermal im Sekundenabstand.

  Der Installer fasst jetzt direkt vor dem Kopieren nach und beendet ein wieder
  hochgefahrenes Programm — dreimal mit kurzem Abstand, damit auch ein Autostart
  erwischt wird, der genau in diesem Moment feuert. Nur beim **Update**; wer neu
  installiert, wartet keine Sekunde länger.

### Geändert

- **Ein Schalter, der „aus“ sagt, macht jetzt auch aus.** Beide Schalter auf
  der Seite „Texte im Spiel“ setzten bisher nur die Einstellung — die Textdatei
  blieb unangetastet, bis jemand unten unter „Von Hand“ auf „Jetzt eintragen“
  drückte. Wer die Angaben abschaltete, das Spiel neu startete und alles
  unverändert vorfand, hielt das Werkzeug für kaputt.

  Verschlimmert wurde es durch den Kasten darüber: Der versprach „Änderungen
  wirken beim nächsten Spielstart“ — also genau das, was nicht stimmte.

  Gemessen im Test: Schalter aus, Statuszeile meldete „aus“ — und in der
  Textdatei standen unverändert **1.217** Angaben. Beim zweiten Schalter
  passierte dasselbe, obwohl der Hinweis danebenstand: Gelesen wird das Fette,
  nicht das Kleingedruckte. Damit war die Frage entschieden — ein Hinweis im
  Kleingedruckten ist keine Lösung.

  Jetzt wirkt das Umlegen sofort — aus heißt weg, an heißt da. Das ist
  verlustfrei: Der ursprüngliche Wortlaut des Spiels ist gemerkt und wird beim
  Entfernen buchstabengenau wiederhergestellt. Bleibt doch etwas stehen, sagt
  der Kasten das jetzt auch, statt „es wird nichts geschrieben“ zu melden.


- **„Star Citizen starten" steht nicht mehr doppelt.** Auf der Seite „Texte im
  Spiel" gab es einen eigenen Abschnitt dafür — obwohl der Knopf ohnehin
  dauerhaft unten links in der Leiste steht, auf jeder Seite erreichbar.
  Der Abschnitt ist weg, der Knopf in der Leiste bleibt unverändert.

## v3.0.0-rc83 - 2026-08-28

### Behoben

- **Der Bericht sagt jetzt, ob die Bauplan-Angaben im Spiel stehen.**
  Der häufigste Support-Fall lautet „ich sehe deine Angaben im Spiel nicht
  mehr". Dahinter steckt fast immer dasselbe: Ein Übersetzungs-Update oder ein
  Spiel-Patch hat die Textdatei des Spiels neu geschrieben und die Angaben
  dabei stillschweigend hinausgeworfen. Das Werkzeug merkt davon nichts.

  Im Bericht stand bisher nur, welche Textquelle eingestellt ist — ob
  tatsächlich etwas eingetragen war, ließ sich daraus nicht ablesen, sondern
  nur erraten. Genau so am 28.08.2026 bei **Morkhan** geschehen.

  Neu sind zwei Zeilen: ob die Angaben eingetragen sind, ob das Einspielen
  überhaupt eingeschaltet ist, ob automatisch aufgefrischt wird — und welche
  Textdatei gemeint ist. Wer unter Linux ohne Übersetzung spielt, bekommt
  dabei **keine** Warnung: Dort gibt es keine solche Datei, und das ist der
  Normalzustand, kein Fehler.

- **Abgeschnittener Text statt Umbruch — überall dort, wo es knapp wurde.**
  Aufgefallen ist es an einer einzigen Stelle: Die englische Warnzeile auf der
  Spiel-Seite („Every translation update and every game patch wipes the
  details.") ragte um 5 Pixel heraus und wurde stillschweigend abgeschnitten.

  Die Ursache lag nicht am Text, sondern an einer Rechnung, der ein Posten
  fehlte. Die Umbruchgrenze begrenzt nur den **Text**; was eine Beschriftung am
  Ende belegt, ist Text plus Rand plus Innenabstand. Stand die Grenze auf der
  vollen verfügbaren Breite, brauchte die Beschriftung ein paar Pixel mehr, als
  sie bekam — und Tk schneidet ein zu breites Element stumm am Rahmen ab, ohne
  Fehler, ohne Hinweis.

  Der Rand wird jetzt beim Element selbst erfragt statt geschätzt und
  abgezogen. Das wirkt an **jeder** Stelle mit selbsttätigem Umbruch, auch an
  denen, die heute knapp durchgingen und beim nächsten längeren Text gekippt
  wären. Nachgemessen: nichts wird mehr abgeschnitten, über 11 Seiten × 2
  Sprachen × 2 Fenstergrößen.

## v3.0.0-rc82 - 2026-08-28

### Behoben

- **Ein Auftrag mit mehreren Preisstufen verlor fast alle seine Baupläne.**
  Verträge, die sich einen Textschlüssel teilen, haben sich beim Aufbauen des
  Katalogs gegenseitig überschrieben — der zuletzt eingelesene gewann, alle
  anderen fielen weg. Gemessen am Spielstand 4.10.0: **123 von 353**
  Auftrags-Schlüsseln sind mehrfach belegt, **319** Verträge fielen weg, und
  **797 Bauplan-Einträge** hat dadurch nie jemand zu Gesicht bekommen. Beim
  Kopfgeld-Auftrag standen 8 Baupläne statt 25.

  Gefunden von **Morkhan**, der nicht lockergelassen hat: „ich bekomme nicht
  angezeigt, welche Baupläne ich beim Neulingsauftrag bekommen kann, sondern
  NUR die auf der höchsten Stufe." Es war nicht die höchste Stufe — es war die
  zuletzt gelesene. Jetzt werden alle Stufen zusammengeführt.

- **Ein Katalog, der schon auf der Platte lag, hätte den Umbau nie
  mitbekommen.** Er wurde bisher nur erneuert, wenn Star Citizen eine neue
  Version bringt. Er trägt jetzt eine eigene Aufbau-Nummer — ändert sich sein
  Inneres, wird er neu gebaut, auch ohne Patch.

### Geändert

- **Die Überschrift heißt jetzt „MÖGLICHE BAUPLÄNE FÜR DIESEN MISSIONSTYP".**
  Vorher stand dort „BAUPLÄNE AUS DIESEM AUFTRAG" — und das versprach mehr, als
  die Daten hergeben. Wer das wörtlich liest, nimmt den Auftrag an und bekommt
  nichts. Morkhan am 28.08.2026: „is trotzdem verwirrend, egal wie man's dreht."
  Er hatte recht, und die Verwirrung saß in der Überschrift, nicht in der Liste.

  Der SC Deutsch Launcher formuliert es aus demselben Grund so — 367 mal in
  seiner Datendatei.


- **Die Zählung `[BP 3/12]` im Titel ist weg, es steht nur noch `[BP]`.** Die
  Zahl sah nützlich aus, war aber nicht wahr: Die Liste eines Auftrags führt
  alle Preisstufen zusammen, und welche davon die eigene Stufe hergibt, lässt
  sich nicht auflösen — 123 von 353 Aufträgen teilen sich den Textschlüssel
  über ihre Stufen hinweg. „3 von 12" hieß in Wahrheit „3 von 12, die
  irgendjemand irgendwo bekommen kann". Dieselbe Zahl ist auch aus der
  Listen-Überschrift verschwunden.

  Was bleibt, ist das Ehrliche: **Angehakt heißt „hab ich"** — unabhängig
  davon, ob diese Stufe den Bauplan hergibt oder woher er kam.

- **Wo sich die Stufen unterscheiden, steht der nötige Rang hinter dem
  Bauplan.** Zum Beispiel „erst ab Head Contractor (38.000 XP)" neben Plänen,
  die es erst weit oben gibt, während andere desselben Auftrags schon ab 800
  XP fallen. Steht nur dort, wo es die Baupläne wirklich unterscheidet —
  brauchen alle denselben Rang, steht er ohnehin oben unter „Min. Reputation".

- **Aufträge, bei denen einzelne Stufen leer ausgehen, sagen das jetzt.**
  „Achtung: 1 der 3 Stufen dieses Auftrags geben gar keine Baupläne."


### Geändert

- **Der Reiter „Diagnose" heißt jetzt „Fehler melden" und trägt Rot.** Niemand
  sucht unter „Diagnose", wenn etwas klemmt — und schon gar nicht in einem
  zugeklappten Menü, wo er vorher steckte.

  Das Rot arbeitet in zwei Stufen, damit es etwas bedeutet: **Das Wort ist
  immer rot**, damit man den Reiter findet. **Das Symbol wird nur rot, wenn
  wirklich Fehler mitgeschrieben wurden** — sonst stünde der Watcher dauerhaft
  auf Alarm, obwohl alles läuft, und niemand nähme die Farbe noch ernst.

### Behoben

- **Beim zweiten Besuch einer Seite fehlte die Spur im Bericht.** Sie wurde nur
  beim ersten Aufbauen geschrieben; ging beim erneuten Einblenden etwas schief,
  fehlte die Zeile ganz statt zur Hälfte — und der Bericht verspricht, dass die
  letzte Zeile ohne „steht" die ist, an der es hing. Jetzt steht dort „zeigen",
  und man sieht den Unterschied zwischen „beim Aufbauen gestorben" und „beim
  Einblenden gestorben".
- **Im Fehlerbericht ließ sich erst rollen, wenn die Seite ganz unten war.**
  Das Mausrad ging an die Seite dahinter statt an das Textfeld unter dem
  Zeiger — man musste also erst die ganze Diagnose-Seite nach unten schieben,
  bevor sich im Bericht etwas bewegte. Jetzt rollt, was unter dem Zeiger liegt,
  wie man es aus dem Browser kennt. Gemeldet von **Morkhan**.
- **Der Knopf zum Absenden ist dauerhaft rot**, nicht erst beim Überfahren —
  ein Warnknopf, den man erst sieht, wenn die Maus darauf steht, warnt
  niemanden.
- **Der zweite Meldeweg heißt jetzt „GitHub Issue"** statt „Fehler melden".
  Zwei Knöpfe, die dasselbe versprachen, während der eine den Browser öffnet
  und ein GitHub-Konto verlangt.

## v3.0.0-rc81 - 2026-08-28

> **Ein Knopf statt neun Schritten: Fehlerbericht absenden.**

### Hinzugefügt

- **Die Diagnose-Seite steht jetzt in der Hauptleiste**, direkt unter
  „Serverstatus“ — nicht mehr im zugeklappten Menü „Für Fortgeschrittene“.
  Wer sie braucht, hat ein Problem und sucht sie nicht dort, wo „nichts für
  mich“ draufsteht.
- **Ein roter Knopf „Fehlerbericht absenden".** Klemmt etwas, drückst du ihn —
  und der Bericht ist beim Entwickler. Kein Kopieren, kein Suchen nach dem
  richtigen Kanal, kein „die Nachricht ist zu lang".

  Vorher waren es neun Schritte: aufklappen, kopieren, Discord finden,
  einfügen, feststellen dass es zu lang ist, als Datei speichern, die Datei
  wiederfinden, hochladen, abschicken. Jetzt einer.

  **Du siehst vorher genau, was rausgeht** — derselbe Text, der auf der Seite
  steht, in einem Fenster zum Nachlesen, und erst dann wird gefragt. Namen,
  Pfade und Zugangsdaten sind ohnehin schon herausgenommen. Ohne dein Ja
  passiert nichts.

## v3.0.0-rc80 - 2026-08-28

> **Baupläne aus dem Launcher werden wieder abgehakt — vorhandene Bestände ziehen selbst um.**

### Behoben

- **Baupläne aus dem Launcher oder einer Sicherung wurden nicht abgehakt.** Wer
  seinen Stand aus dem SC Deutsch Launcher, dem KRT Profit Basetool, von
  scmdb.net oder aus einer eigenen Sicherung mitbrachte, sah in der Liste leere
  Kästchen — obwohl die Baupläne im Bestand standen.

  Der Grund: Namen dieser Quellen tragen oft den Klassen-Zusatz
  (`XL-1 (Mil/2/A)`), abgeschnitten wurde er aber nur beim Lesen der
  Spielprotokolle. Damit standen `xl-1 (mil/2/a)` und `xl-1` als zwei
  verschiedene Einträge da und fanden nie zueinander. Das passiert jetzt an der
  zentralen Stelle — gleich, woher ein Name kommt.

  Betroffen war ausgerechnet, wer schon länger spielt und seinen Stand
  mitbringt. Gefunden beim Nachgehen einer Meldung von **Morkhan**.

  **Vorhandene Bestände ziehen beim ersten Start selbst um.** Die Schlüssel
  werden einmalig neu gebildet, doppelte Einträge zusammengeführt — dabei
  gewinnt der ältere Fund, denn wann ein Bauplan zum ersten Mal auftauchte, ist
  die Angabe, die zählt. Nichts geht verloren, nichts muss von Hand gemacht
  werden.

- **Das Werkzeug sagte nicht, dass die Änderungen erst beim nächsten
  Spielstart wirken.** Star Citizen liest die Textdatei **einmal beim
  Hochfahren**. Wer das Spiel offen hatte, spielte die Angaben ein, las
  „eingetragen (1608 Stellen)" — und sah im Spiel nichts. Naheliegender
  Schluss: kaputt. Der Hinweis steht jetzt direkt in der Erfolgsmeldung und im
  Zustandskasten unter *Texte im Spiel*.

## v3.0.0-rc79 - 2026-08-28

> **Drei Funde aus Morkhans Fragen — einer davon hätte still Baupläne verschluckt.**

### Behoben

- **Baupläne, deren Name ein Kürzel trägt, wurden nicht mehr abgehakt.** Seit
  die Angaben am Gegenstand eingetragen werden, schreibt das Spiel den Namen
  **mitsamt Kürzel** in seine Logdatei — `Bauplan erhalten: Spectre (Sth/1/A)`.
  Abgeschnitten wurden bisher nur die fünf Fraktions-Kürzel; alles Neue blieb
  am Namen kleben, und der Bauplan landete unter falschem Namen im Bestand.
  Betroffen wären **344 Waffen und 62 Raketen** gewesen — und niemand hätte es
  bemerkt, weil ja etwas angezeigt wurde. Gefunden beim Nachgehen einer Frage
  von **Morkhan**.

- **Eine Mission versprach „12 Baupläne" im Titel und zeigte darunter
  keine.** Eine Mission hat im Spiel **mehr Beschreibungen**, als der Katalog
  kennt — verschiedene Zielorte und Waren derselben Mission. Gemessen:
  `Covalex_HaulCargo_SingleToMulti` führt drei Beschreibungen im Katalog, in
  der Textdatei des Spiels stehen **acht**. Wer eine der übrigen fünf erwischte,
  sah den Zähler und darunter nichts. Der Weg über die Vertragsdaten des
  SCDL-Teams löste das längst, der eigene Weg über den Bauplan-Katalog nicht.
  Gemeldet von **Morkhan**.

### Hinzugefügt

- **Ein Rufzeichen im Auftragstitel, wenn die Baupläne an Bedingungen hängen.**
  `[BP 0/19!]` statt `[BP 0/19]`. Bei **332 von 818 Aufträgen** (41 %) fallen
  Baupläne nur in bestimmten Preisstufen oder ab einem Rang — „nur für
  256.500 / 264.000 aUEC", „nur ab Meister-Rang". Das stand zwar im
  Beschreibungstext, aber in der Auftragsliste sah man nur den Zähler, und
  genau danach entscheidet man, ob man annimmt. Gemeldet von **Morkhan**, der
  eine Transportmission mehrfach flog, in der nie einer fallen konnte.

  ⚠️ Warum es nicht sauberer geht: Alle Preisstufen einer Mission teilen sich
  **einen** Beschreibungstext im Spiel. Für die kleine Variante zeigt Star
  Citizen denselben Text wie für die große — unterscheiden lässt sich das nicht.

## v3.0.0-rc78 - 2026-08-28

> **Klicks ins Spiel durchreichen ist keine Einbahnstraße mehr.**

### Hinzugefügt

- **Ein Schloss am Overlay holt dich zurück, wenn Klicks ins Spiel
  durchgereicht werden.** Bisher war das eine Einbahnstraße: Wer die
  Einstellung einschaltete, kam an das Overlay nicht mehr heran — kein Knopf,
  keine Leiste, und die Einstellungen selbst schon gar nicht. Der einzige
  Rückweg war, das Programm ein zweites Mal zu starten. Dafür muss man aus dem
  Spiel heraus — also genau das tun, was die Einstellung vermeiden soll.

  Jetzt liegt oben rechts am Overlay ein kleines Schloss, das als Einziges
  klickbar bleibt. Ein Klick, und das Overlay fängt wieder Klicks ab. Es
  erscheint nur, wenn wirklich durchgereicht wird, und verschwindet von selbst
  — auch wenn du drüben in den Einstellungen umschaltest.

## v3.0.0-rc77 - 2026-08-27

> **„Originaltexte aus dem Spiel" funktioniert jetzt ohne Zusatzprogramm.**

### Behoben

- **Wer die Textquelle „Original" wählte, lief oft gegen eine Wand.** Diese
  Quelle holt die englische `global.ini` aus deiner eigenen `Data.p4k` — ohne
  Download, ohne fremde Übersetzung. CIG komprimiert diese Datei allerdings mit
  **zstd**, und das gebündelte Python konnte das nicht. Übrig blieb die
  Meldung, man möge sich 7-Zip installieren — für ein Werkzeug, das man
  herunterlädt und startet, eine Zumutung.

  Das Programm bringt den Entpacker jetzt selbst mit. Betroffen war vor allem,
  wer **englisch spielt und nur die Angaben am Gegenstand** möchte, ohne
  Übersetzung: Für den war dieser Weg der einzige.

  Falls du bisher 7-Zip nur deswegen installiert hast — du brauchst es nicht
  mehr.

## v3.0.0-rc76 - 2026-08-27

> **Am Traktorstrahl steht jetzt, womit man es zu tun hat — und unter Windows
> gibt es nur noch einen Weg.**

> [!important]
> **Windows: Es gibt nur noch den Installer.** Die einzelne
> `SC-BP-Watcher.exe` hängt ab dieser Fassung nicht mehr am Release.
>
> Der Grund betrifft dich, nicht uns: Ein Update legte die neue Fassung
> **neben** die alte Datei, statt sie zu ersetzen. Wer danach seine gewohnte
> Verknüpfung anklickte, benutzte monatelang unbemerkt die alte Version. Mit
> dem Installer kann das nicht passieren.
>
> **Wenn du bisher die einzelne Datei benutzt hast:** Lade einmal
> `SC-BP-Watcher-Setup.exe`, installiere darüber — dein Bauplan-Bestand bleibt,
> er liegt ohnehin woanders. Die alte Datei kannst du danach löschen.
> Unter Linux ändert sich nichts.

### Behoben

- **Unter Windows gibt es nur noch einen Download: den Installer.** Die
  einzelne `SC-BP-Watcher.exe` entfällt.

  **Was du davon hast:** Du musst nicht mehr überlegen, welche der beiden
  Dateien die richtige ist. Der Watcher steht danach im Startmenü, statt
  irgendwo im Download-Ordner zu liegen. Updates ersetzen wirklich das
  Programm, statt eine zweite Fassung danebenzulegen — der häufigste Grund
  dafür, dass jemand monatelang unbemerkt eine alte Version benutzt. Autostart
  ist ein Häkchen bei der Installation, und über *Apps & Features* wird alles
  wieder sauber los.

  Die einzelne Datei stammte aus der Anfangszeit: Ein unsigniertes Programm
  ohne Installer wirkt harmloser, und es ging darum, überhaupt erst Vertrauen
  zu gewinnen. Das ist erreicht — und zwei Wege nebeneinander heißen doppelt so
  viele Stellen, an denen etwas klemmen kann. Lieber ein Weg, der zuverlässig
  funktioniert.

  Unter Linux ändert sich nichts: dort bleibt es beim AppImage.
- **Wer noch v2.0.0 hat, kommt trotzdem mit.** Deren Update-Weg greift die
  erste Datei auf `.exe` — das ist jetzt der Installer — und startet sie
  anschließend. Er läuft damit von selbst und richtet alles ordentlich ein.
  Der eigene Bauplan-Bestand zieht beim ersten Start automatisch mit um.
- **Ein Update installiert dorthin, wo das Programm liegt** — statt eine zweite
  Fassung daneben anzulegen. v2.0.0 gab es nur als nackte `.exe`, alle ihre
  Nutzer laufen also „portabel", ohne es gewollt zu haben. Ohne diesen Zusatz
  hätte der Installer beim übernächsten Update unter
  `%LOCALAPPDATA%\Programs` installiert und die alte Datei liegen lassen — wer
  sie per Verknüpfung startet, benutzte für immer die alte Fassung.

### Hinzugefügt

- **Angaben am Gegenstand — Klasse, Größe und Gütegrad stehen jetzt am Namen.**
  Wer im Spiel etwas mit dem Traktorstrahl anvisiert, sah bisher nur
  „Glacier". Jetzt steht dort **„Glacier (Mil/1/A)"** — militärisch, Größe 1,
  Gütegrad A. Bei Raketen zählt etwas anderes, deshalb steht dort der Suchkopf:
  **„'Arrow' I Missile (IR1)"** für Infrarot, `EM` für elektromagnetisch, `CS`
  für Querschnitt. Im Gefecht klappt niemand eine Beschreibung auf.

  **856 Gegenstände** bekommen so eine Angabe: 450 mit Klasse, Größe und Güte,
  344 Waffen mit ihrer Klasse (ballistisch, Laser, Plasma …) und 62 Raketen.

  Die Angaben stammen aus der Textdatei des Spiels **selbst** — sie stehen dort
  längst, nur in der Beschreibung, die man erst aufklappen muss. Das Werkzeug
  schreibt sie dorthin um, wo man sie im Gefecht auch sieht.

  Vorgeschlagen von **Morkhan**.

  Abschaltbar unter *Texte im Spiel → Angaben am Gegenstand*. Wer sie wieder
  loswerden will, nimmt „Wieder entfernen" — die ursprünglichen Namen kommen
  auf das Zeichen genau zurück.

## v3.0.0-rc75 - 2026-08-27

> **Der Startverlauf steht wieder im Bericht.**

### Behoben

- **Der Startverlauf wurde von der Bedienung aus dem Bericht gedrängt.** rc74
  schrieb Startschritte und Seitenwechsel in einen Topf, und der Bericht zeigt
  nur die letzten zwölf Zeilen — fünf Klicks genügten, und der komplette Start
  war nicht mehr zu sehen. Ausgerechnet der Teil, für den die Spur gebaut wurde.
  Beides steht jetzt in **zwei getrennten Abschnitten**, jeder für sich
  gedeckelt; auch beim Kürzen der Datei bleibt der Startverlauf stehen.
  Gefunden im ersten rc74-Bericht, eine Viertelstunde nach der Veröffentlichung.
- **Die Diagnose-Seite stand als letzte Zeile in ihrem eigenen Bericht.** Der
  Bericht entsteht, während die Seite gebaut wird — dadurch endete jede Spur mit
  „Seite diagnose: bauen beginnt" und sah aus, als wäre genau dort Schluss
  gewesen. Diese Zeilen bleiben jetzt draußen.

## v3.0.0-rc74 - 2026-08-27

> **Ein Absturz hinterlässt jetzt eine Spur.**

### Hinzugefügt

- **Harte Abbrüche werden festgehalten.** Bisher fing das Programm nur
  Python-Fehler ab. Ein Absturz, der den Prozess mitten im Befehl beendet
  (etwa aus der Tk-Bibliothek heraus), hinterließ **nichts**: keinen Eintrag,
  keine Meldung, nichts zum Mitschicken. Ab jetzt schreibt ein Fänger den
  Aufrufweg aller Fäden in eine Datei, und der nächste Diagnose-Bericht zeigt
  ihn unter „Harter Abbruch beim vorigen Lauf".
- **Die Spur führt jetzt auch über die Bedienung.** Sie hörte nach dem letzten
  Startschritt auf — welche Seite jemand geöffnet hat, stand nirgends. Jetzt
  schreibt jeder Seitenwechsel zwei Zeilen mit. Fehlt die zweite, hat es beim
  Bauen genau dieser Seite geknallt. Damit die Datei nicht wächst, wird sie
  gedeckelt.

### Hinweise

- **Der von Bomb20 gemeldete Absturz beim Öffnen von „Was ist neu" ist damit
  nicht behoben, sondern messbar.** Er ließ sich hier nicht nachstellen, und
  sein Bericht konnte ihn gar nicht zeigen — genau diese Lücke schließt rc74.
  Tritt er erneut auf, steht er im nächsten Bericht.

### Dank

- **Bomb20** (pr0) — für die Meldung, die sich am Ende als etwas
  Größeres entpuppte als ein einzelner Absturz: Das Werkzeug war an dieser
  Stelle blind. Und dafür, dass er sie geschickt hat, obwohl sie nach einem
  Fehlalarm aussah.
- **Haldjas** (pr0) — für den Gegentest unter Windows: Update
  von rc71 auf rc73 und die Oberfläche seit rc61, beides ohne Befund.

## v3.0.0-rc73 - 2026-08-27

> **Die Danke-Seite sagt jetzt, was heute wirklich passiert ist.**

### Geändert

- **Die Seite „Danke & Lizenzen" im Programm nennt Bomb20s heutige Funde.** Sie
  stand noch auf seinem Beitrag vom 25.08., während er an diesem Vormittag drei
  Fehler freigelegt hat, die am Ausliefertag **jeden** Nutzer getroffen hätten:
  der Startknopf für Star Citizen, der abgebrochene Download und der Neustart,
  der nie kam.
  - Der Dank stand ordentlich in beiden CHANGELOGs — nur sieht die im Programm
    niemand. **Wer im Programm nicht auftaucht, dem wurde nicht gedankt.** Die
    Release-Checkliste führt diese dritte Stelle jetzt ausdrücklich auf.

### Bestätigt

- **Der Neustart nach dem Update funktioniert** — nachgewiesen auf einem zweiten
  Rechner (CachyOS), von rc71 auf rc72, ohne einen einzigen Eintrag im
  Fehlerprotokoll. Damit hängt es an keiner Eigenheit einer einzelnen
  Installation.

### Dank

- **Bomb20** (pr0) — für einen Vormittag, an dem er dreimal einen Bericht
  geschickt hat, obwohl er eigentlich arbeiten musste, und für die Geduld, als
  seine Meldungen zunächst nach Bedienfehler aussahen. Sie waren es nie.


## v3.0.0-rc72 - 2026-08-27

> **Die Update-Seite sagt jetzt die Wahrheit** — sie sieht von allein nach, und
> der Weg zur stabilen Version ist keine Sackgasse mehr.

### Behoben

- **Die Seite zeigte eine veraltete Versionsnummer, solange sie offen blieb.**
  Nachgefragt wurde **einmal je Seitenaufbau**. Wer die Seite offen hatte,
  während draußen eine neue Version erschien, sah weiter die alte Nummer auf dem
  Knopf — und hielt sich für aktuell. Gemeldet von **Bomb20** (pr0): „ich
  krieg noch 67 angezeigt", während rc68 seit Minuten veröffentlicht war.
  Nachgesehen wird jetzt alle fünf Minuten, solange die Seite offen ist.
  - Fünf Minuten sind der Kompromiss: oft genug, dass niemand eine Version
    verpasst, und selten genug für GitHubs Grenze von 60 Abfragen pro Stunde.
- **Der Kasten „Stabile Version" war eine Sackgasse.** Statt eines Knopfes stand
  dort „Erst oben auf ‚Jetzt nachsehen' drücken" — wer die stabile Version
  wollte, sah keinen Weg, sondern eine Hausaufgabe.
  - **Der Grund war eine zu kleine Abfrage:** Geholt wurden die letzten **20**
    Freigaben, und darunter war bei inzwischen 83 Veröffentlichungen **keine
    einzige stabile** mehr — nur Testversionen. Jetzt werden 100 geholt (das
    Höchste, was GitHub in einer Abfrage hergibt), und es bleibt bei **einer**
    Anfrage: Die Stundengrenze zählt Anfragen, nicht Einträge.
  - Gemessen: 20 Freigaben → 0 stabile, 100 Freigaben → 3.

### Dank

- **Bomb20** (pr0) — für „ich krieg noch 67 angezeigt". Das klang nach
  einer Kleinigkeit und war der Hinweis auf zwei Fehler auf einmal.


## v3.0.0-rc71 - 2026-08-27

> **Der Neustart nach dem Update funktioniert** — die Ursache war eine ganz
> andere, als alle dachten.

### Behoben

- **Nach dem Update ging der Watcher aus und kam nicht wieder.** Gemeldet von
  **Bomb20** (pr0) am Morgen, hier den ganzen Vormittag über
  reproduziert. Drei Anläufe (rc67, rc68, rc70) haben es nicht gelöst, weil sie
  von einem Absturz der neuen Version ausgingen.
  - **Es war kein Absturz.** Die neue Version startet, sieht den
    Einzelinstanz-Wächter noch belegt, hält sich für die **zweite** Instanz und
    beendet sich planmäßig — mit Rückgabewert 0. Ein sauber beendeter Prozess
    sieht im Nachhinein genauso aus wie ein abgestürzter, bis jemand den
    Rückgabewert liest.
  - **Warum der Port belegt blieb:** Vor dem Neustart wird der Wächter mit
    `close()` geschlossen. Das weckt aber den Faden nicht, der in `accept()`
    wartet — der bleibt hängen, der Deskriptor bleibt gültig, der Port belegt.
    `shutdown()` bricht das wartende `accept()` ab; erst danach gibt `close()`
    den Port wirklich frei.
  - Belegt statt vermutet: Die Probe scheiterte vorher mit `Address already in
    use` und läuft jetzt durch. Selbsttest-Abschnitt 24 hält das fest.

### Dank

- **Bomb20** (pr0) — für die erste Meldung und dafür, nicht lockergelassen
  zu haben, als es nach einem Bedienfehler aussah. Er lag richtig, wir nicht.


## v3.0.0-rc70 - 2026-08-27

> **Wenn der Neustart scheitert, steht künftig im Bericht, warum.**

### Behoben

- **`'Overlay' object has no attribute '_dx'` beim Ziehen des Overlays.** Tk
  liefert eine Mausbewegung nicht immer nach einem Klick auf dasselbe Fenster:
  Wer den Knopf außerhalb drückt und ins Overlay zieht, löst nur die Bewegung
  aus — und den Startpunkt gab es dann nicht. Das Ziehen tat einmal nichts, der
  Fehler landete lautlos im Protokoll. Gemeldet von **Bomb20** (pr0, am
  25.08.2026 auf rc18) und erneut am 27.08.2026 auf rc69 — dazwischen nie
  behoben, weil er nichts kaputt macht, was man sieht.

### Geändert

- **Ein gescheiterter Neustart hinterlässt jetzt eine Spur.** Die
  Fehlerausgabe der frisch gestarteten Version lief bisher nach `/dev/null` —
  deshalb war „geht aus, kommt nicht wieder" nicht aufzuklären: Im
  Diagnosebericht stand dazu **gar nichts**. Sie wird jetzt aufgefangen, und
  kommt die neue Version nicht hoch, hängt ihr letztes Wort im Fehlerprotokoll
  und damit im Bericht.
  - Das ist keine Reparatur, sondern eine Messung. Nach zwei Anläufen, die den
    Neustart nicht gelöst haben, wird nicht ein drittes Mal
    geraten.

### Dank

- **Bomb20** (pr0) — für den Ziehen-Fehler, der zwei Tage lang in
  Berichten stand, ohne dass ihn jemand ernst genommen hat.


## v3.0.0-rc69 - 2026-08-27

> **Das Update wurde bei manchen gar nicht erst heruntergeladen** — schuld war
> die Fortschrittsanzeige.

### Behoben

- **Klick auf „Version holen", und es passierte nichts.** Kein Fortschritt, kein
  Neustart, keine Meldung — nach einem Neustart lief weiter die alte Version.
  Gemeldet von **Bomb20** (pr0): „ich habe auf get 68 geklickt, aber da
  kam nix mit restart oder install."
  - **Die Ursache war die Anzeige, nicht der Download.** Heruntergeladen wird in
    einem eigenen Faden, der den Fortschritt ans Fenster meldet. Dieser Aufruf
    kann werfen (`RuntimeError: main thread is not in main loop`) — und die
    Ausnahme riss den **ganzen Faden** mit, gleich beim ersten Prozentschritt. In
    Bomb20s Bericht stand der Fehler dreimal, einmal pro Klick.
  - Zeichnen ist Beiwerk, das Herunterladen ist der Zweck. Jede Anzeige im
    Update-Faden läuft jetzt gekapselt: Geht sie schief, wird das vermerkt und
    der Vorgang läuft weiter.
- **„Auf Aktualität prüfen" gab fälschlich Entwarnung.** Bomb20 bekam „du hast
  die neueste rc67" gemeldet, während rc68 seit zwei Minuten veröffentlicht war.
  GitHub erlaubt anonym **60 Abfragen pro Stunde und Adresse**; wer an einem
  Vormittag viel klickt, läuft dagegen. Der Abruf scheiterte — und wurde still
  verschluckt, sodass mit dem alten Stand weitergerechnet wurde.
  - „Nichts Neues" und „konnte nicht nachsehen" sind das Gegenteil voneinander
    und werden jetzt auseinandergehalten. Bei erreichter Stundengrenze steht da,
    was los ist und dass es in einer Stunde wieder geht.
  - **Ein Prüfknopf, der fälschlich Entwarnung gibt, ist schlimmer als keiner.**

### Dank

- **Bomb20** (pr0) — für den dritten Diagnosebericht an einem Vormittag,
  genau im richtigen Moment abgeschickt. Ohne ihn wäre „da kam nix" nicht von
  „Download klemmt" zu unterscheiden gewesen; mit ihm stand die Ursache in einer
  Zeile da.


## v3.0.0-rc68 - 2026-08-27

> **Der Update-Knopf steht da, wo man ihn sucht** — und „Fassung" heißt jetzt
> überall „Version".

### Geändert

- **Der Knopf „Jetzt die neueste Version holen" steht ganz oben**, direkt unter
  der Versionskarte. Vorher kam er erst nach der Knopfreihe und dem
  Tagesschalter und lag bei der Mindestgröße des Fensters **unterhalb der
  Kante** — wer ihn nicht findet, updatet nicht.
  - Das Fenster größer zu machen wäre die falsche Antwort gewesen: Auf einem
    1366×768-Laptop passt es dann gar nicht mehr. Der wichtigste Knopf gehört
    nach oben, nicht das Fenster in die Höhe.
- **Auch die beiden Kanal-Kästen sind bei der Mindestgröße vollständig
  sichtbar** — in ihnen sitzt der Knopf, mit dem man gezielt die stabile Version
  holt. Der Tagesschalter steht dafür jetzt darunter; er ist eine
  Nebeneinstellung, die Kästen sind der Zweck der Seite.
- **„Nur fertige Fassungen" heißt jetzt „Stabile Version".** „Fertig" klingt nach
  abgeschlossen — das Werkzeug wird laufend weiterentwickelt.
- **„Fassung" heißt überall „Version".** Ein sperriges Wort, das sonst niemand
  benutzt; in der Oberfläche, in der Anleitung und in den Kommentaren steht jetzt
  durchgehend „Version". Einzige Ausnahme ist die **Sprachfassung** — damit ist
  die Übersetzung gemeint, nicht die Programmversion.
- **„rcXX ist schon da" heißt jetzt „rcXX ist schon installiert"** — klarer, und
  im Englischen stand es längst so.

### Dank



## v3.0.0-rc67 - 2026-08-27

> **Der Neustart nach dem Update funktioniert unter Linux** — und kann nicht mehr
> stumm scheitern.

### Behoben

- **Nach dem Update ging der Watcher aus und kam nicht wieder.** Er lud die neue
  Version, spielte sie ein, schloss sich — und blieb zu. Gemeldet von **Bomb20**
  (pr0) mit dem entscheidenden Satz „es geht dann aus aber startet nicht",
  am selben Tag auf einem zweiten Rechner reproduziert.
  - **Die Ursache:** Beim Start der neuen Version wurden nur `APPIMAGE`, `APPDIR`,
    `OWD` und `ARGV0` aus der Umgebung entfernt — `LD_LIBRARY_PATH`, `PYTHONHOME`
    und `PYTHONPATH` blieben stehen. Die zeigen im AppImage in den **entpackten
    Mount der alten Version**. Zwei Sekunden später beendet sich die alte, ihr
    Mount verschwindet, und die neue sucht ihre Bibliotheken in einem Verzeichnis,
    das es nicht mehr gibt. Sie stirbt, bevor ein Fenster erscheint.
  - Die passende Wäsche gab es längst (`saubere_umgebung`), nur führte der
    Neustart eine eigene, unvollständige Version davon mit. Beide liegen jetzt in
    `scbp/pfade.py` — **eine** Wäsche, benutzt von allen.
- **Und er kann nicht mehr stumm scheitern.** Die alte Version tritt erst ab,
  wenn die neue die ersten Sekunden überlebt hat. Stirbt sie, bleibt der Watcher
  offen und sagt es: „Die neue Version ist nicht hochgekommen." Vorher schloss
  sich die alte pflichtschuldig, während die neue schon tot war — und der Rechner
  stand ohne Watcher da, ohne ein Wort dazu.
  - Dahinter derselbe Merksatz wie beim Startknopf in rc65: **Ein Programm zu
    starten heißt nicht, dass es läuft.** `Popen` meldet Erfolg, sobald der
    Prozess angelegt ist.

### Dank

- **Bomb20** (pr0) — fürs Dranbleiben. Seine nüchterne Beschreibung „es
  geht dann aus aber startet nicht" hat den Fehler festgenagelt, nachdem er
  zunächst für einen Bedienfehler gehalten wurde. Er lag richtig, wir nicht.

## v3.0.0-rc66 - 2026-08-27

> **Die Ausgabe-Dateien halten sich von allein aktuell** — und die Dateiauswahl
> sieht endlich nach dem System aus, auf dem sie läuft.

### Hinzugefügt

- **Die Ablage wird bei jedem neuen Bauplan mitgeschrieben.** Bisher entstanden
  die drei Ausgabe-Dateien (KRT Profit Basetool, scmdb.net, Vollsicherung) nur
  auf Knopfdruck — wer einmal geklickt hatte, hielt sie für aktuell, dabei
  standen sie für immer auf dem Stand jenes Klicks. Jetzt hängt das Schreiben am
  Bestand selbst: Jeder Fund im Spiel, jede Nachlese beim Start, jede Bestätigung
  durch den Launcher und jeder Import ziehen die Dateien mit.
  - **Feste Dateinamen in der Ablage.** Mit Datum im Namen wären dort täglich
    drei neue Dateien entstanden, und niemand wüsste, welche die aktuelle ist.
    Der Speichern-Dialog schlägt weiterhin einen Namen mit Datum vor — wer von
    Hand speichert, hält bewusst einen Stand fest.
  - **Früher abgelegte Dateien mit Datum wandern nach `Ältere/`** — verschoben,
    nicht gelöscht. Was sonst noch im Ordner liegt, bleibt unangetastet.
- **Ein Speichern-Knopf je Version**, direkt an der Version, statt eines
  gemeinsamen Knopfes weiter unten.

### Behoben

- **„Einzeln speichern …" speicherte immer die Basetool-Version.** Die Version
  war im Code fest verdrahtet; scmdb und die Vollsicherung waren über den Dialog
  überhaupt nicht erreichbar.
- **Die Dateiauswahl unter Linux war der alte Tk-Kasten** — eine Spaltenliste mit
  jedem versteckten Ordner, kein Sortieren, keine Vorschau. Jetzt öffnet sich der
  Dialog des Schreibtischs (`kdialog` unter KDE, sonst `zenity`), überall dort,
  wo eine Datei oder ein Ordner gewählt wird: Bestand einlesen, Bestand
  speichern, Spielordner, Launcher-Ordner, eigener Ordner und der
  Einrichtungs-Assistent. Fehlt beides, bleibt der Tk-Dialog als Rückfall —
  **nichts hängt davon ab.** Unter Windows und macOS ändert sich nichts, dort
  reicht Tk schon den echten Systemdialog durch.
  - Für Ordner gab es diesen Weg längst; für Dateien nicht. Beides steht jetzt
    an einer Stelle (`scbp/dateiwahl.py`) statt an dreien.


### Dank


## v3.0.0-rc65 - 2026-08-27

> **Der Startknopf rief unter Linux das falsche Programm auf.**

### Behoben

- **Der Knopf „Star Citizen starten" startete unter Linux nichts.** Er meldete
  „Star Citizen wird gestartet …" und danach geschah nichts — ohne jede
  Fehlermeldung. Aufgerufen wurde der `lug-helper`, und der **kann das Spiel gar
  nicht starten**: Er verwaltet Wine-Präfix, Runner und DXVK; eine Startoption
  hat er nicht. Der Watcher nimmt jetzt das Startskript `sc-launch.sh`, das der
  Helper beim Einrichten im Präfix anlegt, und findet es über den Spielordner
  (eine Ebene über `drive_c`) — unabhängig davon, wohin jemand installiert hat.
  Gemeldet von **Bomb20** (pr0).
  - Kein Rückfall mehr auf den `lug-helper`: Er würde gefunden, der Knopf
    erschiene, und er täte wieder nichts. Wer über Lutris oder Heroic spielt,
    trägt seinen Startbefehl weiterhin in der Einstellung `spielstarter` ein.


### Dank

- **Bomb20** (pr0) — für die Meldung, dass Star Citizen sich nicht aus dem
  Werkzeug starten lässt, und für die Geduld mit zwei Diagnoseberichten an einem
  Vormittag. Ohne den zweiten wäre nicht herausgekommen, dass der `lug-helper`
  das Spiel überhaupt nicht starten kann.

## v3.0.0-rc64 - 2026-08-27

> **Der Neuaufbau frisst die Meldung** — dreimal dieselbe Falle, an drei
> verschiedenen Stellen.

### Behoben

- **„Auf Aktualität prüfen" meldete weiterhin kein Ergebnis.** Der Fehler aus
  rc63 war weg, die Antwort kam trotzdem nicht: Der Knopf blieb bei „Suche nach
  einer neuen Version …" stehen. `neu_aufbauen()` zerstört **alle** Kinder des
  Fensters — auch die Fußzeile, in der die Meldung steht. Sie wurde gesetzt und
  Millisekunden später mitzerstört. Jetzt wird erst aufgebaut, dann gemeldet.

- **Dieselbe Falle nach dem Update unter Linux.** „Fertig — jetzt neu starten"
  wurde bei `after(0)` gesagt und bei `after(50)` weggeräumt. Reihenfolge
  getauscht.

- **Bei „sehr groß" fehlte die halbe linke Leiste.** „Star Citizen starten",
  „Kaffee spendieren" und „Discord" fielen unten aus dem Fenster — sie werden
  von unten gepackt, und was zwischen Reitern und Fußzeile nicht hineinpasst,
  fällt heraus. Die Mindestgröße des Fensters hängt an der Höhe der
  Seitenleiste, und die hängt an der Schrift. Gerechnet hat das Programm das
  immer richtig, nur lief die Rechnung nie nach einem Schrift- oder
  Sprachwechsel — jetzt gehört sie zum Neuaufbau. Der Gedanke dahinter: Wer
  schlecht sieht und die Schrift größer stellt, braucht auch ein Fenster, das
  im Verhältnis mitwächst.

- **Die beiden Kästen unter „Wovon willst du Bescheid bekommen?" waren
  ungleich groß.** `pack(expand=True)` verteilt nur den **Überschuss**
  gleichmäßig — wer mehr Text hat, bleibt breiter. Sie liegen jetzt in einem
  `grid` mit `uniform`, der einzigen Zusage in Tk, die zwei Spalten wirklich
  gleich breit macht; gemessen 545 px zu 545 px, gleiche Höhe.

- **Bei „sehr groß" waren die Knöpfe abgeschnitten.** Ein benanntes Tk-Font
  wirkt sofort auf jeden Text — aber die gezeichneten Rundknöpfe legen ihre
  Leinwand beim Bauen **einmal** auf die gemessene Textbreite fest. Nachgemessen
  an der Overlay-Wahl: Kasten 177 px, Text 206 px, **29 px fehlten**. Das
  Umstellen der Schriftgröße baut die Oberfläche jetzt neu auf — wie der
  Sprachwechsel es längst tut —, damit jede Leinwand neu misst.

### Hinweise

- **Selbsttest-Abschnitt 21.** Prüft beides zusammen: dass ein fertiger
  Rundknopf tatsächlich nicht von allein wächst (sonst liefe die zweite Prüfung
  ins Leere), und dass der Schriftwechsel neu aufbaut **und danach** meldet.

## v3.0.0-rc63 - 2026-08-27

> **„Auf Aktualität prüfen" prüft wieder** — und der Hinweis vor dem Update
> kommt endlich an.

### Behoben

- **„Auf Aktualität prüfen" antwortete mit `name 'datei' is not defined`.**
  Im Knopf stand nicht das Nachsehen, sondern der **Holen**-Ablauf: herunter-
  laden, einspielen, abtreten — mit zwei Variablen, die es in dieser Funktion
  nie gab. Egal ob eine neue Version da war oder nicht, unten stand „Das hat
  nicht geklappt". Jetzt meldet der Knopf wieder, was er findet: die gefundene
  Version — oder **„Du hast die neueste Version."** Diesen Satz gab es die
  ganze Zeit, ihn zeigte nur niemand.

- **Der Hinweis vor dem Update kam bei keinem einzigen Update.** Seit rc52 soll
  der Watcher ansagen, dass er sich gleich schließt, das Setup läuft und danach
  ein Doppelklick nötig ist — ein Programm, das wortlos verschwindet, sieht aus
  wie ein Absturz. Der Dialog saß aber in **derselben toten Funktion** und ist
  deshalb nie erschienen. Er steht jetzt im echten Update, vor dem Einspielen,
  und das Setup wartet, bis er gelesen ist. Bestätigt beim Update
  auf rc62: Es kam kein Fenster.

- **Der Ablage-Ordner ging nach dem Export nie auf.** `os.startfile()` im
  Bestandsfenster griff auf ein `os`, das dort nie importiert war; der Fehler
  fiel still in ein `except Exception`. Beim Ordner-Umzug stand `t(...)` statt
  `sprache.t(...)` — dort blieb die Erfolgsmeldung weg. Beide gefunden von der
  neuen Prüfung unten, nicht von Hand.

### Hinweise

- **Der Selbsttest sucht jetzt Namen, die es nicht gibt** (Abschnitt 20, über
  `pyflakes`). Genau diese Fehlerklasse fliegt sonst erst beim **Klicken** auf:
  Python prüft Namen erst beim Ausführen, und wenn der Rückruf in einem
  `except` endet, sieht es niemand. Die Prüfung fand auf Anhieb drei Fälle. Sie
  läuft im Bau-Ablauf vor jedem Release mit; fehlt `pyflakes` auf einem
  Entwicklungsrechner, wird sie übersprungen statt zu scheitern.

### Geändert

- **Das ⓘ am rechten Rand der Bauplan-Liste ist größer** — es öffnet den
  Herkunftskasten und war in reiner Zeilengröße kaum als Schaltfläche zu
  erkennen. Neuer Größensatz `ANTIPPBAR`, eine Stufe über den übrigen
  Zeilenzeichen: 16 px statt 14 bei „normal", 22 statt 18 bei „sehr groß". Die
  Statuspunkte im Overlay bleiben unverändert — die will niemand anklicken.

## v3.0.0-rc62 - 2026-08-27

> **Der Patch-Filter zeigt wieder, was der Patch gebracht hat.**

### Behoben

- **Der Patch-Filter fand nichts, „neu im Spiel" blieb leer.** Wer den Watcher
  schon vor rc55 benutzt hat, sitzt auf einem Katalog ohne Herkunftsstempel —
  gestempelt wurde bisher nur beim Neubau, und neu gebaut wird nur bei einer
  neuen Spielversion. Das Auswahlfeld zeigte deshalb „4.10.0 (21)" (es liest die
  Historie direkt), die Liste darunter aber „Nichts gefunden". Die Stempel werden
  jetzt beim Start nachgetragen, ohne Neubau und ohne Netz.
- **Der nächste Patch wäre stumm geblieben.** Die Vergleichsgrundlage
  (`bauplaene-gesehen.json`) kam ebenfalls erst mit rc55. Fehlte sie, griff die
  Regel „erster Katalogbau überhaupt — nichts ist neu", und der nächste Patch
  hätte **keinen einzigen** Zugang gemeldet. Fehlt die Datei, gilt jetzt der
  vorhandene Katalog als Grundlage: Was darin steht, war vorher im Spiel.

### Hinweise

- **Der Selbsttest prüft diesen Fall jetzt selbst** (Abschnitt 19, elf neue
  Prüfungen). Er hat sich sofort gelohnt: Das Nachziehen stand zuerst *hinter*
  der Netzsperre `SC_BP_NO_NET` — wer ohne Netz startet, hätte nie einen Stempel
  bekommen, obwohl Historie und Katalog beide auf der Platte liegen.

## v3.0.0-rc61 - 2026-08-27

> **Die Meldung im Discord sagt jetzt, worum es geht.**

### Hinzugefügt

- **Die Release-Meldung im Discord ist jetzt eine lesbare Karte.** Statt
  `[Repo] New release published: v3.0.0-rc60` steht dort der Changelog-Abschnitt
  **dieser** Version — derselbe Text wie im Werkzeug unter „Was ist neu".
  Testfassungen in Gold mit dem Hinweis „weniger lange erprobt", fertige in
  Xharig-Grün, dazu das Programmsymbol — nach dem Vergleich mit dem
  StarStrings-Kanal. Ohne hinterlegten Schlüssel passiert nichts und der
  Bau bleibt grün — eine Chat-Meldung darf keine fertige Veröffentlichung rot
  färben.

## v3.0.0-rc60 - 2026-08-27

> **Was der Diagnosebericht verriet.** Ein unsichtbares Kreuz, acht Fehler je
> Seitenwechsel — und eine neue Prüfung, die beides künftig vorher findet.

### Behoben

- **Acht Fehler im Protokoll bei jedem Seitenwechsel.** `invalid command name
  …!label` — Rückrufe, die den Zeilenumbruch nachziehen, kamen dran, wenn ihr
  Label längst zerstört war. Sichtbar war davon nichts: Der Haken in `fehler.py`
  fing sie ab, sie füllten nur den Bericht und verdeckten damit, was wirklich
  wichtig gewesen wäre. Dieselbe Falle steckte in der Knopfreihe und im
  Eingabefeld mit gezeichnetem Rahmen; alle drei prüfen jetzt vorher, ob es ihr
  Widget noch gibt. Nachgemessen: 39 Seitenwechsel, **0** Fehler.

- **Das Kreuz zum Schließen des Herkunftskastens war unsichtbar.** In der
  Bauplan-Liste blieb dort eine leere Lücke: Das Symbol `schliessen` gab es nur
  in Knopfgröße, gebraucht wurde es in Zeilengröße. `zeichen.bild()` gibt bei
  einer fehlenden Datei still `None` zurück — mit Absicht, damit ein fehlendes
  Symbol das Programm nicht anhält, wodurch der Fehler aber unsichtbar blieb.
  `tools/oberflaeche_pruefen.py` prüft das ab sofort mit.

## v3.0.0-rc59 - 2026-08-27

> **Die Anleitung stimmt wieder.** Alle Bildschirmfotos neu, je Sprache ein
> eigener Satz, und alle Symbole darin stammen aus dem Satz des Programms.

### Hinzugefügt

- **Die farbigen Punkte standen im Fließtext noch als Emoji.** Die
  Zeichen-Erklärung zeigte längst die echten Bilder, die Beschreibung darunter
  aber weiter `🟢 🟡 🔵 ⭐` — zwei verschiedene Darstellungen desselben Zeichens
  auf einer Seite.

- **Auch die englische Anleitung zeigt jetzt die englische Oberfläche.** Sie
  führte bis hierher deutsche Bildschirmfotos vor — bei elf Bildern und einem
  Werkzeug, dessen Nutzer unter Linux überwiegend den englischen Client fahren,
  keine Kleinigkeit. `tools/sprachen_pruefen.py` achtet ab sofort darauf: Er
  zählte nur Abschnitte und hat Bilder nie angesehen.

- **Alle Bilder in der Anleitung sind neu.** Die alten stammten aus
  v3.0.0-rc11 und zeigten nicht nur die abgelösten Symbole, sondern auch einen
  Stand ohne Serverstatus und ohne Patch-Filter. Dazu zwei Seiten, die noch nie
  eins hatten: **Serverstatus** und **Danke & Lizenzen**.

- **Die Merkmalstabelle in der Anleitung zeigte Emoji statt der echten Symbole.**
  `⚡ 📋 🧭 ⭐ 🔔 …` haben mit dem Symbolsatz des Programms nichts zu tun und sehen
  auf jedem System anders aus. Alle sechzehn stammen jetzt aus demselben Satz wie
  die Oberfläche.

- **Ein Bildschirmfoto zeigte den Heimatpfad des Autors.** `screenshot-pfade.png`
  lag seit v3.0.0-rc11 im Repo und führte dreimal `/home/<benutzer>/` vor —
  genau das, was der Fehlerbericht mit `pfade.kuerzen()` sonst herausnimmt.
  Entfernt; die Ordner-Seite bekommt kein Bild mehr, weil dort zwangsläufig
  Pfade stehen. An ihrer Stelle steht jetzt der Serverstatus, der nie eins
  hatte.

### Behoben

- **Die Filterknöpfe auf „Was ist neu" blieben auf Englisch deutsch.** „Alles /
  Neu / Verbessert / Behoben" standen fest im Code statt in `sprache.py` — direkt
  neben einem sauber übersetzten Änderungstext. Aufgefallen auf einem
  Bildschirmfoto der englischen Oberfläche.

## v3.0.0-rc58 - 2026-08-27

> **Wem was gehört — an einer Stelle.** Neuer Reiter „Danke & Lizenzen", der
> die Lizenzen und die Beteiligten zusammenführt. Dazu Namen und Symbole, die
> endlich zu dem passen, was sie tun.

### Hinzugefügt

- **Der Reiter „Auftragstexte" heißt jetzt „Texte im Spiel".** Der alte Name
  sagte nicht, **wo** diese Texte auftauchen. „Ingame-Texte" stand kurz zur Wahl
  und ist unter Spielern gängig — dagegen sprach, dass jeder andere Reiter der
  Leiste deutsch ist und ein einzelner Anglizismus dazwischen auffällt.
- **Auf „Update & Über" steht das Programmsymbol neben der Version.** Die Seite
  hatte gar kein Bild mehr, seit der Autor-Block auf „Danke & Lizenzen" gewandert
  ist.

- **Die Anleitung zeigte Zeichen, die es im Werkzeug nicht mehr gibt.** Die
  Knopf-Legende in beiden READMEs führte `☰`, `ⓘ`, `⟳`, `⏻` und `🗑` auf — zwei
  davon sind längst entfernt, die anderen sehen anders aus. Sie zeigt jetzt die
  **echten Bilddateien** aus `assets/symbole/`; damit kann sie nicht mehr
  veralten, weil sich mit einem getauschten Symbol das Bild in der Anleitung von
  selbst mitändert. Dasselbe für die Zeichen-Erklärung der Meldungen.
- **„Wer das gebaut hat" stand plötzlich zweimal.** Der Block mit Autor,
  scmdb, SC Deutsch Launcher und StarStrings lag auf „Update & Über" — und die
  neue Seite „Danke & Lizenzen" nannte dieselben Projekte noch einmal. Er liegt
  jetzt nur noch auf „Danke & Lizenzen", und zwar mit dem Autor **ganz oben**:
  Eine Seite, die fremde Arbeit aufzählt, muss die eigene zuerst nennen.

- **Der Spenden-Link war auf GitHub nirgends zu sehen.** Der Knopf „Kaffee
  spendieren" gibt es im Werkzeug seit Langem — auf der Projektseite selbst
  fehlte er aber komplett: kein Sponsor-Knopf, keine Erwähnung in der Anleitung.
  Wer das Werkzeug noch nicht installiert hatte, konnte ihn also gar nicht
  finden. Jetzt gibt es beides.

- **Neuer Reiter „Danke & Lizenzen"** unter *Info*. Bis hierher stand im ganzen
  Programm **keine einzige Lizenzangabe** — weder die eigene (GPL-3.0) noch die
  der mitgelieferten Symbole, und fremde Projekte wurden nur nebenbei genannt,
  dort wo sie gerade gebraucht wurden. Jetzt steht an einer Stelle, wem was
  gehört: das Programm selbst, die Symbole von Lucide, die Daten von scmdb,
  StarStrings und der SC Deutsch Launcher — jeweils mit Lizenz und anklickbarem
  Verweis. Dazu der Dank an die, aus deren Rückmeldung etwas geworden ist.

## v3.0.0-rc57 - 2026-08-27

> **Ein Symbolsatz statt vierzehn Schriftzeichen.** Die Zeichen der Melde-Leiste
> waren unterschiedlich groß, im Stil gemischt und sahen auf jedem Betriebssystem
> anders aus. Ersetzt durch fertige Bilder aus einem einzigen, einheitlich
> gezeichneten Satz.

### Geändert

- **Alle Symbole sind jetzt gleich groß — und stammen aus einem Satz.** Die
  Zeichen in der Melde-Leiste waren unterschiedlich groß, die Glocke war die
  größte. Dahinter steckten drei Ursachen mit demselben Kern: *Die Schrift
  entschied, nicht das Programm.* Ein Schriftzeichen füllt seine Box nur zu
  50–70 % aus, und jedes anders; `🗑` und `▶` sind gefüllte Flächen, `⚙ ⟳ ✕`
  dünne Striche; und jedes Betriebssystem greift zu einer anderen Ersatzschrift.
  Ersetzt durch fertige Bilder aus dem **Lucide**-Satz — alle auf einem
  24×24-Raster mit gleicher Strichstärke gezeichnet.
- **Auf Windows, Linux und Mac sieht die Oberfläche jetzt gleich aus.** Das war
  vorher nicht so: Windows nahm `Segoe UI Symbol`, die anderen Systeme etwas
  anderes. Wer auf einem Mac entwickelt, sah damit andere Zeichen als die
  Nutzer unter Windows.
- **Die farbigen Punkte vor den Bauplänen sind keine Emoji mehr.** `🟢 🟡 🔵 ⭐`
  liegen außerhalb der Grundebene; Windows malte sie über die Farb-Emoji-Schrift
  als bunte Klötzchen, die die eingestellte Farbe **ignorierten** — ausgerechnet
  an der Stelle, die man am häufigsten sieht.
- **Star Citizen starten heißt jetzt Rakete statt Abspielpfeil.** Ein `▶` heißt
  überall „Video ab", nicht „Programm starten".
- **Meldungen wegräumen heißt jetzt Radiergummi statt Mülleimer.** Der Knopf
  löscht nichts — er räumt nur die Anzeige auf, die Baupläne bleiben. Ein
  Mülleimer verspricht Vernichtung und schreckt vom Klicken ab.
- **„Einrichtung" heißt jetzt „Einrichtung starten".** Ein Verb sagt, dass etwas
  losgeht; das Wort allein klang nach einem Ort zum Nachschlagen.
- Die Höhe der Melde-Leiste wächst jetzt mit der eingestellten Schriftgröße mit.
  Sie stand fest auf 26 Pixel, wodurch die Symbole bei „groß" oben und unten
  herausragten.

### Entfernt

- **Der Autostart-Schalter ist aus der Melde-Leiste verschwunden.** Ein
  Ein/Aus-Zeichen heißt überall „Gerät ausschalten", und es saß direkt neben dem
  Kreuz, das das Programm wirklich schließt — zwei Knöpfe, die beide nach „aus"
  aussahen. Die Einstellung steht unverändert unter „Allgemein".
- **Der Knopf für den Einrichtungs-Assistenten ist aus der Melde-Leiste
  verschwunden.** Er bleibt im großen Fenster oben rechts erreichbar — in den
  Einstellungen reicht er, dorthin geht ohnehin jeder, der merkt, dass etwas
  klemmt.

### Behoben

- **Ein Hilfetext zeigte auf ein Zeichen, das es nicht mehr gab.** „Mit ☰
  öffnest du jederzeit die Bauplan-Liste" stand noch im Einrichtungs-Assistenten,
  obwohl das `☰` seit v3.0.0-rc55 durch das Klemmbrett ersetzt war. Alle
  Texte benennen die Symbole jetzt in Worten statt sie abzubilden.

### Dank


## v3.0.0 - 2026-08-29

> **Ein Fenster für alles.** Bauplan-Liste und Einstellungen lagen bisher in zwei
> getrennten Fenstern, und man musste wissen, in welchem etwas steckt. Jetzt liegen sie
> zusammen — mit Reitern links, einer sichtbaren Ablage für deine Dateien und einem
> Installer, statt eine Datei von Hand irgendwohin zu ziehen.

### Das Wichtigste in Kürze

- **Die Liste zeigt, was mit dem Patch neu ins Spiel kam.** Neben „beobachtet"
  steht jetzt **🔵 neu im Spiel**. Der Katalog stempelt jedem Bauplan die
  Spielversion auf, in der es ihn zum ersten Mal gab; der Filter zeigt die des
  aktuellen Patches. Kommt der nächste, rücken die neuen nach und die alten
  fallen heraus — der Stempel bleibt aber stehen, du siehst später noch, mit
  welchem Patch ein Bauplan kam. Mit 4.10.0 sind es 21.
- **Eine eigene Patch-Historie**, damit die Angabe auch stimmt. Verglichen wird
  nicht mehr gegen den Katalog von letzter Woche, sondern gegen **alle je
  gesehenen** Baupläne. Der erste Versuch meldete 74 Zugänge, von denen 53
  längst im Spiel waren — die Datenquelle hatte sie zwischendurch schlicht nicht
  geführt. Nachsehen ließ es sich nicht mehr: scmdb hält nur die aktuelle
  Spielversion vor, die Daten zu 4.9.0 waren am selben Tag schon gelöscht.
  Deshalb schreibt das Werkzeug jetzt selbst mit, was ein Patch gebracht hat
  (`daten/patch-historie.json`, im Repo nachlesbar) — nur die Zugänge, nie der
  ganze Katalog.
- **Ein Auswahlfeld „Patch"** neben den übrigen Filtern: dort lässt sich jeder
  frühere Patch nachschlagen — „was kam mit 4.10.0?". Das Feld **erweitert sich
  von allein**; jeder Patch, der Baupläne bringt, steht beim nächsten Öffnen
  darin, mit der Anzahl dahinter.
- **Ein Installer für Windows** — herunterladen, starten, fertig. Kein Herumschieben
  von Dateien mehr.
- **Ein Fenster statt zwei**, mit Reitern links. Dazu ein Symbol neben der Uhr,
  über das du es jederzeit zurückholst.
- **Das Overlay kann sich zurückhalten** und blendet sich nur bei einem Fund ein —
  ein schmaler grüner Streifen bleibt am Rand, die Maus holt es zurück.
- **Das Selbst-Update funktioniert jetzt auch unter Linux.** Dort scheiterte es
  bisher **immer**; wer ein AppImage nutzt, musste jede Version von Hand holen.
- **Star Citizen lässt sich aus dem Werkzeug heraus starten**, und ein
  Diagnose-Bericht sammelt auf Knopfdruck alles, was eine Fehlermeldung braucht —
  ohne Namen und ohne Pfade.

### Beim Umstieg von v2.0.0

- **Dein Bauplan-Bestand zieht von allein mit.** Er lag versteckt in
  `%APPDATA%`, jetzt liegt er sichtbar unter `Dokumente\SC BP Watcher`. Beim
  ersten Start wird er **kopiert**, nicht verschoben — der alte Ordner bleibt
  unangetastet stehen, falls doch etwas fehlt.
- **Nimm für dieses eine Update das Setup, nicht den Knopf im Programm.** Der
  Knopf tut es auch, benutzt aber noch den Update-Weg von v2.0.0 — und der
  lässt unter Windows ein Konsolenfenster stehen, bis du das Programm beendest.
  Ein Fehler im Update-Weg kann sich nicht selbst reparieren; ab v3.0.0 ist das
  erledigt, ab dann genügt der Knopf.
- **Hast du die `.exe` bisher von Hand irgendwohin gelegt, lösch sie nach der
  Installation.** Das Setup legt das Programm unter
  `%LOCALAPPDATA%\Programs\SC BP Watcher` ab. Die alte Datei bleibt sonst
  liegen, und irgendwann startest du versehentlich wieder die alte Version.
- **Unter Linux ist nichts zu tun** — das AppImage tauscht sich selbst aus.

### Hinzugefügt

- **Ein eigener Reiter „Serverstatus".** Läuft Star Citizen gerade? Wer nicht
  ins Spiel kommt, sucht den Fehler zuerst bei sich — ein Blick ins Werkzeug
  beantwortet das vorher. Gezeigt wird, was CIG auf seiner Statusseite meldet:
  die Lage der drei Systeme, dazu die Meldungen der letzten zwei Monate im
  Volltext samt Update-Zeilen. Der Aufbau folgt der Statusseite, die Zustände
  bleiben im **Wortlaut von CIG** (`operational`, `maintenance`) — eine
  Übersetzung wäre eine Aussage, die RSI nie gemacht hat. Die Seite fragt
  jede Minute nach, solange der Reiter offen ist; das kostet fast nichts, weil
  mit `ETag` gefragt wird und der unveränderte Fall ohne Inhalt beantwortet
  wird. Die Quelle steht als anklickbarer Verweis darunter.
  ⚠️ Die Angaben sind **von Hand gepflegt, keine Messung** — das steht auch in
  der Anzeige, damit niemand sie für eine Messung hält.
- **Ein Knopf für „gib mir einfach die neueste".** Bisher musste man erst
  verstehen, was ein Kanal ist, und den richtigen der beiden Kästen anklicken —
  wer den falschen wählte, bekam gar nichts angeboten. Jetzt steht darüber ein
  Knopf über die volle Breite, der sofort holt, was es gerade gibt, auch eine
  Testfassung. An der Einstellung darunter ändert er nichts.

- **Star Citizen lässt sich aus dem Werkzeug heraus starten.** Auf der Seite
  „Angaben im Spiel" steht ein Knopf, der das Spiel über den Weg startet, den
  man ohnehin benutzt: den RSI Launcher unter Windows, den `lug-helper` unter
  Linux. Wird keiner der beiden gefunden, erscheint der Knopf gar nicht erst —
  wer einen eigenen Weg hat (Lutris, Heroic), trägt ihn als `spielstarter` in
  die Einstellungsdatei ein. Vorgeschlagen von Morkhan.

- **Die Maus holt das Overlay zurück.** Im Aufblend-Betrieb genügt es, dorthin zu fahren, wo
  es steht — es kommt von selbst und bleibt, solange der Zeiger darauf ist. Vorher musste
  man das Programm dafür neu starten, und das verlangt kein anderes Overlay.

- **Neustart direkt nach dem Update.** Bisher hieß es „beim nächsten Start läuft die neue
  Version" — man musste selbst beenden und wieder starten. Jetzt wird der Holen-Knopf nach
  dem Laden zu **„⟳ Jetzt neu starten"**. Der Einzelinstanz-Wächter wird dabei zuerst
  geschlossen, sonst hielte sich die neue Version für die zweite und beendete sich sofort.

- **Startverlauf im Diagnose-Bericht.** Ein Absturz beendet das Programm sofort — kein
  Fehlerbericht wird mehr geschrieben, und es bleibt nur „es stürzt ab". Jeder Startschritt
  wird jetzt sofort auf die Platte geschrieben; die letzte Zeile im Bericht sagt, wie weit
  es kam.

- **Version holen, direkt aus dem Fenster.** Unter jeder der beiden Karten („Nur fertige
  Versionen" / „Auch Testfassungen") steht ein Knopf über die volle Breite, der die letzte
  Version dieses Kanals lädt und einspielt — auch zurück von einer Testfassung auf die
  letzte fertige.

- **Eintrag im Startmenü (Linux).** Der Assistent bietet ihn am Ende an, die Einstellungen
  jederzeit. Unter Windows macht das der Installer — unter Linux lag das AppImage bisher
  im Download-Ordner und stand in keinem Menü. Auf den Eintrag lässt sich außerdem eine
  Tastenkombination legen, mit der das Overlay zurückkommt.
- **Symbol im Infobereich (Windows).** Linksklick holt das Fenster, Rechtsklick zeigt ein
  kleines Menü. Der Schalter dafür stand schon in den Einstellungen; das Symbol selbst
  gab es nie.

- **Das Overlay kann sich zurückhalten.** Neu wählbar: dauerhaft sichtbar wie bisher,
  oder nur kurz aufblenden, wenn wirklich ein Bauplan dazukommt. Zurück holt man es,
  indem man das Programm noch einmal startet — auf die Verknüpfung lässt sich eine
  Tastenkombination des Systems legen. Angeregt von Haldjas (pr0): „Wenn ich im
  Kampf mit der Maus ins Overlay komme, wird das unangenehm."
- **Mausklicks lassen sich ins Spiel durchreichen.** Das Overlay bleibt sichtbar, fängt
  aber keine Klicks mehr ab. Unter Windows über `WS_EX_TRANSPARENT`, unter Linux über die
  XShape-Erweiterung; unter nativem Wayland geht es nicht, und das sagt die Einstellung
  dann auch statt einen wirkungslosen Schalter zu zeigen.
- **Ein zweiter Programmstart öffnet keine zweite Version mehr,** sondern holt die
  laufende hervor.

- **Ein Fenster mit Reitern.** Oben die Baupläne, darunter die Einstellungen, ganz unten
  eingeklappt, was nur Fortgeschrittene brauchen. Das Overlay bleibt klein wie bisher;
  dieses Fenster ist das, was sich dahinter öffnet.
- **Ein Installer für Windows.** Startmenü-Eintrag, optionales Desktop-Symbol, optionaler
  Autostart — und eine ordentliche Deinstallation. Wer lieber nichts installiert, findet
  die blanke `.exe` weiterhin im Release.
- **Deine Dateien liegen jetzt sichtbar** unter `Dokumente\SC BP Watcher`, getrennt nach
  Bauplänen, Exporten, Einstellungen und Diagnose. Vorher lagen sie versteckt im
  System — dort sucht niemand seinen Bauplan-Bestand. Beim ersten Start werden sie
  **kopiert**, der alte Ordner bleibt als Rückweg liegen.
- **Vorhandenen Bestand einlesen** — aus dem KRT Profit Basetool, von scmdb.net, aus der
  Launcher-Datei oder einer eigenen Sicherung. Das Format wird am Inhalt erkannt, du
  wählst nur eine Datei. Zusammengeführt, nie ersetzt.
- **Fehler melden mit einem Klick.** „Fehler melden" öffnet ein fertig ausgefülltes
  Formular; du schreibst nur noch dazu, was passiert ist. Der Bericht enthält keine Namen
  und keine Pfade mit deinem Benutzernamen.
- **Testfassungen auf Wunsch.** Wer beim Prüfen helfen will, schaltet sie unter *Über*
  ein und bekommt neue Versionen vor allen anderen — über dieselbe Update-Meldung.
- **Schriftgröße in vier Stufen**, wirkt auf Schrift, Symbole und Knöpfe zugleich.
- **Woher Baupläne ohne Auftrag kommen.** 55 Baupläne schüttet kein regulärer Auftrag
  aus — sie stammen aus benannten Töpfen wie XenoThreat, RDC-Boss oder RedWind. Statt
  eines Fragezeichens steht dort jetzt die Quelle, und man kann danach filtern.
- **Was ist neu** als eigener Reiter, getrennt nach Neu, Verbessert und Behoben.
- **Startbaupläne** werden erkannt und eingetragen — die acht, die jeder von Anfang an
  hat, mit ◆ gekennzeichnet.
- **Bestand ausgeben** in drei Formaten: KRT Profit Basetool, scmdb.net und eine
  vollständige Sicherung.

### Geändert

- **„Pfade" ist zu den Fortgeschrittenen gewandert.** Spielordner und Launcher
  werden gesucht und gefunden; wer doch nachhelfen muss, wird vom
  Einrichtungsassistenten geführt, der erklärt, was die Seite nur als Felder
  zeigt. Ein Reiter, den fast niemand braucht, stand oben nur im Weg.

- **Star Citizen starten sitzt jetzt links unten**, im markanten Grün über
  „Für Fortgeschrittene". Vorher stand der Knopf auf der Seite „Auftragstexte" —
  dort, wo es um Bauplan-Angaben geht — und war danach nur im Overlay zu sehen,
  also nur solange das eingeblendet ist. Jetzt ist er auf **jeder** Seite da.

- **Ein Discord-Knopf** darunter, bewusst ruhiger gehalten: Das Spiel zu starten
  ist die Handlung, für die man das Fenster offen hat, der Weg zum Discord ist
  ein Angebot. Zwei gleich laute Knöpfe nehmen sich gegenseitig die Wirkung.

- **„Jetzt nachsehen" heißt jetzt „Auf Aktualität prüfen".** Der alte Text sagte
  nicht, wonach nachgesehen wird. „Aktualisieren" wäre falsch gewesen — der Knopf
  prüft nur, geholt wird nichts.

- **„Noch keine Version bekannt" klang nach einem Fehler.** Der Knopf sagte
  nicht, was zu tun ist — jetzt steht dort „Erst oben auf ‚Jetzt nachsehen'
  drücken". Und der Kasten „Nur fertige Versionen" trägt den Zusatz
  „empfohlen", damit niemand raten muss, was er wählen soll. Beides fiel bei
  Morkhans Test auf.

- **Der Reiter heißt „Update & Über".** „Über" allein findet niemand, der ein
  Update sucht — der Autor selbst hat dort nicht danach gesucht.

- **Der Startknopf für Star Citizen saß an einer Stelle, an der ihn niemand
  sucht.** Er stand unter „Angaben im Spiel", also dort, wo es um Auftragstexte
  geht — selbst der Autor fand ihn nicht wieder. Jetzt sitzt er als grünes „▶"
  oben im Overlay bei den übrigen Zeichen: Wer das Spiel starten will, hat das
  große Fenster ohnehin nicht offen. Beim Überfahren sagt die Statuszeile, was
  der Klick tut.

- **Vor dem Einsetzen einer Übersetzung wird gefragt.** „Deutsch" und
  „StarStrings" ersetzen die Textdatei des Spiels vollständig — danach ist das
  ganze Spiel in dieser Sprache, nicht nur die Bauplan-Angaben. Das stand
  nirgends; jetzt sagt es der Erklärtext, und vor dem ersten Einsetzen kommt
  eine Rückfrage. Einmal bestätigt, wird nicht wieder gefragt. „Original"
  fragt nicht, weil es die Sprache nicht ändert.

- **Das Overlay hinterlässt im Aufblend-Betrieb einen schmalen grünen Streifen.** Maus
  darauf, und es ist wieder da. Der erste Versuch fragte dafür die Mausposition ab — das
  kann unter Wayland nicht funktionieren: Gemessen meldete Tk zwölfmal denselben Wert,
  während die Maus quer über den Schirm fuhr. Eine Anwendung erfährt die Zeigerposition
  dort nur, solange er über einem **ihrer eigenen** Fenster steht. Der Streifen ist so ein
  Fenster — und nebenbei ehrlicher als eine unsichtbare Zauberzone: Man sieht, wo das
  Overlay wartet.

- **Der Fehlerbericht sagt, aus welcher Version ein Fehler stammt** — und markiert die, die
  aus einer älteren kommen. Der Speicher hebt die letzten zehn über Programmstarts hinweg
  auf; nach einem Update standen dort Fehler, die längst behoben waren, und der Bericht sah
  aus, als sei alles noch kaputt.

- **Bis zu zwölf Bezugswege je Bauplan** statt drei. Gemessen: Über die Hälfte aller
  Baupläne hatte vorher abgeschnittene Wege. Angezeigt wird weiterhin der leichteste, der
  Rest klappt auf.
- **Die Herkunft erscheint erst auf Klick** und lässt sich wieder schließen — bei kleinem
  Fenster fraß sie sonst ein Drittel der Liste.
- **Filtern nach Art, Klasse, Größe, Gütegrad und Quelle**, zusätzlich zu Suche und den
  Listen „beobachtet / vorhanden / fehlt noch".
- **Overlay einklappen** (▾): schiebt sich auf die Titelleiste zusammen.
- **Kein Speichern-Knopf mehr** — Änderungen greifen sofort.

### Behoben

- **Das eingeklappte Overlay ließ sich nicht wieder aufklappen.** Der Knopf
  schaltete um, sichtbar passierte nichts — das Werkzeug war zu und blieb es.
  Ursache: Beim Einklappen wurde die aktuelle Fensterhöhe als „offene" Höhe
  gemerkt. Liefen der gemerkte Zustand und die tatsächliche Geometrie einmal
  auseinander, schrieb der nächste Einklapp-Vorgang die **Leistenhöhe** als
  offene Höhe fest; ab da klappte das Fenster auf seine eigene Größe „auf".
  Jetzt wird die Höhe nur gemerkt, wenn das Fenster wirklich offen ist, und
  beim Aufklappen gilt eine Mindesthöhe.
- **Der Ziehgriff für die Fenstergröße deckte im eingeklappten Zustand das ✕
  zu.** Er sitzt unten rechts — bei einem auf Leistenhöhe geschrumpften Fenster
  ist das dieselbe Stelle wie oben rechts, und man musste zielen, um das
  Werkzeug überhaupt schließen zu können. Er hängt jetzt an der **Liste** statt
  am Fenster — ist die eingeklappt, hat sie keine Höhe, und der Griff ist
  zwangsläufig mit weg. Ihn stattdessen rechtzeitig auszublenden hat dreimal
  nicht verlässlich geklappt: Ein Zustand, der sich aus dem Aufbau ergibt, ist
  verlässlicher als einer, den man nachträglich herstellt.
- **Bauplan-Namen waren ohne Launcher unlesbar** — „Golemmc4Orepod" statt
  „GOLEM MC-4 Ore Pod". Der Rückfall war `.title()` auf den Vergleichsschlüssel,
  in dem es keine Wortgrenzen mehr gibt; der lesbare Name lag die ganze Zeit
  daneben im Zwischenspeicher. Betraf **jeden Linux-Nutzer**, weil es dort nie
  einen Launcher gibt.
- **Das Selbst-Update unter Windows kam nie an.** Wer auf „holen" klickte, bekam
  eine Warnung und danach passierte nichts — außer 14 MB verwaister Datei im
  Programmordner, bei jedem Versuch aufs Neue. Dahinter steckten **zwei**
  Fehler, von denen jeder allein schon gereicht hätte:

  Geholt wurde die **falsche Datei**. An jeder Freigabe hängen drei Anhänge,
  gesucht wurde die erste auf `.exe` — und weil GitHub alphabetisch sortiert und
  ein `-` vor einem `.` steht, kam `SC-BP-Watcher-Setup.exe` zuerst. Der
  Installer wurde also über die Programmdatei geschoben, ohne je ausgeführt zu
  werden: Wer den Watcher danach öffnete, bekam ein Setup-Fenster.

  Und der Tausch konnte ohnehin nicht stattfinden. Nach dem Beenden lebt der
  Bootloader weiter und räumt seinen Ordner unter `%TEMP%` auf; blieb dabei eine
  Datei gesperrt, stand er im Fenster „Failed to remove temporary directory"
  still — und hielt damit die `.exe`, auf deren Freigabe das Hilfsskript wartete.
  Nach zwei Minuten gab es auf. Der Nutzer hätte eine Warnung wegklicken müssen,
  von der niemand wusste, dass sie zum Update gehört.

  **Unter Windows startet jetzt der Installer**, statt dass das Programm seine
  eigene Datei tauscht. Er beendet den laufenden Watcher selbst, ersetzt ihn,
  pflegt den Eintrag in „Apps & Features" und fährt ihn wieder hoch. Unter Linux
  bleibt es beim bewährten Tausch des AppImage.

- **Das Symbol neben der Uhr erschien unter Windows nie.** Es wurde bei jedem
  Start angelegt und scheiterte jedes Mal an derselben Stelle, sichtbar nur im
  Fehlerbericht: `argument 11: OverflowError: int too long to convert`. Der
  Aufruf zum Anlegen des Fensters hatte keine Typangaben, und ohne die reicht
  Python jeden Wert als 32-Bit-Zahl weiter — die Kennung, um die es ging, ist
  unter 64-Bit-Windows breiter. Derselbe Fehler steckte im Rückgabetyp der
  Fensterfunktion. Beim Beenden räumt das Symbol sich jetzt auch wirklich auf:
  Der bisherige Weg durfte von außen gar nicht greifen und lief still ins Leere.

- **Die angezeigte Version in „Apps & Features" blieb stehen.** Nachgesehen
  wurde nur im Benutzerzweig der Registry. Wer beim Installieren „für alle
  Nutzer" gewählt hatte, dessen Eintrag liegt aber im Maschinenzweig — dort
  wurde nie nachgezogen, und Windows zeigte weiter eine Nummer, die es nicht
  mehr gab. Jetzt werden beide Zweige durchsucht. Zusätzlich fragt der Installer
  nicht mehr nach „für mich" oder „für alle": Das Programm landet ohnehin im
  eigenen Benutzerordner, damit entfällt die Rückfrage und jede
  Administrator-Abfrage beim Aktualisieren.

- **Die Symbole in der Leiste sahen unter Windows entstellt aus.** In
  `Segoe UI` steckt **kein einziges** der vierzehn Zeichen — Windows suchte
  sich je Zeichen selbst eine Ersatzschrift und griff dabei zu **Segoe UI
  Emoji**: bunte, quadratische Emoji-Bildchen in einer schlanken dunklen
  Leiste, dazu in ungleichen Breiten (10 bis 21 Pixel bei gleicher Größe).
  Deshalb ließen sich die Symbole auch nie über die Schriftgröße angleichen —
  sie kamen aus verschiedenen Schriftdateien. Jetzt wird unter Windows
  ausdrücklich **Segoe UI Symbol** verlangt: alle vierzehn Zeichen einfarbig,
  in der eingestellten Textfarbe, halb so breit gestreut. Unter Linux war es
  nie ein Problem und bleibt unverändert.

- **Das Overlay blieb beim Umschalten auf Englisch deutsch.** Wer die Sprache
  wechselte, bekam ein englisches Fenster und eine deutsche Melde-Leiste:
  „8 Baupläne · Log ✓ · ohne Launcher · geprüft", dazu „Warte auf neue
  Baupläne …" und der Autostart-Text. Die englischen Versionen dieser Sätze
  gab es längst — benutzt hat sie niemand, der Code setzte die deutschen
  weiter fest zusammen. Zusätzlich erfuhr das Overlay vom Sprachwechsel
  überhaupt nichts; nur das Einstellungsfenster beschriftete sich neu.
  Dasselbe betraf die Meldung „neu im Spiel craftbar" der Katalog-Wache.
  Und Meldungen, die beim Umschalten **schon in der Leiste standen**, blieben
  ebenfalls deutsch — etwa „Keine Log-Sicherungen gefunden". Sie wurden fertig
  zusammengesetzt in die Zeile geschrieben und waren damit in der Sprache von
  vorhin eingefroren; erst ein Neustart räumte das auf. Meldungen tragen jetzt
  ihren Textschlüssel mit und werden beim Sprachwechsel neu gesetzt — samt
  Datum, das im Englischen anders geschrieben wird (2026-08-22 statt
  22.08.2026).

- **Der Hinweis am Startknopf ▶ überschrieb die Statuszeile.** Als einziges der
  zehn Zeichen hatte er keine Erklärblase, sondern schrieb in die Statuszeile
  und stellte danach einen Merker wieder her, der nie fortgeschrieben wurde —
  eine Fundmeldung war nach einem Mausschlenker über das Zeichen weg.

- **Das Logo fehlte in der fertigen Version.** Auf „Update & Über" lud das
  Programm `assets/xharig.png`, der Bau packte diese Datei aber nie ein — beim
  Start aus dem Quellcode fiel das nie auf, weil sie dort liegt.

- **Das „ⓘ" am Overlay öffnete ein eigenes Fenster mit eigener Update-Logik** —
  und in dem fehlte der Neustart-Knopf. Wer darüber ging, lud die neue Version
  herunter und stand dann vor einem Satz statt vor einem Knopf. Jetzt führt es
  ins Hauptfenster auf „Was ist neu"; der Reiter „Update & Über" liegt daneben.
  **Ein Weg statt zwei.** Gemeldet von Morkhan.
- **Gestreckte Knöpfe füllten nur die halbe Breite.** Betraf vor allem die
  Knöpfe unter den beiden Update-Kästen. Gemeldet von Morkhan.

- **Das Update über das Infofenster kam nie an.** Wer über das grüne „ⓘ" am
  Overlay ging statt über die Einstellungen, bekam nach dem Laden nur den Satz
  „Beim nächsten Start läuft die neue Version" — **und keinen Knopf dafür**.
  Unter Windows stimmt der Satz zudem nicht: Dort tauscht ein Hilfsskript die
  Datei erst, wenn das Programm beendet ist, und gibt nach zwei Minuten auf. Wer
  weiterspielte, hatte am Ende gar kein Update. Jetzt steht dort derselbe
  „⟳ Jetzt neu starten"-Knopf wie in den Einstellungen. Gemeldet von Morkhan.
- **Beim Update blitzte kurz ein Konsolenfenster auf.** Das Hilfsskript läuft
  seit v3.0.0 unsichtbar — der `taskkill` davor, der ein schon laufendes Skript
  wegräumt, wurde dabei übersehen. Gemeldet von Morkhan.

- **Fünf Fehler scheiterten bisher lautlos.** Ließen sich Einstellungen, die
  Merkliste, der „Neu"-Stand, der Autostart oder ein gespeicherter Bericht nicht
  schreiben, passierte einfach nichts — die Einstellung war nach dem Neustart
  wieder alt, und im Fehlerbericht stand nichts. Diese Stellen melden jetzt.

- **Der Fehlerbericht ließ die Spielsprache leer.** Dort stand nur ein Strich,
  obwohl die Erkennung einwandfrei lief — die Abfrage lieferte zwei Werte, der
  Bericht erwartete einen, und der Fehler wurde stillschweigend verschluckt.
  Jetzt steht dort, wonach im Log gesucht wird **und woher die Formulierung
  stammt**: aus der `global.ini` des Spiels oder aus der eingebauten Tabelle.
  Das ist die erste Frage bei „er erkennt meine Baupläne nicht".
- **Abgeschnittene Beschreibungen an drei Stellen.** Bei schmalem Fenster fehlten
  wenige Pixel, und die letzten Zeichen fielen weg. Betroffen waren die
  Update-Kanäle, „Angaben in die Auftragstexte schreiben" und „Wie oft
  nachgesehen wird".

- **Der Assistent merkte sich die gewählte Textquelle nicht.** Er holte die
  Texte und setzte sie ein, schrieb die Wahl aber nirgends hin — unter „Angaben
  im Spiel" stand danach keine der drei Quellen angewählt. Gemeldet von Haldjas.
- **Update unter Windows spuckte Konsolenfenster aus.** Das Hilfsskript, das die
  laufende `.exe` austauscht, lief in einer Endlosschleife weiter, solange die
  Datei gesperrt war — und sie bleibt gesperrt, bis das Programm beendet wird.
  Jeder weitere Klick auf „holen" startete noch ein Fenster. Jetzt ist nach zwei
  Minuten Schluss, das Fenster bleibt unsichtbar, und ein schon laufendes
  Hilfsskript wird vorher beendet.
- **„Jetzt nachsehen" hat nicht nachgesehen.** Der Knopf zeigte die Meldung „Suche nach
  einer neuen Version …" und suchte nicht. Wessen Zwischenspeicher veraltet war, kam damit
  nicht heraus — ein Tester bekam auf rc18 weiterhin rc12 angeboten. Jetzt wird wirklich
  gefragt, das Ergebnis gesagt und die Anzeige nachgezogen.
- **Das Selbst-Update ging unter Linux in den Windows-Zweig** und meldete „[Errno 2] No such
  file or directory: 'cmd'". Der Riegel gegen fremde Programme verglich den eigenen Code mit
  `APPDIR` — nur entpackt sich PyInstaller in ein **eigenes** Verzeichnis, der Vergleich
  schlug also immer fehl. Maßgeblich ist jetzt der Dateiname.
- **Das Selbst-Update hätte fremde Programme überschreiben können.** Es hielt jede Datei
  für sich selbst, auf die die Umgebungsvariable `APPIMAGE` zeigte — und die steht in
  **jedem** Programm, das aus einem AppImage heraus gestartet wurde. Jetzt muss auch der
  eigene Code aus dem zugehörigen `APPDIR` kommen, und ein zweiter Riegel lehnt jede
  Zieldatei ab, deren Name nicht zum Programm gehört.
- **Das Selbst-Update scheiterte unter Linux immer.** Geladen wurde nach `/tmp`,
  eingespielt mit `os.replace()` — und `/tmp` ist auf so gut wie jedem Linux ein eigenes
  Dateisystem. Über Dateisystemgrenzen kann `os.replace` nicht verschieben, das endet mit
  „[Errno 18] Invalid cross-device link". Der Kommentar im Code versprach schon immer
  „neben das laufende Programm" — jetzt tut es der Code auch, und das Einspielen ist
  nebenbei atomar geworden.
- **Absturz beim allerersten Start** (`SIGSEGV`), gemeldet von Bomb20. Der Assistent legte
  eine **eigene** Tk-Instanz an und zerstörte sie am Ende; das Overlay legte danach eine
  zweite an. Nach dem `destroy()` der ersten leben Schriften, Bilder und offene Aufträge
  weiter und zeigen auf einen toten Interpreter — ob das gutgeht, hängt am Zeitpunkt. Sein
  Satz „mit Debugging an lief es durch" ist der Fingerabdruck dafür. Es gibt jetzt nur noch
  **eine** Tk-Instanz im ganzen Programm.
- **Die Marken `[SCBPW]` waren im Spiel sichtbar.** Im Auftragstitel stand „Security
  Patrol**[SCBPW]** [BP 3/6]**[/SCBPW]**". Sie sorgten dafür, dass sich Eingefügtes exakt
  wieder entfernen lässt — nur will das niemand in seinem Spiel lesen. Jetzt steht gar
  keine Marke mehr im Text: Der **Wortlaut vor der Einfügung** wird gemerkt, und das
  Zurücksetzen stellt ihn wieder her. Das ist genauer als vorher. Geprüft mit
  `tools/injektion_pruefen.py` an der echten Datei: einspielen und entfernen lässt 743
  Textstellen auf das Zeichen genau so, wie sie waren.
- **Im Spiel stand nur die Zahl, nicht welche Baupläne.** Ein Auftrag hat einen Titel, aber
  oft ein Dutzend Beschreibungen — je eine für „zur Ruinenstation", „zum Verteilzentrum"
  und so weiter. Die Vertragsdaten nennen dazu nur **eine**; die übrigen blieben leer. Im
  Titel stand „[BP 0/12]", und wer die Beschreibung öffnete, um zu sehen *welche* zwölf,
  fand nichts. Gemessen: allein bei Covalex 51 Beschreibungen im Spiel, davon 7 mit
  Angaben. Sie werden jetzt über den gemeinsamen Namensanfang mitversorgt.
- **„Handfeuerwaffe" und „FPS-Waffe" waren zwei Gruppen für dieselbe Sache** — 87 unter
  der einen Kennung, zwei unter der anderen.
- **„Zeilen im Overlay" hatte keine Wirkung.** Die Einstellung wurde gespeichert und nie
  gelesen; im Overlay galt fest die Zahl 200. Jetzt gilt der eingestellte Wert, mit 20 als
  Vorgabe — 200 Baupläne sammelt in einer Sitzung ohnehin niemand.
- **„Durchsuchen" öffnete keinen Dialog** — weder beim Star-Citizen-Ordner noch bei den
  eigenen Dateien. Beide tun es jetzt, und unter Linux mit dem Dialog des Systems statt
  dem grauen von Tk.
- **Die letzten Baupläne der Liste lagen übereinander.** X11 rechnet Fensterkoordinaten in
  16 Bit; alle 722 in einem Rahmen ergeben rund 33000 Pixel und damit 16 Zeilen jenseits
  der Grenze. Die Liste wird jetzt bei Bedarf in Blöcken gezeigt — sichtbar bleibt alles.
- **Die Rollleiste ließ sich nicht anfassen.** Gezeichnet wurde der Griff mit einer
  Mindesthöhe, geprüft wurde mit der rechnerischen — wer die untere Hälfte traf, galt als
  „daneben".
- **Das Fenster startete außerhalb des Bildschirms.** Ohne gemerkte Lage stellte Tk es
  nach `+0+0`; bei einem hochkant stehenden Monitor links außen liegt dort kein Bild.
  Start und „Fensterlage zurücksetzen" setzen es jetzt mittig auf den Hauptbildschirm.
- **Der Autostart war zwischen Overlay und Einstellungen nicht synchron.** Beide lasen
  ihren Zustand nur beim Zeichnen.
- **Das Fenster-Icon fehlte in jeder fertigen Version** — auf beiden Systemen. Die Datei
  lag zur Laufzeit gar nicht bei.

### Dank

Diese Version ist zu einem großen Teil das Verdienst von zwei Testern, die sich
die Mühe gemacht haben, Fehler nicht nur zu bemerken, sondern sie so genau zu
beschreiben, dass sie zu finden waren:

- **Haldjas** (pr0) — der Vorschlag mit dem Aufblend-Betrieb; dazu das
  Setup, das an der laufenden Datei abbrach, die Konsolenfenster beim Update,
  das verschwundene Symbol neben der Uhr, der Absturz nach dem Neustart, die
  Schriftgröße, die das Overlay nicht erreichte, die vergessene Textquelle im
  Assistenten — und der Fund, der alles erklärte: „da bleibt er bei rc25".
- **Bomb20** (pr0) — der Absturz beim allerersten Start (der Fehler, den nur
  neue Nutzer je gesehen hätten), der wirkungslose Knopf „Jetzt nachsehen" und
  der Hinweis, dass die Textquelle „Deutsch" das ganze Spiel übersetzt.
- **Morkhan** (KRT) — der Vorschlag, Star Citizen gleich aus dem Werkzeug
  heraus starten zu können.

Die Bauplan-Angaben beruhen auf den offen veröffentlichten Vertragsdaten des
**SC-Deutsch-Launcher-Teams** und auf **scmdb.net**.

## v2.0.0 - 2026-08-24

**Aus dem Windows-Overlay ist ein eigenständiges Werkzeug für Windows und Linux
geworden — und es schreibt die Bauplan-Angaben auf Wunsch direkt ins Spiel.**

Der SC Deutsch Launcher wird nicht mehr gebraucht. Geprüft an einer echten
Star-Citizen-Installation, mit deutschem **und** englischem Client.

### Ohne Launcher

- **Die `Game.log` ist die Quelle.** Der Bauplan-Bestand wird selbst geführt; beim ersten
  Start werden die aufgehobenen Spielprotokolle nachgelesen. Bleibt eine Lücke, sagt das
  Werkzeug das, statt eine unvollständige Liste als vollständig auszugeben.
- **Die Spielsprache erschließt sich von selbst.** Die Bauplan-Meldung im Log ist
  übersetzt; das Werkzeug leitet den Wortlaut aus den eigenen Logs ab — es kennt über 700
  Bauplan-Namen, und steht einer davon in einer Logzeile, ist der Text davor die gesuchte
  Formulierung. Deutsch und Englisch sind gemessen, andere Sprachen findet es selbst.
- **Ist der Launcher da, wird er weiter genutzt** — auch wenn er auf einer eingehängten
  Windows-Platte liegt, was bei Dual-Boot der Normalfall ist.

### Bauplan-Liste

- **Alle Baupläne zum Nachschlagen**, mit Suche, Filtern und Fortschritt. Gesucht wird
  über Name, Kategorie, Klasse (`military`, `stealth`, `civilian`, …), Hersteller und
  Gütegrad.
- **Woher jeder Bauplan kommt** — Fraktion, Auftrag, nötiger Ruf, Belohnung **und wo sich
  der Auftrag annehmen lässt**.
- **Vier Bereiche** zum Ein- und Ausblenden: Schiffsteile, FPS-Waffen, Rüstung & Kleidung,
  Sonstiges. Sortiert nach Bereichen statt nach Alphabet.
- **Merkliste per Klick.** Taucht ein beobachteter Bauplan auf, meldet das Werkzeug ihn
  auffällig — und trägt den erfüllten Wunsch selbst wieder aus.

### Bauplan-Angaben im Spiel

- **An jede Mission, die Baupläne ausschüttet**, kommt die Liste in den Missionstext —
  mit Kästchen: angehakt, was man hat, leer, was fehlt. Dazu ein Kürzel im Titel
  (`[BP 2/3]`), sichtbar schon in der Auftragsliste. **681 Textstellen**, deutsch und
  englisch.
- **Drei Wege zur Grundlage:** die deutsche Übersetzung von
  [rjcncpt](https://github.com/rjcncpt/StarCitizen-Deutsch-INI),
  [StarStrings](https://github.com/MrKraken/StarStrings) von MrKraken — oder die
  englischen Originaltexte aus dem eigenen `Data.p4k`, ganz ohne Download.
- **Rückgängig auf den Buchstaben genau.** Wer StarStrings nutzt, behält es: Dessen
  Auszeichnungen bleiben stehen, die eigenen kommen dazu.
- Es wird **gefragt**, nie stillschweigend gemacht. Voreingestellt ist nichts.
- **Es bleibt von selbst aktuell.** Beim Start und danach alle sechs Stunden wird
  nachgesehen: neue Übersetzung, neue Bauplan-Daten — oder eine `global.ini`, die ein
  Spiel-Patch ersetzt hat. Alles drei trägt sich dann selbst wieder ein.
  - **Warum das kein Beiwerk ist:** Jedes Übersetzungs-Update und jeder Patch schreibt
    die Datei neu, die Angaben sind dann **weg** — und nach einem Patch geben Missionen
    andere Baupläne aus. Beides fällt niemandem auf, weil das Spiel normal weiterläuft.
    Ohne diesen Abgleich spielt man irgendwann mit falschen Daten.
  - Angefasst wird nur, was der Spieler selbst eingerichtet hat.

### Bedienung

- **Einrichtungsassistent** in fünf Schritten, jederzeit wiederholbar — und ein
  **Einstellungsfenster** für alle Angaben auf einmal.
- **Deutsch und Englisch**, umschaltbar, wirkt sofort.
- Erklärtexte beim Überfahren jedes Zeichens, einstellbare Durchsichtigkeit (wichtig für
  alle mit nur einem Bildschirm), Signalton, Autostart.
- **Update-Meldung mit Änderungsprotokoll** — auch für übersprungene Versionen.

### Verteilung

- **Fertige Dateien für beide Systeme**, von GitHub bei jedem Versions-Tag gebaut. Das
  AppImage entsteht in einem Ubuntu-22.04-Container, damit es auf verbreiteten Systemen
  startet.
- ⚠️ **Wichtig für Arch, Fedora und openSUSE:** Genau dieser Container war auch eine
  Falle. Das gebündelte Python suchte seinen Zertifikatsspeicher unter dem Ubuntu-Pfad
  `/usr/lib/ssl`, den es dort nicht gibt — **jede** HTTPS-Verbindung scheiterte still.
  Kein Bauplan-Katalog, keine Übersetzung, keine Update-Meldung; das Programm startete,
  konnte aber nichts laden. Der Starter sucht den Speicher jetzt an allen üblichen
  Stellen. Auf Ubuntu und Debian fiel das nie auf.
- **Nichts Fremdes wird mitgeliefert.** Bauplan-Katalog (scmdb), Übersetzung und
  StarStrings werden zur Laufzeit beim Nutzer von ihrer eigenen Adresse geholt.

### Dank

Die Bauplan-Angaben beruhen auf den offen veröffentlichten Vertragsdaten des
**SC-Deutsch-Launcher-Teams** (813 Verträge, deutsch und englisch) und auf **scmdb.net**.
Ohne beide gäbe es diese Version nicht.

## v2.0.0-rc1 - 2026-08-24

> **Vorabversion zum Ausprobieren.** Der Umbau ist inhaltlich fertig und gründlich
> geprüft — aber noch nie an einer echten Star-Citizen-Installation gelaufen, nur
> an nachgebauten Logs. Wer sie testet, hilft genau dabei. Rückmeldungen gern als
> [Issue](../../issues).

**Aus dem Windows-Overlay ist ein eigenständiges Werkzeug für Windows und Linux
geworden.** Der SC Deutsch Launcher ist nicht mehr nötig, der Bauplan-Bestand wird
selbst geführt, und zu den meisten Bauplänen steht dabei, woher man sie bekommt.

### Hinzugefügt


- **Der Watcher findet die Spielsprache selbst heraus.** Die Bauplan-Meldung im Log ist übersetzt; bisher war nur die deutsche Formulierung gemessen, die englischen waren geraten und andere Sprachen gar nicht vorgesehen. Jetzt erschließt er sie aus den eigenen Logs: Er kennt über 700 Bauplan-Namen — steht in einer Logzeile einer davon, ist der Text davor die gesuchte Formulierung. An einer erfundenen französischen Version geprüft.
  - Verlangt werden **zwei** verschiedene Treffer für dieselbe Formulierung. Bei einem könnte es Zufall sein (ein Bauplan-Name taucht auch in anderen Meldungen auf).
  - Gefundenes landet in `phrasen.json` — derselben Datei, die man auch von Hand pflegen kann. Keine zweite, versteckte Wahrheit.
  - Damit ist das Werkzeug nicht mehr auf die Sprachen angewiesen, die jemand vorher eingetragen hat.
- **Projektseite auf Englisch und Deutsch**, mit Umschalter oben in beiden Versionen. **Englisch ist die Hauptseite** (`README.md`), Deutsch liegt daneben (`README.de.md`) — auf GitHub ist das Publikum international, und wer über die Star-Citizen-Foren kommt, sollte nicht erst einen Umschalter suchen müssen. Deutschsprachige Spieler kommen mit Englisch zurecht; umgekehrt gilt das seltener.
- **Merkliste per Klick** (`scbp/merkliste.py`). In der Bauplan-Liste macht ein Klick auf den Stern aus jedem Eintrag einen Wunsch — taucht er auf, meldet ihn der Watcher auffällig in Gold. Dafür muss niemand mehr eine `watchlist.json` von Hand anlegen.
  - Eigener Filter **⭐ beobachtet** zeigt, worauf man gerade wartet.
  - **Erfüllte Wünsche verschwinden von selbst.** Landet ein beobachteter Bauplan im Bestand, sagt der Watcher einmal Bescheid und trägt ihn aus — eine Liste voller längst erledigter Wünsche wäre keine Merkliste, sondern ein Archiv.
  - Von außen eingetragene **Muster** funktionieren weiter (ein eigenes Werkzeug des Autors schreibt dort Teile einer Rüstung hinein, deren endgültige Namen noch niemand kennt).
- **Fertige Dateien für beide Systeme, gebaut von GitHub.** Ein Versions-Tag löst den Bau aus: ein Windows-Rechner baut die `.exe`, ein Linux-Rechner das AppImage, beide werden ans Release gehängt — samt Beschreibung aus dem CHANGELOG, damit im Werkzeug unter „Was ist neu" dasselbe steht wie auf GitHub.
  - Das AppImage wird **in einem Ubuntu-22.04-Container** gebaut (glibc 2.35). Auf neuerem glibc gebaut, würde es auf verbreiteten Systemen gar nicht erst starten.
  - Der Bau bricht ab, wenn Tag und `__version__` nicht zusammenpassen. Wer „v2.0.0" lädt, soll im Fenster nicht etwas anderes lesen.
  - Niemand baut mehr selbst — weder die Nutzer noch der Autor.
- **Neue Versionen werden gemeldet und lassen sich nachlesen** (`scbp/aktualisierung.py`, `scbp/versionsfenster.py`). Das Werkzeug sieht höchstens einmal am Tag nach; gibt es etwas Neues, färbt sich ⓘ in der Titelleiste. Dahinter liegt die Versionsgeschichte — **auch für ältere Versionen**, damit man nachlesen kann, was man übersprungen hat.
  - Geladen wird ausschließlich von `github.com`; eine Datei von woanders wird abgelehnt.
  - Unter Linux ersetzt sich das AppImage selbst, unter Windows übernimmt ein Hilfsskript nach dem Beenden (eine laufende `.exe` kann sich nicht selbst überschreiben). Wer aus dem Quellcode startet, bekommt keinen Selbstersatz angeboten — dort ist `git pull` der richtige Weg.
- **Prüfintervall und Signalton sind einstellbar** (`pruefintervall_sekunden`, `signalton` in `einstellungen.json`). Grenzen 1–60; eine vertippte `0` wird auf 1 gezogen statt zur Dauerschleife.
- **Einrichtungsassistent** (`scbp/assistent.py`) — vier Schritte, **jederzeit wiederholbar** über ⟳ in der Titelleiste. Läuft beim ersten Start von allein und immer dann, wenn Star Citizen nicht gefunden wird.
  1. **Sprache** — zuerst, damit der Rest lesbar ist
  2. **Star Citizen finden** — mit Auswahlknopf und Prüfung *beim Tippen*, nicht erst beim Speichern. Der Spieler darf jede Ebene treffen: den LIVE-Ordner, den darüber, den Programme-Ordner oder gleich das Wine-Präfix — sogar die `Game.log` selbst. Es wird daraus der richtige Ordner gemacht und angezeigt, welcher genommen wird.
  3. **Bisherige Baupläne holen** — läuft von selbst, hier bekommt der Spieler seinen ganzen Bestand aus den aufgehobenen Logs geschenkt
  4. **Fertig** — was jetzt passiert und wo die Liste steckt
  - Wiederholbar ist Absicht: Wer sich mit Rechnern nicht auskennt, soll etwas nachstellen können, ohne zu wissen, in welchem Menü es steckt. Ein Assistent führt; ein Einstellungsfenster setzt voraus, dass man weiß, wonach man sucht.
- **Verwaltungsfenster aus der Melde-Leiste** — ☰ in der Titelleiste öffnet die Bauplan-Liste, ein zweiter Klick holt sie nach vorn statt ein zweites Fenster aufzumachen.

**Was sich am Verhalten ändert:** Wird Star Citizen nicht gefunden, zeigte das Programm bisher eine Meldung und **beendete sich** — der Spieler hätte eine JSON-Datei von Hand bearbeiten und neu starten müssen. Das macht niemand. Jetzt wird gefragt, und die Angabe wirkt sofort.

- **Bauplan-Katalog mit Herkunft** (`scbp/katalog.py`). 714 Baupläne, für 655 davon (92 %) steht dabei, **woher man sie bekommt**: Fraktion, Auftrag, nötiger Rang samt Rufpunkten, Belohnung in aUEC und Rufgewinn. Das kann der SC Deutsch Launcher nicht — „mir fehlt X" ist die halbe Information, „X droppt bei Fraktion Y ab Rang Z" die ganze.
  - Die Kette durch die scmdb-Daten: `contracts[].blueprintRewards[].blueprintPool` → `blueprintPools[…].blueprints[].name`, dazu `factions`, `minStanding` und `factionRewardsPools`.
  - Bezugsquellen sind nach **leichtestem Weg** sortiert (niedrigste Ruf-Anforderung zuerst), höchstens drei je Bauplan.
  - Der Sammel-Dump ist rund 12 MB und wird **nicht** aufgehoben, sondern sofort zu 347 KB eingedampft. Geholt wird einmal je Spielversion, mit Wiederholversuchen — bei der Größe reißt die Leitung gern mitten drin ab (beim Bauen zweimal passiert).
- **Verwaltungsfenster** (`scbp/bestandsfenster.py`): durchsuchbare Liste, nach Art gruppiert, Filter *alle / habe ich / fehlt mir*, Fortschrittsanzeige, Häkchen per Klick, Herkunft per Klick ausklappbar.
- **Deutsch und Englisch, umschaltbar** (`scbp/sprache.py`). Standard ist die Systemsprache, aber das Feld `sprache` in `einstellungen.json` (`de`/`en`/`auto`) sticht sie — wer ein englisches System fährt und trotzdem Deutsch lesen will, soll das dürfen. Umschalten wirkt sofort, ohne Neustart.
  - Auch die **Bauplan-Arten** hängen daran: `Char_Armor_Helmet` ist nichts für Menschen, „Helm" nichts für eine englische Liste.
  - Der Selbsttest prüft, dass jeder Text beide Sprachen hat und **jede Art aus dem Katalog übersetzt ist** — nach einem SC-Patch können neue dazukommen.

### Entfernt

- **`EXE bauen.bat`.** Seit GitHub die Dateien baut, braucht sie niemand mehr — und sie war bereits falsch: Sie baute ohne `--add-data`, die daraus entstandene `.exe` hätte weder Änderungsprotokoll noch Katalogdaten gehabt. Zum Ausprobieren lässt sich der Bau-Workflow ohne Tag von Hand starten.

### Wissenswert

- **714 Baupläne, nicht 1573.** Die Datei `crafting_items` zählt alle craftbaren Gegenstände; ein Bauplan droppt nur für einen Teil davon. Für eine Liste zum Abhaken wäre die große Zahl irreführend — maßgeblich sind die `blueprintPools`.
- **Die scmdb-Daten werden weiterhin nicht mitgeliefert** (CC BY-NC-ND), sondern beim Nutzer geholt. `SC_BP_NO_NET=1` schaltet es ab; ohne Katalog fehlt nur die Liste, die Erkennung läuft weiter.


- **Läuft unter Linux.** Eine Codebasis für beide Systeme, keine zweite Version. Wo die Dateien liegen, entscheidet der neue Baustein `scbp/pfade.py`: unter Windows `%APPDATA%` und `C:\Program Files`, unter Linux `~/.config` und das Wine-Präfix (gesucht wird an den Stellen, an denen lug-helper, Lutris, Bottles und Heroic ihre Installationen ablegen). Eigene Wege gehen über `SC_BP_HOME`, `SC_INSTALL_DIR` und `SC_BP_LAUNCHER`.
- **Eigener Bauplan-Bestand** (`bestand.json` im eigenen Ordner). Jeder Fund wird dauerhaft festgehalten, mit Herkunft (Log, Nachlese, Launcher, von Hand). Geschrieben wird über eine Nebendatei und Umbenennen, damit ein Absturz mitten im Speichern nichts zerreißt; die Vorgängerfassung bleibt als `bestand.bak.json` liegen.
- **Nachlese beim Start.** Die aufgehobenen Logs vergangener Sitzungen (`logbackups/`) werden durchgesehen und still in den Bestand übernommen — wer ohne laufenden Watcher gespielt hat, verliert nichts mehr. Beim allerersten Start wird auch die **laufende** Game.log von vorn gelesen, sonst wäre ausgerechnet die gerade laufende Sitzung ein Loch.
- **Ehrlicher Lückenhinweis.** Reichen die vorhandenen Sicherungen nicht bis zum letzten bekannten Stand zurück, sagt der Watcher das als eigene Zeile (ℹ) — statt eine unvollständige Liste als Bestand auszugeben. Dafür gibt es die Liste zum Abhaken.
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

- **Markenfarbe auf `#9ce430` gezogen.** Das Overlay lief noch mit `#47aa42` — der Xharig-Farbe von vor dem Logo-Wechsel. Betrifft `ACCENT` im Overlay und `GREEN` im Icon-Werkzeug. Für helle Flächen (README-Badges) bleibt es beim Text-Grün `#5fa522`.
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
