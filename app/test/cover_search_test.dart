import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/covers/cover_search.dart';

class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.handler);

  final Future<ResponseBody> Function(RequestOptions options) handler;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(Object value, {int status = 200}) {
  return ResponseBody.fromString(
    jsonEncode(value),
    status,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

CoverSearchService _service() {
  return CoverSearchService(
    dio: Dio()
      ..httpClientAdapter = _FakeAdapter((options) async {
        if (options.uri.host == 'openlibrary.org') {
          return _json({
            'docs': [
              {
                'key': '/works/OL1W',
                'title': 'El gato negro',
                'author_name': ['Edgar Allan Poe'],
                'cover_i': 123,
                'first_publish_year': 1843,
              },
            ],
          });
        }
        if (options.uri.host == 'www.googleapis.com') {
          return _json({
            'items': [
              {
                'volumeInfo': {
                  'title': 'El gato negro',
                  'authors': ['Edgar Allan Poe'],
                  'publishedDate': '1843-01-01',
                  'imageLinks': {
                    'thumbnail': 'http://books.google.com/cover.jpg&zoom=1',
                  },
                  'infoLink': 'https://books.google.com/books?id=1',
                },
              },
            ],
          });
        }
        fail('URL inesperada: ${options.uri}');
      }),
  );
}

void main() {
  test('normaliza acentos y puntuación', () {
    expect(normalize('El gato negro: ¡Edición!'), 'el gato negro edicion');
  });

  test('puntúa títulos exactos, contenidos y parecidos', () {
    expect(titleScore('El gato negro', 'El gato negro'), 1);
    expect(titleScore('El gato negro', 'El gato negro y otros cuentos'), 0.95);
    expect(titleScore('El gato negro', 'La casa de los espíritus'), 0);
  });

  test('busca en ambos proveedores y deduplica', () async {
    final hits = await _service().search(
      title: 'El gato negro',
      author: 'Edgar Allan Poe',
    );
    expect(hits, hasLength(1));
    expect(hits.single.source, 'Open Library');
    expect(hits.single.year, 1843);
    expect(hits.single.author, 'Edgar Allan Poe');
    expect(hits.single.score, 1.1);
  });

  test('un proveedor caído no rompe la búsqueda', () async {
    final service = CoverSearchService(
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter((options) async {
          if (options.uri.host == 'openlibrary.org') {
            return _json({'error': 'down'}, status: 503);
          }
          return _json({
            'items': [
              {
                'volumeInfo': {
                  'title': 'El gato negro',
                  'authors': ['Edgar Allan Poe'],
                  'imageLinks': {'thumbnail': 'https://books.google.com/c.jpg'},
                },
              },
            ],
          });
        }),
    );
    final hits = await service.search(
      title: 'El gato negro',
      author: 'Edgar Allan Poe',
    );
    expect(hits.single.source, 'Google Books');
  });

  test('rechaza hosts no permitidos al descargar', () async {
    expect(
      () => _service().download('http://example.com/cover.jpg'),
      throwsA(isA<CoverSearchException>()),
    );
    expect(
      () => _service().download('https://example.com/cover.jpg'),
      throwsA(isA<CoverSearchException>()),
    );
  });

  test('descarga una portada y sigue una redirección', () async {
    final service = CoverSearchService(
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter((options) async {
          if (options.uri.path == '/redirect') {
            return ResponseBody.fromString(
              '',
              302,
              headers: {
                'location': ['https://covers.openlibrary.org/b/id/1-L.jpg'],
              },
            );
          }
          return ResponseBody.fromBytes(
            [1, 2, 3, 4],
            200,
            headers: {
              Headers.contentTypeHeader: ['image/jpeg'],
            },
          );
        }),
    );
    final bytes = await service.download(
      'https://covers.openlibrary.org/redirect',
    );
    expect(bytes, [1, 2, 3, 4]);
  });

  test('rechaza contenido que no es imagen', () async {
    final service = CoverSearchService(
      dio: Dio()
        ..httpClientAdapter = _FakeAdapter(
          (options) async => ResponseBody.fromString(
            'no soy una imagen',
            200,
            headers: {
              Headers.contentTypeHeader: ['text/html'],
            },
          ),
        ),
    );
    expect(
      () => service.download('https://covers.openlibrary.org/x'),
      throwsA(isA<CoverSearchException>()),
    );
  });
}
