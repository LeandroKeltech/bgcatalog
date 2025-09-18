[app]
title = bgcatalog
package.name = bgcatalog
package.domain = org.bgcatalog
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy
orientation = portrait
osx.python_version = 3
fullscreen = 1

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.accept_sdk_license = True
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.sdk_path = ~/.buildozer/android/platform/android-sdk
android.ndk_path = ~/.buildozer/android/platform/android-ndk-r25b
android.gradle_dependencies = 

# Force specific build tools version
android.add_compile_options = 
android.add_gradle_repositories = 
android.gradle_repositories = google(), mavenCentral()
android.enable_androidx = True
