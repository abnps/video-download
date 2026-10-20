# Lokalna proba Store veze s browserom — 20.10.2026

Na Ahmedovom Windowsu 11 (build 26300) Developer Mode je uključen. Sve probe su
registrovane kao **odvojeni razvojni MSIX paketi** pomoću `Add-AppxPackage -Register`.
Nijedna nije mijenjala instaliranu Store aplikaciju. Nakon svake probe uklonjeni su
probni paket i samo HKCU ključevi koje je proba stvorila. Stari ključevi `com.videodl.bridge`
tokom tih proba ostali su prisutni i netaknuti. Microsoftov [postupak za lokalnu registraciju](https://learn.microsoft.com/en-us/windows/apps/develop/testing/loose-file-registration)
zahtijeva Developer Mode.

## Izmjerena razlika pri ponovnoj upotrebi imena

| Ime i postupak | Chrome van paketa | Edge van paketa | Mozilla van paketa |
| --- | --- | --- | --- |
| `io.github.abnps.videodownload`, prvi `reg.exe` paket, tri izuzetka | `True` | `True` | `True` |
| Isto ime poslije uklanjanja paketa i ključeva, isti manifest | `True` | `False` | `False` |
| Svježe `io.github.abnps.videodownload3`, tri izuzetka | `True` | `True` | `True` |
| Svježe `io.github.abnps.videodownload4`, **šest** izuzetaka (tri nova + tri stara) | `True` | `True` | `True` |
| Isto ime `...videodownload4` poslije uklanjanja i ponovne registracije | `True` | `False` | `False` |
| Svježe `io.github.abnps.videodownload5`, PyInstaller kod aplikacije, šest izuzetaka | `True` | `True` | `True` |

U jednoj probi Edge upis je bio vidljiv unutar paketa (`reg query` putem
`Invoke-CommandInDesktopPackage`), ali nije bio vidljiv iz običnog PowerShella.
Svako `True` je potvrđeno i probnom vrijednošću ili `(Default)` putanjom manifesta.
Kombinacija šest izuzetaka **nije** sama uzrok: svježe ime `...4` s njima radi.
Ponovna upotreba iste obrisane putanje na ovom računaru reproducibilno nije radila
za Edge i Firefox. Unutrašnji Windows uzrok nije utvrđen; ne čistiti
AppModel/StateRepository/Helium ručno. Microsoftova [dokumentacija za izuzetke](https://learn.microsoft.com/en-us/windows/msix/desktop/flexible-virtualization)
potvrđuje da su stvarni HKCU ključevi vidljivi van paketa i da mogu ostati nakon
deinstalacije, ali ne objašnjava ovaj slučaj ponovnog upisa.

U probi `...videodownload5` pokrenut je stvarni `videodl.native_messaging.install_native_host`
iz **PyInstaller** izvršnog fajla u posebnom paketu, uz samo probno ime i probni
folder. Izvještaj je pokazao `frozen=true`, `store_package=true`, `alias_exists=true`.
Tri `(Default)` vrijednosti pokazivale su na odgovarajuće Chromium/Firefox JSON
manifeste; u JSON-u je `path` bio probni App Execution Alias. Binary status upit
kroz alias vratio je `{"ok":true,"running":false,"language":"bs"}` bez stderr-a.
Probni paket i ključevi su uklonjeni (`Test-Path=False` za sva tri).

**Završno ime u kodu je `io.github.abnps.videodownload.bridge`.** Na ovom računaru
ono nije korišteno ni brisano u probi (`Test-Path=False` za sva tri browsera).
Ne koristiti ga za probne pakete koji se zatim uklanjaju. Potrebna je zasebna
provjera pune aplikacije i dodatka nakon Store ažuriranja; do tada Store ostaje
privatan. Windows 10 nije ispitan.

## Provjera instalirane Store aplikacije i postojećeg dodatka

Kasnija provjera istog dana našla je vrijednost `probe` u stvarnim HKCU ključevima
za stari host u Chromeu i Firefoxu; Edge je već pokazivao na ispravan manifest.
Oba JSON manifesta za Chrome/Firefox i App Execution Alias su postojali. Sva tri
stara ključa izvezena su u `C:\Video Downloader\Build\store-legacy-key-repair-20261020\`
prije promjene. Samo Chrome i Firefox `(Default)` vrijednosti vraćene su na
odgovarajuće postojeće JSON manifeste; Edge nije promijenjen. To popravlja
zatečene ručne probne vrijednosti, ali nije dokaz da Store 1.0.2 sam piše te
ključeve.

Instalirani alias `abnps-videodl-host.exe` primio je uokvirenu native-messaging
poruku `{"action":"status"}` i odgovorio sa `{"ok":true,"running":false,"language":"bs"}`
bez stderr-a. U odvojenom privremenom Edge profilu učitan je trenutni dodatak iz
`extension/` (ID `jfgcekfmjipklibljeacchccmebppklp`). Poziv njegovog stvarnog
`sendNative({action:"status"})` sa stranice dodatka vratio je isti uspješan odgovor.
Novo ime nije registrovano na ovom računaru, pa je ta proba provjerila povratak
na staro ime i browser → Store alias → host, ne buduću Store verziju s novim imenom.
Privremeni browser procesi su završeni; profili su ostali samo u `Build` folderu.

## Svjež lokalni paket iz ove grane

Iz commita `f532330` napravljen je novi PyInstaller build pune GUI aplikacije i
hosta u `C:\Video Downloader\Build\store-fresh-clean-20261020\`. Bez instalacije
i bez izmjene verzije, `VideoDownload.exe --self-test` vratio je `ok=true` za
verziju 1.0.2. Lokalni MSIX od tog builda je
`msix\VideoDownloadbyabnps-1.0.2.0-x64.msix` (161,9 MB; SHA-256 počinje sa
`38657b5c563e025c8c685e71`). U paketu su oba izvršna fajla, neizmijenjen
trenutni dodatak i svih šest `ExcludedKey` putanja. To je **samo lokalni probni
artefakt**, nije potpisan, instaliran ni poslan u Partner Center.

Prvi pokušaj builda pokupio je `icuuc.dll` i `ucrtbase.dll` iz Codexovog
`PATH`-a (`poppler`/`libheif`), pa je QtCore pao pri uvozu. Čisti build je
izostavio Codexove runtime putanje iz `PATH`-a i eksplicitno koristio već
pripremljeni `ffmpeg` iz susjednog `Build\ffmpeg` foldera; tada je self-test
prošao. Ne koristiti neuspjeli `Build\store-fresh-package-20261020` kao izvor
paketa. Izvorni kod nije mijenjan zbog ove lokalne build konfiguracije.

Ažuriranje postojećeg Store paketa s novim imenom i Windows 10 još nisu
provjereni. Produkcijsko novo ime i dalje nema HKCU ključ; ne koristiti ga u
probnom paketu koji se poslije briše.

## Granica podrške za Store

Ahmed nema Windows 10 za probu. Store MSIX od ove grane zato koristi
`TargetDeviceFamily MinVersion="10.0.22000.0"` (Windows 11), dok se registracija
hosta na Windowsu 10 zasebno ne potvrdi. Ovo mijenja samo Store paket; obični
Windows instaler nije mijenjan. Lokalni MSIX opisan iznad napravljen je **prije**
ove promjene minimalne verzije i nije kandidat za objavu.

Novi lokalni paket je `C:\Video Downloader\Build\store-win11-candidate-20261020\`
`VideoDownloadbyabnps-1.0.2.0-x64.msix` (SHA-256
`af2ba0d773bf2beeeb1e0bff8a1591caf6324195796b708eaee33a126a2f7892`).
`makeappx` ga je prihvatio; provjereni manifest sadrži `MinVersion=10.0.22000.0`,
šest HKCU izuzetaka i oba izvršna fajla. Ciljani `tests.test_browser_bridge`
prošao je svih 27 testova izvan mrežno ograničenog sandboxa, jer testovi koriste
lokalni `127.0.0.1` socket. Paket zadržava verziju 1.0.2.0 i **nije instaliran,
potpisan niti poslan u Partner Center**. Stvarno Store ažuriranje će tražiti višu
verziju i zasebnu potvrdu prije javne objave.

## Izolovana proba pune aplikacije u Windows Sandboxu (20.10.2026)

Na Windows Sandboxu 11, build 26100, originalni raspakovani MSIX nije mogao biti
registrovan bez Developer Modea (`0x80073CFF`). Originalni nepotpisani MSIX sa
`-AllowUnsigned` nije mogao biti instaliran jer Store identitet nema posebni OID za
nepotpisane pakete (`0x80073D2C`). To su očekivana pravila Windowsa, a sistemska
politika nije mijenjana.

Zato je samo u `Build\store-sandbox-probe-20261020` napravljena zasebna kopija
istih binarnih fajlova i manifesta, uz Microsoftov OID za nepotpisane testne
pakete u polju Publisher. Verzija i kod aplikacije nisu promijenjeni. Ta kopija
je pokrenuta u Sandboxu bez mreže, s izvornim paketom mapiranim samo za čitanje.
Rezultati su u `Build\store-sandbox-probe-20261020\results\`:

- `special-unsigned.json`: aplikacija se registrovala i pokrenula; novo ime
  hosta vidljivo je u sva tri stvarna HKCU ključa izvan paketa.
- `verified.json`: Chrome, Edge i Firefox imaju ispravne podrazumijevane
  vrijednosti, postojeće JSON manifeste i putanju na isti App Execution Alias.
- `node-status.json`: uokvireni native-messaging upit kroz alias vratio je
  `{"ok":true,"running":true,"language":"bs"}`.

Prvobitni PowerShell izvještaj `special-unsigned.json` pogrešno je očitao
podrazumijevane vrijednosti kao `null`; zasebna provjera preko .NET Registry API-ja
u `registry.json` i `verified.json` potvrdila je njihove tačne putanje. PowerShell
varijanta slanja binarnog zahtjeva dala je loš okvir; Node je poslao ispravan
uokvireni zahtjev i dobio odgovor.

Sandbox je zaustavljen nakon probe. Produkcijski HKCU ključevi na Ahmedovom
Windowsu nisu dirani. Ovaj test potvrđuje tok pune aplikacije na čistom Windowsu
11, ali **ne zamjenjuje** privatno ažuriranje stvarnog Store-potpisanog paketa s
originalnim Publisher identitetom, provjeru dodatka u stvarnom browseru ni Store
certifikaciju. Testni paket s drugim Publisher identitetom nikad ne slati u Store.

## Provjera poslije privatnog Store ažuriranja

`tools/check_store_browser_link.py` ništa ne upisuje. Iz običnog PowerShella,
izvan paketa, prvo pokrenuti Store aplikaciju jednom, pa:

```powershell
Set-Location 'C:\Video Downloader\Projekat'
python tools/check_store_browser_link.py
```

Prolaz znači: instalirana Store verzija najmanje 1.0.3.0, za Chrome/Edge/Firefox
stvarni HKCU ključevi novog imena pokazuju na očekivane JSON manifeste, njihovi
ID-jevi dodatka su tačni, a App Execution Alias odgovara na uokvireni `status`
upit. Nakon toga učitati trenutni `extension/` u Edge/Chrome i potvrditi status
iz samog dodatka. Provjeriti i da Store ažuriranje poslije ponovnog pokretanja
ostavlja istu vezu. Tek tada razmatrati javnu objavu.

Na trenutno instaliranoj Store 1.0.2.0 `--legacy` prolazi sve stavke. Osnovni
poziv očekivano vraća `NIJE SPREMNO`: verzija je 1.0.2.0 i tri HKCU ključa novog
imena ne postoje. Provjera je rađena 20.10.2026; finalno ime je i dalje netaknuto.

## Ako treba ponoviti osnovni mehanizam

`tools/prepare_store_registry_probe.py` sada namjerno koristi samo **jednokratno
probno ime** `io.github.abnps.registryprobe`, nikad produkcijsko ime. I tu probu
treba tumačiti kao prvi pokušaj; poslije brisanja ključeva istu putanju ne koristiti
za zaključak o čistoj instalaciji.

```powershell
Set-Location 'C:\Video Downloader\Projekat'
$name = 'io.github.abnps.registryprobe'
$keys = @('Google\Chrome','Microsoft\Edge','Mozilla') |
  ForEach-Object { "HKCU:\Software\$_\NativeMessagingHosts\$name" }
$keys | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" } # tri False
python tools/prepare_store_registry_probe.py
Add-AppxPackage -Register 'C:\Video Downloader\Build\store-registry-probe\DisposableHost\AppxManifest.xml'
$probe = Get-AppxPackage -Name 'abnps.VideoDownloadDisposableHostProbe'
foreach ($app in @('Chrome','Edge','Firefox')) {
  Start-Process "$env:WINDIR\explorer.exe" -ArgumentList "shell:AppsFolder\$($probe.PackageFamilyName)!$app"
}
Start-Sleep -Seconds 4
$keys | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" } # očekivano tri True
$keys | ForEach-Object { Get-ItemProperty -LiteralPath $_ -Name ABNPSProbe }
```

Po završetku ukloniti samo paket `abnps.VideoDownloadDisposableHostProbe` i
ključeve koji prije probe nisu postojali i imaju `ABNPSProbe=visible`:

```powershell
Remove-AppxPackage -Package $probe.PackageFullName
$keys | ForEach-Object {
  if ((Get-ItemProperty -LiteralPath $_ -Name ABNPSProbe).ABNPSProbe -eq 'visible') {
    Remove-Item -LiteralPath $_ -Force
  }
}
$keys | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" } # tri False
```
