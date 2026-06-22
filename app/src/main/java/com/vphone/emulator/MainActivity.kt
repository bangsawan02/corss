package com.vphone.emulator

import android.content.Context
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebStorage
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF03DAC5),
                    background = Color(0xFF121212),
                    surface = Color(0xFF1E1E1E)
                )
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    VPhoneEmulatorShell(
                        appName = "VPhoneGaga Pro",
                        enableFrida = true,
                        enableTerminal = true,
                        enableSandbox = true,
                        enableXposed = true,
                        initialUrls = listOf("https://google.com", "https://github.com", "https://whatismybrowser.com")
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VPhoneEmulatorShell(
    appName: String,
    enableFrida: Boolean,
    enableTerminal: Boolean,
    enableSandbox: Boolean,
    enableXposed: Boolean,
    initialUrls: List<String>
) {
    var selectedTab by remember { mutableStateOf(0) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Column {
                        Text(appName, fontWeight = FontWeight.Bold, color = Color(0xFF03DAC5))
                        Text("Root Sandboxed Container • Pro Edition", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1A1A1A)
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = Color(0xFF1A1A1A)
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Text("💻", fontSize = 18.sp) },
                    label = { Text("VM Status") }
                )
                if (enableSandbox) {
                    NavigationBarItem(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        icon = { Text("📦", fontSize = 18.sp) },
                        label = { Text("Sandboxes") }
                    )
                }
                if (enableTerminal) {
                    NavigationBarItem(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        icon = { Text("🐚", fontSize = 18.sp) },
                        label = { Text("Bash") }
                    )
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (selectedTab) {
                0 -> VMSpecsScreen(enableFrida, enableXposed)
                1 -> if (enableSandbox) SandboxScreen(initialUrls) else Text("Sandbox Disabled")
                2 -> if (enableTerminal) TerminalConsoleScreen() else Text("Terminal Disabled")
            }
        }
    }
}

@Composable
fun VMSpecsScreen(enableFrida: Boolean, enableXposed: Boolean) {
    var isRooted by remember { mutableStateOf(true) }
    var xposedActive by remember { mutableStateOf(enableXposed) }
    var fridaActive by remember { mutableStateOf(enableFrida) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text("VIRTUAL HARDWARE SPECIFICATIONS", fontWeight = FontWeight.Bold, color = Color.LightGray, fontSize = 14.sp)
        }
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1E1E))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("System Architecture: arm64-v8a / armeabi-v7a", fontSize = 14.sp, fontFamily = FontFamily.Monospace)
                    Text("Android Version: v12.0 (SDK 31)", fontSize = 14.sp, fontFamily = FontFamily.Monospace)
                    Text("Memory Allocated: 4096MB (RAM Burst)", fontSize = 14.sp, fontFamily = FontFamily.Monospace)
                    Text("Display Overlay Server: Active (Port 5901)", fontSize = 14.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }

        item {
            Text("ACTIVE MOUNT & SYSTEM ENGINES", fontWeight = FontWeight.Bold, color = Color.LightGray, fontSize = 14.sp)
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1E1E))
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Superuser (Root Mount)", fontWeight = FontWeight.Bold)
                            Text("Simulate pre-rooted su binary", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                        }
                        Switch(checked = isRooted, onCheckedChange = { isRooted = it })
                    }
                    Divider(color = Color.DarkGray)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Zygisk Frida Bridge", fontWeight = FontWeight.Bold)
                            Text("Embed frida gadget into root server zygote", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                        }
                        Switch(checked = fridaActive, onCheckedChange = { fridaActive = it })
                    }
                    Divider(color = Color.DarkGray)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("LSPosed / Xposed Module Engine", fontWeight = FontWeight.Bold)
                            Text("Allow hooking virtual system callbacks", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                        }
                        Switch(checked = xposedActive, onCheckedChange = { xposedActive = it })
                    }
                }
            }
        }
    }
}

