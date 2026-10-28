"""Zvanični sajt (folder site/): stranice iz istih izvora kao aplikacija, na više jezika.

Glavni jezik je engleski (site/), bosanski je u site/bs/ (Ahmedova odluka 25.9.2026). Za svaki jezik
pravi terms.html, privacy.html, licenses.html i extension.html iz tekstova u videodl/assets, a u
index.html (pisan ručno) osvježava „Šta je novo" (videodl/changelog.py) i verziju s veličinom instalera.
Pokreće se poslije svake izmjene tih tekstova i pri svakom izdanju; test provjerava da je sajt ažuran.

    python tools/build_site.py [--size-mb 130]
"""

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from videodl import __version__, changelog, legal  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_guides  # noqa: E402  (vodiči: MP3, isječak, plejlista…)
import site_home  # noqa: E402  (početna stranica: šablon i tekstovi)
import site_android  # noqa: E402  (Android tutorijal)
import site_impressum  # noqa: E402  (Impressum, tek kad ima podataka)
import site_winget  # noqa: E402  (winget vodič, tek kad Microsoft prihvati paket)
import site_release  # noqa: E402  (stranica „1.0", sama se uključi od verzije 1.0.0)

SITE = ROOT / "site"
ASSETS = ROOT / "videodl" / "assets"
NEWS_COUNT = 3
REPO = "https://github.com/abnps/video-download"
CONTACT_EMAIL = "abnpsdev@gmail.com"  # javni kontakt projekta (Ahmedova odluka 26.9.2026); lični e-mail nikad
INSTALLER_URL = f"{REPO}/releases/latest/download/VideoDownload-Setup.exe"
PUBLIC_URL = "https://abnps.github.io/video-download/"  # javna adresa sajta (kanonske adrese, mapa sajta)
OG_LOCALES = {"en": "en_US", "bs": "bs_BA", "de": "de_DE", "es": "es_ES", "fr": "fr_FR"}
# Mac (beta): stalna kopija .dmg-a uz posljednje izdanje (kao VideoDownload-Setup.exe za Windows).
MAC_DMG_URL = f"{REPO}/releases/latest/download/VideoDownload-macOS-arm64.dmg"
LINUX_APPIMAGE_URL = f"{REPO}/releases/latest/download/VideoDownload-linux-x86_64.AppImage"

# Android (beta, Ahmed 27.9.2026: „kao Mac beta, na GitHubu"): APK je u posljednjem izdanju (stalno ime), a nove
# verzije aplikacija sama nađe preko android.json iz istog izdanja. (uvod, dugme, napomena, koraci)
ANDROID_APK_URL = f"{REPO}/releases/latest/download/VideoDownload-android.apk"
ANDROID_TEXT = {
    "en": ("<b>New: Video Download for Android.</b> For phones with Android 10 or later. Share a video from any app "
           "and pick the quality. It works, but only a few people have tried it so far: please "
           "<a href=\"{issue}\">report anything that doesn't work</a>.",
           "Download for Android (beta)",
           "The app isn't in Google Play, so the first install takes a few extra taps:",
           ("Open the downloaded file (Downloads or the browser's download list).",
            "If Android asks, allow installing apps from your browser: <b>Settings → Allow from this source</b>.",
            "If <b>Auto Blocker</b> blocks the install on a Samsung phone, turn it off only for the install (Settings → Security and privacy) and turn it back on afterwards.",
            "If Google Play Protect warns about an unknown app, tap <b>More details → Install anyway</b>.",
            "Later versions install from the app itself: <b>Settings → Check for updates</b>.")),
    "bs": ("<b>Novo: Video Download za Android.</b> Za telefone s Androidom 10 ili novijim. Podijeli video iz bilo koje "
           "aplikacije i izaberi kvalitet. Radi, ali ga je probalo još malo ljudi: "
           "<a href=\"{issue}\">javi ako nešto ne radi</a>.",
           "Preuzmi za Android (beta)",
           "Aplikacija nije na Google Playu, pa prva instalacija traži par tapova više:",
           ("Otvori preuzeti fajl (Preuzimanja ili lista preuzimanja u pregledniku).",
            "Ako Android pita, dozvoli instalaciju iz preglednika: <b>Podešavanja → Dozvoli iz ovog izvora</b>.",
            "Ako <b>Auto Blocker</b> na Samsung telefonu blokira instalaciju, isključi ga samo za instalaciju (Podešavanja → Sigurnost i privatnost), a poslije ga ponovo uključi.",
            "Ako Google Play Protect upozori na nepoznatu aplikaciju, tapni <b>Više detalja → Ipak instaliraj</b>.",
            "Nove verzije se instaliraju iz same aplikacije: <b>Postavke → Provjeri ažuriranje</b>.")),
    "de": ("<b>Neu: Video Download für Android.</b> Für Handys mit Android 10 oder neuer. Teile ein Video aus einer "
           "beliebigen App und wähle die Qualität. Es funktioniert, aber bisher haben es nur wenige ausprobiert: "
           "<a href=\"{issue}\">melde bitte alles, was nicht klappt</a>.",
           "Für Android herunterladen (Beta)",
           "Die App ist nicht bei Google Play, daher braucht die erste Installation ein paar Fingertipps mehr:",
           ("Öffne die heruntergeladene Datei (Downloads oder Downloadliste des Browsers).",
            "Wenn Android fragt, erlaube Installationen aus deinem Browser: <b>Einstellungen → Von dieser Quelle zulassen</b>.",
            "Falls der <b>Auto Blocker</b> auf einem Samsung-Handy die Installation blockiert, ihn nur dafür ausschalten (Einstellungen → Sicherheit und Datenschutz) und danach wieder einschalten.",
            "Wenn Google Play Protect vor einer unbekannten App warnt, tippe auf <b>Weitere Details → Trotzdem installieren</b>.",
            "Neue Versionen installierst du direkt in der App: <b>Einstellungen → Nach Updates suchen</b>.")),
    "es": ("<b>Novedad: Video Download para Android.</b> Para móviles con Android 10 o posterior. Comparte un vídeo "
           "desde cualquier app y elige la calidad. Funciona, pero aún lo han probado pocas personas: "
           "<a href=\"{issue}\">avisa si algo no funciona</a>.",
           "Descargar para Android (beta)",
           "La app no está en Google Play, así que la primera instalación requiere unos toques más:",
           ("Abre el archivo descargado (Descargas o la lista de descargas del navegador).",
            "Si Android lo pide, permite instalar apps desde tu navegador: <b>Ajustes → Permitir de esta fuente</b>.",
            "Si <b>Auto Blocker</b> bloquea la instalación en un móvil Samsung, desactívalo solo para instalar (Ajustes → Seguridad y privacidad) y vuelve a activarlo después.",
            "Si Google Play Protect avisa de una app desconocida, pulsa <b>Más detalles → Instalar de todas formas</b>.",
            "Las nuevas versiones se instalan desde la propia app: <b>Ajustes → Buscar actualizaciones</b>.")),
    "fr": ("<b>Nouveau : Video Download pour Android.</b> Pour les téléphones sous Android 10 ou plus récent. Partagez "
           "une vidéo depuis n'importe quelle application et choisissez la qualité. Ça fonctionne, mais peu de personnes "
           "l'ont encore essayé : <a href=\"{issue}\">signalez tout ce qui ne marche pas</a>.",
           "Télécharger pour Android (bêta)",
           "L'application n'est pas sur Google Play, la première installation demande donc quelques touches de plus :",
           ("Ouvrez le fichier téléchargé (Téléchargements ou la liste des téléchargements du navigateur).",
            "Si Android le demande, autorisez l'installation depuis votre navigateur : <b>Paramètres → Autoriser cette source</b>.",
            "Si <b>Auto Blocker</b> bloque l'installation sur un téléphone Samsung, désactivez-le seulement pour installer (Paramètres → Sécurité et confidentialité), puis réactivez-le.",
            "Si Google Play Protect signale une application inconnue, touchez <b>Plus de détails → Installer quand même</b>.",
            "Les nouvelles versions s'installent depuis l'application : <b>Réglages → Rechercher des mises à jour</b>.")),
}
# Obtainium (besplatan, otvoren kod) dodaje aplikaciju direktno s GitHuba i sam je ažurira; zvanična stranica
# za preusmjeravanje otvara Obtainium na telefonu (Ahmed 5.10.2026, umjesto Google Playa).
OBTAINIUM_URL = f"https://apps.obtainium.imranr.dev/redirect?r=obtainium://add/{REPO}"
OBTAINIUM_TEXT = {
    "en": ("Use <b>Obtainium</b>? It installs the app straight from GitHub and keeps it up to date.",
           "Add to Obtainium"),
    "bs": ("Koristiš <b>Obtainium</b>? On instalira aplikaciju direktno s GitHuba i sam je ažurira.",
           "Dodaj u Obtainium"),
    "de": ("Nutzt du <b>Obtainium</b>? Es installiert die App direkt von GitHub und hält sie aktuell.",
           "Zu Obtainium hinzufügen"),
    "es": ("¿Usas <b>Obtainium</b>? Instala la app directamente desde GitHub y la mantiene actualizada.",
           "Añadir a Obtainium"),
    "fr": ("Vous utilisez <b>Obtainium</b> ? Il installe l'application directement depuis GitHub et la tient à jour.",
           "Ajouter à Obtainium"),
}
ISSUE_URL = f"{REPO}/issues/new?template=problem.yml"
INSTALL_DIR = r"%LOCALAPPDATA%\Programs\Video Download\extension"
GITHUB_PRIVACY = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"

# Riječi koje reklamne stranice ne smiju sadržavati (plan sajta: bez tuđih znakova i „zaobiđi zaštitu").
# Pravni tekstovi se ne provjeravaju: moraju biti doslovno isti kao u programu i instaleru.
FORBIDDEN = re.compile(r"youtube|\byt\b(?!-dlp)|tiktok|netflix|spotify|zaobi[đd]|crack|piratsk|besplatna muzika"
                       r"|free music|bypass|umgeh|kostenlose musik|eludir|música gratis|contourn|musique gratuite",
                       re.IGNORECASE)
