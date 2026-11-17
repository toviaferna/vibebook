# Flutter Engine Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate whether a pure Flutter/Dart engine can replace the Python sidecar on Windows and Android before committing to the full refactor.

**Architecture:** A throwaway Flutter app under `spike/flutter_engine/` exercises the riskiest native paths: Piper TTS via sherpa-onnx, Kokoro Spanish, FFmpeg/M4B, Drift with 10k books, EPUB ingest, a paginated reader with karaoke, background audio, and live ambience mixing. It produces measurements and a decision report; it does not ship.

**Tech Stack:** Flutter 3.50 / Dart 3.14, sherpa_onnx 2.0.1, flutter_onnxruntime 1.9.0, ffmpeg_kit_flutter_new_audio 2.5.8, drift 2.35, epub_plus 5.1.0 (vendored or direct), just_audio 0.10 + audio_service 0.18, flutter_riverpod 3.5.

**Spec:** `docs/refactor/02-stack-comparison.md`, `docs/refactor/03-architecture.md`, `docs/refactor/05-platform-matrix.md`, `docs/refactor/07-performance.md`, `docs/refactor/09-plan.md`, `docs/refactor/10-risks-decisions.md`.

## Global Constraints

- No production code, no release tags, no version bumps, no publication.
- Do not modify `.books/` or the existing Tauri/Python/React app.
- All spike files live under `spike/flutter_engine/` and are clearly marked throwaway.
- Do not commit API keys, model files, generated audio, `.dart_tool/`, `build/`, or `*.iml`.
- Models are downloaded on demand with SHA-256 verification; no model binary in git.
- Target hardware: Windows x64 and an Android arm64 device/emulator with API 24+.
- Every measurement records OS, CPU/device, build mode, command, value, and date.
- A failed experiment is a valid result; never fabricate a pass.
- G1 (engine decision) remains pending until the report is reviewed.

## Review Focus

- **EPUB encoding:** a CP1252/BOM EPUB with `ñ`, `á`, `ü`, `¿`, `¡` and embedded images must retain accents and structure.
- **Kokoro Spanish:** `ef_dora`/`em_alex`/`em_santa` must produce intelligible Spanish, not English-accented phonemes or silence.
- **Android background playback:** audio must continue with the screen off and survive app backgrounding for 5 minutes.
- **M4B integrity:** the output must have AAC audio, correct duration, chapter metadata, and a playable file.
- **Large library:** 10,000 books must query and scroll without jank or unbounded memory.

---

### Task 1: Scaffold the spike app

**Files:**
- Create: `spike/flutter_engine/` (Flutter project)
- Create: `spike/flutter_engine/README.md`
- Create: `spike/flutter_engine/lib/main.dart`
- Create: `spike/flutter_engine/pubspec.yaml` (via `flutter create` + deps)
- Create: `spike/flutter_engine/.gitignore`

**Interfaces:**
- Consumes: none.
- Produces: `main()` app with a home screen listing spike routes; `SpikeRoute` enum; `BenchmarkStore` (simple JSON file writer).

- [ ] **Step 1: Create the project**

Run:
```powershell
flutter create --org com.vibebook.spike --project-name vibebook_spike --platforms=windows,android spike/flutter_engine
```

Expected: project created; `flutter run -d windows` opens a counter app.

- [ ] **Step 2: Add dependencies**

Edit `spike/flutter_engine/pubspec.yaml` to add:
```yaml
dependencies:
  flutter_riverpod: ^3.5.0
  drift: ^2.35.4
  sqlite3: ^3.9.1
  path_provider: ^2.1.6
  path: ^1.9.0
  sherpa_onnx: ^2.0.1
  flutter_onnxruntime: ^1.9.0
  ffmpeg_kit_flutter_new_audio: ^2.5.8
  just_audio: ^0.10.6
  audio_service: ^0.18.19
  audio_session: ^0.2.4
  epub_plus: ^5.1.0
  archive: ^4.7.1
  xml: ^7.1.0
  html: ^0.15.7
  crypto: ^3.0.8
  intl: ^0.20.3
```

