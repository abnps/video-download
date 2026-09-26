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

SITE = ROOT / "site"
ASSETS = ROOT / "videodl" / "assets"
NEWS_COUNT = 3
REPO = "https://github.com/abnps/video-download"
CONTACT_EMAIL = "abnpsdev@gmail.com"  # javni kontakt projekta (Ahmedova odluka 26.9.2026); lični e-mail nikad
INSTALLER_URL = f"{REPO}/releases/latest/download/VideoDownload-Setup.exe"
# Mac (beta): stalna kopija .dmg-a uz posljednje izdanje (kao VideoDownload-Setup.exe za Windows).
MAC_DMG_URL = f"{REPO}/releases/latest/download/VideoDownload-macOS-arm64.dmg"
ISSUE_URL = f"{REPO}/issues/new?template=problem.yml"
INSTALL_DIR = r"%LOCALAPPDATA%\Programs\Video Download\extension"
GITHUB_PRIVACY = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"

# Riječi koje reklamne stranice ne smiju sadržavati (plan sajta: bez tuđih znakova i „zaobiđi zaštitu").
# Pravni tekstovi se ne provjeravaju: moraju biti doslovno isti kao u programu i instaleru.
FORBIDDEN = re.compile(r"youtube|\byt\b(?!-dlp)|tiktok|netflix|spotify|zaobi[đd]|crack|piratsk|besplatna muzika"
                       r"|free music|bypass|umgeh|kostenlose musik|eludir|música gratis|contourn|musique gratuite",
                       re.IGNORECASE)
