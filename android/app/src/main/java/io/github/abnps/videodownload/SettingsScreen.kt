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

// Postavke: kvalitet, lokacija, jezik, Instagram, roditeljska zaštita, licence, ažuriranje.

@Composable
fun SettingsScreen(quality: Int, onQuality: (Int) -> Unit, location: SaveLocation, onLocation: (SaveLocation) -> Unit,
                   onLanguage: () -> Unit, onOpenLink: (String) -> Unit, onInvite: () -> Unit, onFeedback: () -> Unit,
                   loggedIn: Set<LoginSite>, onLogin: (LoginSite) -> Unit, onLogout: (LoginSite) -> Unit, appVersion: String,
                   readerVersion: String, update: UpdateState, onCheckUpdate: () -> Unit, onInstallUpdate: () -> Unit,
                   onBack: () -> Unit) {
    var pickQuality by remember { mutableStateOf(false) }
    var pickLocation by remember { mutableStateOf(false) }
    var askLogout by remember { mutableStateOf<LoginSite?>(null) }
    var showLicenses by remember { mutableStateOf(false) }
    val context = LocalContext.current
    var parentalOn by remember { mutableStateOf(Parental.enabled(context)) }
    var askPin by remember { mutableStateOf(false) }
    var editParental by remember { mutableStateOf(false) }
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
        var quick by remember { mutableStateOf(Settings.quickShare(context)) }
        SettingRow(R.drawable.ic_download, stringResource(R.string.quick_title),
            stringResource(if (quick) R.string.quick_on else R.string.quick_off)) {
            quick = !quick
            Settings.setQuickShare(context, quick)
        }
        LoginSite.entries.forEach { site ->
            SettingRow(R.drawable.ic_link, stringResource(site.title),
                stringResource(if (site in loggedIn) R.string.login_on else site.offText)) {
                if (site in loggedIn) askLogout = site else onLogin(site)
            }
        }
        SettingRow(R.drawable.ic_info, stringResource(R.string.parental_title),
            stringResource(if (parentalOn) R.string.parental_on else R.string.parental_off)) {
            if (parentalOn && Parental.hasPin(context)) askPin = true else editParental = true
        }
        SettingRow(R.drawable.ic_info, stringResource(R.string.feedback_title), stringResource(R.string.feedback_sub),
            onClick = onFeedback)
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
    if (askPin) PinDialog(onCancel = { askPin = false }) { pin ->
        if (Parental.checkPin(context, pin)) { askPin = false; editParental = true } else false.also {
            android.widget.Toast.makeText(context, R.string.parental_pin_wrong, android.widget.Toast.LENGTH_SHORT).show()
        }
    }
    if (editParental) ParentalDialog(parentalOn, onCancel = { editParental = false }) { on, pin ->
        Parental.save(context, on, pin)
        parentalOn = on
        editParental = false
    }
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

/** Unos PIN-a roditeljske zaštite prije izmjene; `onPin` vraća false kad je PIN pogrešan (prozor ostaje). */
@Composable
internal fun PinDialog(onCancel: () -> Unit, onPin: (String) -> Any) {
    var pin by remember { mutableStateOf("") }
    AlertDialog(onDismissRequest = onCancel, title = { Text(stringResource(R.string.parental_title)) },
        text = {
            OutlinedTextField(pin, { pin = it.filter(Char::isDigit).take(8) }, label = { Text(stringResource(R.string.parental_ask_pin)) },
                singleLine = true, visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword))
        },
        confirmButton = { TextButton(onClick = { onPin(pin) }) { Text("OK") } },
        dismissButton = { TextButton(onClick = onCancel) { Text(stringResource(R.string.dialog_cancel)) } })
}

/** Uključi/isključi blokadu 18+ i (opciono) postavi PIN od 4–8 cifara, kao na računaru. */
@Composable
internal fun ParentalDialog(enabled: Boolean, onCancel: () -> Unit, onSave: (Boolean, String) -> Unit) {
    var on by remember { mutableStateOf(enabled) }
    var pin by remember { mutableStateOf("") }
    var repeat by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<Int?>(null) }
    AlertDialog(onDismissRequest = onCancel, title = { Text(stringResource(R.string.parental_title)) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = on, onCheckedChange = { on = it })
                    Text(stringResource(R.string.parental_enable))
                }
                Text(stringResource(R.string.parental_note), style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (on) {
                    OutlinedTextField(pin, { pin = it.filter(Char::isDigit).take(8) },
                        label = { Text(stringResource(R.string.parental_pin)) }, singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword))
                    OutlinedTextField(repeat, { repeat = it.filter(Char::isDigit).take(8) },
                        label = { Text(stringResource(R.string.parental_pin_repeat)) }, singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword))
                }
                error?.let { Text(stringResource(it), color = MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val chosen = if (on) pin else ""
                error = when {
                    chosen.isNotEmpty() && !Parental.validPin(chosen) -> R.string.parental_pin_invalid
                    on && chosen != repeat -> R.string.parental_pin_mismatch
                    else -> null
                }
                if (error == null) onSave(on, chosen)
            }) { Text(stringResource(R.string.parental_save)) }
        },
        dismissButton = { TextButton(onClick = onCancel) { Text(stringResource(R.string.dialog_cancel)) } })
}
