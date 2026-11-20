import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/providers/provider_key_store.dart';
import 'package:vibebook_app/domain/providers.dart';

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

void main() {
  late Directory temp;
  late File file;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-providers-');
    file = File('${temp.path}${Platform.pathSeparator}provider-keys.json');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  test('guarda claves y devuelve solo la pista enmascarada', () async {
    final store = ProviderKeyStore(file: file, environment: const {});
    await store.save('gemini', apiKey: 'AIza-secret-1234');

    final status = await store.status('gemini');
    expect(status.configured, isTrue);
    expect(status.source, 'file');
    expect(status.hint, '•••• 1234');
    expect(await store.key('gemini'), 'AIza-secret-1234');

    final raw = await file.readAsString();
    expect(raw, contains('AIza-secret-1234'));
    expect(raw, isNot(contains('••••')));
  });

  test('rechaza claves cortas, con espacios o sin región', () async {
    final store = ProviderKeyStore(file: file, environment: const {});
    expect(
      () => store.save('gemini', apiKey: 'short'),
      throwsA(isA<ProviderKeyException>()),
    );
    expect(
      () => store.save('gemini', apiKey: 'tiene espacios'),
      throwsA(isA<ProviderKeyException>()),
    );
    expect(
      () => store.save('azure', apiKey: '12345678'),
      throwsA(isA<ProviderKeyException>()),
    );
    await store.save('azure', apiKey: '12345678', region: 'westeurope');
    expect(await store.region('azure'), 'westeurope');
    expect(await store.configured('azure'), isTrue);
  });

  test('las variables de entorno tienen prioridad sobre el archivo', () async {
    final store = ProviderKeyStore(
      file: file,
      environment: const {
        'GEMINI_API_KEY': 'env-key-1234',
        'AZURE_SPEECH_KEY': 'azure-env-1234',
        'AZURE_SPEECH_REGION': 'eastus',
      },
    );
    await store.save('gemini', apiKey: 'file-key-1234');
    expect(await store.key('gemini'), 'env-key-1234');
    final status = await store.status('gemini');
    expect(status.source, 'env');
    expect(status.hint, '•••• 1234');
    expect(await store.region('azure'), 'eastus');
    expect(await store.configured('azure'), isTrue);
  });

  test('un archivo corrupto se trata como vacío', () async {
    file.writeAsStringSync('{ not json');
    final store = ProviderKeyStore(file: file, environment: const {});
    expect(await store.key('gemini'), isNull);
    expect(await store.list(), hasLength(3));
    await store.save('gemini', apiKey: '12345678');
    expect(await store.key('gemini'), '12345678');
  });

  test('migra las claves de Tauri una sola vez', () async {
    final legacy = File(
      '${temp.path}${Platform.pathSeparator}legacy-provider-keys.json',
    );
    legacy.writeAsStringSync(
      jsonEncode({
        'gemini': {'api_key': 'legacy-key-1234'},
      }),
    );
    final store = ProviderKeyStore(
      file: file,
      legacyFile: legacy,
      environment: const {},
    );
    expect(await store.key('gemini'), 'legacy-key-1234');
    expect(file.existsSync(), isTrue);
    expect(await file.readAsString(), contains('legacy-key-1234'));
  });

  test('prueba Gemini y detecta acceso al modelo', () async {
    final store = ProviderKeyStore(
      file: file,
      environment: const {'GEMINI_API_KEY': 'gemini-key-1234'},
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter((options) async {
          expect(options.headers['x-goog-api-key'], 'gemini-key-1234');
          return _json({
            'models': [
              {'name': 'models/gemini-3.8-flash-tts'},
            ],
          });
        }),
    );
    final result = await store.test('gemini');
    expect(result.ok, isTrue);
    expect(result.message, contains('Gemini 3.8 Flash TTS'));
  });

  test('prueba Gemini sin acceso al modelo', () async {
    final store = ProviderKeyStore(
      file: file,
      environment: const {'GEMINI_API_KEY': 'gemini-key-1234'},
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter(
          (options) async => _json({'models': []}),
        ),
    );
    final result = await store.test('gemini');
    expect(result.ok, isFalse);
    expect(result.message, contains('no tiene acceso'));
  });

  test('prueba ElevenLabs y calcula los créditos restantes', () async {
    final store = ProviderKeyStore(
      file: file,
      environment: const {'ELEVENLABS_API_KEY': 'eleven-key-1234'},
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter((options) async {
          expect(options.headers['xi-api-key'], 'eleven-key-1234');
          return _json({'character_count': 1000, 'character_limit': 10000});
        }),
    );
    final result = await store.test('elevenlabs');
    expect(result.ok, isTrue);
    expect(result.creditsUsed, 1000);
    expect(result.creditsLimit, 10000);
    expect(result.message, contains('9.000'));
  });

  test('prueba Azure con región', () async {
    final store = ProviderKeyStore(
      file: file,
      environment: const {
        'AZURE_SPEECH_KEY': 'azure-key-1234',
        'AZURE_SPEECH_REGION': 'westeurope',
      },
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter((options) async {
          expect(
            options.uri.toString(),
            'https://westeurope.api.cognitive.microsoft.com/sts/v1.0/issueToken',
          );
          return ResponseBody.fromString('token', 200);
        }),
    );
    final result = await store.test('azure');
    expect(result.ok, isTrue);
    expect(result.message, contains('westeurope'));
  });

  test('un 401 se convierte en un mensaje accionable sin la clave', () async {
    final store = ProviderKeyStore(
      file: file,
      environment: const {'GEMINI_API_KEY': 'super-secret-key'},
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter(
          (options) async => _json({'error': 'nope'}, status: 401),
        ),
    );
    final result = await store.test('gemini');
    expect(result.ok, isFalse);
    expect(result.message, contains('no es válida'));
    expect(result.message, isNot(contains('super-secret-key')));
  });
}
