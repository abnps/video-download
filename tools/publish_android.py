"""Priprema potpisan Android APK i postavlja ga samo u izričito navedeni nacrt.

    python tools/publish_android.py --dry-run       → samo gradi i priprema lokalne fajlove
    python tools/publish_android.py --tag v0.9.8    → dodaje APK postojećem nacrtu tog taga

Objava cijelog izdanja ide kroz tools/publish_release.py, tek po Ahmedovom nalogu.
Ključ je van repoa; nova Android verzija traži veći versionCode.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from publish_release import check_android_apk, check_checkout, draft

PROJECT = Path(__file__).resolve().parent.parent
ANDROID = PROJECT / "android"
TOOLS = PROJECT.parent / "Alati"  # JDK i Android SDK (vidi 00_plan/android_plan.md)
OUT = PROJECT.parent / "Build" / "android"
REPO = "abnps/video-download"
KEY = Path.home() / ".videodl" / "android-release.properties"


def version() -> tuple[int, str]:
    text = (ANDROID / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    code = int(re.search(r"versionCode\s*=\s*(\d+)", text).group(1))
    name = re.search(r'versionName\s*=\s*"([^"]+)"', text).group(1)
    return code, name


def build() -> Path:
    if not KEY.is_file():
        sys.exit(f"Nema ključa za potpis: {KEY}")
    env = dict(os.environ, JAVA_HOME=str(TOOLS / "jdk-21"))
    gradlew = ANDROID / ("gradlew.bat" if os.name == "nt" else "gradlew")
    subprocess.run([str(gradlew), "lintDebug", "testDebugUnitTest", "assembleRelease", "--console=plain", "-q"], cwd=ANDROID, env=env, check=True)
    return ANDROID / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"


def prepare(apk: Path, code: int, name: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    versioned = OUT / f"VideoDownload-android-{name}.apk"
    shutil.copyfile(apk, versioned)
    stable = OUT / "VideoDownload-android.apk"  # stalni link na sajtu
    shutil.copyfile(apk, stable)
    digest = hashlib.sha256(versioned.read_bytes()).hexdigest()
    checksum = OUT / f"{versioned.name}.sha256"
    checksum.write_text(f"{digest}  {versioned.name}\n", encoding="utf-8")
    manifest = OUT / "android.json"
    manifest.write_text(json.dumps({"versionCode": code, "versionName": name, "apk": versioned.name,
                                    "sha256": digest, "size": versioned.stat().st_size}) + "\n", encoding="utf-8")
    return [versioned, checksum, stable, manifest]


def publish(files: list[Path], tag: str) -> str:
    check_checkout(tag)
    draft(tag)
    subprocess.run(["gh", "release", "upload", tag, *map(str, files), "--repo", REPO, "--clobber"], check=True)
    return tag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="samo gradi i pripremi, bez postavljanja na GitHub")
    parser.add_argument("--tag", help="tačan tag postojećeg nacrta; obavezno osim uz --dry-run")
    args = parser.parse_args()
    if not args.dry_run:
        if not args.tag:
            parser.error("--tag je obavezan; APK se više ne postavlja u implicitno posljednje izdanje")
        check_checkout(args.tag)
        draft(args.tag)
    code, name = version()
    apk = build()
    check_android_apk(apk, code, name)
    files = prepare(apk, code, name)
    print(f"Android {name} (versionCode {code}) spreman u {OUT}")
    if not args.dry_run:
        print(f"Postavljeno u izdanje {publish(files, args.tag)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
