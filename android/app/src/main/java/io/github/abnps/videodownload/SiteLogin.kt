package io.github.abnps.videodownload

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Sajtovi na koje se korisnik može prijaviti (Ahmed 2.10. Instagram, 3.10.2026 TikTok); svaki ima svoje kolačiće. */
enum class LoginSite(val loginUrl: String, val siteUrl: String, val domain: String, val hosts: List<String>,
                     val title: Int, val offText: Int, val button: Int, val logoutTitle: Int,
                     val session: String = "sessionid") {
    INSTAGRAM("https://www.instagram.com/accounts/login/", "https://www.instagram.com", ".instagram.com",
        listOf("instagram.com"), R.string.login_title, R.string.login_off, R.string.login_button, R.string.logout_title),
    TIKTOK("https://www.tiktok.com/login", "https://www.tiktok.com", ".tiktok.com", listOf("tiktok.com"),
        R.string.login_title_tiktok, R.string.login_off_tiktok, R.string.login_button_tiktok, R.string.logout_title_tiktok),
    // X (3.10.2026): osjetljive objave („NSFW tweet requires authentication") vide samo prijavljeni; sesija je auth_token.
    X("https://x.com/i/flow/login", "https://x.com", ".x.com", listOf("x.com", "twitter.com"),
        R.string.login_title_x, R.string.login_off_x, R.string.login_button_x, R.string.logout_title_x, session = "auth_token");

    companion object {
        /** Sajt kojem link pripada (i kratki linkovi, npr. vt.tiktok.com), ili null. */
        fun forUrl(url: String): LoginSite? {
            val host = runCatching { java.net.URI(url.trim()).host }.getOrNull()?.lowercase()?.removePrefix("www.") ?: return null
            return entries.firstOrNull { site -> site.hosts.any { host == it || host.endsWith(".$it") } }
        }
    }
}

/**
 * Prijava za yt-dlp kad sajt odbija čitanje bez nje („Sajt traži prijavu ili potvrdu"): korisnik se SAM prijavi u
 * ugrađenom pregledniku (aplikacija nikad ne vidi ni ne pamti lozinku). Kolačići ostaju samo u WebView-u aplikacije;
 * za svako čitanje/preuzimanje pravi se privremeni Netscape fajl SAMO s kolačićima sajta kojem link pripada,
 * koji se briše čim posao završi. Kolačići se nikad ne upisuju u dnevnik ni u izvještaj.
 */
object SiteLogin {
    private const val MAX_COOKIES = 100
    private const val FILE_DAYS = 30L

    /** Raščlanjeni kolačići „ime=vrijednost; …" iz WebView-a (bez neispravnih i prevelikih). */
    private fun cookies(site: LoginSite): List<Pair<String, String>> {
        val raw = onMainThread { runCatching { CookieManager.getInstance().getCookie(site.siteUrl) }.getOrNull().orEmpty() }
        return raw.split(";").mapNotNull { part ->
            val index = part.indexOf('=')
            if (index <= 0) return@mapNotNull null
            val name = part.substring(0, index).trim()
            val value = part.substring(index + 1).trim()
            val bad = name.isEmpty() || value.length > 8000 || (name + value).any { it == '\t' || it == '\r' || it == '\n' }
            if (bad) null else name to value
        }.take(MAX_COOKIES)
    }

    /** CookieManager pouzdano radi tek na glavnoj niti (prvo čitanje iz pozadine zna vratiti prazno). */
    private fun <T> onMainThread(block: () -> T): T {
        if (Looper.myLooper() == Looper.getMainLooper()) return block()
        val result = java.util.concurrent.atomic.AtomicReference<T>()
        val done = CountDownLatch(1)
        Handler(Looper.getMainLooper()).post {
            try { result.set(block()) } finally { done.countDown() }
        }
        done.await(10, TimeUnit.SECONDS)
        return result.get() ?: block()
    }

    /** Prijavljen = sajt je postavio kolačić sesije (Instagram i TikTok „sessionid", X „auth_token"). */
    fun isLoggedIn(site: LoginSite): Boolean = cookies(site).any { it.first == site.session && it.second.isNotEmpty() }

    /**
     * Privremeni cookies fajl u `dir` (poziva se iz posla koji ga sam briše) s kolačićima SAMO sajta kojem `url`
     * pripada, ili "" kad link nije sa sajta s prijavom ili korisnik tamo nije prijavljen.
     */
    fun cookieFile(dir: File, url: String): String {
        val site = LoginSite.forUrl(url) ?: return ""
        val list = cookies(site)
        if (list.none { it.first == site.session }) return ""
        val expires = System.currentTimeMillis() / 1000 + FILE_DAYS * 24 * 3600
        val file = File(dir, "kolacici-${System.nanoTime()}.txt")
        file.bufferedWriter().use { out ->
            out.write("# Netscape HTTP Cookie File\n")
            // Isti kolačići za svaku adresu sajta (X: x.com i stari twitter.com), nikad za druge sajtove.
            for (domain in site.hosts.map { ".$it" }) for ((name, value) in list) {
                out.write(listOf(domain, "TRUE", "/", "TRUE", expires.toString(), name, value).joinToString("\t"))
                out.write("\n")
            }
        }
        return file.absolutePath
    }

