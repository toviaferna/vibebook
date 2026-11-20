# Flutter full-parity implementation plan

> **Status (2026-11-19):** Tasks 1–7 implemented and tested (cloud providers,
> keys, jobs, reader Texto/Libro/Original, search, bookmarks, sleep timer,
> shortcuts/fullscreen, covers, VEP plugins and re-segmentation with backups).
> Remaining: Drift/FTS, background audio/media session, Kokoro, i18n,
> Tauri SQLite state migration, auto-update/signing. The Windows build and 148
> tests pass; no tag or release until the user tests and approves.

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans
> (this session) or superpowers:subagent-driven-development (fresh agents).
> Steps use checkbox (`- [ ]`) syntax.

**Goal:** Finish the Flutter migration of Vibebook so the Tauri/Python app has no
user-visible feature left behind.

**Architecture:** Dart-pure Flutter app in `app/`. The library manifest stays the
source of truth; JSON sidecars hold jobs/bookmarks/preferences; cloud TTS clients
are isolated behind `ChapterSynthesizer`; the reader shares one playback
controller across Texto/Libro/Original modes.

**Tech Stack:** Flutter 3.50 / Dart 3.14, Riverpod 3.5, go_router 18.1,
audioplayers 6.8, FFmpegKit audio, sherpa_onnx, piper_phonemize, archive, html,
dio, shared_preferences, file_selector, desktop_drop, path_provider.

**Spec:** `docs/superpowers/specs/2026-11-19-flutter-full-parity-design.md`

## Global constraints

- Never touch `.books/` outside a book's own directory; no destructive migration.
- No tags, releases, or publishing without the user's explicit approval.
- Keep Spanish as the default UI language; English is a translation, not a fork.
- `flutter analyze` and `flutter test` must stay green after every task.
- Every cloud request is opt-in and never logs the key.
- Every new screen has an empty/loading/error state.
- Commit per task with a conventional message.

## Review focus

- A corrupt/missing sidecar (`bookmarks.json`, `jobs.json`, provider keys) must
  not make the reader or Studio unusable.
- A cloud key that is missing, revoked, rate-limited, or returns HTML must show
  an actionable message, never crash the conversion.
- A book with no audio must still open, search, bookmark, and paginate.
- An EPUB with missing images/links must render the text without exceptions.
- Cancelling a job or closing the app mid-conversion must not corrupt the
  manifest or leave a half-written audio file.

---

### Task 1: Provider key store and status

**Files:**
- Create: `app/lib/domain/providers.dart`
- Create: `app/lib/data/providers/provider_key_store.dart`
- Create: `app/test/provider_key_store_test.dart`
- Modify: `app/lib/app/providers.dart`

**Interfaces:**
- `ProviderInfo` with `id, label, description, docsUrl, keyUrl, requiresRegion`.
- `ProviderStatus` with `info, configured, hint, source, region`.
- `ProviderKeyStore({String? path})`:
  - `Future<List<ProviderStatus>> list()`
  - `Future<void> save(String id, {required String apiKey, String? region})`
  - `Future<void> delete(String id)`
  - `Future<String?> key(String id)` / `Future<String?> region(String id)`
  - `Future<ProviderTestResult> test(String id)`

