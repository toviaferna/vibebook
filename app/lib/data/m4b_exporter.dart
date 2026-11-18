import 'dart:io';

import 'package:ffmpeg_kit_flutter_new_audio/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_audio/return_code.dart';
import 'package:path/path.dart' as p;

import '../core/text.dart';
import '../domain/models.dart';

class M4bExportResult {
  const M4bExportResult({required this.path, required this.logs});

  final String path;
  final String logs;
}

class _ChapterSource {
  const _ChapterSource({
    required this.path,
    required this.durationMs,
    required this.title,
  });

  final String path;
  final int durationMs;
  final String title;
}

class M4bExporter {
  const M4bExporter();

  Future<M4bExportResult> export(Book book, {String? outputPath}) async {
    final directory = book.directoryPath;
    if (directory == null) {
      throw StateError('El libro no tiene carpeta de biblioteca.');
    }
    final chapters = book.chapters.where((chapter) => chapter.audio != null).toList(growable: false);
    if (chapters.isEmpty) {
      throw StateError('El libro no tiene audio para exportar.');
    }
    final sources = [
      for (final chapter in chapters)
        _ChapterSource(
          path: p.isAbsolute(chapter.audio!) ? chapter.audio! : p.join(directory, chapter.audio!),
          durationMs: chapter.durationMs ?? 1000,
          title: chapter.title,
        ),
    ];
    return _exportSources(
      book,
      directory,
      sources,
      outputPath: outputPath ?? p.join(directory, '${slugify(book.title)}.m4b'),
    );
  }

  /// Mixes a looping ambience bed under each chapter and exports the result.
  Future<M4bExportResult> exportWithAmbience(
    Book book, {
    required String bedPath,
    String? outputPath,
    void Function(int chapter, int total)? onProgress,
  }) async {
    final directory = book.directoryPath;
    if (directory == null) {
      throw StateError('El libro no tiene carpeta de biblioteca.');
    }
    if (!await File(bedPath).exists()) {
      throw StateError('No se encontró la cama de ambiente.');
    }
    final chapters = book.chapters.where((chapter) => chapter.audio != null).toList(growable: false);
    if (chapters.isEmpty) {
      throw StateError('El libro no tiene audio para exportar.');
    }
    final work = Directory(p.join(directory, '.m4b-export'));
    await work.create(recursive: true);
    final sources = <_ChapterSource>[];
    for (var index = 0; index < chapters.length; index++) {
      final chapter = chapters[index];
      final voice = p.isAbsolute(chapter.audio!)
          ? chapter.audio!
          : p.join(directory, chapter.audio!);
      final durationMs = chapter.durationMs ?? 1000;
      final durationSeconds = (durationMs / 1000).clamp(0.1, 36000.0);
      final fadeOutStart = (durationSeconds - 2).clamp(0.0, durationSeconds);
      final fadeOutDuration = durationSeconds < 2 ? durationSeconds : 2.0;
      final mixed = p.join(
        work.path,
        'ambient_${(index + 1).toString().padLeft(3, '0')}.m4a',
      );
      final filter = [
        '[0:a]aformat=sample_rates=48000:channel_layouts=mono,'
            'atrim=0:${durationSeconds.toStringAsFixed(3)},asetpts=PTS-STARTPTS,'
            'volume=0.08,'
            'afade=t=in:st=0:d=${(durationSeconds < 1.5 ? durationSeconds : 1.5).toStringAsFixed(3)},'
            'afade=t=out:st=${fadeOutStart.toStringAsFixed(3)}:d=${fadeOutDuration.toStringAsFixed(3)}[bed]',
        '[1:a]aformat=sample_rates=48000:channel_layouts=mono,asplit=2[voice][voice_sidechain]',
        '[bed][voice_sidechain]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked]',
        '[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=0.9[out]',
      ].join(';\n');
      final filterFile = File(
        p.join(work.path, 'ambient_${(index + 1).toString().padLeft(3, '0')}.filter'),
      );
      await filterFile.writeAsString(filter, flush: true);
      final command = [
        '-y',
        '-hide_banner',
        '-loglevel',
        'error',
        '-stream_loop',
        '-1',
        '-i',
        _quote(bedPath),
        '-i',
        _quote(voice),
        '-filter_complex_script',
        _quote(filterFile.path),
        '-map',
        '[out]',
        '-t',
        durationSeconds.toStringAsFixed(3),
        '-c:a',
        'aac',
        '-b:a',
        '96k',
        '-ar',
        '48000',
        '-ac',
        '1',
        _quote(mixed),
      ].join(' ');
      await _run(command, 'No se pudo mezclar el capítulo ${chapter.index}.');
      sources.add(
        _ChapterSource(path: mixed, durationMs: durationMs, title: chapter.title),
      );
      onProgress?.call(index + 1, chapters.length);
    }
    return _exportSources(
      book,
      directory,
      sources,
      outputPath: outputPath ?? p.join(directory, '${slugify(book.title)}-ambientado.m4b'),
      work: work,
    );
  }

