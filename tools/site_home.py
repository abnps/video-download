"""Početna stranica sajta (redizajn 26.9.2026, Ahmed: „po uzoru na windows.com, interaktivan sa animacijama").

Jedan šablon za svih 5 jezika; tekstovi su u HOME, nazivi dugmadi programa dolaze iz videodl/i18n.py (isti kao u
programu). Sajt nema kolačiće ni tuđe skripte: animacije su CSS + assets/site.js, i gase se kod
`prefers-reduced-motion`. Bez Microsoftovih znakova i slika — samo stil.
"""

import html

# Ikona u zaglavlju (Ahmed 2.10.2026: „animiraj ikonicu kao simulacija downloada"): isti oblik i boja kao
# assets/icon.png, ali SVG — strelica se spusti u crtu, crta se napuni kao traka preuzimanja, pa iznova.
# Animacija je samo CSS (.brand-icon u site.css); bez nje, i uz prefers-reduced-motion, ikona miruje.
BRAND_ICON = ('<svg class="brand-icon" viewBox="0 0 128 128" width="28" height="28" aria-hidden="true">'
              '<rect width="128" height="128" rx="28" fill="#6c4ce0"/>'
              '<g class="bi-arrow" fill="none" stroke="#fff" stroke-width="13" stroke-linecap="round" '
              'stroke-linejoin="round"><path d="M64 27V80"/><path d="M38 56 64 82 90 56"/></g>'
              '<path class="bi-track" d="M35.5 99.5H92.5" stroke="#fff" stroke-width="13" stroke-linecap="round"/>'
              '<path class="bi-fill" d="M35.5 99.5H92.5" stroke="#fff" stroke-width="13" stroke-linecap="round" '
              'pathLength="100"/></svg>')
import json

# Sidra sekcija (ista na svim jezicima; nazivi su u HOME[lang]["nav"]).
ANCHORS = ("features", "extension", "install", "news", "help", "support")

ICONS = {
    "download": '<path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 19h14"/>',
    "mp4": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/>',
    "audio": '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    "copy": '<rect x="8" y="3" width="8" height="4" rx="1"/><path d="M8 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>',
    "playlists": '<path d="M4 6h16M4 12h16M4 18h10"/>',
    "clips": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>',
    "theme": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "safe": '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
}

# Boje sličica u demou (iste na svim jezicima); naslovi su u HOME[lang]["demo_titles"].
DEMO_ROWS = (("12:34", 46.0, 9.6, "#3d7a5a", "#2b5a82", "best", False),
             ("52:01", 38.2, 11.2, "#7a3d5c", "#a0306d", "1080p", False),
             ("45:10", 28.4, 8.1, "#3d5c7a", "#5b3fd1", "720p", False),
             ("1:13:08", 7.1, 2.8, "#7a6a3d", "#7a3d5c", "mp3", True))

