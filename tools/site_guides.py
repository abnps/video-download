"""Vodiči na sajtu (SEO): kratka uputstva korak po korak, svako na svojoj adresi i na 5 jezika.

Nazivi menija i dugmadi ({downloads}, {paste}…) dolaze iz samog programa (videodl/i18n.py), pa tekst uvijek
odgovara onome što korisnik vidi. Bez imena platformi (isto pravilo kao za početnu, vidi FORBIDDEN u build_site.py).
"""

import html

GUIDES = ("video-to-mp3", "video-clip", "playlist", "subtitles", "not-downloading")

# (naziv u meniju/podnožju, naslov, opis za Google, uvod, poziv na preuzimanje, „svi vodiči", „još vodiča",
#  „koraci", „dobro je znati", link s početne)
HUB = {
    "en": ("Guides", "Guides", "Short guides for Video Download: MP3, clips, playlists, subtitles and what to do when "
           "a video won't download.", "Short step-by-step guides for the most common tasks.",
           "Video Download is free for Windows and Mac.", "All guides", "More guides", "Steps", "Good to know",
           "Guides: MP3, clips, playlists, subtitles →"),
    "bs": ("Vodiči", "Vodiči", "Kratki vodiči za Video Download: MP3, isječci, plejliste, titlovi i šta uraditi kad se "
           "video ne preuzima.", "Kratka uputstva korak po korak za najčešće zadatke.",
           "Video Download je besplatan za Windows i Mac.", "Svi vodiči", "Još vodiča", "Koraci", "Dobro je znati",
           "Vodiči: MP3, isječci, plejliste, titlovi →"),
    "de": ("Anleitungen", "Anleitungen", "Kurze Anleitungen für Video Download: MP3, Ausschnitte, Playlists, Untertitel "
           "und was tun, wenn ein Video nicht lädt.", "Kurze Schritt-für-Schritt-Anleitungen für die häufigsten Aufgaben.",
           "Video Download ist kostenlos für Windows und Mac.", "Alle Anleitungen", "Weitere Anleitungen", "Schritte",
           "Gut zu wissen", "Anleitungen: MP3, Ausschnitte, Playlists, Untertitel →"),
    "es": ("Guías", "Guías", "Guías breves de Video Download: MP3, fragmentos, listas de reproducción, subtítulos y qué "
           "hacer si un vídeo no se descarga.", "Guías breves paso a paso para las tareas más comunes.",
           "Video Download es gratis para Windows y Mac.", "Todas las guías", "Más guías", "Pasos", "Conviene saber",
           "Guías: MP3, fragmentos, listas, subtítulos →"),
    "fr": ("Guides", "Guides", "Guides courts pour Video Download : MP3, extraits, playlists, sous-titres et que faire "
           "quand une vidéo ne se télécharge pas.", "Des guides courts, étape par étape, pour les tâches les plus courantes.",
           "Video Download est gratuit pour Windows et Mac.", "Tous les guides", "Autres guides", "Étapes", "Bon à savoir",
           "Guides : MP3, extraits, playlists, sous-titres →"),
}