Run:
```powershell
flutter pub get
```

Expected: resolves without version conflicts; note exact resolved versions in `spike/flutter_engine/README.md`.

- [ ] **Step 3: Add the spike shell**

Replace `lib/main.dart` with a `MaterialApp` that lists routes:
`/db`, `/epub`, `/piper`, `/kokoro`, `/ffmpeg`, `/reader`, `/audio`, `/ambience`,
`/report`. Each route is a placeholder `Scaffold` with a title. Add a
`BenchmarkStore` that writes JSON to the app support directory.

- [ ] **Step 4: Verify it builds**

Run:
```powershell
flutter analyze
flutter build windows --debug
```

Expected: analyze clean; build succeeds.

- [ ] **Step 5: Commit**

```powershell
git add spike/flutter_engine
git commit -m "spike(flutter): scaffold engine validation app"
```

---

### Task 2: Drift 10k library benchmark

**Files:**
- Create: `spike/flutter_engine/lib/db/benchmark_db.dart`
- Create: `spike/flutter_engine/lib/db/books_table.dart`
- Create: `spike/flutter_engine/test/db_benchmark_test.dart`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/db`)

**Interfaces:**
- Consumes: `path_provider`, `drift`, `sqlite3`.
- Produces: `BenchmarkDatabase` with `Future<void> seed(int count)`,
  `Future<List<BookRow>> page({int limit, int offset})`,
  `Future<int> count()`, `Future<void> close()`.
  `BookRow` fields: `id`, `title`, `author`, `language`, `durationMs`.

- [ ] **Step 1: Write the failing test**

```dart
test('seed 10000 books and page in under 50ms', () async {
  final db = BenchmarkDatabase.inMemory();
  await db.seed(10000);
  final watch = Stopwatch()..start();
  final page = await db.page(limit: 100, offset: 0);
  watch.stop();
  expect(await db.count(), 10000);
  expect(page, hasLength(100));
  expect(watch.elapsedMilliseconds, lessThan(50));
  await db.close();
});
```

- [ ] **Step 2: Run it**

Run: `flutter test test/db_benchmark_test.dart -r expanded`
Expected: FAIL because `BenchmarkDatabase` does not exist.

- [ ] **Step 3: Implement the table and database**

Create a Drift table `Books` with the fields above and an index on
`title COLLATE NOCASE` and `duration_ms`. Seed with deterministic titles
`Libro 00001`…`Libro 10000`, authors cycling over 20 names, languages
`es`/`en`, durations 1–20 h. Use a transaction for seeding.

- [ ] **Step 4: Run the test**

Run: `flutter test test/db_benchmark_test.dart -r expanded`
Expected: PASS; record the query time.

- [ ] **Step 5: Add a scroll benchmark**

On `/db`, seed 10k, show a `ListView.builder` with 100-row pages, and run in
profile on Windows and Android. Record frame timings and memory in
`spike/flutter_engine/benchmarks/db.md`.

- [ ] **Step 6: Commit**

```powershell
git add spike/flutter_engine/lib/db spike/flutter_engine/test/db_benchmark_test.dart spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): benchmark drift with 10k books"
```

---

### Task 3: EPUB ingest with accents and images

**Files:**
- Create: `spike/flutter_engine/test/fixtures/legacy-cp1252.epub`
- Create: `spike/flutter_engine/lib/epub/epub_ingest.dart`
- Create: `spike/flutter_engine/test/epub_ingest_test.dart`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/epub`)

**Interfaces:**
- Consumes: `epub_plus`, `archive`, `xml`, `html`.
- Produces: `Future<IngestedBook> ingestEpub(Uint8List bytes)` where
  `IngestedBook` has `title`, `author`, `language`, `chapters`
  (`title`, `paragraphs`), `images` (`id`, `bytes`, `alt`).

- [ ] **Step 1: Create the fixture**

