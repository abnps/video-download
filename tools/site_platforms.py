"""Odjeljak „Na svakoj platformi" u Funkcijama početne stranice (Ahmed 22.11.2026).

Pri skrolanju (širok ekran) ostaje okvir uređaja, a platforme se smjenjuju; dugmad gore biraju platformu odmah.
Slike su pravi snimci programa (tools/site_platform_shots.py), okvir prozora i telefona crta CSS. Bez JavaScripta
i uz prefers-reduced-motion sve radi bez animacije; na uskom ekranu svaka platforma ima svoju sliku ispod teksta.
"""

import html

PLATFORMS = ("windows", "macos", "linux", "android")
NAMES = {"windows": "Windows", "macos": "macOS", "linux": "Linux", "android": "Android"}
PANELS = {"windows": "win", "macos": "mac", "linux": "linux", "android": "android"}
REQ_KEYS = {"windows": "win_req", "macos": "mac_req", "linux": "linux_req", "android": "android_req"}
BTN_KEYS = {"windows": "win_btn", "macos": "mac_btn", "linux": "linux_btn", "android": "android_btn"}
SIZES = {"windows": (860, 470), "macos": (860, 470), "linux": (860, 470), "android": (411, 891)}

TEXT = {
    "en": {
        "kicker": "On every platform",
        "heading": "One app.<br>Your system.",
        "sub": "The same queue, MP3 and subtitles everywhere. Scroll or pick a platform.",
        "label": "Choose a platform",
        "alt": "Video Download on {name} with downloads in progress (example titles)",
        "windows": ("At home on Windows", "Install it from the Microsoft Store or with the installer. It updates itself, "
                    "only with updates signed by us, and the browser extension sends a video in one click."),
        "macos": ("macOS on Apple chips", "A real Mac app: the menu sits in the top bar, the theme follows your Mac. "
                  "Same queue, MP3 and subtitles as on Windows."),
        "linux": ("Linux as an AppImage", "One file, no installation needed: download it, allow it to run and open it. "
                  "The extension for Chrome, Edge and Firefox works here too."),
        "android": ("Android in your pocket", "Paste a link or share it from another app. Videos go to the Gallery, "
                    "audio to Music, and downloads keep going with the screen off."),
    },
    "bs": {
        "kicker": "Na svakoj platformi",
        "heading": "Jedan program.<br>Tvoj sistem.",
        "sub": "Isti red preuzimanja, MP3 i titlovi svuda. Skrolaj ili izaberi platformu.",
        "label": "Izaberi platformu",
        "alt": "Video Download na sistemu {name}, preuzimanja u toku (izmišljeni naslovi)",
        "windows": ("Kao kod kuće na Windowsu", "Instaliraj iz Microsoft Storea ili instalerom. Sam se ažurira, samo našim "
                    "potpisanim ažuriranjima, a dodatak za browser šalje video jednim klikom."),
        "macos": ("macOS na Apple čipu", "Pravi Mac program: meni je u gornjoj traci, tema prati Mac. "
                  "Isti red preuzimanja, MP3 i titlovi kao na Windowsu."),
        "linux": ("Linux kao AppImage", "Jedan fajl, bez instalacije: preuzmi ga, dozvoli pokretanje i otvori. "
                  "I ovdje radi dodatak za Chrome, Edge i Firefox."),
        "android": ("Android u džepu", "Zalijepi link ili ga podijeli iz druge aplikacije. Video ide u Galeriju, "
                    "zvuk u Muziku, a preuzimanje ide dalje i kad ugasiš ekran."),
    },
    "de": {
        "kicker": "Auf jeder Plattform",
        "heading": "Ein Programm.<br>Dein System.",
        "sub": "Überall dieselbe Warteschlange, MP3 und Untertitel. Scrolle oder wähle eine Plattform.",
        "label": "Plattform wählen",
        "alt": "Video Download unter {name} mit laufenden Downloads (Beispieltitel)",
        "windows": ("Zu Hause unter Windows", "Installiere es aus dem Microsoft Store oder mit dem Installer. Es aktualisiert "
                    "sich selbst, nur mit von uns signierten Updates, und die Browser-Erweiterung schickt ein Video mit "
                    "einem Klick."),
        "macos": ("macOS mit Apple-Chip", "Ein echtes Mac-Programm: Das Menü sitzt in der oberen Leiste, das Design folgt "
                  "deinem Mac. Dieselbe Warteschlange, MP3 und Untertitel wie unter Windows."),
        "linux": ("Linux als AppImage", "Eine Datei, ohne Installation: herunterladen, Ausführen erlauben, öffnen. "
                  "Auch hier funktioniert die Erweiterung für Chrome, Edge und Firefox."),
        "android": ("Android für unterwegs", "Füge einen Link ein oder teile ihn aus einer anderen App. Videos landen in "
                    "der Galerie, Audio in Musik, und Downloads laufen auch bei ausgeschaltetem Bildschirm weiter."),
    },
    "es": {
        "kicker": "En cada plataforma",
        "heading": "Un programa.<br>Tu sistema.",
        "sub": "La misma cola, MP3 y subtítulos en todas partes. Desplázate o elige una plataforma.",
        "label": "Elige una plataforma",
        "alt": "Video Download en {name} con descargas en curso (títulos de ejemplo)",
        "windows": ("Como en casa en Windows", "Instálalo desde Microsoft Store o con el instalador. Se actualiza solo, únicamente "
                    "con actualizaciones firmadas por nosotros, y la extensión del navegador envía un vídeo con un clic."),
        "macos": ("macOS con chip de Apple", "Un programa de Mac de verdad: el menú está en la barra superior y el tema "
                  "sigue a tu Mac. La misma cola, MP3 y subtítulos que en Windows."),
        "linux": ("Linux como AppImage", "Un solo archivo, sin instalación: descárgalo, permite que se ejecute y ábrelo. "
                  "La extensión para Chrome, Edge y Firefox también funciona aquí."),
        "android": ("Android en el bolsillo", "Pega un enlace o compártelo desde otra app. Los vídeos van a la Galería, "
                    "el audio a Música, y las descargas siguen con la pantalla apagada."),
    },
    "fr": {
        "kicker": "Sur chaque plateforme",
        "heading": "Un programme.<br>Ton système.",
        "sub": "La même file d’attente, le MP3 et les sous-titres partout. Fais défiler ou choisis une plateforme.",
        "label": "Choisis une plateforme",
        "alt": "Video Download sous {name} avec des téléchargements en cours (titres d’exemple)",
        "windows": ("Comme chez lui sous Windows", "Installe-le depuis le Microsoft Store ou avec l’installateur. Il se met à jour "
                    "tout seul, uniquement avec des mises à jour signées par nous, et l’extension du navigateur envoie "
                    "une vidéo en un clic."),
        "macos": ("macOS sur puce Apple", "Un vrai programme Mac : le menu est dans la barre du haut, le thème suit ton "
                  "Mac. La même file, le MP3 et les sous-titres que sous Windows."),
        "linux": ("Linux en AppImage", "Un seul fichier, sans installation : télécharge-le, autorise son exécution et ouvre-le. "
                  "L’extension pour Chrome, Edge et Firefox fonctionne aussi ici."),
        "android": ("Android dans la poche", "Colle un lien ou partage-le depuis une autre appli. Les vidéos vont dans la "
                    "Galerie, l’audio dans Musique, et les téléchargements continuent écran éteint."),
    },
}


