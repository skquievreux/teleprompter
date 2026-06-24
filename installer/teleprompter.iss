; Inno Setup script — builds a proper Windows installer (Start Menu shortcut,
; uninstaller entry in "Apps & Features") around the PyInstaller .exe.
; AppVersion is passed in from CI: iscc /DMyAppVersion=1.2.0 installer/teleprompter.iss
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{9F4D9B7E-8B5B-4C6F-9B5C-3C6B1B4E7B3E}}
AppName=Teleprompter
AppVersion={#MyAppVersion}
AppPublisher=Steffen Quievreux
AppPublisherURL=https://github.com/skquievreux/teleprompter
DefaultDirName={autopf}\Teleprompter
DefaultGroupName=Teleprompter
UninstallDisplayIcon={app}\teleprompter.exe
OutputDir=..\dist
OutputBaseFilename=teleprompter-setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "..\dist\teleprompter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Teleprompter"; Filename: "{app}\teleprompter.exe"
Name: "{autodesktop}\Teleprompter"; Filename: "{app}\teleprompter.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"

[Run]
Filename: "{app}\teleprompter.exe"; Description: "Teleprompter jetzt starten"; Flags: nowait postinstall skipifsilent
