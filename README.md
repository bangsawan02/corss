# My Browser - ARM64 Custom Build

This repository is auto-generated to build a custom Chromium-based Android browser.
- **Chrome Extension Support** (Similar to Kiwi Browser)
- **Full Desktop Mode** (Forced Desktop User Agent & Viewport)
- **Kotlin Integration** (Native Android wrapper)

## Build Process
To avoid massive compilation times on GitHub Actions, this project utilizes a pre-compiled, patched fork of `libchrome.so` optimized specifically for ARM64.

Any push to this repository will automatically trigger a new GitHub Actions build.
Check the **Actions** tab to download your APK!
