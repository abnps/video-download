package io.github.abnps.videodownload

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import kotlin.random.Random

/** Zaštita od blokade kao na računaru (tests/test_pacing.py, Ahmed 2.11.2026). */
class PacingTest {
    private var now = 1_000_000L
    private var wall = 1_800_000_000_000L

    @Before
    fun setUp() {
        Pacing.clock = { now }
        Pacing.wall = { wall }
        Pacing.random = Random(7)
        Pacing.enabled = true
        Pacing.learnedUntil = 0
        Pacing.reset()
    }

    /** `count` preuzimanja zaredom (svako kreće kad pauza prođe); pauza poslije svakog. */
    private fun run(family: String, count: Int): List<Pause?> = List(count) {
        now += Pacing.remaining(family)
        Pacing.started(family)
        Pacing.finished(family)
    }

    @Test
    fun strictSitesAndOthers() {
        assertEquals("youtube", Pacing.familyOf("https://youtu.be/a"))
        assertEquals("youtube", Pacing.familyOf("https://music.youtube.com/watch?v=a"))
        assertEquals("tiktok", Pacing.familyOf("https://vm.tiktok.com/a"))
        assertEquals("x", Pacing.familyOf("https://twitter.com/a/status/1"))
        assertNull(Pacing.familyOf("https://vimeo.com/1"))
        assertTrue(Pacing.isBlockError("ERROR: HTTP Error 429: Too Many Requests"))
        assertTrue(Pacing.isBlockError("Sign in to confirm you're not a bot"))
        assertFalse(Pacing.isBlockError("HTTP Error 403"))
    }

    @Test
    fun levelsFollowTheTable() {
        val pauses = run("youtube", 60)
        pauses.forEachIndexed { index, pause ->
            val number = index + 1
            val following = number + 1
            when {
                number % 25 == 0 -> assertTrue(pause!!.kind == "break" && pause.millis in 30_000..60_000)
                following < 10 -> assertNull(pause)
                following < 25 -> assertTrue("$number $pause", pause!!.kind == "gap" && pause.millis in 2_000..5_000)
                following < 50 -> assertTrue("$number $pause", pause!!.millis in 5_000..10_000)
                else -> assertTrue("$number $pause", pause!!.millis in 8_000..15_000)
            }
        }
    }

    @Test
    fun streakResetsAfterFifteenQuietMinutes() {
        run("youtube", 12)
        now += 15 * 60 * 1000L + 1
        assertTrue(run("youtube", 8).all { it == null })
    }

    @Test
    fun offMeansNoGaps() {
        Pacing.enabled = false
        assertTrue(run("youtube", 60).all { it == null })
    }

    @Test
    fun recognizesTheRobotCheckFromReadingALink() {
        // Poruka YouTubea pri čitanju linka (prijava prijatelja 13.11.2026), i s „pravim" apostrofom.
        assertTrue(Pacing.isBlockError("ERROR: [youtube] wM804ePU4tE: Sign in to confirm you're not a bot."))
        assertTrue(Pacing.isBlockError("sign in to confirm you’re not a bot"))
        assertTrue(!Pacing.isBlockError("Sign in to view this video"))
    }

    @Test
    fun turningOffEndsGapsAndBreaksButNotABlock() {
        run("youtube", 25)
        assertTrue(Pacing.remaining("youtube") > 0) // predah poslije 25.
        Pacing.blocked("x", 1)
        Pacing.enabled = false
        Pacing.dropSoft()
        assertEquals(0L, Pacing.remaining("youtube"))
        assertEquals(5 * 60_000L, Pacing.remaining("x")) // stvarna blokada se i dalje čeka
    }

    @Test
    fun blockWaitsFiveTenFifteenThenGivesUpAndLearns() {
        assertEquals(5 * 60_000L, Pacing.blocked("youtube", 1)!!.millis)
        assertEquals(10 * 60_000L, Pacing.blocked("youtube", 2)!!.millis)
        assertEquals(15 * 60_000L, Pacing.blocked("youtube", 3)!!.millis)
        assertNull(Pacing.blocked("youtube", 4))
        assertEquals("block", Pacing.lastPause("youtube")!!.kind)
        Pacing.skip("youtube")
        assertEquals(0L, Pacing.remaining("youtube"))
        now += 15 * 60 * 1000L + 1
        val pauses = run("youtube", 14)
        assertNull(pauses[2])
        assertEquals("gap", pauses[3]!!.kind) // naučeno: razmak već prije 5.
        assertEquals("break", pauses[12]!!.kind) // i predah poslije 13.
        wall += Pacing.LEARN_MILLIS + 1
        now += 15 * 60 * 1000L + 1
        assertTrue(run("youtube", 8).all { it == null })
    }
}
