#!/bin/bash
# Script untuk setup lokal (jika tidak menggunakan GitHub Actions)

echo "Menyiapkan workspace untuk ${config.appName}..."

# Setup depot_tools
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH="$PATH:$(pwd)/depot_tools"

# Download source
mkdir -p workspace_src && cd workspace_src
git clone --depth 1 https://github.com/kiwibrowser/src.git .

# Konfigurasi
mkdir -p out/arm64
echo 'target_os="android"' >> out/arm64/args.gn
echo 'target_cpu="arm64"' >> out/arm64/args.gn
echo 'enable_extensions=${config.useExtensions}' >> out/arm64/args.gn

gn gen out/arm64
echo "Siap untuk kompilasi: autoninja -C out/arm64 chrome_public_apk"
