# Flutter full parity — design

**Date:** 2026-11-19
**Status:** approved by scope ("todo absolutamente todo"), implementation in progress.
**Branch:** `feat/flutter-app` (PR #84). The Tauri app remains the stable release
until the user tests and approves a cutover.

## 1. Intent and why

Vibebook today is a Tauri shell + React UI + Python sidecar. The Flutter app in
`app/` already proves the hard parts (EPUB ingest, Piper, Edge, karaoke timings,
ambience, M4B, Windows/macOS/Linux/Android CI), but it is still a partial port.
The goal is a real replacement: every user-visible capability of the Tauri app
lives in Flutter/Dart, the existing library on disk keeps working, and no Python
runtime is needed.

The why: one codebase instead of three toolchains, Android becomes viable, and
the reader/TTS pipeline stops depending on a PyInstaller sidecar that cannot run
on mobile.

## 2. Goals

- Full functional parity with the Tauri app for:
  - library, search, sort/filter, detail, covers, delete, import;
  - Studio: Piper, Edge, Azure, Gemini, ElevenLabs, Kokoro, eSpeak, VEP;
  - provider keys (Gemini/ElevenLabs/Azure) with save/test/delete;
  - persistent conversion jobs with progress, cancel, resume;
  - reader Texto, Libro (paginated) and Original (EPUB XHTML);
  - in-book search, audio + reading bookmarks, reading state;
  - sleep timer, playback speed/volume, chapter navigation, auto-advance;
  - fullscreen, keyboard shortcuts, media session/background audio;
  - ambience assets/plan/analysis/live mix/ambient M4B export;
  - repair sync, re-segment, restore;
  - appearance/reader settings, provider settings, plugin settings;
  - i18n es/en, accessibility AA;
  - library/DB/settings migration from the Tauri app;
  - packaging for Windows, macOS (unsigned DMG), Linux, Android.
- Keep `manifest.json` and the on-disk library layout as the source of truth.
- Keep the app local-first: no account, no telemetry, cloud only when configured.

## 3. Non-goals

- iOS (explicitly dropped by the user in this migration).
- Web parity (out of scope per the parity matrix).
- Signed releases / auto-update until certificates exist (same as Tauri today).
- Deleting the Tauri app, `.books/`, or the user's library.
- Bundling TTS models in the installer.

## 4. Approaches considered

1. **Dart pure (chosen).** Rewrite the remaining Python logic in Dart/Flutter.
   One codebase, no runtime, Android viable. Risks: Kokoro Spanish, EPUB
   Original fidelity, live ambience mixing, media session on desktop.
2. **Python embedded** (`serious_python`). Keeps the 13.8k-line engine and 531
   tests, fastest functional parity. Rejected: two runtimes, large installer,
   Android/iOS restrictions, and it does not deliver the migration the user
   asked for.
3. **UI-only port with the Python sidecar.** Same as 2 with extra steps; the
   Tauri shell would just be replaced by Flutter. Rejected for the same reasons.

The existing ADRs (`docs/refactor/adr/`) and the working Flutter pipeline already
point to option 1. The remaining gaps are bounded and testable.

## 5. Architecture

- **Data layer** (`app/lib/data/`)
  - `library_repository`: scan/import/delete; manifest is truth.
  - `bookmark_repository`: audio bookmarks + reading state + reading bookmarks.
  - `preferences_repository`: per-book reader preferences.
  - `job_repository`: `jobs.json` at the library root; durable jobs.
  - `provider_key_store`: `provider-keys.json` in app data; env vars win;
    0600 on Unix.
  - `tts/`: engine specs, voice catalog, cloud clients, synthesizers.
  - `covers/`: Open Library/Google Books search.
  - `repair/`: segment repair/re-segment/restore.
  - `ambience/`: assets, plan, analyzer, mix/export.
- **Feature layer** (`app/lib/features/`)
  - `library`, `import`, `book_detail`, `studio`, `reader`, `settings`.
- **State**: Riverpod. One controller per concern; no widget-owned audio.
- **Persistence**: JSON sidecars per book + `jobs.json` + SharedPreferences.
  No Drift in this pass. The Tauri SQLite is migrated/read once; SQLite/FTS is
  an internal optimization, not a parity requirement.
- **TTS registry**:
  - `TtsEngineSpec(id, label, transport, requiresKey, supportsStyles, timing,
    maxChars, audioSuffix, description, available)`.
  - `listTtsVoices(engine)` returns the engine's catalog.
  - `ChapterSynthesizer` implementations: Piper, Edge, Azure, Gemini,
    ElevenLabs, Kokoro (spike/fallback), eSpeak (if binary).
- **Conversion jobs**: `JobRunner` wraps `TtsConversionService`, persists
  progress per chapter, supports cancel and resume by skipping chapters whose
  audio + timing match the same engine/voice/rate.
- **Reader**:
  - `ReaderViewMode { text, book, original }`.
  - `TextReader` = existing scroll view with karaoke.
  - `BookReader` = paginator with word spans, page cache, double page on wide
    screens, page-turn animation, karaoke auto-page.
  - `OriginalReader` = sanitized EPUB XHTML via
    `flutter_widget_from_html_core`, no scripts, images resolved from the EPUB.
  - Shared `ReaderPlaybackController`, sleep timer, shortcuts, fullscreen.
- **Media session**: `audio_service`/`just_audio` on Android; SMTC on Windows
  when the package supports it; documented fallback on other desktop targets.
- **i18n**: `flutter_localizations` + ARB, Spanish default, English complete.
- **Migration**: read the Tauri SQLite (`library.db`) and settings if present;
  import reading state/bookmarks/preferences idempotently; never rewrite
  `manifest.json` except through the existing conversion/repair paths.

## 6. Parity checklist

| Area | Tauri | Flutter target |
|---|---|---|
| Library scan/search/sort/filter | yes | yes |
| Import EPUB + drag/drop + validation | yes | yes (validation to harden) |
| Covers extracted/generated/searched | yes | add search |
| Detail + delete + metadata | yes | yes |
| Piper | yes | yes |
| Edge | yes | yes (v2 token + raw WS) |
| Azure | yes | add |
| Gemini | yes | add |
| ElevenLabs | yes | add |
| Kokoro | yes | spike; fallback documented |
| eSpeak | yes | add if binary available |
| VEP plugins | yes | add |
| Provider keys + test | yes | add |
| Persistent jobs/progress/cancel/resume | yes | add |
| Segment cache | yes | add chapter-level resume |
| Styles + rate | yes | add for cloud |
| Preview voice | yes | yes (Piper/Edge; add cloud) |
| Reader Texto | yes | yes |
| Reader Libro paginated | yes | add |
| Reader Original | yes | add |
| Karaoke word/segment | yes | yes |
| Player play/skip/chapter/speed/volume | yes | add missing controls |
| Sleep timer | yes | add |
| Auto-advance | yes | yes |
| In-book search | yes | add text search |
| Audio + reading bookmarks | yes | add reading bookmarks |
| Reading state | yes | yes |
| TOC | yes | yes |
| Keyboard shortcuts | yes | add |
| Fullscreen | yes | add |
| Media session/background | yes | add/best-effort |
| Ambience assets/plan/analysis/mix/export | yes | partial; complete |
| Repair sync/resegment/restore | yes | add |
| Settings appearance/reader/providers/plugins | yes | add |
| i18n es/en | planned | add |
| Migration library/DB/state | yes | add |
| Accessibility AA | yes | audit/fix |
| Packaging Win/macOS/Linux/Android | yes | yes (existing CI) |
| Auto-update/signing | no | defer, document |

## 7. Decisions (my calls)

- **JSON-first persistence** instead of Drift in this pass: the on-disk
  manifest is already the truth, sidecars are simple and portable, and it avoids
  a risky schema migration. Documented as an internal optimization to revisit.
- **Original mode is sanitized HTML, not a WebView.** It works on every target,
  has no JS/security surface, and is good enough for reading. Fidelity limits
  are documented.
- **Cloud word timings are estimated** except ElevenLabs (native alignment).
  Azure REST does not expose word boundaries; the Azure SDK path is not
  available in Dart. The reader falls back to segment/word estimation.
- **Kokoro** is attempted with the available ONNX stack; if the Spanish model
  cannot be driven without Python, the app shows a clear "not available in this
  build" message with Piper/cloud alternatives. This is the one parity item that
  may remain conditional; it is surfaced, never silent.
- **Media session** is best-effort on desktop; Android gets the full
  `audio_service` path. No silent failure: the UI states the limitation.
- **Provider keys** live in app data with 0600 on Unix and environment-variable
  precedence, same as Tauri. No key is ever shown in full.
- **No releases, tags, or publishing** until the user tests and approves.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Kokoro Spanish not viable in Dart | Spike, clear fallback message, keep Piper/cloud |
| Original mode fidelity | Sanitized HTML, document limits, no scripts |
| Live ambience mixing | Multiple players + fades; measure; native/FFI if needed |
| Media session on Windows | SMTC integration; fallback documented |
| Cloud APIs change | Isolated clients, retries, clear errors, no secrets in logs |
| FFmpeg on ARM64 | Existing fallback/documented limitation |
| Data loss in migration | Read-only import, backups, tests, never delete `.books/` |
| Regression in reader playback | Existing controller tests + smoke |

## 9. Done criteria

- Every row in the parity checklist has a Flutter implementation or an explicit,
  user-visible limitation approved by the user.
- `flutter analyze` clean, `flutter test` green, Windows release build works.
- Real smoke: import → convert with each available engine → read in all three
  modes → search → bookmarks → sleep timer → export.
- Existing library and settings survive a fresh install.
- The user tests the build and approves before any tag/release.

## 10. Builder check

The design is intentionally implementation-agnostic where the user has not
expressed a preference; the plan pins files, signatures, and tests. The builder
must preserve the existing library and never touch `.books/` outside the book's
own directory.
