# Whisper Of Words App Store

A lightweight, Play Store-inspired catalog for Whisper Of Words apps.

The public storefront is built as a static GitHub Pages site. App metadata lives in `data/apps.json`, while each app keeps its screenshots and install files under `apps/<slug>/`.

## Adding another app

1. Add its APK and screenshots under `apps/<slug>/`.
2. Add one entry to `data/apps.json`.
3. The home catalog and app detail view update from the same data.

Current app: **WoW Reader**.
