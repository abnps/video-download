package io.github.abnps.videodownload

import android.Manifest
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp

/** Jedan ekran: link (iz „Podijeli" ili zalijepljen), dva dugmeta, stanje preuzimanja. */
class MainActivity : ComponentActivity() {
    private val link = mutableStateOf("")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        takeSharedLink(intent)
        askForNotifications()
        setContent { AppTheme { Screen() } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        takeSharedLink(intent)
    }

    private fun takeSharedLink(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        findUrl(intent.getStringExtra(Intent.EXTRA_TEXT))?.let { link.value = it }
    }

    private fun askForNotifications() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
    }

    private fun paste() {
        val clip = getSystemService(ClipboardManager::class.java).primaryClip
        val text = clip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this)?.toString()
        findUrl(text)?.let { link.value = it }
    }

    private fun copyReport() {
        val text = com.chaquo.python.Python.getInstance().getModule("vd_core")
            .callAttr("report", cacheDir.absolutePath).toString()
        getSystemService(ClipboardManager::class.java)
            .setPrimaryClip(android.content.ClipData.newPlainText("Video Download", text))
        android.widget.Toast.makeText(this, R.string.report_copied, android.widget.Toast.LENGTH_SHORT).show()
    }

    @Composable
    private fun Screen() {
        val status by DownloadState.status.collectAsState()
        val busy = status is DownloadStatus.Reading || status is DownloadStatus.Downloading ||
            status is DownloadStatus.Saving
        Column(
            Modifier.fillMaxSize().safeDrawingPadding().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineMedium)
            OutlinedTextField(
                value = link.value, onValueChange = { link.value = it },
                label = { Text(stringResource(R.string.link_hint)) },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { paste() }) { Text(stringResource(R.string.paste)) }
            }
            val url = findUrl(link.value)
            Button(onClick = { url?.let { DownloadService.start(this@MainActivity, it, false) } },
                enabled = url != null && !busy, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.download_video))
            }
            OutlinedButton(onClick = { url?.let { DownloadService.start(this@MainActivity, it, true) } },
                enabled = url != null && !busy, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.download_audio))
            }
            if (url == null && link.value.isBlank()) Text(stringResource(R.string.no_link))
            StatusView(status)
            Text(stringResource(R.string.saved_where), style = MaterialTheme.typography.bodySmall)
            Text(stringResource(R.string.prototype_note), style = MaterialTheme.typography.bodySmall)
        }
    }

    @Composable
    private fun StatusView(status: DownloadStatus) {
        when (status) {
            DownloadStatus.Idle -> Unit
            DownloadStatus.Reading -> {
                Text(stringResource(R.string.status_reading))
                LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            is DownloadStatus.Downloading -> {
                val percent = ((status.fraction ?: 0f) * 100).toInt()
                Text(stringResource(R.string.status_downloading, percent))
                if (status.fraction != null) {
                    LinearProgressIndicator(progress = { status.fraction }, modifier = Modifier.fillMaxWidth())
                } else {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                }
            }
            DownloadStatus.Saving -> Text(stringResource(R.string.status_saving))
            is DownloadStatus.Done -> {
                Text(stringResource(R.string.status_done, status.title))
                TextButton(onClick = {
                    startActivity(Intent(Intent.ACTION_VIEW)
                        .setDataAndType(status.uri, if (status.isAudio) "audio/*" else "video/*")
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
                }) { Text(stringResource(R.string.open)) }
            }
            is DownloadStatus.Failed -> {
                Text(stringResource(R.string.status_failed, status.message), color = MaterialTheme.colorScheme.error)
                // Probna faza: sažetak dnevnika u clipboard, pa ga korisnik zalijepi u poruku (bez kabla i adb-a).
                OutlinedButton(onClick = { copyReport() }) { Text(stringResource(R.string.copy_report)) }
            }
            DownloadStatus.Cancelled -> Text(stringResource(R.string.status_cancelled))
        }
    }
}

private val URL = Regex("""https?://[^\s<>"']+""")

/** Prvi link u tekstu (aplikacije često dijele „Naslov videa https://…"). */
fun findUrl(text: String?): String? = text?.let { URL.find(it)?.value?.trimEnd('.', ',', ')', ']') }

@Composable
private fun AppTheme(content: @Composable () -> Unit) {
    val accent = Color(0xFF6C4CE0) // ista ljubičasta kao ikona i desktop program
    val colors = if (isSystemInDarkTheme()) darkColorScheme(primary = Color(0xFF9C86FF))
    else lightColorScheme(primary = accent)
    MaterialTheme(colorScheme = colors) { Surface(Modifier.fillMaxSize()) { content() } }
}
