"""Impressum (§ 5 DDG, Njemačka) za sajt: stranica impressum.html na svih 5 jezika i link u podnožju.

Ahmed 3.10.2026: „napravi to" — bez pravnika, po standardnom sadržaju za privatnu stranicu s dugmetom za
priloge. Stranica se NE pravi dok DATA nije popunjen (ime, adresa za dostavu pošte, drugi brz kontakt);
do tada sajt ostaje kakav jeste. Kao e-pošta ide samo javna adresa projekta, nikad lični e-mail.
Pravni dio je na njemačkom (to zakon traži); ostali jezici dobijaju kratko objašnjenje iznad njega.
"""

import html

# Popunjava se TEK po Ahmedovim podacima, npr.:
# DATA = {"name": "Ime Prezime", "street": "Ulica 1", "city": "12345 Grad", "country": "Deutschland",
#         "phone": "+49 …"}  # ili "contact_form": "https://…" umjesto telefona
DATA: dict | None = {"name": "Ahmed Biševac", "street": "Im Niederbruch 9a", "city": "46509 Xanten",
                     "country": "Deutschland", "phone": "+49 176 79916914"}  # Ahmed 3.10.2026

PAGE = "impressum.html"

# (naslov u podnožju i na stranici, objašnjenje iznad njemačkog teksta)
TEXT = {
    "en": ("Legal notice (Impressum)", "Information about the provider of this website, required by German law."),
    "bs": ("Impressum (podaci o autoru)", "Podaci o autoru ovog sajta, kako ih traži njemački zakon."),
    "de": ("Impressum", ""),
    "es": ("Aviso legal (Impressum)", "Información sobre el responsable de este sitio, exigida por la ley alemana."),
    "fr": ("Mentions légales (Impressum)", "Informations sur l'éditeur de ce site, exigées par la loi allemande."),
}


def enabled() -> bool:
    return bool(DATA)


def footer_link(lang: str) -> str:
    return f'<a href="{PAGE}">{html.escape(TEXT[lang][0])}</a>' if enabled() else ""


def body(lang: str, email: str) -> tuple[str, str, str]:
    """(naslov, opis, HTML) za build_site._page."""
    assert DATA, "Impressum nema podataka"
    title, lead = TEXT[lang]
    esc = {key: html.escape(str(value)) for key, value in DATA.items()}
    contact = [f"E-Mail: <a href=\"mailto:{html.escape(email)}\">{html.escape(email)}</a>"]
    if esc.get("phone"):
        contact.append(f"Telefon: {esc['phone']}")
    if esc.get("contact_form"):
        contact.append(f"Kontaktformular: <a href=\"{esc['contact_form']}\">{esc['contact_form']}</a>")
    intro = f'<p class="lead">{html.escape(lead)}</p>\n' if lead else ""
    content = f"""<h1>{html.escape(title)}</h1>
{intro}<div class="box" lang="de">
<h2 style="margin-top:0">Angaben gemäß § 5 DDG</h2>
<p>{esc['name']}<br>{esc['street']}<br>{esc['city']}<br>{esc.get('country', 'Deutschland')}</p>
<h2>Kontakt</h2>
<p>{'<br>'.join(contact)}</p>
<p>Video Download ist ein privates, kostenloses Projekt; freiwillige Unterstützung schaltet nichts frei.</p>
</div>"""
    return title, lead or title, content
