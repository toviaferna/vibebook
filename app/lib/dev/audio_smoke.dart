import 'dart:convert';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';

/// Headless playback check for the audio plugin.
///
/// Usage:
///   `vibebook_app.exe --audio-smoke <audio-file> <out.json>`
Future<void> runAudioSmoke(List<String> args) async {
  final flag = args.indexOf('--audio-smoke');
  final path = flag + 1 < args.length ? args[flag + 1] : '';
  final outputJson = flag + 2 < args.length ? args[flag + 2] : '';
  final result = <String, dynamic>{'ok': false, 'path': path};
  final player = AudioPlayer();
  try {
    if (path.isEmpty || outputJson.isEmpty) {
      throw ArgumentError('Uso: --audio-smoke <audio-file> <out.json>');
    }
    if (!await File(path).exists()) {
      throw StateError('No existe el archivo de audio.');
    }
    await player.setSource(DeviceFileSource(path));
    await player.resume();
    await Future<void>.delayed(const Duration(seconds: 2));
    final position = await player.getCurrentPosition();
    final state = player.state;
    result
      ..['ok'] = (position?.inMilliseconds ?? 0) > 0
      ..['position_ms'] = position?.inMilliseconds ?? 0
      ..['state'] = state.name;
    await player.stop();
  } catch (error, stackTrace) {
    result
      ..['ok'] = false
      ..['error'] = '$error'
      ..['stack'] = '$stackTrace';
  } finally {
    await player.dispose();
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
