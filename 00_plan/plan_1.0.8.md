# Plan 1.0.8 (pregled 7.–8.11.2026)

Stanje: izmjene su u `main`, verzija NIJE povećana (`videodl/__init__.py` ostaje 1.0.7 do Ahmedovog „objavi").

## Već u main
- Računar: novi izgled prozora Postavke (stranice lijevo, kartice s objašnjenjem, prekidači; čitač ekrana).
- Računar: veza s browserom bez čekanja od ~2 s poslije pada programa ili gašenja računara dok je radio.
- Android: objašnjenje (i) i za red „Mjesečni pregled" u Postavkama.
- Čišćenje: nekorišten tekst `settings.pacing`; testovi bez lažnih ispisa grešaka.

## Bilješke za „Šta je novo" (prepisati u `videodl/changelog.py` pri izdanju, s datumom objave)
Bez imena video sajtova (FORBIDDEN u `tools/build_site.py`).

- bs:
  - „Postavke na računaru imaju novi izgled: stranice lijevo, a svaka opcija ima kratko objašnjenje i prekidač."
  - „Dodatak u browseru se odmah povezuje s programom i poslije naglog gašenja programa ili računara."
- en:
  - "Settings on the computer have a new look: pages on the left, and every option has a short explanation and a switch."
  - "The browser extension connects to the app right away, even after the app or computer was shut down abruptly."
- de:
  - „Die Einstellungen am Computer haben ein neues Aussehen: Seiten links, und jede Option hat eine kurze Erklärung und einen Schalter."
  - „Die Browser-Erweiterung verbindet sich sofort mit dem Programm, auch nachdem Programm oder Computer abrupt beendet wurden."
- es:
  - «Los Ajustes del ordenador tienen un nuevo aspecto: páginas a la izquierda, y cada opción tiene una breve explicación y un interruptor.»
  - «La extensión del navegador se conecta al programa al instante, incluso después de que el programa o el ordenador se cerraran de golpe.»
- fr:
  - « Les Paramètres sur l’ordinateur ont un nouvel aspect : pages à gauche, et chaque option a une courte explication et un interrupteur. »
  - « L’extension du navigateur se connecte tout de suite au programme, même après un arrêt brutal du programme ou de l’ordinateur. »

## Kandidati (čekaju Ahmedovu odluku)
- Novije biblioteke u paketu: yt-dlp 2026.10.26 (u paketu 2026.8.19, i Android `build.gradle.kts`), certifi, curl_cffi 0.17,
  PyInstaller 6.22.3; mijenja globalni Python i `tools/build-lock.json`.
- Android „Nastavi kasnije" (traži trajni red čekanja) i dijeljenje mjesečnog pregleda kao slike.
- Novi izgled glavnog prozora (demo „Sada i sljedeće" 7.11.2026).
- Dodatak: u popupu ime sajta umjesto naslova taba kad na stranici nema videa (nova provjera u prodavnicama).

## Pri izdanju
Store se ažurira rjeđe (pravilo 25.10.2026): 1.0.8 ide u Store samo ako Ahmed tako odluči.
Build: Node 24.14.1 na početak PATH-a (vidi AGENTS.md „Stanje 7.11.2026").
