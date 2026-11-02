"""Mjesečni i godišnji pregled (Ahmed 2.11.2026): samo brojke, jednom po periodu, bar 10 preuzimanja."""

import unittest
from datetime import date, datetime, timedelta

from videodl import recap

GB = 1024 ** 3


def fill(state, count, start=datetime(2026, 10, 5, 12), url="https://www.youtube.com/watch?v=a", size=GB // 10,
         duration=600.0):
    for i in range(count):
        state.record(url, size, duration, start + timedelta(hours=i))


class RecordTest(unittest.TestCase):
    def test_month_numbers(self):
        state = recap.RecapState()
        fill(state, 9)
        state.record("https://vimeo.com/1", GB, 3 * 3600.0, datetime(2026, 10, 20, 9))
        state.record("https://x.com/a/status/1", 0, None, datetime(2026, 10, 21, 9))
        summary = state.summary("2026-10")
        self.assertEqual(summary.count, 11)
        self.assertEqual(summary.bytes, 9 * (GB // 10) + GB)
        self.assertEqual(summary.seconds, 9 * 600 + 3 * 3600)
        self.assertEqual(summary.longest, 3 * 3600)
        self.assertEqual(summary.top_site, "youtube.com")
        self.assertEqual(summary.busiest_weekday, 0)  # 5.10.2026 je ponedjeljak
        self.assertFalse(summary.yearly)

    def test_no_titles_or_links_are_kept(self):
        state = recap.RecapState()
        state.record("https://www.youtube.com/watch?v=tajno123", 10, 5.0, datetime(2026, 10, 5))
        self.assertNotIn("tajno123", state.to_json())
        self.assertIn("youtube.com", state.to_json())

    def test_today_counter(self):
        state = recap.RecapState()
        fill(state, 3, start=datetime(2026, 11, 2, 8))
        self.assertEqual(state.today(date(2026, 11, 2)), (3, 3 * (GB // 10)))
        self.assertEqual(state.today(date(2026, 11, 3)), (0, 0))
        state.record("https://youtu.be/a", 5, None, datetime(2026, 11, 3, 8))
        self.assertEqual(state.today(date(2026, 11, 3)), (1, 5))

    def test_old_months_are_dropped(self):
        state = recap.RecapState()
        day = datetime(2025, 1, 10)
        for month in range(20):
            state.record("https://youtu.be/a", 1, None, day)
            day = datetime(day.year + (day.month == 12), day.month % 12 + 1, 10)
        self.assertEqual(len(state.months), recap.KEEP_MONTHS)


class DueTest(unittest.TestCase):
    def test_shown_once_in_the_next_month_with_ten_or_more(self):
        state = recap.RecapState()
        fill(state, 10)
        summary = state.due(date(2026, 11, 1))
        self.assertEqual(summary.period, "2026-10")
        state.shown(summary.period)
        self.assertIsNone(state.due(date(2026, 11, 15)))
        self.assertIsNone(state.due(date(2026, 10, 30)))  # tekući mjesec se ne prikazuje

    def test_quiet_month_has_no_recap(self):
        state = recap.RecapState()
        fill(state, 9)
        self.assertIsNone(state.due(date(2026, 11, 1)))

    def test_january_shows_the_year_instead_of_december(self):
        state = recap.RecapState()
        fill(state, 6, start=datetime(2026, 3, 2, 10))
        fill(state, 6, start=datetime(2026, 12, 2, 10))
        summary = state.due(date(2027, 1, 3))
        self.assertEqual((summary.period, summary.yearly, summary.count), ("2026", True, 12))
        state.shown("2026")
        self.assertIsNone(state.due(date(2027, 1, 20)))


class SavingTest(unittest.TestCase):
    def test_round_trip(self):
        state = recap.RecapState()
        fill(state, 12)
        state.shown("2026-09")
        again = recap.RecapState.from_json(state.to_json())
        self.assertEqual(again, state)

    def test_damaged_values_never_break_start(self):
        for text in ("", "{", "[]", "null", '{"months": 5}', '{"months": {"2026-10": "x"}}',
                     '{"months": {"2026-10": {"count": -3, "weekdays": [1]}}, "day_count": "x"}'):
            with self.subTest(text=text):
                state = recap.RecapState.from_json(text)
                state.record("https://youtu.be/a", 1, 1.0, datetime(2026, 10, 5))
                self.assertIsNone(state.due(date(2026, 11, 1)))


if __name__ == "__main__":
    unittest.main()
