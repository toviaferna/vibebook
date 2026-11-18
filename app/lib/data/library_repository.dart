import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../core/text.dart';
import '../domain/models.dart';
import 'epub_ingestor.dart';

class LibraryRepository {
  LibraryRepository({required this.ingestor, String? libraryPath}) {
    _libraryPath = libraryPath;
  }

  final EpubIngestor ingestor;
  String? _libraryPath;

  String? get configuredPath => _libraryPath;

  Future<String> resolveLibraryPath() async {
    if (_libraryPath != null && _libraryPath!.trim().isNotEmpty) {
      return _libraryPath!;
    }
    final environment = Platform.environment;
    String? candidate;
    if (Platform.isWindows) {
      final local = environment['LOCALAPPDATA'];
      if (local != null && local.isNotEmpty) {
        candidate = p.join(local, 'vibebook', 'vibebook', 'library');
      }
    } else if (Platform.isMacOS) {
      final home = environment['HOME'];
      if (home != null && home.isNotEmpty) {
        candidate = p.join(home, 'Library', 'Application Support', 'vibebook', 'library');
      }
    } else if (Platform.isLinux) {
      final home = environment['HOME'];
      final data = environment['XDG_DATA_HOME'];
      if (data != null && data.isNotEmpty) {
        candidate = p.join(data, 'vibebook', 'library');
      } else if (home != null && home.isNotEmpty) {
        candidate = p.join(home, '.local', 'share', 'vibebook', 'library');
      }
    }
    if (candidate == null) {
      final documents = await getApplicationDocumentsDirectory();
      candidate = p.join(documents.path, 'library');
    }
    _libraryPath = candidate;
    return candidate;
  }

  Future<void> setLibraryPath(String? path) async {
    _libraryPath = path;
  }

  Future<List<Book>> scan({String? query}) async {
    final root = Directory(await resolveLibraryPath());
    if (!await root.exists()) {
      await root.create(recursive: true);
      return const [];
    }
    final normalizedQuery = query?.trim().toLowerCase();
    final books = <Book>[];
    await for (final entity in root.list(followLinks: false)) {
      if (entity is! Directory) {
        continue;
      }
      final name = p.basename(entity.path);
      if (name.startsWith('.')) {
        continue;
      }
      final manifest = File(p.join(entity.path, 'manifest.json'));
      if (!await manifest.exists()) {
        continue;
      }
      try {
        final contents = await manifest.readAsString();
        final book = Book.fromJsonString(
          contents,
          id: name,
          manifestPath: manifest.path,
          directoryPath: entity.path,
        );
        if (normalizedQuery != null && normalizedQuery.isNotEmpty) {
          final haystack = '${book.title} ${book.author} ${book.language}'.toLowerCase();
          if (!haystack.contains(normalizedQuery)) {
            continue;
          }
        }
        books.add(book);
      } catch (_) {
        // A corrupt book must not break the whole library.
      }
    }
    books.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
    return books;
  }

  Future<Book?> get(String id) async {
    final root = await resolveLibraryPath();
    final directory = Directory(p.join(root, id));
    final manifest = File(p.join(directory.path, 'manifest.json'));
    if (!await manifest.exists()) {
      return null;
    }
    final book = Book.fromJsonString(
      await manifest.readAsString(),
      id: id,
      manifestPath: manifest.path,
      directoryPath: directory.path,
    );
    return book;
  }

