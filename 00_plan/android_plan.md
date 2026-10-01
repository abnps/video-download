# Android beta — stanje i izvorni plan

Izvorni plan napisan je 27.9.2026 (Ahmed: „Plan za .apk"). Odluke označene **[Ahmed]** su njegove.
Tekst od „Cilj“ naniže čuva tadašnji plan; za sadašnji postupak izdavanja važi `README.md`.

**Stanje 29.9.2026:** Android beta je implementirana kao Kotlin/Compose aplikacija s Chaquopyjem i yt-dlp-om.
Podržani su MP4 video i zaseban M4A zvuk; slika i zvuk se spajaju Androidovim MediaMuxerom, bez ffmpeg-a.
MP3, cijele plejliste i potvrda 18+ sadržaja još nisu dio Android bete. Najstariji podržani sistem je Android 10
(API 29), a ne planirani Android 8. Aplikacija ima dijeljenje linka, foreground preuzimanje, lokalnu istoriju,
oporavak prekinutog reda uz ručni ponovni pokušaj, ograničen dijagnostički izvještaj i ažuriranje iz potpisanog APK-a.
APK se potpisuje lokalno i dodaje tačno određenom nacrtu GitHub izdanja; Mac i Android fajlovi se provjeravaju prije
objave cijelog izdanja. Android lint, Kotlin kompilacija i debug gradnja sada su u CI, kao i Python testovi Android jezgra.
Ručna proba na stvarnom telefonu i puna provjera izdavanja ostaju prije naredne javne verzije.

## Izvorni plan iz 27.9.2026 (historijski zapis)

## Cilj

Isti program kao na Windowsu/Macu, prilagođen telefonu: podijeli link iz bilo koje aplikacije (preglednik,
aplikacija za video, poruke) → izaberi MP4 ili MP3 → fajl je u Galeriji / Muzici. Bez naloga, bez reklama,
bez praćenja, na 5 jezika — kao desktop verzija.

## Kako bi radilo (tehnika)

| Dio | Rješenje | Napomena |
|---|---|---|
| Aplikacija | Kotlin + Jetpack Compose | izvorni Android izgled, svijetla/tamna tema |
| Čitanje sajtova | yt-dlp (Python) spakovan u aplikaciju | isti „čitač sajtova" kao na desktopu, ažurira se u aplikaciji |
| Spajanje slike i zvuka, MP3 | ffmpeg spakovan u aplikaciju | kao na desktopu |
| Ulaz linka | „Podijeli" meni Androida + ručno lijepljenje | zamjenjuje dodatak za browser |
| Preuzimanje | usluga u prvom planu s obavještenjem (napredak, Zaustavi) | radi i kad je aplikacija zatvorena |
| Čuvanje | MediaStore: Movies/Video Download i Music/Video Download | vidi se u Galeriji i muzičkim aplikacijama |
| Tekstovi | skripta prevodi `videodl/i18n.py` u Android `strings.xml` | jedan izvor za 5 jezika |

**Put do yt-dlp-a na telefonu — ključna odluka [Ahmed]:**
- **A) biblioteka youtubedl-android** (koriste je Seal i YTDLnis): gotovo pakovanje Pythona, yt-dlp-a i
  ffmpeg-a, provjereno na milionima telefona. Najbrži put (prototip za ~1 sedmicu).
  **Ali: licenca GPL-3.0** → i Android aplikacija mora biti GPL-3.0 (izvorni kod javan, svako smije
  kopirati i mijenjati). To se sudara s planom privatnog repoa i s budućim plaćenim Video Toolkitom.
- **B) vlastito pakovanje** (Chaquopy, MIT licenca + vlastiti ffmpeg bez GPL dijelova): licenca ostaje naša,
  ali 1–2 sedmice više posla i više održavanja (svaka nova verzija Pythona/ffmpeg-a je naša briga).
- Moja preporuka: **B** ako Android treba ostati pod istom licencom kao desktop; **A** ako je Ahmedu u redu
  da Android verzija bude otvoren kod (GPL).
- **ODLUKA (Ahmed, 27.9.2026): B** — vlastito pakovanje (Chaquopy za Python/yt-dlp, ffmpeg izgrađen bez
  GPL dijelova, npr. bez x264; H.264 kroz Android MediaCodec). Biblioteka youtubedl-android (GPL-3.0) se NE
  koristi, ni njen kod; licenca ostaje kao za desktop (licencni ugovor na 5 jezika).

## Faze

1. **Odluke i priprema (Ahmed + ja, 1 dan)**
   - A ili B (licenca); ime paketa (npr. `io.github.abnps.videodownload`); najstariji Android: 8.0 (API 26);
     prvo samo ARM64 telefoni (99 % današnjih).
   - Ključ za potpis APK-a: pravim ga ja, čuva se kao i ključ za potpis izdanja (nikad u repo; Ahmed pravi
     rezervnu kopiju u OneDrive Personal Vault). **Bez tog ključa nema ažuriranja** — Android odbija APK
     potpisan drugim ključem.
2. **Prototip (~1–2 sedmice)**: podijeli link → MP4 ili MP3 → fajl u Galeriji; obavještenje s napretkom.
   Proba na Ahmedovom telefonu (APK preko USB-a ili linka).
3. **Probna verzija / beta (~2–3 sedmice)**: red s više linkova, formati (najbolji, 1080p, 720p, 480p, MP3,
   M4A), plejliste, istorija, 18+ potvrda (kao desktop; YouTube izuzet), razumljive greške, 5 jezika,
   ažuriranje yt-dlp-a u aplikaciji, uslovi korištenja i privatnost (isti tekstovi kao desktop).
