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
- 22.9.2026 Ahmed: repo `npgamy/video-download` je PREBAČEN U JAVNI, sa svim izdanjima
  (izabrao „Javno sa svim izdanjima" uz objašnjene posljedice: javna distribucija instalera,
  GPL obaveza za ffmpeg, lično ime u dokumentaciji, nepovratnost). Sajt i prodaja i dalje nisu u obimu.
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
- [x] Ahmed potvrdio da prozor i preuzimanje rade (instalirana verzija umjesto `pokreni.bat`; 24.9.2026 Ahmed potvrdio na v0.7.2: „Sve radi trenutno“ (provjera 1–8)).
- [x] E2E „video koji se pušta" u feedu (lokalna stranica nalik X-u): uzeta
      objava videa koji se pušta, ne link taba ni prvi video.
- [x] Ahmed učitao ekstenziju u svoj Edge/Chrome i preuzeo video sa YouTube-a, X-a i TikToka.
      24.9.2026 Ahmed potvrdio na v0.7.2: „Sve radi trenutno“ (provjera 1–8): YouTube preko dodatka (MP4 i MP3) potvrđen.
      17.9.2026: X potvrđen; TikTok potvrđen preko „Preuzmi video koji se pušta"
      (dodatak v0.3.2); YouTube tada još nije bio potvrđen.

Prekid dok yt-dlp još čita informacije o videu (prije prvog bajta, na YouTube-u ponekad
10+ s): od v0.5.6 stavka odmah dobija stanje „prekinuto", a posao se napušta (nijedan
fajl još ne postoji). Sama nit se gasi kad čitanje završi; njen zakašnjeli odgovor se ne koristi.

## Faza 2 — Dorada

- [x] Stabilizacija, Paket 1 (26.9.2026, v0.9.4; iz pregleda Codex-a, sve tvrdnje provjerene u kodu):
  isti link poslije „Zaustavi"; yt-dlp čuva aktivnu i posljednju ispravnu verziju; otporna istorija i
  red (loše polje ne ruši, oštećen fajl se čuva kao `.ostecen`, neuspio upis se javlja); deinstalacija
  briše Firefox ključ (test poredi s registracijom); limit brzine kao zajednički budžet; README/AGENTS
  i SmartScreen tekst usklađeni sa stvarnim ponašanjem. Netačno u pregledu: Mutagen (nije u paketu) i
  „Free/Pro" (odluka je besplatno + prilozi).
- [ ] Paket 2: odvojena imena za 720p/1080p, jedinstvena privremena imena i prekid konverzije bez
  izlaza ffmpeg-a, provjera gotovog fajla prije „Završeno", zatvaranje bez zamrzavanja.
- [ ] Paket 3: GitHub Actions pokreće testove prije objave, zaključane verzije alata, potpisan opis izdanja.
- [ ] Nova adresa (25.9.2026, v0.9.1): repo prelazi u organizaciju `abnps` (Ahmed je napravio organizaciju;
  prebacivanje repoa radi Ahmed u GitHub postavkama), sajt `abnps.github.io/video-download`.
- [x] Udobnost (25.9.2026, v0.9.0; Ahmed: „23456", bez stavke 1 „Završeno · MB za s"):
  2) obavještenje u Windowsu kad se cijela grupa završi (samo ako prozor nije u fokusu, ne poslije
  ručnog „Zaustavi"; isključivo u meniju); 3) istorija: pretraga (sve riječi, naslov/link/ime fajla)
  i filter video/zvuk/obrisani; 4) Preuzimanja → Ime fajla (Naslov [id], Samo naslov, Izvođač -
  Naslov, Kanal - Naslov, Datum Naslov; bez [id] dva videa istog naslova dijele ime); 5) Pomoć →
  Tema: svijetla/tamna/kao Windows (`videodl/theme.py`, tamna naslovna traka); 6) napredak na
  dugmetu u traci zadataka (ITaskbarList3 preko ctypes-a, `videodl/winshell.py`, provjereno na
  pravom Windowsu). Testovi: `tests/test_comfort.py`.
