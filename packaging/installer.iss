; Installer für Windows — gebaut mit Inno Setup (kostenlos, auf den
; GitHub-Baurechnern vorinstalliert).
;
; Warum überhaupt ein Installer: Nutzer haben gemeldet, dass sie die .exe
; selbst irgendwohin ziehen müssen. Genau daran springen Erstnutzer ab.
;
; ⚠ Ziel ist {localappdata}\Programs, NICHT "Programme":
;   * kein Administrator nötig — weder beim Installieren noch beim Update,
;   * und nur so überlebt das Selbst-Update. Es tauscht die laufende .exe per
;     move aus; in C:\Program Files scheitert das an den Rechten.
;   So machen es Discord, VS Code und der SC Deutsch Launcher auch.
;
; Die eigenen Dateien des Spielers (Dokumente\SC BP Watcher) fasst der
; Installer NICHT an — weder beim Installieren noch beim Deinstallieren.
; Ein Bauplan-Bestand, den man über Monate sammelt, gehört nicht dem Programm.

#define AppName "SC BP Watcher"
#define AppPublisher "Xharig"
#define AppURL "https://github.com/Xharig-1/SC-BP-Watcher"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

; ⚠ Windows verlangt für die Datei-Version eine reine Zahlenfolge. Eine
; Vorabfassung wie "3.0.0-rc1" laesst Inno Setup mit "Value of [Setup] section
; directive VersionInfoVersion is invalid" abbrechen — der ganze Bau schlug fehl,
; als die erste Testfassung von v3.0.0 gebaut werden sollte. Deshalb wird hier
; alles ab dem Bindestrich abgeschnitten: Angezeigt wird weiterhin die volle
; Bezeichnung, nur die technische Datei-Version ist die nackte Zahl.
#define ZahlVersion AppVersion
#if Pos("-", ZahlVersion) > 0
  #define ZahlVersion Copy(ZahlVersion, 1, Pos("-", ZahlVersion) - 1)
#endif

[Setup]
; ⚠ Diese Kennung bleibt für immer gleich. Ändert sie sich, hält Windows jede
; Fassung für ein anderes Programm — der Nutzer hätte drei Einträge in "Apps &
; Features" und drei Startmenü-Ordner.
AppId={{7C4B1E93-2A6F-4D58-B0E1-9F3A5C8D2461}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#ZahlVersion}

; ⚠ Das laufende Programm muss beendet werden, bevor die .exe ersetzt wird.
; Ohne diese drei Zeilen bricht das Setup mitten im Kopieren ab:
;
;     An error occurred while trying to replace the existing file:
;     DeleteFile failed; code 32.
;     Der Prozess kann nicht auf die Datei zugreifen, da sie von einem
;     anderen Prozess verwendet wird.
;
; Genau so beim Testen gemeldet (Haldjas, 25.08.2026) — mit der Folge, dass die
; Installation halb fertig liegen blieb und der Watcher danach nur noch das
; Setup startete. `CloseApplications` fragt den Nutzer und schließt das
; Programm, `RestartApplications` startet es danach wieder.
;
; `AppMutex` ist die Voraussetzung dafür, dass Inno das laufende Programm
; überhaupt erkennt — der Name muss mit dem übereinstimmen, den das Programm
; beim Start setzt (siehe `sc_bp_watcher.py`).
; `force` statt `yes`: `yes` **bittet** das Programm zu schließen (der Restart
; Manager schickt ein WM_CLOSE). Ein Programm, das nicht mehr reagiert, hört das
; nicht — und danach scheitert das Kopieren wieder an „code 32". Genau so beim
; Testen gemeldet (Haldjas, 25.08.2026): „der installer schafft es dann aber
; immer noch nicht zu installieren, selber code 32 fehler wie am anfang".
; `force` beendet die Anwendung notfalls hart. Das ist hier vertretbar: Der
; Bauplan-Bestand liegt in `Dokumente\SC BP Watcher` und wird bei jeder Änderung
; geschrieben, nicht erst beim Beenden.
CloseApplications=force
RestartApplications=yes
AppMutex=SC-BP-Watcher-Einzelstart

; Kein Administrator — siehe Kopf.
;
; ⚠ Hier stand einmal `PrivilegesRequiredOverridesAllowed=dialog`. Das lässt Inno
; beim Installieren fragen, ob "für mich" oder "für alle Nutzer" — und wer "für
; alle" wählt, bekommt seinen Eintrag im **Maschinenzweig** der Registry. Genau
; das war am 26.08.2026 auf dem Testrechner passiert, mit zwei Folgen:
;
;   * `windows_eintrag_pflegen()` sucht unter HKCU und fand nichts. Die in
;     "Apps & Features" angezeigte Fassung wurde nie nachgezogen.
;   * Jedes Selbst-Update bräuchte eine Administrator-Abfrage, weil der
;     Installer wieder in den Maschinenzweig schreiben will.
;
; Ohne die Zeile landet alles im Benutzerzweig — passend zum Ziel unter
; `{localappdata}\Programs`, für das ohnehin nie Administratorrechte nötig sind.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto

OutputDir=..\dist
OutputBaseFilename=SC-BP-Watcher-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\SC-BP-Watcher.exe
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

; Deutsch und Englisch — das Werkzeug spricht beide, der Installer auch.
[Languages]
Name: "deutsch"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Mit Windows starten"; \
  GroupDescription: "Nach der Installation:"; Flags: unchecked

[Files]
Source: "..\dist\SC-BP-Watcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SC-BP-Watcher.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\SC-BP-Watcher.exe"; \
  Tasks: desktopicon

[Registry]
; Autostart nur, wenn der Spieler es angehakt hat — und im Benutzerzweig,
; damit kein Administrator nötig ist.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "SC BP Watcher"; \
  ValueData: """{app}\SC-BP-Watcher.exe"""; Flags: uninsdeletevalue; \
  Tasks: autostart

[Run]
Filename: "{app}\SC-BP-Watcher.exe"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

; Kein [UninstallDelete] für die Nutzerdaten: Wer deinstalliert, will das
; Programm loswerden — nicht seinen über Monate gesammelten Bauplan-Bestand.
