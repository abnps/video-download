"""Vodič „Instalacija jednom komandom (winget)" na sajtu, 5 jezika (Ahmed 3.10.2026).

Skriven dok Microsoft ne prihvati paket (PR microsoft/winget-pkgs #445943): komanda prije toga javlja
„paket nije pronađen". Kad PR bude spojen: LIVE = True, `python tools/build_site.py`, commit.
Tada je stranica u vodičima (kartica na vrhu), u sitemapu i sama u sebi; bez LIVE sajt ostaje isti.
"""

import html

LIVE = False  # True tek kad je abnps.VideoDownload prihvaćen u winget katalog
PAGE = "winget.html"
PACKAGE = "abnps.VideoDownload"
COMMANDS = {"install": f"winget install {PACKAGE}", "upgrade": f"winget upgrade {PACKAGE}",
            "uninstall": f"winget uninstall {PACKAGE}"}


def enabled() -> bool:
    return LIVE


TEXT = {
    "en": {
        "title": "Install with one command (winget)",
        "subtitle": "For Windows 10 and 11: install, update and remove from the terminal",
        "lead": "winget is the package manager built into Windows 10 and 11. One command downloads and installs "
                "Video Download, with no browser and no clicking through the installer.",
        "steps": ("Right-click the Start button and choose Terminal (on Windows 10: Windows PowerShell).",
                  "Type the command below and press Enter:",
                  "If asked, confirm the source agreement with Y. When the installation finishes, find Video "
                  "Download in the Start menu."),
        "more": "Updating and removing",
        "upgrade": "Update to the newest version (the app also updates itself):",
        "uninstall": "Remove the app:",
        "tips": ("If the terminal says winget is not recognized, install or update App Installer from the Microsoft "
                 "Store, then open a new terminal.",
                 "The installer is the same file as the download button on this site, digitally signed updates "
                 "included.",
                 "Prefer clicking? Use the normal installer:"),
    },
    "bs": {
        "title": "Instalacija jednom komandom (winget)",
        "subtitle": "Za Windows 10 i 11: instalacija, ažuriranje i uklanjanje iz terminala",
        "lead": "winget je upravitelj paketa ugrađen u Windows 10 i 11. Jedna komanda preuzme i instalira Video "
                "Download, bez browsera i bez klikanja kroz instaler.",
        "steps": ("Desni klik na dugme Start i izaberi Terminal (na Windowsu 10: Windows PowerShell).",
                  "Upiši komandu ispod i pritisni Enter:",
                  "Ako te pita, potvrdi uslove izvora slovom Y. Kad se instalacija završi, Video Download je u "
                  "meniju Start."),
        "more": "Ažuriranje i uklanjanje",
        "upgrade": "Ažuriranje na najnoviju verziju (program se ažurira i sam):",
        "uninstall": "Uklanjanje programa:",
        "tips": ("Ako terminal kaže da ne prepoznaje winget, instaliraj ili ažuriraj App Installer (Instalacijski "
                 "program aplikacija) iz Microsoft Storea, pa otvori novi terminal.",
                 "Instaler je isti fajl kao na dugmetu za preuzimanje na ovom sajtu, s digitalno potpisanim "
                 "ažuriranjima.",
                 "Radije klikom? Koristi običan instaler:"),
    },
    "de": {
        "title": "Installation mit einem Befehl (winget)",
        "subtitle": "Für Windows 10 und 11: installieren, aktualisieren und entfernen im Terminal",
        "lead": "winget ist die in Windows 10 und 11 eingebaute Paketverwaltung. Ein Befehl lädt und installiert "
                "Video Download, ohne Browser und ohne Klicken durch den Installer.",
        "steps": ("Klicke mit der rechten Maustaste auf Start und wähle Terminal (unter Windows 10: Windows "
                  "PowerShell).",
                  "Gib den folgenden Befehl ein und drücke Enter:",
                  "Bestätige bei Nachfrage die Quellvereinbarung mit Y. Nach der Installation findest du Video "
                  "Download im Startmenü."),
        "more": "Aktualisieren und entfernen",
        "upgrade": "Auf die neueste Version aktualisieren (die App aktualisiert sich auch selbst):",
        "uninstall": "App entfernen:",
        "tips": ("Wenn das Terminal winget nicht erkennt, installiere oder aktualisiere den App-Installer aus dem "
                 "Microsoft Store und öffne ein neues Terminal.",
                 "Der Installer ist dieselbe Datei wie hinter dem Download-Button dieser Seite, inklusive digital "
                 "signierter Updates.",
                 "Lieber per Klick? Nimm den normalen Installer:"),
    },
    "es": {
        "title": "Instalar con un solo comando (winget)",
        "subtitle": "Para Windows 10 y 11: instalar, actualizar y desinstalar desde la terminal",
        "lead": "winget es el administrador de paquetes integrado en Windows 10 y 11. Un solo comando descarga e "
                "instala Video Download, sin navegador y sin pasar por el instalador.",
        "steps": ("Haz clic derecho en el botón Inicio y elige Terminal (en Windows 10: Windows PowerShell).",
                  "Escribe el comando de abajo y pulsa Intro:",
                  "Si te lo pide, acepta el acuerdo del origen con Y. Al terminar, Video Download está en el menú "
                  "Inicio."),
        "more": "Actualizar y desinstalar",
        "upgrade": "Actualizar a la última versión (la app también se actualiza sola):",
        "uninstall": "Desinstalar la app:",
        "tips": ("Si la terminal no reconoce winget, instala o actualiza el Instalador de aplicaciones desde "
                 "Microsoft Store y abre una terminal nueva.",
                 "El instalador es el mismo archivo que el botón de descarga de este sitio, con actualizaciones "
                 "firmadas digitalmente.",
                 "¿Prefieres hacer clic? Usa el instalador normal:"),
    },
    "fr": {
        "title": "Installer en une commande (winget)",
        "subtitle": "Pour Windows 10 et 11 : installer, mettre à jour et désinstaller depuis le terminal",
        "lead": "winget est le gestionnaire de paquets intégré à Windows 10 et 11. Une seule commande télécharge et "
                "installe Video Download, sans navigateur ni clics dans le programme d'installation.",
        "steps": ("Faites un clic droit sur le bouton Démarrer et choisissez Terminal (sous Windows 10 : Windows "
                  "PowerShell).",
                  "Tapez la commande ci-dessous et appuyez sur Entrée :",
                  "Si on vous le demande, acceptez l'accord de la source avec Y. À la fin, Video Download se trouve "
                  "dans le menu Démarrer."),
        "more": "Mettre à jour et désinstaller",
        "upgrade": "Mettre à jour vers la dernière version (l'application se met aussi à jour seule) :",
        "uninstall": "Désinstaller l'application :",
        "tips": ("Si le terminal ne reconnaît pas winget, installez ou mettez à jour le Programme d'installation "
                 "d'application depuis le Microsoft Store, puis ouvrez un nouveau terminal.",
                 "Le programme d'installation est le même fichier que le bouton de téléchargement de ce site, mises "
                 "à jour signées numériquement comprises.",
                 "Vous préférez cliquer ? Utilisez le programme d'installation habituel :"),
    },
}


