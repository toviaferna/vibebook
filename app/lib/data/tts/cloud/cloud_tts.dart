import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:ffmpeg_kit_flutter_new_audio/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_audio/return_code.dart';
import 'package:path/path.dart' as p;

/// One word with its position in the provider audio.
class CloudWordTiming {
  const CloudWordTiming({
    required this.text,
    required this.startMs,
    required this.endMs,
  });

  final String text;
  final int startMs;
  final int endMs;

  Map<String, dynamic> toJson() => {
    'text': text,
    'start_ms': startMs,
    'end_ms': endMs,
  };
}

/// Provider audio plus optional native word timings.
class CloudAudio {
  const CloudAudio({
    required this.bytes,
    required this.extension,
    this.words = const [],
  });

  final Uint8List bytes;

  /// `mp3` or `wav`.
  final String extension;
  final List<CloudWordTiming> words;
}

/// A cloud provider returned an error the UI can show verbatim.
class CloudTtsException implements Exception {
  const CloudTtsException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Shared contract for Azure, Gemini and ElevenLabs.
abstract class CloudTtsClient {
  String get providerId;

  /// Synthesizes one segment at the provider's neutral rate. The chapter
  /// synthesizer applies the user's speed once to the concatenated audio.
  Future<CloudAudio> synthesize({
    required String text,
    required String voice,
    String style = 'neutral',
  });
}

const cloudStyles = <String>[
  'neutral',
  'chat',
  'cheerful',
  'excited',
  'sad',
  'whispering',
  'epic',
  'suspense',
];

/// Validates and normalizes a rate such as `-10%` and returns the percent.
int parseRatePercent(String rate) {
  final cleaned = rate.trim();
  final match = RegExp(r'^([+-]?)(\d{1,3})%$').firstMatch(cleaned);
  if (match == null) {
    throw const CloudTtsException(
      'La velocidad debe tener el formato -10% o +5%.',
    );
  }
  final value = int.parse(match.group(2)!);
  final signed = match.group(1) == '-' ? -value : value;
  if (signed < -100 || signed > 100) {
    throw const CloudTtsException(
      'La velocidad debe estar entre -100% y +100%.',
    );
  }
  if (signed == -100) {
    throw const CloudTtsException(
      'No se puede sintetizar a -100% de velocidad.',
    );
  }
  return signed;
}

String formatRatePercent(double percent) {
  final rounded = percent.round();
  return '${rounded >= 0 ? '+' : ''}$rounded%';
}

String xmlEscape(String value) {
  return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&apos;');
}

/// Wraps raw 16-bit little-endian mono PCM in a WAV container.
Uint8List wrapPcm16({
  required Uint8List bytes,
  int sampleRate = 24000,
  int channels = 1,
}) {
  final byteRate = sampleRate * channels * 2;
  final header = ByteData(44);
  void ascii(int offset, String value) {
    for (var index = 0; index < value.length; index++) {
      header.setUint8(offset + index, value.codeUnitAt(index));
    }
  }

  ascii(0, 'RIFF');
  header.setUint32(4, 36 + bytes.length, Endian.little);
  ascii(8, 'WAVE');
  ascii(12, 'fmt ');
  header.setUint32(16, 16, Endian.little);
  header.setUint16(20, 1, Endian.little);
  header.setUint16(22, channels, Endian.little);
  header.setUint32(24, sampleRate, Endian.little);
  header.setUint32(28, byteRate, Endian.little);
  header.setUint16(32, channels * 2, Endian.little);
  header.setUint16(34, 16, Endian.little);
  ascii(36, 'data');
  header.setUint32(40, bytes.length, Endian.little);
  return Uint8List.fromList([...header.buffer.asUint8List(), ...bytes]);
}

/// Best-effort MIME/extension detection from the first bytes.
String audioExtension(Uint8List bytes) {
  if (bytes.length >= 4) {
    final magic = String.fromCharCodes(bytes.take(4));
    if (magic == 'RIFF') {
      return 'wav';
    }
    if (magic == 'OggS') {
      return 'ogg';
    }
    if (magic.startsWith('ID3') || bytes[0] == 0xFF) {
      return 'mp3';
    }
  }
  return 'wav';
}

/// Turns provider bytes into mono float PCM at [sampleRate].
///
/// The default uses FFmpegKit. Tests inject a fake so they do not need the
/// native library.
abstract class CloudAudioDecoder {
  Future<Float32List> decode(CloudAudio audio, {int sampleRate = 24000});

  Future<Float32List> applySpeed(
    Float32List samples, {
    required int sampleRate,
    required double speed,
  });
}

class FfmpegCloudAudioDecoder implements CloudAudioDecoder {
  const FfmpegCloudAudioDecoder();

  @override
  Future<Float32List> decode(CloudAudio audio, {int sampleRate = 24000}) async {
    final directory = await Directory.systemTemp.createTemp('vibebook-cloud-');
    try {
      final input = File(p.join(directory.path, 'audio.${audio.extension}'));
      final output = File(p.join(directory.path, 'audio.pcm'));
      await input.writeAsBytes(audio.bytes, flush: true);
      final session = await FFmpegKit.execute(
        '-y -hide_banner -loglevel error -i "${input.path}" '
        '-f f32le -ac 1 -ar $sampleRate "${output.path}"',
      );
      final code = await session.getReturnCode();
      if (!ReturnCode.isSuccess(code) || !await output.exists()) {
        throw const CloudTtsException(
          'No se pudo decodificar el audio del proveedor.',
        );
      }
      final bytes = await output.readAsBytes();
      return _float32FromBytes(bytes);
    } finally {
      await directory.delete(recursive: true).catchError((_) => directory);
    }
  }

