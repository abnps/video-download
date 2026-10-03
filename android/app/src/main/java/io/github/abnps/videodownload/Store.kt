package io.github.abnps.videodownload

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Gdje ide gotov fajl: Galerija/Muzika u folder s imenom aplikacije (podrazumijevano, Ahmed 2.10.2026)
 *  ili Downloads/Video Download. */
enum class SaveLocation { DOWNLOADS, GALLERY }

object Settings {
    private const val FILE = "postavke"

    fun location(context: Context): SaveLocation = runCatching {
        SaveLocation.valueOf(prefs(context).getString("location", SaveLocation.GALLERY.name)!!)
    }.getOrDefault(SaveLocation.GALLERY)

    fun setLocation(context: Context, value: SaveLocation) = prefs(context).edit().putString("location", value.name).apply()

    /** 0 = najbolji dostupni kvalitet; inače najviše toliko (uži rub: 1080, 720, 480). */
    fun quality(context: Context): Int = prefs(context).getInt("quality", 0)

    fun setQuality(context: Context, value: Int) = prefs(context).edit().putInt("quality", value).apply()

    /** Brzo preuzimanje (plan 1.0): link iz „Podijeli" odmah ide na preuzimanje u podrazumijevanom kvalitetu. */
    fun quickShare(context: Context): Boolean = prefs(context).getBoolean("quick_share", false)

    fun setQuickShare(context: Context, value: Boolean) = prefs(context).edit().putBoolean("quick_share", value).apply()

    private fun prefs(context: Context) = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
}

/** Završeno preuzimanje (ekran Preuzimanja → Završeno i „Nedavno preuzeto" na početnoj). */
data class HistoryItem(
    val id: Long,
    val title: String,
    val uri: String,
    val isAudio: Boolean,
    val format: String, // npr. „MP4 • 1080p" ili „M4A"
    val size: Long,
    val duration: Int,
    val thumbnail: String,
    val finishedAt: Long,
    val adult: Boolean = false, // 18+: sličica ostaje zamućena i u istoriji
) {
    fun toJson(): JSONObject = JSONObject().put("id", id).put("title", title).put("uri", uri).put("audio", isAudio)
        .put("format", format).put("size", size).put("duration", duration).put("thumbnail", thumbnail)
        .put("finished", finishedAt).put("adult", adult)

    companion object {
        fun fromJson(json: JSONObject) = HistoryItem(
            json.optLong("id"), json.optString("title"), json.optString("uri"), json.optBoolean("audio"),
            json.optString("format"), json.optLong("size"), json.optInt("duration"), json.optString("thumbnail"),
            json.optLong("finished"), json.optBoolean("adult"),
        )
    }
}

/** Istorija u privatnom fajlu aplikacije (najviše 300 stavki); oštećen fajl se ne ruši nego počinje prazan. */
object History {
    private const val MAX = 300
    private val mutable = MutableStateFlow<List<HistoryItem>>(emptyList())
    val items: StateFlow<List<HistoryItem>> = mutable
    private var file: File? = null

    fun load(context: Context) {
        val target = File(context.filesDir, "istorija.json").also { file = it }
        mutable.value = runCatching {
            val array = JSONArray(target.readText())
            (0 until array.length()).map { HistoryItem.fromJson(array.getJSONObject(it)) }
        }.getOrDefault(emptyList())
    }

    @Synchronized
    fun add(item: HistoryItem) = save((listOf(item) + mutable.value).take(MAX))

    @Synchronized
    fun remove(id: Long) = save(mutable.value.filterNot { it.id == id })

    private fun save(list: List<HistoryItem>) {
        mutable.value = list
        val target = file ?: return
        val temporary = File(target.path + ".tmp")
        temporary.writeText(JSONArray(list.map { it.toJson() }).toString())
        temporary.renameTo(target) // cijeli fajl ili ništa
    }
}
