# Video Download

Lična Windows desktop aplikacija (PySide6 + yt-dlp) za preuzimanje videa i zvuka:
preko linka ili direktno iz browsera (Edge/Chrome). Samo za ličnu upotrebu.

## Mogućnosti

- Kopiraj link pa klikni zeleno **„Zalijepi"** (ili Ctrl+V, ili prevuci link u
  prozor), izaberi format i klikni plavo **„Preuzmi"**.
- Plejliste i kanali se razvijaju u listu (svaka plejlista dobija svoj podfolder).
- Svaki red ima sličicu i trajanje; plavi link formata mijenja format samo tog
  videa, strelica preuzima samo taj video, × ga uklanja.
- Formati: MP4 najbolji / do 1080p / 720p / 480p, samo zvuk MP3 ili M4A.
- Ukupan napredak, brzina i preostalo vrijeme; „Zaustavi" prekida preuzimanje i
  briše samo privremene fajlove tog pokušaja; neuspjeli red ima dugme „Pokušaj ponovo".
- Završen red ima dugme koje otvara fajl u Exploreru.
- Ekstenzija za Edge/Chrome: prepoznaje video koji stranica pušta (MP4/WebM,
  HLS, DASH) i šalje ga aplikaciji; ako aplikacija nije pokrenuta, pokreće je.

## Zahtjevi

- Python 3.14
- `ffmpeg` na PATH-u (spajanje videa i zvuka, MP3/M4A, HLS)
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
Druga instanca se ne otvara: samo se podigne prozor već pokrenute.

## Preuzimanje iz browsera

1. Pokreni aplikaciju jednom. Ona registruje vezu sa browserom samo za tvog
   Windows korisnika (HKCU, Chrome i Edge).
2. Edge: otvori `edge://extensions`, uključi „Developer mode", klikni
   „Load unpacked" i izaberi folder `extension` iz ovog projekta.
   Chrome: isto preko `chrome://extensions`.
3. Na stranici sa videom pokreni video i klikni ikonu Video Download:
   - „Preuzmi video sa stranice" za YouTube i sajtove koje yt-dlp poznaje;
   - „Preuzmi" pored pronađenog toka za ostale sajtove.

Video ide u red sa formatom i folderom koji su trenutno izabrani u aplikaciji i
odmah se preuzima (bez klika na „Preuzmi").

Ograničenja:
- Video zaštićen DRM-om (Netflix, Disney+, Prime Video…) se ne može preuzeti;
  ekstenzija to označi sa „DRM".
- Video koji se vidi samo uz prijavu na sajt još nije podržan (kolačići).

Ako se projekat premjesti u drugi folder, pokreni aplikaciju ponovo (registracija
se osvježi) i ponovo učitaj ekstenziju. Uklanjanje registracije:

```
python -m videodl.native_messaging --uninstall
```

## Testovi

```
python -m unittest discover -s tests
node --test "tests/extension/*.test.mjs"
node tools/e2e_browser/run.mjs
```

Zadnja komanda je E2E u pravom Edge-u (privremeni profil, lokalni test sajt,
izlaz u `%TEMP%\videodl-e2e`); pokreće i gasi test instancu aplikacije.

## Struktura

- `videodl/presets.py` — formati i yt-dlp opcije
- `videodl/probe.py` — čitanje linka (video, plejlista, kanal)
- `videodl/download.py` — preuzimanje, napredak, prekid, čišćenje
- `videodl/jobs.py` — red čekanja
- `videodl/gui.py` — glavni prozor (meni, traka, red, tema)
- `videodl/widgets.py`, `videodl/icons.py` — red sa sličicom, prazan ekran, ikone
- `videodl/browser.py` — provjera zahtjeva iz browsera
- `videodl/bridge.py` — lokalni most u aplikaciji (127.0.0.1 + token)
- `videodl/native_host.py` — native messaging host (browser ↔ aplikacija)
- `videodl/native_messaging.py` — registracija hosta za Chrome/Edge
- `extension/` — Edge/Chrome ekstenzija (Manifest V3)
- `tools/` — ikone i browser E2E
- `00_plan/plan_projekta.md` — faze i exit gate-ovi
