import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../data/m4b_exporter.dart';
import '../domain/models.dart';

/// Headless check for the M4B exporter.
///
/// Usage:
///   `vibebook_app.exe --m4b-smoke <book-dir> <out.json> [out.m4b]`
Future<void> runM4bSmoke(List<String> args) async {
  final flag = args.indexOf('--m4b-smoke');
  final bookDir = flag + 1 < args.length ? args[flag + 1] : '';
  final outputJson = flag + 2 < args.length ? args[flag + 2] : '';
  final outputM4b = flag + 3 < args.length ? args[flag + 3] : '';
  final result = <String, dynamic>{'book_dir': bookDir, 'ok': false};
  try {
    if (bookDir.isEmpty || outputJson.isEmpty) {
      throw ArgumentError('Uso: --m4b-smoke <book-dir> <out.json> [out.m4b]');
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
    final stopwatch = Stopwatch()..start();
    final export = await const M4bExporter().export(
      book,
      outputPath: outputM4b.isEmpty ? null : outputM4b,
    );
    stopwatch.stop();
    final file = File(export.path);
    if (!await file.exists()) {
      throw StateError('El M4B no se creó.');
    }
    result
      ..['ok'] = true
      ..['path'] = export.path
      ..['bytes'] = await file.length()
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
