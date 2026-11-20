import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../domain/providers.dart';

/// Stores cloud provider keys in the app data directory, never in the UI.
///
/// The file layout matches the Tauri app (`provider-keys.json`). Environment
/// variables win over the file so CI and power users can avoid the UI. On Unix
/// the file is written with mode 0600. A corrupt file is treated as empty: a
/// bad key file must not make the app unusable.
class ProviderKeyStore {
  ProviderKeyStore({
    File? file,
    File? legacyFile,
    Map<String, String>? environment,
    Dio? dio,
    Future<Directory> Function()? supportDirectory,
  }) : _file = file, // ignore: prefer_initializing_formals
       _legacyFile = legacyFile, // ignore: prefer_initializing_formals
       _environment = environment ?? Platform.environment,
       _dio =
           dio ??
           Dio(
             BaseOptions(
               connectTimeout: const Duration(seconds: 15),
               receiveTimeout: const Duration(seconds: 20),
             ),
           ),
       _supportDirectory = supportDirectory ?? getApplicationSupportDirectory;

  static const _envKeys = {
    'gemini': ['GEMINI_API_KEY', 'GOOGLE_API_KEY'],
    'elevenlabs': ['ELEVENLABS_API_KEY'],
    'azure': ['AZURE_SPEECH_KEY'],
  };
  static const _envRegions = {
    'azure': ['AZURE_SPEECH_REGION'],
  };

  final File? _file;
  final File? _legacyFile;
  final Map<String, String> _environment;
  final Dio _dio;
  final Future<Directory> Function() _supportDirectory;
  File? _resolvedFile;

  Future<File> _resolveFile() async {
    final explicit = _file;
    if (explicit != null) {
      return explicit;
    }
    if (_resolvedFile != null) {
      return _resolvedFile!;
    }
    final directory = await _supportDirectory();
    return _resolvedFile = File(p.join(directory.path, 'provider-keys.json'));
  }

  Future<File?> _resolveLegacyFile() async {
    if (_legacyFile != null) {
      return _legacyFile;
    }
    final root = _tauriDataRoot();
    if (root == null) {
      return null;
    }
    final file = File(p.join(root, 'provider-keys.json'));
    return await file.exists() ? file : null;
  }

  String? _tauriDataRoot() {
    if (Platform.isWindows) {
      final local = _environment['LOCALAPPDATA'];
      return local == null || local.isEmpty ? null : p.join(local, 'vibebook');
    }
    final home = _environment['HOME'];
    if (Platform.isMacOS) {
      return home == null || home.isEmpty
          ? null
          : p.join(home, 'Library', 'Application Support', 'vibebook');
    }
    final xdg = _environment['XDG_DATA_HOME'];
    if (xdg != null && xdg.isNotEmpty) {
      return p.join(xdg, 'vibebook');
    }
    return home == null || home.isEmpty
        ? null
        : p.join(home, '.local', 'share', 'vibebook');
  }

  Future<Map<String, Map<String, String>>> _load() async {
    final file = await _resolveFile();
    if (await file.exists()) {
      return _read(file);
    }
    // First run after the migration: adopt the Tauri keys once.
    final legacy = await _resolveLegacyFile();
    if (legacy != null) {
      final payload = await _read(legacy);
      if (payload.isNotEmpty) {
        await _save(payload);
        return payload;
      }
    }
    return {};
  }

