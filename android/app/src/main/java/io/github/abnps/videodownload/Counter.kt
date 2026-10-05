package io.github.abnps.videodownload

import android.content.Context
import java.net.HttpURLConnection
import java.net.URL

/**
 * Brojač bez praćenja (Ahmed 5.10.2026: „samo realna preuzimanja, i kad se podijeli prijatelju"): aplikacija preuzme
 * mali prazan fajl s GitHuba, a GitHub broji samo KOLIKO puta je preuzet. Ništa se ne šalje o korisniku ni uređaju.
 * - nova instalacija: jednom, pri prvom pokretanju (ažuriranje postojeće aplikacije se ne broji);
 * - „Pozovi prijatelja": jednom po slanju (prijateljev APK stiže bez interneta, pa ga GitHub inače ne vidi).
 * Fajlovi su u stalnom izdanju „brojac" repoa za winget; tools/statistika.py čita brojeve.
 */
object Counter {
    private const val BASE = "https://github.com/abnps/video-download-installers/releases/download/brojac/"

    /** Poziva se van glavne niti. */
    fun newInstall(context: Context) {
        val prefs = context.getSharedPreferences("brojac", Context.MODE_PRIVATE)
        if (prefs.getBoolean("instalacija", false)) return
        val info = context.packageManager.getPackageInfo(context.packageName, 0)
        // Ažurirana aplikacija (stari korisnik) nije nova instalacija: samo se zapamti, bez brojanja.
        if (info.firstInstallTime == info.lastUpdateTime && !touch("android-nova-instalacija.txt")) return
        prefs.edit().putBoolean("instalacija", true).apply()
    }

    fun invite() {
        Thread { touch("android-poziv.txt") }.start()
    }

    private fun touch(name: String): Boolean = runCatching {
        val connection = URL(BASE + name).openConnection() as HttpURLConnection
        connection.connectTimeout = 15000
        connection.readTimeout = 15000
        try {
            connection.responseCode == HttpURLConnection.HTTP_OK && connection.inputStream.use { it.readBytes(); true }
        } finally {
            connection.disconnect()
        }
    }.getOrDefault(false)
}
