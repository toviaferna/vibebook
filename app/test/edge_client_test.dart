import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/edge/edge_client.dart';

import 'fakes/fake_edge_connection.dart';

EdgeTtsClient clientFor(FakeEdgeConnection connection) {
  return EdgeTtsClient(
    connectionFactory: (uri, headers) async => connection,
    requestDelay: Duration.zero,
    clockProbe: () async => Duration.zero,
  );
}

Future<List<EdgeTtsEvent>> collect(Stream<EdgeTtsEvent> stream) {
  return stream.toList();
}

void main() {
  test('parsea audio y límites de palabra y termina en turn.end', () async {
    final connection = FakeEdgeConnection(
      onSsml: (ssml) => [
        metadataFrame(offset: 10000000, duration: 5000000, word: 'Hola'),
        audioFrame(const [1, 2, 3]),
        audioFrame(const [4, 5]),
        turnEndFrame,
      ],
    );
    final client = clientFor(connection);

    final events = await collect(
      client.synthesize(text: 'Hola', voice: 'es-ES-ElviraNeural', rate: '+0%'),
    );

    final audio = events.whereType<EdgeAudioEvent>().toList();
    expect(audio, hasLength(2));
    expect(audio.first.data, [1, 2, 3]);
    expect(audio.last.data, [4, 5]);

    final words = events.whereType<EdgeWordBoundaryEvent>().toList();
    expect(words, hasLength(1));
    expect(words.first.text, 'Hola');
    expect(words.first.offset, 10000000);
    expect(words.first.duration, 5000000);

    expect(connection.sent, hasLength(2)); // speech.config + ssml
    expect(connection.sent.first, contains('Path:speech.config'));
    expect(connection.sent.last, contains('Path:ssml'));
    expect(
      connection.sent.last,
      contains(
        'Microsoft Server Speech Text to Speech Voice (es-ES, ElviraNeural)',
      ),
    );
    expect(connection.sent.last, contains("rate='+0%'"));
    expect(connection.closed, isTrue);
  });

  test('un turno sin audio lanza EdgeNoAudioException', () async {
    final connection = FakeEdgeConnection(onSsml: (ssml) => [turnEndFrame]);
    final client = clientFor(connection);

    await expectLater(
      collect(
        client.synthesize(
          text: 'Hola',
          voice: 'es-ES-ElviraNeural',
          rate: '+0%',
        ),
      ),
      throwsA(isA<EdgeNoAudioException>()),
    );
  });

  test('un texto largo se divide en chunks con offsets acumulados', () async {
    late final FakeEdgeConnection connection;
    connection = FakeEdgeConnection(
      onSsml: (ssml) {
        final isSecond =
            connection.sent.where((m) => m.contains('Path:ssml')).length > 1;
        if (!isSecond) {
          return [
            metadataFrame(offset: 1000000, duration: 4000000, word: 'uno'),
            audioFrame(const [1]),
            turnEndFrame,
          ];
        }
        return [
          metadataFrame(offset: 2000000, duration: 6000000, word: 'dos'),
          audioFrame(const [2]),
          turnEndFrame,
        ];
      },
    );
    final client = clientFor(connection);

    final text = 'a' * 5000;
    final events = await collect(
      client.synthesize(text: text, voice: 'es-MX-JorgeNeural', rate: '+0%'),
    );

    final ssmlCount = connection.sent
        .where((message) => message.contains('Path:ssml'))
        .length;
    expect(ssmlCount, 2);

    final words = events.whereType<EdgeWordBoundaryEvent>().toList();
    expect(words, hasLength(2));
    // El primer chunk ya trae su offset; el segundo acumula el final del
    // primero más el pad entre chunks.
    expect(words.first.offset, 1000000);
    expect(
      words.last.offset,
      2000000 + 1000000 + 4000000 + EdgeTtsClient.chunkPadding100Ns,
    );
    expect(events.whereType<EdgeAudioEvent>(), hasLength(2));
  });

  test('un rate inválido emite ArgumentError antes de conectarse', () async {
    var connects = 0;
    final client = EdgeTtsClient(
      connectionFactory: (uri, headers) async {
        connects += 1;
        throw Exception('no debería llegar acá');
      },
    );

    // Un generador async* no lanza sincrónicamente: valida al escuchar.
    await expectLater(
      client.synthesize(text: 'Hola', voice: 'es-ES-ElviraNeural', rate: '10%'),
      emitsError(isA<ArgumentError>()),
    );
    await pumpEventQueue();
    expect(connects, 0);
  });

  test('un rechazo de conexión reintenta una vez', () async {
    final connection = FakeEdgeConnection(
      onSsml: (ssml) => [
        audioFrame(const [9]),
        turnEndFrame,
      ],
    );
    var rejectedOnce = false;
    final client = EdgeTtsClient(
      connectionFactory: (uri, headers) async {
        if (!rejectedOnce) {
          rejectedOnce = true;
          throw Exception('rejected');
        }
        return connection;
      },
      requestDelay: Duration.zero,
      clockProbe: () async => Duration.zero,
    );

    final events = await collect(
      client.synthesize(text: 'Hola', voice: 'es-ES-ElviraNeural', rate: '+0%'),
    );

    expect(events.whereType<EdgeAudioEvent>(), hasLength(1));
  });
}
