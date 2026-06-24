# MyBrowser - Custom Browser Engine

Repositori ini dikonfigurasi untuk mem-build browser Android berbasis Chromium (fork mirip Kiwi Browser) yang dioptimasi khusus untuk arsitektur ARM64.

## Fitur Utama
- **Dukungan Ekstensi Chrome (Manifest V2/V3):** Ya
- **Mode Desktop Penuh:** Ya
- **Optimasi ARM64:** Ya (Ukuran libchrome.so diperkecil)
- **Package Name:** `com.mybrowser.arm64`

## Cara Build
Repositori ini menggunakan GitHub Actions. Buka tab **Actions** di repositori GitHub Anda dan jalankan workflow `Build MyBrowser (ARM64)`.

APK akan tersedia di bagian artefak setelah build selesai (estimasi waktu build: 4-6 jam pada runner standar).