PROMO_PAGES = ("index.html", "extension.html", "changelog.html", "guides.html",
               *(f"{slug}.html" for slug in site_guides.GUIDES), site_release.PAGE, site_winget.PAGE)

# Tekstovi stranica po jeziku. Prvi jezik je glavni (korijen sajta).
TEXTS = {
    "en": {
        "dir": "", "nav": ("Features", "How it works", "What's new", "Help", "♥ Support"),
        "anchors": ("features", "how", "news", "help", "support"),
        "home": "← Home", "version": "Version",
        "footer": ("Terms of use", "Privacy", "Licenses"),
        "terms_title": "Terms of use",
        "terms_lead": "The same text the installer asks you to accept (also in the app: Help → Agreements and licenses).",
        "terms_desc": "Terms of use and license agreement of Video Download.",
        "privacy_title": "Privacy", "privacy_lead": "Neither the website nor the app collects data about you.",
        "privacy_desc": "Privacy policy of the Video Download website and app.",
        "privacy_site": "This website", "privacy_app": "The app",
        "privacy_items": (
            "The website has no cookies, analytics, ads or forms and stores nothing in your browser.",
            "The website is hosted on GitHub Pages (GitHub, Inc.). Like any server, GitHub records technical data "
            f"such as your IP address for security and operation; see <a href=\"{GITHUB_PRIVACY}\">GitHub's privacy statement</a>.",
            "The installer is downloaded from GitHub (same terms as above).",
            "The support button leads to PayPal; PayPal only receives data when you open it, under its own rules.",
            "<b>Problem reports</b> go to GitHub Issues and are <b>public</b> (a GitHub account is needed). The app's "
            "problem report shortens links to the site name and hides your Windows user name; don't add passwords, "
            "cookies or personal data.",
            "<b>Contributions</b> are processed by PayPal. As the recipient, the author sees what PayPal shows for every "
            "payment (e.g. the payer's name and e-mail) and uses it only for bookkeeping, never for advertising or "
            "anything else.",
            "The <b>Share</b> button uses your device's own sharing or opens the network you choose; that network gets the link only when you click it.",
            "Messages to <b>abnpsdev@gmail.com</b> (the project's contact address, a Gmail mailbox at Google) are used "
            "only to reply to you and are never passed on or used for anything else.",
        ),
        "licenses_title": "Licenses",
        "licenses_lead": "Video Download uses the following software by other authors. Their licenses apply to them; the "
                         "full license texts are in the <code>licenses</code> folder next to the installed app.",
        "licenses_desc": "Licenses of the components used by Video Download.",
        "licenses_cols": ("Component", "License"),
        "licenses_android": ('Android (beta)', 'The Android app also shows these licenses in Settings → Open-source licenses.'),
        "licenses_note": "FFmpeg is licensed under GPL-3.0: the source code of the exact build in the installer is at the "
                         "links above, and a copy of the source code is also available on request.",
        "ext_title": "Browser extension",
        "ext_desc": "How to install the Video Download extension in Firefox, Edge and Chrome.",
        "ext_body": """<h2 style="margin-top:0">Chrome: by hand, in 3 steps</h2>
<p>Install the app first (the extension comes with it). Chrome has no store version, so it is loaded once from the app folder:</p>
<ol>
<li>In the app open <b>Help → Downloading from the browser</b> and click <b>Copy the folder path</b>.</li>
<li>Click <b>Open extensions in Chrome</b> (or open <code>chrome://extensions</code>) and turn on <b>Developer mode</b> (top right).</li>
<li>Click <b>Load unpacked</b>, paste the path (Ctrl+V) into the folder field and click <b>Select Folder</b>. Then pin the
Video Download icon (puzzle icon → pin).</li>
</ol>
<div class="box">Chrome may remind you about “Developer mode”; that is expected. After an app update, if the extension stops
responding, click <b>Reload</b> next to it in <code>chrome://extensions</code>. Firefox and Edge update the extension by themselves.</div>
<h2>Using it</h2>
<ul>
<li>Play a video on the page and click the Video Download icon: <b>Download the playing video</b> or <b>Download as MP3</b>.</li>
<li>Right-click a link or video: <b>Download this link</b> or <b>…as MP3</b>.</li>
<li>If the app isn't running, the click starts it.</li>
<li>Live streams and DRM-protected video are not downloaded.</li>
</ul>""",
    },
    "bs": {
        "dir": "bs/", "nav": ("Funkcije", "Kako radi", "Šta je novo", "Pomoć", "♥ Podrži"),
        "anchors": ("features", "how", "news", "help", "support"),
        "home": "← Početna", "version": "Verzija",
        "footer": ("Uslovi korištenja", "Privatnost", "Licence"),
        "terms_title": "Uslovi korištenja",
        "terms_lead": "Isti tekst koji instaler traži da prihvatiš (i koji je u programu: Pomoć → Ugovori i licence).",
        "terms_desc": "Uslovi korištenja i licencni ugovor programa Video Download.",
        "privacy_title": "Privatnost", "privacy_lead": "Ni sajt ni program ne prikupljaju podatke o tebi.",
        "privacy_desc": "Politika privatnosti sajta i programa Video Download.",
        "privacy_site": "Ovaj sajt", "privacy_app": "Program",
        "privacy_items": (
            "Sajt nema kolačića, analitike, reklama ni formulara i ništa ne sprema u tvoj browser.",
            "Sajt je na GitHub Pages (GitHub, Inc.). GitHub pri svakoj posjeti, kao svaki server, bilježi tehničke podatke, "
            f"npr. IP adresu, radi sigurnosti i rada servisa; vidi <a href=\"{GITHUB_PRIVACY}\">izjavu o privatnosti GitHub-a</a>.",
            "Instaler se preuzima sa GitHub-a (isti uslovi kao gore).",
            "Dugme za prilog vodi na PayPal; PayPal dobija podatke tek kad ga otvoriš, po svojim pravilima.",
            "<b>Prijave problema</b> idu na GitHub Issues i <b>javne su</b> (treba GitHub nalog). Izvještaj iz programa "
            "skraćuje linkove na ime sajta i skriva tvoje korisničko ime u Windowsu; ne dodaj lozinke, kolačiće ni lične podatke.",
            "<b>Prilozi</b> idu preko PayPal-a. Kao primalac, autor vidi ono što PayPal pokazuje za svaku uplatu (npr. ime i "
            "e-mail uplatioca) i koristi to samo za evidenciju, nikad za reklame ni bilo šta drugo.",
            "Dugme <b>Podijeli</b> koristi dijeljenje tvog uređaja ili otvara mrežu koju izabereš; ta mreža dobija link tek kad klikneš.",
            "Poruke na <b>abnpsdev@gmail.com</b> (kontakt adresa projekta, Gmail sanduče kod Google-a) koriste se samo za "
            "odgovor tebi i nikad se ne prosljeđuju niti koriste za bilo šta drugo.",
        ),
        "licenses_title": "Licence",
        "licenses_lead": "Video Download koristi sljedeći softver drugih autora. Njihove licence važe za njih; puni tekstovi "
                         "licenci su u folderu <code>licenses</code> pored instaliranog programa.",
        "licenses_desc": "Licence komponenti koje koristi Video Download.",
        "licenses_cols": ("Komponenta", "Licenca"),
        "licenses_android": ('Android (beta)', 'Android aplikacija ove licence prikazuje i u Postavke → Licence otvorenog koda.'),
        "licenses_note": "FFmpeg je pod licencom GPL-3.0: izvorni kod tačnog builda koji je u instaleru je na linkovima "
                         "iznad, a kopiju izvornog koda možeš dobiti i na zahtjev.",
        "ext_title": "Dodatak za browser",
        "ext_desc": "Kako instalirati dodatak Video Download u Firefox, Edge i Chrome.",
        "ext_body": """<h2 style="margin-top:0">Chrome: ručno, u 3 koraka</h2>
<p>Prvo instaliraj program (dodatak dolazi s njim). Chrome nema verziju iz prodavnice, pa se dodatak jednom učita iz foldera programa:</p>
<ol>
<li>U programu otvori <b>Pomoć → Preuzimanje iz browsera</b> i klikni <b>Kopiraj putanju foldera</b>.</li>
<li>Klikni <b>Otvori dodatke u Chrome-u</b> (ili otvori <code>chrome://extensions</code>) i uključi <b>Developer mode</b> (gore desno).</li>
<li>Klikni <b>Load unpacked</b> (Učitaj raspakovano), zalijepi putanju (Ctrl+V) u polje za folder i klikni <b>Select Folder</b>.
Na kraju prikvači ikonu Video Download (ikona slagalice → pribadača).</li>
</ol>
<div class="box">Chrome ponekad podsjeti na „Developer mode“; to je očekivano. Ako poslije ažuriranja programa dodatak prestane
reagovati, u <code>chrome://extensions</code> klikni <b>Reload</b> kod njega. Firefox i Edge dodatak ažuriraju sami.</div>
<h2>Korištenje</h2>
<ul>
<li>Pusti video na stranici i klikni ikonu Video Download: <b>Preuzmi video koji se pušta</b> ili <b>Preuzmi kao MP3</b>.</li>
<li>Desni klik na link ili video: <b>Preuzmi ovaj link</b> ili <b>…kao MP3</b>.</li>
<li>Ako program nije pokrenut, klik ga sam pokreće.</li>
<li>Prenos uživo i video zaštićen DRM-om se ne preuzimaju.</li>
</ul>""",
    },
    "de": {
        "dir": "de/", "nav": ("Funktionen", "So funktioniert's", "Neuigkeiten", "Hilfe", "♥ Unterstützen"),
        "anchors": ("features", "how", "news", "help", "support"),
        "home": "← Startseite", "version": "Version",
        "footer": ("Nutzungsbedingungen", "Datenschutz", "Lizenzen"),
        "terms_title": "Nutzungsbedingungen",
        "terms_lead": "Derselbe Text, den du im Installer akzeptierst (auch in der App: Hilfe → Verträge und Lizenzen).",
        "terms_desc": "Nutzungsbedingungen und Lizenzvertrag von Video Download.",
        "privacy_title": "Datenschutz", "privacy_lead": "Weder die Webseite noch die App sammeln Daten über dich.",
        "privacy_desc": "Datenschutzerklärung der Webseite und der App Video Download.",
        "privacy_site": "Diese Webseite", "privacy_app": "Die App",
        "privacy_items": (
            "Die Webseite hat keine Cookies, keine Analyse, keine Werbung und keine Formulare und speichert nichts in deinem Browser.",
            "Die Webseite liegt auf GitHub Pages (GitHub, Inc.). Wie jeder Server erfasst GitHub technische Daten wie deine "
            f"IP-Adresse für Sicherheit und Betrieb; siehe die <a href=\"{GITHUB_PRIVACY}\">Datenschutzerklärung von GitHub</a>.",
            "Der Installer wird von GitHub heruntergeladen (gleiche Bedingungen wie oben).",
            "Der Knopf zum Unterstützen führt zu PayPal; PayPal erhält Daten erst, wenn du ihn öffnest, nach eigenen Regeln.",
            "<b>Problemmeldungen</b> gehen an GitHub Issues und sind <b>öffentlich</b> (ein GitHub-Konto ist nötig). Der "
            "Problembericht der App kürzt Links auf den Namen der Seite und verbirgt deinen Windows-Benutzernamen; füge keine "
            "Passwörter, Cookies oder persönlichen Daten hinzu.",
            "<b>Beiträge</b> werden über PayPal abgewickelt. Als Empfänger sieht der Autor, was PayPal zu jeder Zahlung anzeigt "
            "(z. B. Name und E-Mail des Zahlenden), und nutzt es nur für die Buchhaltung, nie für Werbung oder etwas anderes.",
            "Der Knopf <b>Teilen</b> nutzt das Teilen deines Geräts oder öffnet das gewählte Netzwerk; dieses erhält den Link erst, wenn du klickst.",
            "Nachrichten an <b>abnpsdev@gmail.com</b> (die Kontaktadresse des Projekts, ein Gmail-Postfach bei Google) "
            "werden nur genutzt, um dir zu antworten, und nie weitergegeben oder anders verwendet.",
        ),
        "licenses_title": "Lizenzen",
        "licenses_lead": "Video Download nutzt die folgende Software anderer Autoren. Für sie gelten ihre eigenen Lizenzen; die "
                         "vollständigen Lizenztexte liegen im Ordner <code>licenses</code> neben der installierten App.",
        "licenses_desc": "Lizenzen der Komponenten, die Video Download nutzt.",
        "licenses_cols": ("Komponente", "Lizenz"),
        "licenses_android": ('Android (Beta)', 'Die Android-App zeigt diese Lizenzen auch unter Einstellungen → Open-Source-Lizenzen.'),
        "licenses_note": "FFmpeg steht unter GPL-3.0: Der Quellcode genau des Builds im Installer ist unter den Links oben, "
                         "und eine Kopie des Quellcodes gibt es auch auf Anfrage.",
        "ext_title": "Browser-Erweiterung",
        "ext_desc": "So installierst du die Erweiterung Video Download in Firefox, Edge und Chrome.",
        "ext_body": """<h2 style="margin-top:0">Chrome: manuell, in 3 Schritten</h2>
<p>Installiere zuerst die App (die Erweiterung ist dabei). Für Chrome gibt es keine Store-Version, daher wird sie einmal aus dem App-Ordner geladen:</p>
<ol>
<li>Öffne in der App <b>Hilfe → Aus dem Browser herunterladen</b> und klicke auf <b>Ordnerpfad kopieren</b>.</li>
<li>Klicke auf <b>Erweiterungen in Chrome öffnen</b> (oder öffne <code>chrome://extensions</code>) und schalte den
<b>Entwicklermodus</b> ein (oben rechts).</li>
<li>Klicke auf <b>Entpackte Erweiterung laden</b>, füge den Pfad (Strg+V) in das Ordnerfeld ein und klicke auf
<b>Ordner auswählen</b>. Hefte dann das Symbol von Video Download an (Puzzle-Symbol → Anheften).</li>
</ol>
<div class="box">Chrome erinnert eventuell an den „Entwicklermodus“; das ist normal. Reagiert die Erweiterung nach einem App-Update
nicht mehr, klicke in <code>chrome://extensions</code> bei ihr auf <b>Neu laden</b>. Firefox und Edge aktualisieren die Erweiterung selbst.</div>
<h2>Verwendung</h2>
<ul>
<li>Spiele ein Video ab und klicke auf das Symbol von Video Download: <b>Laufendes Video herunterladen</b> oder <b>Als MP3 herunterladen</b>.</li>
<li>Rechtsklick auf einen Link oder ein Video: <b>Diesen Link herunterladen</b> oder <b>…als MP3</b>.</li>
<li>Läuft die App nicht, startet der Klick sie.</li>
<li>Livestreams und DRM-geschützte Videos werden nicht heruntergeladen.</li>
</ul>""",
    },
    "es": {
        "dir": "es/", "nav": ("Funciones", "Cómo funciona", "Novedades", "Ayuda", "♥ Apoyar"),
        "anchors": ("features", "how", "news", "help", "support"),
        "home": "← Inicio", "version": "Versión",
        "footer": ("Condiciones de uso", "Privacidad", "Licencias"),
        "terms_title": "Condiciones de uso",
        "terms_lead": "El mismo texto que el instalador te pide aceptar (también en la aplicación: Ayuda → Contratos y licencias).",
        "terms_desc": "Condiciones de uso y contrato de licencia de Video Download.",
        "privacy_title": "Privacidad", "privacy_lead": "Ni el sitio web ni la aplicación recogen datos sobre ti.",
        "privacy_desc": "Política de privacidad del sitio web y de la aplicación Video Download.",
        "privacy_site": "Este sitio web", "privacy_app": "La aplicación",
        "privacy_items": (
            "El sitio web no tiene cookies, analítica, anuncios ni formularios, y no guarda nada en tu navegador.",
            "El sitio web está alojado en GitHub Pages (GitHub, Inc.). Como cualquier servidor, GitHub registra datos técnicos "
            f"como tu dirección IP por seguridad y funcionamiento; consulta la <a href=\"{GITHUB_PRIVACY}\">declaración de "
            "privacidad de GitHub</a>.",
            "El instalador se descarga de GitHub (mismas condiciones que arriba).",
            "El botón de apoyo lleva a PayPal; PayPal solo recibe datos cuando lo abres, según sus propias normas.",
            "<b>Los informes de problemas</b> van a GitHub Issues y son <b>públicos</b> (hace falta una cuenta de GitHub). El "
            "informe de la aplicación acorta los enlaces al nombre del sitio y oculta tu nombre de usuario de Windows; no añadas "
            "contraseñas, cookies ni datos personales.",
            "<b>Las contribuciones</b> las procesa PayPal. Como destinatario, el autor ve lo que PayPal muestra de cada pago "
            "(p. ej., el nombre y el correo de quien paga) y lo usa solo para la contabilidad, nunca para publicidad ni nada más.",
            "El botón <b>Compartir</b> usa el uso compartido de tu dispositivo o abre la red que elijas; esa red recibe el enlace solo cuando pulsas.",
            "Los mensajes a <b>abnpsdev@gmail.com</b> (la dirección de contacto del proyecto, un buzón de Gmail en Google) "
            "se usan solo para responderte y nunca se comparten ni se usan para nada más.",
        ),
        "licenses_title": "Licencias",
        "licenses_lead": "Video Download usa el siguiente software de otros autores. Se rige por sus propias licencias; los textos "
                         "completos están en la carpeta <code>licenses</code> junto a la aplicación instalada.",
        "licenses_desc": "Licencias de los componentes que usa Video Download.",
        "licenses_cols": ("Componente", "Licencia"),
        "licenses_android": ('Android (beta)', 'La app de Android también muestra estas licencias en Ajustes → Licencias de código abierto.'),
        "licenses_note": "FFmpeg tiene licencia GPL-3.0: el código fuente de la compilación exacta del instalador está en los "
                         "enlaces de arriba, y también puedes pedir una copia del código fuente.",
        "ext_title": "Extensión para el navegador",
        "ext_desc": "Cómo instalar la extensión Video Download en Firefox, Edge y Chrome.",
        "ext_body": """<h2 style="margin-top:0">Chrome: a mano, en 3 pasos</h2>
<p>Instala primero la aplicación (la extensión viene con ella). Chrome no tiene versión en tienda, así que se carga una vez desde la carpeta de la aplicación:</p>
<ol>
<li>En la aplicación abre <b>Ayuda → Descargar desde el navegador</b> y pulsa <b>Copiar la ruta de la carpeta</b>.</li>
<li>Pulsa <b>Abrir extensiones en Chrome</b> (o abre <code>chrome://extensions</code>) y activa el <b>Modo de desarrollador</b>
(arriba a la derecha).</li>
<li>Pulsa <b>Cargar descomprimida</b>, pega la ruta (Ctrl+V) en el campo de carpeta y pulsa <b>Seleccionar carpeta</b>.
Después fija el icono de Video Download (icono de puzle → fijar).</li>
</ol>
<div class="box">Chrome puede recordarte el «Modo de desarrollador»; es normal. Si tras actualizar la aplicación la extensión deja de
responder, pulsa <b>Recargar</b> junto a ella en <code>chrome://extensions</code>. Firefox y Edge actualizan la extensión solos.</div>
<h2>Uso</h2>
<ul>
<li>Reproduce un vídeo y pulsa el icono de Video Download: <b>Descargar el vídeo en reproducción</b> o <b>Descargar como MP3</b>.</li>
<li>Clic derecho en un enlace o vídeo: <b>Descargar este enlace</b> o <b>…como MP3</b>.</li>
<li>Si la aplicación no está abierta, el clic la inicia.</li>
<li>Las emisiones en directo y los vídeos con DRM no se descargan.</li>
</ul>""",
    },
    "fr": {
        "dir": "fr/", "nav": ("Fonctions", "Comment ça marche", "Nouveautés", "Aide", "♥ Soutenir"),
        "anchors": ("features", "how", "news", "help", "support"),
        "home": "← Accueil", "version": "Version",
        "footer": ("Conditions d'utilisation", "Confidentialité", "Licences"),
        "terms_title": "Conditions d'utilisation",
        "terms_lead": "Le même texte que le programme d'installation vous demande d'accepter (aussi dans l'application : "
                      "Aide → Contrats et licences).",
        "terms_desc": "Conditions d'utilisation et contrat de licence de Video Download.",
        "privacy_title": "Confidentialité", "privacy_lead": "Ni le site ni l'application ne collectent de données sur vous.",
        "privacy_desc": "Politique de confidentialité du site et de l'application Video Download.",
        "privacy_site": "Ce site", "privacy_app": "L'application",
        "privacy_items": (
            "Le site n'a ni cookies, ni mesure d'audience, ni publicité, ni formulaire, et n'enregistre rien dans votre navigateur.",
            "Le site est hébergé sur GitHub Pages (GitHub, Inc.). Comme tout serveur, GitHub enregistre des données techniques "
            "telles que votre adresse IP pour la sécurité et le fonctionnement ; voir la "
            f"<a href=\"{GITHUB_PRIVACY}\">déclaration de confidentialité de GitHub</a>.",
            "Le programme d'installation est téléchargé depuis GitHub (mêmes conditions que ci-dessus).",
            "Le bouton de soutien mène à PayPal ; PayPal ne reçoit des données que lorsque vous l'ouvrez, selon ses propres règles.",
            "<b>Les signalements de problème</b> vont dans GitHub Issues et sont <b>publics</b> (un compte GitHub est nécessaire). "
            "Le rapport de l'application raccourcit les liens au nom du site et masque votre nom d'utilisateur Windows ; "
            "n'ajoutez ni mots de passe, ni cookies, ni données personnelles.",
            "<b>Les contributions</b> sont traitées par PayPal. En tant que destinataire, l'auteur voit ce que PayPal affiche pour "
            "chaque paiement (p. ex. le nom et l'e-mail du payeur) et ne l'utilise que pour la comptabilité, jamais pour la "
            "publicité ni autre chose.",
            "Le bouton <b>Partager</b> utilise le partage de votre appareil ou ouvre le réseau choisi ; ce réseau ne reçoit le lien que lorsque vous cliquez.",
            "Les messages envoyés à <b>abnpsdev@gmail.com</b> (l'adresse de contact du projet, une boîte Gmail chez "
            "Google) servent uniquement à vous répondre et ne sont jamais transmis ni utilisés à d'autres fins.",
        ),
        "licenses_title": "Licences",
        "licenses_lead": "Video Download utilise les logiciels suivants d'autres auteurs. Leurs propres licences s'appliquent ; "
                         "les textes complets se trouvent dans le dossier <code>licenses</code> à côté de l'application installée.",
        "licenses_desc": "Licences des composants utilisés par Video Download.",
        "licenses_cols": ("Composant", "Licence"),
        "licenses_android": ('Android (bêta)', "L'application Android affiche aussi ces licences dans Réglages → Licences open source."),
        "licenses_note": "FFmpeg est sous licence GPL-3.0 : le code source de la version exacte incluse dans le programme "
                         "d'installation se trouve aux liens ci-dessus, et une copie du code source est aussi disponible sur demande.",
        "ext_title": "Extension pour le navigateur",
        "ext_desc": "Comment installer l'extension Video Download dans Firefox, Edge et Chrome.",
        "ext_body": """<h2 style="margin-top:0">Chrome : à la main, en 3 étapes</h2>
<p>Installez d'abord l'application (l'extension est incluse). Chrome n'a pas de version en boutique : l'extension se charge une fois depuis le dossier de l'application :</p>
<ol>
<li>Dans l'application, ouvrez <b>Aide → Télécharger depuis le navigateur</b> et cliquez sur <b>Copier le chemin du dossier</b>.</li>
<li>Cliquez sur <b>Ouvrir les extensions dans Chrome</b> (ou ouvrez <code>chrome://extensions</code>) et activez le
<b>Mode développeur</b> (en haut à droite).</li>
<li>Cliquez sur <b>Charger l'extension non empaquetée</b>, collez le chemin (Ctrl+V) dans le champ du dossier et cliquez sur
<b>Sélectionner un dossier</b>. Épinglez ensuite l'icône de Video Download (icône puzzle → épingler).</li>
</ol>
<div class="box">Chrome peut vous rappeler le « Mode développeur » ; c'est normal. Si, après une mise à jour de l'application,
l'extension ne réagit plus, cliquez sur <b>Actualiser</b> à côté d'elle dans <code>chrome://extensions</code>. Firefox et Edge mettent
l'extension à jour tout seuls.</div>
<h2>Utilisation</h2>
<ul>
<li>Lancez une vidéo et cliquez sur l'icône de Video Download : <b>Télécharger la vidéo en cours</b> ou <b>Télécharger en MP3</b>.</li>
<li>Clic droit sur un lien ou une vidéo : <b>Télécharger ce lien</b> ou <b>…en MP3</b>.</li>
<li>Si l'application n'est pas ouverte, le clic la démarre.</li>
<li>Les directs et les vidéos protégées par DRM ne sont pas téléchargés.</li>
</ul>""",
    },
}
LANGUAGES = tuple(TEXTS)