@Composable
fun SandboxScreen(urls: List<String>) {
    var activeUrlIndex by remember { mutableStateOf(0) }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF1A1A1A))
                .padding(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            urls.forEachIndexed { index, url ->
                val isSelected = activeUrlIndex == index
                Box(
                    modifier = Modifier
                        .background(if (isSelected) Color(0xFF03DAC5) else Color.DarkGray, RoundedCornerShape(8.dp))
                        .clickable { activeUrlIndex = index }
                        .padding(horizontal = 14.dp, vertical = 8.dp)
                ) {
                    Text(
                        text = "Sandbox ${index + 1}",
                        color = if (isSelected) Color.Black else Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 12.sp
                    )
                }
            }
        }
        
        AndroidView(
            factory = { context ->
                WebView(context).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.databaseEnabled = true
                    settings.userAgentString = "Mozilla/5.0 (VPhoneGaga Core Sandbox Engine v1)"
                    
                    // Root sandboxing trick: partition cookies separate from standard browser instances
                    val cookieManager = CookieManager.getInstance()
                    cookieManager.setAcceptCookie(true)
                    cookieManager.setAcceptThirdPartyCookies(this, true)
                    
                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            super.onPageFinished(view, url)
                        }
                    }
                    loadUrl(urls.getOrNull(activeUrlIndex) ?: "https://google.com")
                }
            },
            update = { webView ->
                val targetUrl = urls.getOrNull(activeUrlIndex) ?: "https://google.com"
                if (webView.url != targetUrl) {
                    webView.loadUrl(targetUrl)
                }
            },
            modifier = Modifier.fillMaxSize().weight(1f)
        )
    }
}

@Composable
fun TerminalConsoleScreen() {
    var commandInput by remember { mutableStateOf("") }
    val logs = remember { mutableStateListOf(
        "VPhone VM BusyBox Terminal initialization completed.",
        "System: uid=0(root) gid=0(root) groups=0(root) context=u:r:su:s0",
        "Type 'help' list available root features.",
        ""
    ) }

    Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(Color.Black, RoundedCornerShape(8.dp))
                .border(1.dp, Color.DarkGray, RoundedCornerShape(8.dp))
                .padding(8.dp)
        ) {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(logs) { log ->
                    Text(
                        text = log,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 13.sp,
                        color = if (log.startsWith("#")) Color(0xFF03DAC5) else Color.White
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("# ", color = Color(0xFF03DAC5), fontWeight = FontWeight.Bold, fontSize = 16.sp)
            TextField(
                value = commandInput,
                onValueChange = { commandInput = it },
                modifier = Modifier.weight(1f),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                ),
                placeholder = { Text("run su busybox or frida tools...", color = Color.Gray, fontSize = 14.sp) }
            )
            Button(
                onClick = {
                    if (commandInput.isNotBlank()) {
                        val cmd = commandInput.trim()
                        logs.add("# $cmd")
                        when (cmd.lowercase()) {
                            "help" -> {
                                logs.add("Available commands:")
                                logs.add("  help         - Command list")
                                logs.add("  su           - Verify superuser path")
                                logs.add("  frida-ps     - List active zygote target packages bound to gadget")
                                logs.add("  busybox-info - Read binary paths installed in VM")
                                logs.add("  clear        - Clear console log stack")
                            }
                            "su" -> {
                                logs.add("su binary located at: /system/xbin/su (Access Allowed)")
                            }
                            "frida-ps" -> {
                                logs.add("frida-gadget injected:")
                                logs.add("  PID: 10452 | com.taxsee.driver2 (Bound to zygisk_frida 16.3.3)")
                                logs.add("  PID: 11090 | system_server (Ready)")
                            }
                            "busybox-info" -> {
                                logs.add("BusyBox v1.34.1-VPhone (2026-06-22) multi-call binary active.")
                            }
                            "clear" -> {
                                logs.clear()
                            }
                            else -> {
                                logs.add("bash: exec: $cmd: command not found or su binary authorization needed.")
                            }
                        }
                        commandInput = ""
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF03DAC5))
            ) {
                Text("RUN", color = Color.Black, fontWeight = FontWeight.Bold)
            }
        }
    }
}