- [ ] Test: saving a short key or a key with spaces throws `ProviderKeyException`.
- [ ] Test: keys round-trip; `hint` is `••••` + last four; no full key in JSON.
- [ ] Test: environment variables (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`,
  `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION`) take precedence over the file.
- [ ] Test: a corrupt file is treated as empty and does not throw.
- [ ] Implement save with a temp file + rename; `chmod 600` on non-Windows.
- [ ] Wire `providerKeyStoreProvider` into Riverpod.

### Task 2: Cloud TTS clients

**Files:**
- Create: `app/lib/data/tts/cloud/cloud_tts.dart` (shared result/exception)
- Create: `app/lib/data/tts/cloud/azure_tts.dart`
- Create: `app/lib/data/tts/cloud/gemini_tts.dart`
- Create: `app/lib/data/tts/cloud/elevenlabs_tts.dart`
- Create: `app/test/cloud_tts_test.dart`
- Modify: `app/lib/data/tts/chapter_synthesizer.dart`

**Interfaces:**
- `CloudAudio { Uint8List bytes; String extension; List<WordTimingData> words; }`
- `CloudTtsClient.synthesize({text, voice, style, rate})`.
- `CloudChapterSynthesizer implements ChapterSynthesizer` with a per-segment
  client, FFmpeg decode to mono PCM 24 kHz, concatenation with pauses, character-
  proportional spans, and native words when the client returns them.

- [ ] Test Azure SSML: style `cheerful` wraps `mstts:express-as`; neutral does not;
  XML escaping works; rate is validated.
- [ ] Test Gemini body: style instructions, `response_format`, model, voice.
- [ ] Test ElevenLabs: alignment character timings become word timings; `[tags]`
  are dropped; 402/429 messages are actionable.
- [ ] Test error mapping: 401/403/429/5xx/HTML produce `CloudTtsException` with a
  Spanish message and no key in the text.
- [ ] Implement clients with Dio, timeouts, 3 attempts, `Retry-After`.
- [ ] Decode MP3/WAV to PCM via FFmpegKit; verify a 1 s fixture yields ~24k
  samples.
- [ ] Build `CloudChapterSynthesizer` and register it in the engine factory.

### Task 3: Engine registry, provider panel, Studio integration

**Files:**
- Create: `app/lib/data/tts/tts_engines.dart`
- Create: `app/lib/features/settings/providers_panel.dart`
- Modify: `app/lib/domain/models.dart` (`ttsVoiceId`, `ttsStyle`, `ttsRate`,
  keep legacy fields readable)
- Modify: `app/lib/app/providers.dart` (engine/voice/rate/style updates)
- Modify: `app/lib/features/settings/settings_page.dart` (mount panel)
- Modify: `app/lib/features/studio/studio_page.dart` (engine list, voice list,
  styles, rate, availability, preview)
- Create: `app/test/tts_engines_test.dart`

**Interfaces:**
- `TtsEngineSpec` + `ttsEngines` + `ttsVoiceCatalog` + `defaultTtsVoice`.
- `BuildContext`-free helper `engineAvailability(spec, statuses)`.

- [ ] Test engine list includes piper, edge, azure, gemini, elevenlabs, kokoro,
  espeak; cloud ones report `configured` from the key store.
- [ ] Test voices filter by engine and include Spanish cloud voices/styles.
- [ ] Provider panel: list, key/region fields, save, delete, test, source badge,
  hint, docs/key links; no key echo.
- [ ] Studio: engine selector with availability badges; voice picker for cloud;
  style chips when supported; rate slider; "no configurada" card with a jump to
  settings; preview uses the selected engine.
- [ ] Settings migration: old `ttsEngine`/`edgeVoiceId`/`edgeRate` still load.

### Task 4: Persistent conversion jobs

**Files:**
- Create: `app/lib/domain/jobs.dart`
- Create: `app/lib/data/jobs/job_repository.dart`
- Create: `app/lib/data/jobs/job_runner.dart`
- Create: `app/test/job_repository_test.dart`
- Create: `app/test/job_runner_test.dart`
- Modify: `app/lib/app/providers.dart`
- Modify: `app/lib/features/studio/studio_page.dart`

**Interfaces:**
- `ConversionJob(id, bookId, status, stage, completed, total, chapterIndex,
  message, error, engine, voice, style, rate, createdAt, updatedAt)`.
- `JobRepository` in `<library>/.vibebook/jobs.json` (atomic write).
- `JobRunner.start(book, synthesizer, ...)`, `cancel()`, `resume(job)`.

- [ ] Test: create/update/list/complete/cancel round-trip; corrupt JSON resets.
- [ ] Test: a job left `running` on startup becomes `interrupted`.
- [ ] Test: resume skips chapters whose `audio` + `timing` match engine/voice/rate.
- [ ] Test: cancel between chapters leaves `manifest.status = imported` and no
  partial chapter file.
- [ ] Studio: progress card with stage, chapter, percent, message, cancel and
  resume buttons; job survives page leave and app restart.

### Task 5: Reader view modes — Libro and Original

**Files:**
- Create: `app/lib/features/reader/reader_view_mode.dart`
- Create: `app/lib/features/reader/book_paginator.dart`
- Create: `app/lib/features/reader/book_reader.dart`
- Create: `app/lib/features/reader/original_reader.dart`
- Create: `app/test/book_paginator_test.dart`
- Create: `app/test/original_reader_test.dart`
- Modify: `app/lib/domain/models.dart` (`ReaderPreferences.viewMode`,
  `pageTurn`; per-book preferences)
- Modify: `app/lib/features/reader/reader_page.dart`
- Modify: `app/pubspec.yaml` (`flutter_widget_from_html_core`)

**Interfaces:**
- `BookPage { chapterIndex, startChar, endChar, spans, wordIndexes }`.
- `BookPaginator.paginate(chapter, size, style, images) -> List<BookPage>`.
- `OriginalReader(book, chapter, onLink)`.

- [ ] Test paginator: a long chapter produces >1 page; no character is lost;
  every page fits the height; images consume space; word indexes map.
- [ ] Test Original: sanitized `<script>`/`on*` removed; headings/paragraphs/
  emphasis preserved; missing image is a placeholder, not an exception.
- [ ] Integrate a Texto/Libro/Original segmented control; persist per book.
- [ ] BookReader: PageView, double page on wide screens, page turn buttons/keys,
  current word highlight, auto-page when karaoke crosses a page, progress.
- [ ] OriginalReader: render current chapter XHTML from `source.epub`, resolve
  images, internal links switch chapter, external links open the browser.

### Task 6: Reader search, reading bookmarks, timer, shortcuts, fullscreen

**Files:**
- Create: `app/lib/features/reader/reader_search.dart`
- Create: `app/lib/features/reader/reader_shortcuts.dart`
- Create: `app/lib/features/reader/reader_sleep_timer.dart`
- Modify: `app/lib/domain/bookmarks.dart` (reading bookmarks)
- Modify: `app/lib/data/bookmark_repository.dart`
- Modify: `app/lib/features/reader/reader_page.dart`
- Create: `app/test/reader_search_test.dart`
- Create: `app/test/reader_bookmarks_test.dart`
- Modify: `app/pubspec.yaml` (`window_manager`)

**Interfaces:**
- `ReaderSearchHit(chapterIndex, segmentId, offset, excerpt, positionMs)`.
- `ReadingBookmark(id, chapterIndex, charOffset, pageIndex, note, createdAt)`.
- `ReaderShortcuts` maps Space/arrows/T/F/?/Esc/+/-.

- [ ] Test search: finds across chapters, case/accent-insensitive, 2-char minimum,
  excerpt bounded, no results state.
- [ ] Test reading bookmarks CRUD and JSON round-trip; corrupt file resets.
- [ ] Search UI: results grouped by chapter, tap jumps to segment and highlights.
- [ ] Bookmarks UI: two tabs (audio/lectura), add note, delete, jump.
- [ ] Sleep timer: 5/15/30/45/60 min, pause at expiry, visible countdown.
- [ ] Shortcuts/fullscreen on desktop; no-op on mobile with a clear tooltip.
- [ ] Media session metadata + play/pause/next/prev where supported; documented
  fallback otherwise.

### Task 7: Covers, repair/re-segment/restore

**Files:**
- Create: `app/lib/data/covers/cover_search.dart`
- Create: `app/lib/features/book_detail/cover_search_dialog.dart`
- Create: `app/lib/data/repair/resegment.dart`
- Create: `app/lib/features/book_detail/resegment_panel.dart`
- Create: `app/test/cover_search_test.dart`
- Create: `app/test/resegment_test.dart`
- Modify: `app/lib/features/book_detail/book_detail_page.dart`
- Modify: `app/lib/app/providers.dart`

- [ ] Test cover search parses Open Library/Google Books fixtures, scores, and
  degrades to empty on HTTP errors.
- [ ] Test re-segment dry-run: reports changed chapters, never writes; apply
  writes a backup and reuses unchanged segment audio.
- [ ] Restore lists backups and restores manifest/audio idempotently.
- [ ] Detail UI: "Buscar portada", "Revisar segmentación", "Restaurar".

### Task 8: Ambience assets, plan editor, export parity

**Files:**
- Create: `app/lib/data/ambience/ambience_assets.dart`
- Create: `app/lib/features/library/ambience_panel.dart`
- Modify: `app/lib/domain/ambience_plan.dart` (beds/effects per chapter)
- Modify: `app/lib/features/reader/reader_page.dart`
- Modify: `app/lib/features/studio/studio_page.dart`
- Create: `app/test/ambience_assets_test.dart`

- [ ] Test asset import (license/checksum), delete, approval; corrupt index resets.
- [ ] Test plan: 1 bed + ≤3 effects, 8 s separation, 2 s guards, clamping.
- [ ] UI: asset library, per-chapter bed/effects, global mix, preview, attribution.
- [ ] Live mix: bed loop + ducking + one-shot effects; seek-aware.
- [ ] Ambient M4B export with sidechain/limiter; verify duration/chapters.

### Task 9: Plugins VEP, eSpeak, Kokoro

**Files:**
- Create: `app/lib/data/tts/plugins/vep_client.dart`
- Create: `app/lib/features/settings/plugins_panel.dart`
- Create: `app/lib/data/tts/kokoro_engine.dart`
- Create: `app/test/vep_client_test.dart`
- Create: `app/test/kokoro_engine_test.dart`

- [ ] Test VEP manifest parsing, HTTPS/loopback policy, token redaction, timeout.
- [ ] UI: add URL/token, test, list voices, delete.
- [x] eSpeak: detect binary, expose voice, clear missing-binary message.
- [ ] Kokoro: spike with available ONNX runtime; if unavailable, show a
  user-visible "no disponible" card with Piper/cloud alternatives.

### Task 10: Migration, i18n, a11y, packaging, docs

**Files:**
- Create: `app/lib/data/migration/tauri_migration.dart`
- Create: `app/l10n/app_es.arb`, `app/l10n/app_en.arb`
- Modify: `app/pubspec.yaml` (`flutter_localizations`, `intl`, `gen_l10n`)
- Modify: `app/lib/app/app.dart` (localizations)
- Create: `app/test/tauri_migration_test.dart`
- Modify: `.github/workflows/flutter.yml` (if needed)
- Modify: `app/README.md`, `docs/refactor/parity-matrix.md`

- [ ] Test migration: reads Tauri `library.db` if present, imports settings/
  state/bookmarks idempotently, never modifies `.books/`, missing DB = no-op.
- [ ] i18n: all user-facing strings via ARB; es default; en complete; locale
  switch in settings.
- [ ] A11y: semantics labels, focus order, contrast, 200% text scale.
- [ ] Packaging: Windows installer, macOS unsigned DMG, Linux, Android APK; CI
  green.
- [ ] Docs: parity matrix updated, README features/limitations, migration notes.

## Verification

- `flutter analyze` clean.
- `flutter test` green (existing 59 + new tests).
- `flutter build windows --release` works.
- Real smoke: import → convert with Piper/Edge/cloud → read Texto/Libro/Original
  → search → bookmarks → timer → export.
- CI green on Windows/Linux/macOS/Android.
- No tag/release until the user tests and approves.
