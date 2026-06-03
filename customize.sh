#/system/bin/sh
# ksu-frida Module Recovery installer routine
SKIPUNZIP=0
ui_print "- Target Arch: $ARCH"
ui_print "- Selected Port: 27342"
ui_print "- Storage Realm: /data/local/tmp/.aux_stealth"

mkdir -p "$MODPATH/bin"
mkdir -p "$MODPATH/hooks"

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
chmod 755 "$MODPATH/bin/frida-server" || true
ui_print "- Stealth patches merged!"
