import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../../core/text.dart';
import '../../domain/models.dart';
import '../epub_ingestor.dart';

class ResegmentException implements Exception {
  const ResegmentException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ChapterDiff {
  const ChapterDiff({
    required this.index,
    required this.title,
    required this.changed,
    required this.changedSegments,
    required this.addedSegments,
    required this.removedSegments,
  });

  final int index;
  final String title;
  final bool changed;
  final int changedSegments;
  final int addedSegments;
  final int removedSegments;
}

class ResegmentPlan {
  const ResegmentPlan({
    required this.bookId,
    required this.title,
    required this.canRepair,
    required this.needsRepair,
    required this.oldSegments,
    required this.newSegments,
    required this.changedSegments,
    required this.chapters,
    this.reason,
    this.currentVersion,
    this.targetVersion = 3,
    this.sourceAvailable = false,
  });

  final String bookId;
  final String title;
  final bool canRepair;
  final bool needsRepair;
  final String? reason;
  final int? currentVersion;
  final int targetVersion;
  final bool sourceAvailable;
  final int oldSegments;
  final int newSegments;
  final int changedSegments;
  final List<ChapterDiff> chapters;

  List<int> get changedChapters => [
    for (final chapter in chapters)
      if (chapter.changed) chapter.index,
  ];
}

class ResegmentResult {
  const ResegmentResult({
    required this.plan,
    required this.changed,
    required this.dryRun,
    this.backupId,
  });

  final ResegmentPlan plan;
  final bool changed;
  final bool dryRun;
  final String? backupId;
}

class ResegmentBackup {
  const ResegmentBackup({
    required this.id,
    required this.createdAt,
    required this.changedChapters,
  });

  final String id;
  final String createdAt;
  final List<int> changedChapters;
}

/// Re-segments a book from its `source.epub`, with backups and restore.
///
/// The Flutter pipeline stores chapter audio, not per-segment audio, so changed
/// chapters are marked for re-synthesis and the Studio job resumes them. This
/// is deliberately explicit in the UI: no audio file is silently reused with
/// stale text.
class ResegmentService {
  const ResegmentService({this.ingestor = const EpubIngestor()});

  final EpubIngestor ingestor;

  Future<ResegmentPlan> analyze(Book book) async {
    final directory = book.directoryPath;
    if (directory == null) {
      return ResegmentPlan(
        bookId: book.id,
        title: book.title,
        canRepair: false,
        needsRepair: false,
        reason: 'Sin carpeta de biblioteca.',
        oldSegments: book.segmentCount,
        newSegments: 0,
        changedSegments: 0,
        chapters: const [],
      );
    }
    final source = _sourceFile(book, directory);
    if (source == null) {
      return ResegmentPlan(
        bookId: book.id,
        title: book.title,
        canRepair: false,
        needsRepair: false,
        reason: 'El libro no tiene una copia del EPUB fuente.',
        oldSegments: book.segmentCount,
        newSegments: 0,
        changedSegments: 0,
        chapters: const [],
      );
    }
    if (book.status != 'ready' &&
        book.status != 'imported' &&
        book.status != 'interrupted') {
      return ResegmentPlan(
        bookId: book.id,
        title: book.title,
        canRepair: false,
        needsRepair: false,
        reason: 'El libro no está listo para reparar.',
        oldSegments: book.segmentCount,
        newSegments: 0,
        changedSegments: 0,
        chapters: const [],
      );
    }
    final manifest = await _readManifest(directory);
    final newChapters = await _newChapters(book, source);
    final diffs = _diff(book.chapters, newChapters);
    final currentVersion = (manifest['segmentation_version'] as num?)?.toInt();
    final changedSegments = diffs.fold<int>(
      0,
      (sum, item) => sum + item.changedSegments + item.addedSegments,
    );
    final needsRepair =
        currentVersion == null ||
        currentVersion < 3 ||
        changedSegments > 0 ||
        diffs.any((item) => item.removedSegments > 0) ||
        newChapters.length != book.chapters.length;
    return ResegmentPlan(
      bookId: book.id,
      title: book.title,
      canRepair: true,
      needsRepair: needsRepair,
      currentVersion: currentVersion,
      oldSegments: book.segmentCount,
      newSegments: newChapters.fold<int>(
        0,
        (sum, chapter) => sum + chapter.segments.length,
      ),
      changedSegments: changedSegments,
      chapters: diffs,
      sourceAvailable: true,
    );
  }

