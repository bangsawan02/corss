# This script is automatically called by the Magisk App during module installation.
SKIPUNZIP=0

# Ensure internal module directory frameworks exist
mkdir -p "$MODPATH/zygisk"
mkdir -p "$MODPATH/system/lib"
mkdir -p "$MODPATH/system/lib64"

# Set permissions for files
set_perm_recursive "$MODPATH/zygisk" 0 0 0755 0755
set_perm_recursive "$MODPATH/system" 0 0 0755 0644

# Initialize dynamic targeting configuration file on /data/local/tmp if not already there
if [ ! -f "/data/local/tmp/frida-targets" ]; then
  ui_print "- Constructing fresh dynamic configuration file"
  touch "/data/local/tmp/frida-targets"
  echo "# Write package names to inspect (one per line)" > "/data/local/tmp/frida-targets"
  echo "com.taxsee.driver2" >> "/data/local/tmp/frida-targets"
  set_perm "/data/local/tmp/frida-targets" 0 0 0666
fi

ui_print "*************************************************"
ui_print "   Zygisk Frida Gadget v1.0.0 Loaded!"
ui_print "*************************************************"
ui_print " - Frida Target Version: v16.3.3"
ui_print " - Default Static Target App: com.taxsee.driver2"
ui_print " - Dynamic Config File: /data/local/tmp/frida-targets"
ui_print " - Active Mode: SCRIPT"
ui_print ""
ui_print " Please reboot your device to enable the Zygisk hooks."
ui_print "*************************************************"
