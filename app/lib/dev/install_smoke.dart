import 'dart:convert';
import 'dart:io';

import '../data/tts/piper_catalog.dart';
import '../data/tts/piper_downloader.dart';

/// Installs a Piper .tar.bz2 without network access.
///
/// Usage:
///   `vibebook_app.exe --install-smoke <archive.tar.bz2> <models-root> <out.json>`
Future<void> runInstallSmoke(List<String> args) async {
  final flag = args.indexOf('--install-smoke');
  final archive = flag + 1 < args.length ? args[flag + 1] : '';
  final root = flag + 2 < args.length ? args[flag + 2] : '';
  final outputJson = flag + 3 < args.length ? args[flag + 3] : '';
  final result = <String, dynamic>{'ok': false, 'archive': archive, 'root': root};
  try {
    if (archive.isEmpty || root.isEmpty || outputJson.isEmpty) {
      throw ArgumentError('Uso: --install-smoke <archive.tar.bz2> <models-root> <out.json>');
    }
    final directory = Directory(root);
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
    await directory.create(recursive: true);
    final downloader = const PiperDownloader();
    final model = archive.startsWith('catalog:')
        ? await downloader.installFromCatalog(
            piperCatalog.firstWhere(
              (entry) => entry.id == archive.substring('catalog:'.length),
            ),
            rootPath: root,
          )
        : await downloader.installFromFile(File(archive), rootPath: root);
    final modelFile = File(model.modelPath);
    final tokens = File(model.tokensPath);
    if (!await modelFile.exists() || !await tokens.exists()) {
      throw StateError('El modelo instalado no está completo.');
    }
    result
      ..['ok'] = true
      ..['id'] = model.id
      ..['name'] = model.name
      ..['language'] = model.language
      ..['sample_rate'] = model.sampleRate
      ..['directory'] = model.directory
      ..['model_bytes'] = await modelFile.length();
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
