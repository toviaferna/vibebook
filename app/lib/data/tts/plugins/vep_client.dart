import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../cloud/cloud_tts.dart';

class VepVoice {
  const VepVoice({
    required this.id,
    required this.locale,
    required this.gender,
    this.styles = const [],
  });

  final String id;
  final String locale;
  final String gender;
  final List<String> styles;
}

class VepPlugin {
  const VepPlugin({
    required this.url,
    required this.id,
    required this.name,
    required this.version,
    required this.license,
    required this.source,
    required this.voices,
    this.styles = const [],
    this.timings = 'segment',
    this.maxChars = 400,
    this.tokenSet = false,
  });

  final String url;
  final String id;
  final String name;
  final String version;
  final String license;
  final String source;
  final List<VepVoice> voices;
  final List<String> styles;
  final String timings;
  final int maxChars;
  final bool tokenSet;

  VepPlugin copyWith({bool? tokenSet}) {
    return VepPlugin(
      url: url,
      id: id,
      name: name,
      version: version,
      license: license,
      source: source,
      voices: voices,
      styles: styles,
      timings: timings,
      maxChars: maxChars,
      tokenSet: tokenSet ?? this.tokenSet,
    );
  }

  Map<String, dynamic> toJson() => {
    'url': url,
    'id': id,
    'name': name,
    'version': version,
    'license': license,
    'source': source,
    'styles': styles,
    'timings': timings,
    'max_chars': maxChars,
    'token_set': tokenSet,
    'voices': [
      for (final voice in voices)
        {
          'id': voice.id,
          'locale': voice.locale,
          'gender': voice.gender,
          'styles': voice.styles,
        },
    ],
  };

  factory VepPlugin.fromJson(Map<String, dynamic> json) {
    return VepPlugin(
      url: json['url'] as String? ?? '',
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      version: json['version'] as String? ?? '0.0.0',
      license: json['license'] as String? ?? 'Desconocida',
      source: json['source'] as String? ?? '',
      styles:
          (json['styles'] as List?)?.whereType<String>().toList() ?? const [],
      timings: json['timings'] as String? ?? 'segment',
      maxChars: (json['max_chars'] as num?)?.toInt() ?? 400,
      tokenSet: json['token_set'] == true,
      voices: [
        for (final item in (json['voices'] as List? ?? const []))
          if (item is Map<String, dynamic> && item['id'] is String)
            VepVoice(
              id: item['id'] as String,
              locale: item['locale'] as String? ?? 'es-419',
              gender: item['gender'] as String? ?? 'neutral',
              styles:
                  (item['styles'] as List?)?.whereType<String>().toList() ??
                  const [],
            ),
      ],
    );
  }
}