PROMO_PAGES = ("index.html", "extension.html")

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
            "Messages to <b>abnpsdev@gmail.com</b> (the project's contact address, a Gmail mailbox at Google) are used "
            "only to reply to you and are never passed on or used for anything else.",
        ),
        "licenses_title": "Licenses",
        "licenses_lead": "Video Download uses the following software by other authors. Their licenses apply to them; the "
                         "full license texts are in the <code>licenses</code> folder next to the installed app.",
        "licenses_desc": "Licenses of the components used by Video Download.",
        "licenses_cols": ("Component", "License"),
        "licenses_note": "FFmpeg is licensed under GPL-3.0: the source code of the exact build in the installer is at the "
                         "links above, and a copy of the source code is also available on request.",
        "ext_title": "Browser extension",
        "ext_desc": "How to install the Video Download extension for Edge and Chrome.",
        "ext_body": f"""<p class="lead">With the extension you download the video that is playing with one click, or with a right-click
on a link or video. Works in Firefox, Edge and Chrome.</p>
<h2>Installation (once)</h2>
<ol>
<li>Install the app (the extension comes with it).</li>
<li>In your browser open <code>edge://extensions</code> (Edge) or <code>chrome://extensions</code> (Chrome).</li>
<li>Turn on <b>Developer mode</b> and click <b>Load unpacked</b>.</li>
<li>Choose the folder <code>{html.escape(INSTALL_DIR)}</code>. Easiest: in the app open
Help → Downloading from the browser, click <b>Copy the folder path</b> and paste it (Ctrl+V) into the folder picker.
The same window has a button that opens the extensions page in Edge or Chrome.</li>
<li>Pin the Video Download icon to the browser toolbar (puzzle icon → pin).</li>
</ol>
<div class="box">For now the extension is loaded by hand, because extension stores don't accept programs like this.
The browser may therefore remind you about “Developer mode”; that is expected and the extension works normally.</div>
<h2>Using it</h2>
<ul>
<li>Play a video on the page and click the Video Download icon: <b>Download the playing video</b> or <b>Download as MP3</b>.</li>
<li>Right-click a link or video: <b>Download this link</b> or <b>…as MP3</b>.</li>
<li>If the app isn't running, the click starts it.</li>
<li>Live streams and DRM-protected video are not downloaded.</li>
</ul>
<h2>After updating the app</h2>
<p>If the extension stops responding, click <b>Reload</b> next to it in <code>edge://extensions</code>.</p>""",
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
            "Poruke na <b>abnpsdev@gmail.com</b> (kontakt adresa projekta, Gmail sanduče kod Google-a) koriste se samo za "
            "odgovor tebi i nikad se ne prosljeđuju niti koriste za bilo šta drugo.",
        ),
        "licenses_title": "Licence",
        "licenses_lead": "Video Download koristi sljedeći softver drugih autora. Njihove licence važe za njih; puni tekstovi "
                         "licenci su u folderu <code>licenses</code> pored instaliranog programa.",
        "licenses_desc": "Licence komponenti koje koristi Video Download.",
        "licenses_cols": ("Komponenta", "Licenca"),
        "licenses_note": "FFmpeg je pod licencom GPL-3.0: izvorni kod tačnog builda koji je u instaleru je na linkovima "
                         "iznad, a kopiju izvornog koda možeš dobiti i na zahtjev.",
        "ext_title": "Dodatak za browser",
        "ext_desc": "Kako instalirati dodatak Video Download za Edge i Chrome.",
        "ext_body": f"""<p class="lead">Sa dodatkom preuzimaš video koji se upravo pušta, jednim klikom ili desnim klikom na link ili video.
Radi u Firefoxu, Edge-u i Chrome-u.</p>
<h2>Instalacija (jednom)</h2>
<ol>
<li>Instaliraj program (dodatak dolazi s njim).</li>
<li>U browseru otvori <code>edge://extensions</code> (Edge) ili <code>chrome://extensions</code> (Chrome).</li>
<li>Uključi <b>Developer mode</b> (Način za programere) i klikni <b>Load unpacked</b> (Učitaj raspakovano).</li>
<li>Izaberi folder <code>{html.escape(INSTALL_DIR)}</code>. Najlakše: u programu otvori
Pomoć → Preuzimanje iz browsera, klikni <b>Kopiraj putanju foldera</b> i zalijepi je (Ctrl+V) u prozor za izbor foldera.
U istom prozoru je i dugme koje otvara stranicu dodataka u Edge-u ili Chrome-u.</li>
<li>Prikvači ikonu Video Download na traku browsera (ikona slagalice → pribadača).</li>
</ol>
<div class="box">Dodatak se za sada učitava ručno jer prodavnice dodataka ne primaju ovakve programe.
Browser zato ponekad podsjeti na „Developer mode"; to je očekivano i dodatak radi normalno.</div>
<h2>Korištenje</h2>
<ul>
<li>Pusti video na stranici i klikni ikonu Video Download: <b>Preuzmi video koji se pušta</b> ili <b>Preuzmi kao MP3</b>.</li>
<li>Desni klik na link ili video: <b>Preuzmi ovaj link</b> ili <b>…kao MP3</b>.</li>
<li>Ako program nije pokrenut, klik ga sam pokreće.</li>
<li>Prenos uživo i video zaštićen DRM-om se ne preuzimaju.</li>
</ul>
<h2>Poslije ažuriranja programa</h2>
<p>Ako dodatak prestane reagovati, u <code>edge://extensions</code> klikni <b>Reload</b> (Ponovo učitaj) kod dodatka.</p>""",
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
            "Nachrichten an <b>abnpsdev@gmail.com</b> (die Kontaktadresse des Projekts, ein Gmail-Postfach bei Google) "
            "werden nur genutzt, um dir zu antworten, und nie weitergegeben oder anders verwendet.",
        ),
        "licenses_title": "Lizenzen",
        "licenses_lead": "Video Download nutzt die folgende Software anderer Autoren. Für sie gelten ihre eigenen Lizenzen; die "
                         "vollständigen Lizenztexte liegen im Ordner <code>licenses</code> neben der installierten App.",
        "licenses_desc": "Lizenzen der Komponenten, die Video Download nutzt.",
        "licenses_cols": ("Komponente", "Lizenz"),
        "licenses_note": "FFmpeg steht unter GPL-3.0: Der Quellcode genau des Builds im Installer ist unter den Links oben, "
                         "und eine Kopie des Quellcodes gibt es auch auf Anfrage.",
        "ext_title": "Browser-Erweiterung",
        "ext_desc": "So installierst du die Erweiterung Video Download für Edge und Chrome.",
        "ext_body": f"""<p class="lead">Mit der Erweiterung lädst du das laufende Video mit einem Klick herunter oder per Rechtsklick
auf einen Link oder ein Video. Funktioniert in Firefox, Edge und Chrome.</p>
<h2>Installation (einmalig)</h2>
<ol>
<li>Installiere die App (die Erweiterung ist dabei).</li>
<li>Öffne im Browser <code>edge://extensions</code> (Edge) oder <code>chrome://extensions</code> (Chrome).</li>
<li>Schalte den <b>Entwicklermodus</b> (Developer mode) ein und klicke auf <b>Entpackte Erweiterung laden</b> (Load unpacked).</li>
<li>Wähle den Ordner <code>{html.escape(INSTALL_DIR)}</code>. Am einfachsten: in der App
Hilfe → Aus dem Browser herunterladen öffnen, auf <b>Ordnerpfad kopieren</b> klicken und den Pfad (Strg+V) im Ordnerdialog einfügen.
Im selben Fenster öffnet ein Knopf die Erweiterungsseite in Edge oder Chrome.</li>
<li>Hefte das Symbol von Video Download an die Symbolleiste (Puzzle-Symbol → Anheften).</li>
</ol>
<div class="box">Die Erweiterung wird vorerst von Hand geladen, weil Erweiterungs-Stores solche Programme nicht aufnehmen.
Der Browser erinnert deshalb manchmal an den „Entwicklermodus“; das ist normal, und die Erweiterung funktioniert trotzdem.</div>
<h2>Benutzung</h2>
<ul>
<li>Spiele ein Video auf der Seite ab und klicke auf das Symbol von Video Download: <b>Laufendes Video herunterladen</b> oder
<b>Als MP3 herunterladen</b>.</li>
<li>Rechtsklick auf einen Link oder ein Video: <b>Diesen Link mit Video Download laden</b> oder <b>…als MP3</b>.</li>
<li>Läuft die App nicht, startet der Klick sie.</li>
<li>Livestreams und DRM-geschützte Videos werden nicht heruntergeladen.</li>
</ul>
<h2>Nach einem Update der App</h2>
<p>Reagiert die Erweiterung nicht mehr, klicke in <code>edge://extensions</code> bei ihr auf <b>Neu laden</b> (Reload).</p>""",
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
            "Los mensajes a <b>abnpsdev@gmail.com</b> (la dirección de contacto del proyecto, un buzón de Gmail en Google) "
            "se usan solo para responderte y nunca se comparten ni se usan para nada más.",
        ),
        "licenses_title": "Licencias",
        "licenses_lead": "Video Download usa el siguiente software de otros autores. Se rige por sus propias licencias; los textos "
                         "completos están en la carpeta <code>licenses</code> junto a la aplicación instalada.",
        "licenses_desc": "Licencias de los componentes que usa Video Download.",
        "licenses_cols": ("Componente", "Licencia"),
        "licenses_note": "FFmpeg tiene licencia GPL-3.0: el código fuente de la compilación exacta del instalador está en los "
                         "enlaces de arriba, y también puedes pedir una copia del código fuente.",
        "ext_title": "Extensión para el navegador",
        "ext_desc": "Cómo instalar la extensión Video Download para Edge y Chrome.",
        "ext_body": f"""<p class="lead">Con la extensión descargas el vídeo en reproducción con un clic, o con clic derecho en un enlace
o un vídeo. Funciona en Firefox, Edge y Chrome.</p>
<h2>Instalación (una vez)</h2>
<ol>
<li>Instala la aplicación (la extensión viene con ella).</li>
<li>En el navegador abre <code>edge://extensions</code> (Edge) o <code>chrome://extensions</code> (Chrome).</li>
<li>Activa el <b>Modo de desarrollador</b> (Developer mode) y pulsa <b>Cargar descomprimida</b> (Load unpacked).</li>
<li>Elige la carpeta <code>{html.escape(INSTALL_DIR)}</code>. Lo más fácil: en la aplicación abre
Ayuda → Descargar desde el navegador, pulsa <b>Copiar la ruta de la carpeta</b> y pégala (Ctrl+V) en la ventana de selección de carpeta.
En la misma ventana hay un botón que abre la página de extensiones en Edge o Chrome.</li>
<li>Fija el icono de Video Download en la barra del navegador (icono de pieza de puzle → fijar).</li>
</ol>
<div class="box">Por ahora la extensión se carga a mano, porque las tiendas de extensiones no aceptan programas como este.
Por eso el navegador a veces recuerda el «Modo de desarrollador»; es lo esperado y la extensión funciona con normalidad.</div>
<h2>Uso</h2>
<ul>
<li>Reproduce un vídeo en la página y pulsa el icono de Video Download: <b>Descargar el vídeo en reproducción</b> o
<b>Descargar como MP3</b>.</li>
<li>Clic derecho en un enlace o vídeo: <b>Descargar este enlace con Video Download</b> o <b>…como MP3</b>.</li>
<li>Si la aplicación no está abierta, el clic la inicia.</li>
<li>Las emisiones en directo y el vídeo protegido con DRM no se descargan.</li>
</ul>
<h2>Después de actualizar la aplicación</h2>
<p>Si la extensión deja de responder, pulsa <b>Volver a cargar</b> (Reload) junto a ella en <code>edge://extensions</code>.</p>""",
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
            "Les messages envoyés à <b>abnpsdev@gmail.com</b> (l'adresse de contact du projet, une boîte Gmail chez "
            "Google) servent uniquement à vous répondre et ne sont jamais transmis ni utilisés à d'autres fins.",
        ),
        "licenses_title": "Licences",
        "licenses_lead": "Video Download utilise les logiciels suivants d'autres auteurs. Leurs propres licences s'appliquent ; "
                         "les textes complets se trouvent dans le dossier <code>licenses</code> à côté de l'application installée.",
        "licenses_desc": "Licences des composants utilisés par Video Download.",
        "licenses_cols": ("Composant", "Licence"),
        "licenses_note": "FFmpeg est sous licence GPL-3.0 : le code source de la version exacte incluse dans le programme "
                         "d'installation se trouve aux liens ci-dessus, et une copie du code source est aussi disponible sur demande.",
        "ext_title": "Extension pour le navigateur",
        "ext_desc": "Comment installer l'extension Video Download pour Edge et Chrome.",
        "ext_body": f"""<p class="lead">Avec l'extension, vous téléchargez la vidéo en cours d'un clic, ou d'un clic droit sur un lien
ou une vidéo. Fonctionne dans Firefox, Edge et Chrome.</p>
<h2>Installation (une seule fois)</h2>
<ol>
<li>Installez l'application (l'extension est fournie avec).</li>
<li>Dans le navigateur, ouvrez <code>edge://extensions</code> (Edge) ou <code>chrome://extensions</code> (Chrome).</li>
<li>Activez le <b>Mode développeur</b> (Developer mode) et cliquez sur <b>Charger l'extension non empaquetée</b> (Load unpacked).</li>
<li>Choisissez le dossier <code>{html.escape(INSTALL_DIR)}</code>. Le plus simple : dans l'application, ouvrez
Aide → Télécharger depuis le navigateur, cliquez sur <b>Copier le chemin du dossier</b> et collez-le (Ctrl+V) dans la fenêtre de choix
du dossier. La même fenêtre a un bouton qui ouvre la page des extensions dans Edge ou Chrome.</li>
<li>Épinglez l'icône de Video Download dans la barre du navigateur (icône de pièce de puzzle → épingler).</li>
</ol>
<div class="box">Pour l'instant, l'extension se charge à la main, car les boutiques d'extensions n'acceptent pas ce genre de
programme. Le navigateur peut donc rappeler le « Mode développeur » ; c'est normal et l'extension fonctionne quand même.</div>
<h2>Utilisation</h2>
<ul>
<li>Lancez une vidéo sur la page et cliquez sur l'icône de Video Download : <b>Télécharger la vidéo en cours</b> ou
<b>Télécharger en MP3</b>.</li>
<li>Clic droit sur un lien ou une vidéo : <b>Télécharger ce lien avec Video Download</b> ou <b>…en MP3</b>.</li>
<li>Si l'application n'est pas lancée, le clic la démarre.</li>
<li>Les directs et les vidéos protégées par DRM ne sont pas téléchargés.</li>
</ul>
<h2>Après une mise à jour de l'application</h2>
<p>Si l'extension ne répond plus, cliquez sur <b>Actualiser</b> (Reload) à côté d'elle dans <code>edge://extensions</code>.</p>""",
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
<link rel="icon" href="{up}assets/icon.png">
<link rel="stylesheet" href="{up}assets/style.css">
{alternates}
</head>
<body>

