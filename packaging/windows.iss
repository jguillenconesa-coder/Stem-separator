#define AppVersion "0.1.0"
[Setup]
AppId={{79A4F012-A35C-4EC3-B769-ABF1F1BCC132}
AppName=Stem Separator
AppVersion={#AppVersion}
AppPublisher=jguillenconesa-coder
DefaultDirName={localappdata}\Programs\Stem Separator
DefaultGroupName=Stem Separator
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=StemSeparator-Setup-{#AppVersion}-x64
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\StemSeparator.exe
[Files]
Source: "..\dist\StemSeparator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\Stem Separator"; Filename: "{app}\StemSeparator.exe"
Name: "{autodesktop}\Stem Separator"; Filename: "{app}\StemSeparator.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Crear acceso directo en el escritorio"; Flags: unchecked
[Run]
Filename: "{app}\StemSeparator.exe"; Description: "Abrir Stem Separator"; Flags: nowait postinstall skipifsilent
