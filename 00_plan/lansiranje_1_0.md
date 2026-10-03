# Lansiranje 1.0: plan i tekstovi za kataloge (plan 1.0, tačke 8 i 13)

Pripremljeno 3.10.2026. Ništa odavde nije objavljeno; svaka objava ide tek na Ahmedovo „objavi".
Važi pravilo „ništa plaćeno do zarade" (AGENTS.md) i „bez imena platformi u reklami".

## 1. Šta znači 1.0

- Računar **1.0.0**, Android **1.0.0** (versionCode +1), dodatak **1.0.0**: isti dan, jedno izdanje na GitHubu.
- Mac i Android ostaju označeni „beta" na sajtu dok nemaju Appleov potpis, odnosno punu Google provjeru
  (dogovor: plaćeno tek uz zaradu). 1.0 se odnosi na program, ne na potpise.
- Na sajtu kratka stranica „Video Download 1.0": `tools/site_release.py` (`version-1.html`, 5 jezika). Spremna je i
  uključuje se SAMA kad `__version__` postane 1.0.0 (stranica, sitemap, link na vrhu „Šta je novo"); do tada se sajt ne mijenja.

## 2. Redoslijed (svaki korak čeka Ahmedovo „objavi")

1. **Računar 0.9.8** (roditeljska zaštita, povratna informacija, manji instaler, Mac samostalno ažuriranje).
   Pri objavi promijeniti tekst na sajtu „on Mac (beta) new versions are downloaded by hand for now"
   (`tools/site_home.py`, svih 5 jezika): od 0.9.8 se i Mac ažurira sam. Ne ranije, jer bi sajt tvrdio nešto
   što objavljena verzija još ne radi. Korak 4b iz README-a (`tools/sign_macos.py`) je novi i obavezan.
2. **Android 0.2.4** (One UI izgled, widget, pločica, 4K/AV1, prijave TikTok/X, roditeljska zaštita, titlovi,
   isječak, neuspjela preuzimanja na listi). Prije toga Ahmedova proba na telefonu.
3. Sedmica-dvije praćenja grešaka (izvještaji, provjera sajtova svako jutro).
4. **1.0.0** svuda, stranica „1.0" na sajtu, pa prijave u kataloge (tačka 4 ispod).

## 3. Katalozi: šta može, a šta ne

Licenca programa je naša (licencni ugovor na 5 jezika, Android odluka B, 27.9.2026), a nije otvoren kod.
Zato otpadaju katalozi koji primaju samo otvoren kod:

| Katalog | Može? | Napomena |
|---|---|---|
| winget | da | PR #445943 prošao automatske provjere, čeka moderatora |
| AlternativeTo | da | besplatan nalog; unos programa + snimci ekrana |
| Softpedia | da | obrazac „Submit program", besplatno |
| Uptodown (Windows i Android) | da | besplatan nalog programera; APK se šalje ručno |
| Firefox AMO | da | ZIP 0.5.3 spreman, šalje Ahmed |
| Edge Add-ons | da, uz rizik | besplatno; pravila o preuzimanju videa mogu odbiti dodatak |
| Chrome Web Store | **ne sada** | jednokratno 5 $ (plaćeno) i pravila zabranjuju preuzimanje s YouTube-a |
| IzzyOnDroid, F-Droid | **ne** | primaju samo otvoren kod (FOSS licenca) |
| Google Play | **ne** | pravila o preuzimanju videa; pun nalog postoji samo radi provjere programera |

Naloge otvara i obrasce šalje Ahmed (agent ne pravi naloge). Kontakt u svim obrascima: `abnpsdev@gmail.com`.

## 4. Tekstovi za kataloge

### Kratki opis (do 80 znakova)

- EN: Free video and audio downloader for Windows, Mac and Android. No ads, no tracking.
- BS: Besplatno preuzimanje videa i zvuka za Windows, Mac i Android. Bez reklama i praćenja.
- DE: Kostenloser Video- und Audio-Downloader für Windows, Mac und Android. Ohne Werbung.

### Dugi opis (EN)

Video Download saves videos as MP4 (up to the best quality the site offers) or audio as MP3/M4A from over
1800 websites. Copy a link and the app picks it up, or send the video that is playing straight from your
browser with the extension.

- MP4 in best, 1080p, 720p or 480p; audio only as MP3 or M4A
- Whole playlists, up to 4 downloads at once, automatic retry
- Clips (just a part of a video), subtitles, cover art
- Light and dark theme, 5 languages (English, Bosnian, German, Spanish, French)
- Updates itself; on Windows and Mac only updates digitally signed by us are installed
- No account, no daily limit, no ads, no tracking: your links never reach us
- Android app: share a link from any app, download in the background, widget and quick settings tile

The app is meant for your own videos, content you have the author's permission for, and content under a
free license. DRM-protected content is not downloaded.

### Dugi opis (BS)

Video Download čuva video kao MP4 (do najboljeg kvaliteta koji sajt nudi) ili zvuk kao MP3/M4A sa više od
1800 sajtova. Kopiraj link i program ga sam preuzme, ili pošalji video koji se upravo pušta direktno iz
browsera, preko dodatka.

- MP4 u najboljem kvalitetu, 1080p, 720p ili 480p; samo zvuk kao MP3 ili M4A
- Cijele liste, do 4 preuzimanja istovremeno, automatski novi pokušaj
- Isječci, titlovi, slika videa kao omot
- Svijetla i tamna tema, 5 jezika
- Sam se ažurira; na Windowsu i Macu instalira samo ažuriranja s našim digitalnim potpisom
- Bez naloga, bez dnevnog ograničenja, bez reklama i praćenja: tvoji linkovi nikad ne stižu do nas
- Android: podijeli link iz bilo koje aplikacije, preuzimanje u pozadini, widget i pločica u Brzim podešavanjima

Program je namijenjen tvojim videima, sadržaju za koji imaš dozvolu autora i sadržaju pod slobodnom licencom.
Sadržaj zaštićen DRM-om se ne preuzima.

### Podaci za obrasce

- Ime: Video Download · Autor/izdavač: abnps · Licenca: besplatno (freeware), vlastiti licencni ugovor
- Sajt: https://abnps.github.io/video-download/
- Windows: https://github.com/abnps/video-download/releases/latest/download/VideoDownload-Setup.exe
  (stalni link za katalog koji traži nepromjenljiv fajl: repo `abnps/video-download-installers`)
- Mac (beta, Apple Silicon): https://github.com/abnps/video-download/releases/latest/download/VideoDownload-macOS-arm64.dmg
- Android (beta): https://github.com/abnps/video-download/releases/latest/download/VideoDownload-android.apk
- Kategorija: Multimedia → Video tools / Downloaders · Oznake: video downloader, mp3, mp4, playlist, yt-dlp
- Snimci ekrana: sajt ih već ima (`site/assets/screenshot-*`); za Android napraviti 3–4 nova kad 0.2.4 izađe.

### Objava na Redditu (EN, bez imena platformi u naslovu)

> **I made a free, ad-free video/audio downloader for Windows, Mac and Android**
> No account, no tracking, no daily limit. MP4 up to best quality or MP3, playlists, clips, subtitles, and
> a browser extension that sends the playing video to the app. It updates itself and only installs updates
> signed by me. Feedback welcome: abnpsdev@gmail.com · https://abnps.github.io/video-download/

Prije objave pročitati pravila svakog subreddita (mnogi zabranjuju samopromociju ili alate za preuzimanje).