HEAD = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Video Download</title>
<meta name="description" content="{description}">
{meta}
<link rel="icon" href="{up}assets/icon.png">
<link rel="apple-touch-icon" href="{up}assets/icon.png">
<meta name="theme-color" content="#f7f9fc" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0b0e14" media="(prefers-color-scheme: dark)">
<link rel="stylesheet" href="{up}assets/{css}">
<script>document.documentElement.classList.add("js")</script>
{alternates}
</head>
<body id="top">

<header>
  <div class="wrap bar">
    <a class="brand" href="index.html">{brand_icon}Video Download</a>
    <nav>
{nav}
    </nav>
    {switcher}
    {menu}
  </div>
  <nav class="mobile-nav" id="mobile-nav" aria-label="{menu_label}" hidden>
{nav}
    <div class="menu-lang">{switcher}</div>
  </nav>
</header>

<main class="doc">
<a class="back" href="index.html">{home}</a>
"""


def page_url(lang: str, page: str = "index.html") -> str:
    """Javna adresa stranice; početna bez „index.html" (tako je i Google vodi)."""
    return PUBLIC_URL + TEXTS[lang]["dir"] + ("" if page == "index.html" else page)


def meta_tags(lang: str, page: str, title: str, description: str) -> str:
    """Kanonska adresa i pregled za dijeljenje (WhatsApp, Viber, Facebook…): naslov, opis i snimak programa."""
    esc = html.escape
    image = f"{PUBLIC_URL}assets/screenshot-light-{lang}.png"
    tags = [f'<link rel="canonical" href="{page_url(lang, page)}">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="Video Download">',
            f'<meta property="og:title" content="{esc(title)}">',
            f'<meta property="og:description" content="{esc(description)}">',
            f'<meta property="og:url" content="{page_url(lang, page)}">',
            f'<meta property="og:image" content="{image}">',
            '<meta property="og:image:width" content="860">',
            '<meta property="og:image:height" content="470">',
            f'<meta property="og:locale" content="{OG_LOCALES[lang]}">',
            '<meta name="twitter:card" content="summary_large_image">']
    return "\n".join(tags)


