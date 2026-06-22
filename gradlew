#!/usr/bin/env bash
# VPhoneGaga dynamic bootstrap utility script
if [ ! -f "gradle/wrapper/gradle-wrapper.jar" ]; then
    echo "Gradle wrapper jar missing. Generating via system gradle..."
    gradle wrapper --gradle-version 8.5 || true
fi
exec ./gradlew "$@"
