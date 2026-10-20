package io.github.abnps.videodownload

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONArray

/** Jedna verzija iz „Šta je novo" (assets/changelog.json pravi tools/android_changelog.py iz videodl/changelog.py). */
data class ReleaseNotes(val version: String, val date: String, val items: List<String>)

fun loadReleaseNotes(context: Context, count: Int = 3): List<ReleaseNotes> = runCatching {
    val language = Links.language()
    val data = JSONArray(context.assets.open("changelog.json").bufferedReader().use { it.readText() })
    (0 until minOf(count, data.length())).map { index ->
        val entry = data.getJSONObject(index)
        val notes = entry.getJSONObject("notes")
        val list = notes.optJSONArray(language) ?: notes.getJSONArray("en")
        ReleaseNotes(entry.getString("version"), entry.getString("date"), (0 until list.length()).map { list.getString(it) })
    }
}.getOrDefault(emptyList())

/** Postavke → Verzija: šta je novo u posljednje 3 verzije (računar i Android zajedno, kao bilješke izdanja). */
@Composable
fun WhatsNewDialog(onClose: () -> Unit) {
    val context = LocalContext.current
    val releases = remember { loadReleaseNotes(context) }
    AlertDialog(onDismissRequest = onClose,
        title = { Text(stringResource(R.string.whats_new_title)) },
        text = {
            Column(Modifier.heightIn(max = 480.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)) {
                releases.forEach { release ->
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("${release.version} · ${release.date}", fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary)
                        release.items.forEach { item ->
                            Row(Modifier.fillMaxWidth()) {
                                Text("•", Modifier.padding(end = 8.dp))
                                Text(item, style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.whats_new_close)) } })
}
