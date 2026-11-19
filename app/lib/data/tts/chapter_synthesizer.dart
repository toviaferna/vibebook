import 'dart:typed_data';

import 'package:piper_phonemize/piper_phonemize.dart' show extractEspeakNgData;

import '../../domain/models.dart';
import 'piper_models.dart';
import 'tts_chapter_worker.dart' show renderChapterInBackground;

/// Extracts the bundled espeak-ng data the Piper worker needs.
Future<String> ensurePiperEspeakData() => extractEspeakNgData();

/// The cancelled flag crossed the synthesizer mid-chapter.
class SynthesisCancelled implements Exception {
  const SynthesisCancelled();
}

/// Audio for one chapter plus everything the karaoke timing needs.
class ChapterSynthesis {
  const ChapterSynthesis({
    required this.samples,
    required this.sampleRate,
    required this.spans,
    required this.wordTimings,
  });

  /// Mono PCM float samples of the whole chapter, pauses included.
  final Float32List samples;

  final int sampleRate;

  /// Per-segment spans: `{'id', 'start_ms', 'end_ms'}`.
  final List<Map<String, dynamic>> spans;

  /// Real word timings when the engine reports them:
  /// `{'id', 'words': [{'text', 'start_ms', 'end_ms'}]}`. Empty when the
  /// timings have to be estimated from the spans.
  final List<Map<String, dynamic>> wordTimings;
}

/// One TTS engine's way of turning a chapter into audio.
abstract class ChapterSynthesizer {
  /// Manifest value: `piper`, `edge`, …
  String get engineId;

  /// Manifest value: the voice the engine should use.
  String get voiceId;

  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  });
}

/// [ChapterSynthesizer] over the local Piper worker.
class PiperSynthesizer implements ChapterSynthesizer {
  PiperSynthesizer({required this.model, required this.espeakDataPath});

  final PiperModel model;
  final String espeakDataPath;

  @override
  String get engineId => 'piper';

  @override
  String get voiceId => model.id;

  @override
  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  }) async {
    final payload = <String, dynamic>{
      'model': {
        'model': model.modelPath,
        'tokens': model.tokensPath,
        'voice': model.espeakVoice,
        'noise_scale': model.noiseScale,
        'noise_w': model.noiseScaleW,
        'length_scale': model.lengthScale,
      },
      'espeak_data_path': espeakDataPath,
      'speed': speed,
      'segments': [
        for (final segment in chapter.segments)
          {
            'id': segment.id,
            'text': segment.text,
            'pause_after_ms': segment.boundary == 'paragraph' ? 190 : 90,
            'speaker_id': 0,
          },
      ],
    };
    final result = await renderChapterInBackground(payload);
    final samples = result['samples'] as Float32List;
    final sampleRate = (result['sample_rate'] as num?)?.toInt() ?? 22050;
    return ChapterSynthesis(
      samples: samples,
      sampleRate: sampleRate,
      spans: (result['spans'] as List<dynamic>).cast<Map<String, dynamic>>(),
      wordTimings: const [],
    );
  }
}
