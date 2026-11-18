import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../data/tts/piper_models.dart';
import '../data/tts/piper_tts_service.dart';
import '../data/tts/wav_writer.dart';

/// Headless end-to-end check for the local Piper pipeline.
///
/// Usage:
///   `vibebook_app.exe --tts-smoke <model-dir> <out.wav> <out.json>`
///
/// It is intentionally kept in the release binary so the same engine and
/// plugin DLLs used by the UI can be verified without a device.
Future<void> runTtsSmoke(List<String> args) async {
  final flag = args.indexOf('--tts-smoke');
  final modelDir = flag + 1 < args.length ? args[flag + 1] : '';
  final outputWav = flag + 2 < args.length ? args[flag + 2] : '';
  final outputJson = flag + 3 < args.length ? args[flag + 3] : '';
  final result = <String, dynamic>{
    'ok': false,
    'model_dir': modelDir,
    'wav': outputWav,
  };
  final service = PiperTtsService();
  try {
    if (modelDir.isEmpty || outputWav.isEmpty || outputJson.isEmpty) {
      throw ArgumentError(
        'Uso: --tts-smoke <model-dir> <out.wav> <out.json>',
      );
    }
    final store = PiperModelStore(rootPath: p.dirname(modelDir));
    final models = await store.scan();
    final model = models
        .where((item) => p.equals(item.directory, p.absolute(modelDir)))
        .firstOrNull;
    if (model == null) {
      throw StateError('No se encontró un modelo Piper en $modelDir');
    }
    result['model_id'] = model.id;
    result['espeak_voice'] = model.espeakVoice;
    result['model_sample_rate'] = model.sampleRate;
    await service.loadModel(model);
    const text = 'La casa de los Ferrer se levantaba sobre una loma que olía a sal. '
        'Desde la ventana se veía el puerto y una línea de barcos que entraban y salían.';
    final stopwatch = Stopwatch()..start();
    final speech = await service.synthesize(text, speed: 0.9);
    stopwatch.stop();
    if (speech.isEmpty) {
      throw StateError('Sherpa no generó audio.');
    }
    final wav = const WavWriter().encode(speech.samples, speech.sampleRate);
    final file = File(outputWav);
    await file.parent.create(recursive: true);
    await file.writeAsBytes(wav, flush: true);
    result
      ..['ok'] = true
      ..['sample_rate'] = speech.sampleRate
      ..['samples'] = speech.samples.length
      ..['duration_ms'] = speech.duration.inMilliseconds
      ..['elapsed_ms'] = stopwatch.elapsedMilliseconds
      ..['wav_bytes'] = wav.length;
  } catch (error, stackTrace) {
    result
      ..['ok'] = false
      ..['error'] = '$error'
      ..['stack'] = '$stackTrace';
  } finally {
    service.dispose();
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