- [x] Animirana traka napretka (25.9.2026, v0.8.0, Ahmedov izbor „varijanta 4" iz 4 prikazane):
  klizi do novog procenta, sjaj prelazi preko popunjenog dijela, plavo = video, ljubičasto = zvuk
  (i MP4→MP3), bez procenta (priprema, ffmpeg) klizi lijevo-desno, na kraju zeleno + kratak puls pa
  nestaje. Tajmer radi samo dok je traka vidljiva (`AnimatedProgress` u `videodl/widgets.py`,
  `tests/test_progress_bar.py`).
- [x] Link koji nije video ni audio (24.9.2026, v0.7.8): `.exe`, `.zip`, `.pdf`… se odbijaju bez čitanja;
  fajl koji yt-dlp samo „nagađa" kao video (`direct`, bez formata) prolazi samo s video/audio
  ekstenzijom; „Unsupported URL" dobija jasnu poruku. Iz clipboarda: bez kartice, samo napomena u
  statusnoj traci; zalijepljen ručno: crveni red s jasnom porukom. Isto i pri „Pokušaj ponovo"
  (`match_filter`). Direktni `.mp3`/`.mp4` linkovi rade (`tests/test_not_media.py`).
  v0.7.9 (Ahmed: „Kartica je i dalje tu" poslije „Zalijepi"): takav link NIKAD ne pravi karticu
  (ni „Zalijepi", ni browser) — samo napomena u statusnoj traci; stara kartica za `.exe` se ne vraća.
- [x] Podrži projekat (24.9.2026, v0.7.5; v0.7.6: PayPal stranica za prilog — Donate dugme nije dostupno u Srbiji): link u statusnoj traci i Pomoć meniju; traka poslije
  svakih 10 novih preuzimanja, prozor najviše jednom sedmično kad ništa ne radi; „Već sam podržao" (bez
  provjere uplate) gasi sve na 90 dana. Ništa se ne otključava ni blokira (`videodl/support.py`).
  v0.7.7: u prozoru i README-u i QR kod (`videodl/assets/support-qr.png`) pored dugmeta; test
  dekodira QR i provjerava da vodi na isti `SUPPORT_URL`.
- [x] Pravni paket (24.9.2026, v0.7.4): licencni ugovor, uslovi i privatnost na 5 jezika u instaleru
  (stranica za prihvatanje + privatnost prije nje) i u Pomoć → Ugovori i licence; puni tekstovi
  licenci komponenti u folderu `licenses`. Tekstovi su nacrt za pregled kod advokata.
- [x] MP4 → MP3 (24.9.2026, v0.7.3): dugme „MP3“ na kartici gotovog MP4 videa, odmah desno od
  foldera (Ahmedov izbor mjesta). ffmpeg, 192 kbps, original ostaje, ime se ne gazi; folder poslije
  pokazuje MP3, a MP3 ulazi u istoriju (`videodl/convert.py`).
- [x] Pomoć → Šta je novo (v0.7.1): kratke bilješke po verzijama na 5 jezika (`videodl/changelog.py`).
- [x] Titlovi i sličica (23.9.2026, v0.7.0): Preuzimanja → „Titlovi uz video“ (ručno napravljeni,
  jezik aplikacije + engleski, ugrađeni u MP4) i „Sličica kao omot fajla“ (MP3 i MP4).
- [x] Isječak videa (v0.7.0): u meniju formata reda „Isječak (od–do)…“; yt-dlp `download_ranges` +
  `force_keyframes_at_cuts`, fajl dobija oznaku isječka u imenu. Živi test: od 8 s ostaje 3 s.
- [x] Ograničenje brzine (v0.7.0): 1/2/5/10 MB/s ukupno, dijeli se na istovremena preuzimanja.
- [x] MP3 u meniju desnog klika (v0.7.0, dodatak v0.5.1): „Preuzmi ovaj link kao MP3“ i
  „Preuzmi video koji se pušta kao MP3“.
- [x] Hvatanje kopiranog linka (18.9.2026, v0.6.0): Fajl → „Hvataj kopirane linkove" (uključeno
  po podrazumijevanom); kopiran link ulazi u red, preuzimanje i dalje kreće na „Preuzmi".
