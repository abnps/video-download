"""Stranica „Video Download 1.0" (plan 1.0, tačka 8; 00_plan/lansiranje_1_0.md).

Pripremljena 3.10.2026, a uključuje se SAMA kad __version__ dođe do 1.0.0 (commit izdanja 1.0 na Ahmedovo
„objavi"). Do tada se ne pravi i sajt ostaje isti. Kad je uključena: stranica na svih 5 jezika, u sitemapu i
kao link na vrhu stranice „Šta je novo". Bez imena platformi u tekstu (FORBIDDEN u build_site.py važi i ovdje).
"""

import html
import re

from videodl import __version__

PAGE = "version-1.html"
VERSION = __version__  # testovi ga mijenjaju


def enabled(version: str | None = None) -> bool:
    parts = tuple(int(part) for part in re.findall(r"\d+", version or VERSION)[:3])
    return parts >= (1, 0, 0)


TEXT = {
    "en": {
        "title": "Video Download 1.0",
        "lead": "After the beta versions: one app, the same on Windows, Mac and Android. Free, no ads, no tracking.",
        "banner": "Video Download 1.0 is here — see what's new",
        "sections": [
            ("Same app everywhere", "Windows, Mac and Android get version 1.0 on the same day: MP4 up to the best "
             "quality or MP3, playlists, clips and subtitles on every device."),
            ("Safe updates", "The app updates itself and installs only updates digitally signed by us, on Windows "
             "and on Mac. The part that reads websites is refreshed without reinstalling."),
            ("Checked every day", "An automatic test downloads from the most popular sites every morning, so a "
             "change on a website is noticed and fixed quickly."),
            ("For families", "Parental control with a PIN: content for adults is never downloaded without it."),
        ],
        "android": "On Android: share a link from any app, download in the background, a home screen widget and a "
                   "quick settings tile.",
        "beta": "Mac and Android are still marked beta until they are signed by Apple and fully verified by Google.",
        "buttons": ("Download for Windows", "macOS (beta)", "Android (beta)"),
        "changelog": "All changes",
    },
    "bs": {
        "title": "Video Download 1.0",
        "lead": "Poslije beta verzija: jedan program, isti na Windowsu, Macu i Androidu. Besplatno, bez "
                "reklama i bez praćenja.",
        "banner": "Stigao je Video Download 1.0 — pogledaj šta je novo",
        "sections": [
            ("Isti program svuda", "Windows, Mac i Android dobijaju verziju 1.0 istog dana: MP4 do najboljeg "
             "kvaliteta ili MP3, liste, isječci i titlovi na svakom uređaju."),
            ("Sigurna ažuriranja", "Program se sam ažurira i instalira samo ažuriranja s našim digitalnim potpisom, "
             "na Windowsu i na Macu. Dio koji čita sajtove osvježava se bez ponovne instalacije."),
            ("Provjereno svaki dan", "Automatski test svako jutro preuzima sa najpopularnijih sajtova, pa se "
             "promjena na nekom sajtu brzo primijeti i popravi."),
            ("Za porodice", "Roditeljska zaštita s PIN-om: sadržaj za odrasle se bez njega nikad ne preuzima."),
        ],
        "android": "Na Androidu: podijeli link iz bilo koje aplikacije, preuzimanje u pozadini, widget na početnom "
                   "ekranu i pločica u Brzim podešavanjima.",
        "beta": "Mac i Android ostaju označeni kao beta dok nemaju Appleov potpis i punu Googleovu provjeru.",
        "buttons": ("Preuzmi za Windows", "macOS (beta)", "Android (beta)"),
        "changelog": "Sve izmjene",
    },
    "de": {
        "title": "Video Download 1.0",
        "lead": "Nach den Beta-Versionen: eine App, gleich unter Windows, Mac und Android. Kostenlos, ohne Werbung "
                "und ohne Tracking.",
        "banner": "Video Download 1.0 ist da – sieh dir die Neuerungen an",
        "sections": [
            ("Überall dieselbe App", "Windows, Mac und Android bekommen Version 1.0 am selben Tag: MP4 bis zur "
             "besten Qualität oder MP3, Playlists, Ausschnitte und Untertitel auf jedem Gerät."),
            ("Sichere Updates", "Die App aktualisiert sich selbst und installiert nur von uns digital signierte "
             "Updates, unter Windows und auf dem Mac. Der Teil, der Websites liest, wird ohne Neuinstallation "
             "erneuert."),
            ("Jeden Tag geprüft", "Ein automatischer Test lädt jeden Morgen von den beliebtesten Seiten, damit "
             "Änderungen an einer Website schnell bemerkt und behoben werden."),
            ("Für Familien", "Kindersicherung mit PIN: Inhalte für Erwachsene werden ohne sie nie geladen."),
        ],
        "android": "Unter Android: Link aus jeder App teilen, Download im Hintergrund, Widget auf dem Startbildschirm "
                   "und Kachel in den Schnelleinstellungen.",
        "beta": "Mac und Android bleiben als Beta markiert, bis sie von Apple signiert und von Google vollständig "
                "verifiziert sind.",
        "buttons": ("Für Windows herunterladen", "macOS (Beta)", "Android (Beta)"),
        "changelog": "Alle Änderungen",
    },
    "es": {
        "title": "Video Download 1.0",
        "lead": "Tras las versiones beta: una sola app, igual en Windows, Mac y Android. Gratis, sin "
                "anuncios y sin rastreo.",
        "banner": "Ya está aquí Video Download 1.0: mira las novedades",
        "sections": [
            ("La misma app en todas partes", "Windows, Mac y Android reciben la versión 1.0 el mismo día: MP4 hasta "
             "la mejor calidad o MP3, listas, fragmentos y subtítulos en cada dispositivo."),
            ("Actualizaciones seguras", "La app se actualiza sola e instala solo actualizaciones firmadas "
             "digitalmente por nosotros, en Windows y en Mac. La parte que lee los sitios se renueva sin "
             "reinstalar."),
            ("Comprobado cada día", "Una prueba automática descarga cada mañana de los sitios más populares, así "
             "que un cambio en un sitio se detecta y se corrige rápido."),
            ("Para familias", "Control parental con PIN: sin él nunca se descarga contenido para adultos."),
        ],
        "android": "En Android: comparte un enlace desde cualquier app, descarga en segundo plano, widget en la "
                   "pantalla de inicio y botón en los ajustes rápidos.",
        "beta": "Mac y Android siguen marcados como beta hasta tener la firma de Apple y la verificación completa "
                "de Google.",
        "buttons": ("Descargar para Windows", "macOS (beta)", "Android (beta)"),
        "changelog": "Todos los cambios",
    },
    "fr": {
        "title": "Video Download 1.0",
        "lead": "Après les versions bêta : une seule application, identique sous Windows, Mac et Android. Gratuite, "
                "sans publicité ni pistage.",
        "banner": "Video Download 1.0 est là : découvrez les nouveautés",
        "sections": [
            ("La même application partout", "Windows, Mac et Android reçoivent la version 1.0 le même jour : MP4 "
             "jusqu'à la meilleure qualité ou MP3, listes, extraits et sous-titres sur chaque appareil."),
            ("Mises à jour sûres", "L'application se met à jour seule et n'installe que des mises à jour signées "
             "numériquement par nous, sous Windows et sur Mac. La partie qui lit les sites se renouvelle sans "
             "réinstallation."),
            ("Vérifiée chaque jour", "Un test automatique télécharge chaque matin depuis les sites les plus "
             "populaires : un changement sur un site est vite repéré et corrigé."),
            ("Pour les familles", "Contrôle parental avec code PIN : sans lui, aucun contenu pour adultes n'est "
             "téléchargé."),
        ],
        "android": "Sur Android : partagez un lien depuis n'importe quelle application, téléchargement en "
                   "arrière-plan, widget sur l'écran d'accueil et tuile dans les réglages rapides.",
        "beta": "Mac et Android restent en bêta jusqu'à la signature d'Apple et la vérification complète de Google.",
        "buttons": ("Télécharger pour Windows", "macOS (bêta)", "Android (bêta)"),
        "changelog": "Toutes les modifications",
    },
}


