import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:collection/collection.dart';
import 'package:html/parser.dart' as html_parser;
import 'package:path/path.dart' as p;
import 'package:xml/xml.dart';

import '../core/text.dart';

class IngestedBook {
  const IngestedBook({
    required this.title,
    required this.author,
    required this.language,
    required this.declaredLanguage,
    required this.chapters,
    this.images = const [],
    this.coverBytes,
    this.coverExtension,
  });

  final String title;
  final String author;
  final String language;
  final String declaredLanguage;
  final List<IngestedChapter> chapters;
  final List<IngestedImage> images;
  final Uint8List? coverBytes;
  final String? coverExtension;
}

class IngestedChapter {
  const IngestedChapter({
    required this.index,
    required this.title,
    required this.paragraphs,
    this.sourceHref,
    this.level = 1,
  });

  final int index;
  final String title;
  final List<String> paragraphs;
  final String? sourceHref;
  final int level;
}

class IngestedImage {
  const IngestedImage({
    required this.id,
    required this.bytes,
    required this.extension,
    this.alt = '',
    this.caption,
  });

  final String id;
  final Uint8List bytes;
  final String extension;
  final String alt;
  final String? caption;
}

class EpubIngestor {
  const EpubIngestor();

  Future<IngestedBook> ingest(Uint8List bytes) async {
    final archive = ZipDecoder().decodeBytes(bytes, verify: true);
    final files = <String, ArchiveFile>{};
    for (final file in archive) {
      if (file.isFile) {
        files[file.name] = file;
      }
    }
    final containerFile = files['META-INF/container.xml'];
    if (containerFile == null) {
      throw const FormatException('El EPUB no contiene META-INF/container.xml.');
    }
    final container = XmlDocument.parse(decodeTextBytes(containerFile.content));
    final rootfile = container.descendants
        .whereType<XmlElement>()
        .firstWhere(
          (element) => element.name.local == 'rootfile',
          orElse: () => throw const FormatException('El EPUB no declara un OPF.'),
        )
        .getAttribute('full-path');
    if (rootfile == null || rootfile.isEmpty) {
      throw const FormatException('El EPUB no declara un OPF válido.');
    }
    final opfFile = files[rootfile];
    if (opfFile == null) {
      throw const FormatException('No se encontró el OPF del EPUB.');
    }
    final opf = XmlDocument.parse(decodeTextBytes(opfFile.content));
    final metadata = _firstElement(opf, 'metadata');
    final title = _textOf(metadata, 'title') ?? 'Sin título';
    final author = _textOf(metadata, 'creator') ?? 'Desconocido';
    final declared = _textOf(metadata, 'language') ?? 'es';
    final manifest = _firstElement(opf, 'manifest');
    final spine = _firstElement(opf, 'spine');
    final items = <String, _ManifestItem>{};
    if (manifest != null) {
      for (final element in manifest.descendants.whereType<XmlElement>()) {
        if (element.name.local != 'item') {
          continue;
        }
        final id = element.getAttribute('id');
        final href = element.getAttribute('href');
        if (id == null || href == null) {
          continue;
        }
        items[id] = _ManifestItem(
          id: id,
          href: href,
          mediaType: element.getAttribute('media-type') ?? '',
          properties: element.getAttribute('properties') ?? '',
        );
      }
    }
    final opfDirectory = p.posix.dirname(rootfile);
    final chapters = <IngestedChapter>[];
    final images = <IngestedImage>[];
    final spineIds = <String>[];
    if (spine != null) {
      for (final element in spine.descendants.whereType<XmlElement>()) {
        if (element.name.local == 'itemref') {
          final idref = element.getAttribute('idref');
          if (idref != null) {
            spineIds.add(idref);
          }
        }
      }
    }
    var chapterIndex = 0;
    for (final idref in spineIds) {
      final item = items[idref];
      if (item == null || item.mediaType != 'application/xhtml+xml') {
        continue;
      }
      if (item.properties.contains('nav')) {
        continue;
      }
      final path = _resolve(opfDirectory, item.href);
      final file = files[path];
      if (file == null) {
        continue;
      }
      final document = html_parser.parse(decodeTextBytes(file.content));
      final heading = document.querySelector('h1, h2, h3, h4');
      final titleText = normalizeWhitespace(heading?.text ?? '');
      final paragraphs = <String>[];
      for (final element in document.querySelectorAll('p, blockquote')) {
        if (element.querySelector('p, blockquote') != null) {
          continue;
        }
        final text = normalizeWhitespace(element.text);
        if (text.isNotEmpty) {
          paragraphs.add(text);
        }
      }
      if (paragraphs.isEmpty) {
        final body = document.body;
        if (body != null) {
          final text = normalizeWhitespace(body.text);
          if (text.isNotEmpty) {
            paragraphs.add(text);
          }
        }
      }
      if (paragraphs.isEmpty) {
        continue;
      }
      chapterIndex += 1;
      chapters.add(
        IngestedChapter(
          index: chapterIndex,
          title: titleText.isEmpty ? 'Capítulo $chapterIndex' : titleText,
          paragraphs: paragraphs,
          sourceHref: path,
          level: heading?.localName == 'h1' ? 1 : 2,
        ),
      );
      for (final image in document.querySelectorAll('img')) {
        final src = image.attributes['src'];
        if (src == null || src.isEmpty) {
          continue;
        }
        final imagePath = _resolve(p.posix.dirname(path), src);
        final imageFile = files[imagePath];
        if (imageFile == null) {
          continue;
        }
        final extension = p.posix.extension(imagePath).replaceFirst('.', '').toLowerCase();
        if (!{'jpg', 'jpeg', 'png', 'gif', 'webp'}.contains(extension)) {
          continue;
        }
        images.add(
          IngestedImage(
            id: 'img-${images.length + 1}',
            bytes: Uint8List.fromList(imageFile.content),
            extension: extension == 'jpeg' ? 'jpg' : extension,
            alt: image.attributes['alt'] ?? '',
            caption: image.attributes['title'],
          ),
        );
      }
    }
    if (chapters.isEmpty) {
      throw const FormatException('El EPUB no tiene capítulos legibles.');
    }
    final rawLanguage = declared.split('-').first.toLowerCase();
    final sampleText = chapters
        .expand((chapter) => chapter.paragraphs)
        .join(' ')
        .let((value) => value.length > 8000 ? value.substring(0, 8000) : value);
    final detected = detectLanguage(sampleText);
    final language = rawLanguage == 'en' || rawLanguage == 'es'
        ? (detected ?? rawLanguage)
        : (detected ?? declared);
    var coverBytes = <int>[];
    String? coverExtension;
    for (final item in items.values) {
      if (!item.properties.contains('cover-image')) {
        continue;
      }
      final file = files[_resolve(opfDirectory, item.href)];
      if (file != null) {
        coverBytes = file.content;
        coverExtension = p.posix.extension(item.href).replaceFirst('.', '').toLowerCase();
        break;
      }
    }
    if (coverBytes.isEmpty) {
      final coverId = metadata?.descendants
          .whereType<XmlElement>()
          .where((element) => element.name.local == 'meta' && element.getAttribute('name') == 'cover')
          .map((element) => element.getAttribute('content'))
          .whereType<String>()
          .firstOrNull;
      final coverItem = coverId == null ? null : items[coverId];
      if (coverItem != null) {
        final file = files[_resolve(opfDirectory, coverItem.href)];
        if (file != null) {
          coverBytes = file.content;
          coverExtension = p.posix.extension(coverItem.href).replaceFirst('.', '').toLowerCase();
        }
      }
    }
    return IngestedBook(
      title: title,
      author: author,
      language: language,
      declaredLanguage: declared,
      chapters: chapters,
      images: images,
      coverBytes: coverBytes.isEmpty ? null : Uint8List.fromList(coverBytes),
      coverExtension: coverExtension,
    );
  }

  XmlElement? _firstElement(XmlDocument document, String localName) {
    for (final element in document.descendants.whereType<XmlElement>()) {
      if (element.name.local == localName) {
        return element;
      }
    }
    return null;
  }

  String? _textOf(XmlElement? parent, String localName) {
    if (parent == null) {
      return null;
    }
    for (final element in parent.descendants.whereType<XmlElement>()) {
      if (element.name.local == localName) {
        final text = normalizeWhitespace(element.innerText);
        if (text.isNotEmpty) {
          return text;
        }
      }
    }
    return null;
  }

  String _resolve(String base, String href) {
    final decoded = Uri.decodeFull(href.split('#').first);
    if (decoded.startsWith('/')) {
      return decoded.substring(1);
    }
    return p.posix.normalize(p.posix.join(base, decoded));
  }
}

class _ManifestItem {
  const _ManifestItem({
    required this.id,
    required this.href,
    required this.mediaType,
    required this.properties,
  });

  final String id;
  final String href;
  final String mediaType;
  final String properties;
}

extension _Let<T> on T {
  R let<R>(R Function(T) block) => block(this);
}
