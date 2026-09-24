; Instaler za Video Download (Inno Setup 6). Pravi se preko: python tools/build_release.py
; Instalira se samo za trenutnog korisnika (bez administratorskih prava), pa auto update
; može zamijeniti fajlove bez UAC prozora.

#ifndef AppVersion
  #error Pokreni preko tools/build_release.py (proslijedi /DAppVersion=x.y.z)
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\VideoDownload"
#endif
#ifndef IconFile
  #define IconFile "..\build\icon.ico"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist\installer"
#endif

[Setup]
AppId={{6C1B7C8E-3F2A-4B8D-9E51-2A7D0C4F9B13}
AppName=Video Download
AppVersion={#AppVersion}
AppVerName=Video Download {#AppVersion}
VersionInfoVersion={#AppVersion}
AppPublisher=Video Download
DefaultDirName={localappdata}\Programs\Video Download
DefaultGroupName=Video Download
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=VideoDownload-Setup-{#AppVersion}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\VideoDownload.exe
UninstallDisplayName=Video Download
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Jezik se bira na početku; ponuđen je jezik Windowsa ako je među pet.
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
UsePreviousLanguage=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "bosnian"; MessagesFile: "Bosnian.isl"; LicenseFile: "{#SourceDir}\legal\agreement_bs.txt"; InfoBeforeFile: "{#SourceDir}\legal\privacy_bs.txt"
Name: "english"; MessagesFile: "compiler:Default.isl"; LicenseFile: "{#SourceDir}\legal\agreement_en.txt"; InfoBeforeFile: "{#SourceDir}\legal\privacy_en.txt"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"; LicenseFile: "{#SourceDir}\legal\agreement_de.txt"; InfoBeforeFile: "{#SourceDir}\legal\privacy_de.txt"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"; LicenseFile: "{#SourceDir}\legal\agreement_es.txt"; InfoBeforeFile: "{#SourceDir}\legal\privacy_es.txt"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"; LicenseFile: "{#SourceDir}\legal\agreement_fr.txt"; InfoBeforeFile: "{#SourceDir}\legal\privacy_fr.txt"

[CustomMessages]
bosnian.BrowserNote=Za preuzimanje iz Edge/Chrome browsera učitaj dodatak iz foldera „extension" (Pomoć → Preuzimanje iz browsera).
english.BrowserNote=To download from Edge/Chrome, load the add-on from the "extension" folder (Help → Downloading from the browser).
german.BrowserNote=Zum Herunterladen aus Edge/Chrome die Erweiterung aus dem Ordner „extension" laden (Hilfe → Aus dem Browser herunterladen).
spanish.BrowserNote=Para descargar desde Edge/Chrome, carga el complemento de la carpeta «extension» (Ayuda → Descargar desde el navegador).
french.BrowserNote=Pour télécharger depuis Edge/Chrome, chargez l'extension du dossier « extension » (Aide → Télécharger depuis le navigateur).

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Kod ažuriranja ukloni stare biblioteke da ne ostanu fajlovi prethodne verzije.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\Video Download"; Filename: "{app}\VideoDownload.exe"
Name: "{autodesktop}\Video Download"; Filename: "{app}\VideoDownload.exe"; Tasks: desktopicon

[Registry]
; Jezik izabran u instaleru postaje jezik aplikacije (isti ključ koristi QSettings).
Root: HKCU; Subkey: "Software\VideoDownload\VideoDownload"; ValueType: string; ValueName: "language"; ValueData: "{code:AppLanguage}"; Flags: uninsdeletekeyifempty
; Registraciju za Chrome/Edge upisuje aplikacija pri pokretanju; deinstalacija je briše.
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.videodl.bridge"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.videodl.bridge"; Flags: uninsdeletekey dontcreatekey

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\VideoDownload\native-host"
Type: files; Name: "{localappdata}\VideoDownload\bridge.json"
; Preuzeti yt-dlp je dio programa, ne korisnikovi podaci (red i istorija ostaju).
Type: filesandordirs; Name: "{localappdata}\VideoDownload\yt-dlp"

[Run]
Filename: "{app}\VideoDownload.exe"; Description: "{cm:LaunchProgram,Video Download}"; Flags: nowait postinstall skipifsilent
; Tiho ažuriranje iz aplikacije (/update=1): aplikacija se sama ponovo pokreće.
Filename: "{app}\VideoDownload.exe"; Flags: nowait; Check: IsUpdate

[Code]
function AppLanguage(Param: String): String;
begin
  case ActiveLanguage of
    'bosnian': Result := 'bs';
    'german': Result := 'de';
    'spanish': Result := 'es';
    'french': Result := 'fr';
  else
    Result := 'en';
  end;
end;

function IsUpdate: Boolean;
begin
  Result := ExpandConstant('{param:update|0}') = '1';
end;

function InitializeSetup: Boolean;
var
  Tries: Integer;
begin
  Result := True;
  // Ažuriranje iz aplikacije: sačekaj da se stara verzija ugasi (drži mutex dok radi).
  if IsUpdate then
  begin
    Tries := 0;
    while CheckForMutexes('VideoDownloadRunning') and (Tries < 120) do
    begin
      Sleep(250);
      Tries := Tries + 1;
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 + CustomMessage('BrowserNote');
end;
