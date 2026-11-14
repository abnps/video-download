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
import com.chaquo.python.PyObject
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
    // Grupa poslova dok usluga radi, za „Gotovo: 50/50 videa" (Ahmed 2.11.2026); mijenja ih samo radna nit.
    private var batchDone = 0
    private var batchOther = 0 // neuspjelo, prekinuto ili čeka potvrdu 18+
    private var batchBytes = 0L

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
        val family = Pacing.familyOf(job.url)
        val work = File(cacheDir, "preuzimanje-${job.id}-${System.nanoTime()}").apply { mkdirs() }
        try {
            if (job.id in cancelled) throw CancelledHere()
            waitForPause(job) // razmak ili predah zaštite od blokade prije ovog posla (Pacing.kt)
            Pacing.started(family)
            Downloads.lastError.value = null
            Downloads.update(job.id) { it.copy(phase = Phase.READING) }
            notify(progressNotification(job.title, null))
            // Kolačići Instagram prijave (ako postoji) idu u privremeni fajl u `work`, koji se briše na kraju.
            val cookies = SiteLogin.cookieFile(work, job.url)
            val result = downloadWithPauses(job, family) {
                Python.getInstance().getModule("vd_core").callAttr(
                    "download", job.url, if (!job.isAudio) "video" else if (job.label == MP3_LABEL) "mp3" else "audio", work.absolutePath, Listener(job), job.height,
                    cookies, job.adultOk, if (job.subtitles && !job.isAudio) Links.language() else "", job.mute && !job.isAudio,
                ).asList()
            }
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
            if (job.mute && !job.isAudio) {
                // Sajt nudi samo video sa zvukom (Instagram, TikTok…): zvuk se skida bez ponovnog kodiranja.
                // Kad je stigla samo slika, ovo je obična kopija od par sekundi.
                val silent = File(work, "${file.nameWithoutExtension}.silent.${file.extension}")
                Muxer.dropAudio(file, silent) { job.id in cancelled }
                file.delete()
                check(silent.renameTo(file)) { "Privremeni fajl nije premješten" }
            }
            if (job.hasClip) {
                // Isječak bez ffmpeg-a (Muxer.trim); ime kao na računaru: „Naslov [id] (2.30–6.10).mp4".
                Downloads.update(job.id) { it.copy(phase = Phase.SAVING) }
                notify(progressNotification(getString(R.string.status_saving), null))
                val clip = File(work, "$name (${clipLabel(job.clipStart)}–${clipLabel(job.clipEnd)}).${file.extension}")
                Muxer.trim(file, clip, job.clipStart * 1_000_000L, job.clipEnd * 1_000_000L) { job.id in cancelled }
                file.delete()
                file = clip
            }
            if (job.isAudio && job.label == MP3_LABEL) {
                // MP3 se pravi na telefonu iz preuzetog M4A, ili iz videa kad sajt nema poseban zvuk (LAME, 192 kbps);
                // preuzeti fajl ostaje samo privremeno.
                Downloads.update(job.id) { it.copy(phase = Phase.CONVERTING, fraction = 0f, done = 0, total = 0) }
                notify(progressNotification(getString(R.string.status_converting), null))
                val mp3 = File(work, "${file.nameWithoutExtension}.mp3")
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
            val height = if (job.isAudio) 0 else videoHeight(file) // stvarna visina (za dostignuće „4K")
            var subtitleFiles = result.getOrNull(4)?.toString().orEmpty().split("|").filter { it.isNotEmpty() }.map(::File)
                .filter { it.isFile }
            if (job.burnSubtitles && subtitleFiles.isNotEmpty() && !job.isAudio) {
                // Titl upisan u sliku (SubtitleBurner): jedan jezik, video se kodira ponovo. Ne uspije li, titl ostaje
                // pored videa kao do sada.
                val chosen = Subtitles.pick(subtitleFiles, Links.language())
                if (chosen != null) {
                    Downloads.update(job.id) { it.copy(phase = Phase.BURNING, fraction = 0f, done = 0, total = 0) }
                    notify(progressNotification(getString(R.string.status_burning), null))
                    val burned = File(work, "${file.nameWithoutExtension}.titl.mp4")
                    var last = 0L
                    val ok = try {
                        SubtitleBurner.burn(this, file, chosen, burned, { job.id in cancelled }) { fraction ->
                            val now = SystemClock.elapsedRealtime()
                            if (now - last >= 400) {
                                last = now
                                Downloads.update(job.id) { it.copy(fraction = fraction) }
                                notify(progressNotification("${job.title} · ${getString(R.string.status_burning)} · ${(fraction * 100).toInt()}%", fraction))
                            }
                        }
                    } catch (_: SubtitleBurner.Cancelled) {
                        throw CancelledHere()
                    }
                    if (ok) {
                        file.delete()
                        check(burned.renameTo(file)) { "Privremeni fajl nije premješten" }
                        subtitleFiles.forEach { it.delete() }
                        subtitleFiles = emptyList()
                    }
                    Downloads.update(job.id) { it.copy(phase = Phase.SAVING) }
                    notify(progressNotification(getString(R.string.status_saving), null))
                }
            }
            if (job.id in cancelled) throw CancelledHere()
            // Titlovi su tekst: MediaStore ih prima samo u Download/, pa tada i video ide tamo (plejer ih nađe zajedno).
            val location = if (subtitleFiles.isNotEmpty()) SaveLocation.DOWNLOADS else Settings.location(this)
            val uri = MediaSaver.save(this, file, job.isAudio, location) { job.id in cancelled }
            subtitleFiles.forEach { sub ->
                // „dio0.en.srt" → „Naslov [id].en.srt" (isto ime kao video, da ga plejer učita sam)
                val renamed = File(work, file.nameWithoutExtension + "." + sub.name.substringAfter("."))
                if (sub.renameTo(renamed)) runCatching { MediaSaver.save(this, renamed, false, SaveLocation.DOWNLOADS) }
            }
            if (job.id in cancelled) {
                contentResolver.delete(uri, null, null)
                throw CancelledHere()
            }
            // Isti link je ranije pao, a sada je uspio (dostignuće „Ne odustaje se").
            val retried = History.items.value.any { it.failed && it.url == job.url }
            History.add(HistoryItem(job.id, job.title.ifBlank { result[0].toString() }, uri.toString(), job.isAudio,
                formatLabel(job, file.extension), size, job.duration, job.thumbnail, System.currentTimeMillis(),
                adult = job.adult))
            Achievements.recordDownload(FinishedDownload(job.url, job.isAudio, job.hasClip, height, size,
                job.subtitles && subtitleFiles.isNotEmpty(), job.duration, retried, job.playlistKey, job.playlistSize))
            Support.countDownload()
            Recap.record(job.url, size, job.duration)
            batchDone++
            batchBytes += size
            notifyFinished(getString(R.string.status_done, job.title), openIntent(uri, job.isAudio), shareIntent(uri, job.isAudio))
            // Kao na računaru: traka zazeleni, kratko pulsira, pa kartica nestane.
            Downloads.update(job.id) { it.copy(phase = Phase.DONE, fraction = 1f) }
            Thread.sleep(1100)
        } catch (error: Exception) {
            batchOther++
            if (job.id in cancelled || error is CancelledHere || error is InterruptedException) {
                notifyFinished(getString(R.string.status_cancelled), null)
            } else if ("ADULT_CONFIRM" in error.message.orEmpty()) {
                // Video za odrasle bez potvrde: čeka na listi (dugme „Imam 18+"), ostali poslovi idu dalje.
                waitsForAdult = true
                Downloads.update(job.id) { it.copy(job = job.copy(adult = true, adultOk = false), phase = Phase.NEEDS_ADULT) }
                notifyFinished(getString(R.string.adult_waiting, job.title), null)
            } else {
                val message = cleanError(this, error.message)
                Downloads.lastError.value = message
                // U sistemski dnevnik smije samo poznata kategorija, bez linka i sirove poruke sajta.
                android.util.Log.w("VideoDownload", "Preuzimanje nije uspjelo: $message")
                History.add(HistoryItem(job.id, job.title.ifBlank { job.url }, "", job.isAudio, job.label, 0, job.duration,
                    job.thumbnail, System.currentTimeMillis(), adult = job.adult, failed = true, url = job.url,
                    error = message))
                notifyFinished(getString(R.string.status_failed, message), null)
            }
        } finally {
            work.deleteRecursively() // privremeni fajlovi nikad ne ostaju
            if (job.id !in cancelled) Pacing.finished(family) // razmak ili predah prije sljedećeg s istog sajta
            cancelled -= job.id
            running = null
            if (!waitsForAdult) Downloads.remove(job.id)
            synchronized(this) {
                pending--
                if (pending == 0) {
                    finishBatch()
                    stopForeground(STOP_FOREGROUND_REMOVE) // napredak nestaje; ostaje samo obavještenje o kraju
                    stopSelf()
                }
            }
        }
    }

    private class CancelledHere : Exception()

    /** Sajt blokira (429, „nisi bot"): čeka 5, 10 pa 15 min i pokušava ponovo; četvrti put je obična greška. */
    private fun downloadWithPauses(job: Job, family: String?, call: () -> List<PyObject>): List<PyObject> {
        var attempt = if (job.blockedOnRead) 1 else 0 // prvo čekanje (5 min) je bilo već poslije čitanja linka
        while (true) {
            try {
                return call()
            } catch (error: Exception) {
                if (job.id in cancelled || family == null || !Pacing.isBlockError(error.message)) throw error
                attempt++
                Pacing.blocked(family, attempt) ?: throw error
                waitForPause(job)
                Downloads.update(job.id) { it.copy(phase = Phase.READING) }
            }
        }
    }

    /** Čeka pauzu zaštite od blokade za sajt ovog posla; kartica za predah i blokadu, tekst za kratak razmak. */
    private fun waitForPause(job: Job) {
        val family = Pacing.familyOf(job.url) ?: return
        val total = Pacing.remaining(family)
        if (total <= 0) return
        val pause = Pacing.lastPause(family) ?: Pause(family, "gap", total)
        val site = Pacing.NAMES[family] ?: family
        val until = SystemClock.elapsedRealtime() + total
        val card = if (pause.card) PauseCard(pause, until, supportLine(true), nextTip()) else null
        Pacing.showCard(card)
        Downloads.update(job.id) { it.copy(phase = Phase.PAUSED, pauseUntil = until, pauseSite = site) }
        var shown = -1L
        while (Pacing.remaining(family) > 0) {
            if (job.id in cancelled) {
                if (card != null && Pacing.card.value == card) Pacing.showCard(null)
                throw CancelledHere()
            }
            val seconds = (Pacing.remaining(family) + 999) / 1000
            if (seconds != shown) {
                shown = seconds
                val time = "%d:%02d".format(seconds / 60, seconds % 60)
                val text = when (pause.kind) {
                    "block" -> getString(R.string.pause_block_title, site, time)
                    "break" -> getString(R.string.pause_break_title, site, time)
                    else -> getString(R.string.pause_gap, seconds.toInt(), site)
                }
                notify(progressNotification(text, null))
            }
            Thread.sleep(250)
        }
        if (card != null) {
            val natural = Pacing.card.value == card // „Nastavi odmah" sklanja karticu prije roka
            Pacing.showCard(null)
            if (natural) {
                Achievements.recordSource("patient") // dostignuće „Strpljivi"
                getSystemService(NotificationManager::class.java).notify(RESUME_NOTIFICATION_ID,
                    Notification.Builder(this, VideoDownloadApp.CHANNEL_DOWNLOADS)
                        .setSmallIcon(android.R.drawable.stat_sys_download)
                        .setContentTitle(getString(R.string.app_name))
                        .setContentText(getString(R.string.pause_resumed, site))
                        .setAutoCancel(true).setTimeoutAfter(15_000).setContentIntent(appIntent()).build())
            }
        }
    }

    /** Red o podršci na kartici (Support.noteAllowed); null = bez reda. */
    private fun supportLine(today: Boolean): String? {
        val now = System.currentTimeMillis()
        if (Support.snoozed(now)) return getString(R.string.pause_thanks)
        if (!Support.noteAllowed(Achievements.downloadCount, now)) return null
        Support.noteShown(now)
        val (count, bytes) = Recap.today()
        return if (today && count > 0) getString(R.string.pause_support_today, count, formatSize(bytes.toDouble()))
        else getString(R.string.pause_support_plain)
    }

    private fun nextTip(): Int {
        val prefs = getSharedPreferences("zastita", Context.MODE_PRIVATE)
        val index = prefs.getInt("savjet", 0)
        prefs.edit().putInt("savjet", (index + 1) % TIPS.size).apply()
        return TIPS[index % TIPS.size]
    }

    /** Kraj grupe: „Gotovo: 50/50 videa" ako je bar 50 uspjelo, a ništa nije palo ni prekinuto. */
    private fun finishBatch() {
        if (batchDone >= SUCCESS_MIN && batchOther == 0) {
            val line = supportLine(false)
            Downloads.success.value = SuccessCard(batchDone, batchDone, batchBytes, line, line != null && !Support.snoozed())
            notifyFinished(getString(R.string.success_title, batchDone, batchDone, formatSize(batchBytes.toDouble())), null)
        }
        batchDone = 0
        batchOther = 0
        batchBytes = 0
    }

    /** 150 → „2.30", 3723 → „1.02.03" (kao section_label na računaru: dvotačka nije dozvoljena u imenu fajla). */
    private fun clipLabel(seconds: Int): String {
        val h = seconds / 3600
        val m = seconds % 3600 / 60
        val s = seconds % 60
        return if (h > 0) "%d.%02d.%02d".format(h, m, s) else "%d.%02d".format(m, s)
    }

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

    private fun notifyFinished(text: String, open: PendingIntent?, share: PendingIntent? = null) {
        val builder = Notification.Builder(this, VideoDownloadApp.CHANNEL_DOWNLOADS)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(open ?: appIntent())
        // Gotov fajl: „Otvori" i „Podijeli" pravo iz obavještenja (plan 1.0).
        if (open != null) builder.addAction(Notification.Action.Builder(null, getString(R.string.open), open).build())
        if (share != null) builder.addAction(Notification.Action.Builder(null, getString(R.string.share), share).build())
        val notification = builder.build()
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

    private fun shareIntent(uri: Uri, isAudio: Boolean): PendingIntent {
        val send = Intent(Intent.ACTION_SEND).setType(if (isAudio) "audio/*" else "video/*")
            .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        return PendingIntent.getActivity(this, 3, Intent.createChooser(send, null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    override fun onDestroy() {
        worker.shutdownNow()
        super.onDestroy()
    }

    private fun videoHeight(file: File): Int = runCatching {
        val retriever = android.media.MediaMetadataRetriever()
        try {
            retriever.setDataSource(file.absolutePath)
            val height = retriever.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toInt() ?: 0
            val width = retriever.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toInt() ?: 0
            minOf(height, width).takeIf { it > 0 } ?: height // uspravan video: kraća strana je „p"
        } finally {
            retriever.release()
        }
    }.getOrDefault(0)

    companion object {
        /** Oznaka posla „zvuk kao MP3" (ekran kvaliteta); bez nje zvuk ostaje M4A. */
        const val MP3_LABEL = "MP3"
        private const val NOTIFICATION_ID = 1
        private const val DONE_NOTIFICATION_ID = 2
        private const val RESUME_NOTIFICATION_ID = 3
        private const val SUCCESS_MIN = 50
        private val TIPS = intArrayOf(R.string.tip_1, R.string.tip_2, R.string.tip_3, R.string.tip_4, R.string.tip_5, R.string.tip_6)
        private const val EXTRA_JOB = "job"
        private const val EXTRA_ID = "id"
        private const val ACTION_CANCEL = "cancel"

        fun start(context: Context, job: Job) {
            // „Sljedeći video bez zvuka" iz Postavki: prvi sljedeći video (i iz „Podijeli", liste…), samo jednom.
            val next = if (!job.isAudio && !job.mute && Settings.takeMuteNext(context)) {
                job.copy(mute = true, label = "${job.label} · ${context.getString(R.string.mute_short)}")
            } else job
            context.startForegroundService(Intent(context, DownloadService::class.java).putExtra(EXTRA_JOB, next.toBundle()))
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
                Pacing.isBlockError(raw) -> context.getString(R.string.error_bot)
                "sign in" in raw || "login" in raw || "log in" in raw || "cookies" in raw ||
                    "authentication" in raw || "nsfw" in raw -> context.getString(R.string.error_login)
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
