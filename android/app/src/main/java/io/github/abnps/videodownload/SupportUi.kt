package io.github.abnps.videodownload

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog

private val SupportPink = Color(0xFFE5486B)

/** Traka na Početnoj poslije svakih 10 preuzimanja (kao traka iznad liste na računaru). */
@Composable
fun SupportBanner(onSupport: () -> Unit, onLater: () -> Unit) {
    Card(shape = RoundedCornerShape(22.dp), modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
        colors = CardDefaults.cardColors(containerColor = SupportPink.copy(alpha = 0.12f)),
        border = BorderStroke(1.dp, SupportPink.copy(alpha = 0.45f))) {
        Column(Modifier.padding(16.dp)) {
            Text(stringResource(R.string.support_banner), style = MaterialTheme.typography.bodyMedium)
            Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = onLater) { Text(stringResource(R.string.support_later)) }
                Button(onClick = onSupport, colors = ButtonDefaults.buttonColors(containerColor = SupportPink)) {
                    Text(stringResource(R.string.badge_support_button), color = Color.White)
                }
            }
        }
    }
}

/** Sedmični prozor „Podrži Video Download": isti tekst i dugmad kao na računaru. Ništa ne blokira. */
@Composable
fun SupportDialog(downloads: Int, onPayPal: () -> Unit, onCard: () -> Unit, onAlready: () -> Unit, onClose: () -> Unit) {
    val accent = MaterialTheme.colorScheme.primary
    Dialog(onDismissRequest = onClose) {
        Card(shape = RoundedCornerShape(32.dp), modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
            Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 22.dp, vertical = 26.dp),
                horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.size(88.dp).clip(CircleShape)
                    .background(Brush.linearGradient(listOf(accent.copy(alpha = 0.35f), SupportPink.copy(alpha = 0.30f)))),
                    contentAlignment = Alignment.Center) {
                    Text("❤️", fontSize = 42.sp)
                }
                Spacer(Modifier.height(16.dp))
                Text(stringResource(R.string.support_title), fontSize = 22.sp, fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center)
                Spacer(Modifier.height(12.dp))
                Text(stringResource(R.string.support_dialog_count, downloads), textAlign = TextAlign.Center)
                Spacer(Modifier.height(10.dp))
                Text(stringResource(R.string.support_voluntary), style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
                Spacer(Modifier.height(20.dp))
                Button(onClick = { onPayPal(); onClose() }, modifier = Modifier.fillMaxWidth().height(50.dp),
                    shape = RoundedCornerShape(25.dp), colors = ButtonDefaults.buttonColors(containerColor = SupportPink)) {
                    Text(stringResource(R.string.support_paypal), color = Color.White, fontWeight = FontWeight.SemiBold,
                        fontSize = 16.sp)
                }
                Spacer(Modifier.height(8.dp))
                OutlinedButton(onClick = { onCard(); onClose() }, modifier = Modifier.fillMaxWidth().height(50.dp),
                    shape = RoundedCornerShape(25.dp)) {
                    Text(stringResource(R.string.set_support_card), fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.height(6.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    TextButton(onClick = onClose) { Text(stringResource(R.string.support_later)) }
                    TextButton(onClick = { onAlready(); onClose() }) { Text(stringResource(R.string.support_already)) }
                }
            }
        }
    }
}