# Po jeziku i vodiču: naslov, opis, uvod, koraci, savjeti.
TEXT = {
    "en": {
        "video-to-mp3": (
            "Save a video as MP3 (audio only)",
            "How to save only the audio of a video as MP3 or M4A with the free Video Download app for Windows and Mac.",
            "For lectures, podcasts and music you often need only the sound. Video Download saves it straight as MP3, "
            "or turns an MP4 you already have into MP3 with one click.",
            ("Copy the video link and click {paste} in Video Download.",
             "In the format list choose {mp3}. {m4a} is there too.",
             "Click {download}. The audio file appears in the download folder."),
            ("Already downloaded the MP4? Click {convert} on its row: {convert_tip}.",
             "MP3 is saved at 192 kbps.",
             "The browser extension has its own MP3 button, and the right-click menu offers MP3 too.")),
        "video-clip": (
            "Download only part of a video (clip)",
            "How to download just a section of a video, between a start and an end time, with Video Download.",
            "You don't need a two-hour recording for one five-minute answer. Video Download can save only the part "
            "between two times.",
            ("Add the video link with {paste}.",
             "Click the format button on that video's row and choose {section}.",
             "Enter the start and end, for example 2:30-6:10 or 1:02:00-1:05:30, and confirm.",
             "Click {download}. Only that part is downloaded."),
            ("The file name includes the start and end time, so several clips of the same video don't overwrite each other.",
             "To get the full video again, choose {whole} in the same menu.")),
        "playlist": (
            "Download a whole playlist",
            "How to download all videos from a playlist at once with Video Download, up to four at a time.",
            "Paste a playlist link and every video in it goes into the list. Video Download downloads several at once "
            "and tries again by itself if the connection drops.",
            ("Copy the playlist link and click {paste}. All its videos are added to the list.",
             "Choose the format, for example {best} or {mp3}. It applies to everything waiting in the list; a single "
             "row can get its own format with its format button.",
             "Click {download}."),
            ("A link to one video that belongs to a playlist downloads only that video. For the whole list, turn on "
             "{downloads} → {whole_playlist}.",
             "{downloads} → {parallel}: from 1 to 4 downloads at the same time.",
             "If the connection drops, the download is tried again up to 3 times.")),
        "subtitles": (
            "Download a video with subtitles",
            "How to save subtitles with a video in Video Download: inside the MP4 and as an .srt file next to it.",
            "Video Download can save subtitles with the video: inside the MP4 and as a separate .srt file that video "
            "players load on their own.",
            ("Turn on {downloads} → {subtitles}.",
             "Add the link with {paste} and click {download}.",
             "Next to the video you get an .srt file with the same name, and the subtitles are also inside the MP4."),
            ("If a video has no hand-made subtitles, automatic ones are used when the site offers them.",
             "If the subtitles can't be downloaded, the video is still saved.",
             "{downloads} → {thumbnail} saves the video's picture as the file cover.")),
        "not-downloading": (
            "Video won't download? What to do",
            "The most common reasons a video won't download with Video Download, and how to fix them.",
            "Websites change how they work all the time. Most problems are solved in a minute.",
            ("Update the site reader: {help} → {update_ytdlp}, then try again.",
             "Is it a live stream? Live streams aren't downloaded. Download the recording once the stream ends and is published.",
             "Only for signed-in users? Send it from the browser extension and allow cookie access when the browser asks. "
             "The app uses them only for that download and does not keep them.",
             "Still not working? {help} → {report}, then {issue}. Reports are public: don't include passwords or personal data."),
            ("Videos protected with DRM (paid streaming services) can't be downloaded. That's intentional.",
             "Check that the link opens and plays in the browser.")),
    },
    "bs": {
        "video-to-mp3": (
            "Sačuvaj video kao MP3 (samo zvuk)",
            "Kako sačuvati samo zvuk videa kao MP3 ili M4A besplatnim programom Video Download za Windows i Mac.",
            "Za predavanja, podcaste i muziku često treba samo zvuk. Video Download ga odmah čuva kao MP3 ili jednim "
            "klikom pretvara MP4 koji već imaš u MP3.",
            ("Kopiraj link videa i klikni {paste} u programu Video Download.",
             "U listi formata izaberi {mp3}. Tu je i {m4a}.",
             "Klikni {download}. Zvučni fajl se pojavi u folderu za preuzimanja."),
            ("MP4 je već preuzet? Klikni {convert} na njegovom redu: {convert_tip}.",
             "MP3 se čuva u kvalitetu 192 kbps.",
             "Dodatak za browser ima svoje dugme za MP3, a MP3 nudi i meni desnog klika.")),
        "video-clip": (
            "Preuzmi samo dio videa (isječak)",
            "Kako preuzeti samo dio videa, od početnog do krajnjeg vremena, programom Video Download.",
            "Za jedan odgovor od pet minuta ne treba ti snimak od dva sata. Video Download može sačuvati samo dio "
            "između dva vremena.",
            ("Dodaj link videa dugmetom {paste}.",
             "Klikni dugme formata na redu tog videa i izaberi {section}.",
             "Upiši početak i kraj, npr. 2:30-6:10 ili 1:02:00-1:05:30, i potvrdi.",
             "Klikni {download}. Preuzima se samo taj dio."),
            ("Ime fajla sadrži početak i kraj, pa se više isječaka istog videa ne prepisuje.",
             "Za cijeli video ponovo izaberi {whole} u istom meniju.")),
        "playlist": (
            "Preuzmi cijelu plejlistu",
            "Kako programom Video Download preuzeti sve videe iz plejliste odjednom, do četiri istovremeno.",
            "Zalijepi link plejliste i svi njeni videi idu u listu. Video Download preuzima više odjednom i sam "
            "pokušava ponovo ako pukne veza.",
            ("Kopiraj link plejliste i klikni {paste}. Svi njeni videi se dodaju u listu.",
             "Izaberi format, npr. {best} ili {mp3}. Važi za sve što čeka u listi; pojedini red može dobiti svoj "
             "format preko dugmeta formata.",
             "Klikni {download}."),
            ("Link jednog videa koji je dio plejliste preuzima samo taj video. Za cijelu listu uključi "
             "{downloads} → {whole_playlist}.",
             "{downloads} → {parallel}: od 1 do 4 preuzimanja istovremeno.",
             "Ako pukne veza, preuzimanje se pokuša ponovo do 3 puta.")),
        "subtitles": (
            "Preuzmi video s titlovima",
            "Kako programom Video Download sačuvati titlove uz video: u MP4 fajlu i kao .srt fajl pored njega.",
            "Video Download može sačuvati titlove uz video: unutar MP4 fajla i kao poseban .srt fajl koji plejeri "
            "sami učitaju.",
            ("Uključi {downloads} → {subtitles}.",
             "Dodaj link dugmetom {paste} i klikni {download}.",
             "Pored videa dobiješ .srt fajl istog imena, a titlovi su i unutar MP4 fajla."),
            ("Ako video nema ručno napravljene titlove, koriste se automatski, kad ih sajt nudi.",
             "Ako se titlovi ne mogu preuzeti, video se svejedno sačuva.",
             "{downloads} → {thumbnail} čuva sličicu videa kao omot fajla.")),
        "not-downloading": (
            "Video se ne preuzima? Šta uraditi",
            "Najčešći razlozi zašto se video ne preuzima programom Video Download i kako ih riješiti.",
            "Sajtovi stalno mijenjaju način rada. Većina problema se riješi za minut.",
            ("Ažuriraj čitač sajtova: {help} → {update_ytdlp}, pa pokušaj ponovo.",
             "Da li je to prenos uživo? Prenos uživo se ne preuzima. Preuzmi snimak kad se prenos završi i bude objavljen.",
             "Samo za prijavljene korisnike? Pošalji ga iz dodatka za browser i dozvoli pristup kolačićima kad browser "
             "pita. Program ih koristi samo za to preuzimanje i ne čuva ih.",
             "I dalje ne radi? {help} → {report}, pa {issue}. Prijave su javne: ne upisuj lozinke ni lične podatke."),
            ("Video zaštićen DRM-om (plaćeni servisi za gledanje) se ne može preuzeti. To je namjerno.",
             "Provjeri da se link otvara i pušta u browseru.")),
    },
    "de": {
        "video-to-mp3": (
            "Video als MP3 speichern (nur Ton)",
            "So speicherst du mit der kostenlosen App Video Download für Windows und Mac nur den Ton eines Videos als MP3 oder M4A.",
            "Für Vorlesungen, Podcasts und Musik brauchst du oft nur den Ton. Video Download speichert ihn direkt als "
            "MP3 oder macht aus einer vorhandenen MP4 mit einem Klick eine MP3.",
            ("Kopiere den Link des Videos und klicke in Video Download auf {paste}.",
             "Wähle in der Formatliste {mp3}. {m4a} gibt es auch.",
             "Klicke auf {download}. Die Audiodatei erscheint im Download-Ordner."),
            ("Die MP4 ist schon geladen? Klicke in ihrer Zeile auf {convert}: {convert_tip}.",
             "MP3 wird mit 192 kbit/s gespeichert.",
             "Die Browser-Erweiterung hat eine eigene MP3-Schaltfläche, und auch das Rechtsklick-Menü bietet MP3.")),
        "video-clip": (
            "Nur einen Teil eines Videos laden (Ausschnitt)",
            "So lädst du mit Video Download nur einen Abschnitt eines Videos zwischen Start- und Endzeit.",
            "Für eine Antwort von fünf Minuten brauchst du keine zweistündige Aufnahme. Video Download kann nur den "
            "Teil zwischen zwei Zeiten speichern.",
            ("Füge den Link mit {paste} hinzu.",
             "Klicke in der Zeile des Videos auf die Format-Schaltfläche und wähle {section}.",
             "Gib Anfang und Ende ein, z. B. 2:30-6:10 oder 1:02:00-1:05:30, und bestätige.",
             "Klicke auf {download}. Nur dieser Teil wird geladen."),
            ("Der Dateiname enthält Anfang und Ende, daher überschreiben sich mehrere Ausschnitte desselben Videos nicht.",
             "Für das ganze Video wähle im selben Menü {whole}.")),
        "playlist": (
            "Eine ganze Playlist herunterladen",
            "So lädst du mit Video Download alle Videos einer Playlist auf einmal, bis zu vier gleichzeitig.",
            "Füge den Link einer Playlist ein, und alle ihre Videos kommen in die Liste. Video Download lädt mehrere "
            "gleichzeitig und versucht es von selbst erneut, wenn die Verbindung abbricht.",
            ("Kopiere den Link der Playlist und klicke auf {paste}. Alle ihre Videos werden hinzugefügt.",
             "Wähle das Format, z. B. {best} oder {mp3}. Es gilt für alles, was in der Liste wartet; eine einzelne "
             "Zeile bekommt über ihre Format-Schaltfläche ein eigenes Format.",
             "Klicke auf {download}."),
            ("Der Link zu einem einzelnen Video aus einer Playlist lädt nur dieses Video. Für die ganze Liste "
             "schalte {downloads} → {whole_playlist} ein.",
             "{downloads} → {parallel}: 1 bis 4 Downloads gleichzeitig.",
             "Bricht die Verbindung ab, wird der Download bis zu 3-mal erneut versucht.")),
        "subtitles": (
            "Video mit Untertiteln herunterladen",
            "So speicherst du mit Video Download Untertitel zum Video: in der MP4 und als .srt-Datei daneben.",
            "Video Download kann Untertitel mit dem Video speichern: in der MP4 und als eigene .srt-Datei, die Player "
            "von selbst laden.",
            ("Schalte {downloads} → {subtitles} ein.",
             "Füge den Link mit {paste} hinzu und klicke auf {download}.",
             "Neben dem Video liegt eine .srt-Datei mit gleichem Namen, und die Untertitel stecken auch in der MP4."),
            ("Hat ein Video keine von Hand erstellten Untertitel, werden automatische verwendet, wenn die Seite sie anbietet.",
             "Lassen sich die Untertitel nicht laden, wird das Video trotzdem gespeichert.",
             "{downloads} → {thumbnail} speichert das Vorschaubild als Cover der Datei.")),
        "not-downloading": (
            "Video lädt nicht? Was tun",
            "Die häufigsten Gründe, warum ein Video mit Video Download nicht lädt, und wie du sie behebst.",
            "Webseiten ändern ständig ihre Funktionsweise. Die meisten Probleme sind in einer Minute gelöst.",
            ("Aktualisiere den Seitenleser: {help} → {update_ytdlp}, dann erneut versuchen.",
             "Ist es ein Livestream? Livestreams werden nicht geladen. Lade die Aufzeichnung, wenn der Stream vorbei und veröffentlicht ist.",
             "Nur für angemeldete Nutzer? Sende es aus der Browser-Erweiterung und erlaube den Cookie-Zugriff, wenn der "
             "Browser fragt. Die App nutzt sie nur für diesen Download und behält sie nicht.",
             "Klappt es immer noch nicht? {help} → {report}, dann {issue}. Meldungen sind öffentlich: keine Passwörter oder persönlichen Daten."),
            ("Mit DRM geschützte Videos (kostenpflichtige Streamingdienste) lassen sich nicht laden. Das ist Absicht.",
             "Prüfe, ob sich der Link im Browser öffnen und abspielen lässt.")),
    },
    "es": {
        "video-to-mp3": (
            "Guardar un vídeo como MP3 (solo audio)",
            "Cómo guardar solo el audio de un vídeo como MP3 o M4A con la aplicación gratuita Video Download para Windows y Mac.",
            "Para clases, pódcasts y música a menudo solo necesitas el sonido. Video Download lo guarda directamente "
            "como MP3 o convierte en MP3 un MP4 que ya tienes con un clic.",
            ("Copia el enlace del vídeo y pulsa {paste} en Video Download.",
             "En la lista de formatos elige {mp3}. También está {m4a}.",
             "Pulsa {download}. El archivo de audio aparece en la carpeta de descargas."),
            ("¿Ya descargaste el MP4? Pulsa {convert} en su fila: {convert_tip}.",
             "El MP3 se guarda a 192 kbps.",
             "La extensión del navegador tiene su propio botón de MP3, y el menú del clic derecho también ofrece MP3.")),
        "video-clip": (
            "Descargar solo una parte de un vídeo (fragmento)",
            "Cómo descargar solo un tramo de un vídeo, entre un inicio y un final, con Video Download.",
            "Para una respuesta de cinco minutos no necesitas una grabación de dos horas. Video Download puede guardar "
            "solo la parte entre dos tiempos.",
            ("Añade el enlace del vídeo con {paste}.",
             "Pulsa el botón de formato en la fila de ese vídeo y elige {section}.",
             "Escribe el inicio y el final, por ejemplo 2:30-6:10 o 1:02:00-1:05:30, y confirma.",
             "Pulsa {download}. Solo se descarga esa parte."),
            ("El nombre del archivo incluye el inicio y el final, así que varios fragmentos del mismo vídeo no se sobrescriben.",
             "Para volver al vídeo completo, elige {whole} en el mismo menú.")),
        "playlist": (
            "Descargar una lista de reproducción completa",
            "Cómo descargar todos los vídeos de una lista de reproducción a la vez con Video Download, hasta cuatro simultáneos.",
            "Pega el enlace de una lista y todos sus vídeos pasan a la cola. Video Download descarga varios a la vez y "
            "lo vuelve a intentar solo si se corta la conexión.",
            ("Copia el enlace de la lista y pulsa {paste}. Se añaden todos sus vídeos.",
             "Elige el formato, por ejemplo {best} o {mp3}. Se aplica a todo lo que espera en la lista; una fila "
             "puede tener su propio formato con su botón de formato.",
             "Pulsa {download}."),
            ("El enlace de un solo vídeo que forma parte de una lista descarga solo ese vídeo. Para la lista completa, "
             "activa {downloads} → {whole_playlist}.",
             "{downloads} → {parallel}: de 1 a 4 descargas a la vez.",
             "Si se corta la conexión, la descarga se reintenta hasta 3 veces.")),
        "subtitles": (
            "Descargar un vídeo con subtítulos",
            "Cómo guardar los subtítulos con el vídeo en Video Download: dentro del MP4 y como archivo .srt al lado.",
            "Video Download puede guardar los subtítulos con el vídeo: dentro del MP4 y como archivo .srt aparte que "
            "los reproductores cargan solos.",
            ("Activa {downloads} → {subtitles}.",
             "Añade el enlace con {paste} y pulsa {download}.",
             "Junto al vídeo tendrás un archivo .srt con el mismo nombre, y los subtítulos también van dentro del MP4."),
            ("Si el vídeo no tiene subtítulos hechos a mano, se usan los automáticos cuando el sitio los ofrece.",
             "Si no se pueden descargar los subtítulos, el vídeo se guarda igualmente.",
             "{downloads} → {thumbnail} guarda la miniatura del vídeo como portada del archivo.")),
        "not-downloading": (
            "¿El vídeo no se descarga? Qué hacer",
            "Los motivos más habituales por los que un vídeo no se descarga con Video Download y cómo solucionarlos.",
            "Los sitios web cambian su funcionamiento constantemente. La mayoría de los problemas se resuelven en un minuto.",
            ("Actualiza el lector de sitios: {help} → {update_ytdlp} y vuelve a intentarlo.",
             "¿Es una transmisión en directo? Los directos no se descargan. Descarga la grabación cuando termine y se publique.",
             "¿Solo para usuarios con sesión iniciada? Envíalo desde la extensión del navegador y permite el acceso a "
             "las cookies cuando el navegador lo pida. La aplicación solo las usa para esa descarga y no las conserva.",
             "¿Sigue sin funcionar? {help} → {report} y después {issue}. Los informes son públicos: no incluyas contraseñas ni datos personales."),
            ("Los vídeos protegidos con DRM (servicios de pago) no se pueden descargar. Es intencionado.",
             "Comprueba que el enlace se abre y se reproduce en el navegador.")),
    },
    "fr": {
        "video-to-mp3": (
            "Enregistrer une vidéo en MP3 (audio seul)",
            "Comment enregistrer uniquement le son d'une vidéo en MP3 ou M4A avec l'application gratuite Video Download pour Windows et Mac.",
            "Pour les cours, les podcasts et la musique, on n'a souvent besoin que du son. Video Download l'enregistre "
            "directement en MP3 ou transforme en MP3 un MP4 que vous avez déjà, en un clic.",
            ("Copiez le lien de la vidéo et cliquez sur {paste} dans Video Download.",
             "Dans la liste des formats, choisissez {mp3}. {m4a} est aussi disponible.",
             "Cliquez sur {download}. Le fichier audio apparaît dans le dossier de téléchargement."),
            ("Le MP4 est déjà téléchargé ? Cliquez sur {convert} dans sa ligne : {convert_tip}.",
             "Le MP3 est enregistré à 192 kbit/s.",
             "L'extension du navigateur a son propre bouton MP3, et le menu du clic droit propose aussi le MP3.")),
        "video-clip": (
            "Télécharger seulement une partie d'une vidéo (extrait)",
            "Comment télécharger seulement un passage d'une vidéo, entre un début et une fin, avec Video Download.",
            "Pour une réponse de cinq minutes, inutile de garder un enregistrement de deux heures. Video Download peut "
            "enregistrer seulement la partie entre deux horaires.",
            ("Ajoutez le lien de la vidéo avec {paste}.",
             "Cliquez sur le bouton de format de la ligne de cette vidéo et choisissez {section}.",
             "Saisissez le début et la fin, par exemple 2:30-6:10 ou 1:02:00-1:05:30, puis validez.",
             "Cliquez sur {download}. Seule cette partie est téléchargée."),
            ("Le nom du fichier contient le début et la fin : plusieurs extraits de la même vidéo ne s'écrasent pas.",
             "Pour retrouver la vidéo entière, choisissez {whole} dans le même menu.")),
        "playlist": (
            "Télécharger une playlist entière",
            "Comment télécharger toutes les vidéos d'une playlist d'un coup avec Video Download, jusqu'à quatre à la fois.",
            "Collez le lien d'une playlist et toutes ses vidéos entrent dans la liste. Video Download en télécharge "
            "plusieurs à la fois et réessaie tout seul si la connexion coupe.",
            ("Copiez le lien de la playlist et cliquez sur {paste}. Toutes ses vidéos sont ajoutées.",
             "Choisissez le format, par exemple {best} ou {mp3}. Il s'applique à tout ce qui attend dans la liste ; "
             "une ligne peut avoir son propre format via son bouton de format.",
             "Cliquez sur {download}."),
            ("Le lien d'une seule vidéo d'une playlist ne télécharge que cette vidéo. Pour toute la liste, activez "
             "{downloads} → {whole_playlist}.",
             "{downloads} → {parallel} : de 1 à 4 téléchargements en même temps.",
             "Si la connexion coupe, le téléchargement est relancé jusqu'à 3 fois.")),
        "subtitles": (
            "Télécharger une vidéo avec sous-titres",
            "Comment enregistrer les sous-titres avec la vidéo dans Video Download : dans le MP4 et en fichier .srt à côté.",
            "Video Download peut enregistrer les sous-titres avec la vidéo : dans le MP4 et dans un fichier .srt séparé "
            "que les lecteurs chargent tout seuls.",
            ("Activez {downloads} → {subtitles}.",
             "Ajoutez le lien avec {paste} et cliquez sur {download}.",
             "À côté de la vidéo, vous obtenez un fichier .srt du même nom, et les sous-titres sont aussi dans le MP4."),
            ("Si la vidéo n'a pas de sous-titres faits à la main, les automatiques sont utilisés quand le site les propose.",
             "Si les sous-titres ne peuvent pas être téléchargés, la vidéo est quand même enregistrée.",
             "{downloads} → {thumbnail} enregistre la miniature de la vidéo comme pochette du fichier.")),
        "not-downloading": (
            "La vidéo ne se télécharge pas ? Que faire",
            "Les raisons les plus fréquentes pour lesquelles une vidéo ne se télécharge pas avec Video Download, et comment y remédier.",
            "Les sites web changent sans cesse de fonctionnement. La plupart des problèmes se règlent en une minute.",
            ("Mettez à jour le lecteur de sites : {help} → {update_ytdlp}, puis réessayez.",
             "C'est un direct ? Les directs ne sont pas téléchargés. Téléchargez l'enregistrement une fois le direct terminé et publié.",
             "Réservé aux utilisateurs connectés ? Envoyez-le depuis l'extension du navigateur et autorisez l'accès aux "
             "cookies quand le navigateur le demande. L'application ne les utilise que pour ce téléchargement et ne les conserve pas.",
             "Ça ne marche toujours pas ? {help} → {report}, puis {issue}. Les signalements sont publics : pas de mots de passe ni de données personnelles."),
            ("Les vidéos protégées par DRM (services de streaming payants) ne peuvent pas être téléchargées. C'est voulu.",
             "Vérifiez que le lien s'ouvre et se lit dans le navigateur.")),
    },
}

