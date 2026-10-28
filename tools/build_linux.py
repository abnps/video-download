"""Linux (x86_64) paket: PyInstaller folder → alati i dodatak → provjere → AppImage. Beta.

Pokreće se na Linuxu (GitHub Actions ubuntu-22.04, pa radi na sistemima s istim ili novijim glibc-om), iz foldera
projekta:
    python tools/build_linux.py
Izlaz: <build folder>/linux/VideoDownload-linux-x86_64-<verzija>.AppImage (+ .sha256). Build folder je isti kao za
Windows i Mac (VIDEODL_BUILD_DIR, folder „Build" pored projekta ili zamjena).

Alati (ffmpeg, ffprobe, node) i alati za pakovanje (appimagetool, AppImage runtime) se preuzimaju sa adresa iz
tools/build-lock.json („linux_tools", „appimage_tools") i provjeravaju po SHA-256. AppImage nema potpis sistema
kao Mac ili Windows; ažuriranje programa provjerava naš potpis (release-linux.json, tools/sign_linux.py).
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tools"))

import build_macos  # noqa: E402  (preuzimanje alata po lock-u, BUILD-MANIFEST)
import build_release  # noqa: E402  (zajednički dijelovi: lock, testovi, licence)
from build_macos import run  # noqa: E402
from videodl import __version__  # noqa: E402

APP_NAME = "Video Download"
EXECUTABLE = "VideoDownload"
DESKTOP_ID = "io.github.abnps.videodownload"
WORK = build_release.BUILD / "linux"
STAGE = WORK / "stage"  # sve što ide u paket, prije PyInstallera
DIST = WORK / "dist"
APPDIR = WORK / "AppDir"
APPIMAGE = WORK / f"VideoDownload-linux-x86_64-{__version__}.AppImage"

# AppRun: pokreće program iz AppImage-a i prosljeđuje argumente (browser tako pokreće host).
APPRUN = """#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/VideoDownload/VideoDownload" "$@"
"""

DESKTOP_ENTRY = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Save videos as MP4 or audio as MP3
Exec={EXECUTABLE}
Icon={DESKTOP_ID}
Categories=AudioVideo;Network;
Terminal=false
StartupWMClass={EXECUTABLE}
"""


def check_environment(lock: dict) -> None:
    import importlib.metadata

    if not sys.platform.startswith("linux") or platform.machine() != "x86_64":
        raise SystemExit("Linux paket se pravi na Linuxu, x86_64.")
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
    if problems:
        raise SystemExit("Okruženje se ne slaže s tools/build-lock.json:\n  " + "\n  ".join(problems))


