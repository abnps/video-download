package io.github.abnps.videodownload

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.temporal.ChronoUnit

/**
 * Dostignuća (Ahmed 20.10.2026), kao na računaru (videodl/achievements.py): čestitke za broj preuzimanja i za način
 * korištenja. Sve se računa i čuva samo na telefonu (privatna podešavanja aplikacije); ništa se ne šalje.
 */
data class Badge(val key: String, val icon: String, val name: Int, val desc: Int, val count: Int = 0)

/** Jedno novo, uspješno preuzimanje: samo ono što dostignuća trebaju. */
data class FinishedDownload(
    val url: String, val audio: Boolean, val clip: Boolean, val height: Int, val size: Long, val subtitles: Boolean,
    val duration: Int, val retried: Boolean, val playlistKey: String, val playlistSize: Int,
    val at: LocalDateTime = LocalDateTime.now(),
)

object Achievements {
    val MILESTONES = listOf(10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
    private const val PLAYLIST_MIN = 10
    private const val MARATHON_SECONDS = 2 * 60 * 60
    private const val GB = 1024L * 1024 * 1024
    private const val SUPPORT_NOTE_EVERY = 24 * 60 * 60 * 1000L // poruka za prilog najviše jednom dnevno
    private val SECOND_LEVEL = setOf("co", "com", "org", "net", "gov", "edu", "ac", "or", "ne", "go", "gob", "nic")

    val BADGES: List<Badge> = MILESTONES.map { Badge("count$it", "🏆", R.string.badge_count, R.string.badge_count_desc, it) } +
        listOf(
            Badge("audio", "🎵", R.string.badge_audio, R.string.badge_audio_desc),
            Badge("playlist", "📚", R.string.badge_playlist, R.string.badge_playlist_desc),
            Badge("clip", "✂️", R.string.badge_clip, R.string.badge_clip_desc),
            Badge("uhd", "🔭", R.string.badge_uhd, R.string.badge_uhd_desc),
            Badge("share", "📤", R.string.badge_share, R.string.badge_share_desc),
            Badge("widget", "🧩", R.string.badge_widget, R.string.badge_widget_desc),
            Badge("tile", "⚡", R.string.badge_tile, R.string.badge_tile_desc),
            Badge("invite", "👫", R.string.badge_invite, R.string.badge_invite_desc),
            Badge("subtitles", "💬", R.string.badge_subtitles, R.string.badge_subtitles_desc),
            Badge("marathon", "🎬", R.string.badge_marathon, R.string.badge_marathon_desc),
            Badge("comeback", "🔁", R.string.badge_comeback, R.string.badge_comeback_desc),
            Badge("night", "🦉", R.string.badge_night, R.string.badge_night_desc),
            Badge("sites5", "🌍", R.string.badge_sites5, R.string.badge_sites5_desc),
            Badge("sites25", "🗺️", R.string.badge_sites25, R.string.badge_sites25_desc),
            Badge("gb1", "💾", R.string.badge_gb1, R.string.badge_gb1_desc),
            Badge("gb10", "💽", R.string.badge_gb10, R.string.badge_gb10_desc),
            Badge("gb100", "🗄️", R.string.badge_gb100, R.string.badge_gb100_desc),
            Badge("streak7", "📅", R.string.badge_streak7, R.string.badge_streak7_desc),
            Badge("anniversary", "🎂", R.string.badge_anniversary, R.string.badge_anniversary_desc),
        )
    private val byKey = BADGES.associateBy { it.key }

    /** Osvojena, a još nečestitana (ekran ih pokaže kad ništa ne preuzima). */
    private val mutablePending = MutableStateFlow<List<Badge>>(emptyList())
    val pending: StateFlow<List<Badge>> = mutablePending

    private var app: Context? = null
    private var earned = JSONObject() // ključ -> vrijeme osvajanja (ms)
    private var downloads = 0
    private var totalBytes = 0L
    private var sites = mutableListOf<String>()
    private var firstDay = ""
    private var lastDay = ""
    private var streak = 0
    private var playlists = JSONObject() // ključ liste -> broj uspjelih stavki
    private var lastSupportNote = 0L

    @Synchronized
    fun load(context: Context) {
        app = context.applicationContext
        val prefs = prefs(context)
        val saved = prefs.getString("stanje", null)
        // Pokvarena vrijednost ne smije srušiti aplikaciju: tada se kreće ispočetka.
        val json = runCatching { JSONObject(saved ?: "{}") }.getOrDefault(JSONObject())
        earned = json.optJSONObject("earned") ?: JSONObject()
        downloads = json.optInt("downloads", -1)
        totalBytes = json.optLong("bytes")
        sites = json.optJSONArray("sites")?.let { array -> (0 until array.length()).map { array.optString(it) } }
            .orEmpty().filter { it.isNotEmpty() }.toMutableList()
        firstDay = json.optString("first_day")
        lastDay = json.optString("last_day")
        streak = json.optInt("streak")
        playlists = json.optJSONObject("playlists") ?: JSONObject()
        lastSupportNote = json.optLong("support_note")
        val waiting = json.optJSONArray("pending")?.let { array -> (0 until array.length()).mapNotNull { byKey[array.optString(it)] } }
        mutablePending.value = waiting.orEmpty()
        if (downloads < 0) {
            // Prvo pokretanje s dostignućima: dosadašnja uspjela preuzimanja se broje, ali bez naknadnih čestitki.
            downloads = History.items.value.count { !it.failed }
            MILESTONES.filter { it <= downloads }.forEach { earned.put("count$it", 0L) }
            save()
        }
    }

    val downloadCount: Int @Synchronized get() = downloads
    val bytes: Long @Synchronized get() = totalBytes
    @Synchronized fun earnedAt(key: String): Long? = if (earned.has(key)) earned.optLong(key) else null

    /** Link iz „Podijeli", widget, pločica ili „Pozovi prijatelja". */
    @Synchronized
    fun recordSource(key: String) {
        earn(key, System.currentTimeMillis())
        save()
    }

    @Synchronized
    fun recordDownload(done: FinishedDownload) {
        val now = System.currentTimeMillis()
        downloads++
        MILESTONES.filter { it <= downloads }.forEach { earn("count$it", now) }
        if (done.audio) earn("audio", now)
        if (done.clip) earn("clip", now)
        if (done.height >= 2160) earn("uhd", now)
        if (done.subtitles && !done.audio) earn("subtitles", now)
        if (done.duration >= MARATHON_SECONDS) earn("marathon", now)
        if (done.retried) earn("comeback", now)
        if (done.at.hour < 4) earn("night", now)
        siteOf(done.url).takeIf { it.isNotEmpty() && it !in sites }?.let { sites += it }
        if (sites.size >= 5) earn("sites5", now)
        if (sites.size >= 25) earn("sites25", now)
        totalBytes += done.size.coerceAtLeast(0)
        if (totalBytes >= GB) earn("gb1", now)
        if (totalBytes >= 10 * GB) earn("gb10", now)
        if (totalBytes >= 100 * GB) earn("gb100", now)
        if (done.playlistKey.isNotEmpty() && done.playlistSize >= PLAYLIST_MIN) {
            // Cijela lista: sve njene stavke uspjele (neuspjela stavka znači da broj nikad ne stigne do ukupnog).
            val ok = playlists.optInt(done.playlistKey) + 1
            playlists.put(done.playlistKey, ok)
            if (ok >= done.playlistSize) {
                earn("playlist", now)
                playlists.remove(done.playlistKey)
            }
        }
        countDay(done.at.toLocalDate(), now)
        save()
    }

    private fun countDay(today: LocalDate, now: Long) {
        val day = today.toString()
        if (firstDay.isEmpty() || runCatching { LocalDate.parse(firstDay) }.isFailure) firstDay = day
        if (lastDay != day) {
            streak = if (lastDay == today.minusDays(1).toString()) streak + 1 else 1
            lastDay = day
        }
        if (streak >= 7) earn("streak7", now)
        if (ChronoUnit.DAYS.between(LocalDate.parse(firstDay), today) >= 365) earn("anniversary", now)
    }

    private fun earn(key: String, now: Long) {
        if (earned.has(key)) return
        earned.put(key, now)
        byKey[key]?.let { badge -> mutablePending.value = mutablePending.value + badge }
    }

    /** Čestitka je prikazana: lista se prazni. */
    @Synchronized
    fun shown() {
        mutablePending.value = emptyList()
        save()
    }

    /** Poruka za prilog u čestitki najviše jednom dnevno (prvi dan zna donijeti više dostignuća). */
    @Synchronized
    fun supportNoteAllowed(): Boolean {
        val now = System.currentTimeMillis()
        if (now - lastSupportNote < SUPPORT_NOTE_EVERY) return false
        lastSupportNote = now
        save()
        return true
    }

    fun siteOf(url: String): String {
        val host = runCatching { java.net.URI(url.trim()).host }.getOrNull().orEmpty().lowercase().removePrefix("www.")
        val parts = host.split(".").filter { it.isNotEmpty() }
        return when {
            parts.size >= 3 && parts.last().length == 2 && parts[parts.size - 2] in SECOND_LEVEL ->
                parts.takeLast(3).joinToString(".")
            parts.size >= 2 -> parts.takeLast(2).joinToString(".")
            else -> host
        }
    }

    private fun save() {
        val context = app ?: return
        val json = JSONObject().put("earned", earned).put("downloads", downloads).put("bytes", totalBytes)
            .put("sites", JSONArray(sites)).put("first_day", firstDay).put("last_day", lastDay).put("streak", streak)
            .put("playlists", playlists).put("support_note", lastSupportNote)
            .put("pending", JSONArray(mutablePending.value.map { it.key }))
        prefs(context).edit().putString("stanje", json.toString()).apply()
    }

    private fun prefs(context: Context) = context.getSharedPreferences("dostignuca", Context.MODE_PRIVATE)
}
