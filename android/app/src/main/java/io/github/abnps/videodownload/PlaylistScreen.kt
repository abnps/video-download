package io.github.abnps.videodownload

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.RadioButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Calendar

// Plejlista: izbor videa i potvrda 18+ (jedan prozor za više videa).

/** Spisak videa iz plejliste: izbor (sve ili neki), video ili zvuk, pa redom preuzimanje kao zasebni poslovi. */
@Composable
fun PlaylistScreen(playlist: PlaylistInfo, defaultHeight: Int, onBack: () -> Unit, onDownload: (List<Job>) -> Unit) {
    val parental = Parental.enabled(LocalContext.current)
    val allowed = playlist.entries.indices.filter { !(parental && playlist.entries[it].adult) }
    val selected = remember(playlist) { mutableStateListOf<Int>().apply { addAll(allowed) } }
    var audio by remember { mutableStateOf(false) }
    var mp3 by remember { mutableStateOf(true) }
    var askAdult by remember { mutableStateOf<List<Job>?>(null) }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { AppIcon(R.drawable.ic_back, tint = MaterialTheme.colorScheme.onSurface) }
            Column(Modifier.weight(1f)) {
                Text(playlist.title.ifBlank { stringResource(R.string.playlist) }, style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(pluralStringResource(R.plurals.playlist_count, playlist.entries.size, playlist.entries.size),
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            val all = selected.size == allowed.size
            TextButton(onClick = { selected.clear(); if (!all) selected.addAll(allowed) }) {
                Text(stringResource(if (all) R.string.select_none else R.string.select_all))
            }
        }
        Column(Modifier.padding(horizontal = 20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                SegmentedButton(selected = !audio, onClick = { audio = false }, shape = SegmentedButtonDefaults.itemShape(0, 2),
                    icon = { AppIcon(R.drawable.ic_videocam, Modifier.size(18.dp)) }) { Text(stringResource(R.string.tab_video)) }
                SegmentedButton(selected = audio, onClick = { audio = true }, shape = SegmentedButtonDefaults.itemShape(1, 2),
                    icon = { AppIcon(R.drawable.ic_music, Modifier.size(18.dp)) }) { Text(stringResource(R.string.tab_audio)) }
            }
            if (audio) Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ChoiceButton(mp3, "MP3 · ${Mp3.KBPS} kbps") { mp3 = true }
                ChoiceButton(!mp3, "M4A") { mp3 = false }
            } else Text(stringResource(R.string.playlist_quality,
                if (defaultHeight > 0) "${defaultHeight}p" else stringResource(R.string.best_quality)),
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        LazyColumn(Modifier.weight(1f), contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items(playlist.entries.size) { index ->
                val entry = playlist.entries[index]
                val checked = index in selected
                val canSelect = index in allowed
                Row(Modifier.fillMaxWidth().clickable(enabled = canSelect) { if (checked) selected.remove(index) else selected.add(index) }
                    .padding(4.dp), verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = checked, enabled = canSelect,
                        onCheckedChange = { if (it) selected.add(index) else selected.remove(index) })
                    Thumb(entry.thumbnail, null, entry.title, entry.duration, Modifier.width(96.dp).height(54.dp), audio,
                        entry.adult)
                    Text(entry.title, Modifier.weight(1f).padding(start = 10.dp), maxLines = 2,
                        overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
        Button(onClick = {
            val now = System.currentTimeMillis()
            val label = if (audio) (if (mp3) DownloadService.MP3_LABEL else "M4A")
                else if (defaultHeight > 0) "${defaultHeight}p" else "MP4"
            val jobs = selected.sorted().mapIndexed { order, index ->
                val e = playlist.entries[index]
                Job(now + order, e.url, e.title, e.thumbnail, e.duration, audio, if (audio) 0 else defaultHeight, label,
                    adult = e.adult)
            }
            // Videe koje je sajt već u spisku označio kao 18+ potvrđuješ odmah, jednim prozorom; ostale
            // (oznaka se vidi tek pri čitanju) pita lista Preuzimanja.
            if (jobs.any { it.adult }) askAdult = jobs else onDownload(jobs)
        }, enabled = selected.isNotEmpty(), modifier = Modifier.fillMaxWidth().padding(20.dp).height(54.dp),
            shape = RoundedCornerShape(12.dp)) {
            AppIcon(R.drawable.ic_download, Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onPrimary)
            Text(pluralStringResource(R.plurals.download_selected, selected.size, selected.size),
                Modifier.padding(start = 10.dp), fontSize = 16.sp)
        }
    }
    askAdult?.let { jobs ->
        AdultDialog(jobs.count { it.adult }, onCancel = { askAdult = null }) {
            askAdult = null
            onDownload(jobs.map { if (it.adult) it.copy(adultOk = true) else it })
        }
    }
}

@Composable
internal fun ChoiceButton(selected: Boolean, text: String, onClick: () -> Unit) {
    if (selected) FilledTonalButton(onClick = onClick) { Text(text) } else OutlinedButton(onClick = onClick) { Text(text) }
}

/** Potvrda 18+ (kao na računaru): pri svakom preuzimanju, više videa = jedan prozor. Ne pamti se. */
@Composable
fun AdultDialog(count: Int, onCancel: () -> Unit, onConfirm: () -> Unit) {
    AlertDialog(onDismissRequest = onCancel,
        title = { Text(stringResource(R.string.adult_title)) },
        text = {
            Text(if (count > 1) pluralStringResource(R.plurals.adult_text_many, count, count)
                 else stringResource(R.string.adult_text))
        },
        confirmButton = { TextButton(onClick = onConfirm) { Text(stringResource(R.string.adult_confirm)) } },
        dismissButton = { TextButton(onClick = onCancel) { Text(stringResource(R.string.dialog_cancel)) } })
}
