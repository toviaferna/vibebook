import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/bookmark_repository.dart';
import 'package:vibebook_app/domain/bookmarks.dart';

void main() {
  test('guarda y recupera marcadores y estado de lectura', () async {
    final directory = await Directory.systemTemp.createTemp(
      'vibebook-bookmarks-',
    );
    addTearDown(() async {
      if (await directory.exists()) {
        await directory.delete(recursive: true);
      }
    });
    const repository = BookmarkRepository();
    final bookmark = Bookmark(
      id: 'one',
      chapterIndex: 2,
      positionMs: 45000,
      createdAt: '2026-11-18T00:00:00Z',
      chapterTitle: 'La casa',
    );
    await repository.addBookmark(directory.path, bookmark);
    await repository.saveReadingState(
      directory.path,
      const ReadingState(
        chapterIndex: 2,
        positionMs: 45000,
        updatedAt: '2026-11-18T00:01:00Z',
      ),
    );
    expect(File(p.join(directory.path, 'bookmarks.json')).existsSync(), isTrue);

    final loaded = await repository.load(directory.path);
    expect(loaded.bookmarks, hasLength(1));
    expect(loaded.bookmarks.first.chapterTitle, 'La casa');
    expect(loaded.readingState?.chapterIndex, 2);
    expect(loaded.readingState?.positionMs, 45000);

    await repository.removeBookmark(directory.path, 'one');
    final removed = await repository.load(directory.path);
    expect(removed.bookmarks, isEmpty);
    expect(removed.readingState?.chapterIndex, 2);
  });

  test('un archivo corrupto cae a datos vacíos', () async {
    final directory = await Directory.systemTemp.createTemp(
      'vibebook-bookmarks-',
    );
    addTearDown(() async {
      if (await directory.exists()) {
        await directory.delete(recursive: true);
      }
    });
    await File(p.join(directory.path, 'bookmarks.json'))
        .writeAsString('{not json');
    final loaded = await const BookmarkRepository().load(directory.path);
    expect(loaded.bookmarks, isEmpty);
    expect(loaded.readingState, isNull);
  });
}
