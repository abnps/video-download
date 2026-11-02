package io.github.abnps.videodownload

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * „Podrži projekat" kao na računaru (videodl/support.py, Ahmed 20.10.2026: isti princip):
 * - traka na Početnoj poslije svakih 10 novih preuzimanja („Kasnije" je vraća tek poslije sljedećih 10);
 * - prozor najviše jednom sedmično, prvi put poslije 5 preuzimanja, nikad dok nešto preuzima;
 * - „Već sam podržao" (bez ikakve provjere uplate) gasi traku, prozor i poruku u čestitkama na 90 dana;
 * - poziv na prilog najviše jednom dnevno, zajedno s porukom u čestitki za dostignuće.
 * - red o podršci na kartici pauze, poruci 50/50 i mjesečnom pregledu (Ahmed 2.11.2026): najviše jednom sedmično,
 *   dvaput sedmično kad se aplikacija koristi često, nikad prije 10 preuzimanja; isti rok kao sedmični prozor.
 * Prilog ništa ne otključava i ništa ne blokira; sve se čuva samo na telefonu.
 */
data class SupportState(val bannerNext: Int = Support.BANNER_EVERY, val lastDialog: Long = 0, val snoozeUntil: Long = 0,
                        val lastNote: Long = 0, val recent: List<Long> = emptyList())

object Support {
    const val BANNER_EVERY = 10
    private const val DAY = 24 * 60 * 60 * 1000L
    private const val DIALOG_INTERVAL = 7 * DAY
    private const val SNOOZE = 90 * DAY
    private const val WEEK = 7 * DAY
    private const val NOTE_MIN_DOWNLOADS = 10
    private const val RECENT_MAX = 60

    private val mutable = MutableStateFlow(SupportState())
    val state: StateFlow<SupportState> = mutable
    private var app: Context? = null

    fun load(context: Context) {
        app = context.applicationContext
        val prefs = prefs(context)
        val recent = prefs.getString("nedavno", "").orEmpty().split(",").mapNotNull { it.toLongOrNull() }
            .filter { it > 0 }.takeLast(RECENT_MAX)
        mutable.value = SupportState(prefs.getInt("traka_sljedeca", BANNER_EVERY), prefs.getLong("prozor_zadnji", 0),
            prefs.getLong("podrzao_do", 0), prefs.getLong("red_zadnji", 0), recent)
    }

    fun snoozed(now: Long = System.currentTimeMillis()) = now < mutable.value.snoozeUntil

    fun showBanner(downloads: Int) = !snoozed() && downloads >= mutable.value.bannerNext

    /** Prozor samo kad ništa ne radi, poslije bar 5 preuzimanja, najviše jednom sedmično i ne isti dan kad je čestitka
     *  već pozvala na prilog (jedan poziv dnevno). */
    fun shouldShowDialog(downloads: Int, busy: Boolean, now: Long = System.currentTimeMillis()): Boolean {
        val s = mutable.value
        if (busy || snoozed(now) || downloads < BANNER_EVERY / 2) return false
        if (now - Achievements.lastSupportNoteAt < DAY) return false
        val last = maxOf(s.lastDialog, s.lastNote) // red na kartici se računa kao poziv
        return last == 0L || now - last >= DIALOG_INTERVAL
    }

    /** Novo uspjelo preuzimanje (za „često": zadnjih 60 vremena, ništa drugo). */
    fun countDownload(now: Long = System.currentTimeMillis()) =
        save(mutable.value.let { it.copy(recent = (it.recent + now).takeLast(RECENT_MAX)) })

    /** Često = u zadnjih 7 dana preuzimanja u bar 3 različita dana ili bar 30 preuzimanja. */
    fun frequent(now: Long = System.currentTimeMillis()): Boolean {
        val week = mutable.value.recent.filter { now - it in 0 until WEEK }
        val days = week.map { java.time.Instant.ofEpochMilli(it).atZone(java.time.ZoneId.systemDefault()).toLocalDate() }.toSet()
        return days.size >= 3 || week.size >= 30
    }

    /** Smije li kartica (pauza, 50/50, pregled) imati red o podršci. */
    fun noteAllowed(downloads: Int, now: Long = System.currentTimeMillis()): Boolean {
        val s = mutable.value
        if (snoozed(now) || downloads < NOTE_MIN_DOWNLOADS) return false
        val interval = if (frequent(now)) DIALOG_INTERVAL / 2 else DIALOG_INTERVAL
        return now - maxOf(s.lastDialog, s.lastNote) >= interval
    }

    fun noteShown(now: Long = System.currentTimeMillis()) = save(mutable.value.copy(lastNote = now))

    /** Poruka za prilog u čestitki: ne poslije „Već sam podržao" i ne isti dan kad je bio sedmični prozor. */
    fun noteAllowedInAchievement(now: Long = System.currentTimeMillis()) =
        !snoozed(now) && now - mutable.value.lastDialog >= DAY

    fun bannerLater(downloads: Int) = save(mutable.value.copy(bannerNext = downloads + BANNER_EVERY))

    fun dialogShown(now: Long = System.currentTimeMillis()) = save(mutable.value.copy(lastDialog = now))

    fun alreadySupported(downloads: Int, now: Long = System.currentTimeMillis()) =
        save(mutable.value.copy(snoozeUntil = now + SNOOZE, bannerNext = downloads + BANNER_EVERY))

    private fun save(new: SupportState) {
        mutable.value = new
        app?.let {
            prefs(it).edit().putInt("traka_sljedeca", new.bannerNext).putLong("prozor_zadnji", new.lastDialog)
                .putLong("podrzao_do", new.snoozeUntil).putLong("red_zadnji", new.lastNote)
                .putString("nedavno", new.recent.joinToString(",")).apply()
        }
    }

    private fun prefs(context: Context) = context.getSharedPreferences("podrska", Context.MODE_PRIVATE)
}
