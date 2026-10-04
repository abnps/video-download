"""Vlastita preuzimanja za statistiku (Ahmed 4.10.2026): naši alati (provjera i objava izdanja, Mac potpis, kopija za
winget, objava Androida) preuzimaju fajlove iz izdanja, a GitHub ih broji kao i tuđa. Svako takvo preuzimanje se
upiše u `<Build>/statistika/vlastita.json` NA OVOM RAČUNARU (Ahmed: „ne želim da drugi vide te podatke"), pa ga
tools/statistika.py oduzme od ukupnog broja.

Neuspjeh upisa nikad ne smije zaustaviti objavu: samo se ispiše upozorenje.
"""

import json
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent.parent / "Build" / "statistika" / "vlastita.json"
KINDS = ("windows", "mac", "android")
CHECK_FILES = {"release.json": "windows", "release-macos.json": "mac", "android.json": "android"}


def empty() -> dict:
    return {"downloads": dict.fromkeys(KINDS, 0), "checks": dict.fromkeys(KINDS, 0)}


def classify(names) -> dict:
    """Koliko instalera i opisa izdanja (dnevna provjera) je u spisku preuzetih fajlova, po platformi."""
    counted = empty()
    for name in names:
        if name.endswith(".exe"):
            counted["downloads"]["windows"] += 1
        elif name.endswith(".dmg"):
            counted["downloads"]["mac"] += 1
        elif name.endswith(".apk"):
            counted["downloads"]["android"] += 1
        elif name in CHECK_FILES:
            counted["checks"][CHECK_FILES[name]] += 1
    return counted


def load(path: Path = DEFAULT) -> dict:
    total = empty()
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        for part in total:
            for kind in KINDS:
                total[part][kind] = int(stored.get(part, {}).get(kind, 0))
    except (OSError, ValueError, AttributeError):
        pass  # fajla još nema ili je oštećen: kreće od nule
    return total


def record(names, path: Path | None = None) -> None:
    """Dodaj preuzete fajlove u zbir u lokalnom fajlu."""
    if path is None and "unittest" in sys.modules:
        return  # testovi nikad ne pišu pravu statistiku
    path = path or DEFAULT
    add = classify(names)
    if not any(sum(part.values()) for part in add.values()):
        return
    try:
        total = load(path)
        for part in total:
            for kind in KINDS:
                total[part][kind] += add[part][kind]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(total, indent=1), encoding="utf-8")
    except OSError as exc:
        print(f"Upozorenje: vlastita preuzimanja nisu upisana u statistiku ({exc}).")
