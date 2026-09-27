# Plan: Video Download za Android (.apk van Play Storea)

Napravljeno 27.9.2026 (Ahmed: „Plan za .apk"). Nadovezuje se na stavku „Android" u `plan_projekta.md`.
Ništa od ovoga još nije počelo; odluke označene **[Ahmed]** su njegove.

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

1. Odluka A (GPL, brže) ili B (naša licenca, sporije).
2. Android telefon za probu: proizvođač i verzija Androida.
3. Spremnost na Googleovu provjeru programera (lični podaci Googleu).
4. Potvrda redoslijeda: Android tek poslije roditeljske kontrole i Mac probe, ili prije.
