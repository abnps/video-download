package io.github.abnps.videodownload

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.os.Build
import kotlinx.coroutines.flow.MutableStateFlow
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/** Nova verzija aplikacije iz GitHub izdanja (android.json pored APK-a). */
data class AppRelease(val versionCode: Int, val versionName: String, val apk: String, val sha256: String, val size: Long)

sealed interface UpdateState {
    data object Idle : UpdateState
    data class Available(val release: AppRelease) : UpdateState
    data class Downloading(val release: AppRelease, val fraction: Float) : UpdateState
    data class Failed(val message: String) : UpdateState
    data object UpToDate : UpdateState
}

/**
 * Ažuriranje aplikacije van Play Storea (Ahmed 27.9.2026: „kao Mac beta, na GitHubu"): opis najnovije verzije je
 * `android.json` u posljednjem GitHub izdanju; APK se preuzima, provjerava SHA-256 i da je potpisan ISTIM ključem
 * kao instalirana aplikacija, pa ga instalira Androidov instaler (korisnik potvrđuje).
 */
object AppUpdater {
    private const val BASE = "https://github.com/abnps/video-download/releases/latest/download/"
    private const val CHECK_INTERVAL = 24 * 60 * 60 * 1000L
    private const val MAX_APK_SIZE = 500L * 1024 * 1024
    val state = MutableStateFlow<UpdateState>(UpdateState.Idle)

    /** Najviše jednom dnevno (ili odmah kad korisnik klikne „Provjeri"); poziva se van glavne niti. */
    fun check(context: Context, force: Boolean = false) {
        val prefs = context.getSharedPreferences("azuriranje", Context.MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (!force && now - prefs.getLong("provjereno", 0) < CHECK_INTERVAL) return
        try {
            // Jedan novi pokušaj: dok se izdanje objavljuje, GitHub kratko vraća 404 za „latest" (3.10.2026).
            val json = JSONObject(runCatching { read(BASE + "android.json") }.getOrElse {
                Thread.sleep(3000)
                read(BASE + "android.json")
            })
            prefs.edit().putLong("provjereno", now).apply()
            val release = AppRelease(json.getInt("versionCode"), json.getString("versionName"), json.getString("apk"),
                json.getString("sha256").lowercase(), json.optLong("size"))
            state.value = if (release.versionCode > installedCode(context)) UpdateState.Available(release) else UpdateState.UpToDate
        } catch (error: Exception) {
            if (force) state.value = UpdateState.Failed(reason(error))
        }
    }

    /** Preuzima, provjerava i predaje Androidovom instaleru. Poziva se van glavne niti. */
    fun install(context: Context, release: AppRelease) {
        try {
            require(release.apk.matches(Regex("[A-Za-z0-9_.-]+\\.apk"))) { "Nevažeće ime APK fajla" }
            require(release.size in 1..MAX_APK_SIZE) { "Nevažeća veličina APK fajla" }
            val folder = File(context.cacheDir, "azuriranje").apply { mkdirs(); listFiles()?.forEach { it.delete() } }
            val apk = File(folder, release.apk)
            download(BASE + release.apk, apk, release.size) { state.value = UpdateState.Downloading(release, it) }
            val hash = MessageDigest.getInstance("SHA-256")
            apk.inputStream().use { input ->
                val buffer = ByteArray(256 * 1024)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    hash.update(buffer, 0, count)
                }
            }
            val digest = hash.digest().joinToString("") { "%02x".format(it) }
            require(digest == release.sha256) { "SHA-256 se ne slaže" }
            require(sameSigner(context, apk, release.versionCode)) { "APK nije potpisan našim ključem ili nije odgovarajuća verzija" }
            val installer = context.packageManager.packageInstaller
            val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
            val session = installer.openSession(installer.createSession(params))
            session.use {
                it.openWrite("app.apk", 0, apk.length()).use { out -> apk.inputStream().use { input -> input.copyTo(out) } }
                val callback = PendingIntent.getBroadcast(context, 3, Intent(context, InstallResult::class.java),
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE)
                it.commit(callback.intentSender)
            }
            state.value = UpdateState.Available(release) // dalje vodi Androidov prozor za potvrdu
        } catch (error: Exception) {
            state.value = UpdateState.Failed(reason(error))
        }
    }

    private fun installedCode(context: Context): Int =
        context.packageManager.getPackageInfo(context.packageName, 0).longVersionCode.toInt()

    /** Isti certifikat kao instalirana aplikacija (Android bi drugačiji ionako odbio, ali ovako jasnija poruka). */
    private fun sameSigner(context: Context, apk: File, expectedVersion: Int): Boolean {
        val flags = PackageManager.GET_SIGNING_CERTIFICATES
        val archive = context.packageManager.getPackageArchiveInfo(apk.path, flags) ?: return false
        if (archive.packageName != context.packageName || archive.longVersionCode != expectedVersion.toLong()) return false
        val candidate = archive.signingInfo ?: return false
        val installed = context.packageManager.getPackageInfo(context.packageName, flags).signingInfo ?: return false
        val mine = installed.apkContentsSigners.map { MessageDigest.getInstance("SHA-256")
            .digest(it.toByteArray()).toList() }.toSet()
        val theirs = candidate.apkContentsSigners.map { MessageDigest.getInstance("SHA-256")
            .digest(it.toByteArray()).toList() }.toSet()
        return mine.isNotEmpty() && theirs == mine
    }

    /** Razumljiv razlog umjesto gole adrese (Java za HTTP 404 javlja samo URL). */
    private fun reason(error: Exception): String = when (error) {
        is java.net.UnknownHostException, is java.net.ConnectException, is java.net.SocketTimeoutException ->
            "nema veze s GitHubom"
        is HttpError -> "GitHub HTTP ${error.code}"
        else -> error.message ?: error.javaClass.simpleName
    }

    private class HttpError(val code: Int) : java.io.IOException("HTTP $code")

    private fun read(url: String): String {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.connectTimeout = 15000
        connection.readTimeout = 15000
        return try {
            if (connection.responseCode != HttpURLConnection.HTTP_OK) throw HttpError(connection.responseCode)
            connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    private fun download(url: String, target: File, expectedSize: Long, onProgress: (Float) -> Unit) {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.connectTimeout = 15000
        connection.readTimeout = 30000
        try {
            if (connection.responseCode != HttpURLConnection.HTTP_OK) throw HttpError(connection.responseCode)
            val total = connection.contentLengthLong
            var done = 0L
            connection.inputStream.use { input ->
                target.outputStream().use { out ->
                    val buffer = ByteArray(256 * 1024)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        done += count
                        require(done <= expectedSize) { "APK je veći od očekivane veličine" }
                        out.write(buffer, 0, count)
                        if (total > 0) onProgress(done.toFloat() / total)
                    }
                }
            }
            require(done == expectedSize) { "APK nije potpuno preuzet" }
        } finally {
            connection.disconnect()
        }
    }
}

/** Androidov instaler javlja rezultat; za potvrdu korisnika otvara svoj prozor. */
class InstallResult : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirm = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION") intent.getParcelableExtra(Intent.EXTRA_INTENT)
                }
                confirm?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)?.let(context::startActivity)
            }
            PackageInstaller.STATUS_SUCCESS -> AppUpdater.state.value = UpdateState.UpToDate
            else -> AppUpdater.state.value = UpdateState.Failed(
                intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "?")
        }
    }
}
