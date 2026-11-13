package io.github.abnps.videodownload

import android.content.Context
import android.graphics.Color
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Handler
import android.os.HandlerThread
import android.text.Spannable
import android.text.SpannableString
import android.text.style.AbsoluteSizeSpan
import android.text.style.BackgroundColorSpan
import android.text.style.ForegroundColorSpan
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.util.UnstableApi
import androidx.media3.effect.OverlayEffect
import androidx.media3.effect.StaticOverlaySettings
import androidx.media3.effect.TextOverlay
import androidx.media3.effect.TextureOverlay
import androidx.media3.transformer.Composition
import androidx.media3.transformer.EditedMediaItem
import androidx.media3.transformer.Effects
import androidx.media3.transformer.ExportException
import androidx.media3.transformer.ExportResult
import androidx.media3.transformer.ProgressHolder
import androidx.media3.transformer.Transformer
import com.google.common.collect.ImmutableList
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * Titl upisan u sliku na telefonu (Ahmed 12.11.2026), kao na računaru (videodl/burn.py), ali bez ffmpeg-a:
 * Media3 Transformer dekodira video, iscrta red titla na svaku sličicu i kodira H.264 koderom samog telefona.
 * Zvuk se prepisuje bez promjene. Greška ostavlja original netaknut (titl tada ostaje pored videa).
 */
@OptIn(UnstableApi::class)
object SubtitleBurner {
    class Cancelled : Exception()

    /** true = `output` je gotov video s titlom; false = nije uspjelo (razlog u dnevniku). Prekid baca [Cancelled]. */
    fun burn(context: Context, video: File, subtitle: File, output: File, isCancelled: () -> Boolean,
             onProgress: (Float) -> Unit): Boolean {
        val cues = Subtitles.parse(runCatching { subtitle.readText() }.getOrDefault(""))
        if (cues.isEmpty()) return false
        val height = videoHeight(video).takeIf { it > 0 } ?: 720
        val thread = HandlerThread("titl-u-slici").apply { start() }
        val handler = Handler(thread.looper)
        val finished = CountDownLatch(1)
        var failure: ExportException? = null
        var transformer: Transformer? = null
        try {
            handler.post {
                val overlay = CueOverlay(cues, height)
                val effects = Effects(emptyList(), listOf(OverlayEffect(ImmutableList.of<TextureOverlay>(overlay))))
                val item = EditedMediaItem.Builder(MediaItem.fromUri(Uri.fromFile(video))).setEffects(effects).build()
                transformer = Transformer.Builder(context)
                    .setVideoMimeType(MimeTypes.VIDEO_H264)
                    .setLooper(thread.looper)
                    .addListener(object : Transformer.Listener {
                        override fun onCompleted(composition: Composition, exportResult: ExportResult) = finished.countDown()

                        override fun onError(composition: Composition, exportResult: ExportResult,
                                             exportException: ExportException) {
                            failure = exportException
                            finished.countDown()
                        }
                    }).build()
                    .also { it.start(item, output.path) }
            }
            val holder = ProgressHolder()
            while (!finished.await(300, TimeUnit.MILLISECONDS)) {
                if (isCancelled()) {
                    handler.post { transformer?.cancel() }
                    output.delete()
                    throw Cancelled()
                }
                handler.post {
                    if (transformer?.getProgress(holder) == Transformer.PROGRESS_STATE_AVAILABLE) {
                        onProgress(holder.progress / 100f)
                    }
                }
            }
            if (failure != null || !output.isFile || output.length() == 0L) {
                output.delete()
                return false
            }
            return true
        } finally {
            thread.quitSafely()
        }
    }

    private fun videoHeight(file: File): Int = runCatching {
        MediaMetadataRetriever().use {
            it.setDataSource(file.path)
            val width = it.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
            val height = it.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
            minOf(width, height).takeIf { size -> size > 0 } ?: height // uspravni video: uži rub
        }
    }.getOrDefault(0)

    /** Red titla za trenutak sličice: bijeli tekst na poluprovidnoj traci, pri dnu slike. */
    private class CueOverlay(private val cues: List<Cue>, frameHeight: Int) : TextOverlay() {
        private val textSize = (frameHeight / 18).coerceIn(14, 96)
        private val settings = StaticOverlaySettings.Builder()
            .setOverlayFrameAnchor(0f, -1f) // donja ivica teksta…
            .setBackgroundFrameAnchor(0f, -0.92f) // …malo iznad dna slike
            .build()

        override fun getText(presentationTimeUs: Long): SpannableString {
            val text = Subtitles.at(cues, presentationTimeUs)?.text ?: " " // prazan tekst nema veličinu sličice
            return SpannableString(text).apply {
                val flags = Spannable.SPAN_INCLUSIVE_INCLUSIVE
                setSpan(ForegroundColorSpan(Color.WHITE), 0, length, flags)
                setSpan(AbsoluteSizeSpan(textSize), 0, length, flags)
                if (text.isNotBlank()) setSpan(BackgroundColorSpan(Color.argb(150, 0, 0, 0)), 0, length, flags)
            }
        }

        override fun getOverlaySettings(presentationTimeUs: Long) = settings
    }
}
