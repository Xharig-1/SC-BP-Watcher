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
VersionInfoVersion={#AppVersion}

; Kein Administrator — siehe Kopf
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
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
