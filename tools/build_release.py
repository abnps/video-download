"""Pravi instaler: PyInstaller (aplikacija + host) → alati i dodatak → self-test → Inno Setup → SHA-256.

Pokretanje iz foldera projekta:  python tools/build_release.py
Izlaz: folder „Build" pored projekta ako postoji (C:\\Video Downloader\\Build, vidljiv Ahmedu), inače
%LOCALAPPDATA%\\VideoDownload-build; VIDEODL_BUILD_DIR ima prednost. Nikad u OneDrive.
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
# Samo Windows ima %LOCALAPPDATA%; zamjena da se modul može uvesti i na Macu (testovi, build_macos.py).
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
sys.path.insert(0, str(PROJECT))

from videodl import __version__  # noqa: E402

# Claude desktop (MSIX) preusmjerava agentove upise u %LOCALAPPDATA%, pa ih Ahmed ne vidi; zato „Build" pored projekta.
_SIBLING_BUILD = PROJECT.parent / "Build"
BUILD = Path(os.environ.get("VIDEODL_BUILD_DIR")
             or (_SIBLING_BUILD if _SIBLING_BUILD.is_dir() else LOCALAPPDATA / "VideoDownload-build"))
DIST = BUILD / "dist"
APP = DIST / "VideoDownload"
INSTALLER_OUT = BUILD / "installer"
ISCC = LOCALAPPDATA / "Programs" / "Inno Setup 6" / "ISCC.exe"
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


def ffmpeg_dir() -> Path | None:
    """Folder sa ffmpeg buildom za paket: VIDEODL_FFMPEG_DIR ili najnoviji raspakovani
    „essentials" u BUILD\\ffmpeg (ili ranije %LOCALAPPDATA%\\VideoDownload-ffmpeg). Upola je manji od „full" builda sa PATH-a,
    a ima sve što aplikacija koristi (lame, x264, aac, mov_text, webp, hls, dash)."""
    override = os.environ.get("VIDEODL_FFMPEG_DIR")
    if override:
        return Path(override)
    for cache in (BUILD / "ffmpeg", LOCALAPPDATA / "VideoDownload-ffmpeg"):
        candidates = sorted(cache.glob("x-ffmpeg-*-essentials_build/*/bin"))
        if candidates:
            return candidates[-1]
    return None


LOCK = PROJECT / "tools" / "build-lock.json"


def load_lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_source(name: str) -> Path:
    """ffmpeg/ffprobe SAMO iz pripremljenog „essentials" builda (nikad tiho sa PATH-a), node sa PATH-a."""
    if name in ("ffmpeg", "ffprobe"):
        folder = ffmpeg_dir()
        path = folder / f"{name}.exe" if folder else None
        if not path or not path.is_file():
            raise SystemExit(f"{name} iz pripremljenog builda nije pronađen (VIDEODL_FFMPEG_DIR ili "
                             "Build\\ffmpeg); build ne uzima drugi sa PATH-a.")
        return path
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"Alat {name} nije na PATH-u; potreban je za paket.")
    return Path(found).resolve()


def verify_environment(lock: dict | None = None) -> list[str]:
    """Razlike između okruženja i build-lock.json (prazno = sve odgovara)."""
    import importlib.metadata

    lock = lock or load_lock()
    problems = []
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if python != lock["python"]:
        problems.append(f"Python {python}, a traži se {lock['python']}")
    for package, version in lock["packages"].items():
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        if installed != version:
            problems.append(f"{package} {installed or 'nije instaliran'}, a traži se {version}")
    for name, spec in lock["tools"].items():
        try:
            digest = sha256_file(tool_source(name))
        except SystemExit as exc:
            problems.append(str(exc))
            continue
        if digest != spec["sha256"]:
            problems.append(f"{name}: SHA-256 {digest[:12]}…, a traži se {spec['sha256'][:12]}… ({spec['version']})")
    return problems


