# Whisper Of Words App Store

A lightweight, GitHub Pages-based catalog for Whisper Of Words Android apps.

## Current state

- Static storefront: GitHub Pages
- Catalog data: `data/apps.json` + `data/wow-note.json`
- App assets: `apps/<slug>/`
- Current WoW Reader development/release source of truth: `whispermmepub/wow-reader-lab`
- Current WoW Reader release line: **v2.20.0 / versionCode 64**
- WoW Reader package: `com.whisper.wowreader`
- The App Store repository is only the storefront/distribution layer; Android source code is not copied here.

## Adding a release

1. Build and verify the release from the source repository.
2. Publish the intended APK under `apps/<slug>/`.
3. Update the matching entry in `data/apps.json` with version, size, date and APK path.
4. Keep screenshots/icons small and web-ready.
5. Verify the GitHub Pages site and the APK download link before announcing the release.

For WoW Reader, do not publish a new APK by guessing the versionCode. Check the source repo and Play tracks first. Preserve the production package/signing identity.

## Storage hygiene

This repository should contain only storefront source, metadata and intentionally published app assets.

Do **not** commit:
- AABs, ZIP backups or build output
- local IDE/editor state
- generated temporary files
- base64 staging files used only to transfer/repair previews

Published APKs are intentionally allowed because this site is a direct-download app store.

## Continuation with WoW Reader

The latest Reader work is designed around large libraries (100,000+ books), incremental per-book Drive sync, resumable transfer checkpoints, paginated restore, SHA-256 integrity, tombstones, custom covers and whole-book page numbering.

The App Store must stay independent of those internal Android implementation details. It only needs the final verified APK, metadata and screenshots. See `STORE_RELEASE_HANDOFF.md` for the current handoff/test checklist.

## Current catalog

The repository currently contains storefront listings for:
- WoW Reader
- WoW Note
- WoW EPUB Maker
- WoW OCR
- WoW Proof Reader

Preview-only listings remain download-disabled until their release APK is intentionally published.