    /** Odjava: brišu se samo kolačići tog sajta (ostali sajtovi ostaju netaknuti). */
    fun logout(site: LoginSite) {
        val manager = CookieManager.getInstance()
        for ((name, _) in cookies(site)) {
            manager.setCookie(site.siteUrl, "$name=; Max-Age=0; Path=/; Domain=${site.domain}")
            manager.setCookie(site.siteUrl, "$name=; Max-Age=0; Path=/")
        }
        manager.flush()
    }
}

/** Ugrađeni preglednik samo za prijavu na jedan sajt (EXTRA_SITE); zatvara se sam čim prijava uspije. */
class LoginActivity : ComponentActivity() {
    companion object {
        const val EXTRA_SITE = "site"
    }

    private val site by lazy {
        runCatching { LoginSite.valueOf(intent.getStringExtra(EXTRA_SITE).orEmpty()) }.getOrDefault(LoginSite.INSTAGRAM)
    }
    private var webView: WebView? = null
    private var finished = false
    private var loading by mutableStateOf(true)
    private var failed by mutableStateOf(false)

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        CookieManager.getInstance().setAcceptCookie(true)
        setContent {
            AppTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    Column(Modifier.fillMaxSize().safeDrawingPadding()) {
                        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(stringResource(site.button), style = MaterialTheme.typography.titleMedium)
                                Text(stringResource(R.string.login_note), style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            TextButton(onClick = { done() }) { Text(stringResource(R.string.login_done)) }
                        }
                        if (loading) AppProgressBar(null, BarPhase.WORK)
                        if (failed) {
                            Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Text(stringResource(R.string.error_network), Modifier.weight(1f),
                                    color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
                                TextButton(onClick = { webView?.reload() }) { Text(stringResource(R.string.retry)) }
                            }
                        }
                        AndroidView(modifier = Modifier.fillMaxSize(), factory = { context ->
                            WebView(context).apply {
                                webView = this
                                // AndroidView daje WRAP_CONTENT, a WebView tada stranici javlja visinu ekrana 0 (100vh = 0):
                                // Instagramov prozor za kolačiće dobije visinu 0 i tamna podloga prekrije formular
                                // (S26 Ultra, 2.10.2026). Zato puna veličina.
                                layoutParams = android.view.ViewGroup.LayoutParams(
                                    android.view.ViewGroup.LayoutParams.MATCH_PARENT, android.view.ViewGroup.LayoutParams.MATCH_PARENT)
                                settings.javaScriptEnabled = true // Instagramova prijava ne radi bez JavaScripta
                                settings.domStorageEnabled = true
                                // Instagram ugrađenom pregledniku („; wv" u oznaci) pokaže praznu stranicu
                                // (S26 Ultra, 2.10.2026); predstavi se kao obični Chrome istog telefona.
                                settings.userAgentString = settings.userAgentString.replace("; wv)", ")")
                                    .replace(Regex(" Version/[\\d.]+"), "")
                                CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
                                webChromeClient = WebChromeClient()
                                webViewClient = object : WebViewClient() {
                                    // Samo web stranice; druge šeme (intent:, instagram:// …) se ne otvaraju.
                                    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest) =
                                        request.url.scheme != "https"

                                    override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
                                        loading = true
                                        failed = false
                                        check()
                                    }

                                    override fun onPageFinished(view: WebView, url: String?) {
                                        loading = false
                                        check()
                                    }

                                    override fun onReceivedError(view: WebView, request: WebResourceRequest,
                                                                 error: WebResourceError) {
                                        if (request.isForMainFrame) failed = true
                                    }
                                }
                                loadUrl(site.loginUrl)
                            }
                        })
                    }
                }
            }
        }
    }

    private fun check() {
        if (SiteLogin.isLoggedIn(site)) done()
    }

    private fun done() {
        if (finished) return
        finished = true
        CookieManager.getInstance().flush()
        if (SiteLogin.isLoggedIn(site)) Toast.makeText(this, R.string.login_on, Toast.LENGTH_SHORT).show()
        finish()
    }

    override fun onDestroy() {
        webView?.destroy()
        webView = null
        super.onDestroy()
    }
}
