# Pregled kvaliteta — 21.10.2026.

Osnova: `main` na `18faad3`. Ahmed je odobrio pregled i ispravke programa i sajta.
Izmjene su pripremljene u grani `quality-review-20261021`; broj verzije i postojeći Store paket ostaju 1.0.3.

## Potvrđeni i ispravljeni propusti

| Mjesto | Problem i ponavljanje | Ispravka |
|---|---|---|
| `android/.../DownloadService.kt`, obrada greške | Neuspješan posao upisivao je puni link i sirovu poruku sajta u logcat; link može sadržati privatnu putanju ili token. | Zapisuje se samo postojeća, očišćena kategorija greške; sirovi link i izuzetak se ne loguju. |
| `videodl/diagnostics.py`, lista alata | Sačuvani izvještaj otkrivao je apsolutnu putanju ffmpeg/ffprobe/Node alata, uključujući privatne nazive foldera. Ponovljeno testom sa izmišljenim korisničkim imenom. | Izvještaj navodi samo „u paketu”, „na sistemu” ili „nema ga”. |
| `extension/popup.js`, slanje i učitavanje stanja | Odbijen `runtime.sendMessage` prekidao je funkciju prije otključavanja dugmadi; pri otvaranju mogao je ostati prazan status. Ponovljeno kontrolisanim prekidom veze u testu stvarnog popup koda. | Obrada greške, `finally` za dugmad i prevedeno rezervno stanje. Novi pokušaj može uspjeti u istom prozoru. |
| `videodl/achievements.py`, učitavanje | U `pending` listi objekat ili lista ruše pokretanje; duplikati ponavljaju čestitke; neispravan datum može srušiti prikaz zbirke. Ponovljeno pokvarenim JSON zapisom. | Prihvataju se samo poznata osvojena dostignuća s upotrebljivim datumom; čestitke i sajtovi se ne dupliraju. |
| `site/assets/site.js`, Podijeli → kopiranje | Kada Clipboard API i rezervni način zakažu, dugme je ipak prikazivalo „Kopirano ✓”. Ponovljeno simulacijom oba neuspjeha. | Potvrda se prikazuje tek nakon uspjeha; pri neuspjehu adresa ostaje izabrana za ručno kopiranje. |
| `tools/build_site.py`, stranica dodatka | Svih pet jezika tvrdilo je da prodavnice ne primaju ovakve dodatke, iako je Firefox dodatak dostupan. | Jasno su razdvojeni ručna Edge/Chrome instalacija i zvanična Firefox stranica. |
| `tools/site_home.py` i `tools/build_site.py`, Android instalacija | APK dugme bilo je iza koraka koji pretpostavljaju da je fajl već preuzet. Samsung uputa tražila je isključivanje zaštite bez uslova da ona blokira instalaciju. | APK dugme je prije koraka; Auto Blocker uputa važi samo ako blokira instalaciju, uz ponovno uključivanje nakon toga. Svih pet jezika je osvježeno. |

## Provjera

- Puni Python discover: 445 testova, 2 preskočena, uspješno. Poslije posljednje izmjene dijagnostike i fokusirana provjera dostignuća, dijagnostike, sajta i Android jezgra: 67/67.
- Node: 28/28 testova za dodatak i sajt. Novi testovi obuhvataju prekid veze, ponovni pokušaj i stvarni ishod kopiranja. CI i provjera pri buildu uključuju i testove sajta.
- Android: `lintDebug testDebugUnitTest assembleDebug` uspješno; 4 Kotlin testa, 0 lint grešaka, 35 upozorenja (pretežno stil, prevodi i održavanje).
- Edge E2E: dobrodošlica, native status, automatsko pokretanje aplikacije, lokalni MP4/HLS, MP3, objava u feedu, tok s kolačićima, desni klik, odbijanje LIVE i DRM oznaka — uspješno.
- E2E je koristio poseban privremeni profil i folder s izmišljenim medijima. Omotač izvan repoa napravio je rezervu i na kraju vratio identičan sadržaj native-host fajlova i svih šest ranijih HKCU vrijednosti.
- Stvarni Edge prikaz lokalnog sajta: Android kartica je odabrana preko linka, APK dugme je prije koraka, tamni izgled i animacije su sačuvani. Generator i testovi provjeravaju svih pet jezika.
- Izolovano okruženje blokiralo je privremene fajlove i lokalne HTTP probe, pa je završni discover pokrenut izvan njega, s privremenim folderom u `Build/quality-review-tests`. Te blokade nisu pripisane aplikaciji.
- Telefon i macOS nisu ručno testirani. Postojeći Store paket nije mijenjan niti je napravljen novi javni paket.

## Nastavak pregleda — stanje ekrana i izbor platforme

- Android: `MainState.kt` zadržava navigaciju, uneseni link, rezultat i čitanje kroz rotaciju/promjenu jezika,
  bez reference na staru aktivnost. Novi link poništava stari zahtjev i njegov zakasnjeli rezultat. Događaj za brzo
  preuzimanje troši se jednom; `MainActivity` ne obrađuje stari Share intent pri obnovi, a novi prima preko `onNewIntent`.
