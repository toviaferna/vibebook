class Bookmark {
  const Bookmark({
    required this.id,
    required this.chapterIndex,
    required this.positionMs,
    required this.createdAt,
    this.chapterTitle,
    this.note,
  });

  final String id;
  final int chapterIndex;
  final int positionMs;
  final String createdAt;
  final String? chapterTitle;
  final String? note;

  Map<String, dynamic> toJson() => {
    'id': id,
    'chapter_index': chapterIndex,
    'position_ms': positionMs,
    'created_at': createdAt,
    'chapter_title': chapterTitle,
    'note': note,
  };

  factory Bookmark.fromJson(Map<String, dynamic> json) {
    return Bookmark(
      id: json['id'] as String? ?? '',
      chapterIndex: (json['chapter_index'] as num?)?.toInt() ?? 1,
      positionMs: (json['position_ms'] as num?)?.toInt() ?? 0,
      createdAt: json['created_at'] as String? ?? '',
      chapterTitle: json['chapter_title'] as String?,
      note: json['note'] as String?,
    );
  }
}

class ReadingState {
  const ReadingState({
    required this.chapterIndex,
    required this.positionMs,
    required this.updatedAt,
  });

  final int chapterIndex;
  final int positionMs;
  final String updatedAt;

  Map<String, dynamic> toJson() => {
    'chapter_index': chapterIndex,
    'position_ms': positionMs,
    'updated_at': updatedAt,
  };

  factory ReadingState.fromJson(Map<String, dynamic> json) {
    return ReadingState(
      chapterIndex: (json['chapter_index'] as num?)?.toInt() ?? 1,
      positionMs: (json['position_ms'] as num?)?.toInt() ?? 0,
      updatedAt: json['updated_at'] as String? ?? '',
    );
  }
}

class BookmarkData {
  const BookmarkData({this.readingState, this.bookmarks = const []});

  final ReadingState? readingState;
  final List<Bookmark> bookmarks;

  static const empty = BookmarkData();

  BookmarkData copyWith({
    ReadingState? readingState,
    List<Bookmark>? bookmarks,
  }) {
    return BookmarkData(
      readingState: readingState ?? this.readingState,
      bookmarks: bookmarks ?? this.bookmarks,
    );
  }

  Map<String, dynamic> toJson() => {
    'version': 1,
    'reading_state': readingState?.toJson(),
    'bookmarks': bookmarks
        .map((bookmark) => bookmark.toJson())
        .toList(growable: false),
  };

  factory BookmarkData.fromJson(Map<String, dynamic> json) {
    final rawBookmarks = json['bookmarks'];
    final bookmarks = <Bookmark>[];
    if (rawBookmarks is List) {
      for (final item in rawBookmarks) {
        if (item is Map<String, dynamic> && item['id'] is String) {
          bookmarks.add(Bookmark.fromJson(item));
        }
      }
    }
    final rawState = json['reading_state'];
    return BookmarkData(
      readingState: rawState is Map<String, dynamic>
          ? ReadingState.fromJson(rawState)
          : null,
      bookmarks: bookmarks,
    );
  }
}
