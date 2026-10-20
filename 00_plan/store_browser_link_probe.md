# Lokalna proba novog imena native messaging hosta

Razvojni paket `abnps.VideoDownloadNewHostProbe` ima odvojeni identitet od Store programa.
Tri vidljive probne aplikacije koriste `reg.exe` i upisuju vrijednost `ABNPSProbe=visible`
u tri HKCU ključa `NativeMessagingHosts\io.github.abnps.videodownload`. Paket ne piše
manifest za browser i ne mijenja objavljeni program. Registracija i provjera rade se iz
običnog PowerShella, **van paketa**. Ako bilo koji od tri ključa već postoji, stati: mogao
ga je upisati stvarni program ili korisnik i proba ga ne smije pregaziti.

1. Uključiti Windows Developer Mode. [Microsoftov postupak za loose-file registraciju](https://learn.microsoft.com/en-us/windows/apps/develop/testing/loose-file-registration)
   zahtijeva Developer Mode. Iz foldera projekta pripremiti paket i provjeriti da ključeva nema:

   ```powershell
   Set-Location 'C:\Video Downloader\Projekat'
   $hostName = 'io.github.abnps.videodownload'
   $browsers = @('Google\Chrome', 'Microsoft\Edge', 'Mozilla')
   $keys = $browsers | ForEach-Object { "HKCU:\Software\$_\NativeMessagingHosts\$hostName" }
   $keys | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" }
   python tools/prepare_store_registry_probe.py
   ```

   Sva tri rezultata `Test-Path` moraju biti `False`. Skripta piše samo u
   `C:\Video Downloader\Build\store-registry-probe\NewHost`.

2. Registrovati probni paket, pokrenuti svaku od tri aplikacije i provjeriti iz istog
   običnog PowerShella:

   ```powershell
   $probeManifest = 'C:\Video Downloader\Build\store-registry-probe\NewHost\AppxManifest.xml'
   Add-AppxPackage -Register $probeManifest
   $probe = Get-AppxPackage -Name 'abnps.VideoDownloadNewHostProbe'
   $probe | Select-Object Name, PackageFamilyName, PackageFullName
   foreach ($browser in @('Chrome', 'Edge', 'Firefox')) {
     Start-Process "$env:WINDIR\explorer.exe" -ArgumentList "shell:AppsFolder\$($probe.PackageFamilyName)!$browser"
   }
   Start-Sleep -Seconds 3
   $keys | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" }
   $keys | ForEach-Object { Get-ItemProperty -LiteralPath $_ -Name ABNPSProbe -ErrorAction SilentlyContinue }
   ```

   Očekivano: **tri `True`** i u svakom ključu `ABNPSProbe : visible`. Ako
   `Add-AppxPackage` prijavi grešku, zabilježiti kod i `Get-AppxLog`; tada nema potvrde.
   Ako aktivacija zakaže, `Test-Path=False` ne dokazuje kvar virtualizacije.

3. Očistiti samo probni paket i probne ključeve, nakon što je potvrđeno da ih je ova
   proba napravila:

   ```powershell
   if ($probe) { Remove-AppxPackage -Package $probe.PackageFullName }
   $keys | ForEach-Object { Remove-Item -LiteralPath $_ -Recurse -Force -ErrorAction SilentlyContinue }
   $keys | ForEach-Object { "$_ = $(Test-Path -LiteralPath $_)" }
   ```

   Završni rezultat treba biti tri `False`. Ne uklanjati ključeve ako su postojali
   prije probe. Ova proba potvrđuje mehanizam `ExcludedKey` na ovom računaru; ne
   potvrđuje Store certifikaciju, pravi PyInstaller program ni rad poslije Store
   ažuriranja.

Na ovoj mašini je 20.10.2026 `AllowDevelopmentWithoutDevLicense=0`; pokušaj
`Add-AppxPackage -Register` vratio je `0x80073CFF`. Probe nije ostavila paket ni
ključeve: sva tri `Test-Path` nakon pokušaja bila su `False`. Izgrađeni probni
MSIX je prošao `makeappx pack`, ali nema rezultata rada paketa dok Ahmed ne uključi
Developer Mode kroz Windows Settings. Skripta ne mijenja sistemsku postavku.

Za zasebnu probu stvarne aplikacije napraviti svjež build iz ove grane, pa kopirati
MSIX layout pod **drugim paketnim identitetom i drugim aliasom**. Za taj probni
build treba uskladiti i `STORE_HOST_ALIAS` u kodu s probnim aliasom. Ne registrovati
nepotpisani paket pod identitetom već instalirane Store aplikacije. Pokrenuti program
jednom, pa izvan paketa provjeriti da sva tri nova ključa imaju `(Default)` REG_SZ
putanju do odgovarajućeg `.json` manifesta i da manifestov `path` pokazuje na
`%LOCALAPPDATA%\Microsoft\WindowsApps\<probni-alias>`. Zatim provjeriti odgovor
dodatka iz browsera i očistiti samo razvojni paket. Bez ove probe Store ostaje privatan.
