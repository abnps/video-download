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

Puni svjež build GUI aplikacije, ažuriranje postojećeg Store paketa i Windows 10
još nisu provjereni. Produkcijsko novo ime i dalje nema HKCU ključ; ne koristiti
ga u probnom paketu koji se poslije briše.

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
