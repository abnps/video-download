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
from publish_release import REPO, ReleaseError, check_checksum, check_tag, draft, record_own, run  # noqa: E402
from videodl import release_signing  # noqa: E402

NAMES = (release_signing.MAC_MANIFEST_NAME, release_signing.MAC_SIGNATURE_NAME)


def sign_package(tag: str, package_name: str, names: tuple[str, str], job: str) -> int:
    """Preuzme paket iz nacrta, provjeri .sha256, potpiše opis i doda ga nacrtu (isto za Mac, Linux i Windows).
    Vraća veličinu paketa u bajtima."""
    version = check_tag(tag)
    draft(tag)  # samo nacrt, nikad već objavljeno izdanje
    package_name = package_name.format(version=version)
    with tempfile.TemporaryDirectory(prefix="videodl-sign-") as temp:
        folder = Path(temp)
        run("gh", "release", "download", tag, "--repo", REPO, "--dir", str(folder),
            "--pattern", package_name, "--pattern", package_name + ".sha256")
        record_own([package_name], run)
        package = folder / package_name
        if not package.is_file():
            raise ReleaseError(f"Nacrt nema {package_name}; prvo pokreni posao „{job}\" (README).")
        check_checksum(package)
        size = package.stat().st_size
        manifest, signature = release_signing.write_signed_manifest(version, package, names=names)
        run("gh", "release", "upload", tag, str(manifest), str(signature), "--repo", REPO, "--clobber")
    print(f"{tag}: {package_name} potpisan ({', '.join(names)} dodati nacrtu).")
    return size


def sign_mac(tag: str) -> None:
    sign_package(tag, "VideoDownload-macOS-arm64-{version}.dmg", NAMES, "Mac paket")


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
