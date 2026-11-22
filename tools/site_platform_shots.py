"""Snimci za odjeljak sajta „Na svakoj platformi": isti prizor (izmišljeni naslovi, ništa se ne preuzima) kako ga
iscrta svaki sistem.

    python tools/site_platform_shots.py desktop --out <folder>   # na Windowsu, Macu ili Linuxu (pravi sistem)
    python tools/site_platform_shots.py android --out <folder>   # Android ekran (Robolectric, bez telefona)
    python tools/site_platform_shots.py install <folder>...       # WebP u site/assets (platform-*.webp)

Mac i Linux snimci nastaju na GitHubovim Mac i Linux mašinama (.github/workflows/site-shots.yml), jer program na
svakom sistemu izgleda malo drugačije (font, meni na Macu u gornjoj traci). Okvir prozora/telefona crta sajt (CSS).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
LANGS = ("en", "bs", "de", "es", "fr")
THEMES = ("light", "dark")
SITE_ASSETS = PROJECT / "site" / "assets"
DESKTOP_SIZE = (860, 470)  # kao snimak u odjeljku Funkcije; dupla oštrina (QT_SCALE_FACTOR=2)
WEBP_WIDTH = {"windows": 1720, "macos": 1720, "linux": 1720, "android": 786}


def platform_name() -> str:
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def shoot_desktop(out: Path) -> list[Path]:
    name = platform_name()
    os.environ["QT_SCALE_FACTOR"] = "2"
    if name == "macos":
        os.environ["QT_QPA_PLATFORM"] = "cocoa"  # pravi Mac prozor (meni ide u gornju traku sistema)
    elif name == "linux":
        os.environ["QT_QPA_PLATFORM"] = "xcb"  # pravi X11 prozor (u CI-ju pod xvfb-run)
        os.environ["QT_QPA_FONTDIR"] = "/usr/share/fonts"
    sys.path.insert(0, str(PROJECT / "tools"))
    import store_screenshots  # noqa: E402  (privremeni podaci; na Windowsu offscreen s Windows fontovima)
    from PySide6.QtWidgets import QApplication

    store_screenshots.SIZE = DESKTOP_SIZE
    app = QApplication([])
    from videodl import gui, theme

    gui.apply_theme(app)
    app.setStyleSheet(theme.stylesheet())
    window = gui.MainWindow()
    # Savjet o kopiranim linkovima se vidi samo pri prvom pokretanju (svježa CI mašina), kao i na Windows snimku: skriven.
    window.clipboard_notice.hide()
    window.show()
    out.mkdir(parents=True, exist_ok=True)
    shots = []
    for lang in LANGS:
        for mode in THEMES:
            shot = store_screenshots.shoot(window, app, lang, mode, out)
            target = out / f"{name}-{mode}-{lang}.png"
            shot.replace(target)
            shots.append(target)
            print(target)
    window.close()
    return shots


def shoot_android(out: Path) -> None:
    sys.path.insert(0, str(PROJECT / "tools"))
    from site_home import HOME

    out.mkdir(parents=True, exist_ok=True)
    titles = out / "titles.json"
    titles.write_text(json.dumps({lang: list(HOME[lang]["demo_titles"]) for lang in LANGS}, ensure_ascii=False),
                      encoding="utf-8")
    gradle = PROJECT / "android" / ("gradlew.bat" if os.name == "nt" else "gradlew")
    subprocess.run([str(gradle), "-q", ":app:testDebugUnitTest", "--tests",
                    "io.github.abnps.videodownload.SiteScreenshotTest",
                    f"-PsiteShots={out}", f"-PsiteTitles={titles}"], cwd=PROJECT / "android", check=True)
    titles.unlink()


def install(folders: list[Path]) -> None:
    """PNG snimci → site/assets/platform-<sistem>-<tema>-<jezik>.webp (manji od PNG-a, oštri i na telefonu)."""
    from PIL import Image

    count = 0
    for folder in folders:
        for png in sorted(folder.glob("*.png")):
            system = png.stem.split("-")[0]
            if system not in WEBP_WIDTH:
                continue
            image = Image.open(png).convert("RGB")
            width = WEBP_WIDTH[system]
            if image.width != width:
                image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
            target = SITE_ASSETS / f"platform-{png.stem}.webp"
            image.save(target, "WEBP", quality=86, method=6)
            count += 1
            print(target, image.size, target.stat().st_size // 1024, "KB")
    if not count:
        raise SystemExit("Nema PNG snimaka u zadatim folderima.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("desktop", "android"):
        sub.add_parser(cmd).add_argument("--out", type=Path, required=True)
    sub.add_parser("install").add_argument("folders", type=Path, nargs="+")
    args = parser.parse_args()
    if args.cmd == "desktop":
        shoot_desktop(args.out.resolve())
    elif args.cmd == "android":
        shoot_android(args.out.resolve())
    else:
        install(args.folders)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
