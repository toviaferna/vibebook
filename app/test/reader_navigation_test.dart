import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vibebook_app/app/providers.dart';
import 'package:vibebook_app/data/ambience/ambience_plan_repository.dart';
import 'package:vibebook_app/data/bookmark_repository.dart';
import 'package:vibebook_app/data/epub_ingestor.dart';
import 'package:vibebook_app/data/library_repository.dart';
import 'package:vibebook_app/domain/ambience_plan.dart';
import 'package:vibebook_app/domain/bookmarks.dart';
import 'package:vibebook_app/domain/models.dart';
import 'package:vibebook_app/features/reader/audio_transport.dart';
import 'package:vibebook_app/features/reader/reader_page.dart';

import 'fakes/fake_audio_transport.dart';

/// Library stub without disk access: native async IO never completes inside
/// the fake async zone of a widget test.
class _FakeLibrary extends LibraryRepository {
  _FakeLibrary(this.book) : super(ingestor: const EpubIngestor());

  final Book book;

  @override
  Future<Book?> get(String id) async => id == book.id ? book : null;

  @override
  Future<List<Book>> scan({String? query}) async => [book];
}

class _FakeBookmarkRepository extends BookmarkRepository {
  BookmarkData _data = BookmarkData.empty;

  @override
  Future<BookmarkData> load(String bookDirectory) async => _data;

  @override
  Future<BookmarkData> saveReadingState(
    String bookDirectory,
    ReadingState state,
  ) async {
    _data = _data.copyWith(readingState: state);
    return _data;
  }
}

class _FakePlanRepository extends AmbiencePlanRepository {
  @override
  Future<AmbiencePlan?> load(String bookDirectory) async => null;
}

Book _bookIn(Directory directory) {
  File(p.join(directory.path, 'chapter_001.mp3'))
      .writeAsBytesSync(List.filled(64, 0));
  return Book(
    id: 'test',
    title: 'Libro de prueba',
    author: 'Autor',
    language: 'es',
    status: 'ready',
    directoryPath: directory.path,
    chapters: [
      Chapter(
        index: 1,
        title: 'Capítulo 1',
        audio: 'chapter_001.mp3',
        segments: const [
          Segment(
            id: 'a',
            chapterIndex: 1,
            paragraphIndex: 1,
            text: 'Hola mundo',
          ),
        ],
      ),
    ],
  );
}

GoRouter _router() {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('inicio'))),
      ),
      GoRoute(
        path: '/books/:id',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('ficha'))),
      ),
      GoRoute(
        path: '/books/:id/read',
        builder: (context, state) =>
            ReaderPage(bookId: state.pathParameters['id']!),
      ),
    ],
  );
}

Future<GoRouter> pumpReader(
  WidgetTester tester, {
  required Book book,
  required ReaderTransportsFactory factory,
}) async {
  SharedPreferences.setMockInitialValues({});
  final router = _router();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        libraryRepositoryProvider.overrideWithValue(_FakeLibrary(book)),
        bookmarkRepositoryProvider.overrideWithValue(_FakeBookmarkRepository()),
        ambiencePlanRepositoryProvider.overrideWithValue(_FakePlanRepository()),
        readerTransportsFactoryProvider.overrideWithValue(factory),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  tester.element(find.text('inicio')).push('/books/test/read');
  await tester.pumpAndSettle();
  return router;
}

Directory _tempDir(String prefix) {
  final directory = Directory.systemTemp.createTempSync(prefix);
  addTearDown(() => directory.deleteSync(recursive: true));
  return directory;
}

void main() {
  testWidgets('volver desde el lector detiene la reproducción y hace pop', (
    tester,
  ) async {
    final voice = FakeAudioTransport();
    final ambience = FakeAudioTransport();
    final book = _bookIn(_tempDir('reader-nav-'));

    await pumpReader(
      tester,
      book: book,
      factory: () => ReaderTransports(voice: voice, ambience: ambience),
    );

    expect(voice.sourcePath, isNotNull);
    expect(find.byTooltip('Volver al libro'), findsOneWidget);

    await tester.tap(find.byTooltip('Volver al libro'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump();

    expect(find.text('inicio'), findsOneWidget);
    expect(voice.calls, contains('stop'));
    expect(voice.disposed, isTrue);
    expect(ambience.disposed, isTrue);
    expect(
      voice.calls.where((call) => call.startsWith('used-after-dispose')),
      isEmpty,
    );
    expect(
      ambience.calls.where((call) => call.startsWith('used-after-dispose')),
      isEmpty,
    );
  });

  testWidgets('el atrás del sistema también detiene y sale', (tester) async {
    final voice = FakeAudioTransport();
    final book = _bookIn(_tempDir('reader-back-'));

    await pumpReader(
      tester,
      book: book,
      factory: () =>
          ReaderTransports(voice: voice, ambience: FakeAudioTransport()),
    );

    // Atrás "del sistema": pide al Navigator que haga pop, que el PopScope del
    // lector intercepta.
    final navigator = tester.state<NavigatorState>(
      find.byType(Navigator).first,
    );
    await navigator.maybePop();
    await tester.pumpAndSettle();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump();

    expect(find.text('inicio'), findsOneWidget);
    expect(voice.calls, contains('stop'));
    expect(voice.disposed, isTrue);
  });

  testWidgets('reabrir el lector usa transports nuevos', (tester) async {
    final created = <ReaderTransports>[];
    final book = _bookIn(_tempDir('reader-open-'));

    final router = await pumpReader(
      tester,
      book: book,
      factory: () {
        final pair = ReaderTransports(
          voice: FakeAudioTransport(),
          ambience: FakeAudioTransport(),
        );
        created.add(pair);
        return pair;
      },
    );

    await tester.tap(find.byTooltip('Volver al libro'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump();

    router.go('/books/test/read');
    await tester.pumpAndSettle();

    expect(created, hasLength(2));
    expect((created[0].voice as FakeAudioTransport).disposed, isTrue);
    expect((created[1].voice as FakeAudioTransport).disposed, isFalse);
    expect(
      (created[0].voice as FakeAudioTransport).calls.where(
        (call) => call.startsWith('used-after-dispose'),
      ),
      isEmpty,
    );
  });
}
