package io.github.abnps.videodownload

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings as SystemSettings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.chaquo.python.Python
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Tri ekrana (Početna, Preuzimanja, Postavke) + „Izaberi kvalitet" preko Početne, po Ahmedovom dizajnu. */
class MainActivity : ComponentActivity() {
    private val link = mutableStateOf("")
    private val tab = mutableIntStateOf(TAB_HOME)
    private val downloadsTab = mutableIntStateOf(0)
    private val info = mutableStateOf<VideoInfo?>(null)
    private val finding = mutableStateOf(false)
    private val findError = mutableStateOf<String?>(null)
    private val location = mutableStateOf(SaveLocation.DOWNLOADS)
    private val quality = mutableIntStateOf(0)
    private var autoFind = false
    private val welcome = mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        location.value = Settings.location(this)
        quality.intValue = Settings.quality(this)
        handle(intent)
        askForNotifications()
        welcome.value = !getSharedPreferences("postavke", MODE_PRIVATE).getBoolean("uslovi_prihvaceni", false)
        // U pozadini, najviše jednom dnevno: nova verzija aplikacije (GitHub) i čitača sajtova (PyPI).
        Thread {
            AppUpdater.check(this)
            runCatching { Python.getInstance().getModule("vd_core").callAttr("update_ytdlp") }
        }.start()
        setContent { AppTheme { App() } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

    /** „Podijeli" iz druge aplikacije: link odmah ide na „Izaberi kvalitet"; obavještenje otvara Preuzimanja. */
    private fun handle(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_OPEN_DOWNLOADS, false) == true) {
            tab.intValue = TAB_DOWNLOADS
            return
        }
        if (intent?.action != Intent.ACTION_SEND) return
        findUrl(intent.getStringExtra(Intent.EXTRA_TEXT))?.let {
            link.value = it
            tab.intValue = TAB_HOME
            info.value = null
            autoFind = true
        }
    }

    private fun askForNotifications() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
    }

    private fun paste() {
        val clip = getSystemService(ClipboardManager::class.java).primaryClip
        val text = clip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this)?.toString()
        findUrl(text)?.let { link.value = it }
    }

    private suspend fun find() {
        val url = findUrl(link.value) ?: return
        finding.value = true
        findError.value = null
        try {
            val json = withContext(Dispatchers.IO) {
                Python.getInstance().getModule("vd_core").callAttr("probe", url, cacheDir.absolutePath).toString()
            }
            info.value = VideoInfo.parse(json)
        } catch (error: Exception) {
            findError.value = DownloadService.cleanError(error.message)
        } finally {
            finding.value = false
        }
    }

    private fun copyReport() {
        val text = Python.getInstance().getModule("vd_core").callAttr("report", cacheDir.absolutePath).toString()
        getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Video Download", text))
        Toast.makeText(this, R.string.report_copied, Toast.LENGTH_SHORT).show()
    }

    private val actions = ItemActions(
        open = { item ->
            runCatching {
                startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(Uri.parse(item.uri), if (item.isAudio) "audio/*" else "video/*")
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
            }
        },
        share = { item ->
            val send = Intent(Intent.ACTION_SEND).setType(if (item.isAudio) "audio/*" else "video/*")
                .putExtra(Intent.EXTRA_STREAM, Uri.parse(item.uri)).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            startActivity(Intent.createChooser(send, null))
        },
        remove = { item -> History.remove(item.id) }, // uklanja samo s liste; fajl ostaje u folderu
    )

    /** „Pozovi prijatelja": šalje samu aplikaciju (kopija instaliranog APK-a) uz kratku poruku, preko menija Podijeli. */
    private suspend fun invite() {
        val version = packageManager.getPackageInfo(packageName, 0).versionName.orEmpty()
        val copy = withContext(Dispatchers.IO) {
            val folder = java.io.File(cacheDir, "dijeli").apply { mkdirs(); listFiles()?.forEach { it.delete() } }
            java.io.File(folder, "VideoDownload-android-$version.apk").also { target ->
                java.io.File(applicationInfo.sourceDir).copyTo(target, overwrite = true)
            }
        }
        val uri = androidx.core.content.FileProvider.getUriForFile(this, "$packageName.dijeli", copy)
        val send = Intent(Intent.ACTION_SEND).setType("application/vnd.android.package-archive")
            .putExtra(Intent.EXTRA_STREAM, uri).putExtra(Intent.EXTRA_TEXT, getString(R.string.invite_text))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        startActivity(Intent.createChooser(send, getString(R.string.invite_title)))
    }

    private fun installUpdate() {
        val release = (AppUpdater.state.value as? UpdateState.Available)?.release ?: return
        // Android traži da korisnik jednom dozvoli ovoj aplikaciji da instalira ažuriranja.
        if (!packageManager.canRequestPackageInstalls()) {
            Toast.makeText(this, R.string.update_allow, Toast.LENGTH_LONG).show()
            runCatching {
                startActivity(Intent(SystemSettings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName")))
            }
            return
        }
        Thread { AppUpdater.install(this, release) }.start()
    }

    private fun openLink(url: String) = runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }

    private fun openLanguage() {
        val intent = if (Build.VERSION.SDK_INT >= 33) {
            Intent(SystemSettings.ACTION_APP_LOCALE_SETTINGS, Uri.fromParts("package", packageName, null))
        } else {
            Intent(SystemSettings.ACTION_LOCALE_SETTINGS)
        }
        runCatching { startActivity(intent) }
    }

    @Composable
    private fun App() {
        val scope = rememberCoroutineScope()
        val active by Downloads.active.collectAsState()
        val history by History.items.collectAsState()
        val update by AppUpdater.state.collectAsState()
        val shown = info.value
        if (welcome.value) WelcomeDialog({ openLink(it) }) {
            welcome.value = false
            getSharedPreferences("postavke", MODE_PRIVATE).edit().putBoolean("uslovi_prihvaceni", true).apply()
        }
        if (autoFind) {
            autoFind = false
            scope.launch { find() }
        }
        BackHandler(enabled = shown != null || tab.intValue != TAB_HOME) {
            if (shown != null) info.value = null else tab.intValue = TAB_HOME
        }
        Scaffold(bottomBar = {
            NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                listOf(
                    Triple(TAB_HOME, R.drawable.ic_home, R.string.nav_home),
                    Triple(TAB_DOWNLOADS, R.drawable.ic_download, R.string.nav_downloads),
                    Triple(TAB_SETTINGS, R.drawable.ic_settings, R.string.nav_settings),
                ).forEach { (index, icon, label) ->
                    NavigationBarItem(selected = tab.intValue == index,
                        onClick = { tab.intValue = index; if (index != TAB_HOME) info.value = null },
                        icon = { AppIcon(icon) }, label = { Text(stringResource(label)) })
                }
            }
        }) { padding ->
            Box(Modifier.fillMaxSize().padding(padding)) {
                when {
                    tab.intValue == TAB_HOME && shown != null -> QualityScreen(
                        info = shown, defaultHeight = quality.intValue, onBack = { info.value = null },
                        onDownload = { job ->
                            DownloadService.start(this@MainActivity, job)
                            info.value = null
                            link.value = ""
                            downloadsTab.intValue = 0
                            tab.intValue = TAB_DOWNLOADS
                        },
                        location = location.value,
                        onLocation = { location.value = it; Settings.setLocation(this@MainActivity, it) },
                    )
                    tab.intValue == TAB_HOME -> HomeScreen(
                        link = link.value, onLinkChange = { link.value = it; findError.value = null }, onPaste = { paste() },
                        onFind = { scope.launch { find() } }, finding = finding.value, error = findError.value,
                        onCopyReport = { copyReport() }, history = history,
                        onShowAll = { downloadsTab.intValue = 1; tab.intValue = TAB_DOWNLOADS }, actions = actions,
                        update = update, onInstallUpdate = { installUpdate() },
                    )
                    tab.intValue == TAB_DOWNLOADS -> {
                        val error by Downloads.lastError.collectAsState()
                        DownloadsScreen(active, history, downloadsTab.intValue, { downloadsTab.intValue = it },
                            onCancel = { DownloadService.cancel(this@MainActivity, it) }, actions = actions)
                        if (error != null && active.isEmpty() && downloadsTab.intValue == 0) {
                            ErrorBanner(error!!) { copyReport() }
                        }
                    }
                    else -> SettingsScreen(
                        quality = quality.intValue,
                        onQuality = { quality.intValue = it; Settings.setQuality(this@MainActivity, it) },
                        location = location.value,
                        onLocation = { location.value = it; Settings.setLocation(this@MainActivity, it) },
                        onLanguage = { openLanguage() }, onOpenLink = { openLink(it) },
                        onInvite = { scope.launch { invite() } },
                        update = update, onInstallUpdate = { installUpdate() },
                        onCheckUpdate = { Thread { AppUpdater.check(this@MainActivity, force = true) }.start() },
                        appVersion = packageManager.getPackageInfo(packageName, 0).versionName.orEmpty(),
                        readerVersion = runCatching {
                            Python.getInstance().getModule("vd_core").callAttr("version").toString()
                        }.getOrDefault("?"),
                    )
                }
            }
        }
    }

    companion object {
        const val EXTRA_OPEN_DOWNLOADS = "otvori_preuzimanja"
        private const val TAB_HOME = 0
        private const val TAB_DOWNLOADS = 1
        private const val TAB_SETTINGS = 2
    }
}

