import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/chapter_synthesizer.dart';
import 'package:vibebook_app/data/tts/cloud/cloud_synthesizer.dart';
import 'package:vibebook_app/data/tts/cloud/cloud_tts.dart';
import 'package:vibebook_app/domain/models.dart';

class _FakeClient implements CloudTtsClient {
  _FakeClient({this.words = const []});

  final List<CloudWordTiming> words;
  final calls = <String>[];

  @override
  String get providerId => 'fake-cloud';

  @override
  Future<CloudAudio> synthesize({
    required String text,
    required String voice,
    String style = 'neutral',
  }) async {
    calls.add(text);
    return CloudAudio(
      bytes: Uint8List.fromList([1, 2, 3]),
      extension: 'wav',
      words: words,
    );
  }
}

class _FakeDecoder implements CloudAudioDecoder {
  _FakeDecoder();

  static const samplesPerCall = 24000;
  static const speedDivisor = 2;
  int speedCalls = 0;

  @override
  Future<Float32List> decode(CloudAudio audio, {int sampleRate = 24000}) async {
    return Float32List(samplesPerCall)..fillRange(0, samplesPerCall, 0.25);
  }

  @override
  Future<Float32List> applySpeed(
    Float32List samples, {
    required int sampleRate,
    required double speed,
  }) async {
    speedCalls += 1;
    final length = (samples.length / speedDivisor).round();
    return Float32List(length)..fillRange(0, length, 0.25);
  }
}

Chapter _chapter() {
  return const Chapter(
    index: 1,
    title: 'Uno',
    segments: [
      Segment(
        id: 'c001p0001s00',
        chapterIndex: 1,
        paragraphIndex: 1,
        text: 'Primer pÃ¡rrafo.',
        boundary: 'paragraph',
      ),
      Segment(
        id: 'c001p0002s00',
        chapterIndex: 1,
        paragraphIndex: 2,
        text: 'Segundo pÃ¡rrafo.',
        boundary: 'paragraph',
      ),
    ],
  );
}

void main() {
  test(
    'concatena segmentos, agrega pausas y conserva los timings nativos',
    () async {
      final client = _FakeClient(
        words: const [
          CloudWordTiming(text: 'Primer', startMs: 10, endMs: 200),
          CloudWordTiming(text: 'pÃ¡rrafo.', startMs: 210, endMs: 500),
        ],
      );
      final synthesizer = CloudChapterSynthesizer(
        client: client,
        voice: 'Kore',
        engine: 'gemini',
        decoder: _FakeDecoder(),
      );
      final result = await synthesizer.synthesize(
        _chapter(),
        speed: 1,
        isCancelled: () => false,
      );
      expect(client.calls, ['Primer pÃ¡rrafo.', 'Segundo pÃ¡rrafo.']);
      expect(result.sampleRate, 24000);
      expect(result.spans, hasLength(2));
      expect(result.spans.first['id'], 'c001p0001s00');
      expect(result.spans.first['start_ms'], 0);
      expect(result.spans.first['end_ms'], 1000);
      expect(result.spans[1]['start_ms'], 1190); // 1000 ms + 190 ms pause
      expect(result.wordTimings.first['words'], hasLength(2));
      expect(result.wordTimings.first['words'][0]['start_ms'], 10);
    },
  );

  test('cancela entre segmentos', () async {
    final synthesizer = CloudChapterSynthesizer(
      client: _FakeClient(),
      voice: 'Kore',
      engine: 'gemini',
      decoder: _FakeDecoder(),
    );
    var calls = 0;
    await expectLater(
      synthesizer.synthesize(
        _chapter(),
        speed: 1,
        isCancelled: () => ++calls > 1,
      ),
      throwsA(isA<SynthesisCancelled>()),
    );
  });

  test('aplica la velocidad y escala spans y palabras', () async {
    final decoder = _FakeDecoder();
    final synthesizer = CloudChapterSynthesizer(
      client: _FakeClient(
        words: const [CloudWordTiming(text: 'Hola', startMs: 100, endMs: 900)],
      ),
      voice: 'Kore',
      engine: 'gemini',
      decoder: decoder,
    );
    final result = await synthesizer.synthesize(
      _chapter(),
      speed: 1.1,
      isCancelled: () => false,
    );
    expect(decoder.speedCalls, 1);
    expect(result.spans.first['start_ms'], 0);
    expect(result.spans.first['end_ms'], 909); // 1000 / 1.1
    expect(result.wordTimings.first['words'][0]['start_ms'], 91);
    expect(result.wordTimings.first['words'][0]['end_ms'], 818);
  });
}