<header>
  <div class="wrap bar">
    <a class="brand" href="index.html"><img src="{up}assets/icon.png" alt="">Video Download</a>
    <nav>
{nav}
    </nav>
    {switcher}
  </div>
</header>

<main class="doc">
<a class="back" href="index.html">{home}</a>
"""

FOOT = """</main>

<footer>
  <div class="wrap">
    <span>© 2026 Video Download</span>
    <div class="links">
      <a href="terms.html">{terms}</a>
      <a href="privacy.html">{privacy}</a>
      <a href="licenses.html">{licenses}</a>
      <a href="https://github.com/abnps/video-download">GitHub</a>
      <a href="mailto:abnpsdev@gmail.com">abnpsdev@gmail.com</a>
    </div>
  </div>
</footer>

</body>
</html>
"""

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
    return "\n".join(f'<link rel="alternate" hreflang="{other}" href="{_up(lang)}{TEXTS[other]["dir"]}{page}">'
                     for other in LANGUAGES)


def _page(lang: str, name: str, title: str, description: str, body: str) -> str:
    t = TEXTS[lang]
    nav = "\n".join(f'      <a{" class=\"heart\"" if i == 4 else ""} href="index.html#{anchor}">{label}</a>'
                    for i, (label, anchor) in enumerate(zip(t["nav"], t["anchors"])))
    head = HEAD.format(lang=lang, title=html.escape(title), description=html.escape(description), up=_up(lang),
                       nav=nav, home=t["home"], switcher=switcher(lang, name), alternates=alternates(lang, name))
    foot = FOOT.format(terms=t["footer"][0], privacy=t["footer"][1], licenses=t["footer"][2])
    return head + body + "\n" + foot


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
    body = f"""<h1>{t['licenses_title']}</h1>