Use the existing repo fixture or create a small EPUB with:
title `El gato negro`, author `Edgar Allan Poe`, language `es`, one chapter
with `ñ`, `á`, `ü`, `¿`, `¡`, and one embedded PNG. Ensure the XHTML bytes are
CP1252 or Latin-1 with a wrong/absent charset declaration, so the decoder must
fall back correctly.

- [ ] **Step 2: Write the failing test**

```dart
test('decodes CP1252 accents and extracts a chapter', () async {
  final bytes = await File('test/fixtures/legacy-cp1252.epub').readAsBytes();
  final book = await ingestEpub(bytes);
  expect(book.title, 'El gato negro');
  expect(book.language, startsWith('es'));
  expect(book.chapters, isNotEmpty);
  expect(book.chapters.first.paragraphs.join(' '), contains('ñ'));
  expect(book.chapters.first.paragraphs.join(' '), contains('¿'));
  expect(book.images, isNotEmpty);
});
```

- [ ] **Step 3: Run it**

Run: `flutter test test/epub_ingest_test.dart -r expanded`
Expected: FAIL because `ingestEpub` does not exist.

- [ ] **Step 4: Implement `ingestEpub`**

Use `EpubReader.readBook(bytes)` for OPF/NCX, but read raw XHTML bytes from the
archive and decode with: BOM UTF-8/16/32 → XML/meta charset → strict UTF-8 →
Windows-1252. Parse with `package:html`, extract headings/paragraphs/images,
normalize whitespace, and return `IngestedBook`. Do not execute scripts.

- [ ] **Step 5: Run the test**

Run: `flutter test test/epub_ingest_test.dart -r expanded`
Expected: PASS for accents, chapter, image.

- [ ] **Step 6: Commit**

```powershell
git add spike/flutter_engine/test/fixtures/legacy-cp1252.epub spike/flutter_engine/lib/epub spike/flutter_engine/test/epub_ingest_test.dart spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): ingest legacy EPUB without losing accents"
```

---

### Task 4: Piper Spanish via sherpa-onnx

**Files:**
- Create: `spike/flutter_engine/lib/tts/piper_benchmark.dart`
- Create: `spike/flutter_engine/test/piper_benchmark_test.dart`
- Create: `spike/flutter_engine/scripts/download_piper_model.ps1`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/piper`)

**Interfaces:**
- Consumes: `sherpa_onnx`, `path_provider`, `crypto`.
- Produces: `Future<File> synthesizePiper(String text, {required String modelDir, required String outputPath})`
  and `Future<PiperBenchmark> runPiperBenchmark()` with `audioSeconds`,
  `wallSeconds`, `rtf`, `wavPath`.

- [ ] **Step 1: Download a Spanish Piper model**

Write `scripts/download_piper_model.ps1` that downloads a pre-converted
Spanish Piper/VITS model and `espeak-ng-data`, verifies SHA-256, and extracts
to `spike/flutter_engine/assets/models/piper-es/`. Do not commit the model.

- [ ] **Step 2: Write the failing test**

```dart
test('piper synthesizes Spanish audio', () async {
  final result = await runPiperBenchmark();
  expect(result.audioSeconds, greaterThan(0.5));
  expect(result.rtf, lessThan(4.0));
  expect(await File(result.wavPath).length(), greaterThan(1000));
});
```

Mark this test `skip` in CI unless the model is present; run it manually on
Windows and Android.

- [ ] **Step 3: Implement the benchmark**

Initialize `sherpa_onnx` offline TTS with the model/tokens/espeak data, set
`numThreads: 2`, synthesize `La casa de los Ferrer se levantaba sobre una loma
que olía a sal y a romero.`, write WAV, measure wall time and audio duration.

- [ ] **Step 4: Run on Windows and Android**

Run on Windows: `flutter test test/piper_benchmark_test.dart -r expanded`.
Run on Android: add a `/piper` button and read the result on device.
Record RTF, model load time, memory.

- [ ] **Step 5: Commit**

```powershell
git add spike/flutter_engine/lib/tts spike/flutter_engine/test/piper_benchmark_test.dart spike/flutter_engine/scripts/download_piper_model.ps1 spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): benchmark Piper Spanish with sherpa-onnx"
```

---

### Task 5: Kokoro Spanish feasibility

**Files:**
- Create: `spike/flutter_engine/lib/tts/kokoro_benchmark.dart`
- Create: `spike/flutter_engine/test/kokoro_benchmark_test.dart`
- Create: `spike/flutter_engine/scripts/download_kokoro_model.ps1`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/kokoro`)

