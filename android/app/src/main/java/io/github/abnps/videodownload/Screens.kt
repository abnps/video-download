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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Calendar

// ---------- zajedničko ----------

@Composable
fun AppIcon(id: Int, modifier: Modifier = Modifier, tint: Color = MaterialTheme.colorScheme.onSurfaceVariant) =
    Icon(painterResource(id), contentDescription = null, modifier = modifier, tint = tint)

/** Zupčanik gore desno, kao u većini Android aplikacija: otvara Postavke. */
@Composable
fun SettingsButton(onClick: () -> Unit) = IconButton(onClick = onClick) {
    Icon(painterResource(R.drawable.ic_settings), contentDescription = stringResource(R.string.nav_settings),
        tint = MaterialTheme.colorScheme.onSurface)
}

@Composable
fun CardBox(modifier: Modifier = Modifier, onClick: (() -> Unit)? = null, content: @Composable () -> Unit) {
    val colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    val border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    if (onClick != null) {
        Card(onClick = onClick, modifier = modifier, shape = RoundedCornerShape(16.dp), colors = colors, border = border) {
            content()
        }
    } else {
        Card(modifier = modifier, shape = RoundedCornerShape(16.dp), colors = colors, border = border) { content() }
    }
}

@Composable
private fun ItemMenu(item: HistoryItem, actions: ItemActions) {
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }) { AppIcon(R.drawable.ic_more) }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            DropdownMenuItem(text = { Text(stringResource(R.string.open)) }, onClick = { open = false; actions.open(item) })
            DropdownMenuItem(text = { Text(stringResource(R.string.share)) }, onClick = { open = false; actions.share(item) })
            DropdownMenuItem(text = { Text(stringResource(R.string.remove_from_list)) },
                onClick = { open = false; actions.remove(item) })
        }
    }
}

/** Šta se može uraditi s gotovim fajlom (ekran Početna i Preuzimanja). */
class ItemActions(val open: (HistoryItem) -> Unit, val share: (HistoryItem) -> Unit, val remove: (HistoryItem) -> Unit)

// ---------- Početna ----------

