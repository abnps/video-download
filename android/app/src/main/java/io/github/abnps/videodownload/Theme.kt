package io.github.abnps.videodownload

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** Boje iz Ahmedovog prijedloga dizajna (27.9.2026): plava dugmad, bijele kartice s tankim rubom, zelena kvačica. */
object Brand {
    val Blue = Color(0xFF1E6FE8)
    val BlueDark = Color(0xFF6EA4FF)
    val Green = Color(0xFF22A55B)
}

private val Light = lightColorScheme(
    primary = Brand.Blue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE8F0FE),
    onPrimaryContainer = Color(0xFF0B3C8C),
    background = Color(0xFFF7F9FC),
    surface = Color.White,
    surfaceVariant = Color(0xFFF1F4F9),
    onSurface = Color(0xFF111827),
    onSurfaceVariant = Color(0xFF5B6474),
    outlineVariant = Color(0xFFE3E8EF),
    surfaceContainerHigh = Color.White,
    surfaceContainerHighest = Color.White,
)

private val Dark = darkColorScheme(
    primary = Brand.BlueDark,
    onPrimary = Color(0xFF002A6B),
    primaryContainer = Color(0xFF1B2F52),
    onPrimaryContainer = Color(0xFFD6E4FF),
    background = Color(0xFF0B0E14),
    surface = Color(0xFF141922),
    surfaceVariant = Color(0xFF1C222D),
    onSurface = Color(0xFFEEF1F6),
    onSurfaceVariant = Color(0xFFA2ABBB),
    outlineVariant = Color(0xFF2A3140),
    // Kartice postavki i plutajuća traka (One UI 9 stil): ista plavkasta paleta, bez Androidovih podrazumijevanih.
    surfaceContainerHigh = Color(0xFF1A202B),
    surfaceContainerHighest = Color(0xFF232A37),
)

@Composable
fun AppTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}
