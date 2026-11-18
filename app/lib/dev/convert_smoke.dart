import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../data/epub_ingestor.dart';
import '../data/library_repository.dart';
import '../data/tts/piper_models.dart';
import '../data/tts/tts_conversion.dart';
import '../domain/timing.dart';

/// End-to-end conversion check: import an EPUB, synthesize real audio for the
/// first chapters, write timings and update the manifest.
///
/// Usage:
///   `vibebook_app.exe --convert-smoke <model-dir> <epub> <library-dir> <out.json> [chapters]`
Future<void> runConvertSmoke(List<String> args) async {
  final flag = args.indexOf('--convert-smoke');
  final modelDir = flag + 1 < args.length ? args[flag + 1] : '';
  final epub = flag + 2 < args.length ? args[flag + 2] : '';
  final libraryDir = flag + 3 < args.length ? args[flag + 3] : '';
  final outputJson = flag + 4 < args.length ? args[flag + 4] : '';
  final maxChapters = flag + 5 < args.length ? int.tryParse(args[flag + 5]) : null;
  final result = <String, dynamic>{
    'ok': false,
    'model_dir': modelDir,
    'epub': epub,
    'library': libraryDir,
  };
  try {
    if (modelDir.isEmpty || epub.isEmpty || libraryDir.isEmpty || outputJson.isEmpty) {
      throw ArgumentError(
        'Uso: --convert-smoke <model-dir> <epub> <library-dir> <out.json> [chapters]',
      );
    }
    final library = Directory(libraryDir);
    if (await library.exists()) {
      await library.delete(recursive: true);
    }
    await library.create(recursive: true);
    final store = PiperModelStore(rootPath: p.dirname(modelDir));
    final models = await store.scan();
    final model = models
        .where((item) => p.equals(item.directory, p.absolute(modelDir)))
        .firstOrNull;
    if (model == null) {
      throw StateError('No se encontró un modelo Piper en $modelDir');
    }
    result['model_id'] = model.id;
    final repository = LibraryRepository(
      ingestor: const EpubIngestor(),
      libraryPath: library.path,
    );
    final imported = await repository.importEpub(epub);
    result['book'] = imported.title;
    result['chapters'] = imported.chapterCount;
    final stopwatch = Stopwatch()..start();
    final espeak = await ensurePiperEspeakData();
    final converted = await const TtsConversionService().convert(
      imported,
      model: model,
      espeakDataPath: espeak,
      maxChapters: maxChapters ?? 1,
      compressAudio: true,
    );
    stopwatch.stop();
    final first = converted.chapters.first;
    final audioFile = first.audio == null ? null : File(p.join(library.path, imported.id, first.audio!));
    final timingFile = first.timing == null ? null : File(p.join(library.path, imported.id, first.timing!));
    if (audioFile == null || !await audioFile.exists()) {
      throw StateError('El audio del primer capítulo no existe.');
    }
    if (timingFile == null || !await timingFile.exists()) {
      throw StateError('El timing del primer capítulo no existe.');
    }
    final timing = ChapterTiming.fromJsonString(await timingFile.readAsString());
    if (timing.segments.isEmpty) {
      throw StateError('El timing no tiene segmentos.');
    }
    result
      ..['ok'] = true
      ..['engine'] = converted.engine
      ..['voice'] = converted.voice
      ..['duration_ms'] = converted.durationMs
      ..['elapsed_ms'] = stopwatch.elapsedMilliseconds
      ..['audio'] = first.audio
      ..['audio_bytes'] = await audioFile.length()
      ..['timing'] = first.timing
      ..['timing_segments'] = timing.segments.length
      ..['timing_precision'] = timing.precision
      ..['first_segment_words'] = timing.segments.first.words.length
      ..['status'] = converted.status;
  } catch (error, stackTrace) {
    result
      ..['ok'] = false
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

extension _FirstOrNull<T> on Iterable<T> {
  T? get firstOrNull {
    final iterator = this.iterator;
    return iterator.moveNext() ? iterator.current : null;
  }
}
