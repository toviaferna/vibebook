import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../data/ambience/ambience_generator.dart';
import '../data/m4b_exporter.dart';
import '../domain/ambience.dart';
import '../domain/models.dart';

/// Headless check for the ambient M4B export.
///
/// Usage:
///   `vibebook_app.exe --ambient-m4b-smoke <book-dir> <preset> <out.json> [out.m4b]`
Future<void> runAmbientM4bSmoke(List<String> args) async {
  final flag = args.indexOf('--ambient-m4b-smoke');
  final bookDir = flag + 1 < args.length ? args[flag + 1] : '';
  final presetId = flag + 2 < args.length ? args[flag + 2] : 'rain';
  final outputJson = flag + 3 < args.length ? args[flag + 3] : '';
  final outputM4b = flag + 4 < args.length ? args[flag + 4] : '';
  final result = <String, dynamic>{
    'ok': false,
    'book_dir': bookDir,
    'preset': presetId,
  };
  try {
    if (bookDir.isEmpty || outputJson.isEmpty) {
      throw ArgumentError(
        'Uso: --ambient-m4b-smoke <book-dir> <preset> <out.json> [out.m4b]',
      );
    }
    final manifestFile = File(p.join(bookDir, 'manifest.json'));
    if (!await manifestFile.exists()) {
      throw StateError('No existe manifest.json en $bookDir');
    }
    final book = Book.fromJsonString(
      await manifestFile.readAsString(),
      id: p.basename(bookDir),
      manifestPath: manifestFile.path,
      directoryPath: bookDir,
    );
    final preset = AmbiencePresetDetails.byId(presetId);
    final bed = await const AmbienceGenerator().ensurePreset(preset);
    final stopwatch = Stopwatch()..start();
    final export = await const M4bExporter().exportWithAmbience(
      book,
      bedPath: bed.path,
      outputPath: outputM4b.isEmpty ? null : outputM4b,
      onProgress: (chapter, total) {},
    );
    stopwatch.stop();
    final file = File(export.path);
    if (!await file.exists()) {
      throw StateError('El M4B ambientado no se creó.');
    }
    result
      ..['ok'] = true
      ..['path'] = export.path
      ..['bytes'] = await file.length()
      ..['bed'] = bed.path
      ..['elapsed_ms'] = stopwatch.elapsedMilliseconds;
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
