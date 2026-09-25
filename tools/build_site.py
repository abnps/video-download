"""Zvanični sajt (folder site/): stranice iz istih izvora kao aplikacija.

Pravi uslovi.html, privatnost.html, licence.html i dodatak.html iz tekstova u videodl/assets,
a u index.html osvježava „Šta je novo" (videodl/changelog.py) i verziju s veličinom instalera.
Pokreće se poslije svake izmjene tih tekstova i pri svakom izdanju; test provjerava da je sajt ažuran.

    python tools/build_site.py [--size-mb 136]
"""

import argparse
import html
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from videodl import __version__, changelog, legal  # noqa: E402

SITE = ROOT / "site"
ASSETS = ROOT / "videodl" / "assets"
LANGUAGE = "bs"
NEWS_COUNT = 3
REPO = "https://github.com/abnps/video-download"
INSTALLER_URL = f"{REPO}/releases/latest/download/VideoDownload-Setup.exe"
INSTALL_DIR = r"%LOCALAPPDATA%\Programs\Video Download\extension"

# Riječi koje reklamne stranice ne smiju sadržavati (plan sajta: bez tuđih znakova i „zaobiđi zaštitu").
# Pravni tekstovi se ne provjeravaju: moraju biti doslovno isti kao u programu i instaleru.
FORBIDDEN = re.compile(r"youtube|\byt\b(?!-dlp)|tiktok|netflix|spotify|zaobi[đd]|crack|piratsk|besplatna muzika",
                       re.IGNORECASE)
PROMO_PAGES = ("index.html", "dodatak.html")

HEAD = """<!doctype html>
<html lang="bs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Video Download</title>
<meta name="description" content="{description}">
<link rel="icon" href="assets/icon.png">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<header>
  <div class="wrap bar">
    <a class="brand" href="index.html"><img src="assets/icon.png" alt="">Video Download</a>
    <nav>
      <a href="index.html#funkcije">Funkcije</a>
      <a href="index.html#kako">Kako radi</a>
      <a href="index.html#novo">Šta je novo</a>
      <a href="index.html#pomoc">Pomoć</a>
      <a class="heart" href="index.html#podrzi">♥ Podrži</a>
    </nav>
  </div>
</header>

<main class="doc">
<a class="back" href="index.html">← Početna</a>
"""

FOOT = """</main>

<footer>
  <div class="wrap">
    <span>© 2026 Video Download</span>
    <div class="links">
      <a href="uslovi.html">Uslovi korištenja</a>
      <a href="privatnost.html">Privatnost</a>
      <a href="licence.html">Licence</a>
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
    name, sep, rest = title.partition(" — ")
    if not sep:
        return title.capitalize()
    return "Video Download — " + rest.lower()


def _asset_text(name: str) -> str:
    return (ASSETS / f"{name}_{LANGUAGE}.txt").read_text(encoding="utf-8-sig")


def _page(title: str, description: str, body: str) -> str:
    return HEAD.format(title=html.escape(title), description=html.escape(description)) + body + "\n" + FOOT


def page_terms() -> str:
    terms_title, terms = text_to_html(_asset_text("terms"))
    eula_title, eula = text_to_html(_asset_text("eula"))
    body = (f"<h1>Uslovi korištenja</h1>\n<p class=\"lead\">Isti tekst koji instaler traži da prihvatiš "
            f"(i koji je u programu: Pomoć → Ugovori i licence).</p>\n"
            f"<h2 style=\"font-size:24px\">{html.escape(_heading(terms_title))}</h2>\n{terms}\n"
            f"<h2 style=\"font-size:24px;margin-top:48px\">{html.escape(_heading(eula_title))}</h2>\n{eula}")
    return _page("Uslovi korištenja", "Uslovi korištenja i licencni ugovor programa Video Download.", body)


def page_privacy() -> str:
    _title, privacy = text_to_html(_asset_text("privacy"))
    body = f"""<h1>Privatnost</h1>