def software_jsonld(lang: str) -> str:
    """Strukturirani podaci za Google: besplatan program za Windows, Mac i Android."""
    import json

    home = site_home.HOME[lang]
    data = {
        "@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Video Download",
        "description": home["description"], "url": page_url(lang), "inLanguage": lang,
        "applicationCategory": "MultimediaApplication", "operatingSystem": "Windows 10, Windows 11, macOS 13, Android 10",
        "softwareVersion": __version__, "downloadUrl": INSTALLER_URL, "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        "image": f"{PUBLIC_URL}assets/icon.png", "screenshot": f"{PUBLIC_URL}assets/screenshot-light-{lang}.png",
        "availableLanguage": ["en", "bs", "de", "es", "fr"],
    }
    text = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{text}\n</script>'


SITEMAP_PAGES = ("index.html", "guides.html", site_android.PAGE, *(f"{slug}.html" for slug in site_guides.GUIDES), "changelog.html",
                 "extension.html", "terms.html", "privacy.html", "licenses.html",
                 *((site_impressum.PAGE,) if site_impressum.enabled() else ()))


def sitemap_xml() -> str:
    """Mapa sajta za Google/Bing: svaka stranica na svakom jeziku, uz veze među jezicima (hreflang)."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for page in SITEMAP_PAGES + ((site_release.PAGE,) if site_release.enabled() else ())             + ((site_winget.PAGE,) if site_winget.enabled() else ()):
        for lang in LANGUAGES:
            lines.append(f"  <url><loc>{page_url(lang, page)}</loc>")
            for other in LANGUAGES:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{other}" href="{page_url(other, page)}"/>')
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{page_url("en", page)}"/>')
            lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


TO_TOP = {"en": "Back to top", "bs": "Nazad na vrh", "de": "Nach oben", "es": "Volver arriba", "fr": "Haut de page"}
TO_TOP_ICON = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
               'stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>')


def footer_html(lang: str) -> str:
    terms, privacy, licenses = TEXTS[lang]["footer"]
    top = html.escape(TO_TOP[lang])
    # „Na vrh": #top (id na <body>) radi i bez JavaScripta; site.js ga pokazuje tek poslije skrola.
    return f"""<a class="to-top" href="#top" aria-label="{top}" title="{top}">{TO_TOP_ICON}</a>
<footer>
  <div class="wrap">
    <span>© 2026 Video Download</span>
    <div class="links">
      <a href="guides.html">{site_guides.HUB[lang][0]}</a><a href="changelog.html">{site_home.HOME[lang]["nav"][3]}</a>
      <a href="terms.html">{terms}</a><a href="privacy.html">{privacy}</a><a href="licenses.html">{licenses}</a>{site_impressum.footer_link(lang)}
      <a href="{REPO}">GitHub</a><a href="{site_home.DISCORD_URL}">Discord</a><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>
    </div>
  </div>
