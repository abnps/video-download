package io.github.abnps.videodownload

import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
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

// Izaberi kvalitet: video ili zvuk (MP3/M4A), titlovi, isječak, gdje se čuva.

@Composable
fun QualityScreen(info: VideoInfo, defaultHeight: Int, onBack: () -> Unit, onDownload: (Job) -> Unit,
                  location: SaveLocation, onLocation: (SaveLocation) -> Unit) {
    var audio by remember { mutableStateOf(false) }
    var mp3 by remember { mutableStateOf(true) } // zvuk: MP3 (kao na računaru) ili originalni M4A
    val best = QualityOption(0, 0, info.video.firstOrNull()?.size ?: 0.0)
    val options = info.video.ifEmpty { listOf(best) }
    var chosen by remember {
        mutableStateOf(options.firstOrNull { defaultHeight == 0 || it.label <= defaultHeight } ?: options.first())
    }
    var pickLocation by remember { mutableStateOf(false) }
    var askAdult by remember { mutableStateOf<Job?>(null) }
    var subtitles by remember { mutableStateOf(false) }
    var clip by remember { mutableStateOf(false) }
    var clipFrom by remember { mutableStateOf("") }
    var clipTo by remember { mutableStateOf("") }
    val clipRange = parseClip(clipFrom, clipTo, info.duration)
    // Roditeljska zaštita: 18+ se ne preuzima i ne nudi se potvrda.
    val blockedByParental = info.adult && Parental.enabled(LocalContext.current)
    fun start(asAudio: Boolean, asMp3: Boolean) {
        val label = if (asAudio) (if (asMp3) DownloadService.MP3_LABEL else "M4A") else if (chosen.label > 0) "${chosen.label}p" else "MP4"
        val range = if (clip) clipRange else null
        val job = Job(System.currentTimeMillis(), info.url, info.title, info.thumbnail, info.duration, asAudio,
            if (asAudio) 0 else chosen.height, label, adult = info.adult, subtitles = subtitles && !asAudio,
            clipStart = range?.first ?: -1, clipEnd = range?.second ?: -1)
        if (info.adult) askAdult = job else onDownload(job)
    }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { AppIcon(R.drawable.ic_back, tint = MaterialTheme.colorScheme.onSurface) }
            Text(stringResource(R.string.choose_quality), style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold)
        }
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Box {
                Thumb(info.thumbnail, null, info.title, info.duration, Modifier.fillMaxWidth().aspectRatio(16f / 9f),
                    adult = info.adult)
                // Brzo preuzimanje jednim dodirom (kao kod sličnih aplikacija): zvuk kao MP3 ili video u
                // izabranom kvalitetu, bez traženja dugmeta ispod. Isti posao kao glavno dugme.
                Row(Modifier.align(Alignment.BottomEnd).padding(10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    QuickButton(R.drawable.ic_music, stringResource(R.string.quick_audio),
                        enabled = !blockedByParental) { start(true, true) }
                    QuickButton(R.drawable.ic_videocam, stringResource(R.string.quick_video),
                        enabled = !blockedByParental) { start(false, mp3) }
                }
            }
            Text(info.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, maxLines = 3,
                overflow = TextOverflow.Ellipsis)
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                SegmentedButton(selected = !audio, onClick = { audio = false }, shape = SegmentedButtonDefaults.itemShape(0, 2),
                    icon = { AppIcon(R.drawable.ic_videocam, Modifier.size(18.dp)) }) { Text(stringResource(R.string.tab_video)) }
                SegmentedButton(selected = audio, onClick = { audio = true; if (!info.audioAvailable) mp3 = true },
                    shape = SegmentedButtonDefaults.itemShape(1, 2),
                    icon = { AppIcon(R.drawable.ic_music, Modifier.size(18.dp)) }) { Text(stringResource(R.string.tab_audio)) }
            }
            if (blockedByParental) Text(stringResource(R.string.parental_blocked),
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.error)
            if (audio) {
                // MP3 192 kbps: veličina ≈ trajanje × 24 KB/s.
                OptionRow(mp3, "MP3 · ${Mp3.KBPS} kbps", sizePills("MP3", info.duration * Mp3.KBPS * 125.0)) { mp3 = true }
                // Bez posebnog zvuka nema originalnog M4A; MP3 se pravi iz videa (preuzimanje je veće).
                if (info.audioAvailable) OptionRow(!mp3, stringResource(R.string.audio_m4a_original),
                    sizePills("M4A", info.audioSize)) { mp3 = false }
                else Text(stringResource(R.string.audio_unavailable),
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                options.forEach { option ->
                    val title = if (option.label > 0) "${option.label}p" else stringResource(R.string.best_quality)
                    OptionRow(option == chosen, title, sizePills("MP4", option.size)) { chosen = option }
                }
                CheckRow(subtitles, stringResource(R.string.subtitles_option), stringResource(R.string.subtitles_note)) {
                    subtitles = it
                }
            }
            CheckRow(clip, stringResource(R.string.clip_option), stringResource(R.string.clip_note)) { clip = it }
            if (clip) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(clipFrom, { clipFrom = it.take(8) }, Modifier.weight(1f), singleLine = true,
                    label = { Text(stringResource(R.string.clip_from)) }, placeholder = { Text("0:30") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
                OutlinedTextField(clipTo, { clipTo = it.take(8) }, Modifier.weight(1f), singleLine = true,
                    label = { Text(stringResource(R.string.clip_to)) }, placeholder = { Text(formatDuration(info.duration)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    isError = (clipFrom.isNotBlank() || clipTo.isNotBlank()) && clipRange == null)
            }
            CardBox(Modifier.fillMaxWidth(), onClick = { pickLocation = true }) {
                Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    AppIcon(R.drawable.ic_folder, Modifier.size(26.dp), tint = MaterialTheme.colorScheme.primary)
                    Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                        Text(stringResource(R.string.save_to))
                        Text(locationName(location), style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    AppIcon(R.drawable.ic_chevron)
                }
            }
        }
        Button(onClick = { start(audio, mp3) }, enabled = !blockedByParental && (!clip || clipRange != null), modifier = Modifier.fillMaxWidth().padding(20.dp).height(54.dp),
            shape = RoundedCornerShape(12.dp)) {
            AppIcon(R.drawable.ic_download, Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onPrimary)
            Text(stringResource(if (audio) R.string.download_btn_audio else R.string.download_btn_video),
                Modifier.padding(start = 10.dp), fontSize = 16.sp)
        }
    }
    askAdult?.let { job ->
        AdultDialog(1, onCancel = { askAdult = null }) { askAdult = null; onDownload(job.copy(adultOk = true)) }
    }
    if (pickLocation) {
        LocationDialog(location, onDismiss = { pickLocation = false }) { onLocation(it); pickLocation = false }
    }
}

@Composable
internal fun sizePills(format: String, size: Double): List<String> =
    listOf(format, if (size > 0) stringResource(R.string.about_size, formatSize(size)) else stringResource(R.string.size_unknown))

/** Okruglo dugme preko sličice (zvuk / video jednim dodirom). */
@Composable
internal fun QuickButton(icon: Int, description: String, enabled: Boolean, onClick: () -> Unit) {
    IconButton(onClick = onClick, enabled = enabled, modifier = Modifier.size(52.dp)
        .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.92f), RoundedCornerShape(16.dp))
        .semantics { contentDescription = description }) {
        AppIcon(icon, Modifier.size(26.dp), tint = MaterialTheme.colorScheme.onPrimaryContainer)
    }
}

