import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path/path.dart' as p;

import '../domain/models.dart';

class DemoConversionService {
  const DemoConversionService();

  Future<Book> convert(
    Book book, {
    required String engine,
    required String voice,
    required String rate,
    void Function(int chapter, int total)? onProgress,
  }) async {
    final directory = book.directoryPath;
    if (directory == null) {
      throw StateError('El libro no tiene una carpeta de biblioteca.');
    }
    final chaptersDirectory = Directory(p.join(directory, 'audio', 'chapters'));
    await chaptersDirectory.create(recursive: true);
    final manifestFile = File(p.join(directory, 'manifest.json'));
    final manifest = jsonDecode(await manifestFile.readAsString()) as Map<String, dynamic>;
    final chapters = manifest['chapters'];
    if (chapters is! List) {
      throw StateError('El manifiesto no tiene capítulos.');
    }
    var totalDuration = 0;
    for (var index = 0; index < chapters.length; index++) {
      final chapter = chapters[index];
      if (chapter is! Map<String, dynamic>) {
        continue;
      }
      final chapterIndex = (chapter['index'] as num?)?.toInt() ?? index + 1;
      final segments = chapter['segments'];
      final text = segments is List
          ? segments
              .whereType<Map<String, dynamic>>()
              .map((segment) => segment['text'] as String? ?? '')
              .join(' ')
          : '';
      final durationMs = (text.length * 45).clamp(1200, 8000);
      final filename = 'chapter_${chapterIndex.toString().padLeft(3, '0')}.wav';
      final file = File(p.join(chaptersDirectory.path, filename));
      await file.writeAsBytes(_silenceWav(durationMs), flush: true);
      chapter['audio'] = p.posix.join('audio', 'chapters', filename);
      chapter['timing'] = null;
      chapter['duration_ms'] = durationMs;
      totalDuration += durationMs;
      onProgress?.call(index + 1, chapters.length);
    }
    manifest['status'] = 'ready';
    manifest['engine'] = engine;
    manifest['voice'] = voice;
    manifest['rate'] = rate;
    manifest['duration_ms'] = totalDuration;
    manifest['updated_at'] = DateTime.now().toUtc().toIso8601String();
    await manifestFile.writeAsString(const JsonEncoder.withIndent('  ').convert(manifest), flush: true);
    return Book.fromJsonString(
      await manifestFile.readAsString(),
      id: book.id,
      manifestPath: manifestFile.path,
      directoryPath: directory,
    );
  }

  Uint8List _silenceWav(int durationMs) {
    const sampleRate = 24000;
    const channels = 1;
    const bitsPerSample = 16;
    final frames = (sampleRate * durationMs / 1000).round();
    final dataSize = frames * channels * bitsPerSample ~/ 8;
    final bytes = BytesBuilder();
    void writeString(String value) => bytes.add(ascii.encode(value));
    void writeInt(int value, int size) {
      final data = ByteData(size);
      if (size == 2) {
        data.setUint16(0, value, Endian.little);
      } else {
        data.setUint32(0, value, Endian.little);
      }
      bytes.add(data.buffer.asUint8List());
    }

    writeString('RIFF');
    writeInt(36 + dataSize, 4);
    writeString('WAVE');
    writeString('fmt ');
    writeInt(16, 4);
    writeInt(1, 2);
    writeInt(channels, 2);
    writeInt(sampleRate, 4);
    writeInt(sampleRate * channels * bitsPerSample ~/ 8, 4);
    writeInt(channels * bitsPerSample ~/ 8, 2);
    writeInt(bitsPerSample, 2);
    writeString('data');
    writeInt(dataSize, 4);
    bytes.add(Uint8List(dataSize));
    return bytes.toBytes();
  }
}
