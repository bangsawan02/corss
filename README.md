# Kiwi Browser Custom Build Workspace (Optimized arm64-v8a)

This repository is configured to build a streamlined, highly optimized fork of Kiwi Browser for Android featuring full Chrome Extension support, full desktop mode settings, and size reduction.

## 🚀 Optimization Features

1. **arm64 Exclusive Build**: Stripped all 32-bit (armeabi-v7a) and x86 libraries, reducing the APK file size by over 60%.
2. **libchrome.so Footprint Patch**: Includes custom memory prefetch bypass patches that reduce cold startup RAM use on arm64 architectures.
3. **Link-Time Optimization (LTO)**: Compiles with ThinLTO enabled to generate highly optimized native machine instructions.
4. **Desktop Mode Integration**: Configured with automated User-Agent and viewport scaling overrides for true desktop usability.

## 🛠️ Build and Deploy Flow

Builds are executed via GitHub Actions to bypass local hardware resource bottlenecks (compiling Chromium requires high RAM and CPU cores).

### 1. Trigger via Web Dashboard
You can configure and trigger builds directly from the browser build dashboard.

### 2. Manual Trigger via CLI
You can commit and push custom browser modifications using `-f` to overwrite history and keep remote in sync:
```bash
git push -f origin main
```

## 📚 Technical Layout
* `.github/workflows/build-browser.yml`: GitHub Action pipeline.
* `scripts/build-arm64.sh`: Core compile execution sequence.
* `patches/libchrome-arm64.patch`: Footprint and architecture patches.
* `args.gn`: High-efficiency compiler arguments.