<p class="lead">{t['licenses_lead']}</p>
<table>
<tr><th>{t['licenses_cols'][0]}</th><th>{t['licenses_cols'][1]}</th></tr>
{chr(10).join(rows)}
</table>
<div class="box">{t['licenses_note']}</div>"""
    return _page(lang, "licenses.html", t["licenses_title"], t["licenses_desc"], body)


MOCK_LABELS = {
    "en": ("Extensions", "Developer mode", "Load unpacked", "Pack extension", "Select folder", "Select Folder",
           "Help → Downloading from the browser", "Copy the folder path", "Open extensions in Edge",
           ""),
    "bs": ("Dodaci", "Developer mode", "Load unpacked", "Pack extension", "Izaberi folder", "Izaberi folder",
           "Pomoć → Preuzimanje iz browsera", "Kopiraj putanju foldera", "Otvori dodatke u Edge-u",
           ""),
    "de": ("Erweiterungen", "Entwicklermodus", "Entpackte Erweiterung laden", "Erweiterung packen", "Ordner auswählen",
           "Ordner auswählen", "Hilfe → Aus dem Browser herunterladen", "Ordnerpfad kopieren",
           "Erweiterungen in Edge öffnen", ""),
    "es": ("Extensiones", "Modo de desarrollador", "Cargar descomprimida", "Empaquetar extensión", "Seleccionar carpeta",
           "Seleccionar carpeta", "Ayuda → Descargar desde el navegador", "Copiar la ruta de la carpeta",
           "Abrir extensiones en Edge", ""),
    "fr": ("Extensions", "Mode développeur", "Charger l'extension non empaquetée", "Empaqueter l'extension",
           "Sélectionner un dossier", "Sélectionner un dossier", "Aide → Télécharger depuis le navigateur",
           "Copier le chemin du dossier", "Ouvrir les extensions dans Edge", ""),
}
MOCK_FOLDER = r"...\Programs\Video Download\extension"


def extension_mock(lang: str) -> str:
    """Tri male slike koraka (u HTML-u, pa rade u svijetloj i tamnoj temi i na svim jezicima)."""
    extensions, dev_mode, load, pack, select, select_button, help_menu, copy_path, open_edge, _ = \
        (html.escape(label) for label in MOCK_LABELS[lang])
    return f"""<div class="mock-row" aria-hidden="true">
  <div class="mock"><div class="mock-bar">Video Download — {help_menu}</div>
    <div class="mock-body"><span class="mock-btn ss-hl">{copy_path}</span>
      <span class="mock-btn">{open_edge}</span></div></div>
  <div class="ss-arrow">→</div>
  <div class="mock"><div class="mock-bar">edge://extensions</div>
    <div class="mock-body"><b>{extensions}</b>
      <span class="mock-toggle ss-hl">{dev_mode} <i></i></span></div>
    <div class="mock-body"><span class="mock-btn ss-hl">{load}</span>
      <span class="mock-btn">{pack}</span></div></div>
  <div class="ss-arrow">→</div>
  <div class="mock"><div class="mock-bar">{select}</div>
    <div class="mock-body"><span class="mock-field ss-hl">{html.escape(MOCK_FOLDER)}</span></div>
    <div class="mock-body" style="justify-content:flex-end"><span class="mock-btn">{select_button}</span></div></div>
