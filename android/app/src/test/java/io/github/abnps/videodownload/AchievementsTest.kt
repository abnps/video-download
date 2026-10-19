package io.github.abnps.videodownload

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AchievementsTest {
    @Test
    fun sitesAreCountedByRegistrableDomain() {
        assertEquals("klix.ba", Achievements.siteOf("https://m.klix.ba/video/1"))
        assertEquals("klix.ba", Achievements.siteOf("https://www.klix.ba/"))
        assertEquals("bbc.co.uk", Achievements.siteOf("https://news.bbc.co.uk/x"))
        assertEquals("", Achievements.siteOf("nije link"))
    }

    @Test
    fun everyBadgeHasAUniqueKeyAndMilestonesAreSorted() {
        assertEquals(Achievements.BADGES.size, Achievements.BADGES.map { it.key }.toSet().size)
        assertEquals(Achievements.MILESTONES.sorted(), Achievements.MILESTONES)
        assertTrue(Achievements.BADGES.size >= 28)
    }
}