**Interfaces:**
- Consumes: `flutter_onnxruntime`, `kokoro-v1.0.onnx`, `voices-v1.0.bin`,
  `espeak-ng-data`.
- Produces: `Future<KokoroBenchmark> runKokoroBenchmark({required String modelDir})`
  with `success`, `audioSeconds`, `rtf`, `notes`.

- [ ] **Step 1: Download the model and voices**

Use the same URLs/SHA-256 as `src/audiol/tts/kokoro_assets.py`:
`kokoro-v1.0.onnx` (325,532,387 bytes) and `voices-v1.0.bin` (28,214,398
bytes). Do not commit them.

- [ ] **Step 2: Write the failing test**

```dart
test('kokoro Spanish produces audio or records a clear failure', () async {
  final result = await runKokoroBenchmark(modelDir: 'assets/models/kokoro');
  if (!result.success) {
    expect(result.notes, isNotEmpty);
    return;
  }
  expect(result.audioSeconds, greaterThan(0.5));
  expect(result.rtf, lessThan(5.0));
});
```

- [ ] **Step 3: Implement the attempt**

Load the ONNX model with `flutter_onnxruntime`. Implement or vendor Spanish
G2P/tokenization compatible with Kokoro (espeak-ng phonemes → tokens) and
synthesize `La casa de los Ferrer se levantaba sobre una loma que olía a sal y
a romero.` for `ef_dora`/`em_alex`/`em_santa`. If the frontend is not viable,
return `success: false` with the exact blocker (missing phonemizer, token
mismatch, input shape, etc.).

- [ ] **Step 4: Run and record**

Run on Windows and Android. Save WAVs for listening; record quality notes
(intelligibility, accent, artifacts). Do not mark success from a waveform alone.

- [ ] **Step 5: Commit**

```powershell
git add spike/flutter_engine/lib/tts/kokoro_benchmark.dart spike/flutter_engine/test/kokoro_benchmark_test.dart spike/flutter_engine/scripts/download_kokoro_model.ps1 spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): evaluate Kokoro Spanish on device"
```

---

### Task 6: FFmpeg and M4B

**Files:**
- Create: `spike/flutter_engine/lib/audio/m4b_benchmark.dart`
- Create: `spike/flutter_engine/test/m4b_benchmark_test.dart`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/ffmpeg`)

**Interfaces:**
- Consumes: `ffmpeg_kit_flutter_new_audio`, a generated WAV.
- Produces: `Future<M4bResult> buildM4b({required List<File> wavs, required List<String> titles, required String outputPath})`
  with `path`, `durationSeconds`, `chapterCount`, `logs`.

- [ ] **Step 1: Generate a 3-chapter WAV fixture**

Use a small Dart/ffmpeg command to create 3 sine/silence WAVs of 2 s each.
Do not commit generated audio.

- [ ] **Step 2: Write the failing test**

```dart
test('builds a playable M4B with chapters', () async {
  final result = await buildM4b(wavs: fixtureWavs, titles: ['Uno', 'Dos', 'Tres'], outputPath: out);
  expect(result.chapterCount, 3);
  expect(result.durationSeconds, closeTo(6.0, 0.5));
  expect(await File(result.path).length(), greaterThan(1000));
});
```

- [ ] **Step 3: Implement the ffmpeg command**

Decode/concatenate WAVs, encode AAC, write `ffmetadata` with chapters and
title/author, mux to `.m4b`. Use `-nostdin -hide_banner -loglevel error`.
Capture logs and return code.

- [ ] **Step 4: Run on Windows and Android**

Run the test and verify with `ffprobe` (desktop) that codec is AAC and chapters
exist. On Android, share/save the file and play it. Record time and size.

- [ ] **Step 5: Commit**

```powershell
git add spike/flutter_engine/lib/audio spike/flutter_engine/test/m4b_benchmark_test.dart spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): validate M4B assembly with ffmpeg"
```

---

### Task 7: Paginated reader and karaoke

**Files:**
- Create: `spike/flutter_engine/lib/reader/reader_benchmark.dart`
- Create: `spike/flutter_engine/test/reader_benchmark_test.dart`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/reader`)

