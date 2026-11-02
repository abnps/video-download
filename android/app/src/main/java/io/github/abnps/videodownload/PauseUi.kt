package io.github.abnps.videodownload

import android.content.Intent
import android.net.Uri
import android.os.SystemClock
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import java.time.LocalDate
import java.time.format.TextStyle

// Zaštita od blokade, „Gotovo: 50/50" i mjesečni pregled na ekranu (Ahmed 2.11.2026); pravila su u Pacing, Support i Recap.

private val PauseAmber = Color(0xFFE0A030)
private val SupportPink = Color(0xFFE5486B)

/** Sat koji se osvježava dvaput u sekundi (za odbrojavanje). */
@Composable
private fun rememberNow(): Long {
    var now by remember { mutableLongStateOf(SystemClock.elapsedRealtime()) }
    LaunchedEffect(Unit) {
        while (true) {
            now = SystemClock.elapsedRealtime()
            delay(500)
        }
    }
    return now
}

private fun clock(millis: Long): String {
    val seconds = (millis.coerceAtLeast(0) + 999) / 1000
    return "%d:%02d".format(seconds / 60, seconds % 60)
}

private fun openSupport(context: android.content.Context) =
    runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(Links.SUPPORT))) }

/** Red na kartici posla: „⏱ Pauza 4 s, čuva od blokade (YouTube)". */
@Composable
internal fun PausedLine(active: ActiveJob) {
    val now = rememberNow()
    val seconds = ((active.pauseUntil - now).coerceAtLeast(0) + 999) / 1000
    Text(stringResource(R.string.pause_gap, seconds.toInt(), active.pauseSite), style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant)
}

/** Kartica predaha ili blokade: odbrojavanje, objašnjenje, savjet, red o podršci, „Nastavi odmah". */
@Composable
fun PauseCardView() {
    val card by Pacing.card.collectAsState()
    val shown = card ?: return
    val context = LocalContext.current
    val now = rememberNow()
    val site = Pacing.NAMES[shown.pause.family] ?: shown.pause.family
    val block = shown.pause.kind == "block"
    Card(shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        colors = CardDefaults.cardColors(containerColor = PauseAmber.copy(alpha = 0.12f)),
        border = BorderStroke(1.dp, PauseAmber.copy(alpha = 0.5f))) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(stringResource(if (block) R.string.pause_block_title else R.string.pause_break_title, site,
                clock(shown.until - now)), fontWeight = FontWeight.SemiBold)
            Text(stringResource(if (block) R.string.pause_block_text else R.string.pause_break_text, site),
                style = MaterialTheme.typography.bodyMedium)
            Text(stringResource(R.string.pause_tip, stringResource(shown.tip)), style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            shown.support?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                if (shown.support != null && !Support.snoozed()) {
                    Button(onClick = { openSupport(context) }, colors = ButtonDefaults.buttonColors(containerColor = SupportPink)) {
                        Text(stringResource(R.string.badge_support_button), color = Color.White)
                    }
                }
                TextButton(onClick = { Pacing.skip(shown.pause.family) }) { Text(stringResource(R.string.pause_now)) }
            }
        }
    }
}

/** „Gotovo: 50/50 videa, 6,1 GB ✓" s redom o podršci po pravilima. */
@Composable
fun SuccessCardView() {
    val card by Downloads.success.collectAsState()
    val shown = card ?: return
    val context = LocalContext.current
    Card(shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.10f)),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.45f))) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(stringResource(R.string.success_title, shown.done, shown.total, formatSize(shown.bytes.toDouble())),
                fontWeight = FontWeight.SemiBold)
            Text(stringResource(R.string.success_text), style = MaterialTheme.typography.bodyMedium)
            shown.support?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                if (shown.offerSupport) {
                    Button(onClick = { openSupport(context) }, colors = ButtonDefaults.buttonColors(containerColor = SupportPink)) {
                        Text(stringResource(R.string.badge_support_button), color = Color.White)
                    }
                }
                TextButton(onClick = { Downloads.success.value = null }) { Text(stringResource(R.string.card_close)) }
            }
        }
    }
}

@Composable
private fun duration(seconds: Long): String {
    val minutes = (seconds + 30) / 60
    if (minutes < 60) return stringResource(R.string.recap_minutes, minutes.toInt())
    val hours = stringResource(R.string.recap_hours, (minutes / 60).toInt())
    val rest = (minutes % 60).toInt()
    return if (rest > 0 && minutes / 60 < 10) "$hours ${stringResource(R.string.recap_minutes, rest)}" else hours
}

/** „Tvoj oktobar u Video Downloadu": brojke, „Podijeli" (tekst s adresom sajta), red o podršci. */
@Composable
fun RecapDialog(summary: RecapSummary, support: String?, offerSupport: Boolean, onClose: () -> Unit) {
    val context = LocalContext.current
    val locale = LocalConfiguration.current.locales[0]
    val title = if (summary.yearly) stringResource(R.string.recap_title_year, summary.period) else {
        val month = LocalDate.parse("${summary.period}-01").month.getDisplayName(TextStyle.FULL_STANDALONE, locale)
        stringResource(R.string.recap_title_month, month)
    }
    val stats = stringResource(R.string.recap_stats, summary.count, formatSize(summary.bytes.toDouble()), duration(summary.seconds))
    val site = Pacing.FAMILIES[summary.topSite]?.let { Pacing.NAMES[it] } ?: summary.topSite
    val day = java.time.DayOfWeek.of(summary.busiestWeekday + 1).getDisplayName(TextStyle.FULL_STANDALONE, locale)
    val lines = listOfNotNull(
        site.takeIf { it.isNotEmpty() }?.let { stringResource(R.string.recap_top_site, it) },
        summary.longest.takeIf { it > 0 }?.let { stringResource(R.string.recap_longest, duration(it)) },
        stringResource(R.string.recap_busiest_day, day),
    )
    AlertDialog(onDismissRequest = onClose, title = { Text(title) }, text = {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(stats, fontWeight = FontWeight.SemiBold)
            lines.forEach { Text(it) }
            Text(stringResource(R.string.recap_private), style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            support?.let { Text(it) }
        }
    }, confirmButton = {
        Row {
            if (offerSupport) TextButton(onClick = { openSupport(context) }) { Text(stringResource(R.string.badge_support_button)) }
            TextButton(onClick = {
                // Dijeli se samo tekst s brojkama i adresom sajta, bez naslova videa.
                val text = (listOf(title, stats) + lines + "Video Download · https://abnps.github.io/video-download/").joinToString("\n")
                val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
                runCatching { context.startActivity(Intent.createChooser(send, null)) }
            }) { Text(stringResource(R.string.share)) }
            TextButton(onClick = onClose) { Text(stringResource(R.string.card_close)) }
        }
    })
}
