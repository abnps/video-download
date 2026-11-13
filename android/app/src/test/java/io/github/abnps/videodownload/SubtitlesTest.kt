package io.github.abnps.videodownload

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.File

/** Titl upisan u sliku (Ahmed 12.11.2026): čitanje .srt/.vtt i izbor jezika, bez Androida. */
class SubtitlesTest {
    @Test
    fun readsSrtWithOurLettersAndTwoLines() {
        val cues = Subtitles.parse("1\r\n00:00:01,000 --> 00:00:03,500\r\nZdravo, čćšđž\r\ndrugi red\r\n\r\n" +
            "2\r\n00:00:04,000 --> 00:00:05,000\r\n<i>Kraj</i>\r\n")
        assertEquals(2, cues.size)
        assertEquals(Cue(1_000_000, 3_500_000, "Zdravo, čćšđž\ndrugi red"), cues[0])
        assertEquals("Kraj", cues[1].text) // oznake stila se ne crtaju
    }

    @Test
    fun readsYoutubeAutomaticVttWithoutRepeatingLines() {
        val vtt = """
            WEBVTT
            Kind: captions
            Language: en

            00:00:00.000 --> 00:00:02.000 align:start position:0%
            hello<00:00:00.500><c> there</c>

            00:00:02.000 --> 00:00:04.000 align:start position:0%
            hello there
            how are<00:00:02.800><c> you</c>
        """.trimIndent()
        val cues = Subtitles.parse(vtt)
        assertEquals(listOf("hello there", "how are you"), cues.map { it.text }) // isti red se ne ponavlja
        assertEquals(2_000_000L, cues[1].startUs)
    }

    @Test
    fun findsTheLineForAMoment() {
        val cues = Subtitles.parse("00:00:01.000 --> 00:00:02.000\nA\n\n00:01:00.000 --> 01:00:00.000\nB\n")
        assertNull(Subtitles.at(cues, 500_000))
        assertEquals("A", Subtitles.at(cues, 1_500_000)?.text)
        assertNull(Subtitles.at(cues, 2_000_000)) // kraj nije uključen
        assertEquals("B", Subtitles.at(cues, 3_599_000_000)?.text)
        assertEquals(3_600_000_000L, Subtitles.micros("1:00:00.000"))
    }

    @Test
    fun picksAppLanguageThenTheFirstOne() {
        val files = listOf(File("dio0.en.vtt"), File("dio0.hr.vtt"))
        assertEquals("dio0.hr.vtt", Subtitles.pick(files, "bs")?.name) // bosanski: i hrvatski i srpski
        assertEquals("dio0.en.vtt", Subtitles.pick(files, "de")?.name)
        assertEquals("dio0.de-DE.vtt", Subtitles.pick(listOf(File("dio0.en.vtt"), File("dio0.de-DE.vtt")), "de")?.name)
        assertNull(Subtitles.pick(emptyList(), "bs"))
    }
}