  @override
  Future<Float32List> applySpeed(
    Float32List samples, {
    required int sampleRate,
    required double speed,
  }) async {
    if ((speed - 1).abs() < 0.001 || samples.isEmpty) {
      return samples;
    }
    if (speed <= 0) {
      throw const CloudTtsException('La velocidad debe ser mayor que cero.');
    }
    final directory = await Directory.systemTemp.createTemp('vibebook-rate-');
    try {
      final input = File(p.join(directory.path, 'in.wav'));
      final output = File(p.join(directory.path, 'out.pcm'));
      await input.writeAsBytes(_wavBytes(samples, sampleRate), flush: true);
      final filters = _atempoFilters(speed);
      final session = await FFmpegKit.execute(
        '-y -hide_banner -loglevel error -i "${input.path}" '
        '-filter:a "$filters" -f f32le -ac 1 -ar $sampleRate "${output.path}"',
      );
      final code = await session.getReturnCode();
      if (!ReturnCode.isSuccess(code) || !await output.exists()) {
        throw const CloudTtsException('No se pudo aplicar la velocidad.');
      }
      return _float32FromBytes(await output.readAsBytes());
    } finally {
      await directory.delete(recursive: true).catchError((_) => directory);
    }
  }

  String _atempoFilters(double speed) {
    var remaining = speed;
    final filters = <String>[];
    while (remaining > 2.0) {
      filters.add('atempo=2.0');
      remaining /= 2.0;
    }
    while (remaining < 0.5) {
      filters.add('atempo=0.5');
      remaining /= 0.5;
    }
    filters.add('atempo=${remaining.toStringAsFixed(4)}');
    return filters.join(',');
  }

  Uint8List _wavBytes(Float32List samples, int sampleRate) {
    final pcm = ByteData(samples.length * 2);
    for (var index = 0; index < samples.length; index++) {
      final clamped = samples[index].clamp(-1.0, 1.0);
      pcm.setInt16(index * 2, (clamped * 32767).round(), Endian.little);
    }
    return wrapPcm16(bytes: pcm.buffer.asUint8List(), sampleRate: sampleRate);
  }
}

Float32List _float32FromBytes(Uint8List bytes) {
  final usable = bytes.length - (bytes.length % 4);
  final copy = Uint8List.fromList(bytes.sublist(0, usable));
  return Float32List.view(copy.buffer, 0, usable ~/ 4);
}

/// Decodes a base64 audio block from Gemini.
CloudAudio decodeGeminiAudio(Map<String, dynamic> block) {
  final data = block['data'];
  if (data is! String || data.isEmpty) {
    throw const CloudTtsException('Gemini no devolvió audio.');
  }
  final Uint8List bytes;
  try {
    bytes = base64Decode(data);
  } on FormatException {
    throw const CloudTtsException('Gemini devolvió audio base64 inválido.');
  }
  final mime = (block['mime_type'] ?? block['mimeType'] ?? '').toString();
  if (mime.contains('l16')) {
    return CloudAudio(
      bytes: wrapPcm16(bytes: bytes),
      extension: 'wav',
    );
  }
  final magic = bytes.length >= 4 ? String.fromCharCodes(bytes.take(4)) : '';
  if (magic == 'RIFF' ||
      magic == 'OggS' ||
      magic.startsWith('ID3') ||
      (bytes.isNotEmpty && bytes[0] == 0xFF)) {
    return CloudAudio(bytes: bytes, extension: audioExtension(bytes));
  }
  return CloudAudio(
    bytes: wrapPcm16(bytes: bytes),
    extension: 'wav',
  );
}

String httpErrorMessage(String provider, int status, {String? detail}) {
  if (status == 401 || status == 403) {
    return 'La clave de $provider no es válida o no tiene permisos.';
  }
  if (status == 402) {
    return 'El plan de $provider no permite esta voz o modelo.';
  }
  if (status == 404) {
    return 'El modelo o la voz de $provider no existe.';
  }
  if (status == 429) {
    return '$provider aplicó un límite de solicitudes. Probá más tarde.';
  }
  if (status >= 500) {
    return '$provider no está disponible ahora (HTTP $status).';
  }
  final trimmed = detail?.trim();
  if (trimmed != null && trimmed.isNotEmpty) {
    final end = trimmed.length < 200 ? trimmed.length : 200;
    return '$provider respondió HTTP $status: ${trimmed.substring(0, end)}';
  }
  return '$provider respondió HTTP $status.';
}

String? errorDetail(Object? data) {
  if (data is Map) {
    final error = data['error'];
    if (error is Map && error['message'] is String) {
      return error['message'] as String;
    }
    if (data['detail'] is String) {
      return data['detail'] as String;
    }
    if (data['detail'] is Map && (data['detail'] as Map)['message'] is String) {
      return (data['detail'] as Map)['message'] as String;
    }
    if (data['message'] is String) {
      return data['message'] as String;
    }
  }
  if (data is String && data.trim().isNotEmpty) {
    return data;
  }
  return null;
}

String cleanErrorMessage(String message) {
  // Never echo a key if a provider includes it in an error body.
  final withoutKeys = message.replaceAll(
    RegExp(r'(api[_-]?key|key|token)\s*[=:]\s*\S+', caseSensitive: false),
    r'$1=***',
  );
  return withoutKeys.length > 300
      ? '${withoutKeys.substring(0, 300)}…'
      : withoutKeys;
}
