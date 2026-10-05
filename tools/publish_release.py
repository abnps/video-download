"""Provjera kompletnog nacrta izdanja; objava samo uz izričit --publish.

Ne pravi ključeve i ne čita privatne ključeve. Windows manifest provjerava ugrađenim
javnim ključem, a Android APK potpis i identitet javnim certifikatom ranijeg izdanja.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
from videodl import __version__, release_signing
import vlastita  # noqa: E402  (naša preuzimanja se oduzimaju u statistici)

REPO = "abnps/video-download"
# Stalni linkovi na Windows instalere za winget (Ahmed 3.10.2026): glavni repo javno drži samo posljednje
# izdanje, a winget traži link koji nikad ne nestaje.
INSTALLERS_REPO = "abnps/video-download-installers"
# Javni certifikat objavljenog Android 0.2.0 APK-a; nikad privatni ključ.
ANDROID_CERTIFICATE = "83c26828568c1c1fc66be15353650c382a73f9badc5c847b22a7a141ca6b7230"
ANDROID_PACKAGE = "io.github.abnps.videodownload"


def record_own(names, _runner=None) -> None:
    """Naša preuzimanja iz izdanja (provjere, kopije) se upišu u lokalnu statistiku (samo na ovom računaru)."""
    vlastita.record(names)


class ReleaseError(ValueError):
    """Nacrt nije spreman za sigurnu objavu."""


def run(*args: str, **kwargs) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kwargs).stdout.strip()


def android_version() -> tuple[int, str]:
    text = (PROJECT / "android/app/build.gradle.kts").read_text(encoding="utf-8")
    return (int(re.search(r"versionCode\s*=\s*(\d+)", text).group(1)),
            re.search(r'versionName\s*=\s*"([^"]+)"', text).group(1))


def check_tag(tag: str) -> str:
    if tag != f"v{__version__}":
        raise ReleaseError(f"Tag {tag!r} ne odgovara lokalnoj verziji v{__version__}.")
    return __version__


def check_checkout(tag: str) -> None:
    check_tag(tag)
    head = run("git", "rev-parse", "HEAD", cwd=PROJECT)
    tagged = run("gh", "api", f"repos/{REPO}/commits/{tag}", "--jq", ".sha")
    if head != tagged:
        raise ReleaseError("Radna grana nije na commitu taga izdanja. Prebaci se na tačan tag.")
    if run("git", "status", "--porcelain", "--untracked-files=no", cwd=PROJECT):
        raise ReleaseError("Praćeni fajlovi imaju lokalne izmjene; prvo pripremi i označi konačan commit.")


def draft(tag: str) -> dict:
    check_tag(tag)
    # GitHub API po tagu (releases/tags/…) ne vraća nacrte, pa se nacrt traži u spisku izdanja.
    found = json.loads(run("gh", "api", f"repos/{REPO}/releases?per_page=100", "--jq",
                           f'[.[] | select(.tag_name == "{tag}")]'))
    if len(found) != 1:
        raise ReleaseError(f"Za tag {tag} mora postojati tačno jedno izdanje (nađeno: {len(found)}).")
    data = found[0]
    if data.get("tag_name") != tag or data.get("draft") is not True or data.get("prerelease"):
        raise ReleaseError("Cilj mora biti postojeći nacrt konačnog izdanja sa tačnim tagom.")
    return data


def snapshot(data: dict) -> tuple:
    return tuple(sorted((a["id"], a["name"], a["size"], a["updated_at"])
                        for a in data.get("assets", [])))


def required_assets(version: str, android_name: str) -> list[str]:
    windows = f"VideoDownload-Setup-{version}.exe"
    mac = f"VideoDownload-macOS-arm64-{version}.dmg"
    apk = f"VideoDownload-android-{android_name}.apk"
    return [windows, windows + ".sha256", "VideoDownload-Setup.exe", "release.json", "release.json.sig",
            mac, mac + ".sha256", "VideoDownload-macOS-arm64.dmg",
            release_signing.MAC_MANIFEST_NAME, release_signing.MAC_SIGNATURE_NAME,
            apk, apk + ".sha256", "VideoDownload-android.apk", "android.json"]


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def check_checksum(path: Path) -> str:
    digest = sha256(path)
    line = path.with_name(path.name + ".sha256").read_text(encoding="utf-8").strip()
    if not re.fullmatch(re.escape(digest) + r" [ *]" + re.escape(path.name), line):
        raise ReleaseError(f"SHA-256 se ne slaže: {path.name}")
    return digest


def android_tools() -> tuple[Path, Path]:
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    folder = (Path(sdk) if sdk else PROJECT.parent / "Alati/android-sdk") / "build-tools"
    suffix = ".bat" if os.name == "nt" else ""
    aapt_suffix = ".exe" if os.name == "nt" else ""
    for version in sorted(folder.glob("*"), reverse=True):
        signer, aapt = version / f"apksigner{suffix}", version / f"aapt2{aapt_suffix}"
        if signer.is_file() and aapt.is_file():
            return signer, aapt
    raise ReleaseError("Nema Android build-tools (apksigner i aapt2); postavi ANDROID_HOME.")


def check_android_apk(apk: Path, code: int, name: str, tool_paths=None) -> None:
    signer, aapt = tool_paths or android_tools()
    env = dict(os.environ)
    jdk = PROJECT.parent / "Alati/jdk-21"
    if not env.get("JAVA_HOME") and jdk.is_dir():
        env["JAVA_HOME"] = str(jdk)
    signature = run(str(signer), "verify", "--print-certs", str(apk), env=env)
    certificates = set(re.findall(r"certificate SHA-256 digest:\s*([0-9a-fA-F]{64})", signature))
    if {cert.lower() for cert in certificates} != {ANDROID_CERTIFICATE}:
        raise ReleaseError("APK nije potpisan javnim certifikatom prethodnog Android izdanja.")
    package = run(str(aapt), "dump", "badging", str(apk))
    identity = re.search(r"^package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", package, re.M)
    if not identity or identity.groups() != (ANDROID_PACKAGE, str(code), name):
        raise ReleaseError("APK paket ili verzija se ne slažu sa Android opisom izdanja.")


def validate_assets(folder: Path, version: str, code: int, name: str) -> dict:
    for filename in required_assets(version, name):
        path = folder / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise ReleaseError(f"Nedostaje fajl izdanja: {filename}")
    windows = folder / f"VideoDownload-Setup-{version}.exe"
    manifest = release_signing.verify_manifest((folder / "release.json").read_bytes(),
                                               (folder / "release.json.sig").read_text(encoding="ascii"))
    if manifest.get("app") != "Video Download":
        raise ReleaseError("Windows manifest pripada drugom programu.")
    release_signing.check_installer(manifest, version, windows)
    mac = folder / f"VideoDownload-macOS-arm64-{version}.dmg"
    # Mac potpis (tools/sign_macos.py): bez njega Mac verzija ne bi mogla sama preći na ovo izdanje.
    mac_manifest = release_signing.verify_manifest(
        (folder / release_signing.MAC_MANIFEST_NAME).read_bytes(),
        (folder / release_signing.MAC_SIGNATURE_NAME).read_text(encoding="ascii"))
    if mac_manifest.get("app") != "Video Download":
        raise ReleaseError("Mac manifest pripada drugom programu.")
    release_signing.check_installer(mac_manifest, version, mac)
    apk = folder / f"VideoDownload-android-{name}.apk"
    for versioned, stable in ((windows, "VideoDownload-Setup.exe"),
                              (mac, "VideoDownload-macOS-arm64.dmg"), (apk, "VideoDownload-android.apk")):
        digest = check_checksum(versioned)
        if sha256(folder / stable) != digest:
            raise ReleaseError(f"Stalni link vodi na drugačiji fajl: {stable}")
    android = json.loads((folder / "android.json").read_text(encoding="utf-8"))
    expected = {"versionCode": code, "versionName": name, "apk": apk.name,
                "size": apk.stat().st_size, "sha256": sha256(apk)}
    if android != expected:
        raise ReleaseError("android.json se ne slaže sa pripremljenim APK-om i verzijom u kodu.")
    check_android_apk(apk, code, name)
    return android


def check_android_upgrade(current: dict, previous: dict) -> None:
    if current["versionCode"] < previous["versionCode"]:
        raise ReleaseError("Android versionCode je manji od javnog izdanja.")
    if current["versionCode"] == previous["versionCode"] and current["sha256"] != previous["sha256"]:
        raise ReleaseError("Izmijenjen APK mora dobiti veći Android versionCode prije objave.")


def publish_latest(tag: str) -> None:
    """Objavi nacrt kao latest; javno je samo posljednje izdanje (Ahmedova odluka 23.9.2026),
    pa se prethodno vraća u nacrt (ne briše se)."""
    old = run("gh", "release", "view", "--repo", REPO, "--json", "tagName", "--jq", ".tagName").strip()
    run("gh", "release", "edit", tag, "--repo", REPO, "--draft=false", "--latest")
    print(f"Objavljeno: {tag}")
    if old and old != tag:
        run("gh", "release", "edit", old, "--repo", REPO, "--draft=true")
        print(f"Prethodno izdanje {old} je vraćeno u nacrt.")
    copy_to_installers_repo(tag)


def copy_to_installers_repo(tag: str) -> None:
    """Isti Windows instaler (i .sha256) u abnps/video-download-installers, za winget. Novi winget opis paketa
    se i dalje šalje ručno (README: korak winget)."""
    version = tag.removeprefix("v")
    names = (f"VideoDownload-Setup-{version}.exe", f"VideoDownload-Setup-{version}.exe.sha256")
    with tempfile.TemporaryDirectory(prefix="videodl-winget-") as temp:
        try:
            run("gh", "release", "download", tag, "--repo", REPO, "--dir", temp,
                *[arg for name in names for arg in ("--pattern", name)])
        finally:
            record_own(names)  # i pukao pokušaj: GitHub je već izbrojao što je stiglo
        files = [str(Path(temp) / name) for name in names]
        try:
            run("gh", "release", "view", tag, "--repo", INSTALLERS_REPO, "--json", "tagName")
            exists = True
        except subprocess.CalledProcessError:
            exists = False
        if exists:
            # Prekinut raniji pokušaj (0.9.8, 3.10.2026: ostao nacrt bez instalera): dopuni i objavi isto izdanje.
            run("gh", "release", "upload", tag, *files, "--repo", INSTALLERS_REPO, "--clobber")
            run("gh", "release", "edit", tag, "--repo", INSTALLERS_REPO, "--draft=false")
        else:
            run("gh", "release", "create", tag, *files, "--repo", INSTALLERS_REPO,
                "--title", f"Video Download {version} (Windows installer)",
                "--notes", f"Same installer as https://github.com/{REPO}/releases/tag/{tag}")
    print(f"Instaler {version} je i u {INSTALLERS_REPO} (winget).")


def validate_draft(tag: str, *, publish: bool = False) -> None:
    version = check_tag(tag)
    check_checkout(tag)
    before = draft(tag)
    code, name = android_version()
    names = required_assets(version, name)
    uploaded = [a["name"] for a in before.get("assets", []) if a.get("state") == "uploaded"]
    missing = set(names) - set(uploaded)
    if missing or len(uploaded) != len(set(uploaded)):
        raise ReleaseError("Nacrt nema sve završene i jedinstvene fajlove: " + ", ".join(sorted(missing)))
    with tempfile.TemporaryDirectory(prefix="videodl-release-") as temp:
        folder = Path(temp)
        patterns = [arg for name in names for arg in ("--pattern", name)]
        try:
            run("gh", "release", "download", tag, "--repo", REPO, "--dir", str(folder), *patterns)
        finally:
            # I kad skidanje pukne na pola (5.10.2026: dvaput), GitHub je izbrojao fajlove koji su stigli; bez
            # upisa bi naše provjere izgledale kao pravi korisnici (npr. „4 Mac preuzimanja").
            record_own(names)
        current = validate_assets(folder, version, code, name)
        previous_folder = folder / "previous"
        previous_folder.mkdir()
        # Već postoji javno izdanje. Nedostupnost provjere prekida objavu, ne preskače zaštitu.
        try:
            run("gh", "release", "download", "--repo", REPO, "--pattern", "android.json", "--dir", str(previous_folder))
        finally:
            record_own(["android.json"])
        previous = json.loads((previous_folder / "android.json").read_text(encoding="utf-8"))
        check_android_upgrade(current, previous)
    after = draft(tag)
    if before["id"] != after["id"] or snapshot(before) != snapshot(after):
        raise ReleaseError("Nacrt se promijenio tokom provjere. Ponovi provjeru.")
    print(f"{tag}: Windows i Mac potpis i SHA-256, Android potpis, verzije i sva tri stalna linka su ispravni.")
    if publish:
        publish_latest(tag)
    else:
        print("Nacrt ostaje neobjavljen. Objavi ga tek po Ahmedovom nalogu, uz --publish.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="tačan tag postojećeg nacrta, npr. v0.9.8")
    parser.add_argument("--publish", action="store_true", help="poslije uspješne provjere objavi nacrt")
    parser.add_argument("--installers-only", action="store_true",
                        help="samo ponovi kopiju instalera za winget (kad je pala poslije objave)")
    args = parser.parse_args()
    try:
        if args.installers_only:
            check_tag(args.tag)
            copy_to_installers_repo(args.tag)
            return 0
        validate_draft(args.tag, publish=args.publish)
    except (ReleaseError, release_signing.SignatureError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Izdanje nije objavljeno: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
