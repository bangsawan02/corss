# My Browser - ARM64 Custom Build

This repository is auto-generated to build a custom Chromium-based browser for Android (ARM64) featuring:
- **Chrome Extension Support** (Similar to Kiwi Browser)
- **Full Desktop Mode** (Forced Desktop User Agent & Viewport)

## Build Process
To avoid massive compilation times and out-of-memory errors on GitHub Actions, this project utilizes a pre-compiled, patched fork of `libchrome.so` optimized specifically for ARM64. 

Any push to `build_config.json` or the `scripts/` directory will automatically trigger a new GitHub Actions build.

Check the **Actions** tab to download your APK!
