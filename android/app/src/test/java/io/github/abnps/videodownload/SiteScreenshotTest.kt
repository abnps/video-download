package io.github.abnps.videodownload

import android.content.res.Configuration
import android.graphics.Bitmap
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onRoot
import androidx.test.core.app.ApplicationProvider
import org.json.JSONObject
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.ParameterizedRobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.util.Locale

/**
 * Snimak ekrana „Preuzimanja" za sajt (odjeljak s platformama): pravi Compose ekran aplikacije, izmišljeni
 * naslovi (isti kao demo na sajtu), ništa se ne preuzima. Radi samo kad ga pokrene tools/site_platform_shots.py
 * (svojstva videodl.shots i videodl.titles); u običnom `testDebugUnitTest` se preskače.
 */
@RunWith(ParameterizedRobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35], qualifiers = "w411dp-h891dp-xxhdpi", application = android.app.Application::class)
class SiteScreenshotTest(private val lang: String, private val dark: Boolean) {
    @get:Rule val compose = createComposeRule()

    @Test
    fun downloads() {
        val out = System.getProperty("videodl.shots").orEmpty()
        val titlesFile = System.getProperty("videodl.titles").orEmpty()
        assumeTrue("Samo za snimke sajta", out.isNotBlank() && titlesFile.isNotBlank())
        val titles = JSONObject(File(titlesFile).readText()).getJSONArray(lang)
        val title = { index: Int -> titles.getString(index) }
        val mb = 1024L * 1024L
        fun job(id: Long, index: Int, audio: Boolean, label: String) =
            Job(id, "https://example.test/video/$id", title(index), "", 0, audio, 0, label)
        val active = listOf(
            ActiveJob(job(1, 0, false, "4K"), Phase.DOWNLOADING, 0.62f, 412 * mb, 664 * mb, 7.4 * mb, 9),
            ActiveJob(job(2, 1, false, "1080p"), Phase.DOWNLOADING, 0.27f, 96 * mb, 356 * mb, 2.0 * mb, 74),
            ActiveJob(job(3, 2, true, "MP3"), Phase.CONVERTING, 0.4f),
            ActiveJob(job(4, 3, true, "MP3"), Phase.QUEUED),
        )
        val base = ApplicationProvider.getApplicationContext<android.app.Application>()
        val config = Configuration(base.resources.configuration).apply {
            setLocale(Locale.forLanguageTag(lang))
            uiMode = (uiMode and Configuration.UI_MODE_NIGHT_MASK.inv()) or
                (if (dark) Configuration.UI_MODE_NIGHT_YES else Configuration.UI_MODE_NIGHT_NO)
        }
        val context = base.createConfigurationContext(config)
        compose.setContent {
            CompositionLocalProvider(LocalContext provides context, LocalConfiguration provides config) {
                AppTheme {
                    Scaffold(containerColor = MaterialTheme.colorScheme.background, bottomBar = {
                        FloatingTabBar(
                            listOf(TabItem(R.drawable.ic_home, stringResource(R.string.nav_home)),
                                TabItem(R.drawable.ic_download, stringResource(R.string.nav_downloads))),
                            selected = 1, action = TabItem(R.drawable.ic_paste, stringResource(R.string.paste)),
                        ) {}
                    }) { padding ->
                        Box(Modifier.fillMaxSize().padding(padding)) {
                            DownloadsScreen(active, emptyList(), 0, {}, {}, {}, ItemActions({}, {}, {}), {})
                        }
                    }
                }
            }
        }
        compose.waitForIdle()
        val image = compose.onRoot().captureToImage().asAndroidBitmap()
        val target = File(out, "android-${if (dark) "dark" else "light"}-$lang.png")
        target.parentFile?.mkdirs()
        target.outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    companion object {
        @JvmStatic
        @ParameterizedRobolectricTestRunner.Parameters(name = "{0}-dark={1}")
        fun cases() = listOf("en", "bs", "de", "es", "fr").flatMap { lang ->
            listOf(arrayOf<Any>(lang, false), arrayOf<Any>(lang, true))
        }
    }
}
