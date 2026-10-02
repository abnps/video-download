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

/**
 * Prijava na Instagram za yt-dlp. Instagram često odbija čitanje bez prijave („Sajt traži prijavu ili potvrdu"),
 * pa se korisnik SAM prijavi u ugrađenom pregledniku (aplikacija nikad ne vidi ni ne pamti lozinku). Kolačići
 * ostaju samo u WebView-u aplikacije; za svako čitanje/preuzimanje pravi se privremeni Netscape fajl za yt-dlp
 * koji se briše čim posao završi. Kolačići se nikad ne upisuju u dnevnik ni u izvještaj.
 */
object SiteLogin {
    const val LOGIN_URL = "https://www.instagram.com/accounts/login/"
    private const val SITE_URL = "https://www.instagram.com"
    private const val DOMAIN = ".instagram.com"
    private const val MAX_COOKIES = 100
    private const val FILE_DAYS = 30L

    /** Raščlanjeni kolačići „ime=vrijednost; …" iz WebView-a (bez neispravnih i prevelikih). */
    private fun cookies(): List<Pair<String, String>> {
        val raw = onMainThread { runCatching { CookieManager.getInstance().getCookie(SITE_URL) }.getOrNull().orEmpty() }
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

    /** Prijavljen = Instagram je postavio kolačić sesije. */
    fun isLoggedIn(): Boolean = cookies().any { it.first == "sessionid" && it.second.isNotEmpty() }

    /**
     * Privremeni cookies fajl u `dir` (poziva se iz posla koji ga sam briše), ili "" ako korisnik nije prijavljen.
     * yt-dlp kolačiće s domenom .instagram.com šalje SAMO Instagramu, pa se fajl može dati svakom linku.
     */
    fun cookieFile(dir: File): String {
        val list = cookies()
        if (list.none { it.first == "sessionid" }) return ""
        val expires = System.currentTimeMillis() / 1000 + FILE_DAYS * 24 * 3600
        val file = File(dir, "kolacici-${System.nanoTime()}.txt")
        file.bufferedWriter().use { out ->
            out.write("# Netscape HTTP Cookie File\n")
            for ((name, value) in list) {
                out.write(listOf(DOMAIN, "TRUE", "/", "TRUE", expires.toString(), name, value).joinToString("\t"))
                out.write("\n")
            }
        }
        return file.absolutePath
    }

    /** Odjava: brišu se samo Instagramovi kolačići (ostali sajtovi ostaju netaknuti). */
    fun logout() {
        val manager = CookieManager.getInstance()
        for ((name, _) in cookies()) {
            manager.setCookie(SITE_URL, "$name=; Max-Age=0; Path=/; Domain=$DOMAIN")
            manager.setCookie(SITE_URL, "$name=; Max-Age=0; Path=/")
        }
        manager.flush()
    }
}

/** Ugrađeni preglednik samo za prijavu na Instagram; zatvara se sam čim prijava uspije (ili dugmetom Gotovo). */
class LoginActivity : ComponentActivity() {
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
                                Text(stringResource(R.string.login_button), style = MaterialTheme.typography.titleMedium)
                                Text(stringResource(R.string.login_note), style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            TextButton(onClick = { done() }) { Text(stringResource(R.string.login_done)) }
                        }
                        if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
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
                                loadUrl(SiteLogin.LOGIN_URL)
                            }
                        })
                    }
                }
            }
        }
    }

    private fun check() {
        if (SiteLogin.isLoggedIn()) done()
    }

    private fun done() {
        if (finished) return
        finished = true
        CookieManager.getInstance().flush()
        if (SiteLogin.isLoggedIn()) Toast.makeText(this, R.string.login_on, Toast.LENGTH_SHORT).show()
        finish()
    }

    override fun onDestroy() {
        webView?.destroy()
        webView = null
        super.onDestroy()
    }
}
