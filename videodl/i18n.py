"""Prevodi aplikacije: bosanski, engleski, njemački, španski, francuski (JSON po jeziku u assets/locales, bez Qt Linguista)."""

import json
import sys
from pathlib import Path

LANGUAGES = {"bs": "Bosanski", "en": "English", "de": "Deutsch", "es": "Español", "fr": "Français"}
_ORDER = ("bs", "en", "de", "es", "fr")
FALLBACK = "en"

# Posebne vrijednosti poruka u redu (prevode se tek pri prikazu).
MESSAGE_EXISTS = "@exists"
MESSAGE_DRM = "@drm"
MESSAGE_LIVE = "@live"
MESSAGE_RETRY = "@retry"
MESSAGE_NOT_MEDIA = "@not_media"
MESSAGE_NO_SUBS = "@no_subs"  # gotovo, ali video nema titlove (ili ih sajt nije dao)
MESSAGE_NO_OUTPUT = "@no_output"  # yt-dlp javio uspjeh, a gotovog fajla nema ili je neispravan

_current = FALLBACK


def decimal(text: str) -> str:
    """Decimalni zarez za bs/de/es/fr, tačka za engleski (npr. „8,4 MB/s" / „8.4 MB/s")."""
    return text if _current == "en" else text.replace(".", ",")

# ključ: (bs, en, de, es, fr)
# Prevodi su u videodl/assets/locales/<jezik>.json, jedan fajl po jeziku s istim ključevima (Faza 4, 29.10.2026).
# TEXTS ima isti oblik kao ranije: ključ → tekstovi po redu _ORDER (bs, en, de, es, fr).
LOCALES_DIR = Path(__file__).resolve().parent / "assets" / "locales"


def _load_texts() -> dict[str, tuple[str, ...]]:
    tables = {code: json.loads((LOCALES_DIR / f"{code}.json").read_text(encoding="utf-8")) for code in _ORDER}
    keys = list(tables[_ORDER[0]])
    mismatched = {code: sorted(set(keys) ^ set(table)) for code, table in tables.items() if set(table) != set(keys)}
    if mismatched:
        raise RuntimeError(f"Jezički fajlovi nemaju iste ključeve: {mismatched}")
    return {key: tuple(tables[code][key] for code in _ORDER) for key in keys}


TEXTS: dict[str, tuple[str, str, str, str, str]] = _load_texts()


def pick_language(locale_name: str | None) -> str:
    """Jezik iz oznake kao „sr_Latn_RS", „de-AT" ili „bs"; bosanski/srpski/hrvatski idu na bosanski."""
    code = (locale_name or "").replace("-", "_").split("_")[0].lower()
    if code in ("bs", "sr", "hr", "sh", "cnr"):
        return "bs"
    return code if code in LANGUAGES else FALLBACK


def set_language(code: str) -> str:
    global _current
    _current = code if code in LANGUAGES else FALLBACK
    return _current


def get_language() -> str:
    return _current


PLATFORM = sys.platform  # testovi ga postavljaju da provjere Mac tekstove i na Windowsu
# Mac: tekst koji pominje Windows ili njegove prečice ima svoju varijantu (ključ + "_mac").
MAC_VARIANTS = {"theme.system", "help.copied", "help.chrome_step3"}
# Linux: isti tekstovi, svoja varijanta (ključ + "_linux"); prečice ostaju Ctrl+.
LINUX_VARIANTS = {"theme.system", "help.copied", "help.chrome_step3"}


def tr(key: str, **values) -> str:
    mac = PLATFORM == "darwin"
    if mac and key in MAC_VARIANTS:
        key += "_mac"
    elif PLATFORM.startswith("linux") and key in LINUX_VARIANTS:
        key += "_linux"
    texts = TEXTS.get(key)
    if texts is None:
        return key
    text = texts[_ORDER.index(_current)]
    if mac:
        text = text.replace("Ctrl+", "⌘").replace("Strg+", "⌘")  # prečice na Macu idu preko Cmd tipke
    return text.format(**values) if values else text
