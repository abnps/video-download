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

## Instalacija (instaler)

Aplikacija je za ličnu upotrebu. Instaler `VideoDownload-Setup-<verzija>.exe` je u
izdanjima repoa `abnps/video-download` (GitHub → Releases).

- Instaler je na 5 jezika: bosanski, engleski, njemački, španski, francuski.
  Izabrani jezik postaje i jezik aplikacije (mijenja se u **Pomoć → Jezik**).
- Instalira se samo za tvog korisnika (`%LOCALAPPDATA%\Programs\Video Download`),
  bez administratorskih prava. Python, ffmpeg i Node su u paketu.
- **Pomoć → Provjeri ažuriranje** ili tiha provjera pri pokretanju (najviše jednom
  dnevno): nova verzija se preuzme običnim HTTPS-om sa javnih GitHub izdanja (bez naloga
  i bez `gh`), provjeri potpis izdanja (`release.json` + `release.json.sig`, Ed25519) i SHA-256
  i instalira preko postojeće. Nepotpisano ili tuđe izdanje se odbija (od v0.9.6).
- Instaler nije digitalno potpisan, pa Windows SmartScreen može pitati
  „Više informacija → Ipak pokreni" — za svaki novi instaler preuzet iz browsera; ažuriranje
  iz same aplikacije to ne traži.

## Sajt

Zvanični sajt: https://abnps.github.io/video-download/ (folder `site/`, objavljuje ga GitHub Actions
pri svakoj izmjeni). Poslije izmjene changeloga ili pravnih tekstova: `python tools/build_site.py`.
Glavni jezik je engleski, bosanski je u `site/bs/`. Lokalni pregled: `python -m http.server 8765 --directory site`.

## Izdavanje nove verzije

1. Povećaj `__version__` u `videodl/__init__.py` i `version` u `extension/manifest.json`.
2. `python tools/build_release.py` (build van OneDrive-a u `%LOCALAPPDATA%\VideoDownload-build`;
   uključuje self-test spakovane aplikacije). Build odbija da radi ako se paketi ili alati ne slažu
   sa `tools/build-lock.json`, prvo pokreće sve testove, a na kraju potpisuje `release.json` ključem
   `%USERPROFILE%\.videodl\release-signing-key.pem` (ključ nikad ne ide u repo; bez njega nema izdanja).
