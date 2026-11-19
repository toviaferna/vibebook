import 'dart:typed_data';

import 'package:dio/dio.dart';

class CoverSearchException implements Exception {
  const CoverSearchException(this.message);

  final String message;

  @override
  String toString() => message;
}

class CoverHit {
  const CoverHit({
    required this.source,
    required this.title,
    required this.author,
    required this.coverUrl,
    required this.score,
    this.year,
    this.editionUrl,
  });

  final String source;
  final String title;
  final String author;
  final int? year;
  final String coverUrl;
  final String? editionUrl;
  final double score;
}

/// Searches Open Library and Google Books for a book cover and downloads it.
class CoverSearchService {
  CoverSearchService({Dio? dio})
    : _dio =
          dio ??
          Dio(
            BaseOptions(
              connectTimeout: const Duration(seconds: 8),
              receiveTimeout: const Duration(seconds: 12),
              headers: {
                'User-Agent':
                    'Vibebook/0.9 (+https://github.com/toviaferna/vibebook)',
              },
            ),
          );

  final Dio _dio;

  static const maxCoverBytes = 8 * 1024 * 1024;
  static const allowedHosts = {
    'covers.openlibrary.org',
    'books.google.com',
    'books.googleusercontent.com',
    'lh3.googleusercontent.com',
  };

  Future<List<CoverHit>> search({
    required String title,
    required String author,
    int limit = 8,
  }) async {
    final hits = <CoverHit>[];
    final errors = <String>[];
    try {
      hits.addAll(await _searchOpenLibrary(title, author));
    } on CoverSearchException catch (error) {
      errors.add(error.message);
    }
    if (hits.length < limit) {
      try {
        hits.addAll(await _searchGoogleBooks(title, author));
      } on CoverSearchException catch (error) {
        errors.add(error.message);
      }
    }
    if (hits.isEmpty && errors.isNotEmpty) {
      throw CoverSearchException(errors.join('; '));
    }
    final unique = <String, CoverHit>{};
    for (final hit in hits) {
      final key = '${normalize(hit.title)}|${normalize(hit.author)}';
      final current = unique[key];
      if (current == null || hit.score > current.score) {
        unique[key] = hit;
      }
    }
    final ordered = unique.values.toList(growable: false)
      ..sort((left, right) => right.score.compareTo(left.score));
    return ordered.take(limit).toList(growable: false);
  }

  Future<List<CoverHit>> _searchOpenLibrary(String title, String author) async {
    final response = await _getJson(
      'https://openlibrary.org/search.json',
      query: {
        'title': title,
        'author': author,
        'limit': 12,
        'fields': 'key,title,author_name,cover_i,first_publish_year',
      },
      provider: 'Open Library',
    );
    final docs = response['docs'];
    if (docs is! List) {
      return const [];
    }
    final hits = <CoverHit>[];
    for (final item in docs) {
      if (item is! Map) {
        continue;
      }
      final coverId = item['cover_i'];
      if (coverId == null) {
        continue;
      }
      final candidateTitle = '${item['title'] ?? ''}';
      var score = titleScore(title, candidateTitle);
      if (score == 0) {
        continue;
      }
      final authors = (item['author_name'] as List? ?? const [])
          .map((name) => '$name')
          .toList(growable: false);
      if (author.isNotEmpty && authorMatches(author, authors)) {
        score += 0.1;
      }
      hits.add(
        CoverHit(
          source: 'Open Library',
          title: candidateTitle,
          author: authors.isEmpty ? 'Autor desconocido' : authors.join(', '),
          year: _optionalInt(item['first_publish_year']),
          coverUrl: 'https://covers.openlibrary.org/b/id/$coverId-L.jpg',
          editionUrl: item['key'] is String
              ? 'https://openlibrary.org${item['key']}'
              : null,
          score: score.clamp(0, 1.1),
        ),
      );
    }
    return hits;
  }

  Future<List<CoverHit>> _searchGoogleBooks(String title, String author) async {
    var query = 'intitle:"$title"';
    if (author.isNotEmpty) {
      query += ' inauthor:"$author"';
    }
    final response = await _getJson(
      'https://www.googleapis.com/books/v1/volumes',
      query: {'q': query, 'maxResults': 12, 'printType': 'books'},
      provider: 'Google Books',
    );
    final items = response['items'];
    if (items is! List) {
      return const [];
    }
    final hits = <CoverHit>[];
    for (final item in items) {
      if (item is! Map) {
        continue;
      }
      final volume = item['volumeInfo'];
      if (volume is! Map) {
        continue;
      }
      final candidateTitle = '${volume['title'] ?? ''}';
      var score = titleScore(title, candidateTitle);
      if (score == 0) {
        continue;
      }
      final authors = (volume['authors'] as List? ?? const [])
          .map((name) => '$name')
          .toList(growable: false);
      if (author.isNotEmpty && authorMatches(author, authors)) {
        score += 0.1;
      }
      final image = volume['imageLinks'];
      if (image is! Map) {
        continue;
      }
      var coverUrl = '${image['thumbnail'] ?? image['smallThumbnail'] ?? ''}';
      if (coverUrl.isEmpty) {
        continue;
      }
      coverUrl = coverUrl
          .replaceFirst('http://', 'https://')
          .replaceAll('&zoom=1', '&zoom=2');
      hits.add(
        CoverHit(
          source: 'Google Books',
          title: candidateTitle,
          author: authors.isEmpty ? 'Autor desconocido' : authors.join(', '),
          year: _optionalInt(
            '${volume['publishedDate'] ?? ''}'.split('-').first,
          ),
          coverUrl: coverUrl,
          editionUrl: volume['infoLink'] is String
              ? volume['infoLink'] as String
              : null,
          score: score.clamp(0, 1.1),
        ),
      );
    }
    return hits;
  }

