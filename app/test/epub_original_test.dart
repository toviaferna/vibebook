import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/epub_original.dart';
import 'package:vibebook_app/domain/models.dart';

void main() {
  late Directory temp;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-original-');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  Book writeBook() {
    final archive = Archive();
    final html = utf8.encode(
      '<html><body><h1>Hola</h1>'
      '<p onclick="alert(1)">Texto <em>énfasis</em></p>'
      '<script>alert(1)</script>'
      '<img src="../Images/pic.png" onerror="alert(1)"/>'
      '</body></html>',
    );
    archive.addFile(ArchiveFile('OEBPS/Text/ch1.xhtml', html.length, html));
    archive.addFile(ArchiveFile('OEBPS/Images/pic.png', 4, [1, 2, 3, 4]));
    final bytes = ZipEncoder().encode(archive);
    File('${temp.path}/source.epub').writeAsBytesSync(bytes);
    return Book(
      id: 'b',
      title: 'Libro',
      author: 'Autora',
      language: 'es',
      sourceEpub: 'source.epub',
      directoryPath: temp.path,
      chapters: const [
        Chapter(
          index: 1,
          title: 'Uno',
          segments: [],
          sourceHref: 'OEBPS/Text/ch1.xhtml',
        ),
        Chapter(
          index: 2,
          title: 'Dos',
          segments: [],
          sourceHref: 'OEBPS/Text/ch2.xhtml',
        ),
      ],
    );
  }

  test('extrae y sanitiza el XHTML del capítulo', () async {
    final book = writeBook();
    final html = await EpubOriginal.chapterHtml(book, book.chapters.first);
    expect(html, isNotNull);
    expect(html, contains('Hola'));
    expect(html, contains('énfasis'));
    expect(html, isNot(contains('<script')));
    expect(html, isNot(contains('onclick')));
    expect(html, isNot(contains('onerror')));
  });

  test('resuelve imágenes relativas al capítulo', () async {
    final book = writeBook();
    final bytes = await EpubOriginal.imageBytes(
      book,
      book.chapters.first,
      '../Images/pic.png',
    );
    expect(bytes, [1, 2, 3, 4]);
  });

  test('mapea enlaces internos a capítulos', () {
    final book = Book(
      id: 'b',
      title: 'Libro',
      author: 'Autora',
      language: 'es',
      chapters: const [
        Chapter(
          index: 1,
          title: 'Uno',
          segments: [],
          sourceHref: 'OEBPS/Text/ch1.xhtml',
        ),
        Chapter(
          index: 2,
          title: 'Dos',
          segments: [],
          sourceHref: 'OEBPS/Text/ch2.xhtml',
        ),
      ],
    );
    expect(
      EpubOriginal.chapterForLink(book, book.chapters.first, 'ch2.xhtml'),
      2,
    );
    expect(
      EpubOriginal.chapterForLink(book, book.chapters.first, 'https://x.test'),
      isNull,
    );
  });

  test('un EPUB ausente devuelve null sin romper', () async {
    final book = Book(
      id: 'b',
      title: 'Libro',
      author: 'Autora',
      language: 'es',
      directoryPath: temp.path,
      sourceEpub: 'missing.epub',
      chapters: const [
        Chapter(index: 1, title: 'Uno', segments: [], sourceHref: 'ch1.xhtml'),
      ],
    );
    expect(await EpubOriginal.chapterHtml(book, book.chapters.first), isNull);
  });
}
