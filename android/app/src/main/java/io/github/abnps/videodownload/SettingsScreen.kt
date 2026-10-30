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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Switch
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
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.compose.ui.unit.sp
import java.util.Calendar

// Postavke: kvalitet, lokacija, jezik, Instagram, roditeljska zaštita, licence, ažuriranje.

@Composable
fun SettingsScreen(quality: Int, onQuality: (Int) -> Unit, location: SaveLocation, onLocation: (SaveLocation) -> Unit,
                   onLanguage: () -> Unit, onOpenLink: (String) -> Unit, onInvite: () -> Unit, onFeedback: () -> Unit,
                   loggedIn: Set<LoginSite>, onLogin: (LoginSite) -> Unit, onLogout: (LoginSite) -> Unit, appVersion: String,
                   readerVersion: String, update: UpdateState, onCheckUpdate: () -> Unit, onInstallUpdate: () -> Unit,
                   onBack: () -> Unit, onAchievements: () -> Unit = {}) {
    var pickQuality by remember { mutableStateOf(false) }
    var pickLocation by remember { mutableStateOf(false) }
    var askLogout by remember { mutableStateOf<LoginSite?>(null) }
    var showLicenses by remember { mutableStateOf(false) }
    var showWhatsNew by remember { mutableStateOf(false) }
    val context = LocalContext.current
    Column(Modifier.fillMaxSize()) {
    // One UI 9 stil (Ahmed 3.10.2026): strelica gore, veliki naslov nisko u zaglavlju — dohvatljiv palcem.
    IconButton(onClick = onBack, modifier = Modifier.padding(start = 4.dp, top = 4.dp)) {
        AppIcon(R.drawable.ic_back, tint = MaterialTheme.colorScheme.onSurface)
    }
    Box(Modifier.fillMaxWidth().height(120.dp).padding(horizontal = 24.dp), contentAlignment = Alignment.BottomStart) {
        Text(stringResource(R.string.nav_settings), fontSize = 34.sp, fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 12.dp))
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)) {
        UpdateBanner(update, onInstallUpdate)
        // Moderne postavke (Ahmed 3.10.2026): grupe u zaobljenim karticama, mreže na jednom mjestu.
        SettingsGroup(stringResource(R.string.settings_downloads)) {
            GroupRow(OneUi.Blue, R.drawable.ic_videocam, stringResource(R.string.set_quality),
                if (quality == 0) stringResource(R.string.best_quality) else "${quality}p", onClick = { pickQuality = true },
                info = stringResource(R.string.info_quality))
            GroupDivider()
            GroupRow(OneUi.Orange, R.drawable.ic_folder, stringResource(R.string.set_location), locationName(location),
                onClick = { pickLocation = true }, info = stringResource(R.string.info_location))
            GroupDivider()
            var quick by remember { mutableStateOf(Settings.quickShare(context)) }
            val toggleQuick = { quick = !quick; Settings.setQuickShare(context, quick) }
            GroupRow(OneUi.Green, R.drawable.ic_download, stringResource(R.string.quick_title),
                stringResource(if (quick) R.string.quick_on else R.string.quick_off), onClick = toggleQuick,
                info = stringResource(R.string.info_quick)) {
                Switch(checked = quick, onCheckedChange = { toggleQuick() })
            }
            GroupDivider()
            // Jednokratno: poslije jednog videa se samo isključi (Settings.takeMuteNext); pri povratku se čita ponovo.
            var muteNext by remember { mutableStateOf(Settings.muteNext(context)) }
            LifecycleResumeEffect(Unit) {
                muteNext = Settings.muteNext(context)
                onPauseOrDispose { }
            }
            val toggleMute = { muteNext = !muteNext; Settings.setMuteNext(context, muteNext) }
            GroupRow(OneUi.Purple, R.drawable.ic_videocam, stringResource(R.string.mute_next_title),
                stringResource(if (muteNext) R.string.mute_next_on else R.string.mute_next_off), onClick = toggleMute,
                info = stringResource(R.string.info_mute_next)) {
                Switch(checked = muteNext, onCheckedChange = { toggleMute() })
            }
        }
        SettingsGroup(stringResource(R.string.settings_accounts), stringResource(R.string.settings_accounts_note)) {
            LoginSite.entries.forEachIndexed { index, site ->
                if (index > 0) GroupDivider()
                val on = site in loggedIn
                AccountRow(site, on) { if (on) askLogout = site else onLogin(site) }
            }
        }
        SettingsGroup(stringResource(R.string.settings_app)) {
            if (ThemeState.supported) {
                val toggleColors = { ThemeState.set(context, !ThemeState.systemColors) }
                GroupRow(OneUi.Pink, R.drawable.ic_heart, stringResource(R.string.system_colors_title),
                    stringResource(if (ThemeState.systemColors) R.string.system_colors_on else R.string.system_colors_off),
                    onClick = toggleColors, info = stringResource(R.string.info_colors)) {
                    Switch(checked = ThemeState.systemColors, onCheckedChange = { toggleColors() })
                }
                GroupDivider()
            }
            GroupRow(OneUi.Teal, R.drawable.ic_language, stringResource(R.string.set_language),
                LocalConfiguration.current.locales[0].displayLanguage, onClick = onLanguage,
                info = stringResource(R.string.info_language))
            GroupDivider()
            GroupRow(OneUi.Blue, R.drawable.ic_download, stringResource(R.string.update_check),
                if (update is UpdateState.UpToDate) stringResource(R.string.update_none) else null, onClick = onCheckUpdate,
                info = stringResource(R.string.info_update))
            GroupDivider()
            GroupRow(OneUi.Gray, R.drawable.ic_settings, stringResource(R.string.set_version),
                "$appVersion · ${stringResource(R.string.test_version)} · yt-dlp $readerVersion\n" +
                    stringResource(R.string.whats_new_sub), onClick = { showWhatsNew = true },
                info = stringResource(R.string.info_version))
        }
        SettingsGroup(stringResource(R.string.settings_support)) {
            GroupRow(OneUi.Orange, R.drawable.ic_check_circle, stringResource(R.string.badge_title),
                stringResource(R.string.badge_settings_sub, Achievements.downloadCount), onClick = onAchievements,
                info = stringResource(R.string.info_badges))
            GroupDivider()
            GroupRow(OneUi.Orange, R.drawable.ic_info, stringResource(R.string.feedback_title), stringResource(R.string.feedback_sub),
                onClick = onFeedback, info = stringResource(R.string.info_feedback))
            GroupDivider()
            GroupRow(OneUi.Purple, R.drawable.ic_share, stringResource(R.string.discord_title), stringResource(R.string.discord_sub),
                onClick = { onOpenLink(Links.DISCORD) }, info = stringResource(R.string.info_discord))
            GroupDivider()
            GroupRow(OneUi.Green, R.drawable.ic_share, stringResource(R.string.invite_title), stringResource(R.string.invite_sub),
                onClick = onInvite, info = stringResource(R.string.info_invite))
            GroupDivider()
            GroupRow(OneUi.Pink, R.drawable.ic_heart, stringResource(R.string.set_support), null,
                onClick = { onOpenLink(Links.SUPPORT) }, info = stringResource(R.string.info_support))
            GroupDivider()
            GroupRow(OneUi.Pink, R.drawable.ic_heart, stringResource(R.string.set_support_card), null,
                onClick = { onOpenLink(Links.CARD) }, info = stringResource(R.string.info_card))
            GroupDivider()
            GroupRow(OneUi.Pink, R.drawable.ic_heart, "Ko-fi", stringResource(R.string.set_support_kofi),
                onClick = { onOpenLink(Links.KOFI) }, info = stringResource(R.string.info_kofi))
            GroupDivider()
            GroupRow(OneUi.Gray, R.drawable.ic_info, stringResource(R.string.set_terms), null, onClick = { onOpenLink(Links.site("terms.html")) },
                info = stringResource(R.string.info_terms))
            GroupDivider()
            GroupRow(OneUi.Gray, R.drawable.ic_info, stringResource(R.string.set_privacy), null,
                onClick = { onOpenLink(Links.site("privacy.html")) }, info = stringResource(R.string.info_privacy))
            GroupDivider()
            GroupRow(OneUi.Gray, R.drawable.ic_info, stringResource(R.string.set_licenses), null, onClick = { showLicenses = true },
                info = stringResource(R.string.info_licenses))
        }
        Spacer(Modifier.height(12.dp))
    }
    }
    if (showLicenses) LicensesDialog { showLicenses = false }
    if (showWhatsNew) WhatsNewDialog { showWhatsNew = false }
    askLogout?.let { site ->
        AlertDialog(onDismissRequest = { askLogout = null },
            title = { Text(stringResource(site.logoutTitle)) },
            confirmButton = { TextButton(onClick = { onLogout(site); askLogout = null }) { Text(stringResource(R.string.logout)) } },
            dismissButton = { TextButton(onClick = { askLogout = null }) { Text(stringResource(R.string.dialog_cancel)) } })
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
internal fun SettingRow(icon: Int, title: String, value: String?, onClick: (() -> Unit)?) {
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

/** Naslov grupe (boja aplikacije) i jedna zaobljena kartica sa svim redovima grupe, kao Postavke na Androidu 15+. */
@Composable
private fun SettingsGroup(title: String, note: String? = null, content: @Composable () -> Unit) {
    Text(title, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
        fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(start = 20.dp, top = 18.dp, bottom = 4.dp))
    if (note != null) Text(note, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(start = 20.dp, end = 12.dp, bottom = 6.dp))
    Card(shape = RoundedCornerShape(26.dp), modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Column { content() }
    }
}

@Composable
private fun GroupDivider() = HorizontalDivider(Modifier.padding(start = 68.dp, end = 16.dp),
    color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))

/** Red u grupi: ikona u obojenom krugu, naslov, opis i desno strelica ili kontrola (prekidač, oznaka). */
@Composable
private fun GroupRow(accent: Color, icon: Int, title: String, value: String?,
                     onClick: (() -> Unit)?, info: String? = null, trailing: (@Composable () -> Unit)? = null) {
    Row(Modifier.fillMaxWidth().then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
        .padding(horizontal = 16.dp, vertical = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(36.dp).background(accent, RoundedCornerShape(11.dp)), contentAlignment = Alignment.Center) {
            AppIcon(icon, Modifier.size(21.dp), tint = Color.White)
        }
        Column(Modifier.weight(1f).padding(horizontal = 16.dp)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            if (value != null) Text(value, style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (info != null) InfoButton(title, info)
        when {
            trailing != null -> trailing()
            onClick != null -> AppIcon(R.drawable.ic_chevron)
        }
    }
}

/** Mreža u kartici „Nalozi": inicijali u krugu (bez tuđih logotipa), stanje prijave desno. */
@Composable
private fun AccountRow(site: LoginSite, loggedIn: Boolean, onClick: () -> Unit) {
    val (initials, color) = when (site) {
        LoginSite.INSTAGRAM -> "IG" to Color(0xFFD9467A)
        LoginSite.TIKTOK -> "TT" to Color(0xFF25C2C8)
        LoginSite.X -> "X" to Color(0xFF8A94A6)
    }
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(36.dp).background(color, RoundedCornerShape(11.dp)), contentAlignment = Alignment.Center) {
            Text(initials, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        }
        Column(Modifier.weight(1f).padding(horizontal = 16.dp)) {
            Text(stringResource(site.title), style = MaterialTheme.typography.bodyLarge)
            if (!loggedIn) Text(stringResource(site.offText), style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        InfoButton(stringResource(site.title), stringResource(R.string.info_account, stringResource(site.title)))
        StatusChip(stringResource(if (loggedIn) R.string.login_on else R.string.chip_login), loggedIn)
    }
}

/** Mala oznaka stanja: zelena kad je nešto uključeno/prijavljeno, inače tiha. */
@Composable
private fun StatusChip(text: String, on: Boolean) {
    val color = if (on) Brand.Green else MaterialTheme.colorScheme.primary
    Text(text, color = color, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold,
        modifier = Modifier.background(color.copy(alpha = 0.14f), RoundedCornerShape(50)).padding(horizontal = 10.dp, vertical = 4.dp))
}


/** Boje ikona u stilu Samsung One UI (puni zaobljeni kvadrati s bijelim simbolom). */
private object OneUi {
    val Blue = Color(0xFF3E7BFA)
    val Orange = Color(0xFFF59A23)
    val Green = Color(0xFF34B36B)
    val Purple = Color(0xFF8B5CF6)
    val Teal = Color(0xFF1FA7B4)
    val Pink = Color(0xFFE5486B)
    val Gray = Color(0xFF7D8696)
}
