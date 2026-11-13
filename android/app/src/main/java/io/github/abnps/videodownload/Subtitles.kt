package io.github.abnps.videodownload

/**
 * Titl iz .srt ili .vtt fajla (Ahmed 12.11.2026, titl upisan u sliku): redovi s vremenom od-do, bez oznaka
 * stila (<c>, <i>, vremena unutar reda kod automatskih titlova). Samo Kotlin, bez Androida, pa se testira na JVM-u.
 */
data class Cue(val startUs: Long, val endUs: Long, val text: String)

object Subtitles {
    private val TIMING = Regex(
        """((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})""")
    private val TAG = Regex("<[^>]*>")
    private val BOM = 0xFEFF.toChar().toString() // oznaka na početku nekih .srt fajlova

    fun parse(text: String): List<Cue> {
        val lines = text.replace(BOM, "").replace("\r\n", "\n").replace('\r', '\n').split('\n')
        val cues = mutableListOf<Cue>()
        var index = 0
        while (index < lines.size) {
            val timing = TIMING.find(lines[index])
            index++
            if (timing == null) continue
            val body = mutableListOf<String>()
            while (index < lines.size && lines[index].isNotBlank()) {
                val clean = TAG.replace(lines[index], "").replace("&nbsp;", " ").replace("&amp;", "&")
                    .replace("&lt;", "<").replace("&gt;", ">").trim()
                if (clean.isNotEmpty()) body += clean
                index++
            }
            val start = micros(timing.groupValues[1])
            val end = micros(timing.groupValues[2])
            if (body.isNotEmpty() && end > start) cues += Cue(start, end, body.joinToString("\n"))
        }
        return merge(cues.sortedBy { it.startUs })
    }

    /**
     * Automatski titlovi (npr. YouTube) ponavljaju prethodni red u sljedećem dijelu („kotrljajući" titl), pa bi
     * u slici isti tekst stajao dvaput. Red koji je već prikazan u prethodnom dijelu se izbacuje.
     */
    private fun merge(cues: List<Cue>): List<Cue> {
        val result = mutableListOf<Cue>()
        for (cue in cues) {
            val previous = result.lastOrNull()
            val lines = cue.text.split('\n')
            val fresh = if (previous != null) lines.filter { it !in previous.text.split('\n') } else lines
            val text = (if (fresh.isEmpty()) lines.takeLast(1) else fresh).joinToString("\n")
            if (previous != null && previous.text == text && cue.startUs <= previous.endUs + 50_000) {
                result[result.lastIndex] = previous.copy(endUs = maxOf(previous.endUs, cue.endUs))
            } else {
                result += cue.copy(text = text)
            }
        }
        return result
    }

    /** Red koji se vidi u trenutku `timeUs`; null = u tom trenutku nema titla. */
    fun at(cues: List<Cue>, timeUs: Long): Cue? {
        var low = 0
        var high = cues.lastIndex
        var found: Cue? = null
        while (low <= high) {
            val middle = (low + high) ushr 1
            if (cues[middle].startUs <= timeUs) { found = cues[middle]; low = middle + 1 } else high = middle - 1
        }
        return found?.takeIf { timeUs < it.endUs }
    }

    /** „00:01:02,500", „01:02.5" → mikrosekunde. */
    internal fun micros(value: String): Long {
        val parts = value.replace(',', '.').split(':')
        val seconds = parts.last().toDouble()
        val minutes = parts[parts.size - 2].toLong()
        val hours = if (parts.size > 2) parts[0].toLong() else 0L
        return ((hours * 3600 + minutes * 60) * 1_000_000L) + (seconds * 1_000_000).toLong()
    }

    /** Titl za upis u sliku: prvi na jeziku aplikacije (bs: i hr, sr), inače prvi koji postoji (engleski). */
    fun pick(files: List<java.io.File>, language: String): java.io.File? {
        val own = if (language == "bs") listOf("bs", "hr", "sr") else listOf(language)
        fun code(file: java.io.File) = file.name.split('.').dropLast(1).lastOrNull().orEmpty()
        return files.firstOrNull { file -> own.any { code(file) == it || code(file).startsWith("$it-") } }
            ?: files.firstOrNull()
    }
}
