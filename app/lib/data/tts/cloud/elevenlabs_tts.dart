import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'cloud_tts.dart';

/// ElevenLabs text-to-speech with character alignment.
///
/// ElevenLabs reports exact character timings; we group them into words so the
/// reader can do native word karaoke.
class ElevenLabsTtsClient implements CloudTtsClient {
  ElevenLabsTtsClient({
    required this.apiKey,
    Dio? dio,
    this.model = 'eleven_turbo_v2_5',
    this.maxAttempts = 3,
    this.timeout = const Duration(seconds: 180),
  }) : _dio =
           dio ??
           Dio(
             BaseOptions(
               connectTimeout: const Duration(seconds: 15),
               receiveTimeout: timeout,
             ),
           );

  final String apiKey;
  final Dio _dio;
  final String model;
  final int maxAttempts;
  final Duration timeout;

  static const apiRoot = 'https://api.elevenlabs.io/v1';
  static const expressiveModel = 'eleven_v3';

  static const styleSettings = {
    'neutral': (0.15, 0.65),
    'chat': (0.35, 0.55),
    'cheerful': (0.55, 0.45),
    'excited': (0.65, 0.4),
    'sad': (0.5, 0.7),
    'whispering': (0.6, 0.8),
    'epic': (0.6, 0.5),
    'suspense': (0.5, 0.7),
  };

  static const styleTags = {
    'sad': '[sad]',
    'whispering': '[whispers]',
    'epic': '[dramatic]',
    'suspense': '[whispers]',
  };

  @override
  String get providerId => 'elevenlabs';

  @override
  Future<CloudAudio> synthesize({
    required String text,
    required String voice,
    String style = 'neutral',
  }) async {
    final cleaned = text.trim();
    if (cleaned.isEmpty) {
      throw const CloudTtsException('ElevenLabs recibió un texto vacío.');
    }
    if (!styleSettings.containsKey(style)) {
      throw CloudTtsException('ElevenLabs no admite el estilo "$style".');
    }
    final selectedModel = styleTags.containsKey(style)
        ? expressiveModel
        : model;
    final tag = styleTags[style];
    final spoken = tag == null ? cleaned : '$tag $cleaned';
    final settings = styleSettings[style]!;
    final body = <String, dynamic>{
      'text': spoken,
      'model_id': selectedModel,
      'voice_settings': {
        'stability': settings.$2,
        'similarity_boost': 0.75,
        'style': settings.$1,
        'use_speaker_boost': true,
      },
    };

    CloudTtsException? lastError;
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        final response = await _dio.post<dynamic>(
          '$apiRoot/text-to-speech/$voice/with-timestamps',
          data: body,
          options: Options(
            headers: {'xi-api-key': apiKey, 'Accept': 'application/json'},
            validateStatus: (status) => status != null,
          ),
        );
        final status = response.statusCode ?? 0;
        if (status == 200) {
          final payload = response.data;
          if (payload is! Map<String, dynamic>) {
            throw const CloudTtsException(
              'ElevenLabs devolvió una respuesta inválida.',
            );
          }
          final encoded = payload['audio_base64'];
          if (encoded is! String || encoded.isEmpty) {
            throw const CloudTtsException('ElevenLabs no devolvió audio.');
          }
          final Uint8List bytes;
          try {
            bytes = base64Decode(encoded);
          } on FormatException {
            throw const CloudTtsException(
              'ElevenLabs devolvió audio base64 inválido.',
            );
          }
          return CloudAudio(
            bytes: bytes,
            extension: 'mp3',
            words: alignmentWords(payload['alignment']),
          );
        }
        final message = cleanErrorMessage(
          httpErrorMessage(
            'ElevenLabs',
            status,
            detail: errorDetail(response.data),
          ),
        );
        if (status >= 500) {
          lastError = CloudTtsException(message, statusCode: status);
          if (attempt < maxAttempts) {
            await Future<void>.delayed(Duration(seconds: 2 * attempt));
            continue;
          }
          break;
        }
        if (status == 429) {
          lastError = CloudTtsException(message, statusCode: status);
          if (attempt < maxAttempts) {
            await Future<void>.delayed(
              Duration(seconds: _retrySeconds(response, 5)),
            );
            continue;
          }
          break;
        }
        throw CloudTtsException(message, statusCode: status);
      } on DioException catch (error) {
        lastError = CloudTtsException(
          _networkMessage(error),
          statusCode: error.response?.statusCode,
        );
        if (attempt < maxAttempts) {
          await Future<void>.delayed(Duration(seconds: 2 * attempt));
          continue;
        }
      }
    }
    throw lastError ?? const CloudTtsException('ElevenLabs TTS falló.');
  }

  int _retrySeconds(Response<dynamic> response, int fallback) {
    final header = response.headers.value('retry-after');
    if (header != null) {
      final parsed = int.tryParse(header);
      if (parsed != null) {
        return parsed.clamp(1, 120);
      }
    }
    return fallback;
  }

  String _networkMessage(DioException error) {
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.sendTimeout) {
      return 'ElevenLabs tardó demasiado en responder.';
    }
    if (error.type == DioExceptionType.connectionError) {
      return 'No se pudo conectar con ElevenLabs. Revisá tu red.';
    }
    return 'No se pudo conectar con ElevenLabs.';
  }
}

final _tag = RegExp(r'^\[[a-zA-Z][a-zA-Z _-]*\]$');

/// Groups ElevenLabs character timings into words, dropping emotional tags.
List<CloudWordTiming> alignmentWords(Object? alignment) {
  if (alignment is! Map) {
    return const [];
  }
  final characters = alignment['characters'];
  final starts = alignment['character_start_times_seconds'];
  final ends = alignment['character_end_times_seconds'];
  if (characters is! List || starts is! List || ends is! List) {
    return const [];
  }
  if (characters.length != starts.length || characters.length != ends.length) {
    return const [];
  }
  final words = <CloudWordTiming>[];
  final buffer = StringBuffer();
  var start = 0.0;
  var end = 0.0;
  for (var index = 0; index < characters.length; index++) {
    final character = characters[index];
    if (character is! String || character.isEmpty) {
      continue;
    }
    if (character.trim().isEmpty) {
      if (buffer.isNotEmpty) {
        _addWord(words, buffer.toString(), start, end);
        buffer.clear();
      }
      continue;
    }
    if (buffer.isEmpty) {
      start = _seconds(starts[index]);
    }
    buffer.write(character);
    end = _seconds(ends[index]);
  }
  if (buffer.isNotEmpty) {
    _addWord(words, buffer.toString(), start, end);
  }
  return words
      .where((word) => word.endMs > word.startMs && !_tag.hasMatch(word.text))
      .toList(growable: false);
}

void _addWord(
  List<CloudWordTiming> words,
  String text,
  double startSeconds,
  double endSeconds,
) {
  final startMs = (startSeconds * 1000).round();
  var endMs = (endSeconds * 1000).round();
  if (endMs <= startMs) {
    endMs = startMs + (text.length * 60).clamp(1, 2000).toInt();
  }
  words.add(
    CloudWordTiming(
      text: text,
      startMs: startMs < 0 ? 0 : startMs,
      endMs: endMs,
    ),
  );
}

double _seconds(Object? value) {
  if (value is num) {
    return value < 0 ? 0 : value.toDouble();
  }
  if (value is String) {
    final parsed = double.tryParse(value);
    return parsed == null || parsed < 0 ? 0 : parsed;
  }
  return 0;
}
