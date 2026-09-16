; *** Inno Setup 6.5.0+ bosanske poruke (latinica) ***
; Prevod za Video Download, prema Default.isl iz Inno Setupa.
;
; Napomena: ne dodavati tačku na kraj poruka koje je u originalu nemaju;
; Inno Setup je na tim mjestima dodaje sam.

[LangOptions]
LanguageName=Bosanski
LanguageID=$141A
LanguageCodePage=1250

[Messages]

; *** Naslovi aplikacije
SetupAppTitle=Instalacija
SetupWindowTitle=Instalacija - %1
UninstallAppTitle=Deinstalacija
UninstallAppFullTitle=Deinstalacija programa %1

; *** Razno
InformationTitle=Informacija
ConfirmTitle=Potvrda
ErrorTitle=Greška

; *** Poruke pokretača instalacije
SetupLdrStartupMessage=Instaliraće se %1. Želite li nastaviti?
LdrCannotCreateTemp=Nije moguće napraviti privremeni fajl. Instalacija je prekinuta
LdrCannotExecTemp=Nije moguće pokrenuti fajl u privremenom folderu. Instalacija je prekinuta
HelpTextNote=

; *** Greške pri pokretanju
LastErrorMessage=%1.%n%nGreška %2: %3
SetupFileMissing=Fajl %1 nedostaje u instalacionom folderu. Riješite problem ili nabavite novu kopiju programa.
SetupFileCorrupt=Instalacioni fajlovi su oštećeni. Nabavite novu kopiju programa.
SetupFileCorruptOrWrongVer=Instalacioni fajlovi su oštećeni ili nisu kompatibilni sa ovom verzijom instalacije. Riješite problem ili nabavite novu kopiju programa.
InvalidParameter=U komandnoj liniji je proslijeđen neispravan parametar:%n%n%1
SetupAlreadyRunning=Instalacija je već pokrenuta.
WindowsVersionNotSupported=Program ne podržava verziju Windowsa na ovom računaru.
WindowsServicePackRequired=Program zahtijeva %1 Service Pack %2 ili noviji.
NotOnThisPlatform=Program ne radi na %1.
OnlyOnThisPlatform=Program mora biti pokrenut na %1.
OnlyOnTheseArchitectures=Program se može instalirati samo na verzijama Windowsa za sljedeće arhitekture procesora:%n%n%1
WinVersionTooLowError=Program zahtijeva %1 verziju %2 ili noviju.
WinVersionTooHighError=Program se ne može instalirati na %1 verziju %2 ili noviju.
AdminPrivilegesRequired=Za instalaciju ovog programa morate biti prijavljeni kao administrator.
PowerUserPrivilegesRequired=Za instalaciju ovog programa morate biti prijavljeni kao administrator ili član grupe Power Users.
SetupAppRunningError=Instalacija je otkrila da je %1 trenutno pokrenut.%n%nZatvorite sve njegove prozore, pa kliknite OK za nastavak ili Otkaži za izlaz.
UninstallAppRunningError=Deinstalacija je otkrila da je %1 trenutno pokrenut.%n%nZatvorite sve njegove prozore, pa kliknite OK za nastavak ili Otkaži za izlaz.

; *** Pitanja pri pokretanju
PrivilegesRequiredOverrideTitle=Izbor načina instalacije
PrivilegesRequiredOverrideInstruction=Izaberite način instalacije
PrivilegesRequiredOverrideText1=%1 se može instalirati za sve korisnike (potrebna su administratorska prava) ili samo za vas.
PrivilegesRequiredOverrideText2=%1 se može instalirati samo za vas ili za sve korisnike (potrebna su administratorska prava).
PrivilegesRequiredOverrideAllUsers=Instaliraj za &sve korisnike
PrivilegesRequiredOverrideAllUsersRecommended=Instaliraj za &sve korisnike (preporučeno)
PrivilegesRequiredOverrideCurrentUser=Instaliraj samo za &mene
PrivilegesRequiredOverrideCurrentUserRecommended=Instaliraj samo za &mene (preporučeno)

; *** Razne greške
ErrorCreatingDir=Instalacija nije mogla napraviti folder "%1"
ErrorTooManyFilesInDir=Nije moguće napraviti fajl u folderu "%1" jer sadrži previše fajlova

