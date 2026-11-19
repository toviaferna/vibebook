import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/tts/chapter_synthesizer.dart';
import 'package:vibebook_app/data/tts/tts_conversion.dart';
import 'package:vibebook_app/domain/models.dart';

class _CountingSynthesizer implements ChapterSynthesizer {
  int calls = 0;

  @override
  String get engineId => 'piper';

  @override
  String get voiceId => 'es_MX-ald-medium';

  @override
  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  }) async {
    calls += 1;
    return ChapterSynthesis(
      samples: Float32List(24000),
      sampleRate: 24000,
      spans: [
        {'id': chapter.segments.first.id, 'start_ms': 0, 'end_ms': 1000},
      ],
      wordTimings: const [],
    );
  }
}

void main() {
  late Directory temp;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-resume-');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  Future<Book> prepareBook() async {
    final audio = File(
      p.join(temp.path, 'audio', 'chapters', 'chapter_001.mp3'),
    );
    await audio.parent.create(recursive: true);
    await audio.writeAsBytes([0x49, 0x44, 0x33]);
    final timing = File(p.join(temp.path, 'timings', 'chapter_001.json'));
    await timing.parent.create(recursive: true);
    await timing.writeAsString('{"segments":[]}');
    final manifest = {
      'schema_version': 2,
      'id': 'book-1',
      'title': 'Un libro',
      'author': 'Autora',
      'language': 'es',
      'status': 'imported',
      'engine': 'piper',
      'voice': 'es_MX-ald-medium',
      'style': 'neutral',
      'rate': '-10%',
      'chapters': [
        {
          'index': 1,
          'title': 'Uno',
          'audio': 'audio/chapters/chapter_001.mp3',
          'timing': 'timings/chapter_001.json',
          'duration_ms': 1000,
          'segments': [
            {
              'id': 'c001p0001s00',
              'chapter_index': 1,
              'paragraph_index': 1,
              'text': 'Uno.',
            },
          ],
        },
      ],
    };
    await File(p.join(temp.path, 'manifest.json'))
        .writeAsString(const JsonEncoder.withIndent('  ').convert(manifest));
    return Book.fromJsonString(
      jsonEncode(manifest),
      id: 'book-1',
      manifestPath: p.join(temp.path, 'manifest.json'),
      directoryPath: temp.path,
    );
  }

  test(
    'reanuda sin volver a sintetizar un capítulo que ya está listo',
    () async {
      final book = await prepareBook();
      final synthesizer = _CountingSynthesizer();
      final result = await TtsConversionService().convert(
        book,
        synthesizer: synthesizer,
        speed: 0.9,
        resume: true,
        style: 'neutral',
      );
      expect(synthesizer.calls, 0);
      expect(result.durationMs, 1000);
      expect(result.status, 'ready');
      final manifest = jsonDecode(
        await File(p.join(temp.path, 'manifest.json')).readAsString(),
      ) as Map<String, dynamic>;
      expect(manifest['status'], 'ready');
      expect(
        File(p.join(temp.path, 'audio', 'chapters', 'chapter_001.mp3'))
            .existsSync(),
        isTrue,
      );
    },
  );

  test('sin resume vuelve a sintetizar el capítulo', () async {
    final book = await prepareBook();
    final synthesizer = _CountingSynthesizer();
    final result = await TtsConversionService().convert(
      book,
      synthesizer: synthesizer,
      speed: 0.9,
      resume: false,
      style: 'neutral',
      compressAudio: false,
    );
    expect(synthesizer.calls, 1);
    expect(result.durationMs, 1000);
    expect(result.chapters.single.audio, endsWith('.wav'));
  });

  test('no reanuda si cambió la voz', () async {
    final book = await prepareBook();
    final synthesizer = _CountingSynthesizer();
    // Change the voice stored in the manifest before converting.
    final manifestFile = File(p.join(temp.path, 'manifest.json'));
    final manifest =
        jsonDecode(await manifestFile.readAsString()) as Map<String, dynamic>;
    manifest['voice'] = 'otra-voz';
    await manifestFile.writeAsString(jsonEncode(manifest));
    final result = await TtsConversionService().convert(
      book,
      synthesizer: synthesizer,
      speed: 0.9,
      resume: true,
      style: 'neutral',
      compressAudio: false,
    );
    expect(synthesizer.calls, 1);
    expect(result.chapters.single.audio, endsWith('.wav'));
  });
}