- Poslije sistemskog gašenja procesa Android obnavlja mali Bundle (link, glavni ekran, kartica istorije, dostignuća),
  a rezultat ponovo čita s mreže ako je bio otvoren. Tada nema automatskog brzog preuzimanja. Bundle ne sadrži
  video-listu, kolačiće ni potvrdu 18+; pretjeran unos preko 8192 znaka se ne čuva. Potpuno zatvaranje/force-stop
  nije trajno čuvanje sesije. Pristup prati [Androidove preporuke](https://developer.android.com/topic/libraries/architecture/saving-states).
- Ekrani kvaliteta i plejliste koriste saveable primitive za izbor formata/isječka i indekse odabranih stavki.
  Dijalog i potvrda za sadržaj 18+ ostaju samo u memoriji trenutnog ekrana; rotacija traži novi klik/potvrdu.
  Ako se pri ponovnom čitanju promijene stavke ili njihov redoslijed, otisak liste poništava stari izbor;
  stari indeks ne smije označiti neki drugi video. Korisnik tada bira stavke ponovo.
- Sajt: izbor Windows/macOS/Android u uvodu prati sistem posjetioca uz ručni izbor. Glavno dugme i dugme u
  zaglavlju vode na odgovarajući EXE/DMG/APK; zahtjevi i instalacijske kartice prate isti izbor. Postojeća animacija
  desktop aplikacije je sačuvana. Svih pet jezika ima nove tekstove; veličina Windows instalera prikazuje se samo za Windows.
- Bez JavaScripta sva tri paketa i pune upute ostaju dostupni. Microsoft Store dugme ostaje uslovljeno `STORE_LIVE`,
  a nakon uključenja vidljivo je samo uz Windows izbor. U privatnosti na svih pet jezika opisano je lokalno čuvanje Android ekrana.
- Ručna Android proba još je potrebna prije izdavanja: rotirati tokom čitanja i na izboru formata, promijeniti jezik,
  vratiti aplikaciju nakon sistemskog gašenja procesa i provjeriti da isti Share poziv ne napravi drugi posao.
  Za probu 18+ koristiti lokalni kontrolisani rezultat; potvrda se mora tražiti iznova.
- Završna provjera nastavka: puni Python discover 447 testova (2 preskočena), Node dodatak/sajt 31/31;
  zasebno 35/35 testova sajta i pravnih dokumenata poslije dopune privatnosti. Lokalni Edge sa posebnim profilom:
  Windows 1440 px, Mac 1280 px, Android 390 px i njemački 320 px; nema horizontalnog preliva ni JS izuzetaka,
  dugmad/upute prate izbor, animacije rade, reduced-motion ih gasi, bez JS-a postoje sva tri paketa.
  Snimci i privremena skripta su izvan repoa u `Build/quality-review-tests/platform-site`.
  Konačni Android `lintDebug testDebugUnitTest assembleDebug` je uspješan: 10 Kotlin testova,
  0 lint grešaka i istih 35 upozorenja kao u početnoj provjeri. Telefon nije instaliran niti ručno testiran.

## Prijedlozi za sljedeći korak

| Prijedlog | Korist | Posao | Rizik / uslov |
|---|---|---|---|
| Poseban Android demo uz novi izbor platforme na sajtu | Posjetilac telefona vidi stvarni mobilni interfejs; trenutna sačuvana animacija prikazuje desktop. | Srednje, oko 1 dan s provjerom svih pet jezika. | Nizak; koristiti snimke aktuelnog Android dizajna, bez izmišljenih funkcija. |
| Ručna Android matrica rotacije, promjene jezika i obnove procesa | Provjerava pripremljenu obnovu ekrana na stvarnom telefonu i hvata razlike proizvođača. | Malo, oko 1 sat po uređaju. | Potreban slobodan telefon i lokalni kandidat; test ne smije ponoviti preuzimanje niti trajno odobriti sadržaj 18+. |
| Vidljiv izbor „Koristi prijavu sa sajta” u dodatku | Dozvola za kolačiće traži se tek kada korisnik želi preuzimanje iza prijave. | Srednje, oko 1 dan plus E2E. | Srednji; sačuvati postojeći rad privatnih videa i pravilo samo za domen izvora. |
| Trajna izolacija native registracije u E2E alatu | Svaka buduća proba automatski čuva stvarnu Store/instaler vezu; trenutni runner bez omotača je prepisuje razvojnim hostom. | Malo do srednje. | Provjeriti i scenario kada ranija registracija ne postoji; ne brisati naslijepo završno ime hosta zbog poznatog Windows problema s ponovnom upotrebom putanje. |
| CMD interfejs za link, format i izlazni folder | Skripte i napredni korisnici koriste isti provjereni mehanizam bez otvaranja GUI-ja. | Srednje, oko 2–3 dana za prvi upotrebljiv obim. | Nizak do srednji; jasni izlazni kodovi, prekid i poštovanje postojećih provjera. |

Procjene su orijentacione, bez plaćenih servisa. Prije narednog izdanja potrebno je ponoviti provjeru konačnog paketa i ručnu Android probu na slobodnom telefonu.