</footer>"""


_URL = re.compile(r"(https?://[^\s<>()\"]+[^\s<>()\".,;:])")
_NUMBERED = re.compile(r"^\d+\.\s+\S")


def _inline(text: str) -> str:
    return _URL.sub(r'<a href="\1">\1</a>', html.escape(text, quote=False))


def text_to_html(text: str) -> tuple[str, str]:
    """Tekst pravnog dokumenta → (naslov, HTML). Prvi red je naslov, „1. …" podnaslov, „- …" stavka liste."""
    lines = [line.rstrip() for line in text.lstrip("﻿").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    title = lines.pop(0).strip() if lines else ""
    parts, paragraph, items = [], [], []

    def flush():
        if paragraph:
            parts.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()
        if items:
            parts.append("<ul>" + "".join(f"<li>{_inline(item)}</li>" for item in items) + "</ul>")
            items.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            flush()
        elif _NUMBERED.match(line) and len(line) < 90 and not line.endswith("."):
            flush()
            parts.append(f"<h2>{_inline(line)}</h2>")
        elif line.startswith("- "):
            if paragraph:
                flush()
            items.append(line[2:])
        elif items and raw.startswith("  "):
            items[-1] += " " + line  # nastavak stavke u sljedećem redu
        else:
            if items:
                flush()
            paragraph.append(line)
    flush()
    return title, "\n".join(parts)


def _heading(title: str) -> str:
    """„VIDEO DOWNLOAD — USLOVI KORIŠTENJA" → „Video Download — uslovi korištenja"."""
    _name, sep, rest = title.partition(" — ")
    if not sep:
        return title.capitalize()
    return "Video Download — " + rest.lower()


def _asset_text(name: str, lang: str = "bs") -> str:
    return (ASSETS / f"{name}_{lang}.txt").read_text(encoding="utf-8-sig")


def _up(lang: str) -> str:
    """Put od stranice jezika do korijena sajta (assets/ je zajednički)."""
    return "../" * TEXTS[lang]["dir"].count("/")


def switcher(lang: str, page: str = "index.html") -> str:
    links = []
    for other in LANGUAGES:
        href = _up(lang) + TEXTS[other]["dir"] + page
        current = ' aria-current="true"' if other == lang else ""
        links.append(f'<a href="{href}"{current}>{other.upper()}</a>')
    return '<span class="lang">' + " · ".join(links) + "</span>"


def alternates(lang: str, page: str) -> str:
    # Google traži pune adrese; x-default = engleska (glavna) verzija.
    links = [f'<link rel="alternate" hreflang="{other}" href="{page_url(other, page)}">' for other in LANGUAGES]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{page_url("en", page)}">')
    return "\n".join(links)


def _page(lang: str, name: str, title: str, description: str, body: str) -> str:
    t = TEXTS[lang]
    nav = "\n".join(f'      <a{" class=\"heart\"" if anchor == "support" else ""} href="index.html#{anchor}">{label}</a>'
                    for anchor, label in zip(site_home.ANCHORS, site_home.HOME[lang]["nav"]))
    head = HEAD.format(brand_icon=site_home.BRAND_ICON, lang=lang, title=html.escape(title), description=html.escape(description), up=_up(lang),
                       nav=nav, home=t["home"], switcher=switcher(lang, name), alternates=alternates(lang, name),
                       meta=meta_tags(lang, name, f"{title} — Video Download", description),
                       css=site_home.asset("site.css"), menu=site_home.menu_button(lang), menu_label=html.escape(site_home.HOME[lang]["a11y"][3]))
    return (head + body + "\n</main>\n\n" + footer_html(lang) +
            f'\n\n<script src="{_up(lang)}assets/{site_home.asset("site.js")}" defer></script>\n</body>\n</html>\n')


def page_terms(lang: str) -> str:
    t = TEXTS[lang]
    terms_title, terms = text_to_html(_asset_text("terms", lang))
    eula_title, eula = text_to_html(_asset_text("eula", lang))
    body = (f"<h1>{t['terms_title']}</h1>\n<p class=\"lead\">{t['terms_lead']}</p>\n"
            f"<h2 style=\"font-size:24px\">{html.escape(_heading(terms_title))}</h2>\n{terms}\n"
            f"<h2 style=\"font-size:24px;margin-top:48px\">{html.escape(_heading(eula_title))}</h2>\n{eula}")
    return _page(lang, "terms.html", t["terms_title"], t["terms_desc"], body)


def page_privacy(lang: str) -> str:
    t = TEXTS[lang]
    _title, privacy = text_to_html(_asset_text("privacy", lang))
    items = "\n".join(f"<li>{item}</li>" for item in t["privacy_items"])
    body = f"""<h1>{t['privacy_title']}</h1>
<p class="lead">{t['privacy_lead']}</p>
<div class="box">
<h2 style="margin-top:0">{t['privacy_site']}</h2>
<ul>
{items}
</ul>
</div>
<h2 style="font-size:24px">{t['privacy_app']}</h2>
{privacy}"""
    return _page(lang, "privacy.html", t["privacy_title"], t["privacy_desc"], body)


def page_licenses(lang: str) -> str:
    t = TEXTS[lang]
    rows = []
    for component in legal.site_components():
        note = f"<br><small>{_inline(component.note)}</small>" if component.note else ""
        rows.append(f"<tr><td><a href=\"{html.escape(component.url)}\">{html.escape(component.name)}</a>{note}</td>"
                    f"<td>{html.escape(component.license)}</td></tr>")
    android = [f"<tr><td><a href=\"{html.escape(c.url)}\">{html.escape(c.name)}</a></td><td>{html.escape(c.license)}</td></tr>"
               for c in legal.ANDROID_COMPONENTS]
    body = f"""<h1>{t['licenses_title']}</h1>
<p class="lead">{t['licenses_lead']}</p>
<table>
<tr><th>{t['licenses_cols'][0]}</th><th>{t['licenses_cols'][1]}</th></tr>
{chr(10).join(rows)}
</table>
<div class="box">{t['licenses_note']}</div>
<h2>{html.escape(t['licenses_android'][0])}</h2>
<table>
<tr><th>{t['licenses_cols'][0]}</th><th>{t['licenses_cols'][1]}</th></tr>
{chr(10).join(android)}
</table>
<p>{html.escape(t['licenses_android'][1])}</p>"""
    return _page(lang, "licenses.html", t["licenses_title"], t["licenses_desc"], body)


MOCK_LABELS = {
    "en": ("Extensions", "Developer mode", "Load unpacked", "Pack extension", "Select folder", "Select Folder",
           "Help → Downloading from the browser", "Copy the folder path", "Open extensions in Chrome",
           ""),
    "bs": ("Dodaci", "Developer mode", "Load unpacked", "Pack extension", "Izaberi folder", "Izaberi folder",
           "Pomoć → Preuzimanje iz browsera", "Kopiraj putanju foldera", "Otvori dodatke u Chrome-u",
           ""),
    "de": ("Erweiterungen", "Entwicklermodus", "Entpackte Erweiterung laden", "Erweiterung packen", "Ordner auswählen",
           "Ordner auswählen", "Hilfe → Aus dem Browser herunterladen", "Ordnerpfad kopieren",
           "Erweiterungen in Chrome öffnen", ""),
    "es": ("Extensiones", "Modo de desarrollador", "Cargar descomprimida", "Empaquetar extensión", "Seleccionar carpeta",
           "Seleccionar carpeta", "Ayuda → Descargar desde el navegador", "Copiar la ruta de la carpeta",
           "Abrir extensiones en Chrome", ""),
    "fr": ("Extensions", "Mode développeur", "Charger l'extension non empaquetée", "Empaqueter l'extension",
           "Sélectionner un dossier", "Sélectionner un dossier", "Aide → Télécharger depuis le navigateur",
           "Copier le chemin du dossier", "Ouvrir les extensions dans Chrome", ""),
}
MOCK_FOLDER = r"...\Programs\Video Download\extension"


def extension_mock(lang: str) -> str:
    """Tri male slike koraka (u HTML-u, pa rade u svijetloj i tamnoj temi i na svim jezicima)."""
    extensions, dev_mode, load, pack, select, select_button, help_menu, copy_path, open_chrome, _ = \
        (html.escape(label) for label in MOCK_LABELS[lang])
    return f"""<div class="mock-row" aria-hidden="true">
  <div class="mock"><div class="mock-bar">Video Download — {help_menu}</div>
    <div class="mock-body"><span class="mock-btn ss-hl">{copy_path}</span>
      <span class="mock-btn">{open_chrome}</span></div></div>
  <div class="ss-arrow">→</div>
  <div class="mock"><div class="mock-bar">chrome://extensions</div>
    <div class="mock-body"><b>{extensions}</b>
      <span class="mock-toggle ss-hl">{dev_mode} <i></i></span></div>
    <div class="mock-body"><span class="mock-btn ss-hl">{load}</span>
      <span class="mock-btn">{pack}</span></div></div>
  <div class="ss-arrow">→</div>
  <div class="mock"><div class="mock-bar">{select}</div>
    <div class="mock-body"><span class="mock-field ss-hl">{html.escape(MOCK_FOLDER)}</span></div>
    <div class="mock-body" style="justify-content:flex-end"><span class="mock-btn">{select_button}</span></div></div>
