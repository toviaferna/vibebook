import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/epub_ingestor.dart';
import 'package:vibebook_app/data/library_repository.dart';

void main() {
  test('importa un EPUB a la biblioteca y lo vuelve a leer', () async {
    final temp = await Directory.systemTemp.createTemp(
      'vibebook-flutter-test-',
    );
    addTearDown(() async {
      if (await temp.exists()) {
        await temp.delete(recursive: true);
      }
    });
    final repository = LibraryRepository(
      ingestor: const EpubIngestor(),
      libraryPath: temp.path,
    );
    final book = await repository.importEpub('test/fixtures/sample.epub');
    expect(book.title, isNotEmpty);
    expect(book.chapters, isNotEmpty);
    expect(book.directoryPath, isNotNull);
    expect(
      File(p.join(book.directoryPath!, 'manifest.json')).existsSync(),
      isTrue,
    );
    expect(
      File(p.join(book.directoryPath!, 'source.epub')).existsSync(),
      isTrue,
    );

    final scanned = await repository.scan();
    expect(scanned, hasLength(1));
    expect(scanned.first.title, book.title);

    final loaded = await repository.get(book.id);
    expect(loaded, isNotNull);
    expect(loaded!.title, book.title);
    expect(loaded.segmentCount, greaterThan(0));

    await repository.deleteBook(book.id);
    expect(await repository.get(book.id), isNull);
    expect(await repository.scan(), isEmpty);
    expect(await Directory(p.join(temp.path, book.id)).exists(), isFalse);
  });

  test('reemplaza la portada y actualiza el manifiesto', () async {
    final temp = await Directory.systemTemp.createTemp('vibebook-cover-test-');
    addTearDown(() async {
      if (await temp.exists()) {
        await temp.delete(recursive: true);
      }
    });
    final repository = LibraryRepository(
      ingestor: const EpubIngestor(),
      libraryPath: temp.path,
    );
    final book = await repository.importEpub('test/fixtures/sample.epub');
    final updated = await repository.setCover(
      book.id,
      Uint8List.fromList([1, 2, 3, 4]),
      extension: 'png',
    );
    expect(updated.cover, 'cover.png');
    final cover = File(p.join(book.directoryPath!, 'cover.png'));
    expect(cover.existsSync(), isTrue);
    expect(await cover.readAsBytes(), [1, 2, 3, 4]);
    final manifest = await File(p.join(book.directoryPath!, 'manifest.json'))
        .readAsString();
    expect(manifest, contains('cover.png'));
    expect(
      () => repository.setCover('../escape', Uint8List.fromList([1])),
      throwsA(isA<ArgumentError>()),
    );
    expect(
      () => repository.setCover(book.id, Uint8List(0)),
      throwsA(isA<FormatException>()),
    );
  });
}