HOME = {
    "en": {
        "promise": ('No account', 'No daily limit', 'Your links never reach us'),
        "a11y": ('Demo', 'Pause animation', 'Play animation', 'Menu', 'Added: {t}', 'Finished: {t}', 'Demo of the app window (not a real download)'),
        "share": ('Share', 'Copy', 'Copied', 'Tell a friend who needs it.', 'Share Video Download', 'More…', 'Close'),
        "title": "Video Download — free video and audio downloader for Windows and Mac",
        "description": "Free app for Windows and Mac for downloading video (MP4) and audio (MP3). No ads, no tracking, in 5 languages.",
        "nav": ("Features", "Extension", "Install", "What's new", "Help", "♥ Support"),
        "download_short": "Download", "new": "New", "eyebrow": "<b>Android and macOS</b> in beta",
        "h1": ("Video and audio.", "In one click."),
        "lead": "A free app for Windows and Mac: MP4 in full quality or MP3, straight from your browser or from a copied link.",
        "win_btn": "Download for Windows", "win_req": "Windows 10 and 11 (64-bit)", "install_help": "installation help",
        "note": "The app is meant for your own videos, content you have the author's permission for, and content under a free "
                "license. By downloading you accept the <a href=\"terms.html\">Terms of use</a>. DRM-protected content is not downloaded.",
        "try_it": "Try it: click <b>{paste}</b>.",
        "stats": ("supported sites", "languages", "ads and trackers", "downloads at once"),
        "features": ("Features", "Everything you need,<br>nothing you don't.",
                     "A simple window, with everything you expect from a good downloader underneath."),
        "tiles": {
            "mp4": ("MP4 up to the best quality", "Best, 1080p, 720p or 480p. Picture and sound are merged into an MP4 (H.264/AAC when the site offers it) that plays on most devices."),
            "audio": ("Audio only: MP3 or M4A", "For lectures, podcasts and music. A finished MP4 turns into an MP3 with one button."),
            "copy": ("Copy a link, done", "The app notices a copied link and adds it to the queue."),
            "playlists": ("Playlists, several at once", "Whole playlists, up to 4 downloads at the same time, automatic retry when the connection drops."),
            "clips": ("Clips, subtitles, cover art", "Just a part of a video, subtitles in the MP4 and the thumbnail as the file's cover."),
            "theme": ("Light and dark theme", "Or same as your system. Progress on the taskbar and a notification at the end."),
            "safe": ("Always up to date, and safe", "The app checks for new versions itself, updates the part that reads websites without "
                     "reinstalling. On Windows and Mac it installs only updates digitally signed by us."),
        },
        "chips": ("5 languages", "No account", "No ads", "No tracking", "Signed updates on Windows"),
        "shot_alt": "The Video Download window with four downloads",
        "extension": ("Browser extension", "Download what's playing.",
                      "Play a video, click the icon, done. Or right-click any link or video. The app starts by itself if it isn't running.",
                      ("Firefox: one click, signed by Mozilla, updates itself",
                       "Edge and Chrome: loaded once from the app folder",
                       "Live streams and DRM-protected video are not downloaded"),
                      "How to install the extension →"),
        "popup": ("the app is running", "Download the playing video", "Download as MP3 (audio only)", "Detected video streams",
                  "Video Download extension"),
        "how": ("How it works", "Your first file in a few minutes.", "Install once, then just copy links.",
                (("Install", "No administrator needed, adds nothing else to your computer."),
                 ("Add a link", "Copy a link, click “Paste”, or use the extension."),
                 ("Download", "MP4 or MP3, then “Download”. The file waits in the Video&nbsp;Download folder."))),
        "install": ("Install", "First start, step by step.",
                    "The app isn't signed with a paid certificate yet, so your system asks once. Updates from inside the app don't.",
                    "System",
                    "<b>Windows may show “Windows protected your PC”.</b> Make sure the file comes from this site, then click "
                    "<b>More info</b> and <b>Run anyway</b>."),
        "dialog": ("Windows protected your PC", "SmartScreen prevented an unrecognized app from starting.", "More info",
                   "Don't run", "App: VideoDownload-Setup.exe<br>Publisher: Unknown publisher", "Run anyway"),
        "news": ("What's new", "Better every week.", "The same list as in the app (Help → What's new)."),
        "support": ("Free, for everyone", "The app is free.",
                    "No ads, no tracking and no “premium” version. If it's useful to you, you can support its development "
                    "voluntarily. A contribution unlocks nothing: the app is the same for everyone.",
                    "♥ Support via PayPal", "QR code for a PayPal contribution", "Scan with your phone camera"),
        "help": ("Help", "Questions?",
                 "If something doesn't work: in the app use Help → Save a problem report, then <a href=\"{issue}\">report the "
                 "problem</a>. Reports are public: don't include passwords or personal data."),
        "faq": (("A video suddenly won't download.", "Websites change often. Help → Update the site reader (yt-dlp), then try again."),
                ("Why aren't live streams downloaded?", "A live stream has no end, so the download would never finish. Download it "
                 "after it ends and the recording is published."),
                ("What does the app send to the internet?", "Only what's needed: the link you download goes to that website, and "
                 "update checks go to GitHub and PyPI. No accounts, statistics or tracking."),
                ("Is it safe?", "The code is public on GitHub, every installer has a SHA-256 checksum, and the app installs only "
                 "updates digitally signed by us, on Windows and on Mac.")),
        "demo_titles": ("Mountain hike – Prokosko lake (4K)", "My live concert – filmed from the crowd",
                        "Lecture: photography basics", "Podcast #12 – a talk about travel"),
        "demo": ("Downloading · {p}% · {v} MB/s · {s} s left", "."),
    },
    "bs": {
        "promise": ('Bez naloga', 'Bez dnevnog ograničenja', 'Tvoji linkovi ne idu nama'),
        "a11y": ('Demonstracija', 'Pauziraj animaciju', 'Pokreni animaciju', 'Meni', 'Dodano: {t}', 'Završeno: {t}', 'Demonstracija prozora programa (nije pravo preuzimanje)'),
        "share": ('Podijeli', 'Kopiraj', 'Kopirano', 'Javi prijatelju kome treba.', 'Podijeli Video Download', 'Više…', 'Zatvori'),
        "title": "Video Download — besplatan program za video i zvuk za Windows i Mac",
        "description": "Besplatan program za Windows i Mac za preuzimanje videa (MP4) i zvuka (MP3). Bez reklama, bez praćenja, na 5 jezika.",
        "nav": ("Funkcije", "Dodatak", "Instalacija", "Šta je novo", "Pomoć", "♥ Podrži"),
        "download_short": "Preuzmi", "new": "Novo", "eyebrow": "<b>Android i macOS</b> u probnoj fazi",
        "h1": ("Video i zvuk.", "Jednim klikom."),
        "lead": "Besplatan program za Windows i Mac: MP4 u punom kvalitetu ili MP3, direktno iz browsera ili iz kopiranog linka.",
        "win_btn": "Preuzmi za Windows", "win_req": "Windows 10 i 11 (64-bit)", "install_help": "pomoć za instalaciju",
        "note": "Program je namijenjen tvojim vlastitim videima, sadržaju uz dozvolu autora i sadržaju pod slobodnom licencom. "
                "Preuzimanjem prihvataš <a href=\"terms.html\">Uslove korištenja</a>. Sadržaj zaštićen DRM-om se ne preuzima.",
        "try_it": "Probaj: klikni <b>{paste}</b>.",
        "stats": ("podržanih sajtova", "jezika", "reklama i praćenja", "preuzimanja odjednom"),
        "features": ("Funkcije", "Sve što treba,<br>ništa viška.",
                     "Jednostavan prozor, a ispod njega sve što očekuješ od dobrog programa za preuzimanje."),
        "tiles": {
            "mp4": ("MP4 do najboljeg kvaliteta", "Najbolji, 1080p, 720p ili 480p. Slika i zvuk se sami spajaju u MP4 (H.264/AAC kad ga sajt nudi) koji se pušta na većini uređaja."),
            "audio": ("Samo zvuk: MP3 ili M4A", "Za predavanja, podcaste i muziku. Gotov MP4 se jednim dugmetom pretvara u MP3."),
            "copy": ("Kopiraj link i gotovo", "Program sam primijeti kopiran link i doda ga u red."),
            "playlists": ("Plejliste, više odjednom", "Cijele plejliste, do 4 preuzimanja istovremeno, automatski novi pokušaj kad pukne veza."),
            "clips": ("Isječak, titlovi, omot", "Samo dio videa, titlovi u MP4 i sličica kao omot fajla."),
            "theme": ("Svijetla i tamna tema", "Ili kao sistem. Napredak na traci zadataka i obavještenje na kraju."),
            "safe": ("Uvijek ažuran i siguran", "Program sam provjerava nove verzije, ažurira dio koji čita sajtove bez ponovne "
                     "instalacije. Na Windowsu i Macu instalira samo ažuriranja koja smo mi digitalno potpisali."),
        },
        "chips": ("5 jezika", "Bez naloga", "Bez reklama", "Bez praćenja", "Potpisana ažuriranja na Windowsu"),
        "shot_alt": "Prozor programa Video Download sa četiri preuzimanja",
        "extension": ("Dodatak za browser", "Preuzmi ono što se pušta.",
                      "Pusti video, klikni ikonu i gotovo. Ili desni klik na bilo koji link ili video. Program se sam pokrene ako nije otvoren.",
                      ("Firefox: jedan klik, potpisala Mozilla, sam se ažurira",
                       "Edge i Chrome: učitava se jednom iz foldera programa",
                       "Prenos uživo i video zaštićen DRM-om se ne preuzimaju"),
                      "Kako se instalira dodatak →"),
        "popup": ("aplikacija radi", "Preuzmi video koji se pušta", "Preuzmi kao MP3 (samo zvuk)", "Pronađeni video tokovi",
                  "Dodatak Video Download"),
        "how": ("Kako radi", "Prvi fajl za par minuta.", "Instaliraj jednom, pa samo kopiraj linkove.",
                (("Instaliraj", "Ne traži administratora i ne dodaje ništa drugo na računar."),
                 ("Dodaj link", "Kopiraj link, klikni „Zalijepi“ ili koristi dodatak."),
                 ("Preuzmi", "MP4 ili MP3, pa „Preuzmi“. Fajl čeka u folderu Video&nbsp;Download."))),
        "install": ("Instalacija", "Prvo pokretanje, korak po korak.",
                    "Program još nema plaćeni certifikat, pa sistem jednom pita. Ažuriranja iz programa ne pitaju.",
                    "Sistem",
                    "<b>Windows može prikazati „Windows je zaštitio vaš računar“.</b> Provjeri da je fajl sa ovog sajta, pa klikni "
                    "<b>Više informacija</b> i <b>Ipak pokreni</b>."),
        "dialog": ("Windows je zaštitio vaš računar", "SmartScreen je spriječio pokretanje neprepoznate aplikacije.",
                   "Više informacija", "Ne pokreći", "Aplikacija: VideoDownload-Setup.exe<br>Izdavač: Nepoznat izdavač",
                   "Ipak pokreni"),
        "news": ("Šta je novo", "Svake sedmice bolje.", "Ista lista kao u programu (Pomoć → Šta je novo)."),
        "support": ("Besplatno, za sve", "Program je besplatan.",
                    "Bez reklama, bez praćenja i bez „premium“ verzije. Ako ti koristi, možeš dobrovoljno podržati razvoj. "
                    "Prilog ništa ne otključava: program je isti za sve.",
                    "♥ Podrži preko PayPal-a", "QR kod za PayPal prilog", "Skeniraj kamerom telefona"),
        "help": ("Pomoć", "Pitanja?",
                 "Ako nešto ne radi: u programu Pomoć → Sačuvaj izvještaj o problemu, pa <a href=\"{issue}\">prijavi problem</a>. "
                 "Prijave su javne: ne upisuj lozinke ni lične podatke."),
        "faq": (("Video se odjednom ne preuzima.", "Sajtovi često mijenjaju način rada. Pomoć → Ažuriraj čitač sajtova (yt-dlp), "
                 "pa pokušaj ponovo."),
                ("Zašto se prenos uživo ne preuzima?", "Prenos uživo nema kraja, pa bi preuzimanje trajalo beskonačno. Preuzmi ga "
                 "kad se završi i snimak bude objavljen."),
                ("Šta program šalje na internet?", "Samo ono što je potrebno: link koji preuzimaš ide do tog sajta, a provjera "
                 "ažuriranja ide na GitHub i PyPI. Nema naloga, statistike ni praćenja."),
                ("Da li je siguran?", "Kod je javan na GitHubu, svaki instaler ima SHA-256 zbir, a program instalira samo "
                 "ažuriranja koja smo mi digitalno potpisali, na Windowsu i na Macu.")),
        "demo_titles": ("Planinarska tura – Prokoško jezero (4K)", "Moj koncert uživo – snimak iz publike",
                        "Predavanje: osnove fotografije", "Podcast #12 – razgovor o putovanjima"),
        "demo": ("Preuzimanje · {p}% · {v} MB/s · još {s} s", ","),
    },
    "de": {
        "promise": ('Kein Konto', 'Kein Tageslimit', 'Deine Links landen nicht bei uns'),
        "a11y": ('Demo', 'Animation anhalten', 'Animation abspielen', 'Menü', 'Hinzugefügt: {t}', 'Fertig: {t}', 'Demo des Programmfensters (kein echter Download)'),
        "share": ('Teilen', 'Kopieren', 'Kopiert', 'Erzähl es jemandem, der es braucht.', 'Video Download teilen', 'Mehr…', 'Schließen'),
        "title": "Video Download — kostenloser Video- und Audio-Downloader für Windows und Mac",
        "description": "Kostenlose App für Windows und Mac zum Herunterladen von Video (MP4) und Audio (MP3). Ohne Werbung, ohne Tracking, in 5 Sprachen.",
        "nav": ("Funktionen", "Erweiterung", "Installation", "Neuigkeiten", "Hilfe", "♥ Unterstützen"),
        "download_short": "Herunterladen", "new": "Neu", "eyebrow": "<b>Android und macOS</b> in der Beta",
        "h1": ("Video und Audio.", "Mit einem Klick."),
        "lead": "Eine kostenlose App für Windows und Mac: MP4 in voller Qualität oder MP3, direkt aus dem Browser oder aus einem kopierten Link.",
        "win_btn": "Für Windows herunterladen", "win_req": "Windows 10 und 11 (64 Bit)", "install_help": "Hilfe zur Installation",
        "note": "Die App ist für eigene Videos gedacht, für Inhalte, für die du die Erlaubnis des Urhebers hast, und für Inhalte "
                "unter freier Lizenz. Mit dem Herunterladen akzeptierst du die <a href=\"terms.html\">Nutzungsbedingungen</a>. "
                "DRM-geschützte Inhalte werden nicht heruntergeladen.",
        "try_it": "Probier's aus: klicke auf <b>{paste}</b>.",
        "stats": ("unterstützte Seiten", "Sprachen", "Werbung und Tracker", "Downloads gleichzeitig"),
        "features": ("Funktionen", "Alles, was du brauchst.<br>Nichts, was du nicht brauchst.",
                     "Ein einfaches Fenster – und darunter alles, was du von einem guten Downloader erwartest."),
        "tiles": {
            "mp4": ("MP4 bis zur besten Qualität", "Beste, 1080p, 720p oder 480p. Bild und Ton werden zu einer MP4 zusammengeführt (H.264/AAC, wenn die Seite es anbietet), die auf den meisten Geräten läuft."),
            "audio": ("Nur Ton: MP3 oder M4A", "Für Vorträge, Podcasts und Musik. Eine fertige MP4 wird mit einem Knopf zur MP3."),
            "copy": ("Link kopieren, fertig", "Die App bemerkt einen kopierten Link und fügt ihn der Liste hinzu."),
            "playlists": ("Playlists, mehrere gleichzeitig", "Ganze Playlists, bis zu 4 Downloads gleichzeitig, automatisch ein neuer Versuch, wenn die Verbindung abbricht."),
            "clips": ("Ausschnitte, Untertitel, Cover", "Nur ein Teil eines Videos, Untertitel in der MP4 und das Vorschaubild als Cover der Datei."),
            "theme": ("Helles und dunkles Design", "Oder wie das System. Fortschritt in der Taskleiste und eine Benachrichtigung am Ende."),
            "safe": ("Immer aktuell – und sicher", "Die App sucht selbst nach neuen Versionen, aktualisiert den Teil, der Webseiten "
                     "liest, ohne Neuinstallation. Unter Windows und auf dem Mac installiert sie nur Updates, die wir digital "
                     "signiert haben."),
        },
        "chips": ("5 Sprachen", "Kein Konto", "Keine Werbung", "Kein Tracking", "Signierte Updates unter Windows"),
        "shot_alt": "Das Fenster von Video Download mit vier Downloads",
        "extension": ("Browser-Erweiterung", "Lade herunter, was gerade läuft.",
                      "Video abspielen, auf das Symbol klicken, fertig. Oder Rechtsklick auf einen Link oder ein Video. Läuft die "
                      "App nicht, startet sie von selbst.",
                      ("Firefox: ein Klick, von Mozilla signiert, aktualisiert sich selbst",
                       "Edge und Chrome: einmal aus dem App-Ordner geladen",
                       "Livestreams und DRM-geschützte Videos werden nicht heruntergeladen"),
                      "So installierst du die Erweiterung →"),
        "popup": ("App läuft", "Laufendes Video herunterladen", "Als MP3 herunterladen (nur Ton)", "Gefundene Videostreams",
                  "Erweiterung Video Download"),
        "how": ("So funktioniert's", "Die erste Datei in wenigen Minuten.", "Einmal installieren, dann nur noch Links kopieren.",
                (("Installieren", "Keine Administratorrechte nötig, installiert nichts anderes auf deinem Computer."),
                 ("Link hinzufügen", "Link kopieren, auf „Einfügen“ klicken oder die Erweiterung nutzen."),
                 ("Herunterladen", "MP4 oder MP3, dann „Herunterladen“. Die Datei wartet im Ordner Video&nbsp;Download."))),
        "install": ("Installation", "Der erste Start, Schritt für Schritt.",
                    "Die App hat noch kein kostenpflichtiges Zertifikat, daher fragt dein System einmal nach. Updates aus der App "
                    "heraus fragen nicht.",
                    "System",
                    "<b>Windows zeigt eventuell „Der Computer wurde durch Windows geschützt“.</b> Prüfe, dass die Datei von dieser "
                    "Seite stammt, und klicke dann auf <b>Weitere Informationen</b> und <b>Trotzdem ausführen</b>."),
        "dialog": ("Der Computer wurde durch Windows geschützt",
                   "Von Microsoft Defender SmartScreen wurde der Start einer unbekannten App verhindert.",
                   "Weitere Informationen", "Nicht ausführen",
                   "App: VideoDownload-Setup.exe<br>Herausgeber: Unbekannter Herausgeber", "Trotzdem ausführen"),
        "news": ("Neuigkeiten", "Jede Woche besser.", "Dieselbe Liste wie in der App (Hilfe → Was ist neu)."),
        "support": ("Kostenlos, für alle", "Die App ist kostenlos.",
                    "Ohne Werbung, ohne Tracking und ohne „Premium“-Version. Wenn sie dir nützt, kannst du ihre Entwicklung "
                    "freiwillig unterstützen. Ein Beitrag schaltet nichts frei: Die App ist für alle gleich.",
                    "♥ Über PayPal unterstützen", "QR-Code für einen PayPal-Beitrag", "Mit der Handykamera scannen"),
        "help": ("Hilfe", "Fragen?",
                 "Wenn etwas nicht klappt: in der App Hilfe → Problembericht speichern, dann <a href=\"{issue}\">das Problem "
                 "melden</a>. Meldungen sind öffentlich: keine Passwörter oder persönlichen Daten angeben."),
        "faq": (("Ein Video lässt sich plötzlich nicht mehr herunterladen.", "Webseiten ändern sich oft. Hilfe → Seiten-Reader "
                 "aktualisieren (yt-dlp), dann erneut versuchen."),
                ("Warum werden Livestreams nicht heruntergeladen?", "Ein Livestream hat kein Ende, der Download würde also nie "
                 "fertig. Lade ihn herunter, wenn er vorbei ist und die Aufzeichnung veröffentlicht wurde."),
                ("Was sendet die App ins Internet?", "Nur das Nötige: Der Link, den du herunterlädst, geht an diese Webseite, und "
                 "die Update-Prüfung an GitHub und PyPI. Keine Konten, Statistiken oder Tracking."),
                ("Ist die App sicher?", "Der Code ist öffentlich auf GitHub, jeder Installer hat eine SHA-256-Prüfsumme, und die "
                 "App installiert unter Windows und auf dem Mac nur Updates, die wir digital signiert haben.")),
        "demo_titles": ("Bergwanderung – Prokoško-See (4K)", "Mein Live-Konzert – aus dem Publikum gefilmt",
                        "Vortrag: Grundlagen der Fotografie", "Podcast #12 – ein Gespräch übers Reisen"),
        "demo": ("Herunterladen · {p}% · {v} MB/s · noch {s} s", ","),
    },
    "es": {
        "promise": ('Sin cuenta', 'Sin límite diario', 'Tus enlaces no nos llegan'),
        "a11y": ('Demostración', 'Pausar animación', 'Reanudar animación', 'Menú', 'Añadido: {t}', 'Terminado: {t}', 'Demostración de la ventana del programa (no es una descarga real)'),
        "share": ('Compartir', 'Copiar', 'Copiado', 'Cuéntaselo a quien le sirva.', 'Compartir Video Download', 'Más…', 'Cerrar'),
        "title": "Video Download — descargador gratuito de vídeo y audio para Windows y Mac",
        "description": "Aplicación gratuita para Windows y Mac para descargar vídeo (MP4) y audio (MP3). Sin anuncios, sin rastreo, en 5 idiomas.",
        "nav": ("Funciones", "Extensión", "Instalación", "Novedades", "Ayuda", "♥ Apoyar"),
        "download_short": "Descargar", "new": "Nuevo", "eyebrow": "<b>Android y macOS</b> en beta",
        "h1": ("Vídeo y audio.", "Con un clic."),
        "lead": "Una aplicación gratuita para Windows y Mac: MP4 en calidad completa o MP3, directamente desde el navegador o desde un enlace copiado.",
        "win_btn": "Descargar para Windows", "win_req": "Windows 10 y 11 (64 bits)", "install_help": "ayuda para instalar",
        "note": "La aplicación está pensada para tus propios vídeos, contenido para el que tienes permiso del autor y contenido con "
                "licencia libre. Al descargar aceptas las <a href=\"terms.html\">Condiciones de uso</a>. El contenido protegido con "
                "DRM no se descarga.",
        "try_it": "Pruébalo: pulsa <b>{paste}</b>.",
        "stats": ("sitios compatibles", "idiomas", "anuncios y rastreadores", "descargas a la vez"),
        "features": ("Funciones", "Todo lo que necesitas,<br>nada que sobre.",
                     "Una ventana sencilla y, por debajo, todo lo que esperas de un buen descargador."),
        "tiles": {
            "mp4": ("MP4 hasta la mejor calidad", "La mejor, 1080p, 720p o 480p. Imagen y sonido se unen en un MP4 (H.264/AAC si el sitio lo ofrece) que se reproduce en la mayoría de los dispositivos."),
            "audio": ("Solo audio: MP3 o M4A", "Para clases, pódcasts y música. Un MP4 terminado se convierte en MP3 con un botón."),
            "copy": ("Copia un enlace y listo", "La aplicación detecta un enlace copiado y lo añade a la cola."),
            "playlists": ("Listas, varias a la vez", "Listas de reproducción completas, hasta 4 descargas a la vez y reintento automático si se corta la conexión."),
            "clips": ("Fragmentos, subtítulos, portada", "Solo una parte del vídeo, subtítulos en el MP4 y la miniatura como portada del archivo."),
            "theme": ("Tema claro y oscuro", "O igual que el sistema. Progreso en la barra de tareas y un aviso al final."),
            "safe": ("Siempre al día y seguro", "La aplicación busca nuevas versiones por sí sola, actualiza la parte que lee los "
                     "sitios web sin reinstalar. En Windows y en Mac instala solo actualizaciones firmadas digitalmente por "
                     "nosotros."),
        },
        "chips": ("5 idiomas", "Sin cuenta", "Sin anuncios", "Sin rastreo", "Actualizaciones firmadas en Windows"),
        "shot_alt": "La ventana de Video Download con cuatro descargas",
        "extension": ("Extensión para el navegador", "Descarga lo que se está reproduciendo.",
                      "Reproduce un vídeo, pulsa el icono y listo. O clic derecho en cualquier enlace o vídeo. La aplicación se "
                      "abre sola si no está abierta.",
                      ("Firefox: un clic, firmada por Mozilla, se actualiza sola",
                       "Edge y Chrome: se carga una vez desde la carpeta de la aplicación",
                       "Las emisiones en directo y el vídeo con DRM no se descargan"),
                      "Cómo instalar la extensión →"),
        "popup": ("aplicación abierta", "Descargar el vídeo en reproducción", "Descargar como MP3 (solo audio)",
                  "Flujos de vídeo detectados", "Extensión Video Download"),
        "how": ("Cómo funciona", "Tu primer archivo en pocos minutos.", "Instala una vez y luego solo copia enlaces.",
                (("Instalar", "No necesita administrador y no añade nada más a tu ordenador."),
                 ("Añadir un enlace", "Copia un enlace, pulsa «Pegar» o usa la extensión."),
                 ("Descargar", "MP4 o MP3 y luego «Descargar». El archivo te espera en la carpeta Video&nbsp;Download."))),
        "install": ("Instalación", "Primer inicio, paso a paso.",
                    "La aplicación aún no tiene un certificado de pago, así que tu sistema pregunta una vez. Las actualizaciones "
                    "desde la aplicación no preguntan.",
                    "Sistema",
                    "<b>Windows puede mostrar «Windows protegió su PC».</b> Comprueba que el archivo viene de este sitio y pulsa "
                    "<b>Más información</b> y luego <b>Ejecutar de todas formas</b>."),
        "dialog": ("Windows protegió su PC", "Microsoft Defender SmartScreen impidió el inicio de una aplicación no reconocida.",
                   "Más información", "No ejecutar", "Aplicación: VideoDownload-Setup.exe<br>Editor: Editor desconocido",
                   "Ejecutar de todas formas"),
        "news": ("Novedades", "Mejor cada semana.", "La misma lista que en la aplicación (Ayuda → Novedades)."),
        "support": ("Gratis, para todos", "La aplicación es gratuita.",
                    "Sin anuncios, sin rastreo y sin versión «premium». Si te resulta útil, puedes apoyar su desarrollo de forma "
                    "voluntaria. Una contribución no desbloquea nada: la aplicación es igual para todos.",
                    "♥ Apoyar con PayPal", "Código QR para una contribución por PayPal", "Escanéalo con la cámara del móvil"),
        "help": ("Ayuda", "¿Preguntas?",
                 "Si algo no funciona: en la aplicación usa Ayuda → Guardar un informe del problema y luego "
                 "<a href=\"{issue}\">informa del problema</a>. Los informes son públicos: no incluyas contraseñas ni datos personales."),
        "faq": (("De repente un vídeo no se descarga.", "Los sitios web cambian a menudo. Ayuda → Actualizar el lector de sitios "
                 "(yt-dlp) y vuelve a intentarlo."),
                ("¿Por qué no se descargan las emisiones en directo?", "Una emisión en directo no tiene fin, así que la descarga "
                 "nunca terminaría. Descárgala cuando acabe y se publique la grabación."),
                ("¿Qué envía la aplicación a internet?", "Solo lo necesario: el enlace que descargas va a ese sitio web y la "
                 "búsqueda de actualizaciones, a GitHub y PyPI. Sin cuentas, estadísticas ni rastreo."),
                ("¿Es segura?", "El código es público en GitHub, cada instalador tiene una suma SHA-256 y la aplicación solo "
                 "instala actualizaciones firmadas digitalmente por nosotros, en Windows y en Mac.")),
        "demo_titles": ("Ruta de montaña – lago Prokoško (4K)", "Mi concierto en directo – grabado desde el público",
                        "Clase: fundamentos de fotografía", "Pódcast #12 – una charla sobre viajes"),
        "demo": ("Descargando · {p}% · {v} MB/s · quedan {s} s", ","),
    },
    "fr": {
        "promise": ('Sans compte', 'Sans limite quotidienne', 'Vos liens ne nous parviennent pas'),
        "a11y": ('Démonstration', "Mettre l'animation en pause", "Relancer l'animation", 'Menu', 'Ajouté : {t}', 'Terminé : {t}', 'Démonstration de la fenêtre du programme (pas un vrai téléchargement)'),
        "share": ('Partager', 'Copier', 'Copié', "Parlez-en à quelqu'un qui en a besoin.", 'Partager Video Download', 'Plus…', 'Fermer'),
        "title": "Video Download — téléchargeur gratuit de vidéo et d'audio pour Windows et Mac",
        "description": "Application gratuite pour Windows et Mac pour télécharger de la vidéo (MP4) et de l'audio (MP3). Sans publicité, sans pistage, en 5 langues.",
        "nav": ("Fonctions", "Extension", "Installation", "Nouveautés", "Aide", "♥ Soutenir"),
        "download_short": "Télécharger", "new": "Nouveau", "eyebrow": "<b>Android et macOS</b> en bêta",
        "h1": ("La vidéo et le son.", "En un clic."),
        "lead": "Une application gratuite pour Windows et Mac : MP4 en pleine qualité ou MP3, directement depuis le navigateur ou depuis un lien copié.",
        "win_btn": "Télécharger pour Windows", "win_req": "Windows 10 et 11 (64 bits)", "install_help": "aide à l'installation",
        "note": "L'application est destinée à vos propres vidéos, aux contenus pour lesquels vous avez l'autorisation de l'auteur "
                "et aux contenus sous licence libre. En téléchargeant, vous acceptez les <a href=\"terms.html\">Conditions "
                "d'utilisation</a>. Les contenus protégés par DRM ne sont pas téléchargés.",
        "try_it": "Essayez : cliquez sur <b>{paste}</b>.",
        "stats": ("sites pris en charge", "langues", "publicités et traqueurs", "téléchargements simultanés"),
        "features": ("Fonctions", "Tout ce qu'il faut,<br>rien de superflu.",
                     "Une fenêtre simple, et en dessous tout ce qu'on attend d'un bon téléchargeur."),
        "tiles": {
            "mp4": ("MP4 jusqu'à la meilleure qualité", "Meilleure, 1080p, 720p ou 480p. L'image et le son sont réunis dans un MP4 (H.264/AAC si le site le propose) lisible sur la plupart des appareils."),
            "audio": ("Son uniquement : MP3 ou M4A", "Pour les cours, les podcasts et la musique. Un MP4 terminé devient un MP3 d'un seul bouton."),
            "copy": ("Copiez un lien, c'est tout", "L'application repère un lien copié et l'ajoute à la file."),
            "playlists": ("Playlists, plusieurs à la fois", "Des playlists entières, jusqu'à 4 téléchargements simultanés, nouvelle tentative automatique si la connexion coupe."),
            "clips": ("Extraits, sous-titres, pochette", "Seulement une partie d'une vidéo, les sous-titres dans le MP4 et la miniature comme pochette du fichier."),
            "theme": ("Thème clair et sombre", "Ou comme le système. La progression dans la barre des tâches et une notification à la fin."),
            "safe": ("Toujours à jour, et sûr", "L'application cherche elle-même les nouvelles versions, met à jour la partie qui "
                     "lit les sites sans réinstallation. Sous Windows et sur Mac, elle n'installe que des mises à jour signées "
                     "numériquement par nous."),
        },
        "chips": ("5 langues", "Sans compte", "Sans publicité", "Sans pistage", "Mises à jour signées sous Windows"),
        "shot_alt": "La fenêtre de Video Download avec quatre téléchargements",
        "extension": ("Extension pour le navigateur", "Téléchargez ce qui est en lecture.",
                      "Lancez une vidéo, cliquez sur l'icône, c'est fait. Ou clic droit sur n'importe quel lien ou vidéo. "
                      "L'application démarre toute seule si elle n'est pas ouverte.",
                      ("Firefox : un clic, signée par Mozilla, se met à jour toute seule",
                       "Edge et Chrome : chargée une fois depuis le dossier de l'application",
                       "Les directs et les vidéos protégées par DRM ne sont pas téléchargés"),
                      "Comment installer l'extension →"),
        "popup": ("application ouverte", "Télécharger la vidéo en cours", "Télécharger en MP3 (son uniquement)",
                  "Flux vidéo détectés", "Extension Video Download"),
        "how": ("Comment ça marche", "Votre premier fichier en quelques minutes.", "Installez une fois, puis copiez simplement des liens.",
                (("Installer", "Pas besoin d'administrateur, rien d'autre n'est ajouté à votre ordinateur."),
                 ("Ajouter un lien", "Copiez un lien, cliquez sur « Coller » ou utilisez l'extension."),
                 ("Télécharger", "MP4 ou MP3, puis « Télécharger ». Le fichier vous attend dans le dossier Video&nbsp;Download."))),
        "install": ("Installation", "Premier lancement, pas à pas.",
                    "L'application n'a pas encore de certificat payant, votre système demande donc une fois. Les mises à jour "
                    "depuis l'application ne demandent rien.",
                    "Système",
                    "<b>Windows peut afficher « Windows a protégé votre ordinateur ».</b> Vérifiez que le fichier provient de ce "
                    "site, puis cliquez sur <b>Informations complémentaires</b> et <b>Exécuter quand même</b>."),
        "dialog": ("Windows a protégé votre ordinateur",
                   "Microsoft Defender SmartScreen a empêché le démarrage d'une application non reconnue.",
                   "Informations complémentaires", "Ne pas exécuter",
                   "Application : VideoDownload-Setup.exe<br>Éditeur : Éditeur inconnu", "Exécuter quand même"),
        "news": ("Nouveautés", "Meilleur chaque semaine.", "La même liste que dans l'application (Aide → Nouveautés)."),
        "support": ("Gratuit, pour tous", "L'application est gratuite.",
                    "Sans publicité, sans pistage et sans version « premium ». Si elle vous est utile, vous pouvez soutenir son "
                    "développement librement. Une contribution ne débloque rien : l'application est la même pour tous.",
                    "♥ Soutenir via PayPal", "Code QR pour une contribution PayPal", "Scannez avec l'appareil photo du téléphone"),
        "help": ("Aide", "Des questions ?",
                 "Si quelque chose ne marche pas : dans l'application, Aide → Enregistrer un rapport de problème, puis "
                 "<a href=\"{issue}\">signalez le problème</a>. Les signalements sont publics : n'y mettez ni mots de passe ni "
                 "données personnelles."),
        "faq": (("Une vidéo ne se télécharge soudain plus.", "Les sites changent souvent. Aide → Mettre à jour le lecteur de sites "
                 "(yt-dlp), puis réessayez."),
                ("Pourquoi les directs ne sont-ils pas téléchargés ?", "Un direct n'a pas de fin, le téléchargement ne se "
                 "terminerait donc jamais. Téléchargez-le une fois terminé, quand l'enregistrement est publié."),
                ("Qu'envoie l'application sur Internet ?", "Seulement le nécessaire : le lien que vous téléchargez va vers ce "
                 "site, et la recherche de mises à jour vers GitHub et PyPI. Ni compte, ni statistiques, ni pistage."),
                ("Est-ce sûr ?", "Le code est public sur GitHub, chaque programme d'installation a une somme SHA-256 et "
                 "l'application n'installe que des mises à jour signées par nous, sous Windows et sur Mac.")),
        "demo_titles": ("Randonnée en montagne – lac de Prokoško (4K)", "Mon concert en direct – filmé depuis le public",
                        "Cours : les bases de la photographie", "Podcast #12 – une discussion sur le voyage"),
        "demo": ("Téléchargement · {p}% · {v} MB/s · encore {s} s", ","),
    },
}