  Future<ResegmentResult> apply(Book book, {bool dryRun = false}) async {
    final plan = await analyze(book);
    if (!plan.canRepair) {
      throw ResegmentException(
        plan.reason ?? 'No se puede reparar este libro.',
      );
    }
    if (!plan.needsRepair) {
      return ResegmentResult(plan: plan, changed: false, dryRun: dryRun);
    }
    if (dryRun) {
      return ResegmentResult(plan: plan, changed: true, dryRun: true);
    }
    final directory = book.directoryPath!;
    final source = _sourceFile(book, directory);
    if (source == null) {
      throw const ResegmentException(
        'El libro no tiene una copia del EPUB fuente.',
      );
    }
    final newChapters = await _newChapters(book, source);
    final manifest = await _readManifest(directory);
    final backupId = await _createBackup(book, directory, manifest, plan);
    final oldByIndex = {
      for (final chapter in manifest['chapters'] as List? ?? const [])
        if (chapter is Map<String, dynamic>) chapter['index']: chapter,
    };
    final changed = plan.changedChapters.toSet();
    final chapters = <Map<String, dynamic>>[];
    for (final chapter in newChapters) {
      final old = oldByIndex[chapter.index];
      final keepAudio = old != null && !changed.contains(chapter.index);
      chapters.add({
        'index': chapter.index,
        'title': chapter.title,
        'source_href': chapter.sourceHref,
        'level': chapter.level,
        'kind': chapter.kind,
        'generated_title': chapter.generatedTitle,
        'segments': [
          for (final segment in chapter.segments)
            {
              'id': segment.id,
              'chapter_index': segment.chapterIndex,
              'paragraph_index': segment.paragraphIndex,
              'chunk_index': segment.chunkIndex,
              'text': segment.text,
              'source_href': segment.sourceHref,
              'source_fragment': segment.sourceFragment,
              'boundary': segment.boundary,
              'continuation': segment.continuation,
            },
        ],
        if (keepAudio && old['audio'] is String) 'audio': old['audio'],
        if (keepAudio && old['timing'] is String) 'timing': old['timing'],
        if (keepAudio && old['duration_ms'] is num)
          'duration_ms': old['duration_ms'],
      });
    }
    manifest['chapters'] = chapters;
    manifest['segmentation_version'] = plan.targetVersion;
    manifest['status'] = changed.isEmpty ? book.status : 'interrupted';
    manifest['updated_at'] = DateTime.now().toUtc().toIso8601String();
    await _writeManifest(directory, manifest);
    await _writeMarkdown(directory, book, newChapters);
    return ResegmentResult(
      plan: plan,
      changed: true,
      dryRun: false,
      backupId: backupId,
    );
  }

  Future<List<ResegmentBackup>> backups(Book book) async {
    final directory = book.directoryPath;
    if (directory == null) {
      return const [];
    }
    final root = Directory(p.join(directory, 'backups'));
    if (!await root.exists()) {
      return const [];
    }
    final result = <ResegmentBackup>[];
    await for (final entity in root.list()) {
      if (entity is! Directory) {
        continue;
      }
      final name = p.basename(entity.path);
      if (!name.startsWith('segments-')) {
        continue;
      }
      final meta = await _readJson(File(p.join(entity.path, 'backup.json')));
      result.add(
        ResegmentBackup(
          id: name,
          createdAt: meta['created_at'] as String? ?? '',
          changedChapters: (meta['changed_chapters'] as List? ?? const [])
              .whereType<num>()
              .map((value) => value.toInt())
              .toList(growable: false),
        ),
      );
    }
    result.sort((left, right) => right.id.compareTo(left.id));
    return result;
  }

