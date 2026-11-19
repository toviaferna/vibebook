import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../data/epub_ingestor.dart';
import '../data/library_repository.dart';
import '../data/tts/edge/edge_client.dart';
import '../data/tts/edge/edge_synthesizer.dart';
import '../data/tts/tts_conversion.dart';
import '../domain/timing.dart';

/// Headless end-to-end check of the Edge pipeline: import an EPUB, synthesize
/// real audio per paragraph, write native-word timings and update the
/// manifest. Needs internet, so it stays out of CI.
///
/// Usage:
///   `vibebook_app.exe --edge-convert-smoke <book.epub> <library-dir> <voice> <out.json> [chapters]`
Future<void> runEdgeConvertSmoke(List<String> args) async {
  final flag = args.indexOf('--edge-convert-smoke');
  final epub = flag + 1 < args.length ? args[flag + 1] : '';
  final libraryPath = flag + 2 < args.length ? args[flag + 2] : '';
  final voice = flag + 3 < args.length ? args[flag + 3] : 'es-ES-ElviraNeural';
  final outputJson = flag + 4 < args.length ? args[flag + 4] : '';
  final maxChapters = flag + 5 < args.length ? int.tryParse(args[flag + 5]) : 1;
  final result = <String, dynamic>{
    'ok': false,
    'voice': voice,
    'epub': epub,
    'library': libraryPath,
  };
  try {
    if (epub.isEmpty || libraryPath.isEmpty || outputJson.isEmpty) {
      throw ArgumentError(
        'Uso: --edge-convert-smoke <book.epub> <library-dir> <voice> '
        '<out.json> [chapters]',
      );
    }
    if (!await File(epub).exists()) {
      throw StateError('No existe el EPUB: $epub');
    }
    final repository = LibraryRepository(
      ingestor: const EpubIngestor(),
      libraryPath: libraryPath,
    );
    final imported = await repository.importEpub(epub);
    result['book'] = imported.title;
    result['chapters'] = imported.chapterCount;
    final stopwatch = Stopwatch()..start();
    final converted = await const TtsConversionService().convert(
      imported,
      synthesizer: EdgeSynthesizer(client: EdgeTtsClient(), voiceId: voice),
      maxChapters: maxChapters ?? 1,
      compressAudio: true,
    );
    stopwatch.stop();
    final first = converted.chapters.first;
    final audioFile = first.audio == null
        ? null
        : File(p.join(libraryPath, imported.id, first.audio!));
    final timingFile = first.timing == null
        ? null
        : File(p.join(libraryPath, imported.id, first.timing!));
    if (audioFile == null || !await audioFile.exists()) {
      throw StateError('El audio del primer capítulo no existe.');
    }
    if (timingFile == null || !await timingFile.exists()) {
      throw StateError('El timing del primer capítulo no existe.');
    }
    final timing = ChapterTiming.fromJsonString(
      await timingFile.readAsString(),
    );
    if (timing.segments.isEmpty) {
      throw StateError('El timing no tiene segmentos.');
    }
    result
      ..['ok'] = true
      ..['engine'] = converted.engine
      ..['duration_ms'] = converted.durationMs
      ..['elapsed_ms'] = stopwatch.elapsedMilliseconds
      ..['audio'] = first.audio
      ..['audio_bytes'] = await audioFile.length()
      ..['timing_segments'] = timing.segments.length
      ..['timing_precision'] = timing.precision
      ..['first_segment_words'] = timing.segments.first.words.length
      ..['sample_rate'] = EdgeSynthesizer.sampleRate
      ..['status'] = converted.status;
  } catch (error, stackTrace) {
    result
      ..['error'] = '$error'
      ..['stack'] = '$stackTrace';
  } finally {
    if (outputJson.isNotEmpty) {
      final file = File(outputJson);
      await file.parent.create(recursive: true);
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(result),
        flush: true,
      );
    }
  }
  exit(result['ok'] == true ? 0 : 1);
}
