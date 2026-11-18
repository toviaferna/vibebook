import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/epub_ingestor.dart';

void main() {
  test('ingiere un EPUB real y conserva capítulos', () async {
    final bytes = await File('test/fixtures/sample.epub').readAsBytes();
    final book = await const EpubIngestor().ingest(bytes);
    expect(book.title, isNotEmpty);
    expect(book.author, isNotEmpty);
    expect(book.chapters, isNotEmpty);
    expect(book.chapters.first.paragraphs, isNotEmpty);
    expect(book.language, anyOf(startsWith('es'), startsWith('en')));
  });
}
