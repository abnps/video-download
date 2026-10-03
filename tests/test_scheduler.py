"""Raspored preuzimanja bez prozora (videodl/scheduler.py): ko kreće sljedeći i ko čeka."""

import unittest

from videodl import scheduler
from videodl.jobs import DownloadQueue, ItemStatus
from videodl.presets import DEFAULT_NAME_TEMPLATE


class PickNextTest(unittest.TestCase):
    def setUp(self):
        self.queue = DownloadQueue()
        self.a = self.queue.add("https://v/a", "A", "best", "C:/x", video_id="a")
        self.b = self.queue.add("https://v/b", "B", "best", "C:/x", video_id="b")
        self.c = self.queue.add("https://v/c", "C", "best", "C:/x", video_id="c")

    def pick(self, manual=(), active=(), auto=False, retry=lambda item: False):
        return scheduler.pick_next(list(manual), self.queue.items(), self.queue.get, list(active),
                                   DEFAULT_NAME_TEMPLATE, auto, retry)

    def test_manual_first_in_order(self):
        item, rest = self.pick(manual=[self.c.id, self.a.id], auto=True)
        self.assertIs(item, self.c)
        self.assertEqual(rest, [self.a.id])

    def test_nothing_without_manual_or_auto(self):
        self.assertEqual(self.pick(), (None, []))

    def test_auto_takes_first_waiting(self):
        self.a.status = ItemStatus.DONE
        item, _ = self.pick(auto=True)
        self.assertIs(item, self.b)

    def test_invalid_manual_entries_are_dropped(self):
        self.a.status = ItemStatus.FAILED
        self.b.adult = True  # 18+ bez potvrde čeka
        item, rest = self.pick(manual=[999, self.a.id, self.b.id, self.c.id])
        self.assertIs(item, self.c)
        self.assertEqual(rest, [])

    def test_adult_with_confirmation_may_start(self):
        self.b.adult, self.b.adult_ok = True, True
        self.assertIs(self.pick(manual=[self.b.id])[0], self.b)

    def test_retry_deadline_waits(self):
        item, _ = self.pick(manual=[self.a.id], auto=True, retry=lambda candidate: candidate is self.a)
        self.assertIs(item, self.b)

    def test_same_output_is_postponed_and_kept_first(self):
        twin = self.queue.add("https://kratko/a", "A", "best", "C:/x", video_id="a")  # isti video, drugi link
        running = self.queue.add("https://v/a", "A", "best", "C:/x", video_id="a")
        running.status = ItemStatus.ACTIVE
        item, rest = self.pick(manual=[twin.id, self.b.id, self.c.id], active=[running])
        self.assertIs(item, self.b)
        self.assertEqual(rest, [twin.id, self.c.id])  # odloženi ostaje PRVI: kreće čim isti posao završi

    def test_auto_skips_busy_output(self):
        running = self.queue.add("https://v/a2", "A", "best", "C:/x", video_id="a")
        running.status = ItemStatus.ACTIVE
        item, _ = self.pick(active=[running], auto=True)
        self.assertIs(item, self.b)  # „a" bi pisao isti fajl kao posao u toku


class OutputKeyTest(unittest.TestCase):
    def test_different_quality_or_folder_is_a_different_file(self):
        queue = DownloadQueue()
        one = queue.add("https://v/a", "A", "best", "C:/x", video_id="a")
        other_preset = queue.add("https://v/a", "A", "mp3", "C:/x", video_id="a")
        other_folder = queue.add("https://v/a", "A", "best", "C:/y", video_id="a")
        same = queue.add("https://kratko/a", "A", "best", "C:/x", video_id="a")
        key = scheduler.output_key(one, DEFAULT_NAME_TEMPLATE)
        self.assertEqual(scheduler.output_key(same, DEFAULT_NAME_TEMPLATE), key)
        self.assertNotEqual(scheduler.output_key(other_preset, DEFAULT_NAME_TEMPLATE), key)
        self.assertNotEqual(scheduler.output_key(other_folder, DEFAULT_NAME_TEMPLATE), key)


if __name__ == "__main__":
    unittest.main()
