; Inno Setup script for the Flutter Windows build.
; Build first:
;   flutter build windows --release
; Then:
;   ISCC.exe packaging\windows\vibebook.iss
;
; The installer is unsigned. Windows SmartScreen will show a warning.

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

#define MyAppName "Vibebook"
#define MyAppPublisher "Vibebook"
#define MyAppExeName "vibebook_app.exe"

[Setup]
AppId={{6F1F8E1E-6E0B-4A8E-9D4F-6B0B0B7C1A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Vibebook
DefaultGroupName=Vibebook
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=Vibebook-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Vibebook"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Vibebook"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,Vibebook}"; Flags: nowait postinstall skipifsilent
