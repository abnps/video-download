package io.github.abnps.videodownload

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.unit.dp

/** Faza trake, iste boje kao na računaru (videodl/widgets.py, PROGRESS_COLORS). */
enum class BarPhase(val color: Color) {
    VIDEO(Color(0xFF1E88E5)), AUDIO(Color(0xFF8E24AA)), WORK(Color(0xFF8E24AA)), DONE(Color(0xFF43A047))
}

private val InOutQuad = CubicBezierEasing(0.455f, 0.03f, 0.515f, 0.955f)
private val OutCubic = CubicBezierEasing(0.215f, 0.61f, 0.355f, 1f)

/**
 * Traka napretka kao u programu za računar (AnimatedProgress): klizi do novog procenta, preko popunjenog
 * dijela prelazi sjaj, bez procenta (čitanje, spajanje) komad trake klizi lijevo-desno, a na kraju
 * zazeleni i kratko pulsira. `fraction == null` = nepoznato trajanje.
 */
@Composable
fun AppProgressBar(fraction: Float?, phase: BarPhase, modifier: Modifier = Modifier) {
    val track = if (isSystemInDarkTheme()) Color(0xFF33404F) else Color(0xFFE3ECF8)
    val value by animateFloatAsState(if (phase == BarPhase.DONE) 1f else (fraction ?: 0f).coerceIn(0f, 1f),
        tween(600, easing = OutCubic), label = "napredak")
    val infinite = rememberInfiniteTransition(label = "traka")
    val shine by infinite.animateFloat(0f, 1f, infiniteRepeatable(tween(1600, easing = LinearEasing)), label = "sjaj")
    val slide by infinite.animateFloat(0f, 1f, infiniteRepeatable(tween(1200, easing = InOutQuad), RepeatMode.Restart),
        label = "klizanje")
    // Puls na kraju: traka se na trenutak podeblja (6 → 8 dp) pa vrati.
    val pulse = remember { Animatable(0f) }
    LaunchedEffect(phase == BarPhase.DONE) {
        if (phase == BarPhase.DONE) {
            pulse.snapTo(0f)
            pulse.animateTo(1f, tween(350, easing = FastOutSlowInEasing))
            pulse.animateTo(0f, tween(350, easing = FastOutSlowInEasing))
        }
    }
    Canvas(modifier.fillMaxWidth().height(8.dp)) {
        val thickness = 6.dp.toPx() + 2.dp.toPx() * pulse.value
        val top = (size.height - thickness) / 2
        val radius = CornerRadius(thickness / 2)
        drawRoundRect(track, Offset(0f, top), Size(size.width, thickness), radius)
        val color = phase.color
        if (fraction == null && phase != BarPhase.DONE) {
            val segment = size.width * 0.3f
            val left = -segment + slide * (size.width + segment)
            val clip = Path().apply { addRoundRect(androidx.compose.ui.geometry.RoundRect(0f, top, size.width, top + thickness, radius)) }
            clipPath(clip) { drawRoundRect(color, Offset(left, top), Size(segment, thickness), radius) }
            return@Canvas
        }
        val filled = size.width * value
        if (filled <= 0f) return@Canvas
        val barWidth = maxOf(filled, thickness)
        drawRoundRect(color, Offset(0f, top), Size(barWidth, thickness), radius)
        if (phase != BarPhase.DONE) {
            // Sjaj koji prelazi preko popunjenog dijela: vidi se da radi i kad je sporo.
            val width = 60.dp.toPx()
            val x = -width + shine * (filled + width)
            val bar = Path().apply { addRoundRect(androidx.compose.ui.geometry.RoundRect(0f, top, barWidth, top + thickness, radius)) }
            clipPath(bar) {
                drawRect(Brush.horizontalGradient(listOf(Color.White.copy(alpha = 0f), Color.White.copy(alpha = 0.59f),
                    Color.White.copy(alpha = 0f)), startX = x, endX = x + width), Offset(x, top), Size(width, thickness))
            }
        }
    }
}
