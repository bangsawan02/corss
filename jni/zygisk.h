#pragma once

#include <jni.h>
#include <stdint.h>

namespace zygisk {

struct AppSpecializeArgs {
    jint &uid;
    jint &gid;
    jintArray &gids;
    jint &runtime_flags;
    jobjectArray &rlimits;
    jint &mount_external;
    jstring &se_info;
    jstring &nice_name;
    jstring &instruction_set;
    jstring &app_data_dir;
    jboolean &is_child_zygote;
    jboolean &is_top_app;
    jobjectArray &pkg_data_info_list;
    jobjectArray &whitelisted_data_info_list;
    jboolean &mount_data_dirs;
    jboolean &mount_storage_dirs;
};

struct ServerSpecializeArgs {
    jint &uid;
    jint &gid;
    jintArray &gids;
    jint &runtime_flags;
    jobjectArray &rlimits;
    jlong &permitted_capabilities;
    jlong &effective_capabilities;
};

class Api {
public:
    virtual int getApiVersion() = 0;
    virtual void setOption(int opt) = 0;
    virtual int getCompanionFd() = 0;
};

class ModuleBase {
public:
    virtual ~ModuleBase() {}
    virtual void onLoad(Api *api, JNIEnv *env) {}
    virtual void preAppSpecialize(AppSpecializeArgs *args) {}
    virtual void postAppSpecialize(const AppSpecializeArgs *args) {}
    virtual void preServerSpecialize(ServerSpecializeArgs *args) {}
    virtual void postServerSpecialize(const ServerSpecializeArgs *args) {}
};

typedef void (*RegisterModuleFn)(ModuleBase *);

} // namespace zygisk

extern "C" {
void zygisk_register_module(void *);
}

#define REGISTER_ZYGISK_MODULE(Clazz) \
extern "C" void zygisk_register_module(void *reg) { \
    reinterpret_cast<zygisk::RegisterModuleFn>(reg)(new Clazz()); \
}
