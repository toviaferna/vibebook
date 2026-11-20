import 'dart:typed_data';

import '../../../domain/models.dart';
import '../chapter_synthesizer.dart';
import 'cloud_tts.dart';

/// Synthesizes a chapter with a cloud provider, one segment at a time.
///
/// Providers return compressed audio; it is decoded to mono 24 kHz PCM so the
/// rest of the pipeline (WAV, MP3, M4B, timings) stays engine-independent.
class CloudChapterSynthesizer implements ChapterSynthesizer {
  CloudChapterSynthesizer({
    required this.client,
    required this.voice,
    required this.engine,
    this.style = 'neutral',
    this.decoder = const FfmpegCloudAudioDecoder(),
    this.sampleRate = 24000,
    this.paragraphPauseMs = 190,
    this.sentencePauseMs = 90,
  });

  final CloudTtsClient client;
  final String voice;
  final String engine;
  final String style;
  final CloudAudioDecoder decoder;
  final int sampleRate;
  final int paragraphPauseMs;
  final int sentencePauseMs;

  @override
  String get engineId => engine;

  @override
  String get voiceId => voice;

  @override
  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  }) async {
    final chunks = <Float32List>[];
    final spans = <Map<String, dynamic>>[];
    final nativeWords = <Map<String, dynamic>>[];
    var totalSamples = 0;

    for (final segment in chapter.segments) {
      if (isCancelled()) {
        throw const SynthesisCancelled();
      }
      final CloudAudio audio;
      try {
        audio = await client.synthesize(
          text: segment.text,
          voice: voice,
          style: style,
        );
      } on CloudTtsException catch (error) {
        throw CloudTtsException(
          '${error.message} (capítulo ${chapter.index}, párrafo '
          '${segment.paragraphIndex})',
          statusCode: error.statusCode,
        );
      }
      if (isCancelled()) {
        throw const SynthesisCancelled();
      }
      final pcm = await decoder.decode(audio, sampleRate: sampleRate);
      if (pcm.isEmpty) {
        throw CloudTtsException(
          'El motor $engine devolvió audio vacío en el párrafo '
          '${segment.paragraphIndex}.',
        );
      }
      final startSample = totalSamples;
      chunks.add(pcm);
      totalSamples += pcm.length;
      final startMs = (startSample * 1000 / sampleRate).round();
      final endMs = (totalSamples * 1000 / sampleRate).round();
      spans.add({'id': segment.id, 'start_ms': startMs, 'end_ms': endMs});
      if (audio.words.isNotEmpty) {
        nativeWords.add({
          'id': segment.id,
          'words': [
            for (final word in audio.words)
              {
                'text': word.text,
                'start_ms': word.startMs + startMs,
                'end_ms': word.endMs + startMs,
              },
          ],
        });
      }
      final pauseMs = segment.boundary == 'paragraph'
          ? paragraphPauseMs
          : sentencePauseMs;
      final pauseSamples = (sampleRate * pauseMs / 1000).round();
      if (pauseSamples > 0) {
        chunks.add(Float32List(pauseSamples));
        totalSamples += pauseSamples;
      }
    }

    var samples = Float32List(totalSamples);
    var offset = 0;
    for (final chunk in chunks) {
      samples.setRange(offset, offset + chunk.length, chunk);
      offset += chunk.length;
    }

    if ((speed - 1).abs() > 0.001 && samples.isNotEmpty) {
      samples = await decoder.applySpeed(
        samples,
        sampleRate: sampleRate,
        speed: speed,
      );
      final inverse = 1 / speed;
      for (final span in spans) {
        span['start_ms'] = ((span['start_ms'] as int) * inverse).round();
        span['end_ms'] = ((span['end_ms'] as int) * inverse).round();
      }
      for (final segment in nativeWords) {
        for (final word in segment['words'] as List<Map<String, dynamic>>) {
          word['start_ms'] = ((word['start_ms'] as int) * inverse).round();
          word['end_ms'] = ((word['end_ms'] as int) * inverse).round();
        }
      }
    }

    return ChapterSynthesis(
      samples: samples,
      sampleRate: sampleRate,
      spans: spans,
      wordTimings: nativeWords,
    );
  }
}
