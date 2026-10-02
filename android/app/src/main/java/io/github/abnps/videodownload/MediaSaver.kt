package io.github.abnps.videodownload

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import java.io.File

/**
 * Gotov fajl iz privremenog foldera aplikacije ide u Download/Video Download (podrazumijevano) ili u Galeriju
 * (Movies/Video Download) i Muziku (Music/Video Download) preko MediaStore-a: bez dozvole za pisanje po memoriji, vidi se odmah u aplikacijama.
 */
object MediaSaver {
    fun save(context: Context, source: File, isAudio: Boolean, location: SaveLocation,
             isCancelled: () -> Boolean = { false }): Uri {
        if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
        val resolver = context.contentResolver
        val volume = MediaStore.VOLUME_EXTERNAL_PRIMARY
        val collection = when {
            location == SaveLocation.DOWNLOADS -> MediaStore.Downloads.getContentUri(volume)
            isAudio -> MediaStore.Audio.Media.getContentUri(volume)
            else -> MediaStore.Video.Media.getContentUri(volume)
        }
        val folder = when {
            location == SaveLocation.DOWNLOADS -> Environment.DIRECTORY_DOWNLOADS
            isAudio -> Environment.DIRECTORY_MUSIC
            else -> Environment.DIRECTORY_MOVIES
        }
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, source.name)
            put(MediaStore.MediaColumns.MIME_TYPE, mimeType(source.extension, isAudio))
            // Folder nosi ime aplikacije, pa Galerija pokazuje poseban album „Video Download".
            put(MediaStore.MediaColumns.RELATIVE_PATH, "$folder/${context.getString(R.string.app_name)}")
            put(MediaStore.MediaColumns.IS_PENDING, 1) // drugi ga ne vide dok se kopira
        }
        val uri = resolver.insert(collection, values) ?: error("MediaStore nije napravio fajl")
        try {
            resolver.openOutputStream(uri).use { out ->
                requireNotNull(out) { "MediaStore nije otvorio fajl za pisanje" }
                source.inputStream().use { input ->
                    val buffer = ByteArray(256 * 1024)
                    while (true) {
                        if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
                        val count = input.read(buffer)
                        if (count < 0) break
                        out.write(buffer, 0, count)
                    }
                }
            }
            if (isCancelled()) throw InterruptedException("Preuzimanje je zaustavljeno")
            resolver.update(uri, ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }, null, null)
        } catch (error: Exception) {
            resolver.delete(uri, null, null) // nedovršen fajl ne ostaje u Galeriji
            throw error
        }
        return uri
    }

    private fun mimeType(extension: String, isAudio: Boolean): String = when (extension.lowercase()) {
        "mp4" -> "video/mp4"
        "webm" -> if (isAudio) "audio/webm" else "video/webm"
        "m4a" -> "audio/mp4"
        "mp3" -> "audio/mpeg"
        "opus", "ogg" -> "audio/ogg"
        else -> if (isAudio) "audio/*" else "video/*"
    }
}