  Future<Book> importEpub(String sourcePath) async {
    final source = File(sourcePath);
    if (!await source.exists()) {
      throw FileSystemException('No existe el EPUB seleccionado.', sourcePath);
    }
    final bytes = await source.readAsBytes();
    final ingested = await ingestor.ingest(bytes);
    final rootPath = await resolveLibraryPath();
    final root = Directory(rootPath);
    await root.create(recursive: true);
    final hash = shortHash(bytes);
    final id = '${slugify(ingested.title)}-$hash';
    final target = Directory(p.join(rootPath, id));
    final existingManifest = File(p.join(target.path, 'manifest.json'));
    if (await existingManifest.exists()) {
      return Book.fromJsonString(
        await existingManifest.readAsString(),
        id: id,
        manifestPath: existingManifest.path,
        directoryPath: target.path,
      );
    }
    final temporary = Directory(p.join(rootPath, '.import-${DateTime.now().microsecondsSinceEpoch}'));
    await temporary.create(recursive: true);
    try {
      final sourceCopy = File(p.join(temporary.path, 'source.epub'));
      await sourceCopy.writeAsBytes(bytes, flush: true);
      final coverName = await _writeCover(temporary, ingested);
      final imageEntries = await _writeImages(temporary, ingested);
      final chapters = <Map<String, dynamic>>[];
      final toc = <Map<String, dynamic>>[];
      final markdown = StringBuffer()
        ..writeln('# ${ingested.title}')
        ..writeln()
        ..writeln('*${ingested.author}*')
        ..writeln();
      for (final chapter in ingested.chapters) {
        final segments = <Map<String, dynamic>>[];
        var paragraphIndex = 0;
        for (final paragraph in chapter.paragraphs) {
          paragraphIndex += 1;
          final chunks = chunkText(paragraph);
          for (var chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
            segments.add({
              'id': _segmentId(chapter.index, paragraphIndex, chunkIndex),
              'chapter_index': chapter.index,
              'paragraph_index': paragraphIndex,
              'chunk_index': chunkIndex,
              'text': chunks[chunkIndex],
              'source_href': chapter.sourceHref,
              'boundary': chunkIndex == chunks.length - 1 ? 'paragraph' : 'sentence',
              'continuation': chunkIndex > 0,
            });
          }
          markdown
            ..writeln(paragraph)
            ..writeln();
        }
        if (segments.isEmpty) {
          continue;
        }
        chapters.add({
          'index': chapter.index,
          'title': chapter.title,
          'segments': segments,
          'source_href': chapter.sourceHref,
          'level': chapter.level,
          'kind': 'chapter',
          'generated_title': chapter.title.startsWith('Capítulo '),
        });
        toc.add({
          'title': chapter.title,
          'level': chapter.level,
          'chapter_index': chapter.index,
          'kind': 'chapter',
          'children': <Map<String, dynamic>>[],
        });
      }
      if (chapters.isEmpty) {
        throw const FormatException('El EPUB no produjo capítulos legibles.');
      }
      final now = DateTime.now().toUtc().toIso8601String();
      final manifest = <String, dynamic>{
        'schema_version': 2,
        'segmentation_version': 3,
        'pause_policy_version': 1,
        'id': id,
        'title': ingested.title,
        'author': ingested.author,
        'language': ingested.language,
        'language_declared': ingested.declaredLanguage,
        'language_checked': true,
        'voice': 'es-MX-JorgeNeural',
        'engine': 'edge',
        'style': 'neutral',
        'rate': '-10%',
        'status': 'imported',
        'chapters': chapters,
        'toc': toc,
        'images': imageEntries,
        'cover': coverName,
        'source_epub': 'source.epub',
        'created_at': now,
        'updated_at': now,
      };
      final manifestFile = File(p.join(temporary.path, 'manifest.json'));
      await manifestFile.writeAsString(const JsonEncoder.withIndent('  ').convert(manifest), flush: true);
      final bookMd = File(p.join(temporary.path, 'book.md'));
      await bookMd.writeAsString(markdown.toString(), flush: true);
      if (await target.exists()) {
        await target.delete(recursive: true);
      }
      await temporary.rename(target.path);
      final targetManifest = File(p.join(target.path, 'manifest.json'));
      return Book.fromJsonString(
        await targetManifest.readAsString(),
        id: id,
        manifestPath: targetManifest.path,
        directoryPath: target.path,
      );
    } catch (_) {
      if (await temporary.exists()) {
        await temporary.delete(recursive: true);
      }
      rethrow;
    }
  }

  Future<String?> _writeCover(Directory directory, IngestedBook ingested) async {
    final bytes = ingested.coverBytes;
    if (bytes == null || bytes.isEmpty) {
      return null;
    }
    final extension = ingested.coverExtension ?? 'jpg';
    final safeExtension = const {'jpg', 'jpeg', 'png', 'gif', 'webp'}.contains(extension) ? extension : 'jpg';
    final name = 'cover.$safeExtension';
    await File(p.join(directory.path, name)).writeAsBytes(bytes, flush: true);
    return name;
  }

  Future<List<Map<String, dynamic>>> _writeImages(Directory directory, IngestedBook ingested) async {
    final result = <Map<String, dynamic>>[];
    if (ingested.images.isEmpty) {
      return result;
    }
    final imagesDirectory = Directory(p.join(directory.path, 'images'));
    await imagesDirectory.create(recursive: true);
    for (final image in ingested.images) {
      final name = '${image.id}.${image.extension}';
      await File(p.join(imagesDirectory.path, name)).writeAsBytes(image.bytes, flush: true);
      result.add({
        'id': image.id,
        'path': p.posix.join('images', name),
        'alt': image.alt,
        'caption': image.caption,
        'role': 'illustration',
        'position': 'after',
      });
    }
    return result;
  }

  String _segmentId(int chapter, int paragraph, int chunk) {
    return 'c${chapter.toString().padLeft(3, '0')}'
        'p${paragraph.toString().padLeft(4, '0')}'
        's${chunk.toString().padLeft(2, '0')}';
  }
}

Future<Uint8List> readFileBytes(String path) async {
  return File(path).readAsBytes();
}
