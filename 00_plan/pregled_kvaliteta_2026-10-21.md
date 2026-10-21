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

## Prijedlozi za sljedeći korak

| Prijedlog | Korist | Posao | Rizik / uslov |
|---|---|---|---|
| Izbor Windows / macOS / Android uz glavno dugme sajta i prikaz odgovarajuće aplikacije | Posjetilac telefona odmah vidi odgovarajuće preuzimanje; zadržati ručni izbor i sadašnju animaciju. | Srednje, oko 1–2 dana s pet jezika i mobilnim prikazom. | Nizak; odluka o rasporedu i priprema Android demoa. |
| Sačuvati Android ekran, uneseni link i izbor pri ponovnom kreiranju aktivnosti | Manje ponovnog unosa nakon rotacije, promjene jezika ili vraćanja procesa. Trenutni podaci su polja aktivnosti; gubitak treba potvrditi na uređaju. | Srednje, oko 1–2 dana. | Srednji; ne smije ponoviti automatsko preuzimanje iz istog Share intenta niti sačuvati potvrdu 18+. |
| Vidljiv izbor „Koristi prijavu sa sajta” u dodatku | Dozvola za kolačiće traži se tek kada korisnik želi preuzimanje iza prijave. | Srednje, oko 1 dan plus E2E. | Srednji; sačuvati postojeći rad privatnih videa i pravilo samo za domen izvora. |
| Trajna izolacija native registracije u E2E alatu | Svaka buduća proba automatski čuva stvarnu Store/instaler vezu; trenutni runner bez omotača je prepisuje razvojnim hostom. | Malo do srednje. | Provjeriti i scenario kada ranija registracija ne postoji; ne brisati naslijepo završno ime hosta zbog poznatog Windows problema s ponovnom upotrebom putanje. |
| CMD interfejs za link, format i izlazni folder | Skripte i napredni korisnici koriste isti provjereni mehanizam bez otvaranja GUI-ja. | Srednje, oko 2–3 dana za prvi upotrebljiv obim. | Nizak do srednji; jasni izlazni kodovi, prekid i poštovanje postojećih provjera. |

Procjene su orijentacione, bez plaćenih servisa. Prije narednog izdanja potrebno je ponoviti provjeru konačnog paketa i ručnu Android probu na slobodnom telefonu.
