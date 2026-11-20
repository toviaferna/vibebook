import 'dart:convert';
import 'dart:io';

import 'package:ffmpeg_kit_flutter_new_audio/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_audio/return_code.dart';
import 'package:path/path.dart' as p;

import '../../domain/models.dart';
import 'chapter_synthesizer.dart';
import 'timing_builder.dart';
import 'wav_writer.dart';

class TtsConversionProgress {
  const TtsConversionProgress({
    required this.chapterIndex,
    required this.chapterTotal,
    required this.fraction,
    required this.message,
  });

  final int chapterIndex;
  final int chapterTotal;
  final double fraction;
  final String message;
}

class TtsConversionCancelled implements Exception {
  const TtsConversionCancelled();
}

/// Converts every chapter with the configured [ChapterSynthesizer].
class TtsConversionService {
  const TtsConversionService();

  Future<Book> convert(
    Book book, {
    required ChapterSynthesizer synthesizer,
    Map<String, String> manifestExtra = const {},
    double speed = 1.0,
    int? maxChapters,
    bool compressAudio = true,
    bool resume = false,
    String? style,
    bool Function()? isCancelled,
    void Function(TtsConversionProgress progress)? onProgress,
  }) async {
    final directory = book.directoryPath;
    if (directory == null) {
      throw StateError('El libro no tiene una carpeta de biblioteca.');
    }
    final manifestFile = File(p.join(directory, 'manifest.json'));
    final manifest =
        jsonDecode(await manifestFile.readAsString()) as Map<String, dynamic>;
    final rawChapters = manifest['chapters'];
    if (rawChapters is! List) {
      throw StateError('El manifiesto no tiene capítulos.');
    }
    final chapters = book.chapters
        .take(maxChapters ?? book.chapters.length)
        .toList(growable: false);
    if (chapters.isEmpty) {
      throw StateError('El libro no tiene capítulos para convertir.');
    }
    final audioDirectory = Directory(p.join(directory, 'audio', 'chapters'));
    final timingDirectory = Directory(p.join(directory, 'timings'));
    final temporaryDirectory = Directory(p.join(directory, 'audio', '.tmp'));
    await audioDirectory.create(recursive: true);
    await timingDirectory.create(recursive: true);
    await temporaryDirectory.create(recursive: true);

    manifest['status'] = 'converting';
    final previousEngine = manifest['engine'];
    final previousVoice = manifest['voice'];
    final previousStyle = manifest['style'];
    final previousRate = manifest['rate'];
    manifest['engine'] = synthesizer.engineId;
    manifest['voice'] = synthesizer.voiceId;
    if (style != null) {
      manifest['style'] = style;
    }
    manifest.addAll(manifestExtra);
    manifest['rate'] = '${((speed - 1) * 100).round()}%';
    manifest['updated_at'] = _now();
    await _writeManifest(manifestFile, manifest);

    final wavWriter = const WavWriter();
    final timingBuilder = const TimingBuilder();
    var totalDuration = 0;
    var completed = 0;
    for (final chapter in chapters) {
      if (isCancelled?.call() ?? false) {
        manifest['status'] = 'interrupted';
        await _writeManifest(manifestFile, manifest);
        throw const TtsConversionCancelled();
      }
      final chapterMap = _chapterMap(rawChapters, chapter.index);
      if (chapterMap == null) {
        throw StateError(
          'El manifiesto no contiene el capítulo ${chapter.index}.',
        );
      }
      if (resume &&
          _canResume(
            chapterMap: chapterMap,
            manifest: {
              'engine': previousEngine,
              'voice': previousVoice,
              'style': previousStyle,
              'rate': previousRate,
            },
            directory: directory,
            synthesizer: synthesizer,
            speed: speed,
            style: style,
          )) {
        final duration = (chapterMap['duration_ms'] as num?)?.toInt() ?? 0;
        totalDuration += duration;
        completed += 1;
        manifest['duration_ms'] = totalDuration;
        manifest['progress'] = {
          'chapters_done': completed,
          'chapters_total': chapters.length,
          'updated_at': _now(),
        };
        await _writeManifest(manifestFile, manifest);
        onProgress?.call(
          TtsConversionProgress(
            chapterIndex: chapter.index,
            chapterTotal: chapters.length,
            fraction: completed / chapters.length,
            message: 'Capítulo ${chapter.index} ya estaba listo.',
          ),
        );
        continue;
      }
      onProgress?.call(
        TtsConversionProgress(
          chapterIndex: chapter.index,
          chapterTotal: chapters.length,
          fraction: completed / chapters.length,
          message:
              'Sintetizando capítulo ${chapter.index} de ${chapters.length}…',
        ),
      );
      final segmentTexts = {
        for (final segment in chapter.segments) segment.id: segment.text,
      };
      final ChapterSynthesis synthesis;
      try {
        synthesis = await synthesizer.synthesize(
          chapter,
          speed: speed,
          isCancelled: () => isCancelled?.call() ?? false,
        );
      } on SynthesisCancelled {
        manifest['status'] = 'interrupted';
        await _writeManifest(manifestFile, manifest);
        throw const TtsConversionCancelled();
      }
      final samples = synthesis.samples;
      final sampleRate = synthesis.sampleRate;
      if (samples.isEmpty) {
        throw StateError(
          'No se generó audio para el capítulo ${chapter.index}.',
        );
      }
      final durationMs = (samples.length * 1000 / sampleRate).round();
      final padded = chapter.index.toString().padLeft(3, '0');
      final wavFile = File(
        p.join(temporaryDirectory.path, 'chapter_$padded.wav'),
      );
      await wavFile.writeAsBytes(
        wavWriter.encode(samples, sampleRate),
        flush: true,
      );

      var audioRelative = 'audio/chapters/chapter_$padded.wav';
      final mp3File = File(p.join(audioDirectory.path, 'chapter_$padded.mp3'));
      if (compressAudio) {
        final encoded = await _encodeMp3(wavFile, mp3File, sampleRate);
        if (encoded) {
          audioRelative = 'audio/chapters/chapter_$padded.mp3';
          await wavFile.delete();
        }
      }
      if (!await File(p.join(directory, audioRelative)).exists()) {
        final fallback = File(
          p.join(audioDirectory.path, 'chapter_$padded.wav'),
        );
        await wavFile.copy(fallback.path);
        audioRelative = 'audio/chapters/chapter_$padded.wav';
      }

      final timing = timingBuilder.build(
        chapterIndex: chapter.index,
        segmentTexts: segmentTexts,
        spans: synthesis.spans,
        durationMs: durationMs,
        wordTimings: synthesis.wordTimings,
        precision: synthesis.wordTimings.isEmpty ? 'estimated' : 'native_word',
      );
      final timingName = 'chapter_$padded.json';
      final timingFile = File(p.join(timingDirectory.path, timingName));
      await timingFile.writeAsString(
        const JsonEncoder.withIndent('  ').convert(timing.toJson()),
        flush: true,
      );

      chapterMap
        ..['audio'] = audioRelative
        ..['timing'] = 'timings/$timingName'
        ..['duration_ms'] = durationMs
        ..['tts_precision'] = synthesis.wordTimings.isEmpty
            ? 'estimated'
            : 'native_word';
      totalDuration += durationMs;
      completed += 1;
      manifest['duration_ms'] = totalDuration;
      manifest['progress'] = {
        'chapters_done': completed,
        'chapters_total': chapters.length,
        'updated_at': _now(),
      };
      await _writeManifest(manifestFile, manifest);
      onProgress?.call(
        TtsConversionProgress(
          chapterIndex: chapter.index,
          chapterTotal: chapters.length,
          fraction: completed / chapters.length,
          message: 'Capítulo ${chapter.index} listo.',
        ),
      );
    }

    manifest['status'] = completed == book.chapters.length
        ? 'ready'
        : 'converting';
    manifest['duration_ms'] = totalDuration;
    manifest['engine'] = synthesizer.engineId;
    manifest['voice'] = synthesizer.voiceId;
    manifest['updated_at'] = _now();
    await _writeManifest(manifestFile, manifest);
    await _deleteIfEmpty(temporaryDirectory);

    return Book.fromJsonString(
      await manifestFile.readAsString(),
      id: book.id,
      manifestPath: manifestFile.path,
      directoryPath: directory,
    );
  }

