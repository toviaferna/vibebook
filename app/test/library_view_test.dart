import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/domain/models.dart';
import 'package:vibebook_app/features/library/library_view.dart';

Book _book({
  required String id,
  required String title,
  String status = 'ready',
  int? durationMs,
  String? updatedAt,
}) {
  return Book(
    id: id,
    title: title,
    author: 'Autora',
    language: 'es',
    status: status,
    durationMs: durationMs,
    updatedAt: updatedAt,
    chapters: const [],
  );
}

void main() {
  final books = [
    _book(id: 'a', title: 'Zeta', durationMs: 3000, updatedAt: '2026-01-02'),
    _book(
      id: 'b',
      title: 'Alfa',
      durationMs: 1000,
      updatedAt: '2026-01-03',
      status: 'imported',
    ),
    _book(id: 'c', title: 'Beta', durationMs: 2000, updatedAt: '2026-01-01'),
  ];

  test('filtra por búsqueda y estado', () {
    expect(applyLibraryView(books, query: 'alf').map((book) => book.id), ['b']);
    expect(applyLibraryView(books, filter: 'ready').map((book) => book.id), [
      'a',
      'c',
    ]);
    expect(applyLibraryView(books, filter: 'imported').map((book) => book.id), [
      'b',
    ]);
  });

  test('ordena por título, duración y fecha', () {
    expect(applyLibraryView(books, sort: 'title').map((book) => book.title), [
      'Alfa',
      'Beta',
      'Zeta',
    ]);
    expect(
      applyLibraryView(books, sort: 'duration').map((book) => book.title),
      ['Zeta', 'Beta', 'Alfa'],
    );
    expect(applyLibraryView(books).map((book) => book.title), [
      'Alfa',
      'Zeta',
      'Beta',
    ]);
  });

  test('no cambia la lista original', () {
    final original = [...books];
    applyLibraryView(books, sort: 'title');
    expect(books.map((book) => book.id), original.map((book) => book.id));
  });
}