def _picture(up: str, system: str, lang: str, alt: str, eager: bool = False) -> str:
    width, height = SIZES[system]
    loading = "eager" if eager else "lazy"
    return (f'<picture><source srcset="{up}assets/platform-{system}-dark-{lang}.webp" media="(prefers-color-scheme: dark)">'
            f'<img src="{up}assets/platform-{system}-light-{lang}.webp" alt="{html.escape(alt)}" width="{width}" '
            f'height="{height}" loading="{loading}" decoding="async"></picture>')


def _device(up: str, system: str, lang: str, alt: str, *, active: bool = False) -> str:
    """Okvir: prozor Windowsa, Maca ili Linuxa (naslovna traka) ili telefon; slika je pravi snimak programa."""
    if system == "android":
        chrome = '<div class="phone-bar"><span>9:41</span><i></i></div>'
    elif system == "macos":
        chrome = '<div class="win-bar"><span class="lights"><i></i><i></i><i></i></span><b>Video Download</b></div>'
    elif system == "linux":
        chrome = '<div class="win-bar"><b>Video Download</b><span class="gnome-x">×</span></div>'
    else:
        chrome = '<div class="win-bar"><b>Video Download</b><span class="caption-btns"><i>–</i><i>□</i><i>×</i></span></div>'
    state = " is-active" if active else ""
    return (f'<figure class="device device-{system}{state}" data-device="{system}">{chrome}'
            f'{_picture(up, system, lang, alt)}</figure>')


def render(lang: str, h: dict, up: str) -> str:
    """HTML odjeljka; `h` je HOME[lang] (zahtjevi i nazivi dugmadi za svaku platformu već postoje tamo)."""
    t = TEXT[lang]
    esc = html.escape
    tabs = "".join(
        f'<button type="button" role="tab" data-platform-tab="{p}" aria-selected="{"true" if i == 0 else "false"}">'
        f'{NAMES[p]}</button>' for i, p in enumerate(PLATFORMS))
    stage = "".join(_device(up, p, lang, t["alt"].format(name=NAMES[p]), active=(i == 0))
                    for i, p in enumerate(PLATFORMS))
    steps = []
    for p in PLATFORMS:
        title, body = t[p]
        steps.append(
            f'        <article class="platform-step" data-platform-step="{p}" id="platform-{p}">\n'
            f'          <span class="platform-name">{NAMES[p]}</span>\n'
            f'          <h3>{esc(title)}</h3>\n'
            f'          <p>{esc(body)}</p>\n'
            f'          <p class="platform-req">{h[REQ_KEYS[p]]}</p>\n'
            f'          <a class="platform-link" href="#panel-{PANELS[p]}">{h[BTN_KEYS[p]]} →</a>\n'
            f'          <div class="platform-inline" data-reveal>{_device(up, p, lang, t["alt"].format(name=NAMES[p]))}</div>\n'
            f'        </article>')
    steps_html = "\n".join(steps)
    return f'''      <div class="platforms" data-platforms>
        <div class="kicker" data-reveal>{t["kicker"]}</div>
        <h2 data-reveal>{t["heading"]}</h2>
        <p class="sub" data-reveal>{t["sub"]}</p>
        <div class="platform-tabs" role="tablist" aria-label="{esc(t["label"])}">{tabs}<span class="platform-tab-glow" aria-hidden="true"></span></div>
        <div class="platform-scroll">
          <div class="platform-steps">
{steps_html}
          </div>
          <div class="platform-stage" aria-hidden="true">{stage}</div>
        </div>
      </div>'''
