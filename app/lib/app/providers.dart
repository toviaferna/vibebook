import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/epub_ingestor.dart';
import '../data/library_repository.dart';
import '../data/settings_repository.dart';
import '../domain/models.dart';

final settingsRepositoryProvider = Provider<SettingsRepository>((ref) {
  return SettingsRepository();
});

final epubIngestorProvider = Provider<EpubIngestor>((ref) {
  return const EpubIngestor();
});

final settingsProvider = AsyncNotifierProvider<SettingsController, AppSettings>(
  SettingsController.new,
);

class SettingsController extends AsyncNotifier<AppSettings> {
  @override
  Future<AppSettings> build() {
    return ref.read(settingsRepositoryProvider).load();
  }

  Future<void> setThemeMode(String mode) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(themeMode: mode);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }

  Future<void> setLibraryPath(String? path) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(libraryPath: path);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
    ref.invalidate(libraryRepositoryProvider);
    ref.invalidate(libraryProvider);
  }

  Future<void> updateReader(ReaderPreferences preferences) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(reader: preferences);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }

  Future<void> rememberBook(String bookId, int chapterIndex) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(lastBookId: bookId, lastChapterIndex: chapterIndex);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }
}

final libraryRepositoryProvider = Provider<LibraryRepository>((ref) {
  final settings = ref.watch(settingsProvider).value;
  return LibraryRepository(
    ingestor: ref.watch(epubIngestorProvider),
    libraryPath: settings?.libraryPath,
  );
});

final libraryProvider = AsyncNotifierProvider<LibraryController, List<Book>>(
  LibraryController.new,
);

class LibraryController extends AsyncNotifier<List<Book>> {
  @override
  Future<List<Book>> build() {
    return ref.watch(libraryRepositoryProvider).scan();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => ref.read(libraryRepositoryProvider).scan());
  }

  Future<Book> importEpub(String path) async {
    final book = await ref.read(libraryRepositoryProvider).importEpub(path);
    await refresh();
    return book;
  }
}

final bookProvider = FutureProvider.family<Book?, String>((ref, id) {
  return ref.watch(libraryRepositoryProvider).get(id);
});

final searchQueryProvider = NotifierProvider<SearchQueryController, String>(
  SearchQueryController.new,
);

class SearchQueryController extends Notifier<String> {
  @override
  String build() => '';

  void setQuery(String query) => state = query;
}

final filteredBooksProvider = Provider<AsyncValue<List<Book>>>((ref) {
  final query = ref.watch(searchQueryProvider).trim().toLowerCase();
  final books = ref.watch(libraryProvider);
  if (query.isEmpty) {
    return books;
  }
  return books.whenData(
    (items) => items.where((book) {
      final haystack = '${book.title} ${book.author} ${book.language}'.toLowerCase();
      return haystack.contains(query);
    }).toList(growable: false),
  );
});

final themeModeProvider = Provider<ThemeMode>((ref) {
  final mode = ref.watch(settingsProvider).value?.themeMode ?? 'system';
  return switch (mode) {
    'light' => ThemeMode.light,
    'dark' => ThemeMode.dark,
    _ => ThemeMode.system,
  };
});

final readerPreferencesProvider = Provider<ReaderPreferences>((ref) {
  return ref.watch(settingsProvider).value?.reader ?? const ReaderPreferences();
});

enum ImportStatus { idle, working, done, error }

class ImportState {
  const ImportState({
    this.status = ImportStatus.idle,
    this.message,
    this.book,
    this.progress,
  });

  final ImportStatus status;
  final String? message;
  final Book? book;
  final double? progress;

  ImportState copyWith({
    ImportStatus? status,
    String? message,
    Book? book,
    double? progress,
  }) {
    return ImportState(
      status: status ?? this.status,
      message: message ?? this.message,
      book: book ?? this.book,
      progress: progress ?? this.progress,
    );
  }
}

final importControllerProvider = NotifierProvider<ImportController, ImportState>(
  ImportController.new,
);

class ImportController extends Notifier<ImportState> {
  @override
  ImportState build() => const ImportState();

  Future<Book?> importEpub(String path) async {
    state = const ImportState(status: ImportStatus.working, message: 'Importando EPUB…');
    try {
      final book = await ref.read(libraryProvider.notifier).importEpub(path);
      state = ImportState(status: ImportStatus.done, message: 'Importado: ${book.title}', book: book);
      return book;
    } catch (error) {
      state = ImportState(status: ImportStatus.error, message: 'No se pudo importar: $error');
      return null;
    }
  }

  void reset() => state = const ImportState();
}
