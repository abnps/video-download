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
import androidx.compose.material3.HorizontalDivider
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

// Početna: link, Preuzmi video, nedavno preuzeto, ponuda ažuriranja.

@Composable
fun HomeScreen(
    link: String,
    onLinkChange: (String) -> Unit,
    onPaste: () -> Unit,
    onFind: () -> Unit,
    finding: Boolean,
    error: String?,
    onCopyReport: () -> Unit,
    loginSite: LoginSite?,
    onLogin: (LoginSite) -> Unit,
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
                    // Prijava samo za sajt kojem link pripada (Instagram ili TikTok).
                    if (loginSite != null) {
                        FilledTonalButton(onClick = { onLogin(loginSite) }) { Text(stringResource(loginSite.button)) }
                    }
                    TextButton(onClick = onCopyReport) { Text(stringResource(R.string.copy_report)) }
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        Card(onClick = { help = true }, shape = RoundedCornerShape(26.dp),
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
            // One UI: sivi naslov grupe i sve stavke u jednoj zaobljenoj kartici, s tankim linijama između.
            Row(Modifier.padding(start = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.recent), style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                TextButton(onClick = onShowAll) { Text(stringResource(R.string.show_all)) }
            }
            CardBox(Modifier.fillMaxWidth()) { Column {
            history.take(3).forEachIndexed { index, item ->
                if (index > 0) HorizontalDivider(Modifier.padding(start = 140.dp, end = 16.dp),
                    color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                Row(Modifier.fillMaxWidth().clickable { actions.open(item) }.padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Thumb(item.thumbnail, item.uri, item.title, item.duration, Modifier.width(112.dp).height(64.dp), item.isAudio,
                        item.adult)
                    Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                        Text(item.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontWeight = FontWeight.Medium)
                        Text(item.format, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    AppIcon(R.drawable.ic_check_circle, Modifier.size(24.dp), tint = Brand.Green)
                    ItemMenu(item, actions)
                }
            }
            } }
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
