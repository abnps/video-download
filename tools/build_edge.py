"""Paket dodatka za Edge Add-ons prodavnicu (partner.microsoft.com, isti Partner Center nalog kao Store).

Isti kod i manifest kao za Chrome/Edge iz foldera, samo bez polja "key": prodavnica dodatku daje svoj ID,
koji se poslije upiše u videodl/native_messaging.py (EDGE_STORE_EXTENSION_ID) da ga program prihvati.

    python tools/build_edge.py   → <build folder>\\edge\\video-download-edge-<verzija>.zip
                                   (isti build folder kao build_release.py: C:\\Video Downloader\\Build)
"""

import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTENSION = ROOT / "extension"
SKIP = {"manifest.json", "package.json"}  # package.json služi samo za Node testove


def edge_manifest(chrome: dict) -> dict:
    return {key: value for key, value in chrome.items() if key != "key"}


def build(out_dir: Path | None = None) -> Path:
    chrome = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    manifest = edge_manifest(chrome)
    sibling = ROOT.parent / "Build"  # isti izbor foldera kao build_release.py
    root = os.environ.get("VIDEODL_BUILD_DIR") or (
        sibling if sibling.is_dir() else Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "VideoDownload-build")
    out_dir = Path(out_dir or Path(root) / "edge")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"video-download-edge-{manifest['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for path in sorted(EXTENSION.rglob("*")):
            relative = path.relative_to(EXTENSION).as_posix()
            if path.is_file() and relative not in SKIP:
                archive.write(path, relative)
    return target


if __name__ == "__main__":
    print(build(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
