package io.github.abnps.videodownload

import org.json.JSONObject

/** Jedan izbor kvaliteta: `height` ide yt-dlp-u (filtar), `label` je ono što korisnik vidi (uži rub: 1080p). */
data class QualityOption(val height: Int, val label: Int, val size: Double)

/** Rezultat vd_core.probe: sve što treba ekranu „Izaberi kvalitet". */
data class VideoInfo(
    val url: String,
    val title: String,
    val thumbnail: String,
    val duration: Int,
    val site: String,
    val video: List<QualityOption>,
    val audioSize: Double,
    val audioAvailable: Boolean,
    val adult: Boolean = false, // sajt ga označio kao 18+ (YouTube izuzet): potvrda pri svakom preuzimanju
) {
    companion object {
        fun parse(json: String): VideoInfo {
            val data = JSONObject(json)
            val options = data.optJSONArray("video")
            val video = (0 until (options?.length() ?: 0)).map {
                val option = options!!.getJSONObject(it)
                QualityOption(option.optInt("height"), option.optInt("label", option.optInt("height")), option.optDouble("size", 0.0))
            }
            return VideoInfo(data.optString("url"), data.optString("title"), data.optString("thumbnail"),
                data.optDouble("duration", 0.0).toInt(), data.optString("site"), video,
                data.optDouble("audio_size", 0.0), data.optBoolean("audio_available", false), data.optBoolean("adult"))
        }
    }
}

/** Jedan video iz plejliste (vd_core.playlist_json): kvalitet se bira tek pri preuzimanju. */
data class PlaylistEntry(val url: String, val title: String, val thumbnail: String, val duration: Int, val adult: Boolean)

data class PlaylistInfo(val url: String, val title: String, val site: String, val entries: List<PlaylistEntry>) {
    companion object {
        /** null kad JSON nije plejlista (onda je VideoInfo). */
        fun parseOrNull(json: String): PlaylistInfo? {
            val data = JSONObject(json)
            if (!data.optBoolean("playlist")) return null
            val array = data.getJSONArray("entries")
            val entries = (0 until array.length()).map {
                val e = array.getJSONObject(it)
                PlaylistEntry(e.getString("url"), e.optString("title"), e.optString("thumbnail"), e.optInt("duration"),
                    e.optBoolean("adult"))
            }
            return PlaylistInfo(data.optString("url"), data.optString("title"), data.optString("site"), entries)
        }
    }
}

/** Javne adrese (iste kao program za računar): sajt na jeziku telefona i dobrovoljni prilog. */
object Links {
    const val SUPPORT = "https://www.paypal.com/ncp/payment/PY6SBUFD6V7JQ"
    private const val SITE = "https://abnps.github.io/video-download/"

    fun site(page: String): String {
        val language = when (val code = java.util.Locale.getDefault().language) {
            "sr", "hr", "bs" -> "bs"
            "de", "es", "fr" -> code
            else -> "en"
        }
        return SITE + (if (language == "en") "" else "$language/") + page
    }
}
