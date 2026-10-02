package io.github.abnps.videodownload

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Build
import android.net.Uri
import android.util.LruCache
import android.util.Size
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

/** Sličice u memoriji (najviše ~24 MB), da se lista ne učitava iznova pri svakom skrolu. */
private val cache = object : LruCache<String, Bitmap>(24 * 1024 * 1024) {
    override fun sizeOf(key: String, value: Bitmap) = value.byteCount
}

/** Parovi boja dok sličica ne stigne (isti kao u programu za računar), izbor po naslovu. */
private val placeholder = listOf(
    Color(0xFF3D7A5A) to Color(0xFF2B5A82), Color(0xFF8A3B6B) to Color(0xFF4B3F8F),
    Color(0xFF8A6A3B) to Color(0xFF8A3B4F), Color(0xFF3B5F8A) to Color(0xFF5B3F8F),
)

/**
 * Sličica videa: za preuzet fajl iz samog fajla (MediaStore), inače sa sajta. Dok ne stigne: dvobojni prelaz.
 * `duration` (sekunde) se crta kao oznaka u uglu, kao u dizajnu.
 */
@Composable
fun Thumb(remote: String, local: String?, seed: String, duration: Int, modifier: Modifier, isAudio: Boolean = false,
          adult: Boolean = false) {
    val context = LocalContext.current
    val key = local ?: remote
    var bitmap by remember(key) { mutableStateOf(cache.get(key)) }
    LaunchedEffect(key) {
        if (bitmap != null || key.isBlank()) return@LaunchedEffect
        bitmap = withContext(Dispatchers.IO) {
            // Prvo iz samog fajla (radi i bez interneta), pa sa sajta; zvučni fajl često nema sličicu.
            val fromFile = local?.let {
                runCatching { context.contentResolver.loadThumbnail(Uri.parse(it), Size(480, 270), null) }.getOrNull()
            }
            (fromFile ?: remote.takeIf { it.isNotBlank() }?.let { runCatching { fetch(it) }.getOrNull() })
                ?.also { cache.put(key, it) }
        }
    }
    val colors = placeholder[(seed.hashCode() and Int.MAX_VALUE) % placeholder.size]
    Box(modifier.clip(RoundedCornerShape(10.dp)).background(Brush.linearGradient(listOf(colors.first, colors.second)))) {
        val image = bitmap
        if (image != null) {
            // 18+ je uvijek zamućen (kao na računaru). Zamućenje postoji od Androida 12; na 10–11 tamni pokrivač.
            Image(image.asImageBitmap(), contentDescription = null, contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize().then(if (adult) Modifier.blur(18.dp) else Modifier))
            if (adult && Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
                Box(Modifier.matchParentSize().background(Color(0xF2202020)))
            }
        } else if (isAudio) {
            Icon(painterResource(R.drawable.ic_music), null, tint = Color.White, modifier = Modifier.align(Alignment.Center))
        }
        if (adult) {
            Text("18+", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.align(Alignment.Center).background(Color(0xCCD32F2F), RoundedCornerShape(5.dp))
                    .padding(horizontal = 7.dp, vertical = 2.dp))
        }
        if (duration > 0) {
            Text(formatDuration(duration), color = Color.White, fontSize = 11.sp,
                modifier = Modifier.align(Alignment.BottomEnd).padding(5.dp)
                    .background(Color(0xB3000000), RoundedCornerShape(4.dp)).padding(horizontal = 5.dp, vertical = 1.dp))
        }
    }
}

private fun fetch(url: String): Bitmap? {
    val connection = URL(url).openConnection() as HttpURLConnection
    connection.connectTimeout = 8000
    connection.readTimeout = 8000
    return try {
        connection.inputStream.use { BitmapFactory.decodeStream(it) }
    } finally {
        connection.disconnect()
    }
}

fun formatDuration(seconds: Int): String {
    val h = seconds / 3600
    val m = seconds % 3600 / 60
    val s = seconds % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, s) else "%02d:%02d".format(m, s)
}

/** „3,2 MB/s" ili null dok brzina nije poznata. */
fun formatSpeed(bytesPerSecond: Double): String? =
    if (bytesPerSecond > 0) formatSize(bytesPerSecond) + "/s" else null

/** „još 1:05" / „još 12 s" (kao na računaru) ili null dok nije poznato. */
fun formatEta(context: android.content.Context, seconds: Long): String? {
    if (seconds < 0) return null
    val text = when {
        seconds >= 3600 -> "%d:%02d:%02d".format(seconds / 3600, seconds % 3600 / 60, seconds % 60)
        seconds >= 60 -> "%d:%02d".format(seconds / 60, seconds % 60)
        else -> "$seconds s"
    }
    return context.getString(R.string.progress_eta, text)
}

fun formatSize(bytes: Double): String = when {
    bytes >= 1e9 -> "%.1f GB".format(bytes / 1e9)
    bytes >= 1e6 -> "%.0f MB".format(bytes / 1e6)
    else -> "%.1f MB".format(bytes / 1e6)
}
