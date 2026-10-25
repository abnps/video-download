package io.github.abnps.videodownload

import androidx.compose.foundation.layout.size
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RichTooltip
import androidx.compose.material3.Text
import androidx.compose.material3.TooltipBox
import androidx.compose.material3.TooltipDefaults
import androidx.compose.material3.rememberTooltipState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

// Detaljnija objašnjenja (Ahmed 25.10.2026: „sva podešavanja Mouseover"): na telefonu nema miša, pa oblačić
// otvara dugi pritisak (Androidov način za opis dugmeta), prelazak mišem (DeX, tablet s mišem) ili dugme ⓘ.

/** Oblačić s objašnjenjem oko kontrole: dugi pritisak ili miš preko nje; običan dodir radi kao i prije. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Hint(text: String, title: String? = null, content: @Composable () -> Unit) {
    TooltipBox(
        positionProvider = TooltipDefaults.rememberRichTooltipPositionProvider(),
        tooltip = { RichTooltip(title = title?.let { { Text(it) } }) { Text(text) } },
        state = rememberTooltipState(isPersistent = true),
        content = content,
    )
}

/** Dugme ⓘ: dodir otvara objašnjenje (za postavke, gdje dugi pritisak ne bi bio očigledan). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InfoButton(title: String, text: String) {
    val state = rememberTooltipState(isPersistent = true)
    val scope = rememberCoroutineScope()
    val label = stringResource(R.string.info_more, title)
    TooltipBox(
        positionProvider = TooltipDefaults.rememberRichTooltipPositionProvider(),
        tooltip = { RichTooltip(title = { Text(title) }) { Text(text) } },
        state = state,
    ) {
        IconButton(onClick = { scope.launch { state.show() } }, modifier = Modifier.semantics { contentDescription = label }) {
            AppIcon(R.drawable.ic_info, Modifier.size(20.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