  Future<M4bExportResult> _exportSources(
    Book book,
    String directory,
    List<_ChapterSource> sources, {
    required String outputPath,
    Directory? work,
  }) async {
    final workDirectory = work ?? Directory(p.join(directory, '.m4b-export'));
    await workDirectory.create(recursive: true);
    final concat = File(p.join(workDirectory.path, 'concat.txt'));
    final metadata = File(p.join(workDirectory.path, 'metadata.txt'));
    final buffer = StringBuffer();
    for (final source in sources) {
      final normalized = source.path.replaceAll(r'\', '/').replaceAll("'", r"'\''");
      buffer.writeln("file '$normalized'");
    }
    await concat.writeAsString(buffer.toString(), flush: true);
    final meta = StringBuffer()
      ..writeln(';FFMETADATA1')
      ..writeln('title=${_escape(book.title)}')
      ..writeln('artist=${_escape(book.author)}');
    var cursor = 0;
    for (final source in sources) {
      meta
        ..writeln('[CHAPTER]')
        ..writeln('TIMEBASE=1/1000')
        ..writeln('START=$cursor')
        ..writeln('END=${cursor + source.durationMs}')
        ..writeln('title=${_escape(source.title)}');
      cursor += source.durationMs;
    }
    await metadata.writeAsString(meta.toString(), flush: true);
    final command = [
      '-y',
      '-hide_banner',
      '-loglevel',
      'error',
      '-f',
      'concat',
      '-safe',
      '0',
      '-i',
      _quote(concat.path),
      '-i',
      _quote(metadata.path),
      '-map_metadata',
      '1',
      '-c:a',
      'aac',
      '-b:a',
      '64k',
      '-movflags',
      '+faststart',
      _quote(outputPath),
    ].join(' ');
    final session = await FFmpegKit.execute(command);
    final returnCode = await session.getReturnCode();
    final logs = await session.getAllLogsAsString() ?? '';
    if (!ReturnCode.isSuccess(returnCode)) {
      throw StateError('FFmpeg no pudo exportar el M4B.\n$logs');
    }
    return M4bExportResult(path: outputPath, logs: logs);
  }

  Future<void> _run(String command, String errorMessage) async {
    final session = await FFmpegKit.execute(command);
    final returnCode = await session.getReturnCode();
    if (!ReturnCode.isSuccess(returnCode)) {
      final logs = await session.getAllLogsAsString() ?? '';
      throw StateError('$errorMessage\n$logs');
    }
  }

  String _quote(String value) => '"${value.replaceAll('"', r'\"')}"';

  String _escape(String value) {
    return value
        .replaceAll(r'\', r'\\')
        .replaceAll('\n', ' ')
        .replaceAll('\r', ' ')
        .replaceAll('=', r'\=')
        .replaceAll(';', r'\;')
        .replaceAll('#', r'\#');
  }
}
