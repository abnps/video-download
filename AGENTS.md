# Video Download — pravila za agente

## Jezik

Sve što agent piše Ahmedu (odgovori, izvještaji, pitanja, sažeci) i komentari u
kodu: bosanski/srpski, isključivo latinica. Identifikatori i nazivi fajlova
ostaju tehnički (engleski). Izvor: vault `CLAUDE.md`, odjeljak „Jezik i stil".

## Kontekst

- Globalna memorija: `C:/Users/ahmed/OneDrive/Прилози/Документи/AHMED/PROJECT A/AGENTS.md`
  (Obsidian vault `C:/Users/ahmed/OneDrive/AHMED STUF/Ahmed Stuf`).
- Projektna memorija u vaultu: `02 Posao/Video Download.md` — status, odluke,
  sledeći korak. Dopuni je poslije materijalne odluke ili verifikovanog rezultata.
- `00_plan/plan_projekta.md` je izvor istine za faze, Definition of Done i exit
  gate-ove. Faza se ne proglašava završenom bez dokaza ili Ahmedovog izuzetka.

## Obim i upotreba

- Samo lična upotreba. Bez zaobilaženja DRM-a, bez piratskih izvora, bez javne
  distribucije ili prodaje prije pravne provjere.
- yt-dlp logika ostaje u `videodl/presets.py`, `probe.py`, `download.py` i
  `jobs.py`, bez Qt-a. `gui.py` samo prikazuje stanje i pokreće poslove.
- Prekid preuzimanja briše samo privremene fajlove tog pokušaja, nikad ranije
  preuzete fajlove.

## Browser integracija — sigurnosna pravila

- Put: ekstenzija → native host (browser dozvoljava samo `EXTENSION_ID` iz
  `native_messaging.py`, koji proizlazi iz `key` u `extension/manifest.json`) →
  lokalni most u aplikaciji (samo 127.0.0.1, tajni token iz `bridge.json`, provjera
  `Host` zaglavlja). Nijednu od ovih provjera ne slabiti.
- Promjena `key` u manifestu mijenja ID ekstenzije i prekida vezu.
- Registracija piše samo u HKCU (`NativeMessagingHosts` za Chrome i Edge).
- Kolačići/prijava (Ahmed izričito potvrdio 17.9.2026, za Instagram stories i
  sadržaj iza prijave): `cookies` je OPCIONA dozvola koju browser traži dijalogom.
  Šalju se samo kolačići sajta sa kog se preuzima (aplikacija dodatno odbacuje tuđe
  domene), drže se samo u memoriji, a yt-dlp ih dobija kroz privremeni fajl koji se
  briše odmah poslije čitanja/preuzimanja. Vrijednosti kolačića nikad u log, poruke,
  `repr`, podešavanja ili server log testa. Ne proširivati bez Ahmedove potvrde.
- DRM se ne zaobilazi; ekstenzija ga samo prepoznaje i označava.

## Okruženje

- Globalni Python 3.14 (paketi iz `requirements.txt`). Ne praviti `.venv` u ovom
  OneDrive folderu — hiljade fajlova bi se sinhronizovale.
- Potrebni su `ffmpeg` i JavaScript runtime (Node.js ili Deno) na PATH-u; bez JS
  runtime-a YouTube često ne radi.
- Preuzeti mediji nikad ne idu u ovaj folder (OneDrive). Živi testovi preuzimaju
  u privremeni folder van OneDrive-a.

## Jezici, instaler i ažuriranje

- 5 jezika (bs, en, de, es, fr): svaki novi tekst ide u `videodl/i18n.py` i, za popup,
  u `extension/i18n.js`, na svih 5 jezika; testovi padaju ako prevod fali.
  Tekstovi iz radnih niti su ključevi prevoda, prevode se tek pri prikazu.
- Instaler: `python tools/build_release.py` (PyInstaller + Inno Setup, build van
  OneDrive-a). `installer/Bosnian.isl` i `.iss` moraju ostati UTF-8 sa BOM-om.
- Aplikacija ostaje LIČNA (Ahmedova odluka 17.9.2026): nema javnog repoa, sajta ni
  prodaje bez nove odluke i pravne provjere (§95a UrhG, LG Hamburg/Uberspace).
- Ažuriranje čita izdanja privatnog repoa `npgamy/video-download` preko `gh` prijave
  (bez tokena u .exe); izdanje mora imati `VideoDownload-Setup-<verzija>.exe` i `.exe.sha256`.
- yt-dlp se ažurira odvojeno od aplikacije (`videodl/ytdlp_update.py`): wheel sa PyPI-ja uz
  SHA-256, raspakuje se u `%LOCALAPPDATA%\VideoDownload\yt-dlp\<verzija>`, a `activate()` iz
  `pokreni.pyw` mora ostati PRIJE prvog `import yt_dlp` (inače radi verzija iz paketa).
- Red i istorija (`videodl/store.py`) se upisuju u folder podataka; u te fajlove NIKAD ne smiju
  ući kolačići. Izvještaj o problemu (`videodl/diagnostics.py`) skraćuje linkove na ime sajta.
- Instalirana verzija koristi alate iz `tools/` pored `.exe`-a (ffmpeg, ffprobe, node);
  razvoj koristi PATH (`videodl/runtime.py`).

## Rad

- Testovi: `python -m unittest discover -s tests` (GUI testovi rade offscreen) i
  `node --test "tests/extension/*.test.mjs"`.
- Poslije izmjene ekstenzije, hosta ili mosta: `node tools/e2e_browser/run.mjs`
  (pravi Edge sa privremenim profilom i `--load-extension`; ne dira Ahmedov profil).
- Najmanja izmjena koja rješava zahtjev; bez refaktorisanja nepovezanog koda.
- Commit samo poslije zelenih testova; push na `origin/main` privatnog repoa.
