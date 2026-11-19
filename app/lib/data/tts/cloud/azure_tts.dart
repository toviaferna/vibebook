import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'cloud_tts.dart';

/// Azure Speech over the REST endpoint.
///
/// The REST endpoint returns MP3 without word boundaries; the reader estimates
/// word timings for Azure. Styles are sent as SSML `mstts:express-as`.
class AzureTtsClient implements CloudTtsClient {
  AzureTtsClient({required this.apiKey, required this.region, Dio? dio})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              connectTimeout: const Duration(seconds: 15),
              receiveTimeout: const Duration(seconds: 90),
            ),
          );

  final String apiKey;
  final String region;
  final Dio _dio;

  static const allowedStyles = {
    'neutral',
    'chat',
    'cheerful',
    'excited',
    'sad',
    'whispering',
  };

  @override
  String get providerId => 'azure';

  @override
  Future<CloudAudio> synthesize({
    required String text,
    required String voice,
    String style = 'neutral',
  }) async {
    if (text.trim().isEmpty) {
      throw const CloudTtsException('Azure recibió un texto vacío.');
    }
    if (!allowedStyles.contains(style)) {
      throw CloudTtsException('Azure no admite el estilo "$style".');
    }
    final ssml = buildSsml(text: text, voice: voice, style: style);
    final response = await _dio.post<List<int>>(
      'https://$region.tts.speech.microsoft.com/cognitiveservices/v1',
      data: utf8.encode(ssml),
      options: Options(
        headers: {
          'Ocp-Apim-Subscription-Key': apiKey,
          'Content-Type': 'application/ssml+xml',
          'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
          'User-Agent': 'vibebook-flutter',
        },
        responseType: ResponseType.bytes,
        validateStatus: (status) => status != null,
      ),
    );
    final status = response.statusCode ?? 0;
    if (status != 200) {
      final body = response.data;
      final detail = body == null
          ? null
          : utf8.decode(body, allowMalformed: true);
      throw CloudTtsException(
        cleanErrorMessage(
          httpErrorMessage('Azure Speech', status, detail: detail),
        ),
        statusCode: status,
      );
    }
    final data = response.data;
    if (data == null || data.isEmpty) {
      throw const CloudTtsException('Azure no devolvió audio.');
    }
    return CloudAudio(bytes: Uint8List.fromList(data), extension: 'mp3');
  }

  String buildSsml({
    required String text,
    required String voice,
    String style = 'neutral',
  }) {
    final parts = voice.split('-');
    final locale = parts.length >= 2 ? '${parts[0]}-${parts[1]}' : 'es-ES';
    final inner = '<prosody rate="+0%">${xmlEscape(text)}</prosody>';
    final styled = style == 'neutral'
        ? inner
        : '<mstts:express-as style="${xmlEscape(style)}" styledegree="1.2">'
              '$inner</mstts:express-as>';
    return '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        'xml:lang="${xmlEscape(locale)}">'
        '<voice name="${xmlEscape(voice)}">$styled</voice>'
        '</speak>';
  }
}
