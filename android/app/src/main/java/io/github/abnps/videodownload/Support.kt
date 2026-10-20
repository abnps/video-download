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
 * Prilog ništa ne otključava i ništa ne blokira; sve se čuva samo na telefonu.
 */
data class SupportState(val bannerNext: Int = Support.BANNER_EVERY, val lastDialog: Long = 0, val snoozeUntil: Long = 0)

object Support {
    const val BANNER_EVERY = 10
    private const val DAY = 24 * 60 * 60 * 1000L
    private const val DIALOG_INTERVAL = 7 * DAY
    private const val SNOOZE = 90 * DAY

    private val mutable = MutableStateFlow(SupportState())
    val state: StateFlow<SupportState> = mutable
    private var app: Context? = null

    fun load(context: Context) {
        app = context.applicationContext
        val prefs = prefs(context)
        mutable.value = SupportState(prefs.getInt("traka_sljedeca", BANNER_EVERY), prefs.getLong("prozor_zadnji", 0),
            prefs.getLong("podrzao_do", 0))
    }

    fun snoozed(now: Long = System.currentTimeMillis()) = now < mutable.value.snoozeUntil

    fun showBanner(downloads: Int) = !snoozed() && downloads >= mutable.value.bannerNext

    /** Prozor samo kad ništa ne radi, poslije bar 5 preuzimanja, najviše jednom sedmično i ne isti dan kad je čestitka
     *  već pozvala na prilog (jedan poziv dnevno). */
    fun shouldShowDialog(downloads: Int, busy: Boolean, now: Long = System.currentTimeMillis()): Boolean {
        val s = mutable.value
        if (busy || snoozed(now) || downloads < BANNER_EVERY / 2) return false
        if (now - Achievements.lastSupportNoteAt < DAY) return false
        return s.lastDialog == 0L || now - s.lastDialog >= DIALOG_INTERVAL
    }

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
                .putLong("podrzao_do", new.snoozeUntil).apply()
        }
    }

    private fun prefs(context: Context) = context.getSharedPreferences("podrska", Context.MODE_PRIVATE)
}