; *** Zajedničke poruke instalacije
ExitSetupTitle=Izlaz iz instalacije
ExitSetupMessage=Instalacija nije završena. Ako sada izađete, program neće biti instaliran.%n%nInstalaciju možete ponovo pokrenuti kasnije.%n%nIzaći iz instalacije?
AboutSetupMenuItem=&O instalaciji...
AboutSetupTitle=O instalaciji
AboutSetupMessage=%1 verzija %2%n%3%n%n%1 početna stranica:%n%4
AboutSetupNote=
TranslatorNote=

; *** Dugmad
ButtonBack=< &Nazad
ButtonNext=&Dalje >
ButtonInstall=&Instaliraj
ButtonOK=OK
ButtonCancel=Otkaži
ButtonYes=&Da
ButtonYesToAll=Da za &sve
ButtonNo=&Ne
ButtonNoToAll=N&e za sve
ButtonFinish=&Završi
ButtonBrowse=&Pregledaj...
ButtonWizardBrowse=P&regledaj...
ButtonNewFolder=&Napravi novi folder

; *** Izbor jezika
SelectLanguageTitle=Izbor jezika instalacije
SelectLanguageLabel=Izaberite jezik koji će se koristiti tokom instalacije.

; *** Zajednički tekst čarobnjaka
ClickNext=Kliknite Dalje za nastavak ili Otkaži za izlaz iz instalacije.
BeveledLabel=
BrowseDialogTitle=Izbor foldera
BrowseDialogLabel=Izaberite folder sa liste ispod, pa kliknite OK.
NewFolderName=Novi folder

; *** Stranica dobrodošlice
WelcomeLabel1=Dobro došli u instalaciju programa [name]
WelcomeLabel2=Na računar će biti instaliran [name/ver].%n%nPreporučuje se da prije nastavka zatvorite sve ostale programe.

; *** Stranica lozinke
WizardPassword=Lozinka
PasswordLabel1=Ova instalacija je zaštićena lozinkom.
PasswordLabel3=Unesite lozinku, pa kliknite Dalje. Lozinka razlikuje velika i mala slova.
PasswordEditLabel=&Lozinka:
IncorrectPassword=Unesena lozinka nije ispravna. Pokušajte ponovo.

; *** Stranica licence
WizardLicense=Licencni ugovor
LicenseLabel=Prije nastavka pročitajte sljedeće važne informacije.
LicenseLabel3=Pročitajte sljedeći licencni ugovor. Prije nastavka instalacije morate prihvatiti njegove uslove.
LicenseAccepted=&Prihvatam ugovor
LicenseNotAccepted=&Ne prihvatam ugovor

; *** Stranice sa informacijama
WizardInfoBefore=Informacija
InfoBeforeLabel=Prije nastavka pročitajte sljedeće važne informacije.
InfoBeforeClickLabel=Kada budete spremni za nastavak instalacije, kliknite Dalje.
WizardInfoAfter=Informacija
InfoAfterLabel=Prije nastavka pročitajte sljedeće važne informacije.
InfoAfterClickLabel=Kada budete spremni za nastavak instalacije, kliknite Dalje.

; *** Podaci o korisniku
WizardUserInfo=Podaci o korisniku
UserInfoDesc=Unesite svoje podatke.
UserInfoName=&Ime korisnika:
UserInfoOrg=&Organizacija:
UserInfoSerial=&Serijski broj:
UserInfoNameRequired=Morate unijeti ime.

; *** Izbor odredišta
WizardSelectDir=Izbor odredišta
SelectDirDesc=Gdje instalirati [name]?
SelectDirLabel3=[name] će biti instaliran u sljedeći folder.
SelectDirBrowseLabel=Za nastavak kliknite Dalje. Ako želite izabrati drugi folder, kliknite Pregledaj.
DiskSpaceGBLabel=Potrebno je najmanje [gb] GB slobodnog prostora na disku.
DiskSpaceMBLabel=Potrebno je najmanje [mb] MB slobodnog prostora na disku.
CannotInstallToNetworkDrive=Instalacija ne može instalirati na mrežni disk.
CannotInstallToUNCPath=Instalacija ne može instalirati na UNC putanju.
InvalidPath=Morate unijeti punu putanju sa slovom diska, na primjer:%n%nC:\APP%n%nili UNC putanju u obliku:%n%n\\server\share
InvalidDrive=Izabrani disk ili UNC dijeljeni folder ne postoji ili nije dostupan. Izaberite drugi.
DiskSpaceWarningTitle=Nema dovoljno prostora na disku
DiskSpaceWarning=Za instalaciju je potrebno najmanje %1 KB slobodnog prostora, a na izabranom disku je dostupno samo %2 KB.%n%nŽelite li ipak nastaviti?
DirNameTooLong=Naziv foldera ili putanja je predugačka.
InvalidDirName=Naziv foldera nije ispravan.
BadDirName32=Naziv foldera ne smije sadržavati nijedan od sljedećih znakova:%n%n%1
DirExistsTitle=Folder postoji
DirExists=Folder:%n%n%1%n%nveć postoji. Želite li ipak instalirati u taj folder?
DirDoesntExistTitle=Folder ne postoji
DirDoesntExist=Folder:%n%n%1%n%nne postoji. Želite li da se napravi?

