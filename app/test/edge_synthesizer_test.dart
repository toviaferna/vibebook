import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/chapter_synthesizer.dart';
import 'package:vibebook_app/data/tts/edge/edge_client.dart';
import 'package:vibebook_app/data/tts/edge/edge_synthesizer.dart';
import 'package:vibebook_app/domain/models.dart';

import 'fakes/fake_edge_connection.dart';

EdgeTtsClient clientFor(FakeEdgeConnection connection) {
  return EdgeTtsClient(
    connectionFactory: (uri, headers) async => connection,
    requestDelay: Duration.zero,
    clockProbe: () async => Duration.zero,
  );
}

EdgeSynthesizer synthesizerFor(
  EdgeTtsClient client, {
  required List<Duration> delays,
}) {
  return EdgeSynthesizer(
    client: client,
    voiceId: 'es-MX-JorgeNeural',
    decodeMp3: (mp3) async => Float32List(mp3.length ~/ 2),
    delay: (delay) async => delays.add(delay),
  );
}

Chapter _chapter() {
  return const Chapter(
    index: 1,
    title: 'Capítulo 1',
    segments: [
      Segment(id: 'a', chapterIndex: 1, paragraphIndex: 1, text: 'Hola mundo'),
      Segment(id: 'b', chapterIndex: 1, paragraphIndex: 2, text: 'Otro texto'),
    ],
  );
}

void main() {
  test('dos segmentos producen samples, spans y palabras absolutas', () async {
    final connection = FakeEdgeConnection(
      onSsml: (ssml) {
        final isFirst = !ssml.contains('Otro');
        if (isFirst) {
          return [
            metadataFrame(offset: 1000000, duration: 5000000, word: 'Hola'),
            audioFrame(List.filled(4800, 7)),
            turnEndFrame,
          ];
        }
        return [
          metadataFrame(offset: 0, duration: 3000000, word: 'Otro'),
          audioFrame(List.filled(2400, 9)),
          turnEndFrame,
        ];
      },
    );
    final client = clientFor(connection);
    final delays = <Duration>[];
    final synthesizer = synthesizerFor(client, delays: delays);

    final synthesis = await synthesizer.synthesize(
      _chapter(),
      speed: 1.1,
      isCancelled: () => false,
    );

    // 2400 + 1200 muestras más 190 ms de pausa (4560 frames a 24 kHz).
    expect(synthesis.sampleRate, 24000);
    expect(synthesis.samples.length, 2400 + 4560 + 1200);
    expect(delays, isEmpty);

    expect(synthesis.spans, hasLength(2));
    expect(synthesis.spans.first['id'], 'a');
    expect(synthesis.spans.first['start_ms'], 0);
    expect(synthesis.spans.first['end_ms'], 100);
    expect(synthesis.spans.last['id'], 'b');
    expect(synthesis.spans.last['start_ms'], 290);
    expect(synthesis.spans.last['end_ms'], 340);

    final firstWords = synthesis.wordTimings.first['words'] as List;
    expect(firstWords.first['text'], 'Hola');
    expect(firstWords.first['start_ms'], 100);
    expect(firstWords.first['end_ms'], 600);
    final lastWords = synthesis.wordTimings.last['words'] as List;
    expect(lastWords.first['start_ms'], 290);

    // El rate pedido lleva el signo de la velocidad.
    final ssml = connection.sent.where((m) => m.contains('Path:ssml')).last;
    expect(ssml, contains("rate='+10%'"));
  });

  test('un fallo transitorio reintenta y luego sigue', () async {
    var request = 0;
    final connection = FakeEdgeConnection(
      onSsml: (ssml) {
        request += 1;
        if (request == 1) {
          throw Exception('network');
        }
        if (request == 2) {
          return [
            metadataFrame(offset: 0, duration: 1000, word: 'Hola'),
            audioFrame(List.filled(960, 1)),
            turnEndFrame,
          ];
        }
        return [audioFrame(List.filled(960, 2)), turnEndFrame];
      },
    );
    final client = clientFor(connection);
    final delays = <Duration>[];
    final synthesizer = synthesizerFor(client, delays: delays);

    final synthesis = await synthesizer.synthesize(
      _chapter(),
      speed: 1,
      isCancelled: () => false,
    );

    expect(request, 3);
    expect(delays, [const Duration(seconds: 2)]);
    expect(synthesis.spans, hasLength(2));
  });

  test('un turno sin audio espera los cooldowns y luego revienta', () async {
    final connection = FakeEdgeConnection(onSsml: (ssml) => [turnEndFrame]);
    final client = clientFor(connection);
    final delays = <Duration>[];
    final synthesizer = synthesizerFor(client, delays: delays);

    await expectLater(
      synthesizer.synthesize(_chapter(), speed: 1, isCancelled: () => false),
      throwsA(isA<EdgeNoAudioException>()),
    );
    expect(delays, const [
      Duration(seconds: 60),
      Duration(seconds: 120),
      Duration(seconds: 240),
      Duration(seconds: 480),
    ]);
  });

  test('la cancelación a mitad de capítulo corta la síntesis', () async {
    var cancelled = false;
    var requests = 0;
    final connection = FakeEdgeConnection(
      onSsml: (ssml) {
        requests += 1;
        cancelled = true; // el usuario cancela durante el primer segmento
        return [audioFrame(List.filled(960, 1)), turnEndFrame];
      },
    );
    final client = clientFor(connection);
    final delays = <Duration>[];
    final synthesizer = synthesizerFor(client, delays: delays);

    await expectLater(
      synthesizer.synthesize(
        _chapter(),
        speed: 1,
        isCancelled: () => cancelled,
      ),
      throwsA(isA<SynthesisCancelled>()),
    );
    expect(requests, 1); // cortó antes del segundo segmento
  });
}