3. Build osvježi i sajt (`site/`: verzija, veličina, „Šta je novo"); te izmjene idu u commit izdanja.
   Objavi instaler, `.sha256`, `release.json`, `release.json.sig` i kopiju bez verzije (za stalni
   link na sajtu) kao izdanje:

```
gh release create v<verzija> "<instaler>.exe" "<instaler>.exe.sha256" "<folder instalera>\release.json" "<folder instalera>\release.json.sig" "<folder instalera>\VideoDownload-Setup.exe" --repo abnps/video-download --title "Video Download <verzija>" --notes-file "<folder instalera>\release-notes.md"
```

4. Prethodno izdanje sakrij kao nacrt, da javno ostane samo posljednje:

```
gh release edit v<prethodna_verzija> --repo abnps/video-download --draft=true
```

## Podrži projekat

Video Download je besplatan, bez reklama i bez praćenja. Ako ti koristi, možeš dobrovoljno
podržati razvoj: **[PayPal — Support for Video Download](https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ)**. Prilog ništa ne otključava;
program je isti za sve.

<img src="videodl/assets/support-qr.png" alt="QR kod za prilog preko PayPal-a" width="160">

## Uslovi korištenja

Program je namijenjen preuzimanju sadržaja koji korisnik ima pravo da preuzme, prije svega
**vlastitih videa** (npr. videa koje je sam objavio na YouTube-u), sadržaja uz dozvolu nosioca
prava i sadržaja pod slobodnom licencom. Zabranjeno je preuzimanje tuđeg zaštićenog sadržaja bez
dozvole i dijeljenje preuzetog. DRM se ne zaobilazi. Korisnik odgovara za ono što preuzima.
Program nije povezan sa YouTube-om ni Google-om.

Pravni dokumenti (5 jezika; u instaleru se prihvataju licencni ugovor i uslovi, prije toga se
prikazuje politika privatnosti; u aplikaciji su u Pomoć → Ugovori i licence):

| | bs | en | de | es | fr |
|---|---|---|---|---|---|
| Licencni ugovor | [bs](videodl/assets/eula_bs.txt) | [en](videodl/assets/eula_en.txt) | [de](videodl/assets/eula_de.txt) | [es](videodl/assets/eula_es.txt) | [fr](videodl/assets/eula_fr.txt) |
| Uslovi korištenja | [bs](videodl/assets/terms_bs.txt) | [en](videodl/assets/terms_en.txt) | [de](videodl/assets/terms_de.txt) | [es](videodl/assets/terms_es.txt) | [fr](videodl/assets/terms_fr.txt) |
| Privatnost | [bs](videodl/assets/privacy_bs.txt) | [en](videodl/assets/privacy_en.txt) | [de](videodl/assets/privacy_de.txt) | [es](videodl/assets/privacy_es.txt) | [fr](videodl/assets/privacy_fr.txt) |

Licence komponenti (FFmpeg GPL-3.0, Qt LGPL-3.0, Node.js, yt-dlp i ostale) instaler stavlja u folder
`licenses` pored programa, a spisak u `THIRD-PARTY-NOTICES.txt` (`videodl/legal.py`).

## Zahtjevi (razvoj)

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
3. Pokreni video (i u feedu: X, TikTok, Instagram, Facebook, YouTube) i klikni
   ikonu Video Download:
   - **„Preuzmi video koji se pušta"** nađe video koji se pušta i link njegove
     objave (npr. `/status/…` na X-u, `/video/…` na TikToku), pa preuzme baš njega;
   - „Preuzmi link ove stranice" šalje link taba;
   - „Preuzmi" pored pronađenog toka (MP4/HLS/DASH) za sajtove koje yt-dlp ne poznaje.

Poslije izmjene ekstenzije klikni „Reload" kod nje u `edge://extensions`.

Video ide u red sa formatom i folderom koji su trenutno izabrani u aplikaciji i
odmah se preuzima (bez klika na „Preuzmi").

Ograničenja:
- Video zaštićen DRM-om (Netflix, Disney+, Prime Video…) se ne može preuzeti;
  ekstenzija to označi sa „DRM".
- Video iza prijave (Instagram stories, privatni nalozi): pri prvom preuzimanju
  browser pita za dozvolu pristupa kolačićima. Ako se popup pri tome zatvori, klikni
  ponovo. Šalju se samo kolačići tog sajta, ne čuvaju se, a privremeni fajl za
  yt-dlp se briše odmah. Dozvola se uklanja u `edge://extensions` → Detalji.

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
- `videodl/dialogs.py`, `videodl/desktop.py` — pomoćni prozori (istorija, podrška, ugovori, uputstvo
  za dodatak) i otvaranje fajlova/foldera u Windowsu
- `videodl/release_signing.py` — potpis i provjera opisa izdanja (Ed25519)
- `videodl/widgets.py`, `videodl/icons.py` — red sa sličicom, prazan ekran, ikone
- `videodl/browser.py` — provjera zahtjeva iz browsera
- `videodl/bridge.py` — lokalni most u aplikaciji (127.0.0.1 + token)
- `videodl/native_host.py` — native messaging host (browser ↔ aplikacija)
- `videodl/native_messaging.py` — registracija hosta za Chrome/Edge
- `videodl/i18n.py`, `extension/i18n.js` — prevodi (BS, EN, DE, ES, FR)
- `videodl/updater.py` — provjera i instalacija nove verzije
- `videodl/runtime.py` — putanje u razvoju i u instaliranoj verziji
- `extension/` — Edge/Chrome ekstenzija (Manifest V3)
- `installer/` — Inno Setup skripta i bosanski prevod instalera
- `tools/` — ikone, build instalera i browser E2E
- `00_plan/plan_projekta.md` — faze i exit gate-ovi
