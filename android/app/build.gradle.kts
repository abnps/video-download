import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

android {
    namespace = "io.github.abnps.videodownload"
    compileSdk = 37
    // NDK samo za MP3 koder (LAME, LGPL, src/main/cpp); ista verzija kao u Alati/android-sdk i u CI.
    ndkVersion = "29.0.14206865"

    defaultConfig {
        applicationId = "io.github.abnps.videodownload"
        // Android 10+: čuvanje u Galeriju/Muziku preko MediaStore bez dozvole za pisanje (~95 % telefona).
        minSdk = 29
        targetSdk = 36
        versionCode = 12
        versionName = "0.2.8"
        ndk {
            // Samo telefoni (arm64). x86_64 (emulator, rijetki Chromebookovi) izbačen 8.10.2026: APK −13 MB.
            abiFilters += listOf("arm64-v8a")
        }
    }

    // Pravi ključ je van projekta (%USERPROFILE%/.videodl/android-release.*), nikad u repou; bez njega (npr. CI)
    // release se pravi nepotpisan. Isti ključ zauvijek: Android ne prima ažuriranje potpisano drugim ključem.
    val keyFile = File(System.getProperty("user.home"), ".videodl/android-release.properties")
    val releaseKey = keyFile.takeIf { it.isFile }?.let { file -> Properties().apply { file.inputStream().use(::load) } }
    signingConfigs {
        if (releaseKey != null) {
            create("release") {
                storeFile = File(keyFile.parentFile, releaseKey.getProperty("storeFile"))
                storePassword = releaseKey.getProperty("storePassword")
                keyAlias = releaseKey.getProperty("keyAlias")
                keyPassword = releaseKey.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            // R8 (8.10.2026): izbacuje neiskorišten Kotlin/Compose kod (APK oko −15 MB). Klase koje Python
            // poziva preko imena čuva proguard-rules.pro.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.findByName("release")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
    }
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "4.1.2"
        }
    }
}

// Ažuriranje yt-dlp-a je isti kod kao u programu za računar (videodl/ytdlp_update.py): kopira se pri gradnji,
// da logika (PyPI, SHA-256, povratak na staru verziju) bude jedna za oba programa.
val sharedPython = tasks.register<Sync>("sharedPython") {
    from(rootProject.file("../videodl")) { include("__init__.py", "runtime.py", "ytdlp_update.py") }
    into(layout.buildDirectory.dir("sharedPython/videodl"))
}
tasks.named("preBuild") { dependsOn(sharedPython) }
tasks.matching { it.name.endsWith("PythonSources") }.configureEach { dependsOn(sharedPython) }

chaquopy {
    sourceSets {
        getByName("main") { srcDir(layout.buildDirectory.dir("sharedPython").get().asFile) }
    }
    defaultConfig {
        // Isti Python kao desktop build (tools/build-lock.json); Chaquopy pip-om ubaci yt-dlp u APK.
        version = "3.14"
        pip {
            install("yt-dlp==2026.8.19")
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.19.1")
    testImplementation("junit:junit:4.13.2") // samo testovi (CI: testDebugUnitTest), ne ide u APK
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
}