def _code(command: str) -> str:
    return f'<pre class="box"><code>{html.escape(command)}</code></pre>'


def hub_card(lang: str) -> str:
    if not enabled():
        return ""
    t = TEXT[lang]
    return (f'<li><a href="{PAGE}"><b>{html.escape(t["title"])}</b></a>'
            f'<br><span>{html.escape(t["subtitle"])}</span></li>')


def guide_body(lang: str, installer_url: str, win_button: str, hub: tuple) -> tuple[str, str, str]:
    """`hub` je site_guides.HUB[lang] (oznake „Koraci", „Dobro je znati", „Svi vodiči")."""
    t = TEXT[lang]
    esc = html.escape
    first, second, third = t["steps"]
    clicked, signed, normal = t["tips"]
    body = f"""<h1>{esc(t['title'])}</h1>
<p class="lead">{esc(t['lead'])}</p>
<h2>{hub[7]}</h2>
<ol class="guide-steps">
<li>{esc(first)}</li>
<li>{esc(second)}{_code(COMMANDS['install'])}</li>
<li>{esc(third)}</li>
</ol>
<h2>{esc(t['more'])}</h2>
<p>{esc(t['upgrade'])}</p>
{_code(COMMANDS['upgrade'])}
<p>{esc(t['uninstall'])}</p>
{_code(COMMANDS['uninstall'])}
<h2>{hub[8]}</h2>
<ul>
<li>{esc(clicked)}</li>
<li>{esc(signed)}</li>
<li>{esc(normal)} <a href="{esc(installer_url)}">{win_button}</a></li>
</ul>
<p><a href="guides.html">{hub[5]} →</a></p>"""
    return t["title"], t["subtitle"], body