</div>"""


# Potpisan Firefox dodatak (Mozilla, nelistan) leži na sajtu; site/firefox/updates.json vodi na isti fajl.
FIREFOX_XPI = "firefox/video-download-0.5.2.xpi"
FIREFOX_TEXT = {
    "en": ("Firefox", "Install in Firefox — no developer mode needed. The extension is signed by Mozilla and "
           "updates itself.", "Add to Firefox",
           ("Install the app first (the extension talks to it).",
            "Open this page in Firefox 140 or newer and click <b>Add to Firefox</b>.",
            "Firefox asks to allow the installation from this site: click <b>Continue to installation</b>, then <b>Add</b>.",
            "Pin the Video Download icon (puzzle icon → pin).")),
    "bs": ("Firefox", "Instalacija u Firefoxu — bez developer moda. Dodatak je potpisala Mozilla i sam se ažurira.",
           "Dodaj u Firefox",
           ("Prvo instaliraj program (dodatak radi s njim).",
            "Otvori ovu stranicu u Firefoxu 140 ili novijem i klikni <b>Dodaj u Firefox</b>.",
            "Firefox pita da dozvoliš instalaciju s ovog sajta: klikni <b>Continue to installation</b>, pa <b>Add</b>.",
            "Prikvači ikonu Video Download (ikona slagalice → pribadača).")),
    "de": ("Firefox", "Installation in Firefox – ohne Entwicklermodus. Die Erweiterung ist von Mozilla signiert und "
           "aktualisiert sich selbst.", "Zu Firefox hinzufügen",
           ("Installiere zuerst die App (die Erweiterung arbeitet mit ihr).",
            "Öffne diese Seite in Firefox 140 oder neuer und klicke auf <b>Zu Firefox hinzufügen</b>.",
            "Firefox fragt, ob die Installation von dieser Seite erlaubt werden soll: erlaube sie und bestätige mit "
            "<b>Hinzufügen</b>.",
            "Hefte das Symbol von Video Download an (Puzzle-Symbol → Anheften).")),
    "es": ("Firefox", "Instalación en Firefox, sin modo de desarrollador. La extensión está firmada por Mozilla y se "
           "actualiza sola.", "Añadir a Firefox",
           ("Instala primero la aplicación (la extensión trabaja con ella).",
            "Abre esta página en Firefox 140 o posterior y pulsa <b>Añadir a Firefox</b>.",
            "Firefox pide permiso para instalar desde este sitio: permítelo y confirma con <b>Añadir</b>.",
            "Fija el icono de Video Download (icono de pieza de puzle → fijar).")),
    "fr": ("Firefox", "Installation dans Firefox, sans mode développeur. L'extension est signée par Mozilla et se met à "
           "jour toute seule.", "Ajouter à Firefox",
           ("Installez d'abord l'application (l'extension fonctionne avec elle).",
            "Ouvrez cette page dans Firefox 140 ou plus récent et cliquez sur <b>Ajouter à Firefox</b>.",
            "Firefox demande d'autoriser l'installation depuis ce site : autorisez-la puis confirmez avec <b>Ajouter</b>.",
            "Épinglez l'icône de Video Download (icône de pièce de puzzle → épingler).")),
}


def firefox_section(lang: str) -> str:
    title, lead, button, steps = FIREFOX_TEXT[lang]
    items = "\n".join(f"<li>{step}</li>" for step in steps)
    return f"""<div class="box">
