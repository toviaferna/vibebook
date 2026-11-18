import 'dart:convert';
import 'dart:io';

import 'package:piper_phonemize/piper_phonemize.dart';

/// Headless diagnostic for the piper-phonemize native library.
///
/// Usage:
///   `vibebook_app.exe --piper-smoke <espeak-data-dir> <out.json>`
Future<void> runPiperSmoke(List<String> args) async {
  final flag = args.indexOf('--piper-smoke');
  final dataDir = flag + 1 < args.length ? args[flag + 1] : '';
  final outputJson = flag + 2 < args.length ? args[flag + 2] : '';
  final result = <String, dynamic>{'data_dir': dataDir};
  try {
    initBindings();
    result['version'] = PiperPhonemize.getVersion();
    if (dataDir.isNotEmpty) {
      result['init_data_dir'] = PiperPhonemize.initialize(dataDir);
    }
    result['init_empty'] = PiperPhonemize.initialize('');
    final phonemes = PiperPhonemize.phonemize('La casa olía a sal.', voice: 'es');
    result['sentences'] = phonemes.length;
    result['codepoints'] = phonemes.isNotEmpty ? phonemes.first.take(12).toList() : [];
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
  exit(0);
}