@Composable
fun HomeScreen(
    link: String,
    onLinkChange: (String) -> Unit,
    onPaste: () -> Unit,
    onFind: () -> Unit,
    finding: Boolean,
    error: String?,
    onCopyReport: () -> Unit,
    onLogin: (() -> Unit)?,
    history: List<HistoryItem>,
    onShowAll: () -> Unit,
    actions: ItemActions,
    update: UpdateState,
    onInstallUpdate: () -> Unit,
    onSettings: () -> Unit,
) {
    var help by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(36.dp).background(MaterialTheme.colorScheme.primary, RoundedCornerShape(9.dp)),
                contentAlignment = Alignment.Center) {
                AppIcon(R.drawable.ic_download, Modifier.size(22.dp), tint = MaterialTheme.colorScheme.onPrimary)
            }
            Text("Video Download", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(start = 12.dp).weight(1f))
            SettingsButton(onSettings)
        }
        Spacer(Modifier.height(28.dp))
        Text(stringResource(R.string.home_title), fontSize = 34.sp, fontWeight = FontWeight.Bold, lineHeight = 38.sp)
        Text(stringResource(R.string.home_sub), style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        UpdateBanner(update, onInstallUpdate)
        Spacer(Modifier.height(20.dp))
        CardBox(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(stringResource(R.string.link_hint), style = MaterialTheme.typography.titleSmall)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = link, onValueChange = onLinkChange, singleLine = true, modifier = Modifier.weight(1f),
                        placeholder = { Text(stringResource(R.string.link_placeholder)) },
                        leadingIcon = { AppIcon(R.drawable.ic_link) }, shape = RoundedCornerShape(12.dp),
                    )
                    OutlinedButton(onClick = onPaste, shape = RoundedCornerShape(12.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 14.dp)) {
                        AppIcon(R.drawable.ic_paste, Modifier.size(18.dp))
                        Text(stringResource(R.string.paste), Modifier.padding(start = 6.dp))
                    }
                }
                Button(onClick = onFind, enabled = !finding && findUrl(link) != null,
                    modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(12.dp)) {
                    if (finding) {
                        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary)
                        Text(stringResource(R.string.finding), Modifier.padding(start = 10.dp))
                    } else {
                        Text(stringResource(R.string.find_video), fontSize = 16.sp)
                        AppIcon(R.drawable.ic_forward, Modifier.padding(start = 8.dp).size(20.dp),
                            tint = MaterialTheme.colorScheme.onPrimary)
                    }
                }
                if (error != null) {
                    Text(stringResource(R.string.status_failed, error), color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium)
                    if (onLogin != null) {
                        FilledTonalButton(onClick = onLogin) { Text(stringResource(R.string.login_button)) }
                    }
                    TextButton(onClick = onCopyReport) { Text(stringResource(R.string.copy_report)) }
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        Card(onClick = { help = true }, shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.55f)),
            modifier = Modifier.fillMaxWidth()) {
            Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(44.dp).background(MaterialTheme.colorScheme.surface, CircleShape),
                    contentAlignment = Alignment.Center) {
                    AppIcon(R.drawable.ic_share, Modifier.size(22.dp), tint = MaterialTheme.colorScheme.primary)
                }
                Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                    Text(stringResource(R.string.share_tip_title), fontWeight = FontWeight.Medium)
                    Text(stringResource(R.string.share_tip_text), style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                AppIcon(R.drawable.ic_chevron)
            }
        }
        if (history.isNotEmpty()) {
            Spacer(Modifier.height(24.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.recent), style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                TextButton(onClick = onShowAll) { Text(stringResource(R.string.show_all)) }
            }
            history.take(3).forEach { item ->
                Row(Modifier.fillMaxWidth().clickable { actions.open(item) }.padding(vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Thumb(item.thumbnail, item.uri, item.title, item.duration, Modifier.width(112.dp).height(64.dp), item.isAudio)
                    Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                        Text(item.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.Medium)
                        Text(item.format, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    AppIcon(R.drawable.ic_check_circle, Modifier.size(24.dp), tint = Brand.Green)
                    ItemMenu(item, actions)
                }
            }
        }
        Spacer(Modifier.height(16.dp))
    }
    if (help) {
        AlertDialog(onDismissRequest = { help = false }, confirmButton = {
            TextButton(onClick = { help = false }) { Text(stringResource(R.string.ok)) }
        }, title = { Text(stringResource(R.string.share_tip_title)) }, text = { Text(stringResource(R.string.share_tip_help)) })
    }
}

/** Nova verzija aplikacije: kartica s „Instaliraj", napredak preuzimanja ili greška. Ništa kad je sve ažurno. */
@Composable
fun UpdateBanner(update: UpdateState, onInstall: () -> Unit) {
    val text = when (update) {
        is UpdateState.Available -> stringResource(R.string.update_available, update.release.versionName)
        is UpdateState.Downloading -> stringResource(R.string.update_downloading, (update.fraction * 100).toInt())
        is UpdateState.Failed -> stringResource(R.string.update_failed, update.message)
        else -> return
    }
    Spacer(Modifier.height(16.dp))
    Card(shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Row(Modifier.padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            AppIcon(R.drawable.ic_download, Modifier.size(22.dp), tint = MaterialTheme.colorScheme.primary)
            Text(text, Modifier.weight(1f).padding(horizontal = 12.dp), color = MaterialTheme.colorScheme.onPrimaryContainer)
            if (update is UpdateState.Available) {
                Button(onClick = onInstall, shape = RoundedCornerShape(10.dp)) { Text(stringResource(R.string.update_install)) }
            }
        }
    }
}

// ---------- Izaberi kvalitet ----------

