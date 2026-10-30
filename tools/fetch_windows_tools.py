"""Zaključani ffmpeg (gyan.dev essentials) i Node za Windows build na GitHubu (posao „Windows paket").

    python tools/fetch_windows_tools.py
Preuzme arhive iz tools/build-lock.json („windows_archives"), provjeri SHA-256 i raspakuje ih u build folder:
ffmpeg u <Build>/ffmpeg/x-ffmpeg-<verzija>-essentials_build (tu ga build_release.py traži), Node u <Build>/node.
Na GitHubu upisuje te foldere u $GITHUB_PATH (prvo Node, pa ffmpeg za testove). Lokalno nije potrebno.
"""

import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_macos  # noqa: E402  (preuzimanje po lock-u, provjera SHA-256)
import build_release  # noqa: E402


def main() -> int:
    lock = build_release.load_lock()["windows_archives"]
    downloads = build_release.BUILD / "downloads"
    ffmpeg_zip = build_macos.download("ffmpeg", lock["ffmpeg"], downloads)
    # npr. .../ffmpeg-9.0.2-essentials_build.zip → <Build>/ffmpeg/x-ffmpeg-9.0.2-essentials_build
    ffmpeg_root = build_release.BUILD / "ffmpeg" / ("x-" + lock["ffmpeg"]["url"].rsplit("/", 1)[-1].removesuffix(".zip"))
    with zipfile.ZipFile(ffmpeg_zip) as archive:
        archive.extractall(ffmpeg_root)
    node_zip = build_macos.download("node", lock["node"], downloads)
    node_root = build_release.BUILD / "node"
    with zipfile.ZipFile(node_zip) as archive:
        archive.extractall(node_root)
    node_dir = next(node_root.glob("node-*-win-x64"))
    ffmpeg_bin = next(ffmpeg_root.glob("*/bin"))
    print(f"Node: {node_dir}\nffmpeg: {ffmpeg_bin}")
    github_path = os.environ.get("GITHUB_PATH")
    if github_path:
        with open(github_path, "a", encoding="utf-8") as file:
            file.write(f"{node_dir}\n{ffmpeg_bin}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