# Tekst linka za prijavu problema (u koraku „I dalje ne radi?").
ISSUE_TEXT = {"en": "report the problem", "bs": "prijavi problem", "de": "melde das Problem",
              "es": "informa del problema", "fr": "signalez le problème"}


def labels(lang: str, issue_url: str) -> dict[str, str]:
    """Nazivi iz programa na jeziku stranice, podebljani kao na ekranu."""
    from videodl import i18n

    keys = {"paste": "toolbar.paste", "download": "toolbar.download", "downloads": "menu.downloads",
            "help": "menu.help", "subtitles": "menu.subtitles", "thumbnail": "menu.thumbnail",
            "whole_playlist": "menu.whole_playlist", "parallel": "menu.parallel", "update_ytdlp": "menu.update_ytdlp",
            "report": "menu.report", "section": "row.section", "whole": "row.section_remove", "mp3": "preset.mp3",
            "m4a": "preset.m4a", "best": "preset.best", "convert": "row.convert"}
    previous = i18n.get_language()
    i18n.set_language(lang)
    try:
        found = {name: "<b>" + html.escape(i18n.tr(key).replace("&", "").rstrip("…").strip()) + "</b>"
                 for name, key in keys.items()}
        found["convert_tip"] = html.escape(i18n.tr("row.convert_tip"))
    finally:
        i18n.set_language(previous)
    found["issue"] = f'<a href="{html.escape(issue_url)}">{ISSUE_TEXT[lang]}</a>'
    return found


