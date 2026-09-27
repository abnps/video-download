package io.github.abnps.videodownload

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import android.os.SystemClock
import com.chaquo.python.PyException
import com.chaquo.python.Python
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Preuzimanje u prvom planu (obavještenje s napretkom i dugmetom Zaustavi), da ga Android — i Samsungovo
 * uspavljivanje aplikacija — ne ugasi kad korisnik izađe iz aplikacije. Poslovi idu jedan za drugim.
 */
class DownloadService : Service() {
    private val worker = Executors.newSingleThreadExecutor()
    private val cancelled = AtomicBoolean(false)
    private var pending = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_CANCEL) {
            synchronized(this) {
                if (pending == 0) {
                    // Ništa ne radi (npr. zaostalo obavještenje): samo ga skloni.
                    getSystemService(NotificationManager::class.java).cancel(NOTIFICATION_ID)
                    stopSelf()
                } else {
                    cancelled.set(true)
                    notify(progressNotification(getString(R.string.status_stopping), null))
                }
            }
            return START_NOT_STICKY
        }
        val url = intent?.getStringExtra(EXTRA_URL) ?: return START_NOT_STICKY
        val isAudio = intent.getBooleanExtra(EXTRA_AUDIO, false)
        startForeground(NOTIFICATION_ID, progressNotification(getString(R.string.status_reading), null),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        synchronized(this) { pending++ }
        worker.execute { run(url, isAudio) }
        return START_NOT_STICKY
    }

    private fun run(url: String, isAudio: Boolean) {
        cancelled.set(false)
        DownloadState.set(DownloadStatus.Reading)
        val work = File(cacheDir, "preuzimanje-${SystemClock.elapsedRealtime()}").apply { mkdirs() }
        try {
            val listener = Listener()
            val result = Python.getInstance().getModule("vd_core")
                .callAttr("download", url, if (isAudio) "audio" else "video", work.absolutePath, listener).asList()
            val title = result[0].toString()
            val name = result[1].toString()
            val first = File(result[2].toString())
            val second = result[3].toString().takeIf { it.isNotEmpty() }?.let(::File)
            DownloadState.set(DownloadStatus.Saving)
            notify(progressNotification(getString(R.string.status_saving), null))
            // Slika i zvuk stigli odvojeno: spajaju se u jedan MP4 bez ponovnog kodiranja.
            val file = if (second != null) {
                File(work, "$name.mp4").also { Muxer.merge(first, second, it) }
            } else {
                File(work, "$name.${first.extension}").also { first.renameTo(it) }
            }
            val uri = MediaSaver.save(this, file, isAudio)
            DownloadState.set(DownloadStatus.Done(title, uri, isAudio))
            notifyFinished(getString(R.string.status_done, title), openIntent(uri, isAudio))
        } catch (error: PyException) {
            if (cancelled.get()) {
                DownloadState.set(DownloadStatus.Cancelled)
                notifyFinished(getString(R.string.status_cancelled), null)
            } else {
                val message = cleanError(error.message)
                DownloadState.set(DownloadStatus.Failed(message))
                notifyFinished(getString(R.string.status_failed, message), null)
            }
        } catch (error: Exception) {
            val message = error.message ?: error.javaClass.simpleName
            DownloadState.set(DownloadStatus.Failed(message))
            notifyFinished(getString(R.string.status_failed, message), null)
        } finally {
            work.deleteRecursively() // privremeni fajlovi nikad ne ostaju
            synchronized(this) {
                pending--
                if (pending == 0) {
                    stopForeground(STOP_FOREGROUND_REMOVE) // napredak nestaje; ostaje samo obavještenje o kraju
                    stopSelf()
                }
            }
        }
    }

    /** Poziva ga Python (vd_core.download) iz iste niti. */
    inner class Listener {
        private var lastUpdate = 0L

        fun onProgress(fraction: Double, done: Long, total: Long) {
            val now = SystemClock.elapsedRealtime()
            if (now - lastUpdate < 500) return // obavještenje najviše dvaput u sekundi
            lastUpdate = now
            val value = fraction.takeIf { it >= 0 }?.toFloat()
            DownloadState.set(DownloadStatus.Downloading(value))
            val percent = ((value ?: 0f) * 100).toInt()
            notify(progressNotification(getString(R.string.status_downloading, percent), value))
        }

        fun isCancelled(): Boolean = cancelled.get()
    }

    private fun progressNotification(text: String, fraction: Float?): Notification {
        val cancel = PendingIntent.getService(
            this, 1, Intent(this, DownloadService::class.java).setAction(ACTION_CANCEL), PendingIntent.FLAG_IMMUTABLE,
        )
        return Notification.Builder(this, VideoDownloadApp.CHANNEL_DOWNLOADS)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setProgress(100, ((fraction ?: 0f) * 100).toInt(), fraction == null)
            .setContentIntent(appIntent())
            .addAction(Notification.Action.Builder(null, getString(R.string.cancel), cancel).build())
            .build()
    }

    private fun notifyFinished(text: String, open: PendingIntent?) {
        val notification = Notification.Builder(this, VideoDownloadApp.CHANNEL_DOWNLOADS)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(open ?: appIntent())
            .build()
        getSystemService(NotificationManager::class.java).notify(DONE_NOTIFICATION_ID, notification)
    }

    private fun notify(notification: Notification) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, notification)
    }

    private fun appIntent(): PendingIntent = PendingIntent.getActivity(
        this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
    )

    private fun openIntent(uri: android.net.Uri, isAudio: Boolean): PendingIntent = PendingIntent.getActivity(
        this, 2,
        Intent(Intent.ACTION_VIEW).setDataAndType(uri, if (isAudio) "audio/*" else "video/*")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION),
        PendingIntent.FLAG_IMMUTABLE,
    )

    override fun onDestroy() {
        worker.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val NOTIFICATION_ID = 1
        private const val DONE_NOTIFICATION_ID = 2
        private const val EXTRA_URL = "url"
        private const val EXTRA_AUDIO = "audio"
        private const val ACTION_CANCEL = "cancel"

        fun start(context: Context, url: String, isAudio: Boolean) {
            context.startForegroundService(
                Intent(context, DownloadService::class.java).putExtra(EXTRA_URL, url).putExtra(EXTRA_AUDIO, isAudio),
            )
        }

        /** „ERROR: [youtube] abc: Video unavailable" → „Video unavailable" (razumljive poruke dolaze kasnije). */
        fun cleanError(message: String?): String {
            val line = message.orEmpty().lines().lastOrNull { it.isNotBlank() }.orEmpty()
            return line.substringAfter("DownloadError: ").removePrefix("ERROR: ")
                .replace(Regex("^\\[[^]]+] [^:]+: "), "").ifBlank { "?" }
        }
    }
}
