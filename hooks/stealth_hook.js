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