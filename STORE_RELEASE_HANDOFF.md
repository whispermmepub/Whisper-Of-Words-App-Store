# Store Release Handoff

## Purpose

This file keeps the App Store repository ready to receive verified releases from the individual app repositories without copying app source code into the store.

## WoW Reader — current handoff

Source of truth: `whispermmepub/wow-reader-lab`

Current verified release line:
- Version: `2.20.0`
- versionCode: `64`
- Package: `com.whisper.wowreader`
- Release APK/AAB must come from the verified v64 build.
- Production signing identity must remain unchanged.

### Before publishing the APK

Run/confirm on the Reader side:
1. Highest Play-track versionCode check.
2. Package/applicationId check.
3. Production signer certificate check.
4. Release build + lint.
5. Upgrade test from v63.
6. Fresh-install test.
7. Incremental Drive restore/sync test.
8. 100k-scale contract tests.
9. Custom-cover regression test.
10. Whole-book pagination regression test.

Only after those checks should the final APK be copied into:
`apps/wow-reader/WoW-Reader-v<version>-v<versionCode>.apk`

Then update `data/apps.json`:
- `version`
- `size`
- `updated`
- `apk`
- relevant `whatsNew`

Do not change the Android package name or signing identity during a store upload.

## Store-side test checklist

After any published release:
- Home → Featured App loads.
- Apps → search/category filters work.
- Detail page loads.
- Screenshots load.
- Install/download button points to the exact published APK.
- Library/Updates state remains local-browser only and does not pretend to know Play Store installation state.
- GitHub Pages deployment succeeds.
- Direct APK URL returns the intended file.

## Important separation

The App Store repository is a static storefront/distribution repository. It should not contain:
- Android source code
- Gradle caches
- build directories
- AABs
- temporary ZIPs
- temporary base64 preview files
- local IDE state

The Android repositories remain the source of truth. The App Store receives only intentionally published release APKs and web-ready assets.

## Large-library work

The Reader's 100,000+ book scalability, database migration, incremental Drive sync, resumable uploads, tombstones, custom-cover storage and pagination are tested in the Reader repository. The Store must not duplicate those datasets or implementation files.

When Reader v64/v65/etc. is ready, continue from the verified release artifact rather than rebuilding or modifying the APK inside this repository.
