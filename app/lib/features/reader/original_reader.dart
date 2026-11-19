import 'dart:typed_data';

import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';
import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/design/tokens.dart';
import '../../data/epub_original.dart';
import '../../domain/models.dart';

/// Renders the EPUB's own XHTML for the current chapter.
///
/// Scripts, styles, iframes and event attributes are removed before rendering.
/// Images are resolved from the EPUB archive; missing images show a placeholder.
class OriginalReader extends StatelessWidget {
  const OriginalReader({
    super.key,
    required this.book,
    required this.chapter,
    required this.palette,
    required this.preferences,
    this.onChapterLink,
  });

  final Book book;
  final Chapter chapter;
  final ReaderPalette palette;
  final ReaderPreferences preferences;
  final ValueChanged<int>? onChapterLink;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: EpubOriginal.chapterHtml(book, chapter),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final html = snapshot.data;
        if (html == null || html.trim().isEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'No se pudo leer el XHTML original de este capítulo. '
                'El modo Texto sigue disponible.',
                textAlign: TextAlign.center,
                style: TextStyle(color: palette.inkSoft),
              ),
            ),
          );
        }
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(28, 24, 28, 48),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: HtmlWidget(
                html,
                textStyle: TextStyle(
                  fontSize: preferences.fontSize,
                  height: 1.65,
                  color: palette.ink,
                ),
                factoryBuilder: () => _EpubFactory(book, chapter),
                onTapUrl: (url) async {
                  final chapterIndex = EpubOriginal.chapterForLink(
                    book,
                    chapter,
                    url,
                  );
                  if (chapterIndex != null) {
                    onChapterLink?.call(chapterIndex);
                    return true;
                  }
                  final uri = Uri.tryParse(url);
                  if (uri != null &&
                      (uri.scheme == 'http' || uri.scheme == 'https')) {
                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                  return true;
                },
              ),
            ),
          ),
        );
      },
    );
  }
}

class _EpubFactory extends WidgetFactory {
  _EpubFactory(this.book, this.chapter);

  final Book book;
  final Chapter chapter;
  final Map<String, Future<Uint8List?>> _images = {};

  @override
  Widget? buildImage(BuildTree tree, ImageMetadata data) {
    final source = data.sources.isNotEmpty ? data.sources.first : null;
    if (source == null) {
      return super.buildImage(tree, data);
    }
    final url = source.url;
    if (url.startsWith('http') ||
        url.startsWith('data:') ||
        url.startsWith('file:')) {
      return super.buildImage(tree, data);
    }
    final future = _images.putIfAbsent(
      url,
      () => EpubOriginal.imageBytes(book, chapter, url),
    );
    return FutureBuilder<Uint8List?>(
      future: future,
      builder: (context, snapshot) {
        final bytes = snapshot.data;
        if (bytes == null) {
          return Container(
            height: 80,
            alignment: Alignment.center,
            margin: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFFD8CDBD)),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              data.alt ?? 'Ilustración no disponible',
              style: const TextStyle(fontSize: 12),
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Image.memory(bytes, fit: BoxFit.contain),
        );
      },
    );
  }
}
