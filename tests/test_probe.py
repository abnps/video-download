import unittest

from videodl.probe import Entry, pick_thumbnail, probe


def fake_extractor(pages: dict):
    calls = []

    def extract(url):
        calls.append(url)
        return pages[url]

    extract.calls = calls
    return extract


class ProbeTest(unittest.TestCase):
    def test_single_video(self):
        extract = fake_extractor({
            "https://v/1": {"_type": "video", "id": "1", "title": "Prvi",
                            "webpage_url": "https://www.v/watch?v=1"},
        })
        result = probe("https://v/1", extract)
        self.assertFalse(result.is_playlist)
        self.assertEqual(result.entries, (Entry("https://www.v/watch?v=1", "Prvi"),))

    def test_playlist_skips_empty_entries_and_uses_id_when_no_title(self):
        extract = fake_extractor({
            "https://v/list": {"_type": "playlist", "title": "Lista", "entries": [
                {"_type": "url", "url": "https://v/1", "title": "Prvi", "ie_key": "Youtube"},
                None,
                {"_type": "url", "url": "https://v/2", "id": "2", "ie_key": "Youtube"},
                {"_type": "url", "title": "Bez linka"},
            ]},
        })
        result = probe("https://v/list", extract)
        self.assertTrue(result.is_playlist)
        self.assertEqual(result.title, "Lista")
        self.assertEqual(result.entries, (Entry("https://v/1", "Prvi"), Entry("https://v/2", "2")))

    def test_channel_tabs_are_flattened(self):
        extract = fake_extractor({
            "https://v/@kanal": {"_type": "playlist", "title": "Kanal", "entries": [
                {"_type": "url", "url": "https://v/@kanal/videos", "ie_key": "YoutubeTab"},
                {"_type": "url", "url": "https://v/@kanal/shorts", "ie_key": "YoutubeTab"},
            ]},
            "https://v/@kanal/videos": {"_type": "playlist", "entries": [
                {"_type": "url", "url": "https://v/1", "title": "Video"},
            ]},
            "https://v/@kanal/shorts": {"_type": "playlist", "entries": [
                {"_type": "url", "url": "https://v/2", "title": "Short"},
            ]},
        })
        result = probe("https://v/@kanal", extract)
        self.assertEqual([e.title for e in result.entries], ["Video", "Short"])

    def test_thumbnail_and_duration(self):
        info = {"_type": "video", "title": "V", "duration": 189, "thumbnails": [
            {"url": "https://i/small.jpg", "width": 120},
            {"url": "https://i/mq.jpg", "width": 320},
            {"url": "https://i/hq.jpg", "width": 480},
            {"url": "https://i/nosize.webp"},
        ]}
        result = probe("https://v/1", fake_extractor({"https://v/1": info}))
        self.assertEqual(result.entries[0].thumbnail, "https://i/mq.jpg")
        self.assertEqual(result.entries[0].duration, 189.0)
        self.assertEqual(pick_thumbnail({"thumbnails": [{"url": "https://i/a"}, {"url": "https://i/b"}]}), "https://i/b")
        self.assertEqual(pick_thumbnail({"thumbnail": "https://i/c"}), "https://i/c")
        self.assertIsNone(pick_thumbnail({}))

    def test_nesting_is_limited(self):
        pages = {}
        for level in range(5):
            pages[f"https://v/{level}"] = {"_type": "playlist", "entries": [
                {"_type": "playlist", "url": f"https://v/{level + 1}", "title": f"nivo {level + 1}"},
            ]}
        extract = fake_extractor(pages)
        result = probe("https://v/0", extract)
        # Početni poziv + najviše MAX_NESTING ugnježdenih; dublji nivo ostaje stavka.
        self.assertEqual(len(extract.calls), 3)
        self.assertEqual(result.entries, (Entry("https://v/3", "nivo 3"),))


if __name__ == "__main__":
    unittest.main()
