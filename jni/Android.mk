LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)

LOCAL_MODULE := zygisk_frida
LOCAL_SRC_FILES := main.cpp
LOCAL_LDLIBS := -llog -ldl

# Target SDK 21+ for Modern Android and maximum optimization
LOCAL_CFLAGS += -Wall -O3 -std=c++17

include $(BUILD_SHARED_LIBRARY)
