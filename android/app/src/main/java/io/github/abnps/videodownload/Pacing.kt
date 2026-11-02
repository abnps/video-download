package io.github.abnps.videodownload

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlin.random.Random

/**
 * Zaštita od blokade kao na računaru (videodl/pacing.py, Ahmed 2.11.2026): YouTube, Instagram, TikTok, Facebook i X
 * privremeno blokiraju kad se skine mnogo videa zaredom. Od 10. preuzimanja zaredom s istog sajta kratak razmak
 * (2–5 s, od 25. 5–10 s, od 50. 8–15 s), svakih 25 predah od 30–60 s, a kad sajt ipak blokira (429, „nisi bot")
 * čeka se 5, 10 pa 15 minuta i nastavlja samo. Poslije blokade 7 dana sve kreće ranije i traje 1,5× duže.
 * Na telefonu preuzimanja ionako idu jedno za drugim, pa nema ograničenja istovremenih.
 */
data class Pause(val family: String, val kind: String, val millis: Long) {
    val card get() = kind != "gap" // predah i blokada: kartica; razmak: samo tekst na kartici posla
}

/** Kartica na ekranu Preuzimanja: pauza traje do `until` (elapsedRealtime). */
data class PauseCard(val pause: Pause, val until: Long, val support: String?, val tip: Int)

object Pacing {
    val FAMILIES = mapOf(
        "youtube.com" to "youtube", "youtu.be" to "youtube", "youtube-nocookie.com" to "youtube",
        "instagram.com" to "instagram", "tiktok.com" to "tiktok",
        "facebook.com" to "facebook", "fb.watch" to "facebook", "x.com" to "x", "twitter.com" to "x",
    )
    val NAMES = mapOf("youtube" to "YouTube", "instagram" to "Instagram", "tiktok" to "TikTok",
        "facebook" to "Facebook", "x" to "X")
    private val SLOW = setOf("instagram", "tiktok")
    private const val IDLE_RESET = 15 * 60 * 1000L
    private val THRESHOLDS = intArrayOf(10, 25, 50)
    private val LEARNED_THRESHOLDS = intArrayOf(5, 13, 25)
    private val GAPS = arrayOf(2.0 to 5.0, 5.0 to 10.0, 8.0 to 15.0)
    private const val BREAK_FROM = 30.0
    private const val BREAK_TO = 60.0
    const val LEARN_MILLIS = 7 * 24 * 60 * 60 * 1000L
    val BLOCK_WAITS = longArrayOf(5 * 60_000L, 10 * 60_000L, 15 * 60_000L)
    private val BLOCK = Regex("http error 429|too many requests|confirm you.?re not a bot|not a robot", RegexOption.IGNORE_CASE)

    /** Satovi se mogu zamijeniti u testovima (JVM nema SystemClock). */
    var clock: () -> Long = { android.os.SystemClock.elapsedRealtime() }
    var wall: () -> Long = { System.currentTimeMillis() }
    var random: Random = Random.Default

    @Volatile var enabled = true
    @Volatile var learnedUntil = 0L

    private class State(var streak: Int = 0, var breaks: Int = 0, var lastSeen: Long? = null, var readyAt: Long = 0,
                        var last: Pause? = null)
    private val states = mutableMapOf<String, State>()

    /** Posljednja zakazana pauza porodice (vrsta: razmak, predah ili blokada). */
    @Synchronized fun lastPause(family: String?): Pause? = family?.let { states[it]?.last }

    private val mutableCard = MutableStateFlow<PauseCard?>(null)
    val card: StateFlow<PauseCard?> = mutableCard
    private var app: Context? = null

    fun load(context: Context) {
        app = context.applicationContext
        val prefs = prefs(context)
        enabled = prefs.getBoolean("ukljuceno", true)
        learnedUntil = prefs.getLong("naucio_do", 0)
    }

    fun setEnabled(context: Context, value: Boolean) {
        enabled = value
        prefs(context).edit().putBoolean("ukljuceno", value).apply()
    }

    fun familyOf(url: String): String? = FAMILIES[Achievements.siteOf(url)]

    fun isBlockError(message: String?) = BLOCK.containsMatchIn(message.orEmpty())

    private fun learned() = wall() < learnedUntil
    private fun thresholds() = if (learned()) LEARNED_THRESHOLDS else THRESHOLDS
    private fun scale(family: String) = (if (learned()) 1.5 else 1.0) * (if (family in SLOW) 1.5 else 1.0)

    @Synchronized fun remaining(family: String?): Long =
        family?.let { states[it] }?.let { (it.readyAt - clock()).coerceAtLeast(0) } ?: 0

    private fun freshStreak(state: State) =
        if (state.lastSeen == null || clock() - state.lastSeen!! > IDLE_RESET) 0 else state.streak

    @Synchronized fun started(family: String?) {
        family ?: return
        val state = states.getOrPut(family) { State() }
        if (freshStreak(state) == 0) { state.streak = 0; state.breaks = 0 }
        state.streak++
        state.lastSeen = clock()
    }

    /** Preuzimanje s porodice je gotovo: razmak ili predah prije sljedećeg; null = bez čekanja. */
    @Synchronized fun finished(family: String?): Pause? {
        val state = family?.let { states[it] } ?: return null
        val now = clock()
        state.lastSeen = now
        if (!enabled) return null
        val (first, second, third) = thresholds().let { Triple(it[0], it[1], it[2]) }
        val pause = if (state.streak / second > state.breaks) {
            state.breaks = state.streak / second
            Pause(family, "break", (random.nextDouble(BREAK_FROM, BREAK_TO) * scale(family) * 1000).toLong())
        } else {
            val following = state.streak + 1
            val level = when {
                following >= third -> 2
                following >= second -> 1
                following >= first -> 0
                else -> return null
            }
            val (from, to) = GAPS[level]
            Pause(family, "gap", (random.nextDouble(from, to) * scale(family) * 1000).toLong())
        }
        state.readyAt = maxOf(state.readyAt, now + pause.millis)
        state.last = pause
        return pause
    }

    /** Sajt je blokirao posao `attempt`-ti put: čeka se i nastavlja; null = odustati (obična greška). */
    @Synchronized fun blocked(family: String, attempt: Int): Pause? {
        learnedUntil = wall() + LEARN_MILLIS
        app?.let { prefs(it).edit().putLong("naucio_do", learnedUntil).apply() }
        if (attempt !in 1..BLOCK_WAITS.size) return null
        val state = states.getOrPut(family) { State() }
        val now = clock()
        state.lastSeen = now
        val pause = Pause(family, "block", BLOCK_WAITS[attempt - 1])
        state.readyAt = maxOf(state.readyAt, now + pause.millis)
        state.last = pause
        return pause
    }

    /** „Nastavi odmah" (jedna porodica) ili zaustavljanje (sve). */
    @Synchronized fun skip(family: String? = null) {
        states.forEach { (name, state) -> if (family == null || name == family) state.readyAt = 0 }
        if (family == null || mutableCard.value?.pause?.family == family) mutableCard.value = null
    }

    fun showCard(card: PauseCard?) {
        mutableCard.value = card
    }

    @Synchronized fun reset() {
        states.clear()
        mutableCard.value = null
    }

    private fun prefs(context: Context) = context.getSharedPreferences("zastita", Context.MODE_PRIVATE)
}
