"""Zaštita od blokade (Ahmed 2.11.2026): razmaci po sajtu, predah na 25, učenje poslije blokade, čekanje na blokadu."""

import random
import unittest

from videodl import pacing


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(**kwargs):
    clock, wall = Clock(), Clock()
    pacer = pacing.Pacer(rng=random.Random(7), clock=clock, wall=wall, **kwargs)
    return pacer, clock, wall


def run(pacer, family, count):
    """`count` preuzimanja zaredom (svako kreće tek kad pauza prođe); vraća pauzu poslije svakog."""
    pauses = []
    for _ in range(count):
        pacer._clock.now += pacer.remaining(family)
        pacer.started(family)
        pauses.append(pacer.finished(family))
    return pauses


class FamilyTest(unittest.TestCase):
    def test_strict_sites_and_their_short_addresses(self):
        for url, family in (("https://www.youtube.com/watch?v=a", "youtube"), ("https://youtu.be/a", "youtube"),
                            ("https://music.youtube.com/watch?v=a", "youtube"), ("https://m.youtube.com/a", "youtube"),
                            ("https://www.instagram.com/reel/a/", "instagram"), ("https://vm.tiktok.com/a", "tiktok"),
                            ("https://m.facebook.com/watch?v=1", "facebook"), ("https://fb.watch/a", "facebook"),
                            ("https://x.com/a/status/1", "x"), ("https://twitter.com/a/status/1", "x")):
            with self.subTest(url=url):
                self.assertEqual(pacing.family_of(url), family)

    def test_other_sites_and_direct_streams_are_not_slowed(self):
        for url in ("https://vimeo.com/1", "https://rr3---sn.googlevideo.com/videoplayback?x=1",
                    "https://cdn.example.com/a.m3u8", "", "nije link"):
            with self.subTest(url=url):
                self.assertIsNone(pacing.family_of(url))

    def test_block_errors(self):
        self.assertTrue(pacing.is_block_error("ERROR: HTTP Error 429: Too Many Requests"))
        self.assertTrue(pacing.is_block_error("Sign in to confirm you’re not a bot"))
        self.assertFalse(pacing.is_block_error("HTTP Error 403: Forbidden"))
        self.assertFalse(pacing.is_block_error(""))


class GapTest(unittest.TestCase):
    def test_first_nine_go_at_full_speed(self):
        pacer, _clock, _wall = make()
        self.assertEqual(run(pacer, "youtube", 8), [None] * 8)
        self.assertEqual(pacer.remaining("youtube"), 0)

    def test_levels_follow_the_table(self):
        pacer, _clock, _wall = make()
        pauses = run(pacer, "youtube", 60)
        for number, pause in enumerate(pauses, 1):  # pauza poslije `number`-tog, prije (number+1)-og
            following = number + 1
            with self.subTest(number=number):
                if number % 25 == 0:
                    self.assertEqual(pause.kind, "break")
                    self.assertTrue(30 <= pause.seconds <= 60)
                elif following < 10:
                    self.assertIsNone(pause)
                elif following < 25:
                    self.assertEqual(pause.kind, "gap")
                    self.assertTrue(2 <= pause.seconds <= 5, pause)
                elif following < 50:
                    self.assertTrue(5 <= pause.seconds <= 10, pause)
                else:
                    self.assertTrue(8 <= pause.seconds <= 15, pause)

    def test_gaps_are_random_not_a_robot_rhythm(self):
        pacer, _clock, _wall = make()
        seconds = {pause.seconds for pause in run(pacer, "youtube", 24)[8:]}
        self.assertGreater(len(seconds), 5)

    def test_next_waits_for_the_gap_and_other_sites_do_not(self):
        pacer, clock, _wall = make()
        pause = run(pacer, "youtube", 10)[-1]
        self.assertAlmostEqual(pacer.remaining("youtube"), pause.seconds)
        self.assertEqual(pacer.remaining("vimeo"), 0)
        self.assertEqual(pacer.remaining(None), 0)
        clock.now += pause.seconds
        self.assertEqual(pacer.remaining("youtube"), 0)

    def test_streak_resets_after_fifteen_quiet_minutes(self):
        pacer, clock, _wall = make()
        run(pacer, "youtube", 12)
        clock.now += pacing.IDLE_RESET + 1
        self.assertEqual(run(pacer, "youtube", 8), [None] * 8)

    def test_streak_is_per_site(self):
        pacer, _clock, _wall = make()
        run(pacer, "youtube", 12)
        self.assertEqual(run(pacer, "x", 8), [None] * 8)

    def test_instagram_and_tiktok_wait_longer(self):
        pacer, _clock, _wall = make()
        pauses = [p for p in run(pacer, "instagram", 23) if p]  # razmaci prije 10. do 24.
        self.assertTrue(all(3 <= p.seconds <= 7.5 for p in pauses))
        self.assertTrue(any(p.seconds > 5 for p in pauses))

    def test_parallel_is_capped_from_the_tenth(self):
        pacer, _clock, _wall = make()
        run(pacer, "youtube", 9)
        self.assertIsNone(pacer.parallel_cap("youtube"))
        pacer.started("youtube")
        self.assertEqual(pacer.parallel_cap("youtube"), 2)
        self.assertIsNone(pacer.parallel_cap("x"))

    def test_turned_off_means_no_gaps_breaks_or_cap(self):
        pacer, _clock, _wall = make()
        pacer.enabled = False
        self.assertEqual(run(pacer, "youtube", 60), [None] * 60)
        self.assertIsNone(pacer.parallel_cap("youtube"))
        self.assertEqual(pacing.request_sleep("https://youtube.com/playlist?list=x", enabled=False), 0)

    def test_playlist_reading_sleeps_only_on_strict_sites(self):
        for url in ("https://youtube.com/playlist?list=x", "https://www.youtube.com/watch?v=a&list=b",
                    "https://www.youtube.com/@kanal/videos", "https://www.tiktok.com/@neko"):
            self.assertEqual(pacing.request_sleep(url), 0.5, url)
        for url in ("https://www.youtube.com/watch?v=a", "https://youtu.be/a", "https://vimeo.com/channels/x"):
            self.assertEqual(pacing.request_sleep(url), 0, url)  # jedan video ili drugi sajt: bez razmaka


