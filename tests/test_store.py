"""Red i istorija na disku: šta se pamti, šta se nikad ne upisuje i šta preživi oštećen fajl."""

import json
import tempfile
import unittest
from pathlib import Path

from videodl import store
from videodl.jobs import DownloadQueue, ItemStatus


class QueueFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = store.queue_path(Path(self.tmp.name))
        self.queue = DownloadQueue()

    def test_waiting_and_failed_are_kept_finished_are_not(self):
        waiting = self.queue.add("https://v/1", "Prvi", "mp3", r"C:\Videi", "Lista")
        active = self.queue.add("https://v/2", "Drugi", "best", r"C:\Videi")
        active.status = ItemStatus.ACTIVE
        failed = self.queue.add("https://v/3", "Treći", "best", r"C:\Videi")
        failed.status = ItemStatus.FAILED
        done = self.queue.add("https://v/4", "Gotov", "best", r"C:\Videi")
        done.status = ItemStatus.DONE

        store.save_queue(self.queue.items(), self.path)
        rows = store.load_queue(self.path)
        self.assertEqual([row["url"] for row in rows], [waiting.url, active.url, failed.url])
        # Prekinuto pri zatvaranju se vraća kao „čeka", bez stare poruke o grešci.
        self.assertEqual({row["status"] for row in rows}, {str(ItemStatus.WAITING)})
        self.assertEqual(rows[0]["preset_key"], "mp3")
        self.assertEqual(rows[0]["subfolder"], "Lista")

    def test_cookies_are_never_written(self):
        item = self.queue.add("https://v/1", "Iza prijave", "best", r"C:\Videi",
                              http_headers={"Referer": "https://v/"},
                              cookies=({"name": "sessionid", "value": "TAJNA"},))
        item.status = ItemStatus.WAITING
        store.save_queue(self.queue.items(), self.path)
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("TAJNA", text)
        self.assertNotIn("sessionid", text)
        self.assertIn("Referer", text)

    def test_broken_or_missing_file_gives_empty_queue(self):
        self.assertEqual(store.load_queue(self.path), [])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{nije json", encoding="utf-8")
        self.assertEqual(store.load_queue(self.path), [])
        self.path.write_text(json.dumps({"items": [{"bez": "linka"}, "smeće"]}), encoding="utf-8")
        self.assertEqual(store.load_queue(self.path), [])

    def test_temporary_file_is_not_left_behind(self):
        store.save_queue(self.queue.items(), self.path)
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["queue.json"])


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = store.history_path(Path(self.tmp.name))
        self.queue = DownloadQueue()

    def add(self, url, title, filepath):
        item = self.queue.add(url, title, "best", self.tmp.name)
        item.filepath = filepath
        item.status = ItemStatus.DONE
        return item

    def test_newest_first_and_same_file_is_not_repeated(self):
        first = self.add("https://v/1", "Prvi", str(Path(self.tmp.name) / "prvi.mp4"))
        second = self.add("https://v/2", "Drugi", str(Path(self.tmp.name) / "drugi.mp4"))
        store.append_history(first, self.path, size=100, now=1000)
        store.append_history(second, self.path, size=200, now=2000)
        store.append_history(first, self.path, size=100, now=3000)  # ponovo preuzet isti fajl

        entries = store.load_history(self.path)
        self.assertEqual([entry.title for entry in entries], ["Prvi", "Drugi"])
        self.assertEqual((entries[0].finished_at, entries[0].size), (3000, 100))

    def test_missing_file_is_recognised_and_list_can_be_cleared(self):
        item = self.add("https://v/1", "Prvi", str(Path(self.tmp.name) / "nema.mp4"))
        store.append_history(item, self.path, size=1)
        self.assertFalse(store.load_history(self.path)[0].exists)

        Path(self.tmp.name, "ima.mp4").write_bytes(b"x")
        item.filepath = str(Path(self.tmp.name) / "ima.mp4")
        store.append_history(item, self.path, size=1)
        self.assertTrue(store.load_history(self.path)[0].exists)

        store.clear_history(self.path)
        self.assertEqual(store.load_history(self.path), [])

    def test_list_does_not_grow_without_end(self):
        item = self.add("https://v/1", "Prvi", "")
        for index in range(store.MAX_HISTORY + 10):
            item.filepath = f"C:\\\\v\\\\{index}.mp4"
            store.append_history(item, self.path, size=index, now=index)
        self.assertEqual(len(store.load_history(self.path)), store.MAX_HISTORY)


if __name__ == "__main__":
    unittest.main()


class DamagedDataTest(unittest.TestCase):
    """Loši podaci ne obaraju program, ispravni zapisi se čuvaju, a oštećen fajl se ne gubi."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def write(self, path, data):
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def test_history_with_wrong_types_keeps_the_good_entries(self):
        path = store.history_path(self.folder)
        self.write(path, {"entries": [
            {"url": "https://v/1", "title": "Dobar", "filepath": "C:/a.mp4", "size": 10, "finished_at": 5},
            {"url": "https://v/2", "title": 7, "size": "bad", "finished_at": "juče"},
            {"url": 3, "title": "Bez ispravnog linka"},
            "smeće", None,
        ]})
        entries = store.load_history(path)
        self.assertEqual([(e.title, e.size) for e in entries], [("Dobar", 10), ("", 0)])
        for bad in ({"entries": 7}, {"entries": {"a": 1}}, [1, 2], "nije json"):
            with self.subTest(bad=bad):
                self.write(path, bad)
                self.assertEqual(store.load_history(path), [])

    def test_queue_with_wrong_types_keeps_the_good_fields(self):
        path = store.queue_path(self.folder)
        self.write(path, {"items": [
            {"url": "https://v/1", "title": ["x"], "duration": "dugo", "section": ["a", 5],
             "http_headers": {"Referer": "https://v/", "X": 5}, "custom_format": "da"},
            {"url": "https://v/2", "duration": 61, "section": [2, 7], "subfolder": None},
        ]})
        first, second = store.load_queue(path)
        self.assertEqual(first, {"url": "https://v/1", "http_headers": {"Referer": "https://v/"}})
        self.assertEqual((second["duration"], second["section"], second["subfolder"]), (61.0, [2.0, 7.0], None))
        self.write(path, {"items": 7})
        self.assertEqual(store.load_queue(path), [])

    def test_damaged_file_is_kept_aside_before_being_replaced(self):
        path = store.history_path(self.folder)
        self.write(path, "{oštećen json")
        self.assertEqual(store.load_history(path), [])
        kept = path.with_name(path.name + ".ostecen")
        self.assertEqual(kept.read_text(encoding="utf-8"), "{oštećen json")

    def test_failed_write_is_reported_not_hidden(self):
        blocked = self.folder / "fajl-umjesto-foldera"
        blocked.write_text("x", encoding="utf-8")  # folder podataka se ne može napraviti
        item = DownloadQueue().add("https://v/1", "Video", "best", "C:/v")
        self.assertFalse(store.append_history(item, blocked / "history.json", 1))
        self.assertFalse(store.save_queue([item], blocked / "queue.json"))
        self.assertTrue(store.save_queue([item], store.queue_path(self.folder)))
