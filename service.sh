#/system/bin/sh
# ksu-frida Stealth Gadget Boot launcher script
MODDIR=${0%/*}
FRIDA_DIR="/data/local/tmp/.aux_stealth"
mkdir -p "$FRIDA_DIR"
chmod 771 "$FRIDA_DIR"
chown system:system "$FRIDA_DIR"

# Move Gadget library to stealth realm
if [ -f "$MODDIR/lib/frida-gadget.so" ]; then
  cp "$MODDIR/lib/frida-gadget.so" "$FRIDA_DIR/ksu_w_core.so"
  cp "$MODDIR/lib/frida-gadget.config" "$FRIDA_DIR/ksu_w_core.config"
  chmod 755 "$FRIDA_DIR/ksu_w_core.so"
  chcon u:object_r:system_file:s0 "$FRIDA_DIR/ksu_w_core.so"
  chmod 700 "$FRIDA_DIR"
fi
