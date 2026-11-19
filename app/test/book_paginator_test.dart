import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:vibebook_app/domain/models.dart';
import 'package:vibebook_app/features/reader/book_paginator.dart';

Chapter _chapter() {
  final words = List.generate(120, (index) => 'palabra$index').join(' ');
  return Chapter(
    index: 1,
    title: 'Uno',
    segments: [
      for (var index = 1; index <= 8; index++)
        Segment(
          id: 'c001p${index.toString().padLeft(4, '0')}s00',
          chapterIndex: 1,
          paragraphIndex: index,
          text: 'Párrafo $index. $words.',
        ),
    ],
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('pagina un capítulo largo sin perder texto', () {
    final chapter = _chapter();
    final pages = const BookPaginator().paginate(
      chapter: chapter,
      size: const Size(360, 520),
      style: const TextStyle(fontSize: 16, height: 1.5),
    );
    expect(pages.length, greaterThan(1));
    expect(pages.every((page) => page.blocks.isNotEmpty), isTrue);
    final allText = pages
        .expand((page) => page.blocks)
        .where((block) => !block.isImage)
        .map((block) => block.text)
        .join(' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    final original = chapter.segments
        .map((segment) => segment.text)
        .join(' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    expect(allText, original);
  });

  test('las imágenes ocupan su propio bloque', () {
    final pages = const BookPaginator().paginate(
      chapter: _chapter(),
      size: const Size(360, 900),
      style: const TextStyle(fontSize: 16, height: 1.5),
      images: const [
        BookImage(
          id: 'i1',
          alt: 'Ilustración',
          chapterIndex: 1,
          paragraphIndex: 1,
          path: 'images/i1.jpg',
        ),
      ],
    );
    final images = pages
        .expand((page) => page.blocks)
        .where((block) => block.isImage)
        .toList(growable: false);
    expect(images, hasLength(1));
    expect(images.single.image!.alt, 'Ilustración');
  });

  test('un tamaño mínimo no produce un bucle infinito', () {
    final pages = const BookPaginator().paginate(
      chapter: _chapter(),
      size: const Size(80, 20),
      style: const TextStyle(fontSize: 16, height: 1.5),
    );
    expect(pages, isNotEmpty);
  });
}