  Future<Map<String, Map<String, String>>> _read(File file) async {
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic>) {
        return {};
      }
      final result = <String, Map<String, String>>{};
      for (final entry in decoded.entries) {
        final values = entry.value;
        if (values is! Map) {
          continue;
        }
        final cleaned = <String, String>{};
        for (final value in values.entries) {
          if ((value.key == 'api_key' || value.key == 'region') &&
              value.value is String &&
              (value.value as String).trim().isNotEmpty) {
            cleaned[value.key as String] = (value.value as String).trim();
          }
        }
        if (cleaned.isNotEmpty) {
          result[entry.key] = cleaned;
        }
      }
      return result;
    } on FileSystemException {
      return {};
    } on FormatException {
      return {};
    }
  }

  Future<void> _save(Map<String, Map<String, String>> payload) async {
    final file = await _resolveFile();
    await file.parent.create(recursive: true);
    final temporary = File('${file.path}.part');
    try {
      await temporary.writeAsString(
        const JsonEncoder.withIndent('  ').convert(payload),
        flush: true,
      );
      if (await file.exists()) {
        await file.delete();
      }
      await temporary.rename(file.path);
      if (!Platform.isWindows) {
        await Process.run('chmod', ['600', file.path]);
      }
    } finally {
      if (await temporary.exists()) {
        await temporary.delete();
      }
    }
  }

  String? _envValue(List<String> names) {
    for (final name in names) {
      final value = _environment[name];
      if (value != null && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return null;
  }

  Future<String?> key(String id) async {
    providerInfo(id);
    final fromEnv = _envValue(_envKeys[id] ?? const []);
    if (fromEnv != null) {
      return fromEnv;
    }
    final values = (await _load())[id];
    return values?['api_key'];
  }

  Future<String?> region(String id) async {
    providerInfo(id);
    final fromEnv = _envValue(_envRegions[id] ?? const []);
    if (fromEnv != null) {
      return fromEnv;
    }
    final values = (await _load())[id];
    return values?['region'];
  }

  Future<bool> configured(String id) async {
    final info = providerInfo(id);
    final apiKey = await key(id);
    if (apiKey == null) {
      return false;
    }
    return !info.requiresRegion || (await region(id)) != null;
  }

  Future<List<ProviderStatus>> list() async {
    final result = <ProviderStatus>[];
    for (final info in providerCatalog) {
      result.add(await status(info.id));
    }
    return result;
  }

  Future<ProviderStatus> status(String id) async {
    final info = providerInfo(id);
    final apiKey = await key(id);
    final source = _envValue(_envKeys[id] ?? const []) != null
        ? 'env'
        : apiKey != null
        ? 'file'
        : null;
    final hint = apiKey == null
        ? null
        : apiKey.length > 4
        ? '•••• ${apiKey.substring(apiKey.length - 4)}'
        : '••••';
    return ProviderStatus(
      info: info,
      configured: await configured(id),
      hint: hint,
      source: source,
      region: await region(id),
    );
  }

  Future<void> save(String id, {required String apiKey, String? region}) async {
    final info = providerInfo(id);
    final cleaned = apiKey.trim();
    if (cleaned.length < 8) {
      throw const ProviderKeyException('La clave es demasiado corta.');
    }
    if (cleaned.contains(RegExp(r'\s'))) {
      throw const ProviderKeyException('La clave no puede tener espacios.');
    }
    final cleanedRegion = (region ?? '').trim();
    if (info.requiresRegion && cleanedRegion.isEmpty) {
      throw const ProviderKeyException('Esta clave necesita una región.');
    }
    final payload = await _load();
    final values = payload.putIfAbsent(id, () => <String, String>{});
    values['api_key'] = cleaned;
    if (cleanedRegion.isNotEmpty) {
      values['region'] = cleanedRegion;
    } else {
      values.remove('region');
    }
    await _save(payload);
  }

  Future<void> delete(String id) async {
    providerInfo(id);
    final payload = await _load();
    if (payload.remove(id) != null) {
      await _save(payload);
    }
  }

  Future<ProviderTestResult> test(String id) async {
    final info = providerInfo(id);
    final apiKey = await key(id);
    if (apiKey == null) {
      return const ProviderTestResult(
        ok: false,
        message: 'La clave todavía no está configurada.',
      );
    }
    try {
      return switch (id) {
        'gemini' => await _testGemini(apiKey),
        'elevenlabs' => await _testElevenLabs(apiKey),
        'azure' => await _testAzure(apiKey, await region(id)),
        _ => ProviderTestResult(
          ok: false,
          message: '${info.label} no tiene prueba disponible.',
        ),
      };
    } on DioException catch (error) {
      return ProviderTestResult(ok: false, message: _networkMessage(error));
    } on FormatException {
      return const ProviderTestResult(
        ok: false,
        message: 'El proveedor devolvió una respuesta inválida.',
      );
    }
  }

  Future<ProviderTestResult> _testGemini(String apiKey) async {
    final response = await _dio.get<dynamic>(
      'https://generativelanguage.googleapis.com/v1beta/models',
      options: Options(
        headers: {'x-goog-api-key': apiKey},
        validateStatus: (status) => status != null,
      ),
    );
    if (response.statusCode != 200) {
      return ProviderTestResult(
        ok: false,
        message: _httpMessage('Gemini', response),
      );
    }
    final body = response.data;
    final models = <String>{};
    if (body is Map && body['models'] is List) {
      for (final item in body['models'] as List) {
        if (item is Map && item['name'] is String) {
          models.add((item['name'] as String).replaceFirst('models/', ''));
        }
      }
    }
    if (!models.contains('gemini-3.8-flash-tts')) {
      return const ProviderTestResult(
        ok: false,
        message:
            'La clave funciona, pero no tiene acceso a gemini-3.8-flash-tts.',
      );
    }
    return const ProviderTestResult(
      ok: true,
      message: 'Conectado. Gemini 3.8 Flash TTS disponible.',
    );
  }

  Future<ProviderTestResult> _testElevenLabs(String apiKey) async {
    final response = await _dio.get<dynamic>(
      'https://api.elevenlabs.io/v1/user/subscription',
      options: Options(
        headers: {'xi-api-key': apiKey},
        validateStatus: (status) => status != null,
      ),
    );
    if (response.statusCode != 200) {
      return ProviderTestResult(
        ok: false,
        message: _httpMessage('ElevenLabs', response),
      );
    }
    final body = response.data;
    final used = body is Map ? _asInt(body['character_count']) : null;
    final limit = body is Map ? _asInt(body['character_limit']) : null;
    final remaining = used != null && limit != null ? limit - used : null;
    return ProviderTestResult(
      ok: true,
      message: remaining == null
          ? 'Conectado.'
          : 'Conectado — ${_formatNumber(remaining)} créditos restantes.',
      creditsUsed: used,
      creditsLimit: limit,
    );
  }

  Future<ProviderTestResult> _testAzure(String apiKey, String? region) async {
    if (region == null || region.isEmpty) {
      return const ProviderTestResult(
        ok: false,
        message: 'Falta la región de Azure.',
      );
    }
    final response = await _dio.post<dynamic>(
      'https://$region.api.cognitive.microsoft.com/sts/v1.0/issueToken',
      options: Options(
        headers: {'Ocp-Apim-Subscription-Key': apiKey},
        contentType: Headers.textPlainContentType,
        validateStatus: (status) => status != null,
      ),
    );
    if (response.statusCode == 200) {
      return ProviderTestResult(
        ok: true,
        message: 'Conectado a Azure Speech ($region).',
      );
    }
    return ProviderTestResult(
      ok: false,
      message: _httpMessage('Azure', response),
    );
  }

  String _httpMessage(String provider, Response<dynamic> response) {
    final status = response.statusCode;
    if (status == 401 || status == 403) {
      return 'La clave de $provider no es válida o no tiene permisos.';
    }
    if (status == 429) {
      return '$provider aplicó un límite de solicitudes. Probá más tarde.';
    }
    if (status != null && status >= 500) {
      return '$provider no está disponible ahora (HTTP $status).';
    }
    return '$provider respondió HTTP ${status ?? 'desconocido'}.';
  }

  String _networkMessage(DioException error) {
    final type = error.type;
    if (type == DioExceptionType.connectionTimeout ||
        type == DioExceptionType.receiveTimeout ||
        type == DioExceptionType.sendTimeout) {
      return 'La conexión tardó demasiado. Revisá tu red.';
    }
    if (type == DioExceptionType.connectionError) {
      return 'No se pudo conectar. Revisá tu red o el firewall.';
    }
    return 'No se pudo conectar con el proveedor.';
  }

  int? _asInt(Object? value) {
    if (value is num) {
      return value.toInt();
    }
    if (value is String) {
      return int.tryParse(value);
    }
    return null;
  }

  String _formatNumber(int value) {
    final digits = value.toString();
    final buffer = StringBuffer();
    for (var index = 0; index < digits.length; index++) {
      if (index > 0 && (digits.length - index) % 3 == 0) {
        buffer.write('.');
      }
      buffer.write(digits[index]);
    }
    return buffer.toString();
  }
}