- [x] Red i istorija se pamte (v0.6.0): `videodl/store.py` upisuje `queue.json` i `history.json` u
  folder podataka; kolačići se nikad ne upisuju. Preuzimanja → „Istorija preuzimanja…".
- [x] Izvještaj o problemu (v0.6.0): Pomoć → „Sačuvaj izvještaj o problemu…"; linkovi se skraćuju
  na ime sajta, ime korisnika i tajne se sakrivaju (`videodl/diagnostics.py`).
- [x] Dugme „Preuzmi kao MP3" u dodatku (22.9.2026, dodatak v0.5.0, aplikacija v0.6.1): isti video,
  ali samo zvuk. Format putuje uz zahtjev (`preset`), aplikacija prihvata samo poznate ključeve i
  označava stavku kao „vlastiti format". E2E u Edge-u pravi .mp3 fajl.
- [x] Desni klik u browseru (17.9.2026, dodatak v0.4.5): stavke „Preuzmi ovaj link / ovaj video /
  video koji se pušta". Direktan tok ide odmah, blob/MSE traži objavu. Kolačići samo ako je dozvola
  već data (meni je ne može tražiti). E2E provjerava da stavke postoje; pravi desni klik potvrđen (24.9.2026 Ahmed potvrdio na v0.7.2: „Sve radi trenutno“ (provjera 1–8)).
- [x] Ažuriranje yt-dlp-a iz aplikacije (17.9.2026, v0.5.4): Pomoć → „Ažuriraj čitač sajtova",
  plus tiha provjera jednom dnevno. Wheel sa PyPI-ja, SHA-256, raspakivanje u folder podataka
  korisnika; `activate()` ga pri pokretanju stavlja ispred verzije iz instalacije, a pokvaren
  paket se briše i ostaje onaj iz paketa. Živa provjera na PyPI-ju prošla.
- [x] Cijela plejlista (v0.7.0): Preuzimanja → „Link videa iz plejliste: preuzmi cijelu
  plejlistu“; tada čitanje linka radi sa `noplaylist=False`.
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
- [x] Ahmed potvrdio ažuriranje sa objavljene verzije i LIVE na pravom sajtu (24.9.2026 Ahmed potvrdio na v0.7.2: „Sve radi trenutno“ (provjera 1–8)).
- [x] Ažuriranje bez `gh` (23.9.2026, v0.6.2): repo je javan, pa se posljednje izdanje čita i
      preuzima HTTPS-om; `gh` je rezerva za 401/403/404. Živo provjereno sa isključenim `gh`:
      v0.6.1 nađena, 198 MB preuzeto za 647 s, SHA-256 se poklopio.
- [x] Ažuriranje sa stvarnog izdanja na sljedeće provjereno uživo (24.9.2026 Ahmed potvrdio na v0.7.2: „Sve radi trenutno“ (provjera 1–8); od v0.6.2 bez `gh`).

Prvobitne stavke:

- PyInstaller `.exe` + bundlovan ffmpeg (vault: „PyInstaller - bundlovanje
  eksternog CLI alata (ffmpeg) uz Python app").
- JS runtime u paketu (Deno `.exe`) ili jasna provjera pri pokretanju.
- Ikona aplikacije.

Exit gate: `.exe` radi na čistom Windowsu bez instaliranog Pythona. — **ispunjeno** 24.9.2026:
Ahmedov prijatelj potvrdio da instaler i program rade na njegovom računaru.