def run_checks() -> None:
    """Svi Python i JS testovi prije pakovanja; izlaz ide u build folder uz izdanje.
    VIDEODL_SKIP_CHECKS=1 samo za hitne slučajeve (i tada se upisuje da su preskočeni)."""
    report = BUILD / "checks.txt"
    BUILD.mkdir(parents=True, exist_ok=True)
    if os.environ.get("VIDEODL_SKIP_CHECKS") == "1":
        report.write_text("PRESKOČENO (VIDEODL_SKIP_CHECKS=1)\n", encoding="utf-8")
        print("› testovi PRESKOČENI", flush=True)
        return
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    python = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=PROJECT, env=env,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    node = subprocess.run(["node", "--test", "tests/extension/*.test.mjs"], cwd=PROJECT, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    report.write_text(f"Python testovi (izlaz {python.returncode}):\n{python.stderr}\n\n"
                      f"JS testovi (izlaz {node.returncode}):\n{node.stdout}\n", encoding="utf-8")
    if python.returncode != 0 or node.returncode != 0:
        raise SystemExit(f"Testovi nisu prošli; vidi {report}")
    print("› testovi prošli", flush=True)


def copy_tool(name: str) -> Path:
    source = tool_source(name)
    print(f"› {name}: {source}", flush=True)
    target = APP / "tools" / f"{name}.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def write_manifest(lock: dict) -> None:
    """BUILD-MANIFEST.json u paketu: tačne verzije i SHA-256 svega što je ugrađeno (za licence i provjeru)."""
    import importlib.metadata

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT, capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = ""
    manifest = {
        "app": __version__, "commit": commit, "python": sys.version.split()[0],
        "packages": {name: importlib.metadata.version(name) for name in lock["packages"]},
        "tools": {name: {"version": spec["version"], "source": spec["source"],
                         "sha256": sha256_file(APP / "tools" / f"{name}.exe")} for name, spec in lock["tools"].items()},
    }
    (APP / "BUILD-MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def write_legal(target: Path | None = None, installer_documents: bool = True) -> None:
    """Licence komponenti (puni tekstovi), pravni dokumenti na 5 jezika i stranica ugovora za instaler.
    `target` je folder paketa (Windows: APP; Mac: priprema za .app); Mac nema Inno instaler pa ni njegove dokumente."""
    import importlib.metadata

    from videodl import legal
    from videodl.i18n import LANGUAGES

    target = target or APP
    licenses = target / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    for source in (PROJECT / "installer" / "licenses").iterdir():
        shutil.copy2(source, licenses / source.name)  # GPL-3.0, LGPL-3.0, Node.js
    for distribution in legal.PYTHON_DISTRIBUTIONS:
        files = importlib.metadata.distribution(distribution).files or []
        for entry in files:
            name = Path(str(entry)).name
            if ".dist-info" in str(entry) and name.upper().startswith(("LICENSE", "NOTICE", "COPYING")):
                shutil.copy2(entry.locate(), licenses / f"{distribution}-{name}")
    shutil.copy2(legal.python_license_path(), licenses / "Python-LICENSE.txt")
    missing = [component.name for component in legal.COMPONENTS if not legal.license_files(component, licenses)]
    if missing:
        raise SystemExit(f"Nedostaje tekst licence za: {', '.join(missing)}")
    (target / "THIRD-PARTY-NOTICES.txt").write_text(legal.notices_text(licenses), encoding="utf-8")

    if not installer_documents:
        return
    documents = target / "legal"
    documents.mkdir(parents=True, exist_ok=True)
    for language in LANGUAGES:
        for kind, _key in legal.DOCUMENTS:
            shutil.copy2(legal.document_path(kind, language), documents / f"{kind}_{language}.txt")
        # Inno Setup čita UTF-8 samo sa BOM-om.
        agreement = legal.agreement_text(language).replace("\r\n", "\n").replace("\n", "\r\n")
        (documents / f"agreement_{language}.txt").write_bytes(b"\xef\xbb\xbf" + agreement.encode("utf-8"))


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
    from videodl import release_signing

    signing_key = release_signing.load_key()  # bez privatnog ključa nema izdanja (provjeri prije dugog builda)
    if release_signing.public_key_hex(signing_key) not in release_signing.PUBLIC_KEYS:
        raise SystemExit("Privatni ključ ne odgovara javnom ključu ugrađenom u aplikaciju.")
    lock = load_lock()
    problems = verify_environment(lock)
    if problems:
        raise SystemExit("Okruženje se ne slaže s tools/build-lock.json:\n  " + "\n  ".join(problems))
    run_checks()
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
    write_manifest(lock)
    write_legal()
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
    # Opis izdanja iz istih bilješki kao Pomoć → Šta je novo; UTF-8 fajl, jer Windows konzola
    # (cp1250) ne zna ispisati znakove poput „→" pa bi se opis izgubio.
    from videodl import changelog

    notes = INSTALLER_OUT / "release-notes.md"
    notes.write_text(changelog.release_notes(__version__) + "\n\nSve izmjene: Pomoć → Šta je novo.\n\n♥ Podrži projekat (dobrovoljno): https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ\n",
                     encoding="utf-8")
    # Potpisan opis izdanja (release.json + .sig): aplikacije od v0.9.6 bez njega ne instaliraju ažuriranje.
    from videodl import release_signing

    release_signing.write_signed_manifest(__version__, installer)
    # Kopija bez broja verzije: link na sajtu (releases/latest/download/VideoDownload-Setup.exe)
    # uvijek vodi na najnovije izdanje. Ažuriranje u aplikaciji traži samo ime s verzijom.
    shutil.copyfile(installer, INSTALLER_OUT / "VideoDownload-Setup.exe")
    size_mb = installer.stat().st_size / 1024 / 1024
    # Sajt pokazuje novu verziju i veličinu instalera; mijenja site/, pa ide u commit izdanja.
    # U istom procesu: ispis putanje projekta (ćirilica u „Прилози") ruši Windows konzolu (cp1250).
    sys.path.insert(0, str(PROJECT / "tools"))
    import build_site

    if build_site.write_site(round(size_mb)):
        raise SystemExit("Sajt sadrži zabranjene izraze (python tools/build_site.py ih ispisuje).")
    print(f"Instaler: {installer} ({size_mb:.0f} MB)\nSHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
