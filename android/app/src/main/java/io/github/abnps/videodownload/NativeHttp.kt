package io.github.abnps.videodownload

import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * HTTP zahtjev kroz Androidov mrežni sloj (isti TLS kao prave Android aplikacije). Koristi ga Python (vd_net.py)
 * za sajtove koji odbijaju „obične" programe (npr. TikTok vrati lažnu stranicu „Site Maintenance"): na računaru
 * to rješava curl_cffi, koji na Androidu ne postoji. Preusmjeravanja i kolačiće vodi yt-dlp.
 */
object NativeHttp {
    /** Identitet ugrađenog preglednika ovog telefona (postavlja ga VideoDownloadApp pri pokretanju). */
    @JvmStatic
    var userAgent: String = "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 (KHTML, like Gecko) Mobile Safari/537.36"

    /** `headers` je ravna lista: ime, vrijednost, ime, vrijednost… */
    @JvmStatic
    fun open(method: String, url: String, headers: Array<String>, body: ByteArray?, timeoutMs: Int): NativeResponse {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.instanceFollowRedirects = false
        connection.requestMethod = method
        connection.connectTimeout = timeoutMs
        connection.readTimeout = timeoutMs
        connection.setRequestProperty("User-Agent", userAgent)
        for (index in 0 until headers.size - 1 step 2) {
            connection.setRequestProperty(headers[index], headers[index + 1])
        }
        if (body != null) {
            connection.doOutput = true
            connection.outputStream.use { it.write(body) }
        }
        val status = connection.responseCode
        val stream = if (status >= 400) connection.errorStream else connection.inputStream
        val flat = mutableListOf<String>()
        for ((name, values) in connection.headerFields) {
            if (name != null) values.forEach { flat += name; flat += it }
        }
        return NativeResponse(status, connection.responseMessage.orEmpty(), flat.toTypedArray(), stream, connection)
    }
}

class NativeResponse internal constructor(
    @JvmField val status: Int,
    @JvmField val reason: String,
    @JvmField val headers: Array<String>,
    private val stream: InputStream?,
    private val connection: HttpURLConnection,
) {
    /** Sljedeći komad odgovora (najviše `max` bajtova) ili null na kraju. */
    fun read(max: Int): ByteArray? {
        val input = stream ?: return null
        val buffer = ByteArray(max)
        val count = input.read(buffer)
        return when {
            count < 0 -> null
            count == max -> buffer
            else -> buffer.copyOf(count)
        }
    }

    fun close() {
        runCatching { stream?.close() }
        connection.disconnect()
    }
}
