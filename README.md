# Video Download

Lična Windows desktop aplikacija (PySide6 + yt-dlp) za preuzimanje videa i zvuka
sa YouTube-a i drugih sajtova koje podržava yt-dlp. Samo za ličnu upotrebu.

## Mogućnosti

- Jedan ili više linkova odjednom; plejliste i kanali se razvijaju u red čekanja
  (svaka plejlista dobija svoj podfolder).
- Formati: MP4 najbolji / do 1080p / 720p / 480p, samo zvuk MP3 ili M4A.
- Ukupan napredak, brzina i preostalo vrijeme; „Zaustavi" prekida preuzimanje i
  briše samo privremene fajlove tog pokušaja; „Ponovi" za neuspjele stavke.
- Dvoklik na završenu stavku otvara fajl u Exploreru.

## Zahtjevi

- Python 3.14
- `ffmpeg` na PATH-u (spajanje videa i zvuka, MP3/M4A)
- Node.js ili Deno na PATH-u (YouTube zaštita linkova)

```
python -m pip install --user -r requirements.txt
```

## Pokretanje

Dvoklik na `pokreni.bat`, ili:

```
python -m videodl
```

Podrazumijevani folder za preuzimanja je `%USERPROFILE%\Videos\Video Download`.

## Testovi

```
python -m unittest discover -s tests
```

## Struktura

- `videodl/presets.py` — formati i yt-dlp opcije
- `videodl/probe.py` — čitanje linka (video, plejlista, kanal)
- `videodl/download.py` — preuzimanje, napredak, prekid, čišćenje
- `videodl/jobs.py` — red čekanja
- `videodl/gui.py` — glavni prozor
- `00_plan/plan_projekta.md` — faze i exit gate-ovi
