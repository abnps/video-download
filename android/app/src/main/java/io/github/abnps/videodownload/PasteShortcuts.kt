package io.github.abnps.videodownload

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.os.Build
import android.service.quicksettings.TileService
import android.widget.RemoteViews

/**
 * „Zalijepi i preuzmi" van aplikacije (plan 1.0, Ahmed 3.10.2026): widget na početnom ekranu i pločica u Brzim
 * podešavanjima. Od Androida 10 međuspremnik smije čitati samo aplikacija na ekranu, pa oba samo otvore
 * MainActivity s EXTRA_PASTE; ona zalijepi i pročita link čim dobije fokus.
 */
object PasteShortcut {
    fun intent(context: Context): Intent = Intent(context, MainActivity::class.java)
        .putExtra(MainActivity.EXTRA_PASTE, true)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)

    fun pending(context: Context): PendingIntent = PendingIntent.getActivity(context, 7, intent(context),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
}

class PasteWidget : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        val views = RemoteViews(context.packageName, R.layout.widget_paste).apply {
            setOnClickPendingIntent(R.id.widget_root, PasteShortcut.pending(context))
        }
        ids.forEach { manager.updateAppWidget(it, views) }
    }
}

class PasteTile : TileService() {
    override fun onClick() {
        super.onClick()
        if (Build.VERSION.SDK_INT >= 34) {
            startActivityAndCollapse(PasteShortcut.pending(this))
        } else {
            @Suppress("DEPRECATION", "StartActivityAndCollapseDeprecated")
            startActivityAndCollapse(PasteShortcut.intent(this))
        }
    }
}
