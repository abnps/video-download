package io.github.abnps.videodownload

import android.content.Context
import android.os.Bundle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import org.json.JSONArray
import org.json.JSONObject

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

enum class Phase { QUEUED, READING, DOWNLOADING, CONVERTING, SAVING, DONE, INTERRUPTED }

data class ActiveJob(val job: Job, val phase: Phase, val fraction: Float? = null, val done: Long = 0, val total: Long = 0,
                     val speed: Double = 0.0, val eta: Long = -1, val audioPart: Boolean = false)

/** Šta usluga za preuzimanje trenutno radi; ekrani samo prikazuju. */
object Downloads {
    private lateinit var app: Context
    private val mutable = MutableStateFlow<List<ActiveJob>>(emptyList())
    val active: StateFlow<List<ActiveJob>> = mutable

    /** Posljednja greška (za poruku i „Kopiraj izvještaj"); null kad je sve u redu. */
    val lastError = MutableStateFlow<String?>(null)

    /** Poslovi iz ugašenog procesa ostaju vidljivi za ponovni pokušaj, bez automatskog preuzimanja. */
    fun load(context: Context) {
        app = context.applicationContext
        val saved = app.getSharedPreferences("pending_jobs", Context.MODE_PRIVATE).getString("jobs", "[]").orEmpty()
        mutable.value = runCatching {
            val array = JSONArray(saved)
            (0 until array.length()).mapNotNull { index ->
                runCatching {
                    val value = array.getJSONObject(index)
                    ActiveJob(Job(value.getLong("id"), value.getString("url"), value.getString("title"),
                        value.optString("thumbnail"), value.optInt("duration"), value.getBoolean("audio"),
                        value.optInt("height"), value.optString("label")), Phase.INTERRUPTED)
                }.getOrNull()
            }.distinctBy { it.job.id }
        }.getOrDefault(emptyList())
    }

    @Synchronized fun add(job: Job) {
        val next = mutable.value.filterNot { it.job.id == job.id } + ActiveJob(job, Phase.QUEUED)
        persist(next)
        mutable.value = next
    }

    fun update(id: Long, change: (ActiveJob) -> ActiveJob) =
        mutable.update { list -> list.map { if (it.job.id == id) change(it) else it } }

    @Synchronized fun remove(id: Long) {
        val next = mutable.value.filterNot { it.job.id == id }
        persist(next)
        mutable.value = next
    }

    private fun persist(list: List<ActiveJob>) {
        val array = JSONArray()
        list.forEach { active ->
            val job = active.job
            array.put(JSONObject().put("id", job.id).put("url", job.url).put("title", job.title)
                .put("thumbnail", job.thumbnail).put("duration", job.duration).put("audio", job.isAudio)
                .put("height", job.height).put("label", job.label))
        }
        check(app.getSharedPreferences("pending_jobs", Context.MODE_PRIVATE).edit()
            .putString("jobs", array.toString()).commit()) { "Lista preuzimanja nije sačuvana" }
    }
}
