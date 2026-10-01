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
                data.optDouble("audio_size", 0.0), data.optBoolean("audio_available", false))
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
