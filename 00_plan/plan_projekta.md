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

## Van obima

- Zaobilaženje DRM-a, plaćeni/zaštićeni sadržaj bez pristupa, piratski izvori.
- Javna distribucija ili prodaja bez prethodne pravne provjere uslova platformi.

## Faza 1 — MVP (u toku)

Sadržaj: unos jednog ili više linkova, plejlista/kanal se razvija u stavke reda,
formati MP4 (najbolji / 1080p / 720p / 480p) i MP3/M4A, ukupan napredak
(video + zvuk), zaustavljanje sa čišćenjem privremenih fajlova, ponavljanje
neuspjelih stavki, izbor foldera, pamćenje podešavanja.

Exit gate:
- [x] Automatski testovi prolaze (logika, red, GUI offscreen) — 33 testa, 16.9.2026.
- [x] Živi test na pravom linku (16.9.2026, „Me at the zoo", jNQXAC9IVRw):
      MP4 najbolji = H.264 + AAC, 19 s (ffprobe); ponovno pokretanje prepoznaje
      postojeći fajl; MP3 192 kbps; plejlista i kanal (@jawed) se čitaju;
      prekid usred preuzimanja i tokom drugog dijela (zvuk) reaguje odmah i ne
      ostavlja nijedan fajl. Napredak je monoton za video + zvuk.
- [ ] Ahmed pokrenuo `pokreni.bat` i potvrdio da prozor i preuzimanje rade.

Poznato ograničenje: prekid dok yt-dlp još čita informacije o videu (prije prvog
bajta, na YouTube-u ponekad 10+ s) djeluje tek kad preuzimanje krene.

## Faza 2 — Dorada

- Titlovi i thumbnail (opciono uz video).
- Lijepljenje linka iz clipboarda jednim klikom.
- Provjera/ažuriranje yt-dlp-a iz aplikacije (YouTube se često mijenja).
- Opcija „cijela plejlista" za linkove videa unutar liste (sada se preuzima samo video).
- Brži prekid u fazi čitanja informacija (prije početka preuzimanja).
- Kolačići iz browsera za sadržaj koji traži prijavu (samo Ahmedov nalog).

## Faza 3 — Pakovanje

- PyInstaller `.exe` + bundlovan ffmpeg (vault: „PyInstaller - bundlovanje
  eksternog CLI alata (ffmpeg) uz Python app").
- JS runtime u paketu (Deno `.exe`) ili jasna provjera pri pokretanju.
- Ikona aplikacije.

Exit gate: `.exe` radi na čistom Windowsu bez instaliranog Pythona.
