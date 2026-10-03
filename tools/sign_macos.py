"""Potpiše Mac .dmg iz nacrta izdanja (release-macos.json + .sig) i doda potpis tom nacrtu.

Korak 4b izdanja (README): poslije posla „Mac paket", na računaru s ključem za potpis izdanja. Bez ovog
potpisa Mac verzija od 0.9.8 ne instalira ažuriranje sama, nego otvara link za preuzimanje (kao ranije).
Ključ se samo čita (release_signing.load_key); ništa se ne ispisuje osim imena fajlova.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_release import REPO, ReleaseError, check_checksum, check_tag, draft, run  # noqa: E402
from videodl import release_signing  # noqa: E402

NAMES = (release_signing.MAC_MANIFEST_NAME, release_signing.MAC_SIGNATURE_NAME)


def sign_mac(tag: str) -> None:
    version = check_tag(tag)
    draft(tag)  # samo nacrt, nikad već objavljeno izdanje
    dmg_name = f"VideoDownload-macOS-arm64-{version}.dmg"
    with tempfile.TemporaryDirectory(prefix="videodl-mac-sign-") as temp:
        folder = Path(temp)
        run("gh", "release", "download", tag, "--repo", REPO, "--dir", str(folder),
            "--pattern", dmg_name, "--pattern", dmg_name + ".sha256")
        dmg = folder / dmg_name
        if not dmg.is_file():
            raise ReleaseError(f"Nacrt nema {dmg_name}; prvo pokreni posao „Mac paket\" (README, korak 4).")
        check_checksum(dmg)
        manifest, signature = release_signing.write_signed_manifest(version, dmg, names=NAMES)
        run("gh", "release", "upload", tag, str(manifest), str(signature), "--repo", REPO, "--clobber")
    print(f"{tag}: {dmg_name} potpisan ({', '.join(NAMES)} dodati nacrtu).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="tačan tag postojećeg nacrta, npr. v0.9.8")
    args = parser.parse_args()
    try:
        sign_mac(args.tag)
    except (ReleaseError, release_signing.SignatureError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Mac paket nije potpisan: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