  Future<Map<String, dynamic>> _getJson(
    String url, {
    required Map<String, dynamic> query,
    required String provider,
  }) async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>(
        url,
        queryParameters: query,
        options: Options(validateStatus: (status) => status != null),
      );
    } on DioException {
      throw CoverSearchException('$provider no respondió.');
    }
    if (response.statusCode != 200) {
      throw CoverSearchException('$provider devolvió ${response.statusCode}.');
    }
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw CoverSearchException('$provider devolvió datos inválidos.');
    }
    return data;
  }

  Future<Uint8List> download(String url) async {
    var current = url;
    for (var attempt = 0; attempt < 3; attempt++) {
      final uri = Uri.tryParse(current);
      if (uri == null ||
          uri.scheme != 'https' ||
          !allowedHosts.contains(uri.host)) {
        throw const CoverSearchException(
          'La portada no viene de un servicio permitido.',
        );
      }
      final Response<List<int>> response;
      try {
        response = await _dio.get<List<int>>(
          current,
          options: Options(
            responseType: ResponseType.bytes,
            followRedirects: false,
            validateStatus: (status) => status != null,
          ),
        );
      } on DioException {
        throw const CoverSearchException('No se pudo descargar la portada.');
      }
      final status = response.statusCode ?? 0;
      if (status >= 300 && status < 400) {
        final location = response.headers.value('location');
        if (location == null || location.isEmpty) {
          throw const CoverSearchException('La portada redirige sin destino.');
        }
        current = uri.resolve(location).toString();
        continue;
      }
      if (status != 200) {
        throw CoverSearchException('El servicio de portadas devolvió $status.');
      }
      final contentType = response.headers.value('content-type') ?? '';
      if (!contentType.startsWith('image/')) {
        throw const CoverSearchException(
          'El recurso descargado no es una imagen.',
        );
      }
      final bytes = response.data;
      if (bytes == null || bytes.isEmpty) {
        throw const CoverSearchException('La portada llegó vacía.');
      }
      if (bytes.length > maxCoverBytes) {
        throw const CoverSearchException(
          'La portada supera el tamaño permitido.',
        );
      }
      return Uint8List.fromList(bytes);
    }
    throw const CoverSearchException('La portada redirige demasiadas veces.');
  }
}

String normalize(String value) {
  final buffer = StringBuffer();
  for (final rune in value.toLowerCase().runes) {
    final character = String.fromCharCode(rune);
    buffer.write(_diacritics[character] ?? character);
  }
  return buffer.toString().replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();
}

double titleScore(String query, String candidate) {
  final left = normalize(query);
  final right = normalize(candidate);
  if (left.isEmpty || right.isEmpty) {
    return 0;
  }
  if (left == right) {
    return 1;
  }
  if (left.contains(right) || right.contains(left)) {
    return 0.95;
  }
  final ratio = _similarity(left, right);
  return ratio >= 0.82 ? ratio : 0;
}

bool authorMatches(String query, List<String> candidates) {
  if (query.trim().isEmpty || candidates.isEmpty) {
    return false;
  }
  final words = normalize(query)
      .split(' ')
      .where((word) => word.length > 2)
      .toList(growable: false);
  final haystack = candidates.map(normalize).join(' ');
  return words.any(haystack.contains);
}

double _similarity(String left, String right) {
  final distance = _levenshtein(left, right);
  final longest = left.length > right.length ? left.length : right.length;
  return longest == 0 ? 1 : 1 - distance / longest;
}

int _levenshtein(String left, String right) {
  var previous = List<int>.generate(right.length + 1, (index) => index);
  for (var i = 1; i <= left.length; i++) {
    final current = List<int>.filled(right.length + 1, 0);
    current[0] = i;
    for (var j = 1; j <= right.length; j++) {
      final cost = left[i - 1] == right[j - 1] ? 0 : 1;
      final deletion = previous[j] + 1;
      final insertion = current[j - 1] + 1;
      final substitution = previous[j - 1] + cost;
      current[j] = deletion < insertion
          ? (deletion < substitution ? deletion : substitution)
          : (insertion < substitution ? insertion : substitution);
    }
    previous = current;
  }
  return previous[right.length];
}

int? _optionalInt(Object? value) {
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
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