def _icon(name: str) -> str:
    return (f'<div class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg></div>')


def app_labels(lang: str) -> dict:
    """Nazivi dugmadi i formata iz samog programa (videodl/i18n.py), da demo odgovara pravom prozoru."""
    from videodl import i18n

    previous = i18n.get_language()
    i18n.set_language(lang)
    try:
        return {"paste": "+ " + i18n.tr("toolbar.paste"), "download": "↓ " + i18n.tr("toolbar.download"),
                "format": i18n.tr("preset.best"), "folder": i18n.tr("folder.label"), "support": i18n.tr("support.link"),
                "done": i18n.tr("row.done"),
                "short": {key: i18n.tr(f"preset.{key}.short") for key in ("best", "1080p", "720p", "mp3")}}
    finally:
        i18n.set_language(previous)


def demo_script(lang: str) -> str:
    h, labels = HOME[lang], app_labels(lang)
    progress, decimal = h["demo"]
    rows = [{"title": title, "len": length, "mb": mb, "speed": speed, "c1": c1, "c2": c2,
             "fmt": labels["short"][preset], "audio": audio}
            for title, (length, mb, speed, c1, c2, preset, audio) in zip(h["demo_titles"], DEMO_ROWS)]
    data = {"progress": progress, "done": labels["done"] + " · {m} MB", "decimal": decimal,
            "finished": [rows[2], rows[3]], "demos": rows, "added": h["a11y"][4], "ended": h["a11y"][5]}
    # </ u JSON-u ne smije zatvoriti <script>
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


