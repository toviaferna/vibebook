import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/cloud/azure_tts.dart';
import 'package:vibebook_app/data/tts/cloud/cloud_tts.dart';
import 'package:vibebook_app/data/tts/cloud/elevenlabs_tts.dart';
import 'package:vibebook_app/data/tts/cloud/gemini_tts.dart';

class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.handler);

  final Future<ResponseBody> Function(RequestOptions options) handler;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Object value, {int status = 200}) {
  return ResponseBody.fromString(
    jsonEncode(value),
    status,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

Uint8List _tinyWav() {
  return wrapPcm16(bytes: Uint8List.fromList([0, 0, 0, 0]));
}

void main() {
  group('Azure', () {
    test('construye SSML con estilo y escapa el texto', () {
      final client = AzureTtsClient(apiKey: 'key', region: 'westeurope');
      final ssml = client.buildSsml(
        text: 'Uno & dos <tres>',
        voice: 'es-MX-JorgeNeural',
        style: 'cheerful',
      );
      expect(ssml, contains('xml:lang="es-MX"'));
      expect(ssml, contains('mstts:express-as style="cheerful"'));
      expect(ssml, contains('Uno &amp; dos &lt;tres&gt;'));
      expect(ssml, contains('<voice name="es-MX-JorgeNeural">'));
    });

    test('neutral no envuelve el audio en express-as', () {
      final client = AzureTtsClient(apiKey: 'key', region: 'westeurope');
      final ssml = client.buildSsml(text: 'Hola', voice: 'es-MX-JorgeNeural');
      expect(ssml, isNot(contains('express-as')));
    });

    test('envía la clave, el formato MP3 y devuelve los bytes', () async {
      final client = AzureTtsClient(
        apiKey: 'azure-key',
        region: 'westeurope',
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter((options) async {
            expect(
              options.uri.toString(),
              'https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1',
            );
            expect(options.headers['Ocp-Apim-Subscription-Key'], 'azure-key');
            expect(
              options.headers['X-Microsoft-OutputFormat'],
              'audio-24khz-48kbitrate-mono-mp3',
            );
            final ssml = utf8.decode(options.data as List<int>);
            expect(ssml, contains('Hola'));
            return ResponseBody.fromBytes([0x49, 0x44, 0x33, 0x04], 200);
          }),
      );
      final audio = await client.synthesize(
        text: 'Hola',
        voice: 'es-MX-JorgeNeural',
      );
      expect(audio.extension, 'mp3');
      expect(audio.bytes, [0x49, 0x44, 0x33, 0x04]);
    });

    test('un 401 es accionable y no filtra la clave', () async {
      final client = AzureTtsClient(
        apiKey: 'secret-azure-key',
        region: 'westeurope',
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter(
            (options) async => _json({'error': 'bad'}, status: 401),
          ),
      );
      expect(
        () => client.synthesize(text: 'Hola', voice: 'es-MX-JorgeNeural'),
        throwsA(
          isA<CloudTtsException>().having(
            (error) => error.message,
            'message',
            contains('no es válida'),
          ),
        ),
      );
    });
  });

  group('Gemini', () {
    test('incluye estilo, modelo y voz', () async {
      late Map<String, dynamic> body;
      final client = GeminiTtsClient(
        apiKey: 'gemini-key',
        maxAttempts: 1,
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter((options) async {
            expect(options.headers['x-goog-api-key'], 'gemini-key');
            body = Map<String, dynamic>.from(options.data as Map);
            return _json({
              'steps': [
                {
                  'content': [
                    {
                      'type': 'audio',
                      'data': base64Encode(_tinyWav()),
                      'mime_type': 'audio/wav',
                    },
                  ],
                },
              ],
            });
          }),
      );
      final audio = await client.synthesize(
        text: 'La casa olía a sal.',
        voice: 'Kore',
        style: 'sad',
      );
      expect(body['model'], 'gemini-3.8-flash-tts');
      expect(body['response_format']['type'], 'audio');
      expect(body['generation_config']['speech_config'][0]['voice'], 'Kore');
      final content = body['input'][0]['content'][0];
      expect(content['annotations'][0]['style'], contains('sad'));
      expect(audio.extension, 'wav');
      expect(audio.bytes.take(4).toList(), [0x52, 0x49, 0x46, 0x46]);
    });

    test('envuelve PCM crudo en WAV', () async {
      final client = GeminiTtsClient(
        apiKey: 'gemini-key',
        maxAttempts: 1,
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter(
            (options) async => _json({
              'output_audio': {
                'data': base64Encode([1, 2, 3, 4]),
                'mimeType': 'audio/l16;rate=24000',
              },
            }),
          ),
      );
      final audio = await client.synthesize(text: 'Hola', voice: 'Kore');
      expect(audio.extension, 'wav');
      expect(audio.bytes.take(4).toList(), [0x52, 0x49, 0x46, 0x46]);
      expect(audio.bytes.length, 48);
    });

    test('un 429 se reintenta y luego falla con mensaje claro', () async {
      var calls = 0;
      final client = GeminiTtsClient(
        apiKey: 'gemini-key',
        maxAttempts: 2,
        providerRetrySeconds: 1,
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter((options) async {
            calls += 1;
            return _json({
              'error': {'message': 'rate limited'},
            }, status: 429);
          }),
      );
      await expectLater(
        client.synthesize(text: 'Hola', voice: 'Kore'),
        throwsA(
          isA<CloudTtsException>().having(
            (error) => error.message,
            'message',
            contains('límite'),
          ),
        ),
      );
      expect(calls, 2);
    });
  });

  group('ElevenLabs', () {
    test('agrupa caracteres en palabras y descarta etiquetas', () {
      final words = alignmentWords({
        'characters': [
          '[',
          's',
          'a',
          'd',
          ']',
          ' ',
          'U',
          'n',
          'o',
          ' ',
          'd',
          'o',
          's',
        ],
        'character_start_times_seconds': [
          0.0,
          0.01,
          0.02,
          0.03,
          0.04,
          0.05,
          0.1,
          0.2,
          0.3,
          0.4,
          0.5,
          0.6,
          0.7,
        ],
        'character_end_times_seconds': [
          0.01,
          0.02,
          0.03,
          0.04,
          0.05,
          0.06,
          0.2,
          0.3,
          0.4,
          0.5,
          0.6,
          0.7,
          0.8,
        ],
      });
      expect(words.map((word) => word.text), ['Uno', 'dos']);
      expect(words.first.startMs, 100);
      expect(words.first.endMs, 400);
      expect(words.last.endMs, 800);
    });

    test('envía la etiqueta emocional y devuelve audio + timings', () async {
      late Map<String, dynamic> body;
      final client = ElevenLabsTtsClient(
        apiKey: 'eleven-key',
        maxAttempts: 1,
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter((options) async {
            expect(options.headers['xi-api-key'], 'eleven-key');
            body = Map<String, dynamic>.from(options.data as Map);
            return _json({
              'audio_base64': base64Encode([0x49, 0x44, 0x33]),
              'alignment': {
                'characters': ['H', 'o', 'l', 'a'],
                'character_start_times_seconds': [0.0, 0.1, 0.2, 0.3],
                'character_end_times_seconds': [0.1, 0.2, 0.3, 0.4],
              },
            });
          }),
      );
      final audio = await client.synthesize(
        text: 'Hola',
        voice: 'pNInz6obpgDQGcFmaJgB',
        style: 'sad',
      );
      expect(body['model_id'], 'eleven_v3');
      expect(body['text'], startsWith('[sad]'));
      expect(audio.words.single.text, 'Hola');
      expect(audio.words.single.startMs, 0);
      expect(audio.words.single.endMs, 400);
    });

    test('un 402 explica el problema del plan', () async {
      final client = ElevenLabsTtsClient(
        apiKey: 'eleven-key',
        maxAttempts: 1,
        dio: Dio()
          ..httpClientAdapter = _FakeAdapter(
            (options) async =>
                _json({'detail': 'paid plan required'}, status: 402),
          ),
      );
      expect(
        () => client.synthesize(text: 'Hola', voice: 'voice'),
        throwsA(
          isA<CloudTtsException>().having(
            (error) => error.message,
            'message',
            contains('plan'),
          ),
        ),
      );
    });
  });

  test('parseRatePercent valida el rango', () {
    expect(parseRatePercent('-10%'), -10);
    expect(parseRatePercent('+5%'), 5);
    expect(() => parseRatePercent('10'), throwsA(isA<CloudTtsException>()));
    expect(() => parseRatePercent('-100%'), throwsA(isA<CloudTtsException>()));
  });
}