</div>"""


# Stari nelistan dodatak ostaje na sajtu samo zbog postojećih instalacija (site/firefox/updates.json vodi na njega).
FIREFOX_XPI = "firefox/video-download-0.5.2.xpi"
# Od 16.10.2026 dodatak je javno na Firefox Add-ons (AMO): dugme vodi tamo, Mozilla isporučuje ažuriranja.
FIREFOX_AMO = "https://addons.mozilla.org/firefox/addon/video-download-abnps/"
FIREFOX_TEXT = {
    "en": ("Firefox", "Install in Firefox — no developer mode needed. The extension is signed by Mozilla and "
           "updates itself.", "Add to Firefox",
           ("Install the app first (the extension talks to it).",
            "In Firefox 140 or newer click <b>Add to Firefox</b> below: the official Firefox Add-ons page opens.",
            "There click <b>Add to Firefox</b>, then <b>Add</b>.",
            "Pin the Video Download icon (puzzle icon → pin).")),
    "bs": ("Firefox", "Instalacija u Firefoxu — bez developer moda. Dodatak je potpisala Mozilla i sam se ažurira.",
           "Dodaj u Firefox",
           ("Prvo instaliraj program (dodatak radi s njim).",
            "U Firefoxu 140 ili novijem klikni <b>Dodaj u Firefox</b> ispod: otvara se zvanična stranica Firefox Add-ons.",
            "Tamo klikni <b>Add to Firefox</b> (Dodaj u Firefox), pa <b>Add</b> (Dodaj).",
            "Prikvači ikonu Video Download (ikona slagalice → pribadača).")),
    "de": ("Firefox", "Installation in Firefox – ohne Entwicklermodus. Die Erweiterung ist von Mozilla signiert und "
           "aktualisiert sich selbst.", "Zu Firefox hinzufügen",
           ("Installiere zuerst die App (die Erweiterung arbeitet mit ihr).",
            "Klicke in Firefox 140 oder neuer unten auf <b>Zu Firefox hinzufügen</b>: die offizielle Seite von Firefox Add-ons öffnet sich.",
            "Klicke dort auf <b>Zu Firefox hinzufügen</b> und dann auf <b>Hinzufügen</b>.",
            "Hefte das Symbol von Video Download an (Puzzle-Symbol → Anheften).")),
    "es": ("Firefox", "Instalación en Firefox, sin modo de desarrollador. La extensión está firmada por Mozilla y se "
           "actualiza sola.", "Añadir a Firefox",
           ("Instala primero la aplicación (la extensión trabaja con ella).",
            "En Firefox 140 o posterior pulsa <b>Añadir a Firefox</b> abajo: se abre la página oficial de Firefox Add-ons.",
            "Allí pulsa <b>Añadir a Firefox</b> y luego <b>Añadir</b>.",
            "Fija el icono de Video Download (icono de pieza de puzle → fijar).")),
    "fr": ("Firefox", "Installation dans Firefox, sans mode développeur. L'extension est signée par Mozilla et se met à "
           "jour toute seule.", "Ajouter à Firefox",
           ("Installez d'abord l'application (l'extension fonctionne avec elle).",
            "Dans Firefox 140 ou plus récent, cliquez sur <b>Ajouter à Firefox</b> ci-dessous : la page officielle de Firefox Add-ons s'ouvre.",
            "Cliquez-y sur <b>Ajouter à Firefox</b>, puis sur <b>Ajouter</b>.",
            "Épinglez l'icône de Video Download (icône de pièce de puzzle → épingler).")),
}


def firefox_section(lang: str) -> str:
    title, lead, button, steps = FIREFOX_TEXT[lang]
    items = "\n".join(f"<li>{step}</li>" for step in steps)
    return f"""<div class="box">
<h2 style="margin-top:0">{title}</h2>
<p>{html.escape(lead)}</p>
<p><a class="btn" href="{FIREFOX_AMO}" rel="noopener">{html.escape(button)}</a></p>
<ol>
{items}
</ol>
</div>"""


# Od 27.10.2026 dodatak je javno i u Microsoft Edge Add-ons: jedan klik, Microsoft isporučuje ažuriranja.
EDGE_ADDON = "https://microsoftedge.microsoft.com/addons/detail/glikmhiifcloegaachgkhinigmnhnjpo"
EDGE_TEXT = {
    "en": ("Microsoft Edge", "Install in Edge from the official Edge Add-ons store — no developer mode needed. "
           "The extension updates itself.", "Get it for Edge",
           ("Install the app first (the extension talks to it).",
            "Click <b>Get it for Edge</b> below: the official Edge Add-ons page opens.",
            "On the Edge Add-ons page click <b>Get</b>, then <b>Add extension</b>.",
            "Pin the Video Download icon (puzzle icon → eye icon).")),
    "bs": ("Microsoft Edge", "Instalacija u Edge iz zvanične prodavnice Edge Add-ons — bez developer moda. "
           "Dodatak se sam ažurira.", "Preuzmi za Edge",
           ("Prvo instaliraj program (dodatak radi s njim).",
            "Klikni <b>Preuzmi za Edge</b> ispod: otvara se zvanična stranica Edge Add-ons.",
            "Na stranici Edge Add-ons klikni <b>Get</b> (Nabavi), pa <b>Add extension</b> (Dodaj proširenje).",
            "Prikvači ikonu Video Download (ikona slagalice → ikona oka).")),
    "de": ("Microsoft Edge", "Installation in Edge aus dem offiziellen Store Edge-Add-ons – ohne Entwicklermodus. "
           "Die Erweiterung aktualisiert sich selbst.", "Für Edge herunterladen",
           ("Installiere zuerst die App (die Erweiterung arbeitet mit ihr).",
            "Klicke unten auf <b>Für Edge herunterladen</b>: die offizielle Seite von Edge-Add-ons öffnet sich.",
            "Klicke auf der Seite von Edge-Add-ons auf <b>Abrufen</b> und dann auf <b>Erweiterung hinzufügen</b>.",
            "Hefte das Symbol von Video Download an (Puzzle-Symbol → Augen-Symbol).")),
    "es": ("Microsoft Edge", "Instalación en Edge desde la tienda oficial Complementos de Edge, sin modo de desarrollador. "
           "La extensión se actualiza sola.", "Obtener para Edge",
           ("Instala primero la aplicación (la extensión trabaja con ella).",
            "Pulsa <b>Obtener para Edge</b> abajo: se abre la página oficial de Complementos de Edge.",
            "En la página de Complementos de Edge pulsa <b>Obtener</b> y luego <b>Agregar extensión</b>.",
            "Fija el icono de Video Download (icono de puzle → icono de ojo).")),
    "fr": ("Microsoft Edge", "Installation dans Edge depuis la boutique officielle Modules complémentaires Edge, sans mode "
           "développeur. L'extension se met à jour toute seule.", "Obtenir pour Edge",
           ("Installez d'abord l'application (l'extension fonctionne avec elle).",
            "Cliquez sur <b>Obtenir pour Edge</b> ci-dessous : la page officielle des modules Edge s'ouvre.",
            "Sur la page des modules Edge, cliquez sur <b>Obtenir</b>, puis sur <b>Ajouter l'extension</b>.",
            "Épinglez l'icône de Video Download (icône puzzle → icône œil).")),
}


def edge_section(lang: str) -> str:
    title, lead, button, steps = EDGE_TEXT[lang]
    items = "\n".join(f"<li>{step}</li>" for step in steps)
    return f"""<div class="box">
