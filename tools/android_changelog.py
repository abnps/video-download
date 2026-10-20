"""Bilješke o izmjenama za Android (Postavke → Verzija → Šta je novo), iz istog izvora kao računar.

    python tools/android_changelog.py   → android/app/src/main/assets/changelog.json

Uzima posljednjih 5 verzija iz videodl/changelog.py (5 jezika; srpski i hrvatski u aplikaciji koriste bosanski).
Test (tests/test_android_changelog.py) pada ako fajl nije osvježen poslije izmjene bilješki.
"""

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from videodl.changelog import CHANGES  # noqa: E402

TARGET = PROJECT / "android" / "app" / "src" / "main" / "assets" / "changelog.json"
KEEP = 5


def build() -> str:
    data = [{"version": version, "date": date, "notes": notes} for version, date, notes in CHANGES[:KEEP]]
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    TARGET.write_text(build(), encoding="utf-8")
    print(TARGET)
