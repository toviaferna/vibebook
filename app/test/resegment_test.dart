import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/repair/resegment.dart';
import 'package:vibebook_app/domain/models.dart';

void _writeEpub(String path, String text) {
  final archive = Archive();
  void add(String name, String content) {
    final bytes = utf8.encode(content);
    archive.addFile(ArchiveFile(name, bytes.length, bytes));
  }

  add(
    'META-INF/container.xml',
    '<?xml version="1.0" encoding="UTF-8"?>'
        '<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles></container>',
  );
  add(
    'OEBPS/content.opf',
    '<?xml version="1.0" encoding="UTF-8"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="id">test</dc:identifier>'
        '<dc:title>Libro de prueba</dc:title>'
        '<dc:creator>Autora</dc:creator>'
        '<dc:language>es</dc:language></metadata>'
        '<manifest><item id="ch1" href="Text/ch1.xhtml" '
        'media-type="application/xhtml+xml"/></manifest>'
        '<spine><itemref idref="ch1"/></spine></package>',
  );
  add(
    'OEBPS/Text/ch1.xhtml',
    '<?xml version="1.0" encoding="UTF-8"?>'
        '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
        '<h1>Capítulo uno</h1><p>$text</p></body></html>',
  );
  File(path).writeAsBytesSync(ZipEncoder().encode(archive));
}

void main() {
  late Directory temp;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-resegment-');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  Future<Book> prepare({String text = 'Texto original.'}) async {
    _writeEpub(p.join(temp.path, 'source.epub'), text);
    final audio = File(
      p.join(temp.path, 'audio', 'chapters', 'chapter_001.mp3'),
    );
    await audio.parent.create(recursive: true);
    await audio.writeAsBytes([0x49, 0x44, 0x33]);
    final timing = File(p.join(temp.path, 'timings', 'chapter_001.json'));
    await timing.parent.create(recursive: true);
    await timing.writeAsString('{"segments":[]}');
    final manifest = {
      'id': 'book-1',
      'title': 'Libro de prueba',
      'author': 'Autora',
      'language': 'es',
      'status': 'ready',
      'engine': 'piper',
      'voice': 'es_MX-ald-medium',
      'style': 'neutral',
      'rate': '-10%',
      'segmentation_version': 2,
      'chapters': [
        {
          'index': 1,
          'title': 'Capítulo uno',
          'audio': 'audio/chapters/chapter_001.mp3',
          'timing': 'timings/chapter_001.json',
          'duration_ms': 1000,
          'segments': [
            {
              'id': 'c001p0001s00',
              'chapter_index': 1,
              'paragraph_index': 1,
              'text': 'Texto original.',
            },
          ],
        },
      ],
    };
    await File(p.join(temp.path, 'manifest.json'))
        .writeAsString(const JsonEncoder.withIndent('  ').convert(manifest));
    await File(p.join(temp.path, 'book.md')).writeAsString('# Libro\n');
    return Book.fromJsonString(
      jsonEncode(manifest),
      id: 'book-1',
      manifestPath: p.join(temp.path, 'manifest.json'),
      directoryPath: temp.path,
    );
  }

  test('detecta cambios y no escribe en dry-run', () async {
    final book = await prepare();
    _writeEpub(p.join(temp.path, 'source.epub'), 'Texto nuevo y más largo.');
    final service = const ResegmentService();
    final plan = await service.analyze(book);
    expect(plan.canRepair, isTrue);
    expect(plan.needsRepair, isTrue);
    expect(plan.changedSegments, 1);
    expect(plan.changedChapters, [1]);
    final dry = await service.apply(book, dryRun: true);
    expect(dry.changed, isTrue);
    expect(dry.dryRun, isTrue);
    final manifest = jsonDecode(
      await File(p.join(temp.path, 'manifest.json')).readAsString(),
    ) as Map<String, dynamic>;
    expect(manifest['segmentation_version'], 2);
  });

  test('aplica, marca el libro para re-síntesis y permite restaurar', () async {
    final book = await prepare();
    _writeEpub(p.join(temp.path, 'source.epub'), 'Texto nuevo y más largo.');
    final service = const ResegmentService();
    final result = await service.apply(book);
    expect(result.changed, isTrue);
    expect(result.backupId, isNotNull);
    final manifest = jsonDecode(
      await File(p.join(temp.path, 'manifest.json')).readAsString(),
    ) as Map<String, dynamic>;
    expect(manifest['segmentation_version'], 3);
    expect(manifest['status'], 'interrupted');
    final chapter =
        (manifest['chapters'] as List).single as Map<String, dynamic>;
    expect(chapter['audio'], isNull);
    expect(chapter['timing'], isNull);
    expect(
      (chapter['segments'] as List).single['text'],
      'Texto nuevo y más largo.',
    );
    final backups = await service.backups(book);
    expect(backups, hasLength(1));
    expect(backups.single.changedChapters, [1]);
    await service.restore(book, backups.single.id);
    final restored = jsonDecode(
      await File(p.join(temp.path, 'manifest.json')).readAsString(),
    ) as Map<String, dynamic>;
    expect(restored['status'], 'ready');
    expect(restored['segmentation_version'], 2);
    final restoredChapter =
        (restored['chapters'] as List).single as Map<String, dynamic>;
    expect(restoredChapter['audio'], 'audio/chapters/chapter_001.mp3');
  });

  test('no repara si falta el EPUB fuente', () async {
    final book = await prepare();
    File(p.join(temp.path, 'source.epub')).deleteSync();
    final plan = await const ResegmentService().analyze(book);
    expect(plan.canRepair, isFalse);
    expect(plan.reason, contains('EPUB fuente'));
  });

  test('rechaza ids de backup con traversal', () async {
    final book = await prepare();
    expect(
      () => const ResegmentService().restore(book, '../escape'),
      throwsA(isA<ResegmentException>()),
    );
  });
}
