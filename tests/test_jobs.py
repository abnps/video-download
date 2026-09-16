import unittest

from videodl.jobs import DownloadQueue, ItemStatus


class DownloadQueueTest(unittest.TestCase):
    def setUp(self):
        self.queue = DownloadQueue()
        self.first = self.queue.add("https://v/1", "Prvi", "best", r"C:\d")
        self.second = self.queue.add("https://v/2", "Drugi", "mp3", r"C:\d", subfolder="Lista")

    def test_ids_are_unique_and_order_is_kept(self):
        self.assertNotEqual(self.first.id, self.second.id)
        self.assertEqual([i.title for i in self.queue.items()], ["Prvi", "Drugi"])
        self.assertIs(self.queue.next_waiting(), self.first)

    def test_active_item_cannot_be_removed(self):
        self.first.status = ItemStatus.ACTIVE
        self.assertFalse(self.queue.remove(self.first.id))
        self.assertIs(self.queue.active(), self.first)
        self.assertIs(self.queue.next_waiting(), self.second)
        self.assertTrue(self.queue.remove(self.second.id))
        self.assertIsNone(self.queue.get(self.second.id))

    def test_retry_only_failed_or_cancelled(self):
        self.assertFalse(self.queue.retry(self.first.id))
        self.first.status = ItemStatus.FAILED
        self.first.message = "Video nije dostupan"
        self.assertTrue(self.queue.retry(self.first.id))
        self.assertEqual(self.first.status, ItemStatus.WAITING)
        self.assertEqual(self.first.message, "")
        self.second.status = ItemStatus.CANCELLED
        self.assertTrue(self.queue.retry(self.second.id))

    def test_move_to_front(self):
        self.assertTrue(self.queue.move_to_front(self.second.id))
        self.assertIs(self.queue.next_waiting(), self.second)
        self.assertFalse(self.queue.move_to_front(999))

    def test_item_format_is_kept_when_main_format_changes(self):
        self.assertTrue(self.queue.set_preset(self.first.id, "m4a"))
        self.assertEqual(self.queue.apply_preset_to_waiting("720p"), [self.second.id])
        self.assertEqual((self.first.preset_key, self.second.preset_key), ("m4a", "720p"))

        self.second.status = ItemStatus.DONE
        self.second.filepath = r"C:\d\x.mp4"
        self.assertTrue(self.queue.set_preset(self.second.id, "mp3"))
        self.assertEqual((self.second.status, self.second.filepath), (ItemStatus.WAITING, None))
        self.first.status = ItemStatus.ACTIVE
        self.assertFalse(self.queue.set_preset(self.first.id, "best"))

    def test_clear_finished_removes_only_done(self):
        self.first.status = ItemStatus.DONE
        self.second.status = ItemStatus.FAILED
        self.assertEqual(self.queue.clear_finished(), [self.first.id])
        self.assertEqual([i.id for i in self.queue.items()], [self.second.id])


if __name__ == "__main__":
    unittest.main()
