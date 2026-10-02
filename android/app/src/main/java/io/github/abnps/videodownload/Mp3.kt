package io.github.abnps.videodownload

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import java.io.File
import java.nio.ByteOrder

/**
 * M4A (AAC) → MP3 na telefonu: Androidov dekoder daje PCM, LAME (libvdmp3.so, LGPL) ga kodira u MP3.
 * Kvalitet kao na računaru: 192 kbps. Bez ffmpeg-a (odluka B iz android_plan.md).
 */
object Mp3 {
    const val KBPS = 192

    init {
        System.loadLibrary("vdmp3")
    }

    @JvmStatic private external fun nativeInit(sampleRate: Int, channels: Int, kbps: Int): Long
    @JvmStatic private external fun nativeEncode(handle: Long, pcm: ShortArray, frames: Int, out: ByteArray): Int
    @JvmStatic private external fun nativeFlush(handle: Long, out: ByteArray): Int
    @JvmStatic private external fun nativeClose(handle: Long)

    /** Pretvara `input` (zvuk u MP4/M4A) u `output` (MP3); `onProgress` dobija udio 0..1. */
    fun convert(input: File, output: File, cancelled: () -> Boolean, onProgress: (Float) -> Unit) {
        val extractor = MediaExtractor()
        var decoder: MediaCodec? = null
        var lame = 0L
        try {
            extractor.setDataSource(input.path)
            val track = (0 until extractor.trackCount).first {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME).orEmpty().startsWith("audio/")
            }
            extractor.selectTrack(track)
            val format = extractor.getTrackFormat(track)
            val duration = if (format.containsKey(MediaFormat.KEY_DURATION)) format.getLong(MediaFormat.KEY_DURATION) else 0L
            decoder = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!)
            decoder.configure(format, null, null, 0)
            decoder.start()

            output.outputStream().buffered().use { out ->
                val info = MediaCodec.BufferInfo()
                var inputDone = false
                var channels = 0
                var mp3 = ByteArray(0)
                while (true) {
                    if (cancelled()) throw InterruptedException()
                    if (!inputDone) {
                        val index = decoder.dequeueInputBuffer(10_000)
                        if (index >= 0) {
                            val size = extractor.readSampleData(decoder.getInputBuffer(index)!!, 0)
                            if (size < 0) {
                                decoder.queueInputBuffer(index, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                                inputDone = true
                            } else {
                                decoder.queueInputBuffer(index, 0, size, extractor.sampleTime, 0)
                                extractor.advance()
                            }
                        }
                    }
                    val index = decoder.dequeueOutputBuffer(info, 10_000)
                    if (index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED || (index >= 0 && lame == 0L)) {
                        // Stvarni broj kanala i frekvencija su poznati tek iz izlaza dekodera.
                        val pcmFormat = decoder.outputFormat
                        channels = pcmFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                        check(channels in 1..2) { "Nepodržan broj kanala: $channels" }
                        if (lame == 0L) {
                            lame = nativeInit(pcmFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE), channels, KBPS)
                            check(lame != 0L) { "MP3 koder nije pokrenut" }
                        }
                    }
                    if (index < 0) continue
                    if (info.size > 0) {
                        val buffer = decoder.getOutputBuffer(index)!!.order(ByteOrder.nativeOrder())
                        buffer.position(info.offset).limit(info.offset + info.size)
                        val pcm = ShortArray(info.size / 2).also { buffer.asShortBuffer().get(it) }
                        val frames = pcm.size / channels
                        val needed = (1.25 * frames + 7200).toInt() // preporuka iz lame.h
                        if (mp3.size < needed) mp3 = ByteArray(needed)
                        val written = nativeEncode(lame, pcm, frames, mp3)
                        check(written >= 0) { "MP3 kodiranje nije uspjelo ($written)" }
                        out.write(mp3, 0, written)
                        if (duration > 0) onProgress((info.presentationTimeUs.toFloat() / duration).coerceIn(0f, 1f))
                    }
                    decoder.releaseOutputBuffer(index, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                }
                if (lame != 0L) {
                    val tail = ByteArray(7200)
                    val written = nativeFlush(lame, tail)
                    if (written > 0) out.write(tail, 0, written)
                }
            }
        } finally {
            runCatching { decoder?.stop() }
            decoder?.release()
            extractor.release()
            if (lame != 0L) nativeClose(lame)
        }
    }
}