<p class="lead">Ni sajt ni program ne prikupljaju podatke o tebi.</p>
<div class="box">
<h2 style="margin-top:0">Ovaj sajt</h2>
<ul>
<li>Sajt nema kolačića, analitike, reklama ni formulara i ništa ne sprema u tvoj browser.</li>
<li>Sajt je na GitHub Pages (GitHub, Inc.). GitHub pri svakoj posjeti, kao svaki server, bilježi tehničke podatke,
npr. IP adresu, radi sigurnosti i rada servisa; vidi <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">izjavu o privatnosti GitHub-a</a>.</li>
<li>Instaler se preuzima sa GitHub-a (isti uslovi kao gore).</li>
<li>Dugme za prilog vodi na PayPal; PayPal dobija podatke tek kad ga otvoriš, po svojim pravilima.</li>
</ul>
</div>
<h2 style="font-size:24px">Program</h2>
{privacy}"""
    return _page("Privatnost", "Politika privatnosti sajta i programa Video Download.", body)


def page_licenses() -> str:
    rows = []
    for component in legal.COMPONENTS:
        note = f"<br><small>{_inline(component.note)}</small>" if component.note else ""
        rows.append(f"<tr><td><a href=\"{html.escape(component.url)}\">{html.escape(component.name)}</a>{note}</td>"
                    f"<td>{html.escape(component.license)}</td></tr>")
    body = f"""<h1>Licence</h1>
<p class="lead">Video Download koristi sljedeći softver drugih autora. Njihove licence važe za njih; puni tekstovi
licenci su u folderu <code>licenses</code> pored instaliranog programa.</p>
<table>
<tr><th>Komponenta</th><th>Licenca</th></tr>
{chr(10).join(rows)}
</table>
<div class="box">FFmpeg je pod licencom GPL-3.0: izvorni kod tačnog builda koji je u instaleru je na linkovima iznad,
a kopiju izvornog koda možeš dobiti i na zahtjev.</div>"""
    return _page("Licence", "Licence komponenti koje koristi Video Download.", body)


def page_extension() -> str:
    body = f"""<h1>Dodatak za browser</h1>
<p class="lead">Sa dodatkom preuzimaš video koji se upravo pušta, jednim klikom ili desnim klikom na link ili video.
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
<p>Ako dodatak prestane reagovati, u <code>edge://extensions</code> klikni <b>Reload</b> (Ponovo učitaj) kod dodatka.</p>"""
    return _page("Dodatak za browser", "Kako instalirati dodatak Video Download za Edge i Chrome.", body)


def news_html() -> str:
    cards = []
    for version, date, items in changelog.entries(LANGUAGE)[:NEWS_COUNT]:
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
    match = re.search(r"<!-- verzija -->Verzija [\d.]+ · (\d+) MB<!-- /verzija -->", index)
    return int(match.group(1)) if match else None


def build(size_mb: int | None = None) -> dict[str, str]:
    """Sadržaj svih generisanih fajlova (putanja u site/ → tekst); ne piše ništa na disk."""
    index = (SITE / "index.html").read_text(encoding="utf-8")
    size = size_mb or current_size_mb(index) or 0
    index = _replace(index, "verzija", f"Verzija {__version__} · {size} MB")
    index = _replace(index, "novo", news_html(), newlines=True)
    return {"index.html": index, "uslovi.html": page_terms(), "privatnost.html": page_privacy(),
            "licence.html": page_licenses(), "dodatak.html": page_extension()}


def forbidden_words(pages: dict[str, str]) -> list[str]:
    found = []
    for name, text in pages.items():
        if name not in PROMO_PAGES:
            continue
        visible = re.sub(r"<[^>]+>", " ", text)  # linkovi (npr. na GitHub) ne računaju, samo vidljiv tekst
        found += [f"{name}: {match.group(0)}" for match in FORBIDDEN.finditer(visible)]
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size-mb", type=int, help="veličina instalera u MB (inače ostaje postojeća)")
    args = parser.parse_args()
    pages = build(args.size_mb)
    problems = forbidden_words(pages)
    if problems:
        print("Zabranjeni izrazi na sajtu:\n  " + "\n  ".join(problems))
        return 1
    for name, text in pages.items():
        (SITE / name).write_text(text, encoding="utf-8", newline="\n")
    print("sajt: " + ", ".join(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