  Future<void> restore(Book book, String backupId) async {
    final directory = book.directoryPath;
    if (directory == null) {
      throw const ResegmentException('El libro no tiene carpeta.');
    }
    if (p.basename(backupId) != backupId || !backupId.startsWith('segments-')) {
      throw const ResegmentException('Copia de seguridad inválida.');
    }
    final backup = Directory(p.join(directory, 'backups', backupId));
    if (!await backup.exists()) {
      throw const ResegmentException('No existe esa copia de seguridad.');
    }
    await for (final entity in backup.list(recursive: true)) {
      if (entity is! File || p.basename(entity.path) == 'backup.json') {
        continue;
      }
      final relative = p.relative(entity.path, from: backup.path);
      final target = File(p.join(directory, relative));
      await target.parent.create(recursive: true);
      await entity.copy(target.path);
    }
  }

  File? _sourceFile(Book book, String directory) {
    final source = book.sourceEpub ?? 'source.epub';
    final file = File(
      p.isAbsolute(source) ? source : p.join(directory, source),
    );
    return file.existsSync() ? file : null;
  }

  Future<List<Chapter>> _newChapters(Book book, File source) async {
    final ingested = await ingestor.ingest(await source.readAsBytes());
    final chapters = <Chapter>[];
    for (final chapter in ingested.chapters) {
      final segments = <Segment>[];
      var paragraphIndex = 0;
      for (final paragraph in chapter.paragraphs) {
        paragraphIndex += 1;
        final chunks = chunkText(paragraph);
        for (var chunkIndex = 0; chunkIndex < chunks.length; chunkIndex++) {
          segments.add(
            Segment(
              id: _segmentId(chapter.index, paragraphIndex, chunkIndex),
              chapterIndex: chapter.index,
              paragraphIndex: paragraphIndex,
              chunkIndex: chunkIndex,
              text: chunks[chunkIndex],
              sourceHref: chapter.sourceHref,
              boundary: chunkIndex == chunks.length - 1
                  ? 'paragraph'
                  : 'sentence',
              continuation: chunkIndex > 0,
            ),
          );
        }
      }
      if (segments.isEmpty) {
        continue;
      }
      final previous = book.chapters.firstWhere(
        (item) => item.index == chapter.index,
        orElse: () => Chapter(
          index: chapter.index,
          title: chapter.title,
          segments: const [],
        ),
      );
      chapters.add(
        Chapter(
          index: chapter.index,
          title: chapter.title,
          segments: segments,
          sourceHref: chapter.sourceHref,
          level: chapter.level,
          kind: previous.kind,
          number: previous.number,
          generatedTitle: chapter.title.startsWith('Capítulo '),
        ),
      );
    }
    return chapters;
  }

  List<ChapterDiff> _diff(
    List<Chapter> oldChapters,
    List<Chapter> newChapters,
  ) {
    final oldByIndex = {
      for (final chapter in oldChapters) chapter.index: chapter,
    };
    final diffs = <ChapterDiff>[];
    for (final chapter in newChapters) {
      final old = oldByIndex[chapter.index];
      if (old == null) {
        diffs.add(
          ChapterDiff(
            index: chapter.index,
            title: chapter.title,
            changed: true,
            changedSegments: 0,
            addedSegments: chapter.segments.length,
            removedSegments: 0,
          ),
        );
        continue;
      }
      final oldSegments = {
        for (final segment in old.segments) segment.id: segment,
      };
      final newSegments = {
        for (final segment in chapter.segments) segment.id: segment,
      };
      var changed = 0;
      var added = 0;
      var removed = 0;
      for (final entry in newSegments.entries) {
        final previous = oldSegments[entry.key];
        if (previous == null) {
          added += 1;
        } else if (previous.text != entry.value.text) {
          changed += 1;
        }
      }
      for (final id in oldSegments.keys) {
        if (!newSegments.containsKey(id)) {
          removed += 1;
        }
      }
      diffs.add(
        ChapterDiff(
          index: chapter.index,
          title: chapter.title,
          changed: changed > 0 || added > 0 || removed > 0,
          changedSegments: changed,
          addedSegments: added,
          removedSegments: removed,
        ),
      );
    }
    final known = {for (final chapter in newChapters) chapter.index};
    for (final chapter in oldChapters) {
      if (!known.contains(chapter.index)) {
        diffs.add(
          ChapterDiff(
            index: chapter.index,
            title: chapter.title,
            changed: true,
            changedSegments: 0,
            addedSegments: 0,
            removedSegments: chapter.segments.length,
          ),
        );
      }
    }
    diffs.sort((left, right) => left.index.compareTo(right.index));
    return diffs;
  }

