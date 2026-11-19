import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/ambience/ambience_plan_repository.dart';
import '../data/bookmark_repository.dart';
import '../data/epub_ingestor.dart';
import '../data/library_repository.dart';
import '../data/settings_repository.dart';
import '../data/tts/piper_downloader.dart';
import '../data/tts/piper_models.dart';
import '../domain/ambience_plan.dart';
import '../domain/bookmarks.dart';
import '../domain/models.dart';
import '../features/reader/audio_transport.dart';
import '../features/reader/audioplayers_audio_transport.dart';

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

  Future<void> setModelsPath(String? path) async {
    final current = state.value ?? const AppSettings();
    final next = path == null
        ? current.copyWith(clearModelsPath: true, clearPiperModel: true)
        : current.copyWith(modelsPath: path, clearPiperModel: true);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
    ref.invalidate(piperModelStoreProvider);
    ref.invalidate(piperModelsProvider);
    ref.invalidate(modelsRootProvider);
  }

  Future<void> selectPiperModel(String modelId) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(piperModelId: modelId);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }

  Future<void> setPiperRate(double rate) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(piperRate: rate);
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }

  Future<void> updateAmbience({
    bool? enabled,
    String? preset,
    double? volume,
    double? ducking,
  }) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(
      ambienceEnabled: enabled,
      ambiencePreset: preset,
      ambienceVolume: volume,
      ambienceDucking: ducking,
    );
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }

  Future<void> updateTtsEngine({
    String? engine,
    String? edgeVoice,
    double? edgeRate,
  }) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(
      ttsEngine: engine,
      edgeVoiceId: edgeVoice,
      edgeRate: edgeRate,
    );
    state = AsyncData(next);
    await ref.read(settingsRepositoryProvider).save(next);
  }

  Future<void> rememberBook(String bookId, int chapterIndex) async {
    final current = state.value ?? const AppSettings();
    final next = current.copyWith(
      lastBookId: bookId,
      lastChapterIndex: chapterIndex,
    );
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
    state = await AsyncValue.guard(
      () => ref.read(libraryRepositoryProvider).scan(),
    );
  }

  Future<Book> importEpub(String path) async {
    final book = await ref.read(libraryRepositoryProvider).importEpub(path);
    await refresh();
    return book;
  }

  Future<void> deleteBook(String id) async {
    await ref.read(libraryRepositoryProvider).deleteBook(id);
    ref.invalidate(bookProvider(id));
    await refresh();
  }
}

final bookProvider = FutureProvider.family<Book?, String>((ref, id) {
  return ref.watch(libraryRepositoryProvider).get(id);
});

final bookmarkRepositoryProvider = Provider<BookmarkRepository>((ref) {
  return const BookmarkRepository();
});

final bookmarkDataProvider = FutureProvider.family<BookmarkData, String>((
  ref,
  bookId,
) async {
  final book = await ref.watch(bookProvider(bookId).future);
  final directory = book?.directoryPath;
  if (directory == null) {
    return BookmarkData.empty;
  }
  return ref.watch(bookmarkRepositoryProvider).load(directory);
});

final ambiencePlanRepositoryProvider = Provider<AmbiencePlanRepository>((ref) {
  return const AmbiencePlanRepository();
});

final ambiencePlanProvider = FutureProvider.family<AmbiencePlan?, String>((
  ref,
  bookId,
) async {
  final book = await ref.watch(bookProvider(bookId).future);
  final directory = book?.directoryPath;
  if (directory == null) {
    return null;
  }
  return ref.watch(ambiencePlanRepositoryProvider).load(directory);
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
    (items) => items
        .where((book) {
          final haystack = '${book.title} ${book.author} ${book.language}'
              .toLowerCase();
          return haystack.contains(query);
        })
        .toList(growable: false),
  );
});

final piperModelStoreProvider = Provider<PiperModelStore>((ref) {
  final path = ref.watch(settingsProvider).value?.modelsPath;
  return PiperModelStore(rootPath: path);
});

final piperModelsProvider = FutureProvider<List<PiperModel>>((ref) {
  return ref.watch(piperModelStoreProvider).scan();
});

final modelsRootProvider = FutureProvider<String>((ref) {
  return ref.watch(piperModelStoreProvider).resolveRoot();
});

final selectedPiperModelProvider = Provider<PiperModel?>((ref) {
  final models = ref.watch(piperModelsProvider).value ?? const <PiperModel>[];
  if (models.isEmpty) {
    return null;
  }
  final id = ref.watch(settingsProvider).value?.piperModelId;
  for (final model in models) {
    if (model.id == id) {
      return model;
    }
  }
  return models.first;
});

final piperDownloaderProvider = Provider<PiperDownloader>((ref) {
  return const PiperDownloader();
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

/// Builds a fresh pair of transports for each reader page.
///
/// The page disposes its own pair when it goes away, so a new page must never
/// reuse dead players. Each call returns a new [ReaderTransports].
final readerTransportsFactoryProvider = Provider<ReaderTransportsFactory>((
  ref,
) {
  return () => ReaderTransports(
    voice: AudioplayersAudioTransport(),
    ambience: AudioplayersAudioTransport(),
  );
});

enum ImportStatus { idle, working, done, error }

class ImportState {
  const ImportState({this.status = ImportStatus.idle, this.message, this.book});

  final ImportStatus status;
  final String? message;
  final Book? book;
}

final importControllerProvider =
    NotifierProvider<ImportController, ImportState>(ImportController.new);

class ImportController extends Notifier<ImportState> {
  @override
  ImportState build() => const ImportState();

  Future<Book?> importEpub(String path) async {
    state = const ImportState(
      status: ImportStatus.working,
      message: 'Importando EPUB…',
    );
    try {
      final book = await ref.read(libraryProvider.notifier).importEpub(path);
      state = ImportState(
        status: ImportStatus.done,
        message: 'Importado: ${book.title}',
        book: book,
      );
      return book;
    } catch (error) {
      state = ImportState(
        status: ImportStatus.error,
        message: 'No se pudo importar: $error',
      );
      return null;
    }
  }
}
