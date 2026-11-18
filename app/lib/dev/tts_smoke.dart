import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path/path.dart' as p;

import '../data/tts/piper_models.dart';
import '../data/tts/tts_chapter_worker.dart';
import '../data/tts/tts_conversion.dart' show ensurePiperEspeakData;
import '../data/tts/wav_writer.dart';

/// Headless end-to-end check for the local Piper pipeline.
///
/// Usage:
///   `vibebook_app.exe --tts-smoke <model-dir> <out.wav> <out.json>`
///
/// It uses the same background worker as the UI.
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
  try {
    if (modelDir.isEmpty || outputWav.isEmpty || outputJson.isEmpty) {
      throw ArgumentError('Uso: --tts-smoke <model-dir> <out.wav> <out.json>');
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
    final espeak = await ensurePiperEspeakData();
    const text =
        'La casa de los Ferrer se levantaba sobre una loma que olía a sal. '
        'Desde la ventana se veía el puerto y una línea de barcos que entraban y salían.';
    final stopwatch = Stopwatch()..start();
    final rendered = await renderChapterInBackground({
      'model': {
        'model': model.modelPath,
        'tokens': model.tokensPath,
        'voice': model.espeakVoice,
        'noise_scale': model.noiseScale,
        'noise_w': model.noiseScaleW,
        'length_scale': model.lengthScale,
      },
      'espeak_data_path': espeak,
      'speed': 0.9,
      'segments': [
        {'id': 'smoke', 'text': text, 'pause_after_ms': 0},
      ],
    });
    stopwatch.stop();
    final samples = rendered['samples'] as Float32List;
    final sampleRate =
        (rendered['sample_rate'] as num?)?.toInt() ?? model.sampleRate;
    if (samples.isEmpty) {
      throw StateError('Sherpa no generó audio.');
    }
    final wav = const WavWriter().encode(samples, sampleRate);
    final file = File(outputWav);
    await file.parent.create(recursive: true);
    await file.writeAsBytes(wav, flush: true);
    result
      ..['ok'] = true
      ..['sample_rate'] = sampleRate
      ..['samples'] = samples.length
      ..['duration_ms'] = (samples.length * 1000 / sampleRate).round()
      ..['elapsed_ms'] = stopwatch.elapsedMilliseconds
      ..['wav_bytes'] = wav.length;
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
