package io.github.abnps.videodownload

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer

/**
 * Spaja H.264 sliku (MP4) i AAC zvuk (M4A) u jedan MP4 Androidovim MediaMuxer-om: bez ffmpeg-a i bez ponovnog
 * kodiranja (kvalitet ostaje isti, traje par sekundi). Radi samo s kodecima koje MP4 kontejner prima.
 */
object Muxer {
    fun merge(video: File, audio: File, output: File, isCancelled: () -> Boolean = { false }) {
        if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
        val muxer = MediaMuxer(output.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val extractors = mutableListOf<MediaExtractor>()
        try {
            val tracks = listOf(video to "video/", audio to "audio/").map { (file, prefix) ->
                val extractor = MediaExtractor().also { extractors += it }
                extractor.setDataSource(file.path)
                val index = (0 until extractor.trackCount).firstOrNull {
                    extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME).orEmpty().startsWith(prefix)
                } ?: error("${file.name}: nema ${prefix.trimEnd('/')} toka")
                extractor.selectTrack(index)
                val format = extractor.getTrackFormat(index)
                if (prefix == "video/" && format.containsKey(MediaFormat.KEY_ROTATION)) {
                    muxer.setOrientationHint(format.getInteger(MediaFormat.KEY_ROTATION)) // uspravni video ostaje uspravan
                }
                val capacity = if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                    format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE)
                } else {
                    4 * 1024 * 1024
                }
                Triple(extractor, muxer.addTrack(format), capacity)
            }
            muxer.start()
            val info = MediaCodec.BufferInfo()
            for ((extractor, track, capacity) in tracks) {
                val buffer = ByteBuffer.allocateDirect(capacity)
                while (true) {
                    if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
                    val size = extractor.readSampleData(buffer, 0)
                    if (size < 0) break
                    // SAMPLE_FLAG_SYNC i BUFFER_FLAG_KEY_FRAME su ista vrijednost (ključni kadar).
                    val flags = if (extractor.sampleFlags and MediaExtractor.SAMPLE_FLAG_SYNC != 0) {
                        MediaCodec.BUFFER_FLAG_KEY_FRAME
                    } else {
                        0
                    }
                    info.set(0, size, extractor.sampleTime, flags)
                    muxer.writeSampleData(track, buffer, info)
                    extractor.advance()
                }
            }
            if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
            muxer.stop()
        } finally {
            extractors.forEach { it.release() }
            muxer.release()
        }
    }

    /**
     * Isječak [startUs, endUs) iz MP4/M4A bez ponovnog kodiranja (kao „Isječak" na računaru, ali bez ffmpeg-a):
     * početak se pomjera na ključni kadar prije `startUs` (najviše par sekundi ranije), kraj je tačan.
     * Svi tokovi kreću od istog trenutka, pa slika i zvuk ostaju usklađeni; vrijeme u izlazu počinje od nule.
     */
    fun trim(input: File, output: File, startUs: Long, endUs: Long, isCancelled: () -> Boolean = { false }) {
        require(endUs > startUs) { "Kraj isječka mora biti poslije početka" }
        val probe = MediaExtractor().apply { setDataSource(input.path) }
        val trackFormats = (0 until probe.trackCount).map { probe.getTrackFormat(it) }
        val videoIndex = trackFormats.indexOfFirst { it.getString(MediaFormat.KEY_MIME).orEmpty().startsWith("video/") }
        // Početak = ključni kadar slike (ili zvuka kad slike nema) na ili prije traženog početka.
        probe.selectTrack(if (videoIndex >= 0) videoIndex else 0)
        probe.seekTo(startUs, MediaExtractor.SEEK_TO_PREVIOUS_SYNC)
        val begin = probe.sampleTime.takeIf { it >= 0 } ?: startUs
        probe.release()
        if (begin >= endUs) error("Isječak je izvan trajanja videa")

        val muxer = MediaMuxer(output.path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val extractors = mutableListOf<MediaExtractor>()
        try {
            val tracks = trackFormats.indices.mapNotNull { index ->
                val format = trackFormats[index]
                val mime = format.getString(MediaFormat.KEY_MIME).orEmpty()
                if (!mime.startsWith("video/") && !mime.startsWith("audio/")) return@mapNotNull null
                val extractor = MediaExtractor().also { extractors += it }
                extractor.setDataSource(input.path)
                extractor.selectTrack(index)
                extractor.seekTo(begin, MediaExtractor.SEEK_TO_PREVIOUS_SYNC)
                if (mime.startsWith("video/") && format.containsKey(MediaFormat.KEY_ROTATION)) {
                    muxer.setOrientationHint(format.getInteger(MediaFormat.KEY_ROTATION))
                }
                val capacity = if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                    format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE)
                } else {
                    4 * 1024 * 1024
                }
                Triple(extractor, muxer.addTrack(format), capacity)
            }
            check(tracks.isNotEmpty()) { "${input.name}: nema slike ni zvuka" }
            muxer.start()
            val info = MediaCodec.BufferInfo()
            for ((extractor, track, capacity) in tracks) {
                val buffer = ByteBuffer.allocateDirect(capacity)
                while (true) {
                    if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
                    val size = extractor.readSampleData(buffer, 0)
                    val time = extractor.sampleTime
                    if (size < 0 || time >= endUs) break
                    if (time >= begin) {
                        val flags = if (extractor.sampleFlags and MediaExtractor.SAMPLE_FLAG_SYNC != 0) {
                            MediaCodec.BUFFER_FLAG_KEY_FRAME
                        } else {
                            0
                        }
                        info.set(0, size, time - begin, flags)
                        muxer.writeSampleData(track, buffer, info)
                    }
                    extractor.advance()
                }
            }
            if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
            muxer.stop()
        } finally {
            extractors.forEach { it.release() }
            muxer.release()
        }
    }
}
