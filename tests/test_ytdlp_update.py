"""Ažuriranje samog yt-dlp-a: čitanje sa PyPI-ja, SHA-256, raspakivanje i aktivacija."""

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from videodl import ytdlp_update

PYPI = "https://pypi.org/pypi/yt-dlp/json"
WHEEL = "https://files.pythonhosted.org/packages/yt_dlp-2099.1.1-py3-none-any.whl"


def make_wheel(version: str, extra: dict | None = None) -> bytes:
    """Najmanji wheel oblika kakav PyPI ima za yt-dlp."""
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("yt_dlp/__init__.py", "from .version import __version__\n")
        archive.writestr("yt_dlp/version.py", f'__version__ = "{version}"\n')
        archive.writestr(f"yt_dlp-{version}.dist-info/METADATA", "Name: yt-dlp\n")
        for name, text in (extra or {}).items():
            archive.writestr(name, text)
    return data.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class YtdlpUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"VIDEODL_DATA_DIR": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.wheel = make_wheel("2099.1.1")
        self.digest = hashlib.sha256(self.wheel).hexdigest()

    def pypi_json(self, version="2099.1.1", digest=None):
        return json.dumps({
            "info": {"version": version},
            "urls": [
                {"filename": "yt_dlp-2099.1.1.tar.gz", "url": "https://x/tar.gz", "packagetype": "sdist"},
                {"filename": f"yt_dlp-{version}-py3-none-any.whl", "url": WHEEL,
                 "digests": {"sha256": digest or self.digest}, "size": len(self.wheel)},
            ],
        }).encode("utf-8")

    def opener(self, pages):
        def open_url(request, timeout):
            return FakeResponse(pages[request.full_url])
        return open_url

    def test_fetch_and_install_puts_version_in_user_folder(self):
        pages = {PYPI: self.pypi_json(), WHEEL: self.wheel}
        with mock.patch.object(ytdlp_update, "active_version", return_value="2026.8.19"):
            release = ytdlp_update.fetch_latest(opener=self.opener(pages))
            self.assertEqual((release.version, release.sha256), ("2099.1.1", self.digest))
            progress = []
            version = ytdlp_update.install(release, on_progress=lambda d, t: progress.append((d, t)),
                                           opener=self.opener(pages))
        self.assertEqual(version, "2099.1.1")
        self.assertEqual(ytdlp_update.installed_versions(), ["2099.1.1"])
        self.assertEqual(progress[-1], (len(self.wheel), len(self.wheel)))
        self.assertFalse(list(ytdlp_update.store_dir().glob("*.whl")))
        self.assertFalse(list(ytdlp_update.store_dir().glob("*.novi")))

    def test_newest_or_equal_version_is_not_downloaded_again(self):
        pages = {PYPI: self.pypi_json(version="2026.8.19")}
        with mock.patch.object(ytdlp_update, "active_version", return_value="2026.8.19"):
            self.assertIsNone(ytdlp_update.fetch_latest(opener=self.opener(pages)))

        pages = {PYPI: self.pypi_json(), WHEEL: self.wheel}
        with mock.patch.object(ytdlp_update, "active_version", return_value="2026.8.19"):
            ytdlp_update.install(ytdlp_update.fetch_latest(opener=self.opener(pages)), opener=self.opener(pages))
            # Preuzeto čeka sljedeće pokretanje: isti paket se ne preuzima ponovo.
            self.assertIsNone(ytdlp_update.fetch_latest(opener=self.opener(pages)))
            self.assertEqual(ytdlp_update.pending_version(), "2099.1.1")

    def test_wrong_checksum_leaves_nothing_behind(self):
        pages = {PYPI: self.pypi_json(digest="0" * 64), WHEEL: self.wheel}
        with mock.patch.object(ytdlp_update, "active_version", return_value="2026.8.19"):
            release = ytdlp_update.fetch_latest(opener=self.opener(pages))
            with self.assertRaises(ytdlp_update.YtdlpUpdateError) as caught:
                ytdlp_update.install(release, opener=self.opener(pages))
        self.assertEqual(caught.exception.key, "ytdlp.checksum")
        self.assertEqual(ytdlp_update.installed_versions(), [])

    def test_files_outside_the_package_are_not_extracted(self):
        wheel = make_wheel("2099.1.1", {"../pobjegao.txt": "x", "drugi_paket/zlo.py": "x"})
        pages = {PYPI: self.pypi_json(digest=hashlib.sha256(wheel).hexdigest()), WHEEL: wheel}
        with mock.patch.object(ytdlp_update, "active_version", return_value="2026.8.19"):
            ytdlp_update.install(ytdlp_update.fetch_latest(opener=self.opener(pages)), opener=self.opener(pages))
        folder = ytdlp_update.store_dir() / "2099.1.1"
        self.assertEqual(sorted(path.name for path in folder.iterdir()), ["yt_dlp"])
        self.assertFalse((ytdlp_update.store_dir() / "pobjegao.txt").exists())

    def test_old_versions_are_removed(self):
        for version in ("2098.1.1", "2099.1.1"):
            target = ytdlp_update.store_dir() / version / "yt_dlp"
            target.mkdir(parents=True)
            (target / "version.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
        ytdlp_update.prune(keep=("2099.1.1",))
        self.assertEqual(ytdlp_update.installed_versions(), ["2099.1.1"])

    def test_insecure_url_is_refused(self):
        with self.assertRaises(ytdlp_update.YtdlpUpdateError):
            ytdlp_update.fetch_latest(url="http://pypi.example/json", opener=self.opener({}))


class ActivationTest(unittest.TestCase):
    """Aktivacija se provjerava u zasebnom procesu: uvoz yt_dlp-a se u ovom više ne može poništiti."""

    def run_child(self, store: Path, expected: str) -> str:
        code = textwrap.dedent(f"""
            import os, sys
            os.environ["VIDEODL_DATA_DIR"] = {str(store)!r}
            sys.path.insert(0, {str(Path.cwd())!r})
            from videodl.ytdlp_update import activate, active_version
            activate()
            print(active_version())
        """)
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_downloaded_version_wins_and_broken_one_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "yt-dlp"
            package = store / "2099.1.1" / "yt_dlp"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("from .version import __version__\n", encoding="utf-8")
            (package / "version.py").write_text('__version__ = "2099.1.1"\n', encoding="utf-8")
            self.assertEqual(self.run_child(Path(tmp), "2099.1.1"), "2099.1.1")

            # Neispravan paket: aplikacija se vraća na yt-dlp iz instalacije, a folder se briše.
            (package / "version.py").write_text("raise RuntimeError('pokvaren')\n", encoding="utf-8")
            import yt_dlp

            self.assertEqual(self.run_child(Path(tmp), yt_dlp.version.__version__), yt_dlp.version.__version__)
            self.assertFalse((store / "2099.1.1").exists())


class JobTest(unittest.TestCase):
    """Posao u pozadinskoj niti javlja rezultat u glavnu nit (prozor ne smije stati na mreži)."""

    def test_job_reports_version_and_error(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        from videodl.gui import YtdlpUpdateJob

        app = QApplication.instance() or QApplication([])
        release = ytdlp_update.YtdlpRelease("2099.1.1", WHEEL, "a" * 64, 10)
        for fetch, install, expected in (
                (lambda: release, lambda r: r.version, ("2099.1.1", None)),
                (lambda: None, lambda r: self.fail("ne smije se instalirati"), (None, None)),
                (lambda: (_ for _ in ()).throw(ytdlp_update.YtdlpUpdateError("x", key="ytdlp.failed")), None, (None, "ytdlp.failed")),
        ):
            with self.subTest(expected=expected):
                results = []
                job = YtdlpUpdateJob(manual=True, fetch=fetch, install=install)
                job.finished.connect(lambda version, error, manual: results.append((version, error)))
                job.start()
                for _ in range(300):
                    app.processEvents()
                    if results:
                        break
                    threading.Event().wait(0.01)
                self.assertTrue(results)
                version, error = results[0]
                self.assertEqual((version, getattr(error, "key", None)), expected)


if __name__ == "__main__":
    unittest.main()
