import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/cloud/cloud_tts.dart';
import 'package:vibebook_app/data/tts/plugins/vep_client.dart';
import 'package:vibebook_app/data/tts/plugins/vep_repository.dart';

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

Map<String, dynamic> _info() => {
  'protocol': 'vep/1',
  'id': 'mi-motor',
  'name': 'Mi motor',
  'version': '1.0.0',
  'license': 'MIT',
  'source': 'https://example.test/repo',
  'capabilities': {
    'styles': ['neutral', 'sad'],
    'timings': 'native_word',
  },
  'limits': {'max_chars': 500},
  'voices': [
    {
      'id': 'es-MX-demo',
      'locale': 'es-MX',
      'gender': 'female',
      'styles': ['neutral'],
    },
  ],
};

VepClient _client() {
  return VepClient(
    dio: Dio()
      ..httpClientAdapter = _FakeAdapter((options) async {
        if (options.path.endsWith('/v1/info')) {
          return _json(_info());
        }
        if (options.path.endsWith('/v1/synthesize')) {
          return _json({
            'format': 'wav',
            'audio_base64': base64Encode(
              wrapPcm16(bytes: Uint8List.fromList([0, 0, 1, 0])),
            ),
            'words': [
              {'text': 'Hola', 'start_ms': 0, 'end_ms': 400},
            ],
          });
        }
        return _json({'error': 'not found'}, status: 404);
      }),
  );
}

void main() {
  test('normaliza URLs y exige HTTPS fuera de loopback', () {
    expect(
      VepClient.normalizeUrl('http://127.0.0.1:9001/v1'),
      'http://127.0.0.1:9001',
    );
    expect(
      VepClient.normalizeUrl('https://example.test/plugin/v1/info'),
      'https://example.test/plugin',
    );
    expect(
      () => VepClient.normalizeUrl('http://example.test/plugin'),
      throwsA(isA<CloudTtsException>()),
    );
    expect(
      () => VepClient.normalizeUrl('ftp://example.test/plugin'),
      throwsA(isA<CloudTtsException>()),
    );
    expect(
      () => VepClient.normalizeUrl('https://user:pass@example.test/plugin'),
      throwsA(isA<CloudTtsException>()),
    );
  });

  test('lee la información del plugin', () async {
    final plugin = await _client().fetchInfo('http://127.0.0.1:9001');
    expect(plugin.id, 'mi-motor');
    expect(plugin.name, 'Mi motor');
    expect(plugin.license, 'MIT');
    expect(plugin.voices.single.locale, 'es-MX');
    expect(plugin.timings, 'native_word');
    expect(plugin.maxChars, 500);
    expect(plugin.styles, contains('sad'));
  });

  test('rechaza un protocolo distinto', () async {
    final client = VepClient(
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter(
          (options) async => _json({..._info(), 'protocol': 'vep/2'}),
        ),
    );
    expect(
      () => client.fetchInfo('http://127.0.0.1:9001'),
      throwsA(
        isA<CloudTtsException>().having(
          (error) => error.message,
          'message',
          contains('vep/1'),
        ),
      ),
    );
  });

  test('sintetiza WAV y timings nativos', () async {
    final audio = await _client().synthesize(
      url: 'http://127.0.0.1:9001',
      text: 'Hola',
      voice: 'es-MX-demo',
    );
    expect(audio.extension, 'wav');
    expect(audio.bytes.take(4).toList(), [0x52, 0x49, 0x46, 0x46]);
    expect(audio.words.single.text, 'Hola');
    expect(audio.words.single.endMs, 400);
  });

  test('rechaza timings inválidos', () async {
    final client = VepClient(
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter(
          (options) async => _json({
            'format': 'wav',
            'audio_base64': base64Encode(
              wrapPcm16(bytes: Uint8List.fromList([0, 0, 1, 0])),
            ),
            'words': [
              {'text': 'Hola', 'start_ms': 500, 'end_ms': 100},
            ],
          }),
        ),
    );
    expect(
      () => client.synthesize(
        url: 'http://127.0.0.1:9001',
        text: 'Hola',
        voice: 'es-MX-demo',
      ),
      throwsA(isA<CloudTtsException>()),
    );
  });

  test('guarda, prueba y elimina plugins', () async {
    final temp = Directory.systemTemp.createTempSync('vibebook-vep-');
    addTearDown(() => temp.deleteSync(recursive: true));
    final repository = VepPluginRepository(
      client: _client(),
      pluginsFile: File('${temp.path}/plugins.json'),
      secretsFile: File('${temp.path}/secrets.json'),
    );
    final plugin = await repository.add(
      'http://127.0.0.1:9001/v1',
      token: 'secret-token',
    );
    expect(plugin.id, 'mi-motor');
    expect(plugin.tokenSet, isTrue);
    expect(await repository.token('mi-motor'), 'secret-token');
    final pluginsRaw = await File('${temp.path}/plugins.json').readAsString();
    expect(pluginsRaw, isNot(contains('secret-token')));
    final result = await repository.test('mi-motor');
    expect(result.ok, isTrue);
    expect(result.message, contains('1 voces'));
    expect(await repository.list(), hasLength(1));
    await repository.remove('mi-motor');
    expect(await repository.list(), isEmpty);
    expect(await repository.token('mi-motor'), isNull);
  });

  test('un archivo corrupto se trata como vacío', () async {
    final temp = Directory.systemTemp.createTempSync('vibebook-vep-bad-');
    addTearDown(() => temp.deleteSync(recursive: true));
    final plugins = File('${temp.path}/plugins.json');
    plugins.writeAsStringSync('{ nope');
    final repository = VepPluginRepository(
      client: _client(),
      pluginsFile: plugins,
      secretsFile: File('${temp.path}/secrets.json'),
    );
    expect(await repository.list(), isEmpty);
  });
}
