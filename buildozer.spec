[app]

# (str) Title of your application
title = MT Manager KivyMD

# (str) Package name
package.name = mtmanager

# (str) Package domain (needed for android packaging)
package.domain = com.bangsawan

# (str) Source code directory
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.png

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,openssl

# (str) Supported orientations (one of landscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
#android.sdk = 34

# (str) Android NDK version to use
#android.ndk = 25b

# (bool) Use private storage or external storage
android.private_storage = False

# (str) Icon of the application
#icon.filename = %(source.dir)s/icon.png

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/presplash.png

# (str) Supported platforms
supported_platforms = android

# (str) Android entry point, default is Main
#android.entrypoint = org.kivy.android.PythonActivity

# (list) Pattern to exclude from the APK
#android.exclude_obfuscate = *.pyc, */__pycache__/*

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid any unwanted updates or redownloads
android.skip_update = False

# (bool) If True, then automatically accept SDK licenses
# This is needed for automated builds (e.g. GitHub Actions)
android.accept_sdk_license = True

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# For modern devices, arm64-v8a is the standard.
android.archs = arm64-v8a, armeabi-v7a

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = error, 1 = warning, 2 = ignore)
warn_on_root = 1