PAUSE_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path class="i-pause" fill="currentColor" '
              'd="M7 5h3.5v14H7zm6.5 0H17v14h-3.5z"/><path class="i-play" fill="currentColor" d="M8 5v14l11-7z"/></svg>')


def menu_button(lang: str) -> str:
    """☰ za telefone i uske prozore: otvara #mobile-nav (isti linkovi kao gornji meni)."""
    label = html.escape(HOME[lang]["a11y"][3])
    return (f'<button class="menu-btn" type="button" aria-controls="mobile-nav" aria-expanded="false" '
            f'aria-label="{label}" title="{label}"><span></span><span></span><span></span></button>')


SHARE_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
              'stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
              '<path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/></svg>')


# Ikone mreža: pojednostavljeni znakovi (bijelo na boji mreže), bez tuđih slika i skripti.
SHARE_APPS = (
    ("WhatsApp", "#25D366", '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" '
     'd="M12 3.5a8.5 8.5 0 0 0-7.3 12.8L3.5 20.5l4.3-1.2A8.5 8.5 0 1 0 12 3.5z"/><path fill="currentColor" '
     'd="M9.2 7.8c.3 0 .5 0 .7.5l.7 1.6c.1.3 0 .5-.1.7l-.5.6c-.2.2-.2.4 0 .7.6 1 1.4 1.8 2.4 2.4.3.2.5.1.7 0l.6-.6c.2-.2.4-.2.7-.1l1.6.8c.4.2.4.4.3.8-.2.9-1.1 1.6-2 1.6-3.3-.3-6.2-3.2-6.5-6.5 0-.9.6-1.8 1.4-2.1z"/>'),
    ("Viber", "#7360F2", '<path fill="currentColor" d="M8 4.5c.5 0 .9.3 1.1.8l1 2.6c.2.4 0 .9-.3 1.2l-.9.8a9 9 0 0 0 '
     '5.2 5.2l.8-.9c.3-.3.8-.5 1.2-.3l2.6 1c.5.2.8.6.8 1.1v1.5c0 1.2-1 2.2-2.2 2A13.5 13.5 0 0 1 4.5 8.3C4.3 7.1 5.3 6 6.5 6z"/>'),
    ("Telegram", "#229ED9", '<path fill="currentColor" d="M20.6 4.2 3.4 10.8c-1 .4-1 1 0 1.3l4.3 1.4 1.7 5c.2.6.5.8 1 .3l2.4-2.3 '
     '4.6 3.4c.8.5 1.4.2 1.6-.8l2.9-13.7c.3-1.2-.4-1.7-1.3-1.2zM9.5 13.3l7.7-5-6 5.6-.3 3.4z"/>'),
    ("Facebook", "#1877F2", '<path fill="currentColor" d="M13.5 21v-7.5H16l.4-3H13.5V8.7c0-.9.3-1.4 1.5-1.4h1.5V4.6'
     'A20 20 0 0 0 14.3 4.5c-2.2 0-3.8 1.3-3.8 3.8v2.2H8v3h2.5V21z"/>'),
    ("X", "#111111", '<path fill="currentColor" d="M17.8 3.5h3l-6.6 7.5 7.8 9.5h-6.1l-4.8-5.9-5.4 5.9h-3l7-7.9L2.3 3.5'
     'h6.2l4.3 5.4zm-1 15.3h1.7L7.3 5.1H5.5z"/>'),
    ("E-mail", "#6B7280", '<rect x="3.5" y="5.5" width="17" height="13" rx="2" fill="none" stroke="currentColor" '
     'stroke-width="2"/><path d="m4 7 8 6 8-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'),
)