@Composable
fun QualityScreen(info: VideoInfo, defaultHeight: Int, onBack: () -> Unit, onDownload: (Job) -> Unit,
                  location: SaveLocation, onLocation: (SaveLocation) -> Unit) {
    var audio by remember { mutableStateOf(false) }
    val best = QualityOption(0, 0, info.video.firstOrNull()?.size ?: 0.0)
    val options = info.video.ifEmpty { listOf(best) }
    var chosen by remember {
        mutableStateOf(options.firstOrNull { defaultHeight == 0 || it.label <= defaultHeight } ?: options.first())
    }
    var pickLocation by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { AppIcon(R.drawable.ic_back, tint = MaterialTheme.colorScheme.onSurface) }
            Text(stringResource(R.string.choose_quality), style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold)
        }
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Box {
                Thumb(info.thumbnail, null, info.title, info.duration, Modifier.fillMaxWidth().aspectRatio(16f / 9f))
                Box(Modifier.align(Alignment.Center).size(56.dp).background(Color(0x99000000), CircleShape),
                    contentAlignment = Alignment.Center) {
                    AppIcon(R.drawable.ic_play, Modifier.size(32.dp), tint = Color.White)
                }
            }
            Text(info.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, maxLines = 3,
                overflow = TextOverflow.Ellipsis)
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                SegmentedButton(selected = !audio, onClick = { audio = false }, shape = SegmentedButtonDefaults.itemShape(0, 2),
                    icon = { AppIcon(R.drawable.ic_videocam, Modifier.size(18.dp)) }) { Text(stringResource(R.string.tab_video)) }
                SegmentedButton(selected = audio, onClick = { audio = true }, enabled = info.audioAvailable,
                    shape = SegmentedButtonDefaults.itemShape(1, 2),
                    icon = { AppIcon(R.drawable.ic_music, Modifier.size(18.dp)) }) { Text(stringResource(R.string.tab_audio)) }
            }
            if (!info.audioAvailable) Text(stringResource(R.string.audio_unavailable),
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (audio) {
                OptionRow(true, stringResource(R.string.best_audio), sizeText("M4A", info.audioSize)) {}
            } else {
                options.forEach { option ->
                    val title = if (option.label > 0) "${option.label}p" else stringResource(R.string.best_quality)
                    OptionRow(option == chosen, title, sizeText("MP4", option.size)) { chosen = option }
                }
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
        Button(onClick = {
            val label = if (audio) "M4A" else if (chosen.label > 0) "${chosen.label}p" else "MP4"
            onDownload(Job(System.currentTimeMillis(), info.url, info.title, info.thumbnail, info.duration, audio,
                if (audio) 0 else chosen.height, label))
        }, modifier = Modifier.fillMaxWidth().padding(20.dp).height(54.dp), shape = RoundedCornerShape(12.dp)) {
            AppIcon(R.drawable.ic_download, Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onPrimary)
            Text(stringResource(if (audio) R.string.download_btn_audio else R.string.download_btn_video),
                Modifier.padding(start = 10.dp), fontSize = 16.sp)
        }
    }
    if (pickLocation) {
        LocationDialog(location, onDismiss = { pickLocation = false }) { onLocation(it); pickLocation = false }
    }
}

@Composable
private fun sizeText(format: String, size: Double): String =
    if (size > 0) "$format • ${stringResource(R.string.about_size, formatSize(size))}"
    else "$format • ${stringResource(R.string.size_unknown)}"

