package io.github.abnps.videodownload

import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job as CoroutineJob
import kotlinx.coroutines.launch

/** Stanje prozora i čitanje linka preživljavaju rotaciju; ne zadržavaju aktivnost ni potvrdu 18+. */
class MainState : ViewModel() {
    val link = mutableStateOf("")
    val tab = mutableIntStateOf(0)
    var tabBeforeSettings = 0
    val downloadsTab = mutableIntStateOf(0)
    val info = mutableStateOf<VideoInfo?>(null)
    val playlist = mutableStateOf<PlaylistInfo?>(null)
    val finding = mutableStateOf(false)
    val findError = mutableStateOf<String?>(null)
    val showAchievements = mutableStateOf(false)
    val quickVideo = mutableStateOf<VideoInfo?>(null)
    var pasteOnFocus = false
    var initialized = false
    private var generation = 0
    private var probeJob: CoroutineJob? = null

    fun cancelProbe() {
        generation++
        probeJob?.cancel()
        probeJob = null
        finding.value = false
        quickVideo.value = null
    }

    fun find(quick: Boolean, load: suspend () -> ProbeResult, errorText: (Exception) -> String,
             scope: CoroutineScope = viewModelScope) {
        cancelProbe()
        val request = generation
        info.value = null
        playlist.value = null
        finding.value = true
        findError.value = null
        probeJob = scope.launch {
            try {
                val result = load()
                // Python poziv se ne može uvijek prekinuti; kasni rezultat ne smije zamijeniti novi link.
                if (request != generation) return@launch
                when {
                    result.playlist != null -> playlist.value = result.playlist
                    quick && result.video != null && !result.video.adult -> quickVideo.value = result.video
                    else -> info.value = result.video
                }
            } catch (error: CancellationException) {
                throw error
            } catch (error: Exception) {
                if (request == generation) findError.value = errorText(error)
            } finally {
                if (request == generation) finding.value = false
            }
        }
    }

    /** Događaj se potroši prije pokretanja servisa, pa ga novi ekran ne može ponoviti. */
    fun takeQuickVideo(): VideoInfo? = quickVideo.value.also { quickVideo.value = null }

    fun snapshot(): MainSnapshot {
        // Bundle dijeli ograničen prostor s ostalim ekranima; pretjeran unos ne skraćujemo u pogrešan URL.
        val savedLink = link.value.takeIf { it.length <= 8192 }.orEmpty()
        return MainSnapshot(savedLink, tab.intValue, tabBeforeSettings, downloadsTab.intValue,
            showAchievements.value, pasteOnFocus, savedLink.isNotEmpty() &&
                (finding.value || info.value != null || playlist.value != null || quickVideo.value != null))
    }

    fun restore(saved: MainSnapshot) {
        link.value = saved.link
        tab.intValue = saved.tab.takeIf { it in 0..2 } ?: 0
        tabBeforeSettings = saved.tabBeforeSettings.takeIf { it in 0..1 } ?: 0
        downloadsTab.intValue = saved.downloadsTab.takeIf { it in 0..1 } ?: 0
        showAchievements.value = saved.showAchievements
        pasteOnFocus = saved.pasteOnFocus
    }
}

data class ProbeResult(val video: VideoInfo? = null, val playlist: PlaylistInfo? = null)

/** U Androidov Bundle idu samo mali ulazni podaci; nema rezultata, kolačića ni potvrda za preuzimanje. */
data class MainSnapshot(val link: String = "", val tab: Int = 0, val tabBeforeSettings: Int = 0,
                        val downloadsTab: Int = 0, val showAchievements: Boolean = false,
                        val pasteOnFocus: Boolean = false, val resumeProbe: Boolean = false)