4. **Ažuriranje aplikacije**: aplikacija čita posljednje izdanje na GitHubu (kao desktop), provjerava
   potpis/SHA-256 i nudi instalaciju novog APK-a (Android traži dozvolu „Instaliraj nepoznate aplikacije"
   jednom). Opciono: Obtainium i IzzyOnDroid (katalog van Play Storea za ovakve aplikacije).
5. **Objava**: APK u istom GitHub izdanju kao Windows i Mac (automatski, GitHub posao pravi i potpisuje APK),
   blok „Android (beta)" na sajtu s uputstvom „dozvoli instalaciju iz preglednika".
6. **Testovi**: Kotlin testovi + Android emulator u GitHub Actions (kao sada Mac); ručna proba na 2–3
   telefona (Ahmed, prijatelji — različiti proizvođači, jer Samsung/Xiaomi različito gase pozadinske poslove).

## Rizici i ograničenja (iskreno)

- **Googleova provjera programera** (najava 2025): APK-ovi van Play Storea na certificiranim telefonima
  moraju biti od identifikovanog programera — od septembra 2026. u Brazilu, Indoneziji, Singapuru i
  Tajlandu, zatim postepeno svuda (2027+). Za DE/RS i tačne uslove (cijena, lični dokument) treba provjeriti
  na dan početka. Bez toga APK uskoro neće moći da se instalira na većini telefona. **[Ahmed: registracija
  na svoje ime]**
- **YouTube na telefonu**: yt-dlp za YouTube danas traži JavaScript izvršavanje (na desktopu to radi Node).
  Na Androidu treba provjeriti šta youtubedl-android / naše pakovanje nudi — najveći tehnički rizik, prvo
  se provjerava u prototipu.
- **Veličina**: ~60–90 MB APK (Python + ffmpeg). Prihvatljivo, ali veće od običnih aplikacija.
- **Pozadinski rad**: Android 14/15 ograničavaju duge pozadinske poslove; dugačke plejliste moraju biti
  izdijeljene i nastavljive.
- **Konkurencija**: Seal, YTDLnis, NewPipe su besplatni i dobri. Naša prednost mora biti ista kao na
  desktopu: jednostavnost, 5 jezika, isti program na svim uređajima, bez praćenja — **[Ahmed: da li je to
  dovoljno razloga]**.
- Bez Play Storea: nema automatskog ažuriranja od strane Googlea, korisnik mora dozvoliti instalaciju
  „iz nepoznatih izvora" (jednom). Pravila ista kao desktop: bez DRM-a, bez piratskih izvora, 18+ potvrda.

## Googleova provjera programera — provjereno 27.9.2026 (zvanične stranice)

- Od 30.9.2026. samo Brazil, Indonezija, Singapur, Tajland; 2027. globalno (DE/RS bez tačnog datuma).
  Certificirani telefoni, Android 7+.
- Pun lični nalog (Android Developer Console): lični dokument s fotografijom, ime, adresa, e-mail, telefon,
  jednokratno 25 $. Za aplikacije van Play Storea kontakt-podaci „nisu prikazani javno" (samo Google ih ima).
- Besplatan ograničen nalog (studenti/hobisti): bez dokumenta i naknade, najviše 20 uređaja — dovoljno za
  prototip i betu s Ahmedom i prijateljima.
- Bez registracije: samo „napredni postupak" na telefonu (opcije za programere, upozorenja, restart,
  24 sata čekanja) — za obične korisnike praktično neupotrebljivo.
- Prijedlog: prototip/beta na besplatnom ograničenom nalogu; pun nalog tek za javno izdanje (najkasnije 2027.).
- Izvori: developer.android.com/developer-verification; support.google.com/android-developer-console/answer/16561738
  i /16641416; 9to5google.com (napredni postupak, 19.3.2026).

## Šta treba od Ahmeda prije početka

1. ~~Odluka A ili B~~ — B (27.9.2026).
2. ~~Android telefon za probu~~ — Samsung Galaxy S26 Ultra (Android 16 / One UI 8.x, ARM64). Paziti na
   Samsungov Auto Blocker (blokira APK van prodavnica; za probu privremeno isključiti) i uspavljivanje
   aplikacija u pozadini (preuzimanje mora biti usluga s obavještenjem).
3. Spremnost na Googleovu provjeru programera (lični podaci Googleu).
4. Potvrda redoslijeda: Android tek poslije roditeljske kontrole i Mac probe, ili prije.

## Alati (instalirano 27.9.2026, Ahmed odobrio preuzimanje i Googleovu SDK licencu)

`C:\Video Downloader\Alati\` (van projekta i van AppData, vidljivo Ahmedu; `PROCITAJ.txt` unutra):
- `jdk-21` — Eclipse Temurin 21.0.12.1 (SHA-256 provjeren s Adoptium API-ja); `JAVA_HOME` postaviti na njega.
- `android-sdk` — cmdline-tools 15859902 (SHA-256 sa developer.android.com), platform-tools 37.0.1 (`adb`),
  build-tools 37.0.0, platforms;android-37.0, ndk;29.0.14206865. `ANDROID_HOME` = taj folder.
- `sdkmanager.bat` iz Basha ne radi zbog razmaka u putanji: pokretati iz PowerShella (Start-Process).
- Emulator nije instaliran (proba na Ahmedovom S26 Ultra + GitHub Actions).
