"""Kratke bilješke o izmjenama (Pomoć → Šta je novo), od najnovije verzije ka starijoj.

Svaka nova verzija mora imati unos na svih 5 jezika; test pada ako `__version__` nema bilješku.
Isti tekst (bs) ide i u opis izdanja na GitHub-u.
"""

from html import escape

# (verzija, datum, {jezik: [stavke]})
CHANGES = [
    ("0.7.6", "24.9.2026", {
        "bs": ["„Podrži projekat“ otvara PayPal stranicu za prilog, gdje sam biraš iznos."],
        "en": ["\u201cSupport the project\u201d opens a PayPal contribution page where you choose the amount."],
        "de": ["\u201eProjekt unterstützen\u201c öffnet eine PayPal-Seite für Beiträge, auf der du den Betrag selbst wählst."],
        "es": ["«Apoyar el proyecto» abre una página de aportaciones de PayPal donde eliges el importe."],
        "fr": ["« Soutenir le projet » ouvre une page de contribution PayPal où tu choisis le montant."],
    }),
    ("0.7.5", "24.9.2026", {
        "bs": ["„Podrži projekat“: dobrovoljni prilog preko PayPal-a (statusna traka, Pomoć, povremeni podsjetnik koji se može sakriti). Prilog ništa ne otključava."],
        "en": ["\u201cSupport the project\u201d: voluntary contribution via PayPal (status bar, Help, an occasional reminder you can hide). A contribution unlocks nothing."],
        "de": ["\u201eProjekt unterstützen\u201c: freiwilliger Beitrag über PayPal (Statusleiste, Hilfe, gelegentliche ausblendbare Erinnerung). Ein Beitrag schaltet nichts frei."],
        "es": ["«Apoyar el proyecto»: aportación voluntaria por PayPal (barra de estado, Ayuda, un recordatorio ocasional que se puede ocultar). La aportación no desbloquea nada."],
        "fr": ["« Soutenir le projet » : contribution volontaire via PayPal (barre d'état, Aide, un rappel occasionnel masquable). Une contribution ne débloque rien."],
    }),
    ("0.7.4", "24.9.2026", {
        "bs": ["Licencni ugovor, uslovi korištenja i politika privatnosti na 5 jezika u instaleru i u Pomoć \u2192 Ugovori i licence.",
               "Puni tekstovi licenci komponenti (FFmpeg, Qt, Node.js, yt-dlp…) u folderu „licenses\u201c."],
        "en": ["License agreement, terms of use and privacy policy in 5 languages, in the installer and under Help \u2192 Agreements and licenses.",
               "Full license texts of the components (FFmpeg, Qt, Node.js, yt-dlp…) in the \u201clicenses\u201d folder."],
        "de": ["Lizenzvertrag, Nutzungsbedingungen und Datenschutzerklärung in 5 Sprachen, im Installer und unter Hilfe \u2192 Verträge und Lizenzen.",
               "Vollständige Lizenztexte der Komponenten (FFmpeg, Qt, Node.js, yt-dlp…) im Ordner \u201elicenses\u201c."],
        "es": ["Contrato de licencia, condiciones de uso y política de privacidad en 5 idiomas, en el instalador y en Ayuda \u2192 Contratos y licencias.",
               "Textos completos de las licencias de los componentes (FFmpeg, Qt, Node.js, yt-dlp…) en la carpeta «licenses»."],
        "fr": ["Contrat de licence, conditions d'utilisation et politique de confidentialité en 5 langues, dans l'installateur et dans Aide \u2192 Contrats et licences.",
               "Textes complets des licences des composants (FFmpeg, Qt, Node.js, yt-dlp…) dans le dossier « licenses »."],
    }),
    ("0.7.3", "24.9.2026", {
        "bs": ["Dugme „MP3“ na kartici preuzetog MP4 videa, pored foldera: pretvara video u MP3, a MP4 ostaje."],
        "en": ["“MP3” button on the card of a downloaded MP4 video, next to the folder: converts it to MP3 and keeps the MP4."],
        "de": ["Schaltfläche „MP3“ auf der Karte eines geladenen MP4-Videos, neben dem Ordner: wandelt in MP3 um, die MP4 bleibt."],
        "es": ["Botón «MP3» en la tarjeta de un vídeo MP4 descargado, junto a la carpeta: lo convierte a MP3 y conserva el MP4."],
        "fr": ["Bouton « MP3 » sur la carte d'une vidéo MP4 téléchargée, à côté du dossier : la convertit en MP3 et garde le MP4."],
    }),
    ("0.7.2", "24.9.2026", {
        "bs": ["Uslovi korištenja: prihvataju se u instaleru i stoje u Pomoć → Uslovi korištenja."],
        "en": ["Terms of use: accepted in the installer and available under Help → Terms of use."],
        "de": ["Nutzungsbedingungen: werden im Installer akzeptiert und stehen unter Hilfe → Nutzungsbedingungen."],
        "es": ["Condiciones de uso: se aceptan en el instalador y están en Ayuda → Condiciones de uso."],
        "fr": ["Conditions d'utilisation : acceptées dans l'installateur et disponibles dans Aide → Conditions d'utilisation."],
    }),
    ("0.7.1", "23.9.2026", {
        "bs": ["Pomoć → Šta je novo: kratke bilješke o izmjenama po verzijama."],
        "en": ["Help → What's new: short notes about the changes in each version."],
        "de": ["Hilfe → Was ist neu: kurze Hinweise zu den Änderungen jeder Version."],
        "es": ["Ayuda → Novedades: notas breves sobre los cambios de cada versión."],
        "fr": ["Aide → Nouveautés : courtes notes sur les changements de chaque version."],
    }),
    ("0.7.0", "23.9.2026", {
        "bs": ["Isječak videa (od–do) iz menija formata u redu.",
               "Titlovi uz video i sličica kao omot fajla.",
               "Ograničenje brzine i opcija da link videa iz plejliste preuzme cijelu plejlistu.",
               "MP3 u meniju desnog klika u browseru.",
               "Instaler je manji za trećinu (136 MB umjesto 198 MB)."],
        "en": ["Video clip (from–to) from the format menu of a row.",
               "Subtitles with the video and the thumbnail as file cover.",
               "Speed limit, and an option for a video link from a playlist to download the whole playlist.",
               "MP3 in the browser right-click menu.",
               "The installer is a third smaller (136 MB instead of 198 MB)."],
        "de": ["Videoausschnitt (von–bis) über das Formatmenü einer Zeile.",
               "Untertitel zum Video und Vorschaubild als Cover.",
               "Geschwindigkeitslimit und Option, bei einem Videolink aus einer Playlist die ganze Playlist zu laden.",
               "MP3 im Rechtsklickmenü des Browsers.",
               "Das Installationsprogramm ist ein Drittel kleiner (136 MB statt 198 MB)."],
        "es": ["Fragmento de vídeo (desde–hasta) desde el menú de formato de una fila.",
               "Subtítulos con el vídeo y la miniatura como portada.",
               "Límite de velocidad y opción para que un enlace de vídeo de una lista descargue la lista completa.",
               "MP3 en el menú contextual del navegador.",
               "El instalador es un tercio más pequeño (136 MB en lugar de 198 MB)."],
        "fr": ["Extrait vidéo (de–à) depuis le menu de format d'une ligne.",
               "Sous-titres avec la vidéo et miniature comme pochette.",
               "Limite de vitesse et option pour qu'un lien vidéo d'une playlist télécharge toute la playlist.",
               "MP3 dans le menu contextuel du navigateur.",
               "L'installateur est plus petit d'un tiers (136 Mo au lieu de 198 Mo)."],
    }),
    ("0.6.2", "23.9.2026", {
        "bs": ["Ažuriranje radi bez GitHub naloga i bez programa gh."],
        "en": ["Updating works without a GitHub account and without the gh program."],
        "de": ["Aktualisierung funktioniert ohne GitHub-Konto und ohne das Programm gh."],
        "es": ["La actualización funciona sin cuenta de GitHub y sin el programa gh."],
        "fr": ["La mise à jour fonctionne sans compte GitHub et sans le programme gh."],
    }),
    ("0.6.1", "22.9.2026", {
        "bs": ["Dugme „Preuzmi kao MP3“ u prozoru dodatka za browser."],
        "en": ["“Download as MP3” button in the browser extension window."],
        "de": ["Schaltfläche „Als MP3 herunterladen“ im Fenster der Browsererweiterung."],
        "es": ["Botón «Descargar como MP3» en la ventana de la extensión del navegador."],
        "fr": ["Bouton « Télécharger en MP3 » dans la fenêtre de l'extension du navigateur."],
    }),
    ("0.6.0", "22.9.2026", {
        "bs": ["Kopiran link sam ulazi u red.",
               "Red i istorija preuzimanja se pamte između pokretanja.",
               "Pomoć → Sačuvaj izvještaj o problemu."],
        "en": ["A copied link goes into the queue by itself.",
               "The queue and download history are kept between sessions.",
               "Help → Save a problem report."],
        "de": ["Ein kopierter Link kommt von selbst in die Liste.",
               "Liste und Download-Verlauf bleiben zwischen Sitzungen erhalten.",
               "Hilfe → Problembericht speichern."],
        "es": ["Un enlace copiado entra solo en la cola.",
               "La cola y el historial de descargas se conservan entre sesiones.",
               "Ayuda → Guardar un informe del problema."],
        "fr": ["Un lien copié entre tout seul dans la file.",
               "La file et l'historique des téléchargements sont conservés entre les sessions.",
               "Aide → Enregistrer un rapport de problème."],
    }),
    ("0.5.7", "17.9.2026", {
        "bs": ["Više istovremenih preuzimanja (1–4).",
               "Kad veza pukne, preuzimanje se samo ponavlja do 3 puta."],
        "en": ["Several simultaneous downloads (1–4).",
               "When the connection drops, the download is retried up to 3 times."],
        "de": ["Mehrere gleichzeitige Downloads (1–4).",
               "Bei Verbindungsabbruch wird der Download bis zu 3-mal wiederholt."],
        "es": ["Varias descargas simultáneas (1–4).",
               "Si se corta la conexión, la descarga se reintenta hasta 3 veces."],
        "fr": ["Plusieurs téléchargements simultanés (1–4).",
               "En cas de coupure, le téléchargement est relancé jusqu'à 3 fois."],
    }),
    ("0.5.6", "17.9.2026", {
        "bs": ["„Zaustavi“ reaguje odmah, i dok se link još čita."],
        "en": ["“Stop” reacts at once, even while a link is still being read."],
        "de": ["„Stopp“ reagiert sofort, auch während ein Link noch gelesen wird."],
        "es": ["«Detener» responde al instante, incluso mientras se lee un enlace."],
        "fr": ["« Arrêter » réagit tout de suite, même pendant la lecture d'un lien."],
    }),
    ("0.5.5", "17.9.2026", {
        "bs": ["Preuzimanje desnim klikom u browseru (link, video, video koji se pušta)."],
        "en": ["Download with a right-click in the browser (link, video, playing video)."],
        "de": ["Herunterladen per Rechtsklick im Browser (Link, Video, laufendes Video)."],
        "es": ["Descarga con clic derecho en el navegador (enlace, vídeo, vídeo en reproducción)."],
        "fr": ["Téléchargement par clic droit dans le navigateur (lien, vidéo, vidéo en cours)."],
    }),
    ("0.5.4", "17.9.2026", {
        "bs": ["Čitač sajtova (yt-dlp) se ažurira odvojeno od aplikacije."],
        "en": ["The site reader (yt-dlp) is updated separately from the app."],
        "de": ["Der Seiten-Reader (yt-dlp) wird getrennt von der App aktualisiert."],
        "es": ["El lector de sitios (yt-dlp) se actualiza aparte de la aplicación."],
        "fr": ["Le lecteur de sites (yt-dlp) est mis à jour séparément de l'application."],
    }),
    ("0.5.3", "17.9.2026", {
        "bs": ["Prenos uživo (LIVE) se ne preuzima, pa nema beskrajnog učitavanja."],
        "en": ["Live streams are not downloaded, so there is no endless loading."],
        "de": ["Livestreams werden nicht heruntergeladen, also kein endloses Laden."],
        "es": ["Las transmisiones en directo no se descargan, así que no hay carga infinita."],
        "fr": ["Les directs ne sont pas téléchargés, donc plus de chargement sans fin."],
    }),
    ("0.5.2", "17.9.2026", {
        "bs": ["Ispravljene ikonice dodatka za browser."],
        "en": ["Fixed the browser extension icons."],
        "de": ["Symbole der Browsererweiterung korrigiert."],
        "es": ["Corregidos los iconos de la extensión del navegador."],
        "fr": ["Icônes de l'extension du navigateur corrigées."],
    }),
    ("0.5.1", "17.9.2026", {
        "bs": ["Instaler na 5 jezika i automatsko ažuriranje (Pomoć → Provjeri ažuriranje)."],
        "en": ["Installer in 5 languages and automatic updates (Help → Check for updates)."],
        "de": ["Installationsprogramm in 5 Sprachen und automatische Updates (Hilfe → Nach Updates suchen)."],
        "es": ["Instalador en 5 idiomas y actualizaciones automáticas (Ayuda → Buscar actualizaciones)."],
        "fr": ["Installateur en 5 langues et mises à jour automatiques (Aide → Rechercher des mises à jour)."],
    }),
]


def entries(language: str) -> list[tuple[str, str, list[str]]]:
    """(verzija, datum, stavke) na traženom jeziku; nepoznat jezik dobija engleski."""
    return [(version, date, notes.get(language) or notes["en"]) for version, date, notes in CHANGES]


def to_html(language: str, current: str) -> str:
    parts = []
    for version, date, items in entries(language):
        marker = " ←" if version == current else ""
        parts.append(f"<h3 style='margin:12px 0 4px'>{escape(version)}"
                     f"<span style='color:#7a7a7a;font-weight:normal'> — {escape(date)}{marker}</span></h3>")
        parts.append("<ul style='margin-top:0'>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>")
    return "".join(parts)


def release_notes(version: str, language: str = "bs") -> str:
    """Tekst za opis izdanja na GitHub-u."""
    for entry_version, _date, items in entries(language):
        if entry_version == version:
            return "\n".join(f"- {item}" for item in items)
    raise KeyError(version)
