import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/domain/models.dart';
import 'package:vibebook_app/features/reader/reader_search.dart';
import 'package:vibebook_app/features/reader/reader_view_mode.dart';

Book _book() {
  return const Book(
    id: 'b',
    title: 'Libro',
    author: 'Autora',
    language: 'es',
    chapters: [
      Chapter(
        index: 1,
        title: 'La casa',
        segments: [
          Segment(
            id: 'c001p0001s00',
            chapterIndex: 1,
            paragraphIndex: 1,
            text: 'La casa de los Ferrer olía a sal.',
          ),
          Segment(
            id: 'c001p0002s00',
            chapterIndex: 1,
            paragraphIndex: 2,
            text: 'Nadie sabía por qué.',
          ),
        ],
      ),
      Chapter(
        index: 2,
        title: 'El mar',
        segments: [
          Segment(
            id: 'c002p0001s00',
            chapterIndex: 2,
            paragraphIndex: 1,
            text: 'El mar golpeaba la casa cada noche.',
          ),
        ],
      ),
    ],
  );
}

void main() {
  test('busca en todos los capítulos y arma un extracto', () {
    final hits = searchBook(_book(), 'casa');
    expect(hits, hasLength(2));
    expect(hits.first.chapterIndex, 1);
    expect(hits.first.excerpt, contains('casa'));
    expect(hits.last.chapterIndex, 2);
  });

  test('ignora mayúsculas y acentos', () {
    final hits = searchBook(_book(), 'OLIA');
    expect(hits, hasLength(1));
    expect(hits.single.excerpt, contains('olía'));
  });

  test('no busca con menos de dos letras', () {
    expect(searchBook(_book(), 'a'), isEmpty);
    expect(searchBook(_book(), '  '), isEmpty);
  });

  test('respeta el límite', () {
    final hits = searchBook(_book(), 'la', limit: 1);
    expect(hits, hasLength(1));
  });

  test('el modo de lectura se lee desde el nombre', () {
    expect(ReaderViewMode.fromName('book'), ReaderViewMode.book);
    expect(ReaderViewMode.fromName('original'), ReaderViewMode.original);
    expect(ReaderViewMode.fromName('otro'), ReaderViewMode.text);
  });
}