<h2 style="margin-top:0">{title}</h2>
<p>{html.escape(lead)}</p>
<p><a class="btn" href="{EDGE_ADDON}" rel="noopener">{html.escape(button)}</a></p>
<ol>
{items}
</ol>
</div>"""


# Mac (beta): folder dodatka je unutar programa, pa se putanja kopira iz programa i lijepi s ⌘⇧G.
MAC_EXTENSION_NOTE = {
    "en": "<b>Mac (beta):</b> the folder is inside the app. In the app use Help → Downloading from the browser → "
          "<b>Copy the folder path</b>, then in the folder picker press <b>⌘⇧G</b>, paste (⌘V) and press Return.",
    "bs": "<b>Mac (beta):</b> folder je unutar programa. U programu Pomoć → Preuzimanje iz browsera → "
          "<b>Kopiraj putanju foldera</b>, pa u prozoru za izbor foldera pritisni <b>⌘⇧G</b>, zalijepi (⌘V) i Enter.",
    "de": "<b>Mac (Beta):</b> Der Ordner liegt im Programm. In der App Hilfe → Aus dem Browser herunterladen → "
          "<b>Ordnerpfad kopieren</b>, dann im Ordnerdialog <b>⌘⇧G</b> drücken, einfügen (⌘V) und Return drücken.",
    "es": "<b>Mac (beta):</b> la carpeta está dentro de la aplicación. En la aplicación, Ayuda → Descargar desde el "
          "navegador → <b>Copiar la ruta de la carpeta</b>; luego, en el selector de carpetas, pulsa <b>⌘⇧G</b>, pega (⌘V) "
          "y pulsa Intro.",
    "fr": "<b>Mac (bêta) :</b> le dossier se trouve dans l'application. Dans l'application, Aide → Télécharger depuis le "
          "navigateur → <b>Copier le chemin du dossier</b>, puis dans le sélecteur de dossier appuyez sur <b>⌘⇧G</b>, "
          "collez (⌘V) et appuyez sur Entrée.",
}


def page_extension(lang: str) -> str:
    t = TEXTS[lang]
    # Slike koraka idu ispod uvoda u Chrome dio (jedini ručni način).
    intro, rest = t["ext_body"].split("</p>", 1)
    body = (f"<h1>{t['ext_title']}</h1>\n{firefox_section(lang)}\n{edge_section(lang)}\n{intro}</p>\n"
            f"{extension_mock(lang)}{rest}"
            f'\n<div class="box">{MAC_EXTENSION_NOTE[lang]}</div>')
    return _page(lang, "extension.html", t["ext_title"], t["ext_desc"], body)


# (naslov, uvod s linkom {issue}, dugme, napomena, koraci) — nazivi iz macOS-a na tom jeziku.
MAC_TEXT = {
    "en": ("Beta", "<b>New: Video Download for Mac.</b> For Macs with an Apple chip (M1 or newer) and macOS 13 or later. "
           "It works, but only a few people have tried it so far: please <a href=\"{issue}\">report anything that doesn't work</a>.",
           "Download for Mac (beta)",
           "The Mac version isn't signed by Apple yet, so the first start takes a few extra clicks:",
           ("Open the downloaded .dmg and drag Video Download to Applications.",
            "Open the app. macOS says it can't verify it: click <b>Done</b> (not “Move to Trash”).",
            "Open <b>System Settings → Privacy &amp; Security</b>, scroll down, click <b>Open Anyway</b> and enter your Mac password.",
            "Open the app again and confirm <b>Open</b>. This is needed only once.")),
    "bs": ("Beta", "<b>Novo: Video Download za Mac.</b> Za Mac sa Apple čipom (M1 ili noviji) i macOS 13 ili noviji. "
           "Radi, ali ga je probalo još malo ljudi: <a href=\"{issue}\">javi ako nešto ne radi</a>.",
           "Preuzmi za Mac (beta)",
           "Mac verzija još nema Appleov potpis, pa prvo pokretanje traži par klikova više:",
           ("Otvori preuzeti .dmg i prevuci Video Download u Applications.",
            "Otvori program. macOS kaže da ga ne može provjeriti: klikni <b>Done</b> (ne „Move to Trash“).",
            "Otvori <b>System Settings → Privacy &amp; Security</b> (Postavke sistema → Privatnost i sigurnost), skroluj dolje, "
            "klikni <b>Open Anyway</b> (Ipak otvori) i upiši lozinku Maca.",
            "Ponovo otvori program i potvrdi <b>Open</b>. To treba samo jednom.")),
    "de": ("Beta", "<b>Neu: Video Download für Mac.</b> Für Macs mit Apple-Chip (M1 oder neuer) und macOS 13 oder neuer. "
           "Es funktioniert, aber bisher haben es erst wenige ausprobiert: <a href=\"{issue}\">melde bitte, was nicht klappt</a>.",
           "Für Mac herunterladen (Beta)",
           "Die Mac-Version ist noch nicht von Apple signiert, daher braucht der erste Start ein paar Klicks mehr:",
           ("Öffne die geladene .dmg und ziehe Video Download in den Ordner „Programme“.",
            "Öffne das Programm. macOS meldet, dass es nicht überprüft werden kann: Schließe die Meldung "
            "(nicht „In den Papierkorb legen“).",
            "Öffne <b>Systemeinstellungen → Datenschutz &amp; Sicherheit</b>, scrolle nach unten, klicke auf "
            "<b>Dennoch öffnen</b> und gib dein Mac-Passwort ein.",
            "Öffne das Programm erneut und bestätige mit <b>Öffnen</b>. Das ist nur einmal nötig.")),
    "es": ("Beta", "<b>Novedad: Video Download para Mac.</b> Para Mac con chip de Apple (M1 o posterior) y macOS 13 o posterior. "
           "Funciona, pero aún lo han probado pocas personas: <a href=\"{issue}\">avísanos si algo no funciona</a>.",
           "Descargar para Mac (beta)",
           "La versión para Mac aún no está firmada por Apple, así que el primer inicio requiere unos clics más:",
           ("Abre el .dmg descargado y arrastra Video Download a Aplicaciones.",
            "Abre la app. macOS dice que no puede verificarla: cierra el aviso (no «Trasladar a la papelera»).",
            "Ve a <b>Ajustes del Sistema → Privacidad y seguridad</b>, desplázate hacia abajo, pulsa <b>Abrir igualmente</b> "
            "e introduce la contraseña del Mac.",
            "Vuelve a abrir la app y confirma <b>Abrir</b>. Solo hace falta una vez.")),
    "fr": ("Bêta", "<b>Nouveau : Video Download pour Mac.</b> Pour les Mac avec puce Apple (M1 ou plus récent) et macOS 13 "
           "ou plus récent. Il fonctionne, mais peu de personnes l'ont encore essayé : "
           "<a href=\"{issue}\">signalez ce qui ne marche pas</a>.",
           "Télécharger pour Mac (bêta)",
           "La version Mac n'est pas encore signée par Apple, le premier lancement demande donc quelques clics de plus :",
           ("Ouvrez le .dmg téléchargé et glissez Video Download dans Applications.",
            "Ouvrez l'app. macOS indique qu'il ne peut pas la vérifier : fermez le message (pas « Placer dans la corbeille »).",
            "Allez dans <b>Réglages Système → Confidentialité et sécurité</b>, faites défiler vers le bas, cliquez sur "
            "<b>Ouvrir quand même</b> et saisissez le mot de passe du Mac.",
            "Rouvrez l'app et confirmez <b>Ouvrir</b>. Cela n'est nécessaire qu'une fois.")),
}


# Linux (beta): (uvod s linkom {issue}, dugme, napomena, koraci). Oznaka „Beta" je ista kao za Mac (MAC_TEXT[0]).
LINUX_TEXT = {
    "en": ("<b>New: Video Download for Linux.</b> For 64-bit PCs (x86_64) with Ubuntu 22.04 or newer, Linux Mint 21+, "
           "Debian 12+, Fedora 38+ or similar. It works, but only a few people have tried it so far: please "
           "<a href=\"{issue}\">report anything that doesn't work</a>.",
           "Download for Linux (beta)",
           "One file, nothing to install:",
           ("Download the .AppImage file and keep it in a folder of your choice (for example your home folder).",
            "Allow it to run: right-click → <b>Properties</b> → <b>Allow executing file as program</b>, or in a terminal "
            "<code>chmod +x VideoDownload-linux-x86_64.AppImage</code>.",
            "Double-click it to start. Updates replace the same file, so you never need to download it again.",
            "If it doesn't start, install FUSE (Ubuntu/Debian: <code>sudo apt install fuse3</code>) or start it with "
            "<code>--appimage-extract-and-run</code>.",
            "The browser extension works with Chrome, Edge and Firefox from your distribution or the browser's website; "
            "browsers installed as Flatpak can't connect to the app yet.")),
    "bs": ("<b>Novo: Video Download za Linux.</b> Za 64-bitne računare (x86_64) s Ubuntu 22.04 ili novijim, Linux Mint 21+, "
           "Debian 12+, Fedora 38+ ili sličnim. Radi, ali ga je probalo još malo ljudi: "
           "<a href=\"{issue}\">javi ako nešto ne radi</a>.",
           "Preuzmi za Linux (beta)",
           "Jedan fajl, ništa se ne instalira:",
           ("Preuzmi .AppImage fajl i drži ga u folderu po želji (npr. u ličnom folderu).",
            "Dozvoli pokretanje: desni klik → <b>Properties</b> (Svojstva) → <b>Allow executing file as program</b> "
            "(Dozvoli pokretanje kao program), ili u terminalu <code>chmod +x VideoDownload-linux-x86_64.AppImage</code>.",
            "Pokreni ga dvoklikom. Ažuriranja mijenjaju isti fajl, pa ga ne treba ponovo preuzimati.",
            "Ako se ne pokreće, instaliraj FUSE (Ubuntu/Debian: <code>sudo apt install fuse3</code>) ili ga pokreni s "
            "<code>--appimage-extract-and-run</code>.",
            "Dodatak za browser radi s Chromeom, Edgeom i Firefoxom iz tvoje distribucije ili sa sajta browsera; "
            "browseri instalirani kao Flatpak se zasad ne mogu povezati s programom.")),
    "de": ("<b>Neu: Video Download für Linux.</b> Für 64-Bit-PCs (x86_64) mit Ubuntu 22.04 oder neuer, Linux Mint 21+, "
           "Debian 12+, Fedora 38+ oder ähnlich. Es funktioniert, aber bisher haben es erst wenige ausprobiert: "
           "<a href=\"{issue}\">melde bitte, was nicht klappt</a>.",
           "Für Linux herunterladen (Beta)",
           "Eine Datei, keine Installation:",
           ("Lade die .AppImage-Datei herunter und lege sie in einen Ordner deiner Wahl (z. B. deinen Persönlichen Ordner).",
            "Ausführen erlauben: Rechtsklick → <b>Eigenschaften</b> → <b>Datei als Programm ausführen</b>, oder im Terminal "
            "<code>chmod +x VideoDownload-linux-x86_64.AppImage</code>.",
            "Mit Doppelklick starten. Updates ersetzen dieselbe Datei, du musst sie also nie neu herunterladen.",
            "Startet sie nicht, installiere FUSE (Ubuntu/Debian: <code>sudo apt install fuse3</code>) oder starte sie mit "
            "<code>--appimage-extract-and-run</code>.",
            "Die Browser-Erweiterung funktioniert mit Chrome, Edge und Firefox aus deiner Distribution oder von der Website "
            "des Browsers; als Flatpak installierte Browser können sich noch nicht mit der App verbinden.")),
    "es": ("<b>Novedad: Video Download para Linux.</b> Para PC de 64 bits (x86_64) con Ubuntu 22.04 o posterior, Linux Mint 21+, "
           "Debian 12+, Fedora 38+ o similar. Funciona, pero aún lo han probado pocas personas: "
           "<a href=\"{issue}\">avísanos si algo no funciona</a>.",
           "Descargar para Linux (beta)",
           "Un solo archivo, sin instalación:",
           ("Descarga el archivo .AppImage y guárdalo en la carpeta que quieras (por ejemplo, tu carpeta personal).",
            "Permite ejecutarlo: clic derecho → <b>Propiedades</b> → <b>Permitir ejecutar el archivo como programa</b>, "
            "o en una terminal <code>chmod +x VideoDownload-linux-x86_64.AppImage</code>.",
            "Haz doble clic para iniciarlo. Las actualizaciones reemplazan el mismo archivo, así que no hace falta volver a "
            "descargarlo.",
            "Si no se inicia, instala FUSE (Ubuntu/Debian: <code>sudo apt install fuse3</code>) o inícialo con "
            "<code>--appimage-extract-and-run</code>.",
            "La extensión del navegador funciona con Chrome, Edge y Firefox de tu distribución o del sitio del navegador; "
            "los navegadores instalados como Flatpak aún no pueden conectarse con la app.")),
    "fr": ("<b>Nouveau : Video Download pour Linux.</b> Pour les PC 64 bits (x86_64) avec Ubuntu 22.04 ou plus récent, "
           "Linux Mint 21+, Debian 12+, Fedora 38+ ou similaire. Il fonctionne, mais peu de personnes l'ont encore essayé : "
           "<a href=\"{issue}\">signalez ce qui ne marche pas</a>.",
           "Télécharger pour Linux (bêta)",
           "Un seul fichier, rien à installer :",
           ("Téléchargez le fichier .AppImage et gardez-le dans le dossier de votre choix (par exemple votre dossier personnel).",
            "Autorisez son exécution : clic droit → <b>Propriétés</b> → <b>Autoriser l'exécution du fichier comme un "
            "programme</b>, ou dans un terminal <code>chmod +x VideoDownload-linux-x86_64.AppImage</code>.",
            "Double-cliquez pour le lancer. Les mises à jour remplacent le même fichier : inutile de le télécharger à nouveau.",
            "S'il ne démarre pas, installez FUSE (Ubuntu/Debian : <code>sudo apt install fuse3</code>) ou lancez-le avec "
            "<code>--appimage-extract-and-run</code>.",
            "L'extension du navigateur fonctionne avec Chrome, Edge et Firefox de votre distribution ou du site du navigateur ; "
            "les navigateurs installés en Flatpak ne peuvent pas encore se connecter à l'app.")),
}


# Stranica sa svim verzijama (vlastita adresa, pa je Google može naći): (uvod, opis, link s početne, izdanja).
CHANGELOG_TEXT = {
    "en": ("Every version of the app, newest first.", "All changes to Video Download: new features and fixes by version.",
           "All versions →", "Releases and installers on GitHub"),
    "bs": ("Sve verzije programa, od najnovije.", "Sve izmjene u programu Video Download: nove funkcije i popravke po verzijama.",
           "Sve verzije →", "Izdanja i instaleri na GitHubu"),
    "de": ("Alle Versionen, die neueste zuerst.", "Alle Änderungen an Video Download: neue Funktionen und Korrekturen nach Version.",
           "Alle Versionen →", "Veröffentlichungen und Installer auf GitHub"),
    "es": ("Todas las versiones, de la más reciente a la más antigua.",
           "Todos los cambios de Video Download: funciones nuevas y correcciones por versión.",
           "Todas las versiones →", "Versiones e instaladores en GitHub"),
    "fr": ("Toutes les versions, de la plus récente à la plus ancienne.",
           "Toutes les modifications de Video Download : nouvelles fonctions et corrections par version.",
           "Toutes les versions →", "Versions et installateurs sur GitHub"),
}


def page_changelog(lang: str) -> str:
    intro, description, _more, releases = CHANGELOG_TEXT[lang]
    title = site_home.HOME[lang]["nav"][3]
    parts = [f"<h1>{html.escape(title)}</h1>",
             f'<p class="lead">{html.escape(intro)} {site_home.HOME[lang]["news"][2]}</p>']
    if site_release.enabled():
        parts.append(site_release.banner(lang))  # do 1.0 se ništa ne dodaje, ni prazan red
    for version, date, items in changelog.entries(lang):
        anchor = "v" + version.replace(".", "-")
        points = "\n".join(f"<li>{html.escape(item)}</li>" for item in items)
        parts.append(f'<h2 id="{anchor}">{html.escape(version)} <small>{html.escape(date)}</small></h2>\n<ul>\n{points}\n</ul>')
    parts.append(f'<p><a href="{REPO}/releases">{html.escape(releases)}</a></p>')
    return _page(lang, "changelog.html", title, description, "\n".join(parts))


NOT_FOUND = {
    "en": ("Page not found", "This page doesn't exist or has moved.", "Home"),
    "bs": ("Stranica nije pronađena", "Ova stranica ne postoji ili je premještena.", "Početna"),
    "de": ("Seite nicht gefunden", "Diese Seite gibt es nicht oder sie wurde verschoben.", "Startseite"),
    "es": ("Página no encontrada", "Esta página no existe o se ha movido.", "Inicio"),
    "fr": ("Page introuvable", "Cette page n'existe pas ou a été déplacée.", "Accueil"),
}


def page_not_found() -> str:
    base = "/video-download/"
    blocks = "\n".join(
        f'<div lang="{lang}" class="box"><h2 style="margin-top:0">{html.escape(title)}</h2><p>{html.escape(text)}</p>'
        f'<p><a class="btn" href="{base}{TEXTS[lang]["dir"]}">{html.escape(home)}</a> '
        f'<a class="btn ghost" href="{base}{TEXTS[lang]["dir"]}guides.html">{html.escape(site_guides.HUB[lang][0])}</a></p></div>'
        for lang, (title, text, home) in NOT_FOUND.items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>404 — Video Download</title>
<meta name="robots" content="noindex">
<link rel="icon" href="{base}assets/icon.png">
<link rel="stylesheet" href="{base}assets/{site_home.asset("site.css")}">
</head>
<body>
<main class="doc">
<p><a class="brand" href="{base}">{site_home.BRAND_ICON} Video Download</a></p>
<h1>404</h1>
{blocks}
</main>
</body>
</html>
"""


