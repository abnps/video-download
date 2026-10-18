"""Snimci ekrana programa za Microsoft Store (najmanje 1366×768), na 5 jezika, svijetla i tamna tema.

    python tools/store_screenshots.py [--out <folder>]

Program se pokreće nevidljivo (offscreen) s privremenim podacima i izmišljenim, neutralnim primjerima
(isti naslovi kao demo na sajtu, bez imena stvarnih sajtova): ništa se ne preuzima i ne dira korisnikova
podešavanja.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tools"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")  # offscreen inače nema fontova (kvadratići)
os.environ["VIDEODL_DATA_DIR"] = tempfile.mkdtemp(prefix="videodl-snimci-")

from PySide6.QtWidgets import QApplication  # noqa: E402

from site_home import HOME  # noqa: E402  (naslovi primjera, već prevedeni za sajt)
from videodl import i18n  # noqa: E402
from videodl.download import Progress  # noqa: E402
from videodl.jobs import DownloadQueue, ItemStatus  # noqa: E402

SIZE = (1366, 768)
DURATIONS = (754, 3851, 2986, 1534)


def shoot(window, app, lang: str, theme: str, out: Path) -> Path:
    import videodl.gui as gui

    i18n.set_language(lang)
    window.set_theme(theme, save=False)
    window.retranslate_ui()
    for row in list(window._rows.values()):
        row.setParent(None)
    window._rows.clear()
    window._queue = DownloadQueue()  # aktivne stavke se ne daju ukloniti, pa nova prazna lista za svaki snimak
    titles = HOME[lang]["demo_titles"]
    states = (ItemStatus.ACTIVE, ItemStatus.ACTIVE, ItemStatus.DONE, ItemStatus.DONE)
    presets = ("best", "1080p", "mp3", "car")
    for title, duration, status, preset in zip(titles, DURATIONS, states, presets):
        item = window._queue.add(f"https://example.test/video/{abs(hash(title)) % 10**6}", title, preset,
                                 window._output_dir, None, duration=duration)
        item.status = status
        window._append_row(item)
        window._refresh_row(item)
        if status == ItemStatus.ACTIVE:
            fraction, speed, eta = (0.62, 6.4e6, 9) if preset == "best" else (0.27, 2.1e6, 74)
            progress = Progress("download", fraction, speed, eta, "progress.video")
            window._rows[item.id].show_progress(gui.format_progress(progress), fraction)
    window.preset_combo.setCurrentIndex(window.preset_combo.findData("best"))
    window._running = True  # dugme „Stop", kao dok preuzimanje traje
    window._update_controls()
    window.resize(*SIZE)
    app.processEvents()
    path = out / f"store-{lang}-{theme}.png"
    window.grab().save(str(path))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=PROJECT.parent / "Build" / "store-snimci")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    from videodl import gui, theme

    app.setStyleSheet(theme.stylesheet())
    window = gui.MainWindow()
    window.show()
    for lang in ("en", "bs", "de", "es", "fr"):
        for name in ("light", "dark"):
            print(shoot(window, app, lang, name, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
