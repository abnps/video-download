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

## Odluke (17.9.2026, Ahmed) — instaler, jezici, auto update

- Instaler i aplikacija na 5 jezika: bosanski/srpski, engleski, njemački, španski, francuski.
- ~~Javni repo izdanja~~ → 17.9.2026 Ahmed: aplikacija ostaje lična (bez sajta/prodaje/javne
  distribucije). Izdanja u privatnom repou `npgamy/video-download`, ažuriranje preko `gh` prijave.
- Auto update: tiho pri pokretanju (najviše jednom dnevno) + Pomoć → Provjeri ažuriranje;
  instalira tek poslije pitanja i SHA-256 provjere.

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
      17.9.2026: X potvrđen; TikTok potvrđen preko „Preuzmi video koji se pušta"
      (dodatak v0.3.2). YouTube preko dodatka još nije potvrđen.

Prekid dok yt-dlp još čita informacije o videu (prije prvog bajta, na YouTube-u ponekad
10+ s): od v0.5.6 stavka odmah dobija stanje „prekinuto", a posao se napušta (nijedan
fajl još ne postoji). Sama nit se gasi kad čitanje završi; njen zakašnjeli odgovor se ne koristi.

## Faza 2 — Dorada

- Titlovi i thumbnail (opciono uz video).
- Lijepljenje linka iz clipboarda jednim klikom.
- [x] Desni klik u browseru (17.9.2026, dodatak v0.4.5): stavke „Preuzmi ovaj link / ovaj video /
  video koji se pušta". Direktan tok ide odmah, blob/MSE traži objavu. Kolačići samo ako je dozvola
  već data (meni je ne može tražiti). E2E provjerava da stavke postoje; pravi desni klik čeka Ahmeda.
- [x] Ažuriranje yt-dlp-a iz aplikacije (17.9.2026, v0.5.4): Pomoć → „Ažuriraj čitač sajtova",
  plus tiha provjera jednom dnevno. Wheel sa PyPI-ja, SHA-256, raspakivanje u folder podataka
  korisnika; `activate()` ga pri pokretanju stavlja ispred verzije iz instalacije, a pokvaren
  paket se briše i ostaje onaj iz paketa. Živa provjera na PyPI-ju prošla.
- Opcija „cijela plejlista" za linkove videa unutar liste (sada se preuzima samo video).
- [x] Više istovremenih preuzimanja (17.9.2026, v0.5.7): Preuzimanja → „Istovremenih preuzimanja"
  (1–4, podrazumijevano 2); izbor se pamti. Prekid i zatvaranje rade nad svim poslovima u toku.
- [x] Automatsko ponavljanje kad veza pukne (17.9.2026, v0.5.7): yt-dlp sam ponavlja i nastavlja
  `.part`, a aplikacija stavku vraća u red do 3 puta (5 s pauze). DRM, LIVE, 404 i nepodržan
  sajt se ne ponavljaju. „Zaustavi" poništava zakazano ponavljanje.
- [x] Brži prekid u fazi čitanja informacija (17.9.2026, v0.5.6): „Zaustavi" radi i dok se
  čitaju linkovi (ProbeJob.cancel), a preuzimanje koje još nije počelo se napušta odmah.
- [x] Video iza prijave (17.9.2026, Ahmed izričito potvrdio „Kolačići prijave"):
  opciona dozvola `cookies` kroz dijalog browsera, samo kolačići tog sajta, privremeni
  fajl za yt-dlp se briše odmah. E2E: stranica iza prijave preuzeta, 0× 403.
  17.9.2026 Ahmed potvrdio: Instagram radi (dodatak v0.4.1, poslije popravke linka
  muzike /reels/audio/).

## Faza 3 — Pakovanje (u toku od 17.9.2026)

- [x] Aplikacija i popup na 5 jezika, promjena jezika uživo; testovi provjeravaju sve prevode.
- [x] Auto update (provjera, SHA-256, tiha instalacija) — unit testovi.
- [x] Instaler napravljen, self-test spakovane aplikacije prošao (v0.5.1, 17.9.2026).
- [x] Instalacija/deinstalacija i tiho ažuriranje 0.5.0 → 0.5.1 provjereni lokalno (instaler
      čeka gašenje aplikacije preko mutexa i ponovo je pokreće).
- [x] Izdanje v0.5.1 u privatnom repou `npgamy/video-download` (17.9.2026); aplikacija ga
      čita preko `gh`. v0.5.0 označeno „NE KORISTITI" (u gh načinu pokušavala HTTP → 404).
- [x] v0.5.2 (17.9.2026): u 0.5.1 je prekinut build ostavio 5 malih fajlova punih nula (ikonice i
      DRM skripte dodatka, strelica menija); build sada poredi paket sa izvorom prije instalera.
      Slanje na GitHub jednom palo sa HTTP 500, drugi pokušaj prošao.
- [x] v0.5.3 (17.9.2026): prenos uživo (LIVE) se ne preuzima — dodatak (v0.4.4) ga ne šalje
      (video bez kraja, `duration = Infinity`), probe ga odbija, `match_filter` ga zaustavlja i
      prije preuzimanja, a stavke uživo u plejlisti/kanalu se preskaču. Testovi 82 + 10, E2E
      sa MediaSource „live" stranicom u Edge-u: dodatak odbio, nijedan fajl.
- [ ] Ahmed potvrdio ažuriranje preko `gh` sa objavljene verzije (0.5.2 → 0.5.3) i LIVE na pravom sajtu.
- [ ] Ažuriranje preko `gh` sa stvarnog izdanja na sljedeće provjereno uživo.

Prvobitne stavke:

- PyInstaller `.exe` + bundlovan ffmpeg (vault: „PyInstaller - bundlovanje
  eksternog CLI alata (ffmpeg) uz Python app").
- JS runtime u paketu (Deno `.exe`) ili jasna provjera pri pokretanju.
- Ikona aplikacije.

Exit gate: `.exe` radi na čistom Windowsu bez instaliranog Pythona.
