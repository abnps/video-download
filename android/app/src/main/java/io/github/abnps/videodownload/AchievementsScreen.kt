package io.github.abnps.videodownload

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.DateFormat
import java.util.Date

private val Pink = Color(0xFFE5486B)

@Composable
fun badgeName(badge: Badge): String =
    if (badge.count > 0) stringResource(badge.name, badge.count) else stringResource(badge.name)

@Composable
fun badgeDesc(badge: Badge): String =
    if (badge.count > 0) stringResource(badge.desc, badge.count) else stringResource(badge.desc)

/**
 * Čestitka za jedno ili više dostignuća. Poruka i dugme za prilog najviše jednom dnevno (odluka se pamti dok je
 * prozor otvoren); „Super!" samo zatvara. Ništa ne blokira i ništa ne otključava.
 */
@Composable
fun AchievementDialog(badges: List<Badge>, onSupport: () -> Unit, onClose: () -> Unit) {
    val showSupport = remember(badges) { Achievements.supportNoteAllowed() }
    val single = badges.singleOrNull()
    AlertDialog(onDismissRequest = onClose,
        title = {
            Text(if (single != null) "${single.icon} ${badgeName(single)}" else stringResource(R.string.badge_new_many),
                fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (single != null) {
                    Text(badgeDesc(single), textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
                } else {
                    badges.forEach { Text("${it.icon} ${badgeName(it)}: ${badgeDesc(it)}") }
                }
                Text(stringResource(R.string.badge_thanks), textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
                if (showSupport) {
                    Text(stringResource(R.string.badge_support), style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth())
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.badge_ok)) } },
        dismissButton = if (showSupport) {
            {
                Button(onClick = { onSupport(); onClose() }, colors = ButtonDefaults.buttonColors(containerColor = Pink)) {
                    Text(stringResource(R.string.badge_support_button), color = Color.White)
                }
            }
        } else null)
}

/** Postavke → Moja dostignuća: osvojena (s datumom) pa zaključana, i ukupno preuzimanja. */
@Composable
fun AchievementsScreen(onBack: () -> Unit) {
    val rows = remember {
        Achievements.BADGES.map { it to Achievements.earnedAt(it.key) }.sortedBy { it.second == null }
    }
    val earned = rows.count { it.second != null }
    Column(Modifier.fillMaxSize()) {
        IconButton(onClick = onBack, modifier = Modifier.padding(start = 4.dp, top = 4.dp)) {
            AppIcon(R.drawable.ic_back, tint = MaterialTheme.colorScheme.onSurface)
        }
        Box(Modifier.fillMaxWidth().height(110.dp).padding(horizontal = 24.dp), contentAlignment = Alignment.BottomStart) {
            Text(stringResource(R.string.badge_title), fontSize = 32.sp, fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 10.dp))
        }
        Text(stringResource(R.string.badge_summary, earned, rows.size, Achievements.downloadCount,
            formatSize(Achievements.bytes.toDouble())),
            style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 24.dp, vertical = 4.dp))
        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            item { Spacer(Modifier.height(4.dp)) }
            items(rows, key = { it.first.key }) { (badge, at) -> BadgeRow(badge, at) }
            item {
                Text(stringResource(R.string.badge_local), style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(8.dp))
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}

@Composable
private fun BadgeRow(badge: Badge, at: Long?) {
    val done = at != null
    Card(shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth().alpha(if (done) 1f else 0.55f),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(42.dp).background(MaterialTheme.colorScheme.surfaceContainerHighest, RoundedCornerShape(13.dp)),
                contentAlignment = Alignment.Center) {
                Text(if (done) badge.icon else "🔒", fontSize = 22.sp)
            }
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(badgeName(badge), fontWeight = FontWeight.SemiBold)
                Text(badgeDesc(badge), style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(when {
                    !done -> stringResource(R.string.badge_locked)
                    at!! > 0 -> stringResource(R.string.badge_earned_on, DateFormat.getDateInstance().format(Date(at)))
                    else -> stringResource(R.string.badge_earned)
                }, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
