package io.github.abnps.videodownload

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * Mjesečni i godišnji pregled kao na računaru (videodl/recap.py, Ahmed 2.11.2026): „Tvoj oktobar u Video Downloadu".
 * Pamte se samo brojke po mjesecu (broj, veličina, trajanje, sajtovi, dani u sedmici), bez naslova i linkova;
 * ništa se ne šalje. Prikaz pri prvom otvaranju u novom mjesecu (u januaru godišnji), ako je bilo bar 10 preuzimanja.
 */
data class RecapSummary(val period: String, val yearly: Boolean, val count: Int, val bytes: Long, val seconds: Long,
                        val longest: Long, val topSite: String, val busiestWeekday: Int) // 0 = ponedjeljak

object Recap {
    const val MIN_DOWNLOADS = 10
    private const val KEEP_MONTHS = 14

    private var months = JSONObject() // "2026-10" -> brojke
    private var lastShown = ""
    private var day = ""
    private var dayCount = 0
    private var dayBytes = 0L
    @Volatile var enabled = true
    private var app: Context? = null

    @Synchronized fun load(context: Context) {
        app = context.applicationContext
        val prefs = prefs(context)
        enabled = prefs.getBoolean("ukljuceno", true)
        val json = runCatching { JSONObject(prefs.getString("stanje", "{}") ?: "{}") }.getOrDefault(JSONObject())
        fromJson(json)
    }

    @Synchronized fun fromJson(json: JSONObject) {
        months = json.optJSONObject("months") ?: JSONObject()
        lastShown = json.optString("last_shown")
        day = json.optString("day")
        dayCount = json.optInt("day_count").coerceAtLeast(0)
        dayBytes = json.optLong("day_bytes").coerceAtLeast(0)
    }

    fun setEnabled(context: Context, value: Boolean) {
        enabled = value
        prefs(context).edit().putBoolean("ukljuceno", value).apply()
    }

    private fun key(date: LocalDate) = "%04d-%02d".format(date.year, date.monthValue)

    @Synchronized fun record(url: String, size: Long, seconds: Int, at: LocalDateTime = LocalDateTime.now()) {
        val month = months.optJSONObject(key(at.toLocalDate())) ?: JSONObject().also { months.put(key(at.toLocalDate()), it) }
        month.put("count", month.optInt("count") + 1)
        month.put("bytes", month.optLong("bytes") + size.coerceAtLeast(0))
        month.put("seconds", month.optLong("seconds") + seconds.coerceAtLeast(0))
        month.put("longest", maxOf(month.optLong("longest"), seconds.toLong()))
        val sites = month.optJSONObject("sites") ?: JSONObject().also { month.put("sites", it) }
        Achievements.siteOf(url).takeIf { it.isNotEmpty() }?.let { sites.put(it, sites.optInt(it) + 1) }
        val weekdays = month.optJSONArray("weekdays")?.takeIf { it.length() == 7 } ?: JSONArray(List(7) { 0 })
        val index = at.dayOfWeek.value - 1
        weekdays.put(index, weekdays.optInt(index) + 1)
        month.put("weekdays", weekdays)
        val today = at.toLocalDate().toString()
        if (day != today) { day = today; dayCount = 0; dayBytes = 0 }
        dayCount++
        dayBytes += size.coerceAtLeast(0)
        months.keys().asSequence().toList().sorted().dropLast(KEEP_MONTHS).forEach { months.remove(it) }
        save()
    }

    /** (broj, bajtovi) preuzetih danas, za red o podršci na kartici pauze. */
    @Synchronized fun today(date: LocalDate = LocalDate.now()): Pair<Int, Long> =
        if (day == date.toString()) dayCount to dayBytes else 0 to 0L

    /** Pregled koji treba pokazati danas (jednom po periodu); null = ništa. */
    @Synchronized fun due(today: LocalDate = LocalDate.now()): RecapSummary? {
        if (!enabled) return null
        val period = if (today.monthValue == 1) (today.year - 1).toString() else key(today.minusMonths(1))
        return summary(period)?.takeIf { lastShown != period }
    }

    @Synchronized fun summary(period: String): RecapSummary? {
        val yearly = period.length == 4
        val parts = months.keys().asSequence().filter { if (yearly) it.startsWith(period) else it == period }
            .mapNotNull { months.optJSONObject(it) }.toList()
        val count = parts.sumOf { it.optInt("count") }
        if (count < MIN_DOWNLOADS) return null
        val sites = mutableMapOf<String, Int>()
        val weekdays = IntArray(7)
        parts.forEach { month ->
            month.optJSONObject("sites")?.let { json -> json.keys().forEach { sites[it] = (sites[it] ?: 0) + json.optInt(it) } }
            month.optJSONArray("weekdays")?.let { array -> (0 until minOf(7, array.length())).forEach { weekdays[it] += array.optInt(it) } }
        }
        val top = sites.entries.sortedWith(compareByDescending<Map.Entry<String, Int>> { it.value }.thenBy { it.key })
            .firstOrNull()?.key.orEmpty()
        val busiest = (0 until 7).maxWith(compareBy<Int> { weekdays[it] }.thenByDescending { it })
        return RecapSummary(period, yearly, count, parts.sumOf { it.optLong("bytes") }, parts.sumOf { it.optLong("seconds") },
            parts.maxOf { it.optLong("longest") }, top, busiest)
    }

    @Synchronized fun shown(period: String) {
        lastShown = period
        save()
    }

    @Synchronized fun toJson(): JSONObject = JSONObject().put("months", months).put("last_shown", lastShown)
        .put("day", day).put("day_count", dayCount).put("day_bytes", dayBytes)

    private fun save() {
        app?.let { prefs(it).edit().putString("stanje", toJson().toString()).apply() }
    }

    private fun prefs(context: Context) = context.getSharedPreferences("pregled", Context.MODE_PRIVATE)
}
