"""Android (beta): potpisan APK u posljednje GitHub izdanje, da ga nađu sajt (stalno ime) i aplikacije (android.json).

Pokretanje iz foldera projekta:
    python tools/publish_android.py           → gradi, priprema i postavlja u posljednje izdanje (--clobber)
    python tools/publish_android.py --dry-run → samo gradi i priprema fajlove u Build/android, ništa ne postavlja

Ključ za potpis je %USERPROFILE%/.videodl/android-release.* (nikad u repou); bez njega se ne objavljuje.
Nova verzija = veći `versionCode` u android/app/build.gradle.kts (aplikacije porede versionCode).
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
    subprocess.run([str(gradlew), "assembleRelease", "--console=plain", "-q"], cwd=ANDROID, env=env, check=True)
    return ANDROID / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"


def prepare(apk: Path, code: int, name: str) -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("VideoDownload-android-*.apk*"):
        old.unlink()  # u folderu ostaje samo posljednja verzija
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


def publish(files: list[Path]) -> str:
    tag = subprocess.run(["gh", "release", "view", "--repo", REPO, "--json", "tagName", "--jq", ".tagName"],
                         capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["gh", "release", "upload", tag, *map(str, files), "--repo", REPO, "--clobber"], check=True)
    return tag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="samo gradi i pripremi, bez postavljanja na GitHub")
    args = parser.parse_args()
    code, name = version()
    files = prepare(build(), code, name)
    print(f"Android {name} (versionCode {code}) spreman u {OUT}")
    if not args.dry_run:
        print(f"Postavljeno u izdanje {publish(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
