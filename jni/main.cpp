#include <android/log.h>
#include <jni.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <dlfcn.h>
#include <unistd.h>
#include <fcntl.h>
#include "zygisk.h"

#define LOG_TAG "ZygiskFrida"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

using zygisk::Api;
using zygisk::AppSpecializeArgs;

class ZygiskFridaModule : public zygisk::ModuleBase {
public:
    void onLoad(Api *api, JNIEnv *env) override {
        this->api = api;
        this->env = env;
        LOGI("ZygiskFridaModule onLoad called");
    }

    void preAppSpecialize(AppSpecializeArgs *args) override {
        if (!args || !args->nice_name) {
             return;
        }
        
        const char *process_name = env->GetStringUTFChars(args->nice_name, nullptr);
        if (process_name) {
            std::string proc(process_name);
            env->ReleaseStringUTFChars(args->nice_name, process_name);

            // Set flags inside is_target_app checks
            if (is_target_app(proc)) {
                enable_injection = true;
                LOGI("Target app discovered: [%s]. Arming Frida Gadget injection.", proc.c_str());
            }
        }
    }

    void postAppSpecialize(const AppSpecializeArgs *args) override {
        if (enable_injection) {
            LOGI("Injecting libfrida-gadget.so into specialised process...");
            
            // Try loading from mounted system paths first (bypasses isolation / SELinux blocks)
            void *handle = dlopen("libfrida-gadget.so", RTLD_NOW | RTLD_GLOBAL);
            if (handle) {
                LOGI("Frida Gadget loaded successfully via dlopen system mount!");
            } else {
                LOGE("dlopen direct libfrida-gadget.so failed: %s. Trying fallback local directory", dlerror());
                
                // Fallback attempt from root directory or /data/local/tmp if writable
                void* fallback_handle = dlopen("/data/local/tmp/re.frida.gadget.so", RTLD_NOW | RTLD_GLOBAL);
                if (fallback_handle) {
                     LOGI("Frida Gadget loaded via local fallback target path.");
                } else {
                     LOGE("dlopen fallback /data/local/tmp/re.frida.gadget.so failed: %s", dlerror());
                     LOGE("All dlopen injection vectors failed completely.");
                }
            }
        }
    }

private:
    Api *api = nullptr;
    JNIEnv *env = nullptr;
    bool enable_injection = false;

    bool is_target_app(const std::string& process_name) {
        // 1. Static check configured directly inside Web UI
        std::string static_target = "com.taxsee.driver2";
        LOGI("is_target_app checking process: [%s]", process_name.c_str());
        
        if (!static_target.empty() && process_name.find(static_target) != std::string::npos) {
            LOGI("Target matched static target %s", static_target.c_str());
            return true;
        }

        // 2. Dynamic check via disk storage configuration
        std::vector<std::string> disk_targets = load_targets("/data/local/tmp/frida-targets");
        for (const auto& target : disk_targets) {
            if (process_name.find(target) != std::string::npos) {
                LOGI("Matched dynamic target from disk: [%s]", target.c_str());
                return true;
            }
        }

        // 3. Fallback dynamic check inside module local repository
        std::vector<std::string> local_targets = load_targets("/data/adb/modules/zygisk-fridagadget/target_packages.txt");
        if (local_targets.empty()) {
            // Also try module path without knowing id just to be safe
            local_targets = load_targets("/data/adb/modules/zygisk_frida/target_packages.txt");
        }
        for (const auto& target : local_targets) {
            if (process_name.find(target) != std::string::npos) {
                LOGI("Matched dynamic target from local repo: [%s]", target.c_str());
                return true;
            }
        }

        return false;
    }

    std::vector<std::string> load_targets(const std::string& path) {
        std::vector<std::string> list;
        std::ifstream file(path);
        if (!file.is_open()) {
            LOGE("Failed to open target file: %s", path.c_str());
            return list;
        }

        std::string line;
        while (std::getline(file, line)) {
            // Trim whitespace
            line.erase(0, line.find_first_not_of(" \t\r\n"));
            line.erase(line.find_last_not_of(" \t\r\n") + 1);
            if (!line.empty() && line[0] != '#') {
                list.push_back(line);
                LOGI("Loaded dynamic target from file: %s", line.c_str());
            }
        }
        return list;
    }
};

REGISTER_ZYGISK_MODULE(ZygiskFridaModule)
