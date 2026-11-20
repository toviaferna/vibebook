import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:html/parser.dart' as html_parser;
import 'package:path/path.dart' as p;

import '../domain/models.dart';

/// Reads the original XHTML and images from a book's `source.epub`.
///
/// The archive is cached per path. Nothing is written to disk; the reader only
/// needs the bytes to render the original layout.
class EpubOriginal {
  static final _archives = <String, Archive>{};

  static Future<Archive?> _archive(Book book) async {
    final directory = book.directoryPath;
    final source = book.sourceEpub ?? 'source.epub';
    final path = p.isAbsolute(source) || directory == null
        ? source
        : p.join(directory, source);
    final cached = _archives[path];
    if (cached != null) {
      return cached;
    }
    final file = File(path);
    if (!await file.exists()) {
      return null;
    }
    try {
      final archive = ZipDecoder().decodeBytes(
        await file.readAsBytes(),
        verify: false,
      );
      _archives[path] = archive;
      return archive;
    } catch (_) {
      return null;
    }
  }

  /// Returns sanitized XHTML for [chapter], or null when the EPUB is missing.
  static Future<String?> chapterHtml(Book book, Chapter chapter) async {
    final archive = await _archive(book);
    final href = chapter.sourceHref;
    if (archive == null || href == null || href.isEmpty) {
      return null;
    }
    final entry = _findEntry(archive, href);
    if (entry == null) {
      return null;
    }
    final decoded = _decode(entry.content);
    final document = html_parser.parse(decoded);
    for (final element in document.querySelectorAll(
      'script, style, iframe, object, embed, link, meta',
    )) {
      element.remove();
    }
    for (final element in document.querySelectorAll('*')) {
      final attributes = element.attributes.keys.toList(growable: false);
      for (final name in attributes) {
        final value = element.attributes[name] ?? '';
        final lower = name.toString().toLowerCase();
        if (lower.startsWith('on') ||
            (lower == 'href' &&
                value.trim().toLowerCase().startsWith('javascript:'))) {
          element.attributes.remove(name);
        }
      }
    }
    final body = document.body;
    return body?.outerHtml ?? document.outerHtml;
  }

  /// Resolves an image source relative to the chapter and returns its bytes.
  static Future<Uint8List?> imageBytes(
    Book book,
    Chapter chapter,
    String source,
  ) async {
    final archive = await _archive(book);
    if (archive != null) {
      final href = chapter.sourceHref;
      final candidates = <String>[
        source,
        if (href != null)
          p.posix.normalize(
            p.posix.join(p.posix.dirname(href.split('#').first), source),
          ),
      ];
      for (final candidate in candidates) {
        final entry = _findEntry(archive, candidate);
        if (entry != null) {
          return Uint8List.fromList(entry.content);
        }
      }
    }
    // Fallback: an image that the importer copied next to the book.
    final directory = book.directoryPath;
    if (directory != null) {
      final basename = p.posix.basename(source);
      for (final image in book.images) {
        final path = image.path;
        if (path == null) {
          continue;
        }
        if (p.posix.basename(path) == basename) {
          final file = File(p.join(directory, path));
          if (await file.exists()) {
            return file.readAsBytes();
          }
        }
      }
    }
    return null;
  }

  /// Maps an internal link to a chapter index, or null when it is external.
  static int? chapterForLink(Book book, Chapter chapter, String href) {
    final cleaned = href.split('#').first;
    if (cleaned.isEmpty) {
      return chapter.index;
    }
    final target = p.posix.normalize(
      p.posix.join(p.posix.dirname(chapter.sourceHref ?? ''), cleaned),
    );
    for (final item in book.chapters) {
      final source = item.sourceHref;
      if (source == null) {
        continue;
      }
      final normalized = p.posix.normalize(source.split('#').first);
      if (normalized == target ||
          p.posix.basename(normalized) == p.posix.basename(target)) {
        return item.index;
      }
    }
    return null;
  }

  static ArchiveFile? _findEntry(Archive archive, String href) {
    final raw = href.split('#').first;
    String cleaned;
    try {
      cleaned = Uri.decodeFull(raw);
    } on ArgumentError {
      cleaned = raw;
    }
    final normalized = p.posix.normalize(cleaned);
    final basename = p.posix.basename(normalized);
    ArchiveFile? fallback;
    for (final file in archive) {
      if (!file.isFile) {
        continue;
      }
      final name = p.posix.normalize(file.name);
      if (name == normalized) {
        return file;
      }
      if (name.endsWith('/$normalized')) {
        return file;
      }
      if (fallback == null && p.posix.basename(name) == basename) {
        fallback = file;
      }
    }
    return fallback;
  }

  static String _decode(List<int> bytes) {
    try {
      return utf8.decode(bytes);
    } on FormatException {
      return latin1.decode(bytes);
    }
  }
}
