# Plan 1.0.7: zaštita od blokade, pauze i podrška (Ahmed 2.11.2026)

Grana `zastita-od-blokade`, radna kopija `C:\Video Downloader\Build\wt-107`. Bez commita, verzije i objave dok
Ahmed ne kaže. Samo desktop (Windows/Mac/Linux, isti Python kod); Android dolazi kasnije, posebno.

## Usvojeno (sve, Ahmed 2.11.2026)

1. Automatsko čekanje kad sajt blokira (HTTP 429, „potvrdi da nisi bot"): kartica s odbrojavanjem, sam nastavlja.
2. Preventivna pauza svakih 25 preuzimanja zaredom s istog sajta (30–60 s), ista kartica.
3. „Jesi li znao?" savjet na kartici dok traje pauza.
4. Windows obavještenje kad se poslije pauze nastavi (samo ako prozor nije u fokusu).
5. Program uči: poslije blokade 7 dana pauze kreću ranije (od 5. videa) i traju 1,5× duže.
6. „Nastavi kasnije": ostatak ostaje u redu; pri sljedećem pokretanju kartica „Imaš N nedovršenih — Nastavi".
7. Dostignuće „Strpljivi" (⏳): pauza je odbrojala do kraja (bez „Nastavi odmah", „Nastavi kasnije", „Zaustavi").
8. Poruka uspjeha „Gotovo: 50/50 videa, 6,1 GB ✓" kad grupa od bar 50 preuzimanja završi bez ijedne greške.
9. Mjesečni pregled („Tvoj oktobar") prvog pokretanja u novom mjesecu + godišnji u januaru; slika za dijeljenje.
10. Blagi usporivači po sajtu (tabela ispod).

## Pravila za red o podršci (važe za karticu pauze, 50/50 i pregled)

- „Već sam podržao" → 90 dana bez poziva (postojeće `support.SNOOZE`); umjesto poziva „Hvala što podržavaš ♥".
- Najviše **jednom sedmično**; ako se program koristi **često → dvaput sedmično** (najmanje 3,5 dana razmaka).
- „Često" = u posljednjih 7 dana preuzimanja u bar 3 različita dana ILI bar 30 novih preuzimanja.
- Ne prije 10 novih preuzimanja ukupno.
- Zajednički rok s postojećim sedmičnim prozorom: računa se od kasnijeg od (zadnji prozor, zadnji red na kartici),
  pa korisnik nikad ne dobije dva poziva u kratkom razmaku. Ostala postojeća pravila (traka svakih 10, čestitke)
  se ne mijenjaju.
- Pauza (odbrojavanje) nikad ne zavisi od priloga: isto traje i za one koji su podržali. Prilog ništa ne otključava.

## Usporivači (modul `videodl/pacing.py`, bez Qt-a)

Porodice sajtova (adresa stavke → porodica; ostali sajtovi i direktni tokovi iz dodatka = bez usporavanja):
youtube (youtube.com, youtu.be, youtube-nocookie.com, music.youtube.com), instagram, tiktok, facebook (facebook.com,
fb.watch), x (x.com, twitter.com). Instagram i TikTok: trajanja ×1,5 (brže blokiraju).

Brojač zaredom po porodici: +1 pri svakom POKRETANJU preuzimanja; nula ako 15 min nije bilo preuzimanja s te porodice.

| zaredom (redni broj sljedećeg) | razmak prije sljedećeg | ostalo |
|---|---|---|
| 1–9 | 0 | |
| 10–24 | 2–5 s nasumično | najviše 2 istovremeno s te porodice |
| 25–49 | 5–10 s | pauza 30–60 s poslije svakog 25. (kartica) |
| 50+ | 8–15 s | isto |

- Naučeno (blokada u zadnjih 7 dana, pamti se u podešavanjima): pragovi 10/25/50 → 5/13/25, trajanja ×1,5.
- Razmak se drži u rasporedu (kao rok ponovnog pokušaja), a ne `time.sleep` u niti: drugi sajtovi idu dalje.
- Statusna traka: „⏱ Pauza 4 s, čuva od blokade (YouTube)".
- Čitanje velike plejliste/kanala sa stroge porodice: `sleep_interval_requests` 0,5 s.
- Postavke → Ponašanje: „Zaštita od blokade" (uključeno). Isključeno gasi razmake, pauze na 25 i ograničenje
  istovremenih; automatsko čekanje na blokadu ostaje (bez njega bi preuzimanje samo palo).

## Blokada (429 / bot)

- Stavka sa stroge porodice padne s greškom „rate" ili „bot" (isti obrasci kao `widgets._FRIENDLY_ERRORS`):
  vraća se u red (čeka), porodica stoji 5 min (druga blokada iste stavke 10 min, treća 15 min), pa nastavlja
  sama. Četvrta = obična greška s razumljivom porukom. Postojeće „veza je pukla" ponavljanje ostaje kakvo jeste.
- Pamti se vrijeme blokade (učenje, tačka 5).
- „Zaustavi" poništava čekanje (stavke ostaju u redu kao i do sada).

## Kartica pauze (iznad liste, kao traka za podršku)

- Naslov: blokada „YouTube traži kratku pauzu — nastavljam za 4:32"; preventivna „Kratak predah da YouTube ne
  blokira — nastavljam za 0:45".
- Objašnjenje (1 rečenica), savjet „💡 Jesi li znao? …" (8 savjeta, redom), red o podršci po pravilima gore
  s brojem preuzetih danas i veličinom.
- Dugmad: „Nastavi odmah", „Nastavi kasnije", „♥ Podrži" (samo uz red o podršci).
- Ostale porodice/sajtovi se za to vrijeme preuzimaju normalno.

## Mjesečni pregled (`videodl/recap.py`, bez Qt-a)

- Bilježi se po mjesecu (podešavanja, JSON, zadnjih 13 mjeseci): broj, bajtovi, sekunde sadržaja, sajtovi,
  najduži video, dani u sedmici. Ništa se ne šalje; naslovi se ne pamte.
- Prikaz: prvo pokretanje u novom mjesecu, ako je prošli mjesec imao bar 10 preuzimanja; jednom po mjesecu.
  U januaru umjesto decembarskog ide godišnji pregled (cijela godina, bar 10).
- Dugmad: „Sačuvaj sliku" (PNG kartica: brojke + adresa sajta, bez naslova videa), „Kopiraj sliku", „♥ Podrži"
  (po pravilima), „Zatvori". Postavke → Ponašanje: „Mjesečni pregled" (uključeno).

## Testovi (za svaku tačku)

- `tests/test_pacing.py`: porodice, pragovi, nasumični rasponi, reset poslije 15 min, ograničenje istovremenih,
  pauza na 25, učenje 7 dana, blokada 5/10/15 min i odustajanje.
- `tests/test_recap.py`: bilježenje, mjesec/godina, prag 10, jednom po mjesecu, oštećen JSON.
- `tests/test_support.py`: dvaput sedmično uz čestu upotrebu, 90 dana, zajednički rok s prozorom.
- `tests/test_pause_gui.py`: kartica, „Nastavi odmah/kasnije", obavještenje, dostignuće, 50/50, nastavak reda
  pri pokretanju, statusna traka, Postavke.
- Svi postojeći testovi (`python -m unittest discover -s tests`, Node testovi) moraju ostati zeleni.

## Redoslijed rada

1. `pacing.py` + testovi → 2. `support.py` pravila + testovi → 3. `recap.py` + testovi →
4. prozor: kartica, raspored, blokada, nastavak, obavještenje, dostignuće, 50/50, pregled, Postavke →
5. prevodi (bs, en, de, es, fr) → 6. svi testovi → 7. snimci ekrana Ahmedu → čeka „commit"/„objavi".
