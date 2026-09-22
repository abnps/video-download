"""Pravi instaler: PyInstaller (aplikacija + host) → alati i dodatak → self-test → Inno Setup → SHA-256.

Pokretanje iz foldera projekta:  python tools/build_release.py
Izlaz ide van OneDrive-a: %LOCALAPPDATA%\\VideoDownload-build (ili VIDEODL_BUILD_DIR).
"""

import filecmp
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from videodl import __version__  # noqa: E402

BUILD = Path(os.environ.get("VIDEODL_BUILD_DIR") or Path(os.environ["LOCALAPPDATA"]) / "VideoDownload-build")
DIST = BUILD / "dist"
APP = DIST / "VideoDownload"
INSTALLER_OUT = BUILD / "installer"
ISCC = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Inno Setup 6" / "ISCC.exe"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def run(command: list[str], **kwargs) -> None:
    print("›", " ".join(str(part) for part in command[:6]), "…" if len(command) > 6 else "", flush=True)
    subprocess.run(command, check=True, **kwargs)


def make_icon(target: Path) -> None:
    """ICO sa PNG slojevima (podržano od Windowsa Vista), nacrtan istom funkcijom kao ikone dodatka."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QGuiApplication

    sys.path.insert(0, str(PROJECT / "tools"))
    from make_icons import draw

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    images = []
    for size in ICON_SIZES:
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        draw(size).save(buffer, "PNG")
        images.append((size, bytes(data)))
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, blobs = b"", b""
    for size, png in images:
        edge = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", edge, edge, 0, 0, 1, 32, len(png), offset + len(blobs))
        blobs += png
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(header + entries + blobs)


def pyinstaller(*args: str) -> None:
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
         "--distpath", str(DIST), "--workpath", str(BUILD / "work"), "--specpath", str(BUILD / "spec"), *args],
        cwd=PROJECT)


def copy_tool(name: str) -> Path:
    source = shutil.which(name)
    if not source:
        raise SystemExit(f"Alat {name} nije na PATH-u; potreban je za paket.")
    target = APP / "tools" / f"{name}.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(source).resolve(), target)
    return target


def write_notices() -> None:
    (APP / "THIRD-PARTY-NOTICES.txt").write_text("""Video Download uključuje sljedeći softver treće strane:

- yt-dlp (Unlicense) — https://github.com/yt-dlp/yt-dlp
- yt-dlp-ejs (Unlicense/MIT) — https://github.com/yt-dlp/ejs
- Qt for Python / PySide6 (LGPLv3) — https://doc.qt.io/qtforpython/ ; izvorni kod: https://code.qt.io/
- FFmpeg (GPLv3 build) — https://ffmpeg.org/ ; izvorni kod i build: https://www.gyan.dev/ffmpeg/builds/
  Izvorni kod korišćenog ffmpeg builda dostupan je na https://www.gyan.dev/ffmpeg/builds/ (odjeljak
  „source code"), u skladu sa GPLv3. Na zahtjev se može dostaviti i kopija tog izvornog koda.
- Node.js (MIT i licence zavisnosti) — https://nodejs.org/ ; licence: https://github.com/nodejs/node/blob/main/LICENSE
- curl_cffi (MIT) — https://github.com/lexiforest/curl_cffi
- Python (PSF License) — https://www.python.org/

Licence se odnose na navedene komponente; FFmpeg i Qt se mogu zamijeniti drugim verzijama.
""", encoding="utf-8")


def verify_package() -> None:
    """Prekinut build je jednom ostavio male fajlove pune nula (ikone dodatka, DRM skripte)."""
    problems = []
    for root, target in ((PROJECT / "extension", APP / "extension"),
                         (PROJECT / "videodl" / "assets", APP / "_internal" / "videodl" / "assets")):
        for source in root.rglob("*"):
            if source.is_file() and source.name != "package.json":
                copy = target / source.relative_to(root)
                if not copy.is_file() or not filecmp.cmp(source, copy, shallow=False):
                    problems.append(str(copy.relative_to(APP)))
    for path in APP.rglob("*"):
        if path.is_file() and 0 < path.stat().st_size <= 64 * 1024 and not path.read_bytes().strip(b"\0"):
            problems.append(str(path.relative_to(APP)))
    if problems:
        raise SystemExit("Paket je oštećen (razlika ili same nule): " + ", ".join(sorted(set(problems))))


def main() -> int:
    if not ISCC.is_file():
        raise SystemExit(f"Inno Setup nije pronađen: {ISCC}")
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.rmtree(INSTALLER_OUT, ignore_errors=True)
    icon = BUILD / "icon.ico"
    make_icon(icon)

    pyinstaller("--windowed", "--name", "VideoDownload", "--icon", str(icon),
                "--add-data", f"{PROJECT / 'videodl' / 'assets'}{os.pathsep}videodl/assets",
                "--collect-data", "yt_dlp_ejs", "--collect-all", "curl_cffi",
                str(PROJECT / "pokreni.pyw"))
    pyinstaller("--onefile", "--console", "--name", "videodl-host", "--icon", str(icon),
                str(PROJECT / "videodl" / "native_host.py"))
    shutil.move(str(DIST / "videodl-host.exe"), APP / "videodl-host.exe")

    # Dodatak ide bez razvojnog package.json-a.
    shutil.copytree(PROJECT / "extension", APP / "extension", ignore=shutil.ignore_patterns("package.json"))
    for tool in ("ffmpeg", "ffprobe", "node"):
        copy_tool(tool)
    write_notices()
    verify_package()

    report = BUILD / "self-test.json"
    report.unlink(missing_ok=True)
    result = subprocess.run([str(APP / "VideoDownload.exe"), "--self-test", str(report)], timeout=120)
    checks = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
    print("self-test:", json.dumps(checks, ensure_ascii=False))
    if result.returncode != 0 or not checks.get("ok") or checks.get("version") != __version__:
        raise SystemExit("Self-test spakovane aplikacije nije prošao.")

    run([str(ISCC), "/Q", f"/DAppVersion={__version__}", f"/DSourceDir={APP}", f"/DIconFile={icon}",
         f"/DOutputDir={INSTALLER_OUT}", str(PROJECT / "installer" / "VideoDownload.iss")])
    installer = INSTALLER_OUT / f"VideoDownload-Setup-{__version__}.exe"
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    Path(f"{installer}.sha256").write_text(f"{digest}  {installer.name}\n", encoding="ascii")
    size_mb = installer.stat().st_size / 1024 / 1024
    print(f"Instaler: {installer} ({size_mb:.0f} MB)\nSHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
