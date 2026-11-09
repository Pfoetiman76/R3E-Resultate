; Inno Setup Skript fuer R3E Resultate (RaceRoom Results Companion)
; Baut aus dist\R3EResultate\ einen Windows-Installer.
; Version kommt aus der Umgebungsvariable APP_VERSION (in CI aus dem Git-Tag).
#define AppName "R3E Resultate"
#ifndef AppVer
  #define AppVer GetEnv("APP_VERSION")
#endif
#if AppVer == ""
  #define AppVer "0.0.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Pfoetiman76
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName} {#AppVer}
OutputDir=Output
OutputBaseFilename=R3E-Resultate-Setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\R3EResultate.exe

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"

[Files]
Source: "..\dist\R3EResultate\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\R3EResultate.exe"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\R3EResultate.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\R3EResultate.exe"; Description: "{#AppName} starten"; Flags: nowait postinstall skipifsilent
