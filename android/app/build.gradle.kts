plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

android {
    namespace = "io.github.abnps.videodownload"
    compileSdk = 37

    defaultConfig {
        applicationId = "io.github.abnps.videodownload"
        // Android 10+: čuvanje u Galeriju/Muziku preko MediaStore bez dozvole za pisanje (~95 % telefona).
        minSdk = 29
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-proba"
        ndk {
            // Telefoni (arm64) i emulator na računaru (x86_64).
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
    }
}

chaquopy {
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
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
}
