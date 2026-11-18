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
    final work = Directory(p.join(directory, '.m4b-export'));
    await work.create(recursive: true);
    final concat = File(p.join(work.path, 'concat.txt'));
    final metadata = File(p.join(work.path, 'metadata.txt'));
    final buffer = StringBuffer();
    for (final chapter in chapters) {
      final audio = chapter.audio!;
      final path = p.isAbsolute(audio) ? audio : p.join(directory, audio);
      final normalized = path.replaceAll(r'\', '/').replaceAll("'", r"'\''");
      buffer.writeln("file '$normalized'");
    }
    await concat.writeAsString(buffer.toString(), flush: true);
    final meta = StringBuffer()
      ..writeln(';FFMETADATA1')
      ..writeln('title=${_escape(book.title)}')
      ..writeln('artist=${_escape(book.author)}');
    var cursor = 0;
    for (final chapter in chapters) {
      final duration = chapter.durationMs ?? 1000;
      meta
        ..writeln('[CHAPTER]')
        ..writeln('TIMEBASE=1/1000')
        ..writeln('START=$cursor')
        ..writeln('END=${cursor + duration}')
        ..writeln('title=${_escape(chapter.title)}');
      cursor += duration;
    }
    await metadata.writeAsString(meta.toString(), flush: true);
    final target = outputPath ?? p.join(directory, '${slugify(book.title)}.m4b');
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
      _quote(target),
    ].join(' ');
    final session = await FFmpegKit.execute(command);
    final returnCode = await session.getReturnCode();
    final logs = await session.getAllLogsAsString() ?? '';
    if (!ReturnCode.isSuccess(returnCode)) {
      throw StateError('FFmpeg no pudo exportar el M4B.\n$logs');
    }
    return M4bExportResult(path: target, logs: logs);
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