@Composable
internal fun OptionRow(selected: Boolean, title: String, pills: List<String>, onClick: () -> Unit) {
    // One UI 9: ispunjene zaobljene kartice; izabrana dobija boju aplikacije i tanak obojen rub.
    val border = if (selected) BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary) else null
    Card(onClick = onClick, shape = RoundedCornerShape(22.dp), border = border, modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer
        else MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Row(Modifier.padding(horizontal = 8.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = selected, onClick = onClick)
            Column(Modifier.padding(start = 6.dp)) {
                Text(title, fontWeight = FontWeight.SemiBold)
                PillRow(pills, Modifier.padding(top = 4.dp))
            }
        }
    }
}

@Composable
fun locationName(location: SaveLocation): String =
    stringResource(if (location == SaveLocation.DOWNLOADS) R.string.loc_downloads else R.string.loc_gallery)

@Composable
fun LocationDialog(current: SaveLocation, onDismiss: () -> Unit, onPick: (SaveLocation) -> Unit) {
    AlertDialog(onDismissRequest = onDismiss, confirmButton = {}, title = { Text(stringResource(R.string.save_to)) }, text = {
        Column {
            SaveLocation.entries.forEach { value ->
                Row(Modifier.fillMaxWidth().clickable { onPick(value) }.padding(vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = value == current, onClick = { onPick(value) })
                    Text(locationName(value), Modifier.padding(start = 8.dp))
                }
            }
        }
    })
}

/** Red s kvačicom i kratkim objašnjenjem (titlovi, isječak). */
@Composable
internal fun CheckRow(checked: Boolean, title: String, note: String, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!checked) }, verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onChange)
        Column(Modifier.weight(1f)) {
            Text(title)
            Text(note, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/** „2:30", „150" ili „1:02:03" u sekunde; null ako nije ispravno. */
fun parseClock(text: String): Int? {
    val parts = text.trim().split(":")
    if (parts.isEmpty() || parts.size > 3 || parts.any { it.isEmpty() || !it.all(Char::isDigit) }) return null
    val numbers = parts.map { it.toIntOrNull() ?: return null }
    if (numbers.drop(1).any { it >= 60 }) return null
    return numbers.fold(0) { total, value -> total * 60 + value }
}

/** Isječak od–do (prazno „do" = do kraja); null kad nije ispravan ili je van trajanja videa. */
fun parseClip(from: String, to: String, duration: Int): Pair<Int, Int>? {
    val start = if (from.isBlank()) 0 else parseClock(from) ?: return null
    val end = if (to.isBlank()) duration else parseClock(to) ?: return null
    return if (start >= 0 && end > start && (duration <= 0 || end <= duration)) start to end else null
}