def share_html(lang: str, url: str, up: str = "") -> str:
    """Dugme „Podijeli" i prozor za dijeljenje kao u aplikacijama: pregled, okrugla dugmad mreža, kopiranje adrese
    i „Više…" (dijeljenje sistema). Obični linkovi, bez tuđih skripti: mreža dobija link tek kad posjetilac klikne."""
    from urllib.parse import quote

    label, copy, copied, hint, title, more, close = HOME[lang]["share"]
    page_title = HOME[lang]["title"]
    u, text, t = quote(url, safe=""), quote(f"{page_title} {url}", safe=""), quote(page_title, safe="")
    hrefs = {"WhatsApp": f"https://wa.me/?text={text}", "Viber": f"viber://forward?text={text}",
             "Telegram": f"https://t.me/share/url?url={u}&text={t}",
             "Facebook": f"https://www.facebook.com/sharer/sharer.php?u={u}",
             "X": f"https://x.com/intent/post?url={u}&text={t}", "E-mail": f"mailto:?subject={t}&body={text}"}
    apps = "\n".join(
        f'            <a class="sheet-app" style="--c:{color}" href="{html.escape(hrefs[name])}" target="_blank" '
        f'rel="noopener noreferrer"><i><svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg></i><span>{name}</span></a>'
        for name, color, icon in SHARE_APPS)
    esc = html.escape
    return f"""            <div class="share" data-url="{esc(url)}" data-title="{esc(page_title)}" data-copied="{esc(copied)}">
              <button class="btn ghost share-btn" type="button" aria-haspopup="dialog" title="{esc(hint)}">{SHARE_ICON} {label}</button>
              <dialog class="share-sheet" aria-label="{esc(title)}">
                <div class="sheet-head"><h3>{title}</h3><button class="sheet-close" type="button" aria-label="{esc(close)}">✕</button></div>
                <div class="sheet-preview"><img src="{up}assets/icon.png" alt=""><div><b>Video Download</b><span>{esc(url)}</span></div></div>
                <div class="sheet-grid">
{apps}
            <button class="sheet-app sheet-more" type="button" style="--c:#8A94A6" hidden><i>{SHARE_ICON}</i><span>{more}</span></button>
                </div>
                <div class="sheet-copy"><input type="text" readonly value="{esc(url)}" aria-label="URL"><button type="button" data-copy data-label="{esc(copy)}">{copy}</button></div>
              </dialog>
            </div>"""