  Future<bool> _encodeMp3(File input, File output, int sampleRate) async {
    try {
      final command = [
        '-y',
        '-hide_banner',
        '-loglevel',
        'error',
        '-i',
        _quote(input.path),
        '-codec:a',
        'libmp3lame',
        '-b:a',
        '64k',
        '-ar',
        '$sampleRate',
        '-ac',
        '1',
        _quote(output.path),
      ].join(' ');
      final session = await FFmpegKit.execute(command);
      final code = await session.getReturnCode();
      return ReturnCode.isSuccess(code) &&
          await output.exists() &&
          await output.length() > 0;
    } catch (_) {
      return false;
    }
  }

  Future<void> _writeManifest(File file, Map<String, dynamic> manifest) async {
    manifest['updated_at'] = _now();
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(manifest),
      flush: true,
    );
  }

  Future<void> _deleteIfEmpty(Directory directory) async {
    if (!await directory.exists()) {
      return;
    }
    if (await directory.list().isEmpty) {
      await directory.delete();
    }
  }

  Map<String, dynamic>? _chapterMap(List<dynamic> rawChapters, int index) {
    for (final item in rawChapters) {
      if (item is Map<String, dynamic> && item['index'] == index) {
        return item;
      }
    }
    return null;
  }

  bool _canResume({
    required Map<String, dynamic> chapterMap,
    required Map<String, dynamic> manifest,
    required String directory,
    required ChapterSynthesizer synthesizer,
    required double speed,
    required String? style,
  }) {
    final audio = chapterMap['audio'];
    final timing = chapterMap['timing'];
    if (audio is! String || timing is! String) {
      return false;
    }
    if (chapterMap['duration_ms'] is! num) {
      return false;
    }
    if (!File(p.join(directory, audio)).existsSync()) {
      return false;
    }
    if (!File(p.join(directory, timing)).existsSync()) {
      return false;
    }
    if (manifest['engine'] != synthesizer.engineId ||
        manifest['voice'] != synthesizer.voiceId) {
      return false;
    }
    if (!_ratesMatch(manifest['rate'], speed)) {
      return false;
    }
    if (style != null && manifest['style'] != style) {
      return false;
    }
    return true;
  }

  bool _ratesMatch(Object? value, double speed) {
    if (value is! String) {
      return false;
    }
    final parsed = int.tryParse(
      value.replaceAll('%', '').replaceAll('+', '').trim(),
    );
    return parsed == ((speed - 1) * 100).round();
  }

  String _quote(String value) => '"${value.replaceAll('"', r'\"')}"';

  String _now() => DateTime.now().toUtc().toIso8601String();
}
