"""Vlastita preuzimanja za statistiku (Ahmed 4.10.2026): naši alati (provjera i objava izdanja, Mac potpis, kopija za
winget) preuzimaju fajlove iz izdanja, a GitHub ih broji kao i tuđa. Svako takvo preuzimanje se ovdje upiše u
`vlastita.json` na grani „statistika", pa ga site/admin.html oduzme od ukupnog broja.

Neuspjeh upisa nikad ne smije zaustaviti objavu: samo se ispiše upozorenje.
"""

import base64
import json
import subprocess
import sys

REPO = "abnps/video-download"
BRANCH = "statistika"
PATH = "vlastita.json"
KINDS = ("windows", "mac", "android")
CHECK_FILES = {"release.json": "windows", "release-macos.json": "mac", "android.json": "android"}


def classify(names) -> dict:
    """Koliko instalera i opisa izdanja (dnevna provjera) je u spisku preuzetih fajlova, po platformi."""
    downloads = dict.fromkeys(KINDS, 0)
    checks = dict.fromkeys(KINDS, 0)
    for name in names:
        if name.endswith(".exe"):
            downloads["windows"] += 1
        elif name.endswith(".dmg"):
            downloads["mac"] += 1
        elif name.endswith(".apk"):
            downloads["android"] += 1
        elif name in CHECK_FILES:
            checks[CHECK_FILES[name]] += 1
    return {"downloads": downloads, "checks": checks}


def _gh(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(["gh", *args], input=stdin, check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout


def record(names, run=_gh) -> None:
    """Dodaj preuzete fajlove u zbir na grani statistika (pročitaj, saberi, upiši)."""
    add = classify(names)
    if not any(sum(part.values()) for part in add.values()):
        return
    if run is _gh and "unittest" in sys.modules:
        return  # testovi nikad ne pišu pravu statistiku (jedan jeste 4.10.2026, prije ove zaštite)
    try:
        sha = None
        total = {"downloads": dict.fromkeys(KINDS, 0), "checks": dict.fromkeys(KINDS, 0)}
        try:
            current = json.loads(run("api", f"repos/{REPO}/contents/{PATH}?ref={BRANCH}"))
            sha = current["sha"]
            stored = json.loads(base64.b64decode(current["content"]).decode("utf-8"))
            for part in total:
                for kind in KINDS:
                    total[part][kind] = int(stored.get(part, {}).get(kind, 0))
        except subprocess.CalledProcessError:
            pass  # fajla još nema
        for part in total:
            for kind in KINDS:
                total[part][kind] += add[part][kind]
        body = {"message": "Vlastita preuzimanja (alati za objavu)", "branch": BRANCH,
                "content": base64.b64encode(json.dumps(total, indent=1).encode("utf-8")).decode("ascii")}
        if sha:
            body["sha"] = sha
        run("api", "-X", "PUT", f"repos/{REPO}/contents/{PATH}", "--input", "-", stdin=json.dumps(body))
    except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as exc:
        print(f"Upozorenje: vlastita preuzimanja nisu upisana u statistiku ({exc}).")