**Interfaces:**
- Consumes: plain text paragraphs + a word timing list.
- Produces: `ReaderPageLayout paginate(String text, Size size, TextStyle style)`
  with `pages` (list of `ReaderPage` with spans) and `ReaderPageLayout.hitTestWord(Offset)`.
  `KaraokeSpan` has `startMs`, `endMs`, `range`.

- [ ] **Step 1: Write the failing test**

```dart
test('paginates a long chapter and highlights the active word', () {
  final layout = paginate(longSpanishText, const Size(800, 600), const TextStyle(fontSize: 18));
  expect(layout.pages.length, greaterThan(1));
  final span = layout.wordAt(const Duration(seconds: 3));
  expect(span, isNotNull);
  expect(span!.range.start, greaterThanOrEqualTo(0));
});
```

- [ ] **Step 2: Implement the paginator**

Use `TextPainter` with the chapter style; split paragraphs into pages that fit
the height; keep a mapping from character ranges to page/line; map word timings
to ranges. Cache pages by text+size+style.

- [ ] **Step 3: Build the reader UI**

Show a `PageView` with one page on Android and two pages on Windows wide;
highlight the active segment and word; tap to seek (fake timer). Measure
page-turn frame time with DevTools.

- [ ] **Step 4: Run and record**

Run in profile on Windows and Android; record pagination time, page-turn jank,
and memory. Test text scale 1.0 and 2.0.

- [ ] **Step 5: Commit**

```powershell
git add spike/flutter_engine/lib/reader spike/flutter_engine/test/reader_benchmark_test.dart spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): paginate and karaoke a chapter"
```

---

### Task 8: Background audio

**Files:**
- Create: `spike/flutter_engine/lib/audio/background_audio.dart`
- Create: `spike/flutter_engine/android/app/src/main/AndroidManifest.xml` (modify)
- Modify: `spike/flutter_engine/lib/main.dart` (route `/audio`)

**Interfaces:**
- Consumes: `just_audio`, `audio_service`, `audio_session`.
- Produces: `AudioHandler` implementation with `play`, `pause`, `seek`;
  `Future<void> startBackgroundTest(File audioFile)`.

- [ ] **Step 1: Configure Android**

Add the `audio_service` service/receiver and permissions:
`FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS`.
Set the activity/service attributes required by `audio_service`.

- [ ] **Step 2: Implement the handler**

Wrap a `just_audio` player in an `AudioHandler`; expose play/pause/seek and
media item metadata. Initialize `AudioService.init` in `main()`.

- [ ] **Step 3: Run the manual test**

On Android: play a 5-minute file, lock the screen, wait 2 minutes, unlock, and
assert the position advanced by ~2 minutes and the notification controls work.
Record the result. On Windows: verify playback continues when the window is
unfocused (no background service requirement).

- [ ] **Step 4: Commit**

```powershell
git add spike/flutter_engine/lib/audio spike/flutter_engine/android/app/src/main/AndroidManifest.xml spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): validate background audio on Android"
```

---

### Task 9: Live ambience mixing

**Files:**
- Create: `spike/flutter_engine/lib/audio/ambience_benchmark.dart`
- Create: `spike/flutter_engine/test/ambience_benchmark_test.dart`
- Modify: `spike/flutter_engine/lib/main.dart` (route `/ambience`)

