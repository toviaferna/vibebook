import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:ffmpeg_kit_flutter_new_audio/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_audio/return_code.dart';
import 'package:path/path.dart' as p;
import 'package:piper_phonemize/piper_phonemize.dart';

import '../../domain/models.dart';
import 'piper_models.dart';
import 'timing_builder.dart';
import 'tts_chapter_worker.dart';
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

/// Converts every chapter with a local Piper voice.
class TtsConversionService {
  const TtsConversionService();

  Future<Book> convert(
    Book book, {
    required PiperModel model,
    required String espeakDataPath,
    double speed = 1.0,
    int? maxChapters,
    bool compressAudio = true,
    bool Function()? isCancelled,
    void Function(TtsConversionProgress progress)? onProgress,
  }) async {
    final directory = book.directoryPath;
    if (directory == null) {
      throw StateError('El libro no tiene una carpeta de biblioteca.');
    }
    if (!model.isValid) {
      throw StateError('El modelo Piper no está completo.');
    }
    final manifestFile = File(p.join(directory, 'manifest.json'));
    final manifest = jsonDecode(await manifestFile.readAsString()) as Map<String, dynamic>;
    final rawChapters = manifest['chapters'];
    if (rawChapters is! List) {
      throw StateError('El manifiesto no tiene capítulos.');
    }
    final chapters = book.chapters.take(maxChapters ?? book.chapters.length).toList(growable: false);
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
    manifest['engine'] = 'piper';
    manifest['voice'] = model.id;
    manifest['tts_model'] = model.id;
    manifest['tts_model_path'] = model.directory;
    manifest['rate'] = '${((speed - 1) * 100).round()}%';
    manifest['updated_at'] = _now();
    await _writeManifest(manifestFile, manifest);

    final wavWriter = const WavWriter();
    final timingBuilder = const TimingBuilder();
    var totalDuration = 0;
    var completed = 0;
    for (final chapter in chapters) {
      if (isCancelled?.call() ?? false) {
        manifest['status'] = 'imported';
        await _writeManifest(manifestFile, manifest);
        throw const TtsConversionCancelled();
      }
      onProgress?.call(
        TtsConversionProgress(
          chapterIndex: chapter.index,
          chapterTotal: chapters.length,
          fraction: completed / chapters.length,
          message: 'Sintetizando capítulo ${chapter.index} de ${chapters.length}…',
        ),
      );
      final segmentTexts = {
        for (final segment in chapter.segments) segment.id: segment.text,
      };
      final payload = <String, dynamic>{
        'model': {
          'model': model.modelPath,
          'tokens': model.tokensPath,
          'voice': model.espeakVoice,
          'noise_scale': model.noiseScale,
          'noise_w': model.noiseScaleW,
          'length_scale': model.lengthScale,
        },
        'espeak_data_path': espeakDataPath,
        'speed': speed,
        'segments': [
          for (final segment in chapter.segments)
            {
              'id': segment.id,
              'text': segment.text,
              'pause_after_ms': segment.boundary == 'paragraph' ? 190 : 90,
            },
        ],
      };
      final result = await renderChapterInBackground(payload);
      final samples = result['samples'] as Float32List;
      final sampleRate = (result['sample_rate'] as num?)?.toInt() ?? model.sampleRate;
      if (samples.isEmpty) {
        throw StateError('No se generó audio para el capítulo ${chapter.index}.');
      }
      final durationMs = (samples.length * 1000 / sampleRate).round();
      final padded = chapter.index.toString().padLeft(3, '0');
      final wavFile = File(p.join(temporaryDirectory.path, 'chapter_$padded.wav'));
      await wavFile.writeAsBytes(wavWriter.encode(samples, sampleRate), flush: true);

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
        final fallback = File(p.join(audioDirectory.path, 'chapter_$padded.wav'));
        await wavFile.copy(fallback.path);
        audioRelative = 'audio/chapters/chapter_$padded.wav';
      }

      final timing = timingBuilder.build(
        chapterIndex: chapter.index,
        segmentTexts: segmentTexts,
        spans: (result['spans'] as List<dynamic>).cast<Map<String, dynamic>>(),
        durationMs: durationMs,
      );
      final timingName = 'chapter_$padded.json';
      final timingFile = File(p.join(timingDirectory.path, timingName));
      await timingFile.writeAsString(
        const JsonEncoder.withIndent('  ').convert(timing.toJson()),
        flush: true,
      );

      Map<String, dynamic>? chapterMap;
      for (final item in rawChapters) {
        if (item is Map<String, dynamic> && item['index'] == chapter.index) {
          chapterMap = item;
          break;
        }
      }
      if (chapterMap == null) {
        throw StateError('El manifiesto no contiene el capítulo ${chapter.index}.');
      }
      chapterMap
        ..['audio'] = audioRelative
        ..['timing'] = 'timings/$timingName'
        ..['duration_ms'] = durationMs
        ..['tts_precision'] = 'estimated';
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

    manifest['status'] = completed == book.chapters.length ? 'ready' : 'converting';
    manifest['duration_ms'] = totalDuration;
    manifest['engine'] = 'piper';
    manifest['voice'] = model.id;
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
      return ReturnCode.isSuccess(code) && await output.exists() && await output.length() > 0;
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

  String _quote(String value) => '"${value.replaceAll('"', r'\"')}"';

  String _now() => DateTime.now().toUtc().toIso8601String();
}

Future<String> ensurePiperEspeakData() => extractEspeakNgData();
