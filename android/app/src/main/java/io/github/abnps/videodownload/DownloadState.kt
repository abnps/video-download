package io.github.abnps.videodownload

import android.net.Uri
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** Šta usluga za preuzimanje trenutno radi; ekran ga samo prikazuje. */
sealed interface DownloadStatus {
    data object Idle : DownloadStatus
    data object Reading : DownloadStatus
    data class Downloading(val fraction: Float?) : DownloadStatus
    data object Saving : DownloadStatus
    data class Done(val title: String, val uri: Uri, val isAudio: Boolean) : DownloadStatus
    data class Failed(val message: String) : DownloadStatus
    data object Cancelled : DownloadStatus
}

object DownloadState {
    private val mutable = MutableStateFlow<DownloadStatus>(DownloadStatus.Idle)
    val status: StateFlow<DownloadStatus> = mutable

    fun set(status: DownloadStatus) {
        mutable.value = status
    }
}
