import 'package:material_ui/material_ui.dart';

import '../../core/design/tokens.dart';
import '../../domain/models.dart';

/// One in-book search result.
class ReaderSearchHit {
  const ReaderSearchHit({
    required this.chapterIndex,
    required this.chapterTitle,
    required this.segmentId,
    required this.offset,
    required this.excerpt,
    required this.positionMs,
  });

  final int chapterIndex;
  final String chapterTitle;
  final String segmentId;

  /// Character offset inside the segment where the match starts.
  final int offset;
  final String excerpt;
  final int positionMs;
}

const _diacritics = {
  'á': 'a',
  'à': 'a',
  'ä': 'a',
  'â': 'a',
  'ã': 'a',
  'é': 'e',
  'è': 'e',
  'ë': 'e',
  'ê': 'e',
  'í': 'i',
  'ì': 'i',
  'ï': 'i',
  'î': 'i',
  'ó': 'o',
  'ò': 'o',
  'ö': 'o',
  'ô': 'o',
  'õ': 'o',
  'ú': 'u',
  'ù': 'u',
  'ü': 'u',
  'û': 'u',
  'ñ': 'n',
  'ç': 'c',
};

String foldForSearch(String value) {
  final buffer = StringBuffer();
  for (final rune in value.toLowerCase().runes) {
    final character = String.fromCharCode(rune);
    buffer.write(_diacritics[character] ?? character);
  }
  return buffer.toString();
}

/// Searches every segment of [book]. Case and accents are ignored.
///
/// Returns at most [limit] hits. A query shorter than two characters returns
/// an empty list so the UI can ask for more input.
List<ReaderSearchHit> searchBook(Book book, String query, {int limit = 120}) {
  final cleaned = query.trim();
  if (cleaned.length < 2) {
    return const [];
  }
  final needle = foldForSearch(cleaned);
  final hits = <ReaderSearchHit>[];
  for (final chapter in book.chapters) {
    for (final segment in chapter.segments) {
      final haystack = foldForSearch(segment.text);
      var from = 0;
      while (hits.length < limit) {
        final index = haystack.indexOf(needle, from);
        if (index < 0) {
          break;
        }
        hits.add(
          ReaderSearchHit(
            chapterIndex: chapter.index,
            chapterTitle: chapter.title,
            segmentId: segment.id,
            offset: index,
            excerpt: _excerpt(segment.text, index, cleaned.length),
            positionMs: 0,
          ),
        );
        from = index + needle.length;
      }
      if (hits.length >= limit) {
        return hits;
      }
    }
  }
  return hits;
}

String _excerpt(String text, int index, int length) {
  final start = index - 42 < 0 ? 0 : index - 42;
  final end = index + length + 58 > text.length
      ? text.length
      : index + length + 58;
  final prefix = start > 0 ? '…' : '';
  final suffix = end < text.length ? '…' : '';
  return '$prefix${text.substring(start, end).replaceAll(RegExp(r'\s+'), ' ')}$suffix';
}

class BookSearchDelegate extends SearchDelegate<ReaderSearchHit> {
  BookSearchDelegate({
    required this.book,
    required this.palette,
    required this.onSelect,
  }) : super(searchFieldLabel: 'Buscar en el libro');

  final Book book;
  final ReaderPalette palette;
  final ValueChanged<ReaderSearchHit> onSelect;

  @override
  List<Widget>? buildActions(BuildContext context) {
    return [
      IconButton(
        tooltip: 'Limpiar',
        onPressed: () => query = '',
        icon: const Icon(Icons.clear),
      ),
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      tooltip: 'Volver',
      onPressed: () => Navigator.of(context).pop(),
      icon: const Icon(Icons.arrow_back),
    );
  }

  @override
  Widget buildResults(BuildContext context) => _results(context);

  @override
  Widget buildSuggestions(BuildContext context) => _results(context);

  Widget _results(BuildContext context) {
    if (query.trim().length < 2) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            'Escribí al menos dos letras para buscar en el libro.',
            style: TextStyle(color: palette.inkSoft),
          ),
        ),
      );
    }
    final hits = searchBook(book, query);
    if (hits.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            'No encontramos “${query.trim()}” en este libro.',
            textAlign: TextAlign.center,
            style: TextStyle(color: palette.inkSoft),
          ),
        ),
      );
    }
    return ListView.separated(
      itemCount: hits.length,
      separatorBuilder: (context, index) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final hit = hits[index];
        return ListTile(
          leading: CircleAvatar(radius: 16, child: Text('${hit.chapterIndex}')),
          title: Text(hit.chapterTitle),
          subtitle: Text(
            hit.excerpt,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          onTap: () {
            close(context, hit);
            onSelect(hit);
          },
        );
      },
    );
  }
}
