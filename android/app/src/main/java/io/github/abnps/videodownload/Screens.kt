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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.foundation.layout.navigationBarsPadding
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

// Zajednički dijelovi ekrana (ikone, kartice, meni stavke).

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
    // One UI 9 stil (Ahmed 3.10.2026): ispunjena kartica bez ruba, jače zaobljena — ista u cijeloj aplikaciji.
    val colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)
    val shape = RoundedCornerShape(26.dp)
    if (onClick != null) {
        Card(onClick = onClick, modifier = modifier, shape = shape, colors = colors) { content() }
    } else {
        Card(modifier = modifier, shape = shape, colors = colors) { content() }
    }
}

@Composable
internal fun ItemMenu(item: HistoryItem, actions: ItemActions) {
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }) { AppIcon(R.drawable.ic_more) }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            if (item.failed) {
                DropdownMenuItem(text = { Text(stringResource(R.string.copy_report)) },
                    onClick = { open = false; actions.copyReport() })
            } else {
                DropdownMenuItem(text = { Text(stringResource(R.string.open)) }, onClick = { open = false; actions.open(item) })
                DropdownMenuItem(text = { Text(stringResource(R.string.share)) }, onClick = { open = false; actions.share(item) })
            }
            DropdownMenuItem(text = { Text(stringResource(R.string.remove_from_list)) },
                onClick = { open = false; actions.remove(item) })
        }
    }
}

/** Šta se može uraditi s gotovim fajlom (ekran Početna i Preuzimanja). */
class ItemActions(
    val open: (HistoryItem) -> Unit, val share: (HistoryItem) -> Unit, val remove: (HistoryItem) -> Unit,
    // Za neuspjela preuzimanja:
    val retry: (HistoryItem) -> Unit = {}, val copyLink: (HistoryItem) -> Unit = {}, val copyReport: () -> Unit = {},
)


class TabItem(val icon: Int, val label: String)

/**
 * Donja traka u stilu One UI 9 (kao Samsung Health, Ahmed 3.10.2026): plutajuća poluprozirna kapsula s karticama
 * (ikona iznad naziva, izabrana na svjetlijoj podlozi) i odvojeno okruglo dugme za glavnu radnju desno.
 */
@Composable
fun FloatingTabBar(items: List<TabItem>, selected: Int, action: TabItem? = null, onAction: () -> Unit = {},
                   onSelect: (Int) -> Unit) {
    val bar = MaterialTheme.colorScheme.surfaceContainerHighest.copy(alpha = 0.94f)
    Row(Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 20.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
        Row(Modifier.shadow(10.dp, RoundedCornerShape(36.dp)).background(bar, RoundedCornerShape(36.dp)).padding(5.dp),
            verticalAlignment = Alignment.CenterVertically) {
            items.forEachIndexed { index, item ->
                val on = index == selected
                val color = if (on) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
                Column(Modifier.clip(RoundedCornerShape(30.dp))
                    .background(if (on) MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f) else Color.Transparent)
                    .clickable { onSelect(index) }.padding(horizontal = 24.dp, vertical = 8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally) {
                    AppIcon(item.icon, Modifier.size(24.dp), tint = color)
                    Text(item.label, color = color, fontSize = 12.sp,
                        fontWeight = if (on) FontWeight.SemiBold else FontWeight.Normal, modifier = Modifier.padding(top = 2.dp))
                }
            }
        }
        if (action != null) {
            Box(Modifier.padding(start = 10.dp).size(58.dp).shadow(10.dp, CircleShape).background(bar, CircleShape)
                .clip(CircleShape).clickable(onClick = onAction), contentAlignment = Alignment.Center) {
                AppIcon(action.icon, Modifier.size(24.dp), tint = MaterialTheme.colorScheme.primary)
            }
        }
    }
}

/** Mala zaobljena oznaka („1080P", „MP4", „46 MB"), kao kod sličnih aplikacija (Ahmed 3.10.2026). */
@Composable
internal fun Pill(text: String, accent: Boolean = false) {
    val colors = MaterialTheme.colorScheme
    Text(text, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold,
        color = if (accent) colors.onPrimaryContainer else colors.onSurfaceVariant,
        modifier = Modifier.background(if (accent) colors.primaryContainer else colors.surfaceContainerHighest,
            RoundedCornerShape(8.dp)).padding(horizontal = 7.dp, vertical = 2.dp))
}

@Composable
internal fun PillRow(texts: List<String>, modifier: Modifier = Modifier) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
        texts.filter { it.isNotBlank() }.forEachIndexed { index, text -> Pill(text, accent = index == 0) }
    }
}

