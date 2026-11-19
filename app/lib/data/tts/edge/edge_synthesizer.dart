import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:ffmpeg_kit_flutter_new_audio/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_audio/return_code.dart';
import 'package:path/path.dart' as p;

import '../../../domain/models.dart';
import '../chapter_synthesizer.dart';
import 'edge_client.dart';

/// [ChapterSynthesizer] over the Edge Read Aloud service.
///
/// Each paragraph is one request, so word boundaries map directly to the
/// chapter timeline. Failures retry with the same backoff the Python app
/// uses (`convert.py`: five attempts, two seconds doubling) and a no-audio
/// turn waits the cooldown ladder of `edge.py` (60 s doubling, four times).
class EdgeSynthesizer implements ChapterSynthesizer {
  EdgeSynthesizer({
    required this.client,
    required this.voiceId,
    Future<Float32List> Function(Uint8List mp3)? decodeMp3,
    Future<void> Function(Duration delay)? delay,
  }) : _decode = decodeMp3 ?? decodeEdgeMp3,
       _delay = delay ?? _sleep;

  static const sampleRate = 24000;
  static const _maxAttempts = 5;
  static const _maxCooldowns = 4;

  final EdgeTtsClient client;
  final Future<Float32List> Function(Uint8List mp3) _decode;
  final Future<void> Function(Duration delay) _delay;

  @override
  String get engineId => 'edge';

  @override
  final String voiceId;

  static Future<void> _sleep(Duration delay) => Future<void>.delayed(delay);

  @override
  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  }) async {
    final rate = _rateFromSpeed(speed);
    final parts = <Float32List>[];
    final spans = <Map<String, dynamic>>[];
    final wordTimings = <Map<String, dynamic>>[];
    var cursor = 0;
    final segments = chapter.segments
        .where((segment) => segment.text.trim().isNotEmpty)
        .toList(growable: false);
    for (var index = 0; index < segments.length; index++) {
      if (isCancelled()) {
        throw const SynthesisCancelled();
      }
      final segment = segments[index];
      final audio = await _synthesizeWithRetries(segment.text, rate);
      if (isCancelled()) {
        throw const SynthesisCancelled();
      }
      final samples = await _decode(audio.bytes);
      if (samples.isEmpty) {
        throw StateError(
          'Edge devolvió audio ilegible para el segmento ${segment.id}.',
        );
      }
      final startMs = (cursor * 1000 / sampleRate).round();
      parts.add(samples);
      cursor += samples.length;
      final endMs = (cursor * 1000 / sampleRate).round();
      spans.add({'id': segment.id, 'start_ms': startMs, 'end_ms': endMs});
      wordTimings.add({
        'id': segment.id,
        'words': [
          for (final word in audio.words)
            {
              'text': word.text,
              'start_ms': startMs + (word.offset / 10000).round(),
              'end_ms':
                  startMs + ((word.offset + word.duration) / 10000).round(),
            },
        ],
      });
      if (index < segments.length - 1) {
        final pauseMs = segment.boundary == 'paragraph' ? 190 : 90;
        final pauseFrames = sampleRate * pauseMs ~/ 1000;
        parts.add(Float32List(pauseFrames));
        cursor += pauseFrames;
      }
    }
    final total = parts.fold<int>(0, (sum, part) => sum + part.length);
    final merged = Float32List(total);
    var offset = 0;
    for (final part in parts) {
      merged.setAll(offset, part);
      offset += part.length;
    }
    return ChapterSynthesis(
      samples: merged,
      sampleRate: sampleRate,
      spans: spans,
      wordTimings: wordTimings,
    );
  }

  String _rateFromSpeed(double speed) {
    final percent = ((speed - 1) * 100).round();
    return '${percent >= 0 ? '+' : ''}$percent%';
  }

  Future<_EdgeAudio> _synthesizeWithRetries(String text, String rate) async {
    var attempt = 0;
    var cooldowns = 0;
    while (true) {
      attempt += 1;
      try {
        final bytes = BytesBuilder(copy: false);
        final words = <EdgeWordBoundaryEvent>[];
        await for (final event in client.synthesize(
          text: text,
          voice: voiceId,
          rate: rate,
        )) {
          if (event is EdgeAudioEvent) {
            bytes.add(event.data);
          } else if (event is EdgeWordBoundaryEvent) {
            words.add(event);
          }
        }
        return _EdgeAudio(bytes.takeBytes(), words);
      } on EdgeNoAudioException {
        cooldowns += 1;
        if (cooldowns > _maxCooldowns) {
          rethrow;
        }
        await _delay(Duration(seconds: 60 * (1 << (cooldowns - 1))));
      } catch (_) {
        if (attempt >= _maxAttempts) {
          rethrow;
        }
        await _delay(Duration(seconds: 2 * (1 << (attempt - 1))));
      }
    }
  }
}

class _EdgeAudio {
  const _EdgeAudio(this.bytes, this.words);

  final Uint8List bytes;
  final List<EdgeWordBoundaryEvent> words;
}

/// Decodes an Edge MP3 (24 kHz mono) into float samples.
Future<Float32List> decodeEdgeMp3(
  Uint8List mp3, {
  Directory? workDirectory,
}) async {
  final work = workDirectory ?? Directory.systemTemp;
  await work.create(recursive: true);
  final stamp = DateTime.now().microsecondsSinceEpoch;
  final suffix = Random().nextInt(0x7fffffff).toRadixString(36);
  final mp3File = File(p.join(work.path, 'edge-$stamp-$suffix.mp3'));
  final rawFile = File(p.join(work.path, 'edge-$stamp-$suffix.raw'));
  try {
    await mp3File.writeAsBytes(mp3, flush: true);
    final command = [
      '-y',
      '-hide_banner',
      '-loglevel',
      'error',
      '-i',
      '"${mp3File.path}"',
      '-f',
      's16le',
      '-acodec',
      'pcm_s16le',
      '-ar',
      '24000',
      '-ac',
      '1',
      '"${rawFile.path}"',
    ].join(' ');
    final session = await FFmpegKit.execute(command);
    final code = await session.getReturnCode();
    if (!ReturnCode.isSuccess(code)) {
      final logs = await session.getAllLogsAsString() ?? '';
      throw StateError('FFmpeg no pudo decodificar el audio de Edge.\n$logs');
    }
    final raw = await rawFile.readAsBytes();
    final samples = Float32List(raw.length ~/ 2);
    final data = ByteData.sublistView(raw);
    for (var index = 0; index < samples.length; index++) {
      samples[index] = data.getInt16(index * 2, Endian.little) / 32768;
    }
    return samples;
  } finally {
    await mp3File.delete().catchError((_) => mp3File);
    await rawFile.delete().catchError((_) => rawFile);
  }
}
