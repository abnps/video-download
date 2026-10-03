package io.github.abnps.videodownload

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.Uri
import android.os.IBinder
import android.os.SystemClock
import com.chaquo.python.Python
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors

/**
 * Preuzimanja u prvom planu (obavještenje s napretkom i dugmetom Zaustavi), da ih Android — i Samsungovo
 * uspavljivanje aplikacija — ne ugasi kad korisnik izađe iz aplikacije. Poslovi idu jedan za drugim; svaki se
 * može zaustaviti posebno (✕ na ekranu Preuzimanja ili Zaustavi u obavještenju za onaj koji radi).
 */
class DownloadService : Service() {
    private val worker = Executors.newSingleThreadExecutor()
    private val cancelled: MutableSet<Long> = ConcurrentHashMap.newKeySet()
    @Volatile private var running: Long? = null
    private var pending = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_CANCEL) {
            val id = intent.getLongExtra(EXTRA_ID, running ?: -1)
            synchronized(this) {
                if (pending == 0) {
                    // Ništa ne radi (npr. zaostalo obavještenje): samo ga skloni.
                    getSystemService(NotificationManager::class.java).cancel(NOTIFICATION_ID)
                    stopSelf()
                } else {
                    cancelled += id
                    if (id == running) notify(progressNotification(getString(R.string.status_stopping), null))
                }
            }
            return START_NOT_STICKY
        }
        val job = intent?.getBundleExtra(EXTRA_JOB)?.let(Job::fromBundle) ?: return START_NOT_STICKY
        startForeground(NOTIFICATION_ID, progressNotification(job.title, null), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        synchronized(this) { pending++ }
        Downloads.add(job)
        worker.execute { run(job) }
        return START_NOT_STICKY
    }

    private fun run(job: Job) {
        var waitsForAdult = false
        running = job.id
        val work = File(cacheDir, "preuzimanje-${job.id}-${System.nanoTime()}").apply { mkdirs() }
        try {
            if (job.id in cancelled) throw CancelledHere()
            Downloads.lastError.value = null
            Downloads.update(job.id) { it.copy(phase = Phase.READING) }
            notify(progressNotification(job.title, null))
            // Kolačići Instagram prijave (ako postoji) idu u privremeni fajl u `work`, koji se briše na kraju.
            val cookies = SiteLogin.cookieFile(work)
            val result = Python.getInstance().getModule("vd_core").callAttr(
                "download", job.url, if (job.isAudio) "audio" else "video", work.absolutePath, Listener(job), job.height,
                cookies, job.adultOk,
            ).asList()
            val name = result[1].toString()
            val first = File(result[2].toString())
            val second = result[3].toString().takeIf { it.isNotEmpty() }?.let(::File)
            Downloads.update(job.id) { it.copy(phase = Phase.SAVING) }
            notify(progressNotification(getString(R.string.status_saving), null))
            // Slika i zvuk stigli odvojeno: spajaju se u jedan MP4 bez ponovnog kodiranja.
            var file = if (second != null) {
                File(work, "$name.mp4").also { Muxer.merge(first, second, it) { job.id in cancelled } }
            } else {
                File(work, "$name.${first.extension}").also { check(first.renameTo(it)) { "Privremeni fajl nije premješten" } }
            }
            if (job.isAudio && job.label == MP3_LABEL) {
                // MP3 se pravi na telefonu iz preuzetog M4A (LAME, 192 kbps); M4A ostaje samo privremeno.
                Downloads.update(job.id) { it.copy(phase = Phase.CONVERTING, fraction = 0f, done = 0, total = 0) }
                notify(progressNotification(getString(R.string.status_converting), null))
                val mp3 = File(work, "$name.mp3")
                var last = 0L
                Mp3.convert(file, mp3, { job.id in cancelled }) { fraction ->
                    val now = SystemClock.elapsedRealtime()
                    if (now - last >= 400) {
                        last = now
                        Downloads.update(job.id) { it.copy(fraction = fraction) }
                        notify(progressNotification("${job.title} · ${getString(R.string.status_converting)} · ${(fraction * 100).toInt()}%", fraction))
                    }
                }
                file.delete()
                file = mp3
                Downloads.update(job.id) { it.copy(phase = Phase.SAVING) }
                notify(progressNotification(getString(R.string.status_saving), null))
            }
            if (job.id in cancelled) throw CancelledHere()
            val size = file.length()
            val uri = MediaSaver.save(this, file, job.isAudio, Settings.location(this)) { job.id in cancelled }
            if (job.id in cancelled) {
                contentResolver.delete(uri, null, null)
                throw CancelledHere()
            }
            History.add(HistoryItem(job.id, job.title.ifBlank { result[0].toString() }, uri.toString(), job.isAudio,
                formatLabel(job, file.extension), size, job.duration, job.thumbnail, System.currentTimeMillis(),
                adult = job.adult))
            notifyFinished(getString(R.string.status_done, job.title), openIntent(uri, job.isAudio))
            // Kao na računaru: traka zazeleni, kratko pulsira, pa kartica nestane.
            Downloads.update(job.id) { it.copy(phase = Phase.DONE, fraction = 1f) }
            Thread.sleep(1100)
        } catch (error: Exception) {
            if (job.id in cancelled || error is CancelledHere || error is InterruptedException) {
                notifyFinished(getString(R.string.status_cancelled), null)
            } else if ("ADULT_CONFIRM" in error.message.orEmpty() && Parental.enabled(this)) {
                // Roditeljska zaštita: 18+ se ne preuzima i ne čeka potvrdu.
                notifyFinished(getString(R.string.status_failed, getString(R.string.parental_blocked)), null)
            } else if ("ADULT_CONFIRM" in error.message.orEmpty()) {
                // Video za odrasle bez potvrde: čeka na listi (dugme „Imam 18+"), ostali poslovi idu dalje.
                waitsForAdult = true
                Downloads.update(job.id) { it.copy(job = job.copy(adult = true, adultOk = false), phase = Phase.NEEDS_ADULT) }
                notifyFinished(getString(R.string.adult_waiting, job.title), null)
            } else {
                val message = cleanError(this, error.message)
                Downloads.lastError.value = message
                notifyFinished(getString(R.string.status_failed, message), null)
            }
        } finally {
            work.deleteRecursively() // privremeni fajlovi nikad ne ostaju
            cancelled -= job.id
            running = null
            if (!waitsForAdult) Downloads.remove(job.id)
            synchronized(this) {
                pending--
                if (pending == 0) {
                    stopForeground(STOP_FOREGROUND_REMOVE) // napredak nestaje; ostaje samo obavještenje o kraju
                    stopSelf()
                }
            }
        }
    }

    private class CancelledHere : Exception()

    private fun formatLabel(job: Job, extension: String): String =
        if (job.isAudio || job.label.isBlank() || job.label.equals(extension, ignoreCase = true)) extension.uppercase()
        else "${extension.uppercase()} • ${job.label}" // bez „MP4 • MP4" kad sajt ne javi visinu (Instagram)

    /** Poziva ga Python (vd_core.download) iz iste niti. */
    inner class Listener(private val job: Job) {
        private var lastUpdate = 0L

        fun onProgress(fraction: Double, done: Long, total: Long, speed: Double, eta: Long, audioPart: Boolean) {
            val now = SystemClock.elapsedRealtime()
            if (now - lastUpdate < 400) return // ekran i obavještenje najviše ~2,5 puta u sekundi
            lastUpdate = now
            val value = fraction.takeIf { it >= 0 }?.toFloat()
            Downloads.update(job.id) {
                it.copy(phase = Phase.DOWNLOADING, fraction = value, done = done, total = total, speed = speed, eta = eta,
                    audioPart = audioPart)
            }
            val percent = ((value ?: 0f) * 100).toInt()
            // Kao na računaru: „Preuzimanje 45% · 3,2 MB/s · još 0:12"
            val details = listOfNotNull(getString(R.string.status_downloading, percent), formatSpeed(speed),
                formatEta(this@DownloadService, eta)).joinToString(" · ")
            notify(progressNotification("${job.title} · $details", value))
        }

        fun isCancelled(): Boolean = job.id in cancelled
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
        this, 0, Intent(this, MainActivity::class.java).putExtra(MainActivity.EXTRA_OPEN_DOWNLOADS, true),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    private fun openIntent(uri: Uri, isAudio: Boolean): PendingIntent = PendingIntent.getActivity(
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
        /** Oznaka posla „zvuk kao MP3" (ekran kvaliteta); bez nje zvuk ostaje M4A. */
        const val MP3_LABEL = "MP3"
        private const val NOTIFICATION_ID = 1
        private const val DONE_NOTIFICATION_ID = 2
        private const val EXTRA_JOB = "job"
        private const val EXTRA_ID = "id"
        private const val ACTION_CANCEL = "cancel"

        fun start(context: Context, job: Job) {
            context.startForegroundService(Intent(context, DownloadService::class.java).putExtra(EXTRA_JOB, job.toBundle()))
        }

        fun cancel(context: Context, id: Long) {
            context.startService(Intent(context, DownloadService::class.java).setAction(ACTION_CANCEL).putExtra(EXTRA_ID, id))
        }

        /** Greška može sadržati potpisan URL, kolačić ili tekst stranice: prikazujemo samo poznate kategorije. */
        fun cleanError(context: Context, message: String?): String {
            val raw = message.orEmpty().lowercase()
            return when {
                "audio_unavailable" in raw -> context.getString(R.string.audio_unavailable)
                "unsupported url" in raw -> context.getString(R.string.error_unsupported)
                "sign in" in raw || "login" in raw || "cookies" in raw -> context.getString(R.string.error_login)
                else -> {
                    val status = Regex("\\bhttp(?: error)?[ :]+([45]\\d\\d)\\b").find(raw)?.groupValues?.get(1)
                    when {
                        status != null -> context.getString(R.string.error_http, status)
                        "timed out" in raw || "timeout" in raw || "connection" in raw || "network" in raw ->
                            context.getString(R.string.error_network)
                        else -> context.getString(R.string.error_generic)
                    }
                }
            }
        }
    }
}