def make_icon(target: Path) -> None:
    """Ikona istom funkcijom kao za Windows, Mac i dodatak."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    from make_icons import draw

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    draw(256).save(str(target), "PNG")


def check_app(executable: Path, bundled: Path, env: dict | None = None) -> None:
    """Self-test spakovanog programa i host način (browser pokreće isti program s porijeklom dodatka)."""
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", **(env or {})}
    report = WORK / "self-test.json"
    report.unlink(missing_ok=True)
    result = subprocess.run([str(executable), "--self-test", str(report)], timeout=180, env=env)
    checks = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
    print("self-test:", json.dumps(checks, ensure_ascii=False), flush=True)
    if result.returncode != 0 or not checks.get("ok") or checks.get("version") != __version__:
        raise SystemExit(f"Self-test nije prošao: {executable}")
    for tool in ("ffmpeg", "ffprobe", "node"):
        if not str(checks.get(tool) or "").startswith(str(bundled)):
            raise SystemExit(f"{tool} nije iz paketa nego {checks.get(tool)}")

    body = json.dumps({"action": "status"}).encode("utf-8")
    message = len(body).to_bytes(4, "little") + body
    host = subprocess.run([str(executable), "chrome-extension://jfgcekfmjipklibljeacchccmebppklp/"], input=message,
                          capture_output=True, timeout=60, env=env)
    reply = json.loads(host.stdout[4:].decode("utf-8")) if len(host.stdout) > 4 else {}
    print("host:", reply, flush=True)
    if not reply.get("ok"):
        raise SystemExit(f"Host način ne odgovara: {host.stdout[:200]!r} {host.stderr[-400:]!r}")


def make_appdir(program: Path) -> None:
    shutil.rmtree(APPDIR, ignore_errors=True)
    (APPDIR / "usr" / "lib").mkdir(parents=True)
    shutil.copytree(program, APPDIR / "usr" / "lib" / EXECUTABLE, symlinks=True)
    apprun = APPDIR / "AppRun"
    apprun.write_text(APPRUN, encoding="utf-8")
    apprun.chmod(0o755)
    (APPDIR / f"{DESKTOP_ID}.desktop").write_text(DESKTOP_ENTRY, encoding="utf-8")
    make_icon(APPDIR / f"{DESKTOP_ID}.png")
    shutil.copyfile(APPDIR / f"{DESKTOP_ID}.png", APPDIR / ".DirIcon")


def make_appimage(lock: dict) -> None:
    tools = lock["appimage_tools"]
    downloads = WORK / "downloads"
    appimagetool = build_macos.download("appimagetool", tools["appimagetool"], downloads)
    appimagetool.chmod(0o755)
    runtime_file = build_macos.download("runtime", tools["runtime"], downloads)
    APPIMAGE.unlink(missing_ok=True)
    # appimagetool je i sam AppImage: bez FUSE-a na CI računaru se raspakuje i pokrene.
    env = {**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    run([str(appimagetool), "--no-appstream", "--runtime-file", str(runtime_file), str(APPDIR), str(APPIMAGE)],
        env=env)
    APPIMAGE.chmod(0o755)
    digest = hashlib.sha256(APPIMAGE.read_bytes()).hexdigest()
    Path(f"{APPIMAGE}.sha256").write_text(f"{digest}  {APPIMAGE.name}\n", encoding="ascii")
    print(f"AppImage: {APPIMAGE} ({APPIMAGE.stat().st_size / 1024 / 1024:.0f} MB)\nSHA-256: {digest}", flush=True)


def main() -> int:
    lock = build_release.load_lock()
    check_environment(lock)
    build_release.run_checks()
    for folder in (STAGE, DIST, WORK / "work"):
        shutil.rmtree(folder, ignore_errors=True)
    STAGE.mkdir(parents=True)

    tools = build_macos.fetch_tools(lock, "linux_tools", WORK, STAGE)
    shutil.copytree(PROJECT / "extension", STAGE / "extension", ignore=shutil.ignore_patterns("package.json"))
    build_release.write_legal(STAGE, installer_documents=False)
    build_macos.write_manifest(lock, tools, "linux_tools", "linux-x86_64", STAGE)

    separator = os.pathsep
    args = ["--windowed", "--name", EXECUTABLE,
            "--add-data", f"{PROJECT / 'videodl' / 'assets'}{separator}videodl/assets",
            "--add-data", f"{STAGE / 'extension'}{separator}extension",
            "--add-data", f"{STAGE / 'licenses'}{separator}licenses",
            "--add-data", f"{STAGE / 'THIRD-PARTY-NOTICES.txt'}{separator}.",
            "--add-data", f"{STAGE / 'BUILD-MANIFEST.json'}{separator}.",
            "--collect-data", "yt_dlp_ejs", "--collect-all", "curl_cffi"]
    for name in build_macos.TOOL_FILES:
        args += ["--add-binary", f"{tools / name}{separator}tools"]
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
         "--distpath", str(DIST), "--workpath", str(WORK / "work"), "--specpath", str(WORK),
         *args, str(PROJECT / "pokreni.pyw")], cwd=PROJECT)

    program = DIST / EXECUTABLE
    check_app(program / EXECUTABLE, program)
    make_appdir(program)
    make_appimage(lock)
    # Gotov AppImage (raspakovan, jer CI računar nema FUSE): isti self-test i host način.
    check_app(APPIMAGE, Path("/tmp"), {"APPIMAGE_EXTRACT_AND_RUN": "1"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
