package io.github.abnps.videodownload

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Isječak na ekranu kvaliteta: isti zapis vremena kao na računaru („2:30", „150", „1:02:03"). */
class ClipTest {
    @Test
    fun clockFormats() {
        assertEquals(150, parseClock("2:30"))
        assertEquals(150, parseClock("150"))
        assertEquals(3723, parseClock("1:02:03"))
        assertEquals(30, parseClock(" 0:30 "))
        for (bad in listOf("", "2:", ":30", "1:60", "a:10", "1:2:3:4", "-5")) assertNull(bad, parseClock(bad))
    }

    @Test
    fun clipRange() {
        assertEquals(30 to 135, parseClip("0:30", "2:15", 600))
        assertEquals(0 to 600, parseClip("", "", 600)) // prazno = od početka do kraja
        assertNull(parseClip("2:15", "0:30", 600)) // kraj prije početka
        assertNull(parseClip("0:30", "11:00", 600)) // poslije kraja videa
        assertEquals(30 to 5000, parseClip("0:30", "5000", 0)) // trajanje nepoznato
    }
}
