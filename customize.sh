#/system/bin/sh
# ksu-frida Module Recovery installer routine
SKIPUNZIP=0
ui_print "- Target Arch: $ARCH"
ui_print "- Gadget Port: 27342"
ui_print "- Zygisk Core: Enabled (lico-n Bridge)"

mkdir -p "$MODPATH/lib"
mkdir -p "$MODPATH/hooks"
mkdir -p "$MODPATH/zygisk"
mkdir -p "$MODPATH/web"

# Create initial config
echo '{"port": 27342, "packages": "com.android.chrome"}' > "$MODPATH/config.json"

# Bundle customized Frida JS script payloads
cat << 'EOF' > "$MODPATH/hooks/stealth_hook.js"
/* Custom Frida Action Payload - ssl_pinning */
Java.perform(function() {
    console.log("[★] Stealth Zygisk Frida Injected. Activating dynamic TrustManager hook...");
    
    var TrustManagerImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
    if (TrustManagerImpl) {
        TrustManagerImpl.checkTrustedRecursive.implementation = function(certs, host, clientAuth, untrustedChain, trustAnchorChain, certIndex) {
            console.log("[+] Conscrypt TrustManagerImpl check bypassed for Host: " + host);
            return certs; // Intercept & trust list unconditionally
        };
    }
});
EOF

# Grant execution clearances
ui_print "- Gadget library staging..."
chmod 755 "$MODPATH/lib/frida-gadget.so" || true
ui_print "- Stealth Gadget architecture merged!"
