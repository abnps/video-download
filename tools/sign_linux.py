"""Potpiše Linux AppImage iz nacrta izdanja (release-linux.json + .sig) i doda potpis tom nacrtu.

Korak izdanja poslije posla „Linux paket", na računaru s ključem za potpis izdanja (kao tools/sign_macos.py).
Bez ovog potpisa Linux verzija ne instalira ažuriranje sama, nego otvara link za preuzimanje.
Ključ se samo čita (release_signing.load_key); ništa se ne ispisuje osim imena fajlova.
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_release import ReleaseError  # noqa: E402
from sign_macos import sign_package  # noqa: E402
from videodl import release_signing  # noqa: E402

NAMES = (release_signing.LINUX_MANIFEST_NAME, release_signing.LINUX_SIGNATURE_NAME)


def sign_linux(tag: str) -> None:
    sign_package(tag, "VideoDownload-linux-x86_64-{version}.AppImage", NAMES, "Linux paket")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="tačan tag postojećeg nacrta, npr. v1.1.0")
    args = parser.parse_args()
    try:
        sign_linux(args.tag)
    except (ReleaseError, release_signing.SignatureError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Linux paket nije potpisan: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
