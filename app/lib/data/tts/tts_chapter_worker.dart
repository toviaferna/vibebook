import 'dart:isolate';
import 'dart:typed_data';

import 'package:piper_phonemize/piper_phonemize.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

import '../../core/platform_paths.dart';

/// Synthesizes a whole chapter in a background isolate.
///
/// The isolate loads the model once, so the UI thread stays responsive even
/// for long chapters. The payload and result only contain primitive values,
/// lists and maps, which keeps them safe to send across isolates.
Future<Map<String, dynamic>> renderChapterInBackground(
  Map<String, dynamic> payload,
) {
  return Isolate.run(() => _renderChapter(payload));
}

Map<String, dynamic> _renderChapter(Map<String, dynamic> payload) {
  final model = payload['model'] as Map<String, dynamic>;
  final espeakDataPath = payload['espeak_data_path'] as String;
  final speed = (payload['speed'] as num?)?.toDouble() ?? 1.0;
  final rawSegments = payload['segments'] as List<dynamic>;

  sherpa.initBindings();
  initBindings();
  final initialized = PiperPhonemize.initialize(nativePath(espeakDataPath));
  if (initialized < 0) {
    throw StateError('espeak-ng no pudo inicializarse en el worker.');
  }

  final config = sherpa.OfflineTtsConfig(
    model: sherpa.OfflineTtsModelConfig(
      vits: sherpa.OfflineTtsVitsModelConfig(
        model: nativePath(model['model'] as String),
        tokens: nativePath(model['tokens'] as String),
        noiseScale: (model['noise_scale'] as num?)?.toDouble() ?? 0.667,
        noiseScaleW: (model['noise_w'] as num?)?.toDouble() ?? 0.8,
        lengthScale: (model['length_scale'] as num?)?.toDouble() ?? 1.0,
      ),
      numThreads: 2,
      debug: false,
      provider: 'cpu',
    ),
    maxNumSentences: 1,
  );

  sherpa.OfflineTts? tts;
  try {
    tts = sherpa.OfflineTts(config);
    var sampleRate = tts.sampleRate;
    final parts = <Float32List>[];
    final spans = <Map<String, dynamic>>[];
    var cursor = 0;
    for (var rawIndex = 0; rawIndex < rawSegments.length; rawIndex++) {
      final segment = rawSegments[rawIndex] as Map<String, dynamic>;
      final id = segment['id'] as String? ?? '';
      final text = segment['text'] as String? ?? '';
      if (text.trim().isEmpty) {
        continue;
      }
      final phonemes = PiperPhonemize.phonemize(
        text,
        voice: model['voice'] as String? ?? 'es',
      ).where((sentence) => sentence.isNotEmpty).toList(growable: false);
      if (phonemes.isEmpty) {
        continue;
      }
      final chunks = <Float32List>[];
      for (final sentence in phonemes) {
        final audio = tts.generateWithConfig(
          text: '',
          config: sherpa.OfflineTtsGenerationConfig(
            phonemeCodepoints: [sentence],
            speed: speed,
            sid: (segment['speaker_id'] as num?)?.toInt() ?? 0,
          ),
        );
        if (audio.samples.isNotEmpty) {
          sampleRate = audio.sampleRate;
          chunks.add(audio.samples);
        }
      }
      final length = chunks.fold<int>(0, (sum, chunk) => sum + chunk.length);
      if (length == 0) {
        continue;
      }
      final startMs = (cursor * 1000 / sampleRate).round();
      parts.addAll(chunks);
      cursor += length;
      final endMs = (cursor * 1000 / sampleRate).round();
      spans.add({'id': id, 'start_ms': startMs, 'end_ms': endMs});
      if (rawIndex < rawSegments.length - 1) {
        final pauseMs = (segment['pause_after_ms'] as num?)?.toInt() ?? 90;
        final pauseFrames = (sampleRate * pauseMs / 1000).round();
        if (pauseFrames > 0) {
          parts.add(Float32List(pauseFrames));
          cursor += pauseFrames;
        }
      }
    }
    final total = parts.fold<int>(0, (sum, part) => sum + part.length);
    final merged = Float32List(total);
    var offset = 0;
    for (final part in parts) {
      merged.setAll(offset, part);
      offset += part.length;
    }
    return {'samples': merged, 'sample_rate': sampleRate, 'spans': spans};
  } finally {
    tts?.free();
  }
}
