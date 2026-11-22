#ifndef AppVersion
  #define AppVersion "1.0.1"
#endif
#define AppName "四象限待办"
#define AppExe "TodoQuadrant.exe"

[Setup]
AppId={{B7B6EC10-8E06-4F46-9ADC-AC6565EF00F2}
AppName={#AppName}
AppVersion={#AppVersion}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\TodoQuadrant
UsePreviousAppDir=yes
DisableDirPage=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no
OutputDir=..\..\dist\windows
OutputBaseFilename=TodoQuadrant-{#AppVersion}-windows-x64-setup
SetupIconFile=TodoQuadrant.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no

[Languages]
Name: "zhcn"; MessagesFile: "languages\ChineseSimplified.isl"

[Files]
Source: "..\..\.build\windows\dist\TodoQuadrant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\卸载{#AppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "启动{#AppName}"; Flags: nowait postinstall skipifsilent
