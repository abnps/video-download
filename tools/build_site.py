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
INSTALLER_URL = f"{REPO}/releases/latest/download/VideoDownload-Setup.exe"
INSTALL_DIR = r"%LOCALAPPDATA%\Programs\Video Download\extension"
GITHUB_PRIVACY = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"

# Riječi koje reklamne stranice ne smiju sadržavati (plan sajta: bez tuđih znakova i „zaobiđi zaštitu").
# Pravni tekstovi se ne provjeravaju: moraju biti doslovno isti kao u programu i instaleru.
FORBIDDEN = re.compile(r"youtube|\byt\b(?!-dlp)|tiktok|netflix|spotify|zaobi[đd]|crack|piratsk|besplatna muzika"
                       r"|free music|bypass", re.IGNORECASE)
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
on a link or video. Works in Edge and Chrome.</p>
<h2>Installation (once)</h2>
<ol>
<li>Install the app (the extension comes with it).</li>
<li>In your browser open <code>edge://extensions</code> (Edge) or <code>chrome://extensions</code> (Chrome).</li>
<li>Turn on <b>Developer mode</b> and click <b>Load unpacked</b>.</li>
<li>Choose the folder <code>{html.escape(INSTALL_DIR)}</code>. The app also shows the exact path:
Help → Downloading from the browser.</li>
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
Radi u Edge-u i Chrome-u.</p>
<h2>Instalacija (jednom)</h2>
<ol>
<li>Instaliraj program (dodatak dolazi s njim).</li>
<li>U browseru otvori <code>edge://extensions</code> (Edge) ili <code>chrome://extensions</code> (Chrome).</li>
<li>Uključi <b>Developer mode</b> (Način za programere) i klikni <b>Load unpacked</b> (Učitaj raspakovano).</li>
<li>Izaberi folder <code>{html.escape(INSTALL_DIR)}</code>. Tačnu putanju prikazuje i program:
Pomoć → Preuzimanje iz browsera.</li>
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
    for component in legal.COMPONENTS:
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


def page_extension(lang: str) -> str:
    t = TEXTS[lang]
    return _page(lang, "extension.html", t["ext_title"], t["ext_desc"], f"<h1>{t['ext_title']}</h1>\n{t['ext_body']}")


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
