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

// Preuzimanja: aktivna (trake kao na računaru) i završena.

@Composable
fun DownloadsScreen(active: List<ActiveJob>, history: List<HistoryItem>, tab: Int, onTab: (Int) -> Unit,
                    onCancel: (Long) -> Unit, onRetry: (Job) -> Unit, actions: ItemActions, onSettings: () -> Unit,
                    lastError: String? = null, onCopyReport: () -> Unit = {}) {
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(end = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.nav_downloads), fontSize = 30.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(start = 20.dp, top = 16.dp, bottom = 8.dp).weight(1f))
            SettingsButton(onSettings)
        }
        PrimaryTabRow(selectedTabIndex = tab, containerColor = Color.Transparent) {
            Tab(selected = tab == 0, onClick = { onTab(0) }, text = { Text(stringResource(R.string.tab_active, active.size)) })
            Tab(selected = tab == 1, onClick = { onTab(1) }, text = { Text(stringResource(R.string.tab_done)) })
        }
        if (tab == 0) {
            // Posljednja greška zamjenjuje „Ništa se ne preuzima" (bila je iscrtana preko tog teksta).
            if (active.isEmpty() && lastError != null) ErrorBanner(lastError, onCopyReport)
            else if (active.isEmpty()) Empty(stringResource(R.string.no_active))
            LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(active, key = { it.job.id }) { ActiveCard(it, onCancel, onRetry) }
            }
        } else {
            if (history.isEmpty()) Empty(stringResource(R.string.no_done))
            val today = startOfToday()
            LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                val (recent, older) = history.partition { it.finishedAt >= today }
                if (recent.isNotEmpty()) item { SectionTitle(stringResource(R.string.today)) }
                items(recent, key = { it.id }) { DoneCard(it, actions) }
                if (older.isNotEmpty()) item { SectionTitle(stringResource(R.string.earlier)) }
                items(older, key = { it.id }) { DoneCard(it, actions) }
            }
        }
    }
}

@Composable
internal fun Empty(text: String) = Text(text, Modifier.padding(24.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
internal fun SectionTitle(text: String) = Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 4.dp))

@Composable
internal fun ActiveCard(active: ActiveJob, onCancel: (Long) -> Unit, onRetry: (Job) -> Unit) {
    CardBox(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Thumb(active.job.thumbnail, null, active.job.title, 0, Modifier.width(104.dp).height(64.dp), active.job.isAudio,
                active.job.adult)
            Column(Modifier.weight(1f).padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(active.job.title, maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.SemiBold)
                val fraction = active.fraction
                // Iste trake kao na računaru: video plavo, zvuk i obrada ljubičasto, završeno zeleno.
                if (active.phase == Phase.DONE) {
                    AppProgressBar(1f, BarPhase.DONE)
                } else if (active.phase == Phase.CONVERTING && fraction != null) {
                    AppProgressBar(fraction, BarPhase.WORK)
                    Text("MP3 · ${(fraction * 100).toInt()}%", style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else if (active.phase == Phase.DOWNLOADING && fraction != null) {
                    AppProgressBar(fraction, if (active.job.isAudio || active.audioPart) BarPhase.AUDIO else BarPhase.VIDEO)
                    Row {
                        val context = LocalContext.current
                        val size = if (active.total > 0) "${formatSize(active.done.toDouble())} / ${formatSize(active.total.toDouble())}" else null
                        Text(listOfNotNull(size, formatSpeed(active.speed), formatEta(context, active.eta)).joinToString(" · "),
                            style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("${(fraction * 100).toInt()}%", style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else if (active.phase != Phase.QUEUED && active.phase != Phase.INTERRUPTED) {
                    AppProgressBar(null, BarPhase.WORK) // čitanje, spajanje, snimanje: traka klizi
                }
                Text(stringResource(when (active.phase) {
                    Phase.QUEUED -> R.string.phase_queued
                    Phase.READING -> R.string.status_reading
                    Phase.DOWNLOADING -> R.string.phase_downloading
                    Phase.CONVERTING -> R.string.status_converting
                    Phase.SAVING -> R.string.status_saving
                    Phase.DONE -> R.string.phase_done
                    Phase.INTERRUPTED -> R.string.phase_interrupted
                    Phase.NEEDS_ADULT -> R.string.phase_needs_adult
                }), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (active.phase == Phase.INTERRUPTED) TextButton(onClick = { onRetry(active.job) }) {
                    Text(stringResource(R.string.retry))
                }
                // 18+ bez potvrde: MainActivity pita jednim prozorom za sve koji čekaju.
                if (active.phase == Phase.NEEDS_ADULT) TextButton(onClick = { onRetry(active.job) }) {
                    Text(stringResource(R.string.adult_confirm))
                }
            }
            IconButton(onClick = { onCancel(active.job.id) }) { AppIcon(R.drawable.ic_close, tint = MaterialTheme.colorScheme.onSurface) }
        }
    }
}

@Composable
internal fun DoneCard(item: HistoryItem, actions: ItemActions) {
    if (item.failed) return FailedCard(item, actions)
    CardBox(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp)) {
            Thumb(item.thumbnail, item.uri, item.title, item.duration, Modifier.width(120.dp).height(80.dp), item.isAudio,
                item.adult)
            Column(Modifier.weight(1f).padding(start = 12.dp)) {
                Row(verticalAlignment = Alignment.Top) {
                    Text(item.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.weight(1f))
                    ItemMenu(item, actions)
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    AppIcon(R.drawable.ic_check_circle, Modifier.size(16.dp), tint = Brand.Green)
                    Text(stringResource(R.string.done_label), color = Brand.Green, style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(start = 4.dp))
                }
                Text("${item.format} • ${formatSize(item.size.toDouble())}", style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilledTonalButton(onClick = { actions.open(item) }, shape = RoundedCornerShape(10.dp)) {
                        AppIcon(R.drawable.ic_play, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurface)
                        Text(stringResource(R.string.open), Modifier.padding(start = 6.dp))
                    }
                    OutlinedButton(onClick = { actions.share(item) }, shape = RoundedCornerShape(10.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)) {
                        AppIcon(R.drawable.ic_share, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
        }
    }
}

/** Neuspjelo preuzimanje: naslov, poruka i link, uz „Pokušaj ponovo" i „Kopiraj link" (izvještaj je u meniju). */
@Composable
internal fun FailedCard(item: HistoryItem, actions: ItemActions) {
    CardBox(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp)) {
            Thumb(item.thumbnail, "", item.title, item.duration, Modifier.width(120.dp).height(80.dp), item.isAudio,
                item.adult)
            Column(Modifier.weight(1f).padding(start = 12.dp)) {
                Row(verticalAlignment = Alignment.Top) {
                    Text(item.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.weight(1f))
                    ItemMenu(item, actions)
                }
                Text(stringResource(R.string.failed_label), color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                Text(item.error, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall,
                    maxLines = 3, overflow = TextOverflow.Ellipsis)
                Text(item.url, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilledTonalButton(onClick = { actions.retry(item) }, shape = RoundedCornerShape(10.dp)) {
                        Text(stringResource(R.string.retry))
                    }
                    OutlinedButton(onClick = { actions.copyLink(item) }, shape = RoundedCornerShape(10.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)) {
                        AppIcon(R.drawable.ic_link, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
        }
    }
}

internal fun startOfToday(): Long = Calendar.getInstance().apply {
    set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
}.timeInMillis