**Interfaces:**
- Consumes: two audio files (bed + effect), `just_audio`.
- Produces: `Future<AmbienceBenchmark> runAmbienceBenchmark()` with
  `underRuns`, `cpuPercent`, `memoryMb`, `notes`.

- [ ] **Step 1: Implement two players**

Play a looping bed at volume 0.4 and a one-shot effect at 0.7; duck the bed to
0.2 for 2 s while the effect plays; restore. Schedule 5 effects over 60 s.

- [ ] **Step 2: Run 10 minutes**

On Windows and Android, run the mix for 10 minutes with the screen on and off
(Android). Record underruns/glitches, CPU, memory, and whether volumes/ducking
behave. Use a real audio interface/headphones.

- [ ] **Step 3: Record and commit**

Write results to `spike/flutter_engine/benchmarks/ambience.md`.

```powershell
git add spike/flutter_engine/lib/audio/ambience_benchmark.dart spike/flutter_engine/test/ambience_benchmark_test.dart spike/flutter_engine/lib/main.dart
git commit -m "spike(flutter): measure live ambience mixing"
```

---

### Task 10: Build, size and startup measurements

**Files:**
- Create: `spike/flutter_engine/benchmarks/build.md`
- Create: `spike/flutter_engine/scripts/measure.ps1`

**Interfaces:**
- Consumes: all previous routes.
- Produces: a measurement table.

- [ ] **Step 1: Build release artifacts**

```powershell
flutter build windows --release --analyze-size
flutter build apk --release --target-platform android-arm64 --analyze-size
```

Expected: builds succeed; record artifact sizes.

- [ ] **Step 2: Measure startup**

Run `flutter run --profile --trace-startup` on Windows and Android; record
time to first frame and time to interactive library.

- [ ] **Step 3: Measure memory**

Use DevTools Memory on Windows and Android; record idle, reader, and
conversion peaks.

- [ ] **Step 4: Record and commit**

Write `benchmarks/build.md` with OS/device, artifact size, startup, memory,
and comparison to the budgets.

```powershell
git add spike/flutter_engine/benchmarks/build.md spike/flutter_engine/scripts/measure.ps1
git commit -m "spike(flutter): record build and startup measurements"
```

---

### Task 11: Decision report

**Files:**
- Create: `docs/refactor/spike-report.md`
- Modify: `docs/refactor/10-risks-decisions.md` (only the G1 section, if approved)

**Interfaces:**
- Consumes: all benchmark files.
- Produces: a report with a clear recommendation and evidence.

- [ ] **Step 1: Write the report**

Include:
- environment and exact versions;
- results per task with pass/fail and numbers;
- Kokoro Spanish verdict with audio samples/notes;
- EPUB/M4B/background/ambience verdicts;
- APK/installer sizes and startup/memory;
- what failed and why;
- recommendation: **Dart puro**, **Python embebido**, or **híbrido**;
- remaining risks and the next plan.

- [ ] **Step 2: Review with the user**

Do not change G1 or start production code until the user reviews the report.
Do not create tags/releases.

- [ ] **Step 3: Commit**

```powershell
git add docs/refactor/spike-report.md
git commit -m "docs(refactor): record Flutter engine spike decision"
```

---

## Self-Review

- **Spec coverage:** tasks cover the risky paths from `02-stack-comparison.md`
  (engine, TTS, FFmpeg, EPUB, reader, audio, ambience), `05-platform-matrix.md`
  (Windows/Android/background), `07-performance.md` (metrics), and `09-plan.md`
  F0.
- **Placeholders:** no “TBD”; failures are allowed but must be recorded, not
  fabricated.
- **Type consistency:** `IngestedBook`, `PiperBenchmark`, `KokoroBenchmark`,
  `M4bResult`, `ReaderPageLayout`, `AmbienceBenchmark` are defined once and used
  consistently.
- **Review focus:** five failure modes are pinned to Tasks 3, 5, 8, 6, and 2.
- **Scope:** this plan is only F0; the production phases get separate plans
  after G1 is approved.
