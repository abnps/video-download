"""Firefox verzija dodatka: isti kod kao za Chrome/Edge, drugačiji manifest.

Pravi ZIP za predaju na addons.mozilla.org („On your own" = nije u katalogu, Mozilla ga samo potpiše).
Potpisan .xpi Firefox instalira trajno, bez developer moda. Predaju i potpis radi vlasnik Firefox naloga.

    python tools/build_firefox.py            → %LOCALAPPDATA%\\VideoDownload-build\\firefox\\video-download-firefox-<verzija>.zip
"""

import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from videodl.native_messaging import FIREFOX_EXTENSION_ID  # noqa: E402

EXTENSION = ROOT / "extension"
# world: "MAIN" za content skripte i scripting.executeScript postoji od Firefoxa 128.
FIREFOX_MIN_VERSION = "128.0"
SKIP = {"manifest.json", "package.json"}  # package.json služi samo za Node testove


def firefox_manifest(chrome: dict) -> dict:
    manifest = {key: value for key, value in chrome.items() if key not in ("key", "minimum_chrome_version")}
    background = dict(chrome.get("background") or {})
    background.pop("service_worker", None)
    # Firefox MV3 nema service worker: ista skripta ide kao pozadinska stranica (ES modul).
    manifest["background"] = {"scripts": ["background.js"], "type": background.get("type", "module")}
    manifest["browser_specific_settings"] = {"gecko": {
        "id": FIREFOX_EXTENSION_ID,
        "strict_min_version": FIREFOX_MIN_VERSION,
        # Dodatak ništa ne šalje autoru: linkovi idu samo programu na istom računaru.
        "data_collection_permissions": {"required": ["none"]},
    }}
    return manifest


def build(out_dir: Path | None = None) -> Path:
    chrome = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    manifest = firefox_manifest(chrome)
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "VideoDownload-build" / "firefox"
    out_dir = Path(out_dir or base)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"video-download-firefox-{manifest['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for path in sorted(EXTENSION.rglob("*")):
            relative = path.relative_to(EXTENSION).as_posix()
            if path.is_file() and relative not in SKIP:
                archive.write(path, relative)
    return target


if __name__ == "__main__":
    print(build())