; *** Izbor komponenti
WizardSelectComponents=Izbor komponenti
SelectComponentsDesc=Koje komponente instalirati?
SelectComponentsLabel2=Označite komponente koje želite instalirati, a uklonite oznaku sa onih koje ne želite. Kada budete spremni, kliknite Dalje.
FullInstallation=Potpuna instalacija
CompactInstallation=Sažeta instalacija
CustomInstallation=Prilagođena instalacija
NoUninstallWarningTitle=Komponente već postoje
NoUninstallWarning=Instalacija je otkrila da su sljedeće komponente već instalirane na računaru:%n%n%1%n%nUklanjanje oznake sa ovih komponenti neće ih deinstalirati.%n%nŽelite li ipak nastaviti?
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceGBLabel=Trenutni izbor zahtijeva najmanje [gb] GB prostora na disku.
ComponentsDiskSpaceMBLabel=Trenutni izbor zahtijeva najmanje [mb] MB prostora na disku.

; *** Dodatni zadaci
WizardSelectTasks=Izbor dodatnih zadataka
SelectTasksDesc=Koje dodatne zadatke izvršiti?
SelectTasksLabel2=Izaberite dodatne zadatke koje instalacija treba izvršiti tokom instaliranja programa [name], pa kliknite Dalje.

; *** Izbor foldera u Start meniju
WizardSelectProgramGroup=Izbor foldera u Start meniju
SelectStartMenuFolderDesc=Gdje postaviti prečice programa?
SelectStartMenuFolderLabel3=Instalacija će napraviti prečice programa u sljedećem folderu Start menija.
SelectStartMenuFolderBrowseLabel=Za nastavak kliknite Dalje. Ako želite izabrati drugi folder, kliknite Pregledaj.
MustEnterGroupName=Morate unijeti naziv foldera.
GroupNameTooLong=Naziv foldera ili putanja je predugačka.
InvalidGroupName=Naziv foldera nije ispravan.
BadGroupName=Naziv foldera ne smije sadržavati nijedan od sljedećih znakova:%n%n%1
NoProgramGroupCheck2=&Ne pravi folder u Start meniju

; *** Spremno za instalaciju
WizardReady=Spremno za instalaciju
ReadyLabel1=Instalacija je spremna da počne instaliranje programa [name] na računar.
ReadyLabel2a=Kliknite Instaliraj za nastavak ili Nazad ako želite pregledati ili promijeniti podešavanja.
ReadyLabel2b=Kliknite Instaliraj za nastavak instalacije.
ReadyMemoUserInfo=Podaci o korisniku:
ReadyMemoDir=Odredište:
ReadyMemoType=Vrsta instalacije:
ReadyMemoComponents=Izabrane komponente:
ReadyMemoGroup=Folder u Start meniju:
ReadyMemoTasks=Dodatni zadaci:

; *** Preuzimanje fajlova
DownloadingLabel2=Preuzimanje fajlova...
ButtonStopDownload=&Zaustavi preuzimanje
StopDownload=Da li sigurno želite zaustaviti preuzimanje?
ErrorDownloadAborted=Preuzimanje je prekinuto
ErrorDownloadFailed=Preuzimanje nije uspjelo: %1 %2
ErrorDownloadSizeFailed=Nije moguće saznati veličinu: %1 %2
ErrorProgress=Neispravan napredak: %1 od %2
ErrorFileSize=Neispravna veličina fajla: očekivano %1, pronađeno %2

