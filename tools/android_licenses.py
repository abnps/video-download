"""Licence za Android (Postavke → Licence): osvježava android/app/src/main/assets/licenses.

    python tools/android_licenses.py

NOTICES.txt pravi iz `videodl.legal.ANDROID_COMPONENTS`; licence yt-dlp-a i Pythona kopira iz instaliranih
paketa (iste verzije kao u APK-u, vidi tools/build-lock.json i android/app/build.gradle.kts). Apache-2.0,
Chaquopy i 0BSD su stalni tekstovi u repou. `tests/test_android_licenses.py` pada ako nešto ne odgovara.
"""

import shutil
import sys
from importlib import metadata
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from videodl import legal  # noqa: E402

TARGET = PROJECT / "android" / "app" / "src" / "main" / "assets" / "licenses"


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    (TARGET / "NOTICES.txt").write_text(legal.android_notices_text(), encoding="utf-8", newline="\n")
    ytdlp = next(f for f in metadata.distribution("yt-dlp").files if f.name == "LICENSE")
    shutil.copyfile(ytdlp.locate(), TARGET / "yt-dlp-LICENSE")
    shutil.copyfile(legal.python_license_path(), TARGET / "Python-LICENSE.txt")
    shutil.copyfile(PROJECT / "android" / "app" / "src" / "main" / "cpp" / "lame" / "COPYING", TARGET / "LAME-COPYING.txt")
    print(f"Licence osvježene u {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
