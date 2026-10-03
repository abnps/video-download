package io.github.abnps.videodownload

import android.content.Context
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * Roditeljska zaštita (Ahmed 3.10.2026), ista pravila kao na računaru (videodl/parental.py): uključena →
 * sadržaj 18+ se ne preuzima i ne nudi se potvrda „Imam 18". PIN (4–8 cifara) je opcion i čuva se samo kao
 * otisak PBKDF2-SHA256 sa nasumičnom solju, u istom zapisu kao na računaru. Sprečava slučajno preuzimanje;
 * nije brava koja se ne može zaobići (npr. brisanjem podataka aplikacije).
 */
object Parental {
    private const val FILE = "postavke"
    private const val ITERATIONS = 200_000
    private val PIN = Regex("\\d{4,8}")

    fun enabled(context: Context): Boolean = prefs(context).getBoolean("parental_enabled", false)

    fun hasPin(context: Context): Boolean = prefs(context).getString("parental_pin", "").orEmpty().isNotEmpty()

    fun validPin(pin: String): Boolean = PIN.matches(pin)

    /** Uključi (s novim PIN-om ili bez njega) ili isključi; isključena zaštita briše PIN. */
    fun save(context: Context, enabled: Boolean, pin: String) {
        val edit = prefs(context).edit().putBoolean("parental_enabled", enabled)
        when {
            !enabled -> edit.remove("parental_pin")
            pin.isNotEmpty() -> edit.putString("parental_pin", hash(pin))
        }
        edit.apply()
    }

    fun checkPin(context: Context, pin: String): Boolean {
        val parts = prefs(context).getString("parental_pin", "").orEmpty().split("$")
        if (parts.size != 4 || parts[0] != "pbkdf2-sha256" || !validPin(pin)) return false
        return runCatching {
            val candidate = derive(pin, hex(parts[2]), parts[1].toInt())
            MessageDigest.isEqual(candidate, hex(parts[3]))
        }.getOrDefault(false)
    }

    private fun hash(pin: String): String {
        require(validPin(pin)) { "PIN mora imati 4 do 8 cifara" }
        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        return "pbkdf2-sha256$$ITERATIONS$${salt.toHex()}$${derive(pin, salt, ITERATIONS).toHex()}"
    }

    private fun derive(pin: String, salt: ByteArray, iterations: Int): ByteArray =
        SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            .generateSecret(PBEKeySpec(pin.toCharArray(), salt, iterations, 256)).encoded

    private fun ByteArray.toHex() = joinToString("") { "%02x".format(it) }
    private fun hex(text: String) = ByteArray(text.length / 2) { text.substring(it * 2, it * 2 + 2).toInt(16).toByte() }
    private fun prefs(context: Context) = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
}
