#/system/bin/sh
# webfridagadget Module Installer
SKIPUNZIP=0
ui_print "- Arch: $ARCH"
ui_print "- Base: bangsawan02/webfridagadget"


mkdir -p "$MODPATH/lib"
mkdir -p "$MODPATH/zygisk"
mkdir -p "$MODPATH/web"

# Create targets-based config as expected by webfridagadget bridge
cat << 'EOF' > "$MODPATH/config.json"
{
    "targets": [
        {
            "app_name": "com.android.chrome",
            "enabled": true,
            "kernel_assisted_evasion": true,
            "start_up_delay_ms": 100,
            "injected_libraries": [
                { "path": "/data/local/tmp/libsec/libsecmon.so" }
            ],
            "child_gating": {
                "enabled": false,
                "mode": "freeze",
                "injected_libraries": []
            }
        }
    ]
}
EOF

# Grant permissions
ui_print "- Finalizing permissions..."
chmod 755 "$MODPATH/lib/frida-gadget.so" || true
chmod 755 "$MODPATH/zygisk/"*.so || true
ui_print "- Done. Reboot to inject into com.android.chrome"
