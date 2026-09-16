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
- Kolačići/prijava: ekstenzija trenutno NEMA pristup kolačićima. Ahmed je odobrio
  slanje kolačića samo za sajt sa kog se preuzima, ali ga je sigurnosni filter
  blokirao; ne dodavati bez Ahmedove nove izričite potvrde.
- DRM se ne zaobilazi; ekstenzija ga samo prepoznaje i označava.

## Okruženje

- Globalni Python 3.14 (paketi iz `requirements.txt`). Ne praviti `.venv` u ovom
  OneDrive folderu — hiljade fajlova bi se sinhronizovale.
- Potrebni su `ffmpeg` i JavaScript runtime (Node.js ili Deno) na PATH-u; bez JS
  runtime-a YouTube često ne radi.
- Preuzeti mediji nikad ne idu u ovaj folder (OneDrive). Živi testovi preuzimaju
  u privremeni folder van OneDrive-a.

## Rad

- Testovi: `python -m unittest discover -s tests` (GUI testovi rade offscreen) i
  `node --test "tests/extension/*.test.mjs"`.
- Poslije izmjene ekstenzije, hosta ili mosta: `node tools/e2e_browser/run.mjs`
  (pravi Edge sa privremenim profilom i `--load-extension`; ne dira Ahmedov profil).
- Najmanja izmjena koja rješava zahtjev; bez refaktorisanja nepovezanog koda.
- Commit samo poslije zelenih testova; push na `origin/main` privatnog repoa.
