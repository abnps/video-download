// Verzije: Chaquopy 17 podržava Android Gradle Plugin do 9.2 (zato ne 9.4); AGP 9.2 nosi Kotlin 2.2.10.
plugins {
    id("com.android.application") version "9.2.1" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.10" apply false
    id("com.chaquo.python") version "17.0.0" apply false
}
