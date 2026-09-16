# Video Download — plan projekta

Pokrenuto: 16.9.2026.

## Cilj

Lična Windows desktop aplikacija za preuzimanje videa i zvuka sa YouTube-a i
drugih sajtova koje podržava yt-dlp. Samo za ličnu upotrebu.

## Odluke (16.9.2026, Ahmed)

- Interfejs: desktop GUI, Python + PySide6 (isti stack kao Kadar).
- Prva verzija: izbor kvaliteta/formata, samo zvuk (MP3/M4A), plejliste i red čekanja.
- Git: lokalni repo + privatni GitHub repo.
- Titlovi i thumbnail: nisu u prvoj verziji.

## Odluke (16.9.2026, Ahmed) — preuzimanje iz browsera

- Aplikacija preuzima svaki video pokrenut u browseru ili zadat URL-om (osim DRM).
- Edge/Chrome ekstenzija; kad aplikacija nije pokrenuta, klik je automatski pokreće
  (registracija samo za trenutnog korisnika, HKCU).
- Video iza prijave: Ahmed je odobrio slanje kolačića samo za taj sajt, bez čuvanja.
  Automatski sigurnosni filter Claude Code-a blokirao je ekstenziju sa pristupom
  kolačićima, pa ovaj dio čeka Ahmedovu izričitu potvrdu (vidi Faza 2).

## Zahtjev (Ahmed) — X, TikTok, YouTube i svi ostali

- „Preuzmi video koji se pušta": ekstenzija nalazi video koji se pušta i link
  njegove objave (feed na X/TikTok/Instagram/Facebook), yt-dlp preuzima objavu.
- yt-dlp sa `curl-cffi` (predstavljanje kao browser). X javne objave rade bez
  prijave (provjereno: HLS 720p). TikTok stari primjeri iz yt-dlp testova vraćaju
  „IP blocked" za ovu mrežu; aktuelni TikTok nije moguće automatski provjeriti jer
  TikTok i X automatizovanom Edge-u daju captcha/403 → potrebna Ahmedova ručna provjera.
- Video iza prijave (privatni nalozi, neki TikTok/X/Instagram) i dalje čeka odluku o kolačićima.

## Odluka (16.9.2026, Ahmed) — izgled

- GUI po uzoru na DVDVideoSoft „Free YouTube to MP3 Converter": svijetao prozor,
  meni, traka zeleno „Zalijepi" / izbor formata / plavo „Preuzmi", prazan ekran
  „Prevuci link ovdje", redovi sa sličicom, trajanjem, linkom formata i dugmadima.
  Preuzet je izgled i raspored, ne njihovo ime, logo ni grafika.
- Ponašanje kao u uzoru: zalijepljeni linkovi čekaju na „Preuzmi"; klik u browseru
  i dugme u redu odmah preuzimaju samo taj video.

## Van obima

- Zaobilaženje DRM-a, plaćeni/zaštićeni sadržaj bez pristupa, piratski izvori.
- Javna distribucija ili prodaja bez prethodne pravne provjere uslova platformi.

## Faza 1 — MVP (u toku)

Sadržaj: unos jednog ili više linkova, plejlista/kanal se razvija u stavke reda,
formati MP4 (najbolji / 1080p / 720p / 480p) i MP3/M4A, ukupan napredak
(video + zvuk), zaustavljanje sa čišćenjem privremenih fajlova, ponavljanje
neuspjelih stavki, izbor foldera, pamćenje podešavanja.

Browser integracija: Edge/Chrome ekstenzija prepoznaje tokove (MP4/WebM, HLS,
DASH) i DRM, šalje stranicu ili izabrani tok aplikaciji preko native messaging
hosta (dozvoljen samo ID naše ekstenzije) i lokalnog mosta sa tokenom; prosljeđuje
Referer i User-Agent; pokreće aplikaciju ako nije pokrenuta.

Exit gate:
- [x] Automatski testovi prolaze (logika, red, GUI offscreen) — 33 testa, 16.9.2026.
- [x] Browser dio: 52 Python + 7 JS testova; E2E u pravom Edge-u
      (`node tools/e2e_browser/run.mjs`, 16.9.2026): tokovi prepoznati, klik je
      pokrenuo ugašenu aplikaciju, HLS koji traži Referer preuzet (0 odgovora 403),
      stranica preuzeta preko yt-dlp-a, DRM stranica označena; fajlovi H.264 + AAC.
- [x] Živi test na pravom linku (16.9.2026, „Me at the zoo", jNQXAC9IVRw):
      MP4 najbolji = H.264 + AAC, 19 s (ffprobe); ponovno pokretanje prepoznaje
      postojeći fajl; MP3 192 kbps; plejlista i kanal (@jawed) se čitaju;
      prekid usred preuzimanja i tokom drugog dijela (zvuk) reaguje odmah i ne
      ostavlja nijedan fajl. Napredak je monoton za video + zvuk.
- [ ] Ahmed pokrenuo `pokreni.bat` i potvrdio da prozor i preuzimanje rade.
- [x] E2E „video koji se pušta" u feedu (lokalna stranica nalik X-u): uzeta
      objava videa koji se pušta, ne link taba ni prvi video.
- [ ] Ahmed učitao ekstenziju u svoj Edge/Chrome i preuzeo video sa YouTube-a, X-a i TikToka.

Poznato ograničenje: prekid dok yt-dlp još čita informacije o videu (prije prvog
bajta, na YouTube-u ponekad 10+ s) djeluje tek kad preuzimanje krene.

## Faza 2 — Dorada

- Titlovi i thumbnail (opciono uz video).
- Lijepljenje linka iz clipboarda jednim klikom.
- Provjera/ažuriranje yt-dlp-a iz aplikacije (YouTube se često mijenja).
- Opcija „cijela plejlista" za linkove videa unutar liste (sada se preuzima samo video).
- Brži prekid u fazi čitanja informacija (prije početka preuzimanja).
- Video iza prijave: kolačići samo za sajt sa kog se preuzima, samo za to preuzimanje
  (privremeni cookies fajl za yt-dlp, briše se odmah). Ahmed je odobrio 16.9.2026,
  ali čeka izričitu potvrdu zbog sigurnosnog filtera; prijedlog je da ekstenzija
  pristup kolačićima traži tek na prvi takav klik (dijalog browsera).

## Faza 3 — Pakovanje

- PyInstaller `.exe` + bundlovan ffmpeg (vault: „PyInstaller - bundlovanje
  eksternog CLI alata (ffmpeg) uz Python app").
- JS runtime u paketu (Deno `.exe`) ili jasna provjera pri pokretanju.
- Ikona aplikacije.

Exit gate: `.exe` radi na čistom Windowsu bez instaliranog Pythona.
