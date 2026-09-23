# Mobile Use Android

This repository is now dedicated to the Android port of Mobile Use.

Upstream reference: https://github.com/minitap-ai/mobile-use

The app is a native Android MVP that runs on the phone without a PC or ADB. It uses AccessibilityService to inspect the visible UI and execute LLM-planned tap, type, back, home, scroll and wait actions.

Setup:
1. Install the debug APK.
2. Enable Mobile Use in Android Accessibility settings.
3. Enter an LLM-compatible endpoint and API key.
4. Enter a task and press Run.

Current MVP; screenshot/vision understanding, verification/retry, voice, safer confirmations and release signing are planned next.