@Composable
private fun OptionRow(selected: Boolean, title: String, subtitle: String, onClick: () -> Unit) {
    val border = if (selected) BorderStroke(2.dp, MaterialTheme.colorScheme.primary)
    else BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    Card(onClick = onClick, shape = RoundedCornerShape(14.dp), border = border, modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f)
        else MaterialTheme.colorScheme.surface)) {
        Row(Modifier.padding(horizontal = 8.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = selected, onClick = onClick)
            Column(Modifier.padding(start = 6.dp)) {
                Text(title, fontWeight = FontWeight.SemiBold)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
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

// ---------- Preuzimanja ----------

@Composable
fun DownloadsScreen(active: List<ActiveJob>, history: List<HistoryItem>, tab: Int, onTab: (Int) -> Unit,
                    onCancel: (Long) -> Unit, onRetry: (Job) -> Unit, actions: ItemActions, onSettings: () -> Unit) {
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
            if (active.isEmpty()) Empty(stringResource(R.string.no_active))
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
private fun Empty(text: String) = Text(text, Modifier.padding(24.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
private fun SectionTitle(text: String) = Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 4.dp))

@Composable
private fun ActiveCard(active: ActiveJob, onCancel: (Long) -> Unit, onRetry: (Job) -> Unit) {
    CardBox(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Thumb(active.job.thumbnail, null, active.job.title, 0, Modifier.width(104.dp).height(64.dp), active.job.isAudio)
            Column(Modifier.weight(1f).padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(active.job.title, maxLines = 1, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.SemiBold)
                val fraction = active.fraction
                if (active.phase == Phase.DOWNLOADING && fraction != null) {
                    LinearProgressIndicator(progress = { fraction }, modifier = Modifier.fillMaxWidth())
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
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                }
                Text(stringResource(when (active.phase) {
                    Phase.QUEUED -> R.string.phase_queued
                    Phase.READING -> R.string.status_reading
                    Phase.DOWNLOADING -> R.string.phase_downloading
                    Phase.SAVING -> R.string.status_saving
                    Phase.INTERRUPTED -> R.string.phase_interrupted
                }), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (active.phase == Phase.INTERRUPTED) TextButton(onClick = { onRetry(active.job) }) {
                    Text(stringResource(R.string.retry))
                }
            }
            IconButton(onClick = { onCancel(active.job.id) }) { AppIcon(R.drawable.ic_close, tint = MaterialTheme.colorScheme.onSurface) }
        }
    }
}

@Composable
private fun DoneCard(item: HistoryItem, actions: ItemActions) {
    CardBox(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp)) {
            Thumb(item.thumbnail, item.uri, item.title, item.duration, Modifier.width(120.dp).height(80.dp), item.isAudio)
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

private fun startOfToday(): Long = Calendar.getInstance().apply {
    set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
}.timeInMillis

// ---------- Postavke ----------

@Composable
fun SettingsScreen(quality: Int, onQuality: (Int) -> Unit, location: SaveLocation, onLocation: (SaveLocation) -> Unit,
                   onLanguage: () -> Unit, onOpenLink: (String) -> Unit, onInvite: () -> Unit,
                   instagram: Boolean, onLogin: () -> Unit, onLogout: () -> Unit, appVersion: String,
                   readerVersion: String, update: UpdateState, onCheckUpdate: () -> Unit, onInstallUpdate: () -> Unit,
                   onBack: () -> Unit) {
    var pickQuality by remember { mutableStateOf(false) }
    var pickLocation by remember { mutableStateOf(false) }
    var askLogout by remember { mutableStateOf(false) }
    var showLicenses by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
    // Standardna Android traka: strelica nazad + naslov (kao ekran „Izaberi kvalitet").
    Row(Modifier.padding(horizontal = 4.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onBack) { AppIcon(R.drawable.ic_back, tint = MaterialTheme.colorScheme.onSurface) }
        Text(stringResource(R.string.nav_settings), style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold)
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)) {
        UpdateBanner(update, onInstallUpdate)
        SettingRow(R.drawable.ic_videocam, stringResource(R.string.set_quality),
            if (quality == 0) stringResource(R.string.best_quality) else "${quality}p") { pickQuality = true }
        SettingRow(R.drawable.ic_folder, stringResource(R.string.set_location), locationName(location)) { pickLocation = true }
        SettingRow(R.drawable.ic_language, stringResource(R.string.set_language),
            LocalConfiguration.current.locales[0].displayLanguage,
            onClick = onLanguage)
        SettingRow(R.drawable.ic_link, stringResource(R.string.login_title),
            stringResource(if (instagram) R.string.login_on else R.string.login_off)) {
            if (instagram) askLogout = true else onLogin()
        }
        SettingRow(R.drawable.ic_share, stringResource(R.string.invite_title), stringResource(R.string.invite_sub),
            onClick = onInvite)
        SettingRow(R.drawable.ic_heart, stringResource(R.string.set_support), null) { onOpenLink(Links.SUPPORT) }
        SettingRow(R.drawable.ic_info, stringResource(R.string.set_terms), null) { onOpenLink(Links.site("terms.html")) }
        SettingRow(R.drawable.ic_info, stringResource(R.string.set_privacy), null) { onOpenLink(Links.site("privacy.html")) }
        SettingRow(R.drawable.ic_info, stringResource(R.string.set_licenses), null) { showLicenses = true }
        SettingRow(R.drawable.ic_download, stringResource(R.string.set_version),
            "$appVersion · ${stringResource(R.string.test_version)}", null)
        SettingRow(R.drawable.ic_download, stringResource(R.string.update_check),
            if (update is UpdateState.UpToDate) stringResource(R.string.update_none) else null, onClick = onCheckUpdate)
        SettingRow(R.drawable.ic_settings, stringResource(R.string.set_reader), readerVersion, null)
    }
    }
    if (showLicenses) LicensesDialog { showLicenses = false }
    if (askLogout) {
        AlertDialog(onDismissRequest = { askLogout = false },
            title = { Text(stringResource(R.string.logout_title)) },
            confirmButton = { TextButton(onClick = { onLogout(); askLogout = false }) { Text(stringResource(R.string.logout)) } },
            dismissButton = { TextButton(onClick = { askLogout = false }) { Text(stringResource(R.string.dialog_cancel)) } })
    }
    if (pickQuality) {
        AlertDialog(onDismissRequest = { pickQuality = false }, confirmButton = {},
            title = { Text(stringResource(R.string.set_quality)) }, text = {
                Column {
                    listOf(0, 1080, 720, 480).forEach { value ->
                        Row(Modifier.fillMaxWidth().clickable { onQuality(value); pickQuality = false }.padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            RadioButton(selected = value == quality, onClick = { onQuality(value); pickQuality = false })
                            Text(if (value == 0) stringResource(R.string.best_quality) else "${value}p", Modifier.padding(start = 8.dp))
                        }
                    }
                }
            })
    }
    if (pickLocation) {
        LocationDialog(location, onDismiss = { pickLocation = false }) { onLocation(it); pickLocation = false }
    }
}

@Composable
private fun SettingRow(icon: Int, title: String, value: String?, onClick: (() -> Unit)?) {
    CardBox(Modifier.fillMaxWidth(), onClick = onClick) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            AppIcon(icon, Modifier.size(24.dp), tint = MaterialTheme.colorScheme.primary)
            Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                Text(title)
                if (value != null) {
                    Text(value, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            if (onClick != null) AppIcon(R.drawable.ic_chevron)
        }
    }
}


/** Licence komponenti iz APK-a (assets/licenses, pravi ih tools/android_licenses.py): spisak pa puni tekstovi. */
@Composable
fun LicensesDialog(onClose: () -> Unit) {
    val context = LocalContext.current
    val text = remember {
        val folder = "licenses"
        val names = context.assets.list(folder).orEmpty().sorted()
        val notices = context.assets.open("$folder/NOTICES.txt").bufferedReader().use { it.readText() }
        notices + names.filter { it != "NOTICES.txt" }.joinToString("") { name ->
            "\n\n===== $name =====\n\n" + context.assets.open("$folder/$name").bufferedReader().use { it.readText() }
        }
    }
    AlertDialog(onDismissRequest = onClose,
        title = { Text(stringResource(R.string.set_licenses)) },
        text = {
            Text(text, Modifier.verticalScroll(rememberScrollState()), fontFamily = FontFamily.Monospace,
                fontSize = 11.sp, lineHeight = 14.sp)
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.dialog_close)) } })
}