class BlockTest(unittest.TestCase):
    def test_waits_five_ten_fifteen_minutes_then_gives_up(self):
        pacer, clock, _wall = make()
        for attempt, minutes in ((1, 5), (2, 10), (3, 15)):
            pause = pacer.blocked("youtube", attempt)
            self.assertEqual((pause.kind, pause.seconds), ("block", minutes * 60))
            self.assertTrue(pause.card)
            self.assertAlmostEqual(pacer.remaining("youtube"), minutes * 60)
            clock.now += minutes * 60
        self.assertIsNone(pacer.blocked("youtube", 4))

    def test_waiting_for_a_block_works_even_when_protection_is_off(self):
        pacer, _clock, _wall = make()
        pacer.enabled = False
        self.assertEqual(pacer.blocked("youtube", 1).seconds, 300)

    def test_skip_ends_the_wait(self):
        pacer, _clock, _wall = make()
        pacer.blocked("youtube", 1)
        pacer.blocked("x", 1)
        pacer.skip("youtube")
        self.assertEqual(pacer.remaining("youtube"), 0)
        self.assertGreater(pacer.remaining("x"), 0)
        pacer.skip()
        self.assertEqual(pacer.remaining("x"), 0)

    def test_pending_tells_which_pause_holds_the_site(self):
        pacer, clock, _wall = make()
        self.assertIsNone(pacer.pending("youtube"))
        self.assertEqual(pacer.deadline("youtube"), 0.0)
        pauses = run(pacer, "youtube", 25)
        self.assertEqual(pauses[-1].kind, "break")
        pending = pacer.pending("youtube")
        self.assertEqual((pending.kind, pending.seconds), ("break", pauses[-1].seconds))
        self.assertEqual(pacer.deadline("youtube"), clock.now + pauses[-1].seconds)
        clock.now += pauses[-1].seconds
        self.assertIsNone(pacer.pending("youtube"))  # pauza je prošla

    def test_shorter_pause_does_not_replace_a_running_block(self):
        pacer, clock, _wall = make()
        run(pacer, "youtube", 9)
        pacer.blocked("youtube", 1)
        pacer.started("youtube")
        gap = pacer.finished("youtube")  # 10. zaredom: razmak od par sekundi dok blokada još teče
        self.assertEqual(gap.kind, "gap")
        self.assertEqual(pacer.pending("youtube").kind, "block")
        self.assertAlmostEqual(pacer.remaining("youtube"), 300)

    def test_turning_protection_off_ends_gaps_and_breaks_but_not_a_block(self):
        pacer, _clock, _wall = make()
        run(pacer, "youtube", 25)
        pacer.blocked("x", 1)
        self.assertGreater(pacer.remaining("youtube"), 0)
        pacer.enabled = False
        pacer.drop_soft()
        self.assertEqual(pacer.remaining("youtube"), 0)  # predah prestaje odmah
        self.assertEqual(pacer.remaining("x"), 300)  # stvarna blokada se i dalje čeka

    def test_learns_for_seven_days_after_a_block(self):
        pacer, clock, wall = make()
        pacer.blocked("youtube", 1)
        pacer.skip()
        clock.now += pacing.IDLE_RESET + 1
        pauses = run(pacer, "youtube", 14)
        self.assertEqual(pauses[:3], [None] * 3)
        self.assertEqual(pauses[3].kind, "gap")  # prije 5. umjesto prije 10.
        self.assertTrue(3 <= pauses[3].seconds <= 7.5)
        self.assertEqual(pauses[12].kind, "break")  # predah već poslije 13.
        self.assertEqual(pacer.parallel_cap("youtube"), 2)
        wall.now += pacing.LEARN_SECONDS + 1
        clock.now += pacing.IDLE_RESET + 1
        self.assertEqual(run(pacer, "youtube", 8), [None] * 8)


if __name__ == "__main__":
    unittest.main()
