#/system/bin/sh
# ksu-frida Stealth Daemon Boot launcher script
MODDIR=${0%/*}
FRIDA_DIR="/data/local/tmp/.aux_stealth"
mkdir -p "$FRIDA_DIR"
chmod 771 "$FRIDA_DIR"
chown system:system "$FRIDA_DIR"

# Read dynamic config
CONFIG_FILE="$MODDIR/config.json"
PORT=$(grep -o '"port":[0-9]*' "$CONFIG_FILE" | cut -d: -f2 || echo "27342")

if [ -f "$MODDIR/bin/frida-server" ]; then
  cp "$MODDIR/bin/frida-server" "$FRIDA_DIR/ksu_w_core"
  chmod 755 "$FRIDA_DIR/ksu_w_core"
  chcon u:object_r:system_file:s0 "$FRIDA_DIR/ksu_w_core"
  
  # Start the background proxy stealth daemon 
  "$FRIDA_DIR/ksu_w_core" -D --listen 127.0.0.1:$PORT &
  chmod 700 "$FRIDA_DIR"
fi