def news_html(lang: str) -> str:
    cards = []
    for version, date, items in changelog.entries(lang)[:NEWS_COUNT]:
        points = "".join(f"\n          <li>{html.escape(item)}</li>" for item in items)
        delay = f' style="--d:{len(cards) * 0.05:.2f}s"' if cards else ""
        cards.append(f'        <div class="card" data-reveal{delay}><h3>{html.escape(version)} <span>{html.escape(date)}</span>'
                     f"</h3><ul>{points}</ul></div>")
    return "\n".join(cards)


def current_size_mb(index: str) -> int | None:
    match = re.search(r"<!-- version -->\w+ [\d.]+ · (\d+) MB<!-- /version -->", index)
    return int(match.group(1)) if match else None


def build(size_mb: int | None = None) -> dict[str, str]:
    """Sadržaj svih generisanih fajlova (putanja u site/ → tekst); ne piše ništa na disk."""
    pages = {}
    for lang in LANGUAGES:
        prefix = TEXTS[lang]["dir"]
        existing = SITE / prefix / "index.html"
        # Veličinu instalera zna samo build; između izdanja ostaje ona iz postojeće stranice.
        size = size_mb or (current_size_mb(existing.read_text(encoding="utf-8")) if existing.is_file() else None) or 0
        pages[f"{prefix}index.html"] = site_home.render(
            lang, up=_up(lang), switcher=switcher(lang), alternates=alternates(lang, "index.html"),
            footer=footer_html(lang), news=news_html(lang),
            version_line=f"<!-- version -->{TEXTS[lang]['version']} {__version__} · {size} MB<!-- /version -->",
            version_short=f"{TEXTS[lang]['version']} {__version__}",
            installer_url=INSTALLER_URL, mac_url=MAC_DMG_URL, issue_url=ISSUE_URL, mac_text=MAC_TEXT[lang],
            android_url=ANDROID_APK_URL, android_text=ANDROID_TEXT[lang],
            linux_url=LINUX_APPIMAGE_URL, linux_text=LINUX_TEXT[lang],
            obtainium=(OBTAINIUM_URL, *OBTAINIUM_TEXT[lang]),
            android_guide_label=site_android.TEXT[lang]["dev_guide_title"],
            meta=meta_tags(lang, "index.html", site_home.HOME[lang]["title"], site_home.HOME[lang]["description"])
            + "\n" + software_jsonld(lang), page_url=page_url(lang), news_more=CHANGELOG_TEXT[lang][2],
            guides_link=site_guides.HUB[lang][9])
        pages[f"{prefix}changelog.html"] = page_changelog(lang)
        pages[f"{prefix}guides.html"] = _page(lang, "guides.html", *site_guides.hub_body(
            lang, extra_card=site_winget.hub_card(lang) + site_android.hub_card(lang)))
        pages[f"{prefix}{site_android.PAGE}"] = _page(lang, site_android.PAGE, *site_android.guide_body(
            lang, ANDROID_APK_URL, ANDROID_TEXT[lang][1]))
        for slug in site_guides.GUIDES:
            pages[f"{prefix}{slug}.html"] = _page(lang, f"{slug}.html", *site_guides.guide_body(
                lang, slug, issue_url=ISSUE_URL, installer_url=INSTALLER_URL, win_button=site_home.HOME[lang]["win_btn"]))
        pages[f"{prefix}terms.html"] = page_terms(lang)
        pages[f"{prefix}privacy.html"] = page_privacy(lang)
        pages[f"{prefix}licenses.html"] = page_licenses(lang)
        pages[f"{prefix}extension.html"] = page_extension(lang)
        if site_winget.enabled():
            pages[f"{prefix}{site_winget.PAGE}"] = _page(lang, site_winget.PAGE, *site_winget.guide_body(
                lang, INSTALLER_URL, site_home.HOME[lang]["win_btn"], site_guides.HUB[lang]))
        if site_release.enabled():
            pages[f"{prefix}{site_release.PAGE}"] = _page(lang, site_release.PAGE, *site_release.body(
                lang, INSTALLER_URL, MAC_DMG_URL, ANDROID_APK_URL))
        if site_impressum.enabled():
            pages[f"{prefix}{site_impressum.PAGE}"] = _page(lang, site_impressum.PAGE,
                                                            *site_impressum.body(lang, CONTACT_EMAIL))
    pages["sitemap.xml"] = sitemap_xml()
    pages["404.html"] = page_not_found()
    return pages


def forbidden_words(pages: dict[str, str]) -> list[str]:
    found = []
    for name, text in pages.items():
        if name.rsplit("/", 1)[-1] not in PROMO_PAGES:
            continue
        visible = re.sub(r"<[^>]+>", " ", text)  # linkovi (npr. na GitHub) ne računaju, samo vidljiv tekst
        found += [f"{name}: {match.group(0)}" for match in FORBIDDEN.finditer(visible)]
    return found


def write_site(size_mb: int | None = None) -> list[str]:
    """Piše sve stranice; vraća zabranjene izraze (tada ne piše ništa). Zove ga i build_release.py."""
    pages = build(size_mb)
    problems = forbidden_words(pages)
    if not problems:
        for name, text in pages.items():
            (SITE / name).write_text(text, encoding="utf-8", newline="\n")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size-mb", type=int, help="veličina instalera u MB (inače ostaje postojeća)")
    args = parser.parse_args()
    problems = write_site(args.size_mb)
    if problems:
        print("Zabranjeni izrazi na sajtu:\n  " + "\n  ".join(problems))
        return 1
    print("sajt: gotov")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
