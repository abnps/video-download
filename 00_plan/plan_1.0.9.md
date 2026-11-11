# Plan 1.0.9 (stanje 9.11.2026)

Verzija NIJE povećana (`videodl/__init__.py` ostaje 1.0.8 do Ahmedovog „objavi").

## Već urađeno za 1.0.9
- Izgled „Sada i sljedeće" (Ahmed potvrdio 8.11.2026): boje i pozadina kao na sajtu, kartica „Sada preuzima"
  (sličica, velika traka s fazama, brzina, preostalo vrijeme, grafikon brzine, zaustavi), lista ispod je „Sljedeće",
  statusna traka sa stanjem zaštite od blokade i „Danas".
- Kartica ima puni i sažeti oblik (nizak prozor); prozor se ne može smanjiti toliko da se kartice preklope;
  standardni prozor 900×640; kad je jedini video u kartici, lista poziva da se doda još.
- Zaštita od blokade: link dodat usred predaha odmah dobije karticu s odbrojavanjem (ranije je čekao bez poruke);
  isključivanje zaštite odmah prekida razmake i predahe (i na Androidu), čekanje poslije stvarne blokade ostaje.
- Tamna tema: polja za unos, liste i meniji imaju boju kartice (ranije su se stapali s pozadinom).
- Licenca GNU GPL-3.0: `LICENSE`, licencni ugovor (5 jezika), „O programu", Android Licence, sajt, winget opis.

## Bilješke za „Šta je novo" (prepisati u `videodl/changelog.py` pri izdanju, s datumom objave)
Bez imena video sajtova (FORBIDDEN u `tools/build_site.py`).

- bs:
  - „Novi izgled glavnog prozora u bojama sajta: kartica „Sada preuzima" pokazuje video koji se upravo preuzima,
    s velikom trakom, brzinom, preostalim vremenom i grafikonom brzine; ispod je red onoga što slijedi."
  - „Zaštita od blokade: link dodat usred pauze odmah pokaže koliko se još čeka, a isključivanje zaštite pauzu
    prekida odmah."
  - „Video Download je sada slobodan softver otvorenog koda (GNU GPL-3.0)."
- en:
  - "A new look for the main window in the colours of the site: the “Downloading now” card shows the video being
    downloaded, with a big progress bar, speed, time left and a speed graph; below is the queue of what comes next."
  - "Block protection: a link added during a pause shows right away how long the wait is, and turning protection
    off ends the pause immediately."
  - "Video Download is now free, open-source software (GNU GPL-3.0)."
- de:
  - „Neues Aussehen des Hauptfensters in den Farben der Website: Die Karte „Wird gerade geladen“ zeigt das Video,
    das gerade geladen wird, mit großem Fortschrittsbalken, Geschwindigkeit, Restzeit und Geschwindigkeitsgrafik;
    darunter steht die Warteschlange."
  - „Schutz vor Sperren: Ein Link, der während einer Pause hinzukommt, zeigt sofort, wie lange noch gewartet wird,
    und das Ausschalten des Schutzes beendet die Pause sofort."
  - „Video Download ist jetzt freie Open-Source-Software (GNU GPL-3.0)."
- es:
  - «Nuevo aspecto de la ventana principal con los colores del sitio: la tarjeta «Descargando ahora» muestra el
    vídeo que se está descargando, con una barra grande, velocidad, tiempo restante y un gráfico de velocidad;
    debajo está la cola de lo que sigue.»
  - «Protección contra bloqueos: un enlace añadido durante una pausa muestra enseguida cuánto falta, y desactivar
    la protección termina la pausa al instante.»
  - «Video Download es ahora software libre de código abierto (GNU GPL-3.0).»
- fr:
  - « Nouvel aspect de la fenêtre principale aux couleurs du site : la carte « En cours de téléchargement » montre
    la vidéo en cours, avec une grande barre, la vitesse, le temps restant et un graphique de vitesse ; en dessous,
    la file de ce qui suit. »
  - « Protection contre les blocages : un lien ajouté pendant une pause affiche tout de suite l’attente restante, et
    désactiver la protection met fin à la pause immédiatement. »
  - « Video Download est désormais un logiciel libre et open source (GNU GPL-3.0). »

## Pri izdanju 1.0.9 (pored koraka iz README-ja)
- Novi snimci glavnog prozora za sajt (`tools/site_screenshots.py`) i za Store (`tools/store_screenshots.py`): sada
  prikazuju stari izgled.
- Dodatak za browser: licenca na stranicama u Edge i Firefox prodavnici (GPL-3.0) pri prvoj sljedećoj izmjeni dodatka.
- Build: Node 24.14.1 na početak PATH-a (vidi AGENTS.md).
- Store se ažurira rjeđe (pravilo 25.10.2026): 1.0.9 ide u Store ako Ahmed tako odluči.

## Kandidati (čekaju Ahmedovu odluku)
- Pregled linka prije preuzimanja i plejlista kao grupa s vlastitom trakom (dio demonstracije od 7.11.2026).
- Program pamti veličinu prozora.
- „Ocijeni u Microsoft Storeu" jednom, poslije npr. 20 preuzimanja (Store stranica nema nijednu ocjenu).
- Crtane ikonice umjesto emoji znakova (Postavke, statusna traka): na Linuxu bez emoji fonta su kvadratići.
- Kartica „Sada preuzima" i na Androidu; Android „Nastavi kasnije" i mjesečni pregled kao slika.
- Novije biblioteke u paketu: yt-dlp 2026.10.26 (u paketu 2026.8.19, i Android `build.gradle.kts`), certifi,
  curl_cffi 0.17, PyInstaller 6.22.3; mijenja globalni Python i `tools/build-lock.json`.
- Dodatak: u popupu ime sajta umjesto naslova taba kad na stranici nema videa (nova provjera u prodavnicama).
