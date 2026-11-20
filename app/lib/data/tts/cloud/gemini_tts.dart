import 'package:dio/dio.dart';

import 'cloud_tts.dart';

/// Google Gemini TTS.
///
/// Gemini returns WAV/PCM audio and does not expose word boundaries, so the
/// reader estimates word timings from the segment duration.
class GeminiTtsClient implements CloudTtsClient {
  GeminiTtsClient({
    required this.apiKey,
    Dio? dio,
    this.maxAttempts = 3,
    this.providerRetrySeconds = 5,
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
  final int maxAttempts;
  final int providerRetrySeconds;
  final Duration timeout;

  static const model = 'gemini-3.8-flash-tts';
  static const url =
      'https://generativelanguage.googleapis.com/v1beta/interactions';

  static const styleInstructions = {
    'neutral': '',
    'chat': 'warm, conversational, close and natural, like a friendly audiobook narrator',
    'cheerful': 'cheerful, bright and friendly',
    'excited': 'excited, energetic and lively',
    'sad': 'sad, melancholic and restrained',
    'whispering': 'whispering, intimate and very quiet',
    'epic': 'epic, dramatic and measured',
    'suspense': 'tense, suspenseful and low',
  };

  @override
  String get providerId => 'gemini';

  @override
  Future<CloudAudio> synthesize({
    required String text,
    required String voice,
    String style = 'neutral',
  }) async {
    final cleaned = text.trim();
    if (cleaned.isEmpty) {
      throw const CloudTtsException('Gemini recibió un texto vacío.');
    }
    if (!styleInstructions.containsKey(style)) {
      throw CloudTtsException('Gemini no admite el estilo "$style".');
    }
    final body = <String, dynamic>{
      'model': model,
      'input': [
        {
          'type': 'user_input',
          'content': [
            {
              'type': 'text',
              'text': cleaned,
              if (styleInstructions[style]!.isNotEmpty)
                'annotations': [
                  {
                    'type': 'speech_metadata',
                    'style': styleInstructions[style],
                  },
                ],
            },
          ],
        },
      ],
      'response_format': {'type': 'audio'},
      'generation_config': {
        'speech_config': [
          {'voice': voice},
        ],
      },
    };

    CloudTtsException? lastError;
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        final response = await _dio.post<dynamic>(
          url,
          data: body,
          options: Options(
            headers: {'x-goog-api-key': apiKey},
            validateStatus: (status) => status != null,
          ),
        );
        final status = response.statusCode ?? 0;
        if (status == 200) {
          final payload = response.data;
          if (payload is! Map<String, dynamic>) {
            throw const CloudTtsException(
              'Gemini devolvió una respuesta inválida.',
            );
          }
          final block = _audioBlock(payload);
          if (block == null) {
            throw const CloudTtsException('Gemini no devolvió audio.');
          }
          return decodeGeminiAudio(block);
        }
        final detail = errorDetail(response.data);
        final message = cleanErrorMessage(
          httpErrorMessage('Gemini', status, detail: detail),
        );
        if (status == 429) {
          lastError = CloudTtsException(message, statusCode: status);
          if (attempt < maxAttempts) {
            await Future<void>.delayed(
              Duration(seconds: _retrySeconds(response, providerRetrySeconds)),
            );
            continue;
          }
          break;
        }
        if (status >= 500) {
          lastError = CloudTtsException(message, statusCode: status);
          if (attempt < maxAttempts) {
            await Future<void>.delayed(Duration(seconds: 2 * attempt));
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
    throw lastError ?? const CloudTtsException('Gemini TTS falló.');
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
      return 'Gemini tardó demasiado en responder.';
    }
    if (error.type == DioExceptionType.connectionError) {
      return 'No se pudo conectar con Gemini. Revisá tu red.';
    }
    return 'No se pudo conectar con Gemini.';
  }

  Map<String, dynamic>? _audioBlock(Map<String, dynamic> payload) {
    for (final step in (payload['steps'] as List? ?? const [])) {
      if (step is! Map) {
        continue;
      }
      for (final content in (step['content'] as List? ?? const [])) {
        if (content is Map && content['type'] == 'audio') {
          return Map<String, dynamic>.from(content);
        }
      }
    }
    final output = payload['output_audio'];
    if (output is Map && output['data'] is String) {
      return {
        'data': output['data'],
        'mime_type': output['mimeType'] ?? output['mime_type'],
      };
    }
    for (final candidate in (payload['candidates'] as List? ?? const [])) {
      if (candidate is! Map) {
        continue;
      }
      final content = candidate['content'];
      if (content is! Map) {
        continue;
      }
      for (final part in (content['parts'] as List? ?? const [])) {
        if (part is Map && part['inlineData'] is Map) {
          final inline = part['inlineData'] as Map;
          if (inline['data'] is String) {
            return {'data': inline['data'], 'mime_type': inline['mimeType']};
          }
        }
      }
    }
    return null;
  }
}
