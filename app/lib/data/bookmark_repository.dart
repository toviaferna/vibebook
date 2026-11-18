import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../domain/bookmarks.dart';

/// Persists bookmarks and the last position next to the book.
///
/// Keeping the file inside the book directory means it survives app updates
/// and travels with a copied library.
class BookmarkRepository {
  const BookmarkRepository();

  String _path(String bookDirectory) => p.join(bookDirectory, 'bookmarks.json');

  Future<BookmarkData> load(String bookDirectory) async {
    final file = File(_path(bookDirectory));
    if (!await file.exists()) {
      return BookmarkData.empty;
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is Map<String, dynamic>) {
        return BookmarkData.fromJson(decoded);
      }
    } on FormatException {
      // A corrupt bookmark file must not make the reader unusable.
    }
    return BookmarkData.empty;
  }

  Future<void> save(String bookDirectory, BookmarkData data) async {
    final file = File(_path(bookDirectory));
    await file.parent.create(recursive: true);
    final temporary = File('${file.path}.tmp');
    await temporary.writeAsString(
      const JsonEncoder.withIndent('  ').convert(data.toJson()),
      flush: true,
    );
    if (await file.exists()) {
      await file.delete();
    }
    await temporary.rename(file.path);
  }

  Future<BookmarkData> saveReadingState(
    String bookDirectory,
    ReadingState state,
  ) async {
    final current = await load(bookDirectory);
    final next = current.copyWith(readingState: state);
    await save(bookDirectory, next);
    return next;
  }

  Future<BookmarkData> addBookmark(String bookDirectory, Bookmark bookmark) async {
    final current = await load(bookDirectory);
    final next = current.copyWith(bookmarks: [...current.bookmarks, bookmark]);
    await save(bookDirectory, next);
    return next;
  }

  Future<BookmarkData> removeBookmark(String bookDirectory, String id) async {
    final current = await load(bookDirectory);
    final next = current.copyWith(
      bookmarks: current.bookmarks.where((bookmark) => bookmark.id != id).toList(growable: false),
    );
    await save(bookDirectory, next);
    return next;
  }
}
