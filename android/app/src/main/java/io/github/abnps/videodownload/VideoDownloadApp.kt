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
        History.load(this)
        Downloads.load(this)
        runCatching { Python.getInstance().getModule("vd_core").callAttr("clean_diagnostics", cacheDir.absolutePath) }
        // 1440p/4K (AV1) samo gdje se sigurno spaja i glatko gleda: Android 14+ i hardverski AV1 dekoder.
        runCatching { Python.getInstance().getModule("vd_core").callAttr("set_av1", supportsAv1()) }
        val staleWork = cacheDir.listFiles()?.filter { it.isDirectory && it.name.startsWith("preuzimanje-") }.orEmpty()
        Thread { staleWork.forEach { it.deleteRecursively() } }.start()
        // Za sajtove koji traže pravi preglednik (TikTok): Chrome za računar, iste verzije kao Chrome ovog telefona.
        // Mobilni identitet TikTok odbije („Video not available") — isto kao yt-dlp na računaru, provjereno 27.9.2026.
        runCatching {
            val version = Regex("""Chrome/(\d+)""").find(android.webkit.WebSettings.getDefaultUserAgent(this))
                ?.groupValues?.get(1) ?: "140"
            NativeHttp.userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                "(KHTML, like Gecko) Chrome/$version.0.0.0 Safari/537.36"
        }
        val channel = NotificationChannel(
            CHANNEL_DOWNLOADS, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW,
        )
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun supportsAv1(): Boolean = android.os.Build.VERSION.SDK_INT >= 34 &&
        android.media.MediaCodecList(android.media.MediaCodecList.REGULAR_CODECS).codecInfos.any { codec ->
            !codec.isEncoder && codec.isHardwareAccelerated && codec.supportedTypes.any { it.equals("video/av01", true) }
        }

    companion object {
        const val CHANNEL_DOWNLOADS = "downloads"
    }
}
