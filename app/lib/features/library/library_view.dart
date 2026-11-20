import '../../domain/models.dart';

const libraryFilters = <String, String>{
  'all': 'Todos',
  'ready': 'Con audio',
  'imported': 'Sin audio',
  'interrupted': 'Interrumpidos',
};

const librarySorts = <String, String>{
  'recent': 'Recientes',
  'title': 'Título',
  'duration': 'Duración',
};

/// Applies the library search, status filter and sort in one pure step.
List<Book> applyLibraryView(
  List<Book> books, {
  String query = '',
  String filter = 'all',
  String sort = 'recent',
}) {
  final needle = query.trim().toLowerCase();
  var result = books
      .where((book) {
        if (filter != 'all' && book.status != filter) {
          return false;
        }
        if (needle.isEmpty) {
          return true;
        }
        final haystack = '${book.title} ${book.author} ${book.language}'
            .toLowerCase();
        return haystack.contains(needle);
      })
      .toList(growable: false);

  result = [...result]
    ..sort((left, right) {
      switch (sort) {
        case 'title':
          return left.title.toLowerCase().compareTo(right.title.toLowerCase());
        case 'duration':
          final leftDuration = left.durationMs ?? -1;
          final rightDuration = right.durationMs ?? -1;
          final byDuration = rightDuration.compareTo(leftDuration);
          if (byDuration != 0) {
            return byDuration;
          }
          return left.title.toLowerCase().compareTo(right.title.toLowerCase());
        default:
          final leftDate = left.updatedAt ?? left.createdAt ?? '';
          final rightDate = right.updatedAt ?? right.createdAt ?? '';
          final byDate = rightDate.compareTo(leftDate);
          if (byDate != 0) {
            return byDate;
          }
          return left.title.toLowerCase().compareTo(right.title.toLowerCase());
      }
    });
  return result;
}