def render(lang: str, *, up: str, switcher: str, alternates: str, footer: str, news: str, version_line: str,
           installer_url: str, mac_url: str, issue_url: str, mac_text: tuple, meta: str = "",
           android_url: str = "", android_text: tuple = ("", "", "", ()), android_guide_label: str = "",
           page_url: str = "", news_more: str = "", guides_link: str = "") -> str:
    h, labels = HOME[lang], app_labels(lang)
    esc = html.escape
    nav = "\n".join(f'      <a{" class=\"heart\"" if anchor == "support" else ""} href="#{anchor}">{label}</a>'
                    for anchor, label in zip(ANCHORS, h["nav"]))
    badge, mac_lead, mac_button, mac_note, mac_steps = mac_text
    tiles = h["tiles"]
    small = [("audio", ".05s"), ("copy", ".1s"), ("playlists", ""), ("clips", ".05s"), ("theme", ".1s")]
    small_html = "\n".join(
        f'        <div class="tile" data-reveal{f" style=\"--d:{d}\"" if d else ""}>\n          {_icon(k)}\n'
        f'          <h3>{tiles[k][0]}</h3>\n          <p>{tiles[k][1]}</p>\n        </div>' for k, d in small)
    chips = "".join(f"<span>{c}</span>" for c in h["chips"])
    promise = "".join(f"<li>{item}</li>" for item in h["promise"])
    ext_kicker, ext_h2, ext_sub, ext_list, ext_link = h["extension"]
    running, playing, mp3, streams, ext_aria = h["popup"]
    how_kicker, how_h2, how_sub, steps = h["how"]
    steps_html = "\n".join(f'        <div class="step"><div class="n">{i}</div><h3>{title}</h3><p>{text}</p></div>'
                           for i, (title, text) in enumerate(steps, 1))
    in_kicker, in_h2, in_sub, in_label, in_win = h["install"]
    d_title, d_body, d_more, d_dont, d_app, d_run = h["dialog"]
    news_kicker, news_h2, news_sub = h["news"]
    s_kicker, s_h2, s_text, s_btn, s_qr, s_scan = h["support"]
    help_kicker, help_h2, help_sub = h["help"]
    faq = "\n".join(f"        <details><summary>{q}</summary><p>{a}</p></details>" for q, a in h["faq"])
    mac_items = "\n".join(f"          <li>{step}</li>" for step in mac_steps)
    android_lead, android_button, android_note, android_steps = android_text
    android_items = "\n".join(f"          <li>{step}</li>" for step in android_steps)
    download_icon = (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
                     f'stroke-linejoin="round">{ICONS["download"]}</svg>')
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(h["title"])}</title>
<meta name="description" content="{esc(h["description"])}">
{meta}
<link rel="icon" href="{up}assets/icon.png">
<link rel="apple-touch-icon" href="{up}assets/icon.png">
<meta name="theme-color" content="#f7f9fc" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0b0e14" media="(prefers-color-scheme: dark)">
<link rel="stylesheet" href="{up}assets/site.css">
<script>document.documentElement.classList.add("js")</script>
{alternates}
</head>
<body>