/// Client for the Vibebook Engine Protocol v1 (`vep/1`).
class VepClient {
  VepClient({Dio? dio})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 120),
            ),
          );

  final Dio _dio;

  static final _idPattern = RegExp(r'^[a-z0-9][a-z0-9._-]{0,63}$');

  static String normalizeUrl(String url) {
    final parsed = Uri.tryParse(url.trim());
    if (parsed == null ||
        !const {'http', 'https'}.contains(parsed.scheme) ||
        parsed.host.isEmpty) {
      throw const CloudTtsException(
        'La URL del plugin debe ser http(s) absoluta.',
      );
    }
    if (parsed.userInfo.isNotEmpty) {
      throw const CloudTtsException(
        'La URL del plugin no puede incluir credenciales.',
      );
    }
    final local = const {
      '127.0.0.1',
      'localhost',
      '::1',
    }.contains(parsed.host.toLowerCase());
    if (parsed.scheme == 'http' && !local) {
      throw const CloudTtsException('Los plugins remotos deben usar HTTPS.');
    }
    var path = parsed.path;
    for (final suffix in const ['/v1/synthesize', '/v1/info', '/v1']) {
      if (path.endsWith(suffix)) {
        path = path.substring(0, path.length - suffix.length);
        break;
      }
    }
    path = path.replaceAll(RegExp(r'/+$'), '');
    final normalized = Uri(
      scheme: parsed.scheme,
      host: parsed.host,
      port: parsed.hasPort ? parsed.port : null,
      path: path,
    );
    return normalized.toString().replaceAll(RegExp(r'/+$'), '');
  }

  Map<String, String> _headers(String? token) {
    return {
      if (token != null && token.trim().isNotEmpty)
        'X-Vibebook-Plugin-Token': token.trim(),
    };
  }

  Future<VepPlugin> fetchInfo(String url, {String? token}) async {
    final normalized = normalizeUrl(url);
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>(
        '$normalized/v1/info',
        options: Options(
          headers: _headers(token),
          validateStatus: (status) => status != null,
        ),
      );
    } on DioException {
      throw const CloudTtsException('No se pudo conectar con el plugin.');
    }
    if (response.statusCode != 200) {
      throw CloudTtsException(
        'El plugin devolvió HTTP ${response.statusCode}.',
      );
    }
    final data = response.data;
    if (data is! Map) {
      throw const CloudTtsException('El plugin devolvió datos inválidos.');
    }
    if (data['protocol'] != 'vep/1') {
      throw const CloudTtsException(
        'El plugin no implementa el protocolo vep/1.',
      );
    }
    final id = '${data['id'] ?? ''}';
    if (!_idPattern.hasMatch(id)) {
      throw const CloudTtsException('El id del plugin no es válido.');
    }
    final name = '${data['name'] ?? ''}';
    if (name.isEmpty) {
      throw const CloudTtsException('El plugin no tiene nombre.');
    }
    final voices = <VepVoice>[];
    for (final item in (data['voices'] as List? ?? const [])) {
      if (item is! Map || item['id'] is! String) {
        continue;
      }
      voices.add(
        VepVoice(
          id: item['id'] as String,
          locale: '${item['locale'] ?? 'es-419'}',
          gender: '${item['gender'] ?? 'neutral'}',
          styles: (item['styles'] as List? ?? const [])
              .whereType<String>()
              .toList(growable: false),
        ),
      );
    }
    if (voices.isEmpty) {
      throw const CloudTtsException('El plugin no expone ninguna voz.');
    }
    final capabilities = data['capabilities'];
    final limits = data['limits'];
    return VepPlugin(
      url: normalized,
      id: id,
      name: name,
      version: '${data['version'] ?? '0.0.0'}',
      license: '${data['license'] ?? 'Desconocida'}',
      source: '${data['source'] ?? ''}',
      voices: voices,
      styles: capabilities is Map
          ? (capabilities['styles'] as List? ?? const [])
                .whereType<String>()
                .toList(growable: false)
          : const [],
      timings: capabilities is Map
          ? '${capabilities['timings'] ?? 'segment'}'
          : 'segment',
      maxChars: limits is Map
          ? (limits['max_chars'] as num?)?.toInt() ?? 400
          : 400,
      tokenSet: token != null && token.trim().isNotEmpty,
    );
  }

  Future<CloudAudio> synthesize({
    required String url,
    required String text,
    required String voice,
    String style = 'neutral',
    String? token,
  }) async {
    final normalized = normalizeUrl(url);
    final Response<dynamic> response;
    try {
      response = await _dio.post<dynamic>(
        '$normalized/v1/synthesize',
        data: {
          'text': text,
          'voice': voice,
          'style': style,
          'rate': '+0%',
          'format': 'wav',
        },
        options: Options(
          headers: _headers(token),
          validateStatus: (status) => status != null,
        ),
      );
    } on DioException {
      throw const CloudTtsException('No se pudo conectar con el plugin.');
    }
    final status = response.statusCode ?? 0;
    if (status >= 400) {
      throw CloudTtsException(
        'El plugin respondió HTTP $status'
        '${errorDetail(response.data) == null ? '' : ': ${errorDetail(response.data)}'}',
      );
    }
    final data = response.data;
    if (data is! Map) {
      throw const CloudTtsException('El plugin devolvió datos inválidos.');
    }
    if ('${data['format'] ?? 'wav'}' != 'wav') {
      throw CloudTtsException(
        'El plugin devolvió un formato no soportado: ${data['format']}.',
      );
    }
    final encoded = data['audio_base64'];
    if (encoded is! String || encoded.isEmpty) {
      throw const CloudTtsException('El plugin no devolvió audio.');
    }
    final Uint8List bytes;
    try {
      bytes = base64Decode(encoded);
    } on FormatException {
      throw const CloudTtsException(
        'El plugin devolvió audio base64 inválido.',
      );
    }
    if (bytes.length < 12 || String.fromCharCodes(bytes.take(4)) != 'RIFF') {
      throw const CloudTtsException('El plugin devolvió un WAV inválido.');
    }
    return CloudAudio(
      bytes: bytes,
      extension: 'wav',
      words: _parseWords(data['words']),
    );
  }

  Future<void> test(String url, {String? token}) async {
    final plugin = await fetchInfo(url, token: token);
    if (plugin.voices.isEmpty) {
      throw const CloudTtsException('El plugin no tiene voces.');
    }
  }

  List<CloudWordTiming> _parseWords(Object? value) {
    if (value == null) {
      return const [];
    }
    if (value is! List) {
      throw const CloudTtsException('El plugin devolvió timings inválidos.');
    }
    final words = <CloudWordTiming>[];
    for (final item in value) {
      if (item is! Map) {
        throw const CloudTtsException('El plugin devolvió timings inválidos.');
      }
      final text = item['text'];
      final start = item['start_ms'];
      final end = item['end_ms'];
      if (text is! String ||
          text.isEmpty ||
          start is! num ||
          end is! num ||
          end <= start) {
        throw const CloudTtsException('El plugin devolvió timings inválidos.');
      }
      words.add(
        CloudWordTiming(text: text, startMs: start.toInt(), endMs: end.toInt()),
      );
    }
    return words;
  }
}

class VepTtsClient implements CloudTtsClient {
  VepTtsClient({required this.client, required this.url, this.token});

  final VepClient client;
  final String url;
  final String? token;

  @override
  String get providerId => 'plugin';

  @override
  Future<CloudAudio> synthesize({
    required String text,
    required String voice,
    String style = 'neutral',
  }) {
    return client.synthesize(
      url: url,
      text: text,
      voice: voice,
      style: style,
      token: token,
    );
  }
}
