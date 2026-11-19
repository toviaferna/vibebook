import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/bookmark_repository.dart';
import 'package:vibebook_app/domain/bookmarks.dart';

void main() {
  late Directory temp;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-bookmarks-');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  test('lee archivos viejos sin marcadores de lectura', () async {
    File('${temp.path}/bookmarks.json').writeAsStringSync(
      jsonEncode({
        'version': 1,
        'reading_state': {
          'chapter_index': 2,
          'position_ms': 1200,
          'updated_at': 'ayer',
        },
        'bookmarks': [
          {
            'id': 'a',
            'chapter_index': 1,
            'position_ms': 500,
            'created_at': 'hoy',
          },
        ],
      }),
    );
    final data = await const BookmarkRepository().load(temp.path);
    expect(data.readingBookmarks, isEmpty);
    expect(data.readingState!.chapterIndex, 2);
    expect(data.bookmarks.single.positionMs, 500);
  });

  test('agrega, persiste y elimina un marcador de lectura', () async {
    const repository = BookmarkRepository();
    await repository.addReadingBookmark(
      temp.path,
      const ReadingBookmark(
        id: 'r1',
        chapterIndex: 3,
        charOffset: 420,
        pageIndex: 2,
        createdAt: 'hoy',
        note: 'Volver acá',
      ),
    );
    final loaded = await repository.load(temp.path);
    expect(loaded.readingBookmarks.single.charOffset, 420);
    expect(loaded.readingBookmarks.single.note, 'Volver acá');
    final raw = await File('${temp.path}/bookmarks.json').readAsString();
    expect(raw, contains('reading_bookmarks'));
    await repository.removeReadingBookmark(temp.path, 'r1');
    expect((await repository.load(temp.path)).readingBookmarks, isEmpty);
  });

  test('un archivo corrupto no rompe el lector', () async {
    File('${temp.path}/bookmarks.json').writeAsStringSync('{ nope');
    expect(
      (await const BookmarkRepository().load(temp.path)).bookmarks,
      isEmpty,
    );
  });
}