def guide_body(lang: str, slug: str, *, issue_url: str, installer_url: str, win_button: str) -> tuple[str, str, str]:
    """(naslov, opis, HTML tijela) jednog vodiča."""
    title, description, lead, steps, tips = TEXT[lang][slug]
    hub = HUB[lang]
    values = labels(lang, issue_url)
    def fill(text: str) -> str:
        # Tekstovi su naši (bez <, > i &); nazivi iz programa su već escape-ovani u labels().
        return text.format_map(values)
    others = "\n".join(f'<li><a href="{other}.html">{html.escape(TEXT[lang][other][0])}</a></li>'
                       for other in GUIDES if other != slug)
    body = f"""<h1>{html.escape(title)}</h1>
<p class="lead">{html.escape(lead)}</p>
<h2>{hub[7]}</h2>
<ol class="guide-steps">
{chr(10).join(f"<li>{fill(step)}</li>" for step in steps)}
</ol>
<h2>{hub[8]}</h2>
<ul>
{chr(10).join(f"<li>{fill(tip)}</li>" for tip in tips)}
</ul>
<div class="box guide-cta"><p>{hub[4]}</p><p><a class="btn" href="{html.escape(installer_url)}">{win_button}</a>
<a class="btn ghost" href="index.html#install">Mac</a></p></div>
<h2>{hub[6]}</h2>
<ul class="guide-list">
{others}
</ul>
<p><a href="guides.html">{hub[5]} →</a></p>"""
    return title, description, body


def hub_body(lang: str) -> tuple[str, str, str]:
    hub = HUB[lang]
    cards = "\n".join(f'<li><a href="{slug}.html"><b>{html.escape(TEXT[lang][slug][0])}</b></a>'
                      f"<br><span>{html.escape(TEXT[lang][slug][1])}</span></li>" for slug in GUIDES)
    body = f"""<h1>{hub[1]}</h1>
<p class="lead">{hub[3]}</p>
<ul class="guide-list cards">
{cards}
</ul>"""
    return hub[1], hub[2], body
