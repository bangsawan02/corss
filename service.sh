#/system/bin/sh
# webfridagadget Boot launcher script
MODDIR=${0%/*}
SEC_DIR="/data/local/tmp/libsec"
mkdir -p "$SEC_DIR"
chmod 777 "$SEC_DIR"
chown system:system "$SEC_DIR"

# Stage binaries and configs
if [ -f "$MODDIR/lib/frida-gadget.so" ]; then
  cp "$MODDIR/lib/frida-gadget.so" "$SEC_DIR/libsecmon.so"
  cp "$MODDIR/lib/frida-gadget.config" "$SEC_DIR/libsecmon.so.config"
  # Also create the legacy name if needed
  cp "$MODDIR/lib/frida-gadget.config" "$SEC_DIR/libsecmon.config.so"
  
  chmod 755 "$SEC_DIR/libsecmon.so"
  chcon u:object_r:system_file:s0 "$SEC_DIR/libsecmon.so"
fi

if [ -f "$MODDIR/config.json" ]; then
  cp "$MODDIR/config.json" "$SEC_DIR/config.json"
  chmod 666 "$SEC_DIR/config.json"
fi