; *** Raspakivanje
ExtractingLabel=Raspakivanje fajlova...
ButtonStopExtraction=&Zaustavi raspakivanje
StopExtraction=Da li sigurno želite zaustaviti raspakivanje?
ErrorExtractionAborted=Raspakivanje je prekinuto
ErrorExtractionFailed=Raspakivanje nije uspjelo: %1

; *** Detalji greške pri raspakivanju arhive
ArchiveIncorrectPassword=Lozinka nije ispravna
ArchiveIsCorrupted=Arhiva je oštećena
ArchiveUnsupportedFormat=Format arhive nije podržan

; *** Priprema instalacije
WizardPreparing=Priprema instalacije
PreparingDesc=Instalacija priprema instaliranje programa [name] na računar.
PreviousInstallNotCompleted=Instalacija ili uklanjanje prethodnog programa nije završeno. Da biste to završili, potrebno je ponovo pokrenuti računar.%n%nNakon ponovnog pokretanja računara, ponovo pokrenite instalaciju da završite instaliranje programa [name].
CannotContinue=Instalacija ne može nastaviti. Kliknite Otkaži za izlaz.
ApplicationsFound=Sljedeći programi koriste fajlove koje instalacija treba ažurirati. Preporučuje se da dozvolite instalaciji da automatski zatvori ove programe.
ApplicationsFound2=Sljedeći programi koriste fajlove koje instalacija treba ažurirati. Preporučuje se da dozvolite instalaciji da automatski zatvori ove programe. Nakon završetka instalacije, instalacija će pokušati ponovo pokrenuti programe.
CloseApplications=&Automatski zatvori programe
DontCloseApplications=&Ne zatvaraj programe
ErrorCloseApplications=Instalacija nije mogla automatski zatvoriti sve programe. Prije nastavka preporučuje se da zatvorite sve programe koji koriste fajlove koje instalacija treba ažurirati.
PrepareToInstallNeedsRestart=Instalacija mora ponovo pokrenuti računar. Nakon ponovnog pokretanja, ponovo pokrenite instalaciju da završite instaliranje programa [name].%n%nŽelite li sada ponovo pokrenuti računar?

; *** Instaliranje
WizardInstalling=Instaliranje
InstallingLabel=Sačekajte dok instalacija instalira [name] na računar.

; *** Instalacija završena
FinishedHeadingLabel=Završetak instalacije programa [name]
FinishedLabelNoIcons=Instalacija programa [name] na računar je završena.
FinishedLabel=Instalacija programa [name] na računar je završena. Program možete pokrenuti preko instaliranih prečica.
ClickFinish=Kliknite Završi za izlaz iz instalacije.
FinishedRestartLabel=Da bi se instalacija programa [name] završila, računar mora biti ponovo pokrenut. Želite li ga sada ponovo pokrenuti?
FinishedRestartMessage=Da bi se instalacija programa [name] završila, računar mora biti ponovo pokrenut.%n%nŽelite li ga sada ponovo pokrenuti?
ShowReadmeCheck=Da, želim pogledati fajl README
YesRadio=&Da, ponovo pokreni računar sada
NoRadio=&Ne, ponovo ću pokrenuti računar kasnije
RunEntryExec=Pokreni %1
RunEntryShellExec=Prikaži %1

; *** Potreban sljedeći disk
ChangeDiskTitle=Instalacija treba sljedeći disk
SelectDiskLabel2=Ubacite disk %1 i kliknite OK.%n%nAko se fajlovi sa ovog diska nalaze u drugom folderu od prikazanog, unesite ispravnu putanju ili kliknite Pregledaj.
PathLabel=&Putanja:
FileNotInDir2=Fajl "%1" nije pronađen u "%2". Ubacite ispravan disk ili izaberite drugi folder.
SelectDirectoryLabel=Navedite lokaciju sljedećeg diska.

; *** Poruke tokom instalacije
SetupAborted=Instalacija nije završena.%n%nRiješite problem i ponovo pokrenite instalaciju.
AbortRetryIgnoreSelectAction=Izaberite radnju
AbortRetryIgnoreRetry=&Pokušaj ponovo
AbortRetryIgnoreIgnore=&Zanemari grešku i nastavi
AbortRetryIgnoreCancel=Otkaži instalaciju
RetryCancelSelectAction=Izaberite radnju
RetryCancelRetry=&Pokušaj ponovo
RetryCancelCancel=Otkaži

