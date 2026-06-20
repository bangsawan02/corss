# Zygisk Frida Gadget

This is a **Zygisk-based Frida Gadget injector** Magisk module templates pre-configured for **GitHub Actions auto-compilations**.
Once loaded, the module intercepts the specialist specialized loops inside Android's Zygote process to dynamically inject a `dlopen` hook, launching the packaged Frida Gadget (`libfrida-gadget.so`) safely inside your target user app processes.

## 🔥 Key Features

- **Magisk Zygisk Hooking:** Zero runtime configuration, robust injection bypassing basic hook indicators by working straight from the specialised process initialization.
- **SELinux Bypass:** Mounts the compiled Frida Gadget `libfrida-gadget.so` into system libraries (`/system/lib(64)/`), bypassing Android's strict SELinux rules preventing standard applications from executing custom shared objects from `/data/adb/modules/`.
- **Dynamic Package Lists:** Add or remove bundle targets dynamically without ever needs for re-compilations! Just append package identifiers to `/data/local/tmp/frida-targets`.
- **Pre-Configured Frida Configuration:** Pre-configured to execute in **SCRIPT** Mode dynamically.
- **Full Automated CI/CD:** Ready to push to GitHub; standard workflows fetch pre-built gadgets, run NDK native compilers, and construct flashable ZIP module archives ready to sideload.

---

## 🛠️ File Structure

```text
├── .github/workflows/
│   └── build.yml               # GitHub CI builder workflow
├── jni/
│   ├── Android.mk              # NDK Build Instructions
│   ├── Application.mk          # Target CPU and architectures
│   ├── main.cpp                # Core C++ module and hooks logic
│   └── zygisk.h                # Zygisk interface header file
├── customize.sh                # Magisk installation customization script
├── libfrida-gadget.config.json # Frida runtime mode JSON parameters
├── module.prop                 # Module metadata information
└── README.md                   # This instruction documentation
```

---

## 🚀 Step-by-Step Guide

### 1. Make GitHub Repository
1. Create a **New Repository** on your GitHub account.
2. Push all the gen files in this directory to your newly created repository:
   ```bash
   git init
   git add .
   git commit -m "Initialize Zygisk Frida Module Builder"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

### 2. Compile via GitHub Actions
GitHub Actions will automatically run upon pushed commits to build the native C++ code and package your flashable Magisk module:
1. Navigate to the **Actions** tab of your GitHub Repository.
2. Click on the **Build Zygisk Frida Module** workflow.
3. Click **Run workflow** (or pushes to watch it build in real time!).
4. Once completed, your final flashable **ZIP Module** is available as a build artifact in the Action run attachments!

### 3. Flash on Android Device
1. Transfer the compiled `zip` file from GitHub artifacts to your Android phone storage.
2. Open the **Magisk App**, go to the **Modules** tab, and click **Install from storage**.
3. Select the compiled ZIP module.
4. Magisk will process, execute the permissions in `customize.sh`, and complete.
5. Reboot your device to trigger the Zygisk registration hooks.

---

## ⚙️ Target Settings & Configurations

### Static Settings
- Default targeted app: `com.taxsee.driver2`

### Dynamic Configuration (No Rebuilding Needed!)
If dynamic targets config is enabled, you can edit targets actively via Android Shell:
1. Shell into your device (via local terminal emulator or shell ADB):
   ```bash
   adb shell
   ```
2. Edit target packages:
   ```bash
   # Add new app ID
   echo "com.target.package.name" >> /data/local/tmp/frida-targets
   
   # Or replace everything in file
   echo "com.target.app" > /data/local/tmp/frida-targets
   ``s

---

## 💎 Frida Gadget Parameter Spec
The Frida gadget configuration is written dynamically based on your build variables inside `libfrida-gadget.config.json`:
- Mode: `script`


- Internal Script File Path: `/data/local/tmp/custom-frida-script.js`
