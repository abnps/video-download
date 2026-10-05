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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.chaquo.python.Python
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Tri ekrana (Početna, Preuzimanja, Postavke) + „Izaberi kvalitet" preko Početne, po Ahmedovom dizajnu. */
class MainActivity : ComponentActivity() {
    private val link = mutableStateOf("")
    private val tab = mutableIntStateOf(TAB_HOME)
    private var tabBeforeSettings = TAB_HOME // Postavke su poseban ekran; „nazad" vraća tamo odakle se došlo
    private val downloadsTab = mutableIntStateOf(0)
    private val info = mutableStateOf<VideoInfo?>(null)
    private val finding = mutableStateOf(false)
    private val findError = mutableStateOf<String?>(null)
    private val location = mutableStateOf(SaveLocation.DOWNLOADS)
    private val quality = mutableIntStateOf(0)
    private var autoFind by mutableStateOf(false)
    private var pasteOnFocus = false // widget/pločica: zalijepi čim prozor bude u fokusu
    private var fromShare = false // link je stigao iz „Podijeli" (za brzo preuzimanje)
    private val welcome = mutableStateOf(false)
    private val loggedIn = mutableStateOf(emptySet<LoginSite>()) // na koje sajtove je korisnik prijavljen
    private val playlist = mutableStateOf<PlaylistInfo?>(null)
    private val askAdultFor = mutableStateOf<List<Job>>(emptyList()) // 18+ koji čekaju potvrdu (jedan prozor)

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
            Counter.newInstall(this)
            AppUpdater.check(this)
            runCatching { Python.getInstance().getModule("vd_core").callAttr("update_ytdlp") }
        }.start()
        setContent { AppTheme { App() } }
    }

    override fun onResume() {
        super.onResume()
        loggedIn.value = LoginSite.entries.filter { SiteLogin.isLoggedIn(it) }.toSet() // i poslije povratka s prijave
    }

    private fun openLogin(site: LoginSite) {
        findError.value = null
        startActivity(Intent(this, LoginActivity::class.java).putExtra(LoginActivity.EXTRA_SITE, site.name))
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && pasteOnFocus) {
            pasteOnFocus = false
            paste()
            if (findUrl(link.value) != null) lifecycleScope.launch { find() }
            else Toast.makeText(this, R.string.paste_empty, Toast.LENGTH_SHORT).show()
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
    }

    /** „Podijeli" iz druge aplikacije: link odmah ide na „Izaberi kvalitet"; obavještenje otvara Preuzimanja. */
    private fun handle(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_PASTE, false) == true) {
            // Widget ili pločica: međuspremnik se smije čitati tek kad prozor dobije fokus (onWindowFocusChanged).
            pasteOnFocus = true
            tab.intValue = TAB_HOME
            info.value = null
            playlist.value = null
            return
        }
        if (intent?.getBooleanExtra(EXTRA_OPEN_DOWNLOADS, false) == true) {
            tab.intValue = TAB_DOWNLOADS
            return
        }
        if (intent?.action != Intent.ACTION_SEND) return
        findUrl(intent.getStringExtra(Intent.EXTRA_TEXT))?.let {
            link.value = it
            tab.intValue = TAB_HOME
            info.value = null
            fromShare = true
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
                val cookies = SiteLogin.cookieFile(cacheDir, url)
                try {
                    Python.getInstance().getModule("vd_core").callAttr("probe", url, cacheDir.absolutePath, cookies)
                        .toString()
                } finally {
                    if (cookies.isNotEmpty()) java.io.File(cookies).delete() // privremeni kolačići nikad ne ostaju
                }
            }
            val list = PlaylistInfo.parseOrNull(json)
            val video = if (list == null) VideoInfo.parse(json) else null
            val quick = fromShare && Settings.quickShare(this)
            fromShare = false
            when {
                list != null -> playlist.value = list
                // Brzo preuzimanje: samo običan video; plejlista, 18+ i roditeljska zaštita idu kroz ekran (odluka korisnika).
                quick && video != null && !video.adult -> quickDownload(video)
                else -> info.value = video
            }
        } catch (error: CancellationException) {
            throw error // prekid nije greška sajta
        } catch (error: Exception) {
            findError.value = DownloadService.cleanError(this, error.message)
        } finally {
            finding.value = false
        }
    }

    /** Kao „Preuzmi" na ekranu kvaliteta s podrazumijevanim kvalitetom; korisnik ostaje u aplikaciji iz koje je dijelio. */
    private fun quickDownload(video: VideoInfo) {
        val wanted = Settings.quality(this)
        val options = video.video
        val chosen = options.firstOrNull { wanted == 0 || it.label <= wanted } ?: options.firstOrNull()
        val label = chosen?.label?.takeIf { it > 0 }?.let { "${it}p" } ?: "MP4"
        DownloadService.start(this, Job(System.currentTimeMillis(), video.url, video.title, video.thumbnail, video.duration,
            false, chosen?.height ?: 0, label))
        link.value = ""
        Toast.makeText(this, getString(R.string.quick_started, video.title), Toast.LENGTH_SHORT).show()
        moveTaskToBack(true)
    }

    /** Postavke → Prijavi problem ili prijedlog: e-pošta na javnu adresu projekta, uz siguran izvještaj
     *  (vrsta događaja, domen, HTTP status; bez linkova i podataka o nalogu). Bez programa za poštu: kopira adresu. */
    private fun sendFeedback() {
        val version = packageManager.getPackageInfo(packageName, 0).versionName.orEmpty()
        val report = runCatching {
            Python.getInstance().getModule("vd_core").callAttr("report", cacheDir.absolutePath).toString()
        }.getOrDefault("")
        val body = getString(R.string.feedback_body) + "\n\n" +
            "Video Download $version · Android ${Build.VERSION.RELEASE} · ${Build.MANUFACTURER} ${Build.MODEL}\n\n" + report
        val mail = Intent(Intent.ACTION_SENDTO, Uri.parse("mailto:")).putExtra(Intent.EXTRA_EMAIL, arrayOf(Links.CONTACT_EMAIL))
            .putExtra(Intent.EXTRA_SUBJECT, getString(R.string.feedback_subject, version)).putExtra(Intent.EXTRA_TEXT, body)
        if (runCatching { startActivity(mail) }.isFailure) {
            getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("e-mail", Links.CONTACT_EMAIL))
            Toast.makeText(this, getString(R.string.feedback_no_mail, Links.CONTACT_EMAIL), Toast.LENGTH_LONG).show()
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
        retry = { item ->
            // Isti link ponovo kroz Početnu (svjež izbor kvaliteta); stara crvena kartica nestaje.
            History.remove(item.id)
            link.value = item.url
            findError.value = null
            info.value = null
            playlist.value = null
            tab.intValue = TAB_HOME
            lifecycleScope.launch { find() }
        },
        copyLink = { item ->
            getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Video Download", item.url))
            Toast.makeText(this, R.string.link_copied, Toast.LENGTH_SHORT).show()
        },
        copyReport = { copyReport() },
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
        Counter.invite()
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
        LaunchedEffect(autoFind) {
            if (autoFind) {
                autoFind = false
                // Ne u ovom efektu: promjena autoFind ga ponovo pokrene i prekine čitanje (link iz „Podijeli"
                // je zato uvijek prvi put padao, S26 Ultra 2.10.2026). Čitanje pripada aktivnosti, ne ekranu.
                lifecycleScope.launch { find() }
            }
        }
        val shownList = playlist.value
        BackHandler(enabled = shown != null || shownList != null || tab.intValue != TAB_HOME) {
            when {
                shown != null -> info.value = null
                shownList != null -> playlist.value = null
                tab.intValue == TAB_SETTINGS -> tab.intValue = tabBeforeSettings
                else -> tab.intValue = TAB_HOME
            }
        }
        val openSettings = { tabBeforeSettings = tab.intValue; tab.intValue = TAB_SETTINGS }
        if (askAdultFor.value.isNotEmpty()) {
            AdultDialog(askAdultFor.value.size, onCancel = { askAdultFor.value = emptyList() }) {
                askAdultFor.value.forEach { DownloadService.start(this@MainActivity, it.copy(adultOk = true)) }
                askAdultFor.value = emptyList()
            }
        }
        Scaffold(bottomBar = {
            // Donja traka samo na glavnim ekranima; Postavke se otvaraju zupčanikom gore desno.
            // One UI 9 stil (Ahmed 3.10.2026): plutajuća zaobljena traka umjesto trake preko cijele širine.
            if (tab.intValue != TAB_SETTINGS) FloatingTabBar(
                listOf(TabItem(R.drawable.ic_home, stringResource(R.string.nav_home)),
                    TabItem(R.drawable.ic_download, stringResource(R.string.nav_downloads))),
                selected = tab.intValue,
                // Glavna radnja: zalijepi link iz međuspremnika i odmah ga pročitaj (kao „Zalijepi" + „Preuzmi video").
                action = TabItem(R.drawable.ic_paste, stringResource(R.string.paste)),
                onAction = {
                    tab.intValue = TAB_HOME; info.value = null; playlist.value = null
                    paste()
                    if (findUrl(link.value) != null) lifecycleScope.launch { find() }
                },
            ) { index -> tab.intValue = index; if (index != TAB_HOME) { info.value = null; playlist.value = null } }
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
                    tab.intValue == TAB_HOME && shownList != null -> PlaylistScreen(
                        playlist = shownList, defaultHeight = quality.intValue, onBack = { playlist.value = null },
                        onDownload = { jobs ->
                            jobs.forEach { DownloadService.start(this@MainActivity, it) }
                            playlist.value = null
                            link.value = ""
                            downloadsTab.intValue = 0
                            tab.intValue = TAB_DOWNLOADS
                        },
                    )
                    tab.intValue == TAB_HOME -> HomeScreen(
                        link = link.value, onLinkChange = { link.value = it; findError.value = null }, onPaste = { paste() },
                        onFind = { lifecycleScope.launch { find() } }, finding = finding.value, error = findError.value,
                        onCopyReport = { copyReport() }, history = history.filterNot { it.failed },
                        // Prijava postoji samo za Instagram; za druge sajtove (npr. TikTok) dugme bi zbunjivalo.
                        loginSite = LoginSite.forUrl(link.value).takeIf { findError.value == getString(R.string.error_login) },
                        onLogin = { openLogin(it) },
                        onShowAll = { downloadsTab.intValue = 1; tab.intValue = TAB_DOWNLOADS }, actions = actions,
                        update = update, onInstallUpdate = { installUpdate() }, onSettings = openSettings,
                    )
                    tab.intValue == TAB_DOWNLOADS -> {
                        val error by Downloads.lastError.collectAsState()
                        DownloadsScreen(active, history, downloadsTab.intValue, { downloadsTab.intValue = it },
                            onCancel = { id ->
                                val waiting = setOf(Phase.INTERRUPTED, Phase.NEEDS_ADULT)
                                if (active.any { it.job.id == id && it.phase in waiting }) Downloads.remove(id)
                                else DownloadService.cancel(this@MainActivity, id)
                            }, onRetry = { job ->
                                // 18+: jedan prozor za SVE koji čekaju potvrdu (kao na računaru), potvrda ne ostaje.
                                val adults = active.filter { it.phase == Phase.NEEDS_ADULT }.map { it.job }
                                if (job.id in adults.map { it.id } && Parental.enabled(this@MainActivity)) {
                                    // Roditeljska zaštita: bez potvrde, ti videi se uklanjaju sa liste.
                                    adults.forEach { Downloads.remove(it.id) }
                                    Toast.makeText(this@MainActivity, R.string.parental_blocked, Toast.LENGTH_LONG).show()
                                } else if (job.id in adults.map { it.id }) askAdultFor.value = adults
                                else DownloadService.start(this@MainActivity, job)
                            }, actions = actions,
                            onSettings = openSettings, lastError = error, onCopyReport = { copyReport() })
                    }
                    else -> SettingsScreen(
                        quality = quality.intValue,
                        onQuality = { quality.intValue = it; Settings.setQuality(this@MainActivity, it) },
                        location = location.value,
                        onLocation = { location.value = it; Settings.setLocation(this@MainActivity, it) },
                        onLanguage = { openLanguage() }, onOpenLink = { openLink(it) },
                        onInvite = { scope.launch { invite() } }, onFeedback = { sendFeedback() },
                        loggedIn = loggedIn.value, onLogin = { openLogin(it) },
                        onLogout = { site -> SiteLogin.logout(site); loggedIn.value = loggedIn.value - site },
                        update = update, onInstallUpdate = { installUpdate() },
                        onCheckUpdate = { Thread { AppUpdater.check(this@MainActivity, force = true) }.start() },
                        appVersion = packageManager.getPackageInfo(packageName, 0).versionName.orEmpty(),
                        readerVersion = runCatching {
                            Python.getInstance().getModule("vd_core").callAttr("version").toString()
                        }.getOrDefault("?"),
                        onBack = { tab.intValue = tabBeforeSettings },
                    )
                }
            }
        }
    }

    companion object {
        const val EXTRA_OPEN_DOWNLOADS = "otvori_preuzimanja"
        const val EXTRA_PASTE = "zalijepi_i_preuzmi"
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
internal fun ErrorBanner(message: String, onCopyReport: () -> Unit) {
    // U rasporedu ekrana (ispod kartica), ne preko njega: fiksni razmak od vrha se preklapao s naslovom.
    Column(Modifier.padding(horizontal = 20.dp, vertical = 12.dp)) {
        Text(stringResource(R.string.status_failed, message), color = MaterialTheme.colorScheme.error)
        TextButton(onClick = onCopyReport) { Text(stringResource(R.string.copy_report)) }
    }
}

private val URL = Regex("""https?://[^\s<>"']+""")

/** Prvi link u tekstu (aplikacije često dijele „Naslov videa https://…"). */
fun findUrl(text: String?): String? = text?.let { URL.find(it)?.value?.trimEnd('.', ',', ')', ']') }