def banner(lang: str) -> str:
    """Link na vrhu stranice „Šta je novo" (prazno dok 1.0 nije izašla)."""
    if not enabled():
        return ""
    return f'<p class="box"><a href="{PAGE}"><b>{html.escape(TEXT[lang]["banner"])}</b></a></p>'


def body(lang: str, windows_url: str, mac_url: str, android_url: str) -> tuple[str, str, str]:
    """(naslov, opis, HTML) za build_site._page."""
    t = TEXT[lang]
    esc = html.escape
    parts = [f"<h1>{esc(t['title'])}</h1>", f'<p class="lead">{esc(t["lead"])}</p>']
    for heading, text in t["sections"]:
        parts.append(f'<section class="box"><h2 style="margin-top:0">{esc(heading)}</h2><p>{esc(text)}</p></section>')
    parts.append(f"<p>{esc(t['android'])}</p>")
    windows, mac, android = t["buttons"]
    parts.append(f'<p><a class="btn" href="{esc(windows_url)}">{esc(windows)}</a> '
                 f'<a href="{esc(mac_url)}">{esc(mac)}</a> · <a href="{esc(android_url)}">{esc(android)}</a></p>')
    parts.append(f"<p><small>{esc(t['beta'])}</small></p>")
    parts.append(f'<p><a href="changelog.html">{esc(t["changelog"])}</a></p>')
    return t["title"], t["lead"], "\n".join(parts)
