"""Potpiše Windows instaler iz nacrta izdanja (release.json + .sig) i upiše njegovu veličinu na sajt.

Poslije posla „Windows paket" (GitHub gradi bez privatnog ključa), na računaru s ključem za potpis izdanja:
    python tools/sign_windows.py --tag v1.0.6
Bez ovog potpisa instalirane verzije ne prelaze same na novo izdanje, a objava odbija nacrt. Sajt dobija stvarnu
veličinu instalera; ta izmjena ide u commit izdanja. Ključ se samo čita (release_signing.load_key).
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_release import ReleaseError  # noqa: E402
from sign_macos import sign_package  # noqa: E402
from videodl import release_signing  # noqa: E402

NAMES = (release_signing.MANIFEST_NAME, release_signing.SIGNATURE_NAME)


def sign_windows(tag: str) -> int:
    return sign_package(tag, "VideoDownload-Setup-{version}.exe", NAMES, "Windows paket")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="tačan tag postojećeg nacrta, npr. v1.0.6")
    args = parser.parse_args()
    try:
        size = sign_windows(args.tag)
    except (ReleaseError, release_signing.SignatureError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Windows instaler nije potpisan: {exc}", file=sys.stderr)
        return 1
    import build_site

    if build_site.write_site(round(size / 1024 / 1024)):
        print("Sajt sadrži zabranjene izraze (python tools/build_site.py ih ispisuje).", file=sys.stderr)
        return 1
    print(f"Sajt: veličina instalera {size / 1024 / 1024:.0f} MB; site/ ide u commit izdanja.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
