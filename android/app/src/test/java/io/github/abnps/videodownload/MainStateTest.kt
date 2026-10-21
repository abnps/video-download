package io.github.abnps.videodownload

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.yield
import org.junit.Assert.*
import org.junit.Test
import kotlin.coroutines.Continuation
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

class MainStateTest {
    private fun video(adult: Boolean = false) = VideoInfo("https://example.org/video", "Primjer", "", 30,
        "example.org", emptyList(), 0.0, true, adult)

    @Test fun snapshotRestoresInputAndNavigationWithoutDownloadEvent() {
        val old = MainState().apply {
            link.value = "https://example.org/video"
            tab.intValue = 2
            tabBeforeSettings = 1
            downloadsTab.intValue = 1
            showAchievements.value = true
            quickVideo.value = video()
        }
        val saved = old.snapshot()
        val fresh = MainState().apply { restore(saved) }
        assertEquals(saved.link, fresh.link.value)
        assertEquals(2, fresh.tab.intValue)
        assertEquals(1, fresh.tabBeforeSettings)
        assertEquals(1, fresh.downloadsTab.intValue)
        assertTrue(fresh.showAchievements.value)
        assertTrue(saved.resumeProbe)
        assertNull(fresh.takeQuickVideo())
        assertNull(fresh.info.value)
    }

    @Test fun quickDownloadIsConsumedOnceAndNeverForAdult() = runBlocking {
        val state = MainState()
        state.find(true, { ProbeResult(video()) }, { "Greška" }, this)
        yield()
        assertEquals(video(), state.takeQuickVideo())
        assertNull(state.takeQuickVideo())
        state.find(true, { ProbeResult(video(adult = true)) }, { "Greška" }, this)
        yield()
        assertNull(state.takeQuickVideo())
        assertTrue(state.info.value!!.adult)
    }

    @Test fun oversizedInputIsNotTruncatedIntoAnotherLinkOrSavedInBundle() {
        val state = MainState().apply { link.value = "https://example.org/" + "a".repeat(9000); finding.value = true }
        assertEquals("", state.snapshot().link)
        assertFalse(state.snapshot().resumeProbe)
        assertTrue(state.link.value.length > 8192)
    }

    @Test fun playlistSelectionCannotFollowIndicesIntoReorderedVideos() {
        val first = PlaylistEntry("https://example.org/a", "A", "", 1, false)
        val second = first.copy(url = "https://example.org/b", title = "B")
        val list = PlaylistInfo("https://example.org/list", "Lista", "example.org", listOf(first, second))
        assertEquals(list.selectionKey(), list.copy(entries = listOf(first.copy(title = "Novi naslov"), second)).selectionKey())
        assertNotEquals(list.selectionKey(), list.copy(entries = listOf(second, first)).selectionKey())
    }

    @Test fun lateProbeCannotReplaceNewResultOrStopItsSpinner() {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Unconfined)
        try {
            val state = MainState()
            lateinit var first: Continuation<ProbeResult>
            lateinit var second: Continuation<ProbeResult>
            state.find(true, { suspendCoroutine { first = it } }, { "Stara greška" }, scope)
            state.find(false, { suspendCoroutine { second = it } }, { "Nova greška" }, scope)
            first.resume(ProbeResult(video()))
            assertTrue(state.finding.value)
            assertNull(state.takeQuickVideo())
            assertNull(state.info.value)
            second.resume(ProbeResult(video().copy(title = "Novi link")))
            assertEquals("Novi link", state.info.value!!.title)
            assertFalse(state.finding.value)
        } finally { scope.cancel() }
    }

    @Test fun cancelledInputCannotStartQuickDownloadAndFailureAllowsRetry() {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Unconfined)
        try {
            val state = MainState()
            lateinit var pending: Continuation<ProbeResult>
            state.find(true, { suspendCoroutine { pending = it } }, { "Greška" }, scope)
            state.cancelProbe()
            pending.resume(ProbeResult(video()))
            assertNull(state.takeQuickVideo())
            assertFalse(state.finding.value)
            state.find(false, { throw IllegalStateException("Privatni detalji") }, { "Očišćena greška" }, scope)
            assertEquals("Očišćena greška", state.findError.value)
            state.find(false, { ProbeResult(video()) }, { "Greška" }, scope)
            assertNull(state.findError.value)
            assertEquals(video(), state.info.value)
        } finally { scope.cancel() }
    }
}
