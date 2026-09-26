"""Mac (Apple Silicon) paket: PyInstaller .app → alati i dodatak → provjere → .dmg. Bez Appleovog potpisa (beta).

Pokreće se na Macu (GitHub Actions macos runner ili pravi Mac), iz foldera projekta:
    python tools/build_macos.py
Izlaz: <build folder>/macos/VideoDownload-macOS-arm64-<verzija>.dmg (+ .sha256). Build folder je isti kao za
Windows (VIDEODL_BUILD_DIR, folder „Build" pored projekta ili zamjena).

Alati (ffmpeg, ffprobe, node) se preuzimaju sa adresa iz tools/build-lock.json („macos_tools") i provjeravaju po
SHA-256 prije raspakivanja. Paket se potpisuje samo lokalno („ad-hoc"): Apple Silicon bez toga ne pokreće program,
a Appleov Developer ID potpis i notarizacija dolaze kasnije, kao jedan dodatni korak prije .dmg-a.
"""

import hashlib
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tools"))

import build_release  # noqa: E402  (zajednički dijelovi: lock, testovi, licence)
from videodl import __version__  # noqa: E402

APP_NAME = "Video Download"
BUNDLE_ID = "io.github.abnps.videodownload"
MIN_MACOS = "12.0"
WORK = build_release.BUILD / "macos"
STAGE = WORK / "stage"  # sve što ide u paket, prije PyInstallera
DIST = WORK / "dist"
APP = DIST / f"{APP_NAME}.app"
DMG = WORK / f"VideoDownload-macOS-arm64-{__version__}.dmg"
TOOL_FILES = {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe", "node": "bin/node"}  # ime → putanja u arhivi


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("›", " ".join(str(part) for part in command)[:160], flush=True)
    return subprocess.run(command, check=True, **kwargs)


def check_environment(lock: dict) -> None:
    import importlib.metadata

    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise SystemExit("Mac paket se pravi na Macu sa Apple Silicon procesorom (arm64).")
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


def fetch_tools(lock: dict) -> Path:
    """Preuzme arhive iz lock-a, provjeri SHA-256 i raspakuje samo potrebne izvršne fajlove u STAGE/tools."""
    downloads = WORK / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    tools = STAGE / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    for name, inside in TOOL_FILES.items():
        spec = lock["macos_tools"][name]
        archive = downloads / f"{name}-{spec['url'].rsplit('/', 1)[-1]}"
        if not archive.is_file() or build_release.sha256_file(archive) != spec["sha256"]:
            print(f"› preuzimam {name}: {spec['url']}", flush=True)
            request = urllib.request.Request(spec["url"], headers={"User-Agent": "VideoDownload-build"})
            with urllib.request.urlopen(request, timeout=300) as response, open(archive, "wb") as file:
                shutil.copyfileobj(response, file)
        digest = build_release.sha256_file(archive)
        if digest != spec["sha256"]:
            raise SystemExit(f"{name}: SHA-256 {digest} se ne slaže s lock-om ({spec['sha256']}).")
        target = tools / name
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as bundle:
                member = next(item for item in bundle.namelist() if item.rsplit("/", 1)[-1] == name)
                target.write_bytes(bundle.read(member))
        else:
            with tarfile.open(archive) as bundle:
                member = next(item for item in bundle.getmembers() if item.name.endswith("/" + inside))
                target.write_bytes(bundle.extractfile(member).read())
        target.chmod(0o755)
    return tools


def make_icns(target: Path) -> None:
    """Ikona istom funkcijom kao za Windows i dodatak; iconutil pravi .icns iz PNG seta."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    from make_icons import draw

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
    iconset = WORK / "icon.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir(parents=True)
    for size in (16, 32, 128, 256, 512):
        draw(size).save(str(iconset / f"icon_{size}x{size}.png"), "PNG")
        draw(size * 2).save(str(iconset / f"icon_{size}x{size}@2x.png"), "PNG")
    run(["iconutil", "-c", "icns", str(iconset), "-o", str(target)])


def write_manifest(lock: dict, tools: Path) -> None:
    import importlib.metadata

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT, capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = ""
    manifest = {
        "app": __version__, "platform": "macos-arm64", "commit": commit, "python": sys.version.split()[0],
        "packages": {name: importlib.metadata.version(name) for name in lock["packages"]},
        "tools": {name: {"version": spec["version"], "source": spec["source"], "archive_sha256": spec["sha256"],
                         "sha256": build_release.sha256_file(tools / name)}
                  for name, spec in lock["macos_tools"].items() if name != "comment"},
    }
    (STAGE / "BUILD-MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def set_info_plist() -> None:
    path = APP / "Contents" / "Info.plist"
    with open(path, "rb") as file:
        info = plistlib.load(file)
    info.update({
        "CFBundleDisplayName": APP_NAME, "CFBundleName": APP_NAME, "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleShortVersionString": __version__, "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": MIN_MACOS, "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHumanReadableCopyright": "© 2026 Video Download",
    })
    with open(path, "wb") as file:
        plistlib.dump(info, file)


def check_app() -> None:
    """Self-test spakovane aplikacije i host način (browser pokreće isti program)."""
    executable = APP / "Contents" / "MacOS" / APP_NAME
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    report = WORK / "self-test.json"
    report.unlink(missing_ok=True)
    result = subprocess.run([str(executable), "--self-test", str(report)], timeout=180, env=env)
    checks = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
    print("self-test:", json.dumps(checks, ensure_ascii=False), flush=True)
    bundled = str(APP)
    if result.returncode != 0 or not checks.get("ok") or checks.get("version") != __version__:
        raise SystemExit("Self-test spakovane aplikacije nije prošao.")
    for tool in ("ffmpeg", "ffprobe", "node"):
        if not str(checks.get(tool) or "").startswith(bundled):
            raise SystemExit(f"{tool} nije iz paketa nego {checks.get(tool)}")

    body = json.dumps({"action": "status"}).encode("utf-8")
    message = len(body).to_bytes(4, "little") + body
    host = subprocess.run([str(executable), "chrome-extension://jfgcekfmjipklibljeacchccmebppklp/"], input=message,
                          capture_output=True, timeout=60, env=env)
    reply = json.loads(host.stdout[4:].decode("utf-8")) if len(host.stdout) > 4 else {}
    print("host:", reply, flush=True)
    if not reply.get("ok"):
        raise SystemExit(f"Host način ne odgovara: {host.stdout[:200]!r} {host.stderr[-400:]!r}")


def make_dmg() -> None:
    root = WORK / "dmg"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    run(["ditto", str(APP), str(root / APP.name)])  # ditto čuva potpis i atribute paketa
    (root / "Applications").symlink_to("/Applications")
    DMG.unlink(missing_ok=True)
    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", str(root), "-ov", "-format", "UDZO", str(DMG)])
    digest = hashlib.sha256(DMG.read_bytes()).hexdigest()
    Path(f"{DMG}.sha256").write_text(f"{digest}  {DMG.name}\n", encoding="ascii")
    print(f"DMG: {DMG} ({DMG.stat().st_size / 1024 / 1024:.0f} MB)\nSHA-256: {digest}", flush=True)


def main() -> int:
    lock = build_release.load_lock()
    check_environment(lock)
    build_release.run_checks()
    for folder in (STAGE, DIST, WORK / "work"):
        shutil.rmtree(folder, ignore_errors=True)
    STAGE.mkdir(parents=True)

    tools = fetch_tools(lock)
    shutil.copytree(PROJECT / "extension", STAGE / "extension", ignore=shutil.ignore_patterns("package.json"))
    build_release.write_legal(STAGE, installer_documents=False)
    write_manifest(lock, tools)
    icon = WORK / "icon.icns"
    make_icns(icon)

    separator = os.pathsep
    args = ["--windowed", "--name", APP_NAME, "--icon", str(icon), "--osx-bundle-identifier", BUNDLE_ID,
            "--target-architecture", "arm64",
            "--add-data", f"{PROJECT / 'videodl' / 'assets'}{separator}videodl/assets",
            "--add-data", f"{STAGE / 'extension'}{separator}extension",
            "--add-data", f"{STAGE / 'licenses'}{separator}licenses",
            "--add-data", f"{STAGE / 'THIRD-PARTY-NOTICES.txt'}{separator}.",
            "--add-data", f"{STAGE / 'BUILD-MANIFEST.json'}{separator}.",
            "--collect-data", "yt_dlp_ejs", "--collect-all", "curl_cffi"]
    for name in TOOL_FILES:
        args += ["--add-binary", f"{tools / name}{separator}tools"]
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
         "--distpath", str(DIST), "--workpath", str(WORK / "work"), "--specpath", str(WORK),
         *args, str(PROJECT / "pokreni.pyw")], cwd=PROJECT)

    set_info_plist()
    # Poslije izmjene Info.plist-a paket se mora ponovo potpisati (ad-hoc), inače ga macOS smatra oštećenim.
    run(["codesign", "--force", "--deep", "--sign", "-", str(APP)])
    run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(APP)])
    check_app()
    make_dmg()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
