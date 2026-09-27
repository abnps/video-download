package io.github.abnps.videodownload

import android.os.Bundle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

/** Jedno preuzimanje, kako ga je korisnik izabrao na ekranu „Izaberi kvalitet". */
data class Job(
    val id: Long,
    val url: String,
    val title: String,
    val thumbnail: String,
    val duration: Int,
    val isAudio: Boolean,
    val height: Int, // 0 = najbolji
    val label: String, // „1080p", „Najbolji", „M4A"
) {
    fun toBundle() = Bundle().apply {
        putLong("id", id); putString("url", url); putString("title", title); putString("thumbnail", thumbnail)
        putInt("duration", duration); putBoolean("audio", isAudio); putInt("height", height); putString("label", label)
    }

    companion object {
        fun fromBundle(bundle: Bundle) = Job(
            bundle.getLong("id"), bundle.getString("url").orEmpty(), bundle.getString("title").orEmpty(),
            bundle.getString("thumbnail").orEmpty(), bundle.getInt("duration"), bundle.getBoolean("audio"),
            bundle.getInt("height"), bundle.getString("label").orEmpty(),
        )
    }
}

enum class Phase { QUEUED, READING, DOWNLOADING, SAVING }

data class ActiveJob(val job: Job, val phase: Phase, val fraction: Float? = null, val done: Long = 0, val total: Long = 0)

/** Šta usluga za preuzimanje trenutno radi; ekrani samo prikazuju. */
object Downloads {
    private val mutable = MutableStateFlow<List<ActiveJob>>(emptyList())
    val active: StateFlow<List<ActiveJob>> = mutable

    /** Posljednja greška (za poruku i „Kopiraj izvještaj"); null kad je sve u redu. */
    val lastError = MutableStateFlow<String?>(null)

    fun add(job: Job) = mutable.update { it + ActiveJob(job, Phase.QUEUED) }

    fun update(id: Long, change: (ActiveJob) -> ActiveJob) =
        mutable.update { list -> list.map { if (it.job.id == id) change(it) else it } }

    fun remove(id: Long) = mutable.update { list -> list.filterNot { it.job.id == id } }
}
