import 'dart:convert';
import 'dart:io';

import '../data/ambience/ambience_generator.dart';
import '../domain/ambience.dart';

/// Generates every procedural ambience bed and reports its size.
///
/// Usage:
///   `vibebook_app.exe --ambience-smoke <out.json>`
Future<void> runAmbienceSmoke(List<String> args) async {
  final flag = args.indexOf('--ambience-smoke');
  final outputJson = flag + 1 < args.length ? args[flag + 1] : '';
  final result = <String, dynamic>{'ok': false, 'presets': <String, dynamic>{}};
  try {
    if (outputJson.isEmpty) {
      throw ArgumentError('Uso: --ambience-smoke <out.json>');
    }
    for (final preset in AmbiencePreset.values) {
      final file = await const AmbienceGenerator().ensurePreset(preset);
      final length = await file.length();
      if (length <= 44) {
        throw StateError('La cama ${preset.id} quedó vacía.');
      }
      (result['presets'] as Map<String, dynamic>)[preset.id] = {
        'path': file.path,
        'bytes': length,
      };
    }
    result['ok'] = true;
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