; *** Statusne poruke instalacije
StatusClosingApplications=Zatvaranje programa...
StatusCreateDirs=Pravljenje foldera...
StatusExtractFiles=Raspakivanje fajlova...
StatusDownloadFiles=Preuzimanje fajlova...
StatusCreateIcons=Pravljenje prečica...
StatusCreateIniEntries=Upisivanje INI podešavanja...
StatusCreateRegistryEntries=Upisivanje u registry...
StatusRegisterFiles=Registrovanje fajlova...
StatusSavingUninstall=Čuvanje podataka za deinstalaciju...
StatusRunProgram=Završavanje instalacije...
StatusRestartingApplications=Ponovno pokretanje programa...
StatusRollback=Poništavanje promjena...

; *** Razne greške
ErrorInternal2=Interna greška: %1
ErrorFunctionFailedNoCode=%1 nije uspjelo
ErrorFunctionFailed=%1 nije uspjelo; kod %2
ErrorFunctionFailedWithMessage=%1 nije uspjelo; kod %2.%n%3
ErrorExecutingProgram=Nije moguće pokrenuti fajl:%n%1

; *** Greške registry-ja
ErrorRegOpenKey=Greška pri otvaranju ključa u registry-ju:%n%1\%2
ErrorRegCreateKey=Greška pri pravljenju ključa u registry-ju:%n%1\%2
ErrorRegWriteKey=Greška pri upisu u ključ registry-ja:%n%1\%2

; *** INI greške
ErrorIniEntry=Greška pri upisu INI podešavanja u fajl "%1".

; *** Greške pri kopiranju fajlova
FileAbortRetryIgnoreSkipNotRecommended=&Preskoči ovaj fajl (nije preporučeno)
FileAbortRetryIgnoreIgnoreNotRecommended=&Zanemari grešku i nastavi (nije preporučeno)
SourceIsCorrupted=Izvorni fajl je oštećen
SourceDoesntExist=Izvorni fajl "%1" ne postoji
SourceVerificationFailed=Provjera izvornog fajla nije uspjela: %1
VerificationSignatureDoesntExist=Fajl potpisa "%1" ne postoji
VerificationSignatureInvalid=Fajl potpisa "%1" nije ispravan
VerificationKeyNotFound=Fajl potpisa "%1" koristi nepoznat ključ
VerificationFileNameIncorrect=Naziv fajla nije ispravan
VerificationFileTagIncorrect=Oznaka fajla nije ispravna
VerificationFileSizeIncorrect=Veličina fajla nije ispravna
VerificationFileHashIncorrect=Heš fajla nije ispravan
ExistingFileReadOnly2=Postojeći fajl nije moguće zamijeniti jer je označen samo za čitanje.
ExistingFileReadOnlyRetry=&Ukloni oznaku samo za čitanje i pokušaj ponovo
ExistingFileReadOnlyKeepExisting=&Zadrži postojeći fajl
ErrorReadingExistingDest=Došlo je do greške pri čitanju postojećeg fajla:
FileExistsSelectAction=Izaberite radnju
FileExists2=Fajl već postoji.
FileExistsOverwriteExisting=&Prepiši postojeći fajl
FileExistsKeepExisting=&Zadrži postojeći fajl
FileExistsOverwriteOrKeepAll=&Uradi isto za sljedeće sukobe
ExistingFileNewerSelectAction=Izaberite radnju
ExistingFileNewer2=Postojeći fajl je noviji od onog koji instalacija pokušava instalirati.
ExistingFileNewerOverwriteExisting=&Prepiši postojeći fajl
ExistingFileNewerKeepExisting=&Zadrži postojeći fajl (preporučeno)
ExistingFileNewerOverwriteOrKeepAll=&Uradi isto za sljedeće sukobe
ErrorChangingAttr=Došlo je do greške pri promjeni atributa postojećeg fajla:
ErrorCreatingTemp=Došlo je do greške pri pravljenju fajla u odredišnom folderu:
ErrorReadingSource=Došlo je do greške pri čitanju izvornog fajla:
ErrorCopying=Došlo je do greške pri kopiranju fajla:
ErrorDownloading=Došlo je do greške pri preuzimanju fajla:
ErrorExtracting=Došlo je do greške pri raspakivanju arhive:
ErrorReplacingExistingFile=Došlo je do greške pri zamjeni postojećeg fajla:
ErrorRestartReplace=RestartReplace nije uspio:
ErrorRenamingTemp=Došlo je do greške pri preimenovanju fajla u odredišnom folderu:
ErrorRegisterServer=Nije moguće registrovati DLL/OCX: %1
ErrorRegSvr32Failed=RegSvr32 nije uspio, izlazni kod %1
ErrorRegisterTypeLib=Nije moguće registrovati biblioteku tipova: %1

