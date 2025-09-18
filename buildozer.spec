[app]
title = bgcatalog
package.name = bgcatalog
package.domain = org.bgcatalog
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,kivymd,pillow,requests
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.accept_sdk_license = True
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.enable_androidx = True