/** Prvo pokretanje: namjena aplikacije i prihvatanje uslova (kao u instaleru za računar); ne može se preskočiti. */
@Composable
private fun WelcomeDialog(onOpenLink: (String) -> Unit, onAccept: () -> Unit) {
    androidx.compose.material3.AlertDialog(
        onDismissRequest = {},
        title = { Text(stringResource(R.string.welcome_title)) },
        text = {
            Column {
                Text(stringResource(R.string.welcome_text))
                TextButton(onClick = { onOpenLink(Links.site("terms.html")) }) { Text(stringResource(R.string.set_terms)) }
                TextButton(onClick = { onOpenLink(Links.site("privacy.html")) }) { Text(stringResource(R.string.set_privacy)) }
            }
        },
        confirmButton = { androidx.compose.material3.Button(onClick = onAccept) { Text(stringResource(R.string.accept)) } },
    )
}

/** Posljednja greška ispod praznog „Aktivno": šta nije uspjelo i „Kopiraj izvještaj". */
@Composable
private fun ErrorBanner(message: String, onCopyReport: () -> Unit) {
    Column(Modifier.padding(top = 140.dp, start = 20.dp, end = 20.dp)) {
        Text(stringResource(R.string.status_failed, message), color = MaterialTheme.colorScheme.error)
        TextButton(onClick = onCopyReport) { Text(stringResource(R.string.copy_report)) }
    }
}

private val URL = Regex("""https?://[^\s<>"']+""")

/** Prvi link u tekstu (aplikacije često dijele „Naslov videa https://…"). */
fun findUrl(text: String?): String? = text?.let { URL.find(it)?.value?.trimEnd('.', ',', ')', ']') }