; *** Oznake u nazivu za deinstalaciju
UninstallDisplayNameMark=%1 (%2)
UninstallDisplayNameMarks=%1 (%2, %3)
UninstallDisplayNameMark32Bit=32-bitna
UninstallDisplayNameMark64Bit=64-bitna
UninstallDisplayNameMarkAllUsers=Svi korisnici
UninstallDisplayNameMarkCurrentUser=Trenutni korisnik

; *** Greške nakon instalacije
ErrorOpeningReadme=Došlo je do greške pri otvaranju fajla README.
ErrorRestartingComputer=Instalacija nije mogla ponovo pokrenuti računar. Uradite to ručno.

; *** Poruke deinstalacije
UninstallNotFound=Fajl "%1" ne postoji. Deinstalacija nije moguća.
UninstallOpenError=Fajl "%1" nije moguće otvoriti. Deinstalacija nije moguća
UninstallUnsupportedVer=Dnevnik deinstalacije "%1" je u formatu koji ova verzija deinstalacije ne prepoznaje. Deinstalacija nije moguća
UninstallUnknownEntry=U dnevniku deinstalacije pronađen je nepoznat zapis (%1)
ConfirmUninstall=Da li sigurno želite potpuno ukloniti %1 i sve njegove komponente?
UninstallOnlyOnWin64=Ova instalacija se može deinstalirati samo na 64-bitnom Windowsu.
OnlyAdminCanUninstall=Ovu instalaciju može deinstalirati samo korisnik sa administratorskim pravima.
UninstallStatusLabel=Sačekajte dok se %1 uklanja sa računara.
UninstalledAll=%1 je uspješno uklonjen sa računara.
UninstalledMost=Deinstalacija programa %1 je završena.%n%nNeki elementi nisu mogli biti uklonjeni. Možete ih ukloniti ručno.
UninstalledAndNeedsRestart=Da bi se deinstalacija programa %1 završila, računar mora biti ponovo pokrenut.%n%nŽelite li ga sada ponovo pokrenuti?
UninstallDataCorrupted=Fajl "%1" je oštećen. Deinstalacija nije moguća

; *** Poruke tokom deinstalacije
ConfirmDeleteSharedFileTitle=Ukloniti dijeljeni fajl?
ConfirmDeleteSharedFile2=Sistem pokazuje da sljedeći dijeljeni fajl više ne koristi nijedan program. Želite li da ga deinstalacija ukloni?%n%nAko ga neki program ipak koristi, taj program možda neće raditi ispravno. Ako niste sigurni, izaberite Ne. Ostavljanje fajla na sistemu neće napraviti nikakvu štetu.
SharedFileNameLabel=Naziv fajla:
SharedFileLocationLabel=Lokacija:
WizardUninstalling=Status deinstalacije
StatusUninstalling=Deinstaliranje programa %1...

; *** Razlozi blokiranja gašenja računara
ShutdownBlockReasonInstallingApp=Instaliranje programa %1.
ShutdownBlockReasonUninstallingApp=Deinstaliranje programa %1.

[CustomMessages]

NameAndVersion=%1 verzija %2
AdditionalIcons=Dodatne prečice:
CreateDesktopIcon=Napravi prečicu na &radnoj površini
CreateQuickLaunchIcon=Napravi prečicu za &brzo pokretanje
ProgramOnTheWeb=%1 na internetu
UninstallProgram=Deinstaliraj %1
LaunchProgram=Pokreni %1
AssocFileExtension=&Poveži %1 sa ekstenzijom fajla %2
AssocingFileExtension=Povezivanje programa %1 sa ekstenzijom fajla %2...
AutoStartProgramGroupDescription=Pokretanje:
AutoStartProgram=Automatski pokreni %1
AddonHostProgramNotFound=%1 nije pronađen u izabranom folderu.%n%nŽelite li ipak nastaviti?