  String _segmentId(int chapter, int paragraph, int chunk) {
    return 'c${chapter.toString().padLeft(3, '0')}'
        'p${paragraph.toString().padLeft(4, '0')}'
        's${chunk.toString().padLeft(2, '0')}';
  }

  Future<Map<String, dynamic>> _readManifest(String directory) async {
    final file = File(p.join(directory, 'manifest.json'));
    final decoded = jsonDecode(await file.readAsString());
    if (decoded is! Map<String, dynamic>) {
      throw const ResegmentException('El manifiesto no es válido.');
    }
    return decoded;
  }

  Future<void> _writeManifest(
    String directory,
    Map<String, dynamic> manifest,
  ) async {
    final file = File(p.join(directory, 'manifest.json'));
    final temporary = File('${file.path}.part');
    await temporary.writeAsString(
      const JsonEncoder.withIndent('  ').convert(manifest),
      flush: true,
    );
    if (await file.exists()) {
      await file.delete();
    }
    await temporary.rename(file.path);
  }

  Future<void> _writeMarkdown(
    String directory,
    Book book,
    List<Chapter> chapters,
  ) async {
    final buffer = StringBuffer()
      ..writeln('# ${book.title}')
      ..writeln()
      ..writeln('*${book.author}*')
      ..writeln();
    for (final chapter in chapters) {
      buffer
        ..writeln('## ${chapter.title}')
        ..writeln();
      for (final segment in chapter.segments) {
        buffer
          ..writeln(segment.text)
          ..writeln();
      }
    }
    final file = File(p.join(directory, 'book.md'));
    final temporary = File('${file.path}.part');
    await temporary.writeAsString(buffer.toString(), flush: true);
    if (await file.exists()) {
      await file.delete();
    }
    await temporary.rename(file.path);
  }

  Future<String> _createBackup(
    Book book,
    String directory,
    Map<String, dynamic> manifest,
    ResegmentPlan plan,
  ) async {
    final stamp = DateTime.now()
        .toUtc()
        .toIso8601String()
        .replaceAll(RegExp(r'[^0-9]'), '')
        .substring(0, 14);
    final id =
        'segments-$stamp-${DateTime.now().microsecondsSinceEpoch % 1000000}';
    final root = Directory(p.join(directory, 'backups', id));
    await root.create(recursive: true);
    await File(p.join(directory, 'manifest.json'))
        .copy(p.join(root.path, 'manifest.json'));
    final markdown = File(p.join(directory, 'book.md'));
    if (await markdown.exists()) {
      await markdown.copy(p.join(root.path, 'book.md'));
    }
    final changed = plan.changedChapters.toSet();
    for (final item in manifest['chapters'] as List? ?? const []) {
      if (item is! Map<String, dynamic>) {
        continue;
      }
      final index = (item['index'] as num?)?.toInt();
      if (index == null || !changed.contains(index)) {
        continue;
      }
      for (final key in const ['audio', 'timing']) {
        final value = item[key];
        if (value is! String || value.isEmpty) {
          continue;
        }
        final source = File(p.join(directory, value));
        if (!await source.exists()) {
          continue;
        }
        final target = File(p.join(root.path, value));
        await target.parent.create(recursive: true);
        await source.copy(target.path);
      }
    }
    await File(p.join(root.path, 'backup.json')).writeAsString(
      const JsonEncoder.withIndent('  ').convert({
        'created_at': DateTime.now().toUtc().toIso8601String(),
        'reason': 'resegment',
        'changed_chapters': plan.changedChapters,
        'changed_segments': plan.changedSegments,
      }),
      flush: true,
    );
    return id;
  }

  Future<Map<String, dynamic>> _readJson(File file) async {
    try {
      final decoded = jsonDecode(await file.readAsString());
      return decoded is Map<String, dynamic> ? decoded : {};
    } on FormatException {
      return {};
    } on FileSystemException {
      return {};
    }
  }
}
