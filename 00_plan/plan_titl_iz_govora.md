# Plan: titl iz govora (računar) — stanje 14.11.2026

**Urađeno za 1.0.9** (Ahmed 14.11.2026: „Napravi to u 1.0.9"): `videodl/speech.py`, `videodl/speech_dialogs.py`,
postavka u Postavke → Uz video, korak u `download.py`, pregled i upis u `gui.py`, testovi `test_speech*.py`.
Za sada samo procesor (CPU); NVIDIA ubrzanje (CUDA, još ~1 GB naknadno) ostaje otvoreno.

Kad video nema titl (ni na jeziku programa, ni engleski, ni na izvornom jeziku), program ga može napraviti sam
iz govora (faster-whisper, model large-v3-turbo). Android za sada bez toga (APK 30 MB, spora obrada).

## Proba 14.11.2026 (Build/proba-titl)
- Video 10:46, propovijed na bosanskom s arapskim citatima, YouTube nema nijedan titl ni automatski.
- Model „small" (0,46 GB): neupotrebljiv za bosanski. large-v3-turbo (1,6 GB): bosanski uglavnom tačan, greške u
  pojedinim riječima („Laga vrećo, cijene džematlije"), arapski citati po sluhu latinicom.
- Prvi prolaz je bosanski dio poslije dove pisao arapskim pismom; `condition_on_previous_text=False` popravlja.
- Izmišljen tekst preko tišine/učenja („Allah", „Al-Fatiha"): treba ga izbaciti (malo vjerovatan govor).
- Brzina: CPU (Ryzen 9 7945HX, int8) 17 min za 11 min govora; GPU (CUDA) procjena 1–2 min; upis u sliku 52 s.

## Odluke (Ahmed)
- Model se NE pakuje u program; preuzima se naknadno, tek kad korisnik uključi funkciju (14.11.2026).
- Preuzimanje modela ima traku napretka (procenat, MB, brzina, preostalo vrijeme, otkaži), da korisnik zna da se
  nešto dešava (14.11.2026).
- Opisi svuda kažu da model može praviti greške (14.11.2026) — tekstovi ispod.

## Kako radi (prijedlog)
1. Postavka „Titl iz govora" (isključena). Uključivanje pita za preuzimanje modela (1,6 GB) i pokaže traku.
2. Video bez titla: poslije preuzimanja traka „Pravim titl iz govora · 40 %", s procjenom trajanja unaprijed.
3. NVIDIA kartica ako je ima (CUDA biblioteke ~1 GB, isto naknadno), inače procesor.
4. Podešavanja: `language` = jezik programa ili jezik videa, `condition_on_previous_text=False`, VAD, početni
   tekst/riječi s prednošću na jeziku videa, izbacivanje malo vjerovatnih redova.
5. Prije upisa u sliku: prozor s redovima titla (vrijeme + tekst) za ispravku, dugme „Upiši titl".
6. Fajl titla dobija oznaku u imenu, npr. `Naslov [id].bs.iz-govora.srt`, da se razlikuje od titla sa sajta.

## Tekstovi: model može praviti greške (5 jezika)

### Opis postavke „Titl iz govora"
- bs: „Kad video nema titl, program ga napravi iz govora. Titl pravi računar sam, pa može imati grešaka,
  naročito u imenima i stranim riječima."
- en: "If a video has no subtitles, the app creates them from speech. They're made automatically, so they can
  contain mistakes, especially in names and foreign words."
- de: „Hat ein Video keine Untertitel, erstellt das Programm sie aus der Sprache. Sie entstehen automatisch und
  können Fehler enthalten, besonders bei Namen und Fremdwörtern."
- es: «Si un vídeo no tiene subtítulos, el programa los crea a partir del habla. Se generan automáticamente, así
  que pueden tener errores, sobre todo en nombres y palabras extranjeras.»
- fr: « Si une vidéo n'a pas de sous-titres, le programme les crée à partir de la parole. Ils sont générés
  automatiquement et peuvent contenir des erreurs, surtout dans les noms et les mots étrangers. »

### Pitanje prije preuzimanja modela
- bs: „Za titl iz govora treba preuzeti model za prepoznavanje govora (1,6 GB), samo jednom. Prepoznavanje nije
  savršeno: titl može imati grešaka. Preuzeti?"
- en: "Subtitles from speech need a speech-recognition model (1.6 GB), downloaded once. Recognition isn't perfect:
  the subtitles may contain mistakes. Download it?"
- de: „Für Untertitel aus der Sprache wird ein Spracherkennungsmodell (1,6 GB) einmalig heruntergeladen. Die
  Erkennung ist nicht perfekt: Die Untertitel können Fehler enthalten. Herunterladen?"
- es: «Para crear subtítulos a partir del habla hay que descargar una vez un modelo de reconocimiento de voz
  (1,6 GB). El reconocimiento no es perfecto: los subtítulos pueden tener errores. ¿Descargarlo?»
- fr: « Pour créer des sous-titres à partir de la parole, un modèle de reconnaissance vocale (1,6 Go) est
  téléchargé une seule fois. La reconnaissance n'est pas parfaite : les sous-titres peuvent contenir des erreurs.
  Le télécharger ? »

### Prozor za pregled titla (prije upisa u sliku)
- bs: „Ovaj titl je napravljen automatski iz govora i može imati grešaka. Ispravi pogrešne riječi, pa klikni
  „Upiši titl"."
- en: "These subtitles were created automatically from speech and may contain mistakes. Fix any wrong words, then
  click “Add subtitles”."
- de: „Diese Untertitel wurden automatisch aus der Sprache erstellt und können Fehler enthalten. Korrigiere falsche
  Wörter und klicke dann auf „Untertitel einfügen“."
- es: «Estos subtítulos se crearon automáticamente a partir del habla y pueden tener errores. Corrige las palabras
  incorrectas y haz clic en «Añadir subtítulos».»
- fr: « Ces sous-titres ont été créés automatiquement à partir de la parole et peuvent contenir des erreurs.
  Corrige les mots erronés, puis clique sur « Ajouter les sous-titres ». »

### Kratka oznaka uz gotov video u listi (savjet/oblačić)
- bs: „Titl iz govora — može imati grešaka" · en: "Subtitles from speech — may contain mistakes" ·
  de: „Untertitel aus der Sprache – kann Fehler enthalten" · es: «Subtítulos del habla: pueden tener errores» ·
  fr: « Sous-titres de la parole : peuvent contenir des erreurs »

## Otvoreno
- Probati početni tekst/riječi s prednošću na prve 3 minute probnog videa (koliko pomažu).
- Model dodatno treniran na hrvatskom/srpskom (npr. ParlaSpeech): provjeriti licencu i kvalitet.
- Licence: faster-whisper (MIT), Whisper modeli (MIT), CTranslate2 (MIT) — upisati u „O programu".
