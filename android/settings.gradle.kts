// Video Download za Android (prototip, 27.9.2026). Licenca kao desktop verzija (Ahmedova odluka B):
// bez GPL biblioteka; Python i yt-dlp preko Chaquopyja (MIT).
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "VideoDownload"
include(":app")