<h2 style="margin-top:0">{title}</h2>
<p>{html.escape(lead)}</p>
<p><a class="btn" href="{_up(lang)}{FIREFOX_XPI}">{html.escape(button)}</a></p>
<ol>
{items}
</ol>
</div>
<h2>Edge / Chrome</h2>"""


def page_extension(lang: str) -> str:
    t = TEXTS[lang]
    body = f"<h1>{t['ext_title']}</h1>\n{firefox_section(lang)}\n{extension_mock(lang)}\n{t['ext_body']}"
    return _page(lang, "extension.html", t["ext_title"], t["ext_desc"], body)


# (naslov, uvod s linkom {issue}, dugme, napomena, koraci) — nazivi iz macOS-a na tom jeziku.
MAC_TEXT = {
    "en": ("Beta", "<b>New: Video Download for Mac.</b> For Macs with an Apple chip (M1 or newer) and macOS 12 or later. "
           "It works, but only a few people have tried it so far: please <a href=\"{issue}\">report anything that doesn't work</a>.",
           "Download for Mac (beta)",
           "The Mac version isn't signed by Apple yet, so the first start takes a few extra clicks:",
           ("Open the downloaded .dmg and drag Video Download to Applications.",
            "Open the app. macOS says it can't verify it: click <b>Done</b> (not “Move to Trash”).",
            "Open <b>System Settings → Privacy &amp; Security</b>, scroll down, click <b>Open Anyway</b> and enter your Mac password.",
            "Open the app again and confirm <b>Open</b>. This is needed only once.")),
    "bs": ("Beta", "<b>Novo: Video Download za Mac.</b> Za Mac sa Apple čipom (M1 ili noviji) i macOS 12 ili noviji. "
           "Radi, ali ga je probalo još malo ljudi: <a href=\"{issue}\">javi ako nešto ne radi</a>.",
           "Preuzmi za Mac (beta)",
           "Mac verzija još nema Appleov potpis, pa prvo pokretanje traži par klikova više:",
           ("Otvori preuzeti .dmg i prevuci Video Download u Applications.",
            "Otvori program. macOS kaže da ga ne može provjeriti: klikni <b>Done</b> (ne „Move to Trash“).",
            "Otvori <b>System Settings → Privacy &amp; Security</b> (Postavke sistema → Privatnost i sigurnost), skroluj dolje, "
            "klikni <b>Open Anyway</b> (Ipak otvori) i upiši lozinku Maca.",
            "Ponovo otvori program i potvrdi <b>Open</b>. To treba samo jednom.")),
    "de": ("Beta", "<b>Neu: Video Download für Mac.</b> Für Macs mit Apple-Chip (M1 oder neuer) und macOS 12 oder neuer. "
           "Es funktioniert, aber bisher haben es erst wenige ausprobiert: <a href=\"{issue}\">melde bitte, was nicht klappt</a>.",
           "Für Mac herunterladen (Beta)",
           "Die Mac-Version ist noch nicht von Apple signiert, daher braucht der erste Start ein paar Klicks mehr:",
           ("Öffne die geladene .dmg und ziehe Video Download in den Ordner „Programme“.",
            "Öffne das Programm. macOS meldet, dass es nicht überprüft werden kann: Schließe die Meldung "
            "(nicht „In den Papierkorb legen“).",
            "Öffne <b>Systemeinstellungen → Datenschutz &amp; Sicherheit</b>, scrolle nach unten, klicke auf "
            "<b>Dennoch öffnen</b> und gib dein Mac-Passwort ein.",
            "Öffne das Programm erneut und bestätige mit <b>Öffnen</b>. Das ist nur einmal nötig.")),
    "es": ("Beta", "<b>Novedad: Video Download para Mac.</b> Para Mac con chip de Apple (M1 o posterior) y macOS 12 o posterior. "
           "Funciona, pero aún lo han probado pocas personas: <a href=\"{issue}\">avísanos si algo no funciona</a>.",
           "Descargar para Mac (beta)",
           "La versión para Mac aún no está firmada por Apple, así que el primer inicio requiere unos clics más:",
           ("Abre el .dmg descargado y arrastra Video Download a Aplicaciones.",
            "Abre la app. macOS dice que no puede verificarla: cierra el aviso (no «Trasladar a la papelera»).",
            "Ve a <b>Ajustes del Sistema → Privacidad y seguridad</b>, desplázate hacia abajo, pulsa <b>Abrir igualmente</b> "
            "e introduce la contraseña del Mac.",
            "Vuelve a abrir la app y confirma <b>Abrir</b>. Solo hace falta una vez.")),
    "fr": ("Bêta", "<b>Nouveau : Video Download pour Mac.</b> Pour les Mac avec puce Apple (M1 ou plus récent) et macOS 12 "
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


def mac_html(lang: str) -> str:
    badge, lead, button, note, steps = MAC_TEXT[lang]
    items = "\n".join(f"        <li>{step}</li>" for step in steps)
    return f"""    <div class="smartscreen mac">
      <p><span class="badge">{badge}</span> {lead.format(issue=ISSUE_URL)}</p>
      <p><a class="btn btn-small" href="{MAC_DMG_URL}">{button}</a></p>
      <p>{note}</p>
      <ol>
{items}
      </ol>
    </div>"""


def news_html(lang: str) -> str:
    cards = []
    for version, date, items in changelog.entries(lang)[:NEWS_COUNT]:
        points = "".join(f"\n          <li>{html.escape(item)}</li>" for item in items)
        cards.append(f'        <div class="card"><h3>{html.escape(version)} <span>{html.escape(date)}</span></h3><ul>'
                     f"{points}</ul></div>")
    return "\n".join(cards)


def _replace(text: str, name: str, value: str, newlines: bool = False) -> str:
    sep = "\n" if newlines else ""
    pattern = re.compile(rf"(<!-- {name} -->).*?(<!-- /{name} -->)", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"U index.html nedostaje <!-- {name} -->")
    return pattern.sub(lambda m: m.group(1) + sep + value + sep + m.group(2), text, count=1)


_LANG_SWITCH = re.compile(r'<span class="lang">.*?</span>', re.DOTALL)
_ALTERNATES = re.compile(r'(?:<link rel="alternate" hreflang="[a-z]+" href="[^"]*">\n)+')


def current_size_mb(index: str) -> int | None:
    match = re.search(r"<!-- version -->\w+ [\d.]+ · (\d+) MB<!-- /version -->", index)
    return int(match.group(1)) if match else None


def build(size_mb: int | None = None) -> dict[str, str]:
    """Sadržaj svih generisanih fajlova (putanja u site/ → tekst); ne piše ništa na disk."""
    pages = {}
    for lang in LANGUAGES:
        prefix = TEXTS[lang]["dir"]
        index = (SITE / prefix / "index.html").read_text(encoding="utf-8")
        size = size_mb or current_size_mb(index) or 0
        index = _replace(index, "version", f"{TEXTS[lang]['version']} {__version__} · {size} MB")
        index = _replace(index, "news", news_html(lang), newlines=True)
        index = _replace(index, "mac", mac_html(lang), newlines=True)
        index = _LANG_SWITCH.sub(lambda _m: switcher(lang), index, count=1)
        index = _ALTERNATES.sub(lambda _m: alternates(lang, "index.html") + "\n", index, count=1)
        pages[f"{prefix}index.html"] = index
        pages[f"{prefix}terms.html"] = page_terms(lang)
        pages[f"{prefix}privacy.html"] = page_privacy(lang)
        pages[f"{prefix}licenses.html"] = page_licenses(lang)
        pages[f"{prefix}extension.html"] = page_extension(lang)
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
