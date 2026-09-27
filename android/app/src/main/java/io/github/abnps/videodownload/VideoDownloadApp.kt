package io.github.abnps.videodownload

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/** Pokreće Python (yt-dlp) jednom po procesu i pravi kanal obavještenja za preuzimanja. */
class VideoDownloadApp : Application() {
    override fun onCreate() {
        super.onCreate()
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        val channel = NotificationChannel(
            CHANNEL_DOWNLOADS, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW,
        )
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_DOWNLOADS = "downloads"
    }
}