<header>
  <div class="wrap bar">
    <a class="brand" href="index.html">{BRAND_ICON}Video Download</a>
    <nav>
{nav}
    </nav>
    {switcher}
    <a class="btn btn-mini" href="{installer_url}">{h["download_short"]}</a>
    {menu_button(lang)}
  </div>
  <nav class="mobile-nav" id="mobile-nav" aria-label="{esc(h["a11y"][3])}" hidden>
{nav}
    <div class="menu-lang">{switcher}</div>
  </nav>
</header>

<main>
  <div class="hero">
    <div class="bloom" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
    <div class="wrap hero-grid">
      <div data-reveal>
        <div class="eyebrow"><span class="badge">{h["new"]}</span> {h["eyebrow"]}</div>
        <h1>{h["h1"][0]}<br><span class="grad">{h["h1"][1]}</span></h1>
        <p class="lead">{h["lead"]}</p>
        <div class="cta">
          <a class="btn" href="{installer_url}">
            {download_icon}
            {h["win_btn"]}
          </a>
          <a class="btn ghost" href="#panel-mac" data-mac>macOS <span class="badge">{badge}</span></a>
          <a class="btn ghost" href="#panel-android" data-android>Android <span class="badge">{badge}</span></a>
        </div>
        <ul class="promise">{promise}</ul>
        <div class="meta">{version_line} · {h["win_req"]} · <a href="#install">{h["install_help"]}</a></div>
        <p class="note">{h["note"]}</p>
      </div>

      <div class="stage" data-reveal style="--d:.15s">
        <!-- Ahmed 27.9.2026: bez vidljive oznake i dugmeta iznad demoa; pauza ostaje za tastaturu (vidi se tek na Tab). -->
        <button class="anim-toggle" type="button" aria-pressed="false" data-pause="{esc(h["a11y"][1])}"
                data-play="{esc(h["a11y"][2])}">{PAUSE_ICON}<span>{h["a11y"][1]}</span></button>
        <div class="app" role="region" aria-label="{esc(h["a11y"][6])}">
          <div class="app-title" aria-hidden="true"><img src="{up}assets/icon.png" alt="">Video Download<span class="dots">– ▢ ✕</span></div>
          <div class="app-tools">
            <button class="paste" type="button">{esc(labels["paste"])}</button>
            <div class="fmt" aria-hidden="true">{esc(labels["format"])}</div>
            <div class="go" aria-hidden="true">{esc(labels["download"])}</div>
          </div>
          <div class="rows" aria-hidden="true"></div>
          <p class="sr" role="status" aria-live="polite" data-announce></p>
          <div class="app-foot" aria-hidden="true"><span>{esc(labels["folder"])} Video Download</span><span class="heart">{esc(labels["support"])}</span></div>
        </div>
        <p class="stage-note">{h["try_it"].format(paste=esc(labels["paste"]))}</p>
      </div>
    </div>

    <div class="wrap stats" data-reveal>
      <div class="stat"><b data-count="1800" data-suffix="+">1800+</b><span>{h["stats"][0]}</span></div>
      <div class="stat"><b data-count="5">5</b><span>{h["stats"][1]}</span></div>
      <div class="stat"><b data-count="0">0</b><span>{h["stats"][2]}</span></div>
      <div class="stat"><b data-count="4">4</b><span>{h["stats"][3]}</span></div>
    </div>
  </div>

  <section id="features">
    <div class="wrap">
      <div class="kicker" data-reveal>{h["features"][0]}</div>
      <h2 data-reveal>{h["features"][1]}</h2>
      <p class="sub" data-reveal>{h["features"][2]}</p>
      <div class="bento">
        <div class="tile wide tall shot" data-reveal>
          {_icon("mp4")}
          <h3>{tiles["mp4"][0]}</h3>
          <p>{tiles["mp4"][1]}</p>
          <picture>
            <source srcset="{up}assets/screenshot-dark-{lang}.png" media="(prefers-color-scheme: dark)">
            <img src="{up}assets/screenshot-light-{lang}.png" alt="{esc(h["shot_alt"])}" width="860" height="470" loading="lazy">
          </picture>
        </div>
{small_html}
        <div class="tile full" data-reveal>
          {_icon("safe")}
          <h3>{tiles["safe"][0]}</h3>
          <p>{tiles["safe"][1]}</p>
          <div class="chips">{chips}</div>
        </div>
      </div>
    </div>
  </section>

  <section id="extension">
    <div class="wrap split">
      <div data-reveal>
        <div class="kicker">{ext_kicker}</div>
        <h2>{ext_h2}</h2>
        <p class="sub">{ext_sub}</p>
        <ul class="list">
{chr(10).join(f"          <li>{item}</li>" for item in ext_list)}
        </ul>
        <p><a href="extension.html">{ext_link}</a></p>
      </div>
      <div class="browser" data-reveal style="--d:.1s">
        <div class="top"><i></i><i></i><i></i><span class="url">example-video-site.test/watch</span><button class="ext" type="button" aria-label="{esc(ext_aria)}"></button></div>
        <div class="page">
          <div class="video"></div>
          <div class="popup" aria-hidden="true">
            <b>Video Download</b> · {running}
            <span class="pb">⬇ {playing}</span>
            <span class="pb alt">♪ {mp3}</span>
            <small>{streams}: 1</small>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section id="how">
    <div class="wrap center">
      <div class="kicker" data-reveal>{how_kicker}</div>
      <h2 data-reveal>{how_h2}</h2>
      <p class="sub" data-reveal>{how_sub}</p>
      <div class="steps">
{steps_html}
      </div>
    </div>
  </section>

  <section id="install">
    <div class="wrap">
      <div class="kicker" data-reveal>{in_kicker}</div>
      <h2 data-reveal>{in_h2}</h2>
      <p class="sub" data-reveal>{in_sub}</p>
      <div class="tabs" aria-label="{esc(in_label)}">
        <a href="#panel-win" id="tab-win" aria-controls="panel-win">Windows</a>
        <a href="#panel-mac" id="tab-mac" aria-controls="panel-mac">macOS <span class="badge">{badge}</span></a>
        <a href="#panel-android" id="tab-android" aria-controls="panel-android">Android <span class="badge">{badge}</span></a>
      </div>
      <div class="panel" id="panel-win" role="tabpanel" aria-labelledby="tab-win">
        <p>{in_win}</p>
        <div class="dialogs" aria-hidden="true">
          <div class="dlg"><div class="h">{d_title}</div><div>{d_body}</div><div style="margin-top:8px"><span class="hl" style="text-decoration:underline">{d_more}</span></div><div class="btns"><span>{d_dont}</span></div></div>
          <div class="arrow">→</div>
          <div class="dlg"><div class="h">{d_title}</div><div>{d_app}</div><div class="btns"><span class="hl">{d_run}</span><span>{d_dont}</span></div></div>
        </div>
        <p style="margin-top:22px"><a class="btn" href="{installer_url}">{h["win_btn"]}</a></p>
      </div>
      <div class="panel" id="panel-mac" role="tabpanel" aria-labelledby="tab-mac">
        <p><span class="badge">{badge}</span> {mac_lead.format(issue=issue_url)}</p>
        <p>{mac_note}</p>
        <ol>
{mac_items}
        </ol>
        <p style="margin-top:22px"><a class="btn" href="{mac_url}">{mac_button}</a></p>
      </div>
      <div class="panel" id="panel-android" role="tabpanel" aria-labelledby="tab-android">
        <p><span class="badge">{badge}</span> {android_lead.format(issue=issue_url)}</p>
        <p>{android_note}</p>
        <ol>
{android_items}
        </ol>
        <p style="margin-top:22px"><a class="btn" href="{android_url}">{android_button}</a></p>
        <p><a href="android-guide.html">{esc(android_guide_label)} →</a></p>
      </div>
    </div>
  </section>

  <section id="news">
    <div class="wrap">
      <div class="kicker" data-reveal>{news_kicker}</div>
      <h2 data-reveal>{news_h2}</h2>
      <p class="sub" data-reveal>{news_sub}</p>
      <div class="news">
{news}
      </div>
      <p class="more" data-reveal><a href="changelog.html">{news_more}</a></p>
    </div>
  </section>

  <section id="support">
    <div class="wrap">
      <div class="support-card" data-reveal>
        <div>
          <div class="kicker" style="color:var(--pink)">{s_kicker}</div>
          <h2>{s_h2}</h2>
          <p class="sub" style="margin-bottom:26px">{s_text}</p>
          <div class="support-actions">
            <a class="btn" href="https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ">{s_btn}</a>
            <a class="btn ghost" href="https://ko-fi.com/abnps">Ko-fi</a>
{share_html(lang, page_url, up)}
          </div>
        </div>
        <div class="qr"><img src="{up}assets/support-qr.png" alt="{esc(s_qr)}" width="500" height="561" loading="lazy">{s_scan}</div>
      </div>
    </div>
  </section>

  <section id="help">
    <div class="wrap">
      <div class="center">
        <div class="kicker" data-reveal>{help_kicker}</div>
        <h2 data-reveal>{help_h2}</h2>
        <p class="sub" data-reveal>{help_sub.format(issue=issue_url)}</p>
      </div>
      <div class="faq" data-reveal>
{faq}
      </div>
      <p class="more" data-reveal><a href="guides.html">{guides_link}</a></p>
    </div>
  </section>
</main>

{footer}

<script>window.VD_TEXT = {demo_script(lang)};</script>
<script src="{up}assets/site.js" defer></script>
</body>
</html>
"""
