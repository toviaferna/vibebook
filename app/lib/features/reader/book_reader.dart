import 'dart:io';

import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;

import '../../core/design/tokens.dart';
import '../../domain/models.dart';
import 'book_paginator.dart';

/// Paginated reading mode with one page on narrow screens and two on desktop.
class BookReader extends StatefulWidget {
  const BookReader({
    super.key,
    required this.book,
    required this.chapter,
    required this.palette,
    required this.preferences,
    this.activeSegmentId,
    this.onPageChanged,
  });

  final Book book;
  final Chapter chapter;
  final ReaderPalette palette;
  final ReaderPreferences preferences;
  final String? activeSegmentId;
  final ValueChanged<int>? onPageChanged;

  @override
  State<BookReader> createState() => _BookReaderState();
}

class _BookReaderState extends State<BookReader> {
  final _controller = PageController();
  Size? _lastSize;
  List<BookPage> _pages = const [];
  int _spread = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant BookReader oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.chapter.index != widget.chapter.index) {
      _pages = const [];
      _lastSize = null;
      _spread = 0;
      if (_controller.hasClients) {
        _controller.jumpToPage(0);
      }
      return;
    }
    if (oldWidget.activeSegmentId != widget.activeSegmentId) {
      _followActiveSegment();
    }
  }

  void _followActiveSegment() {
    final segment = widget.activeSegmentId;
    if (segment == null || _pages.isEmpty) {
      return;
    }
    final index = _pages.indexWhere(
      (page) => page.segmentIds.contains(segment),
    );
    if (index < 0) {
      return;
    }
    final spread = _perSpread == 2 ? index ~/ 2 : index;
    if (spread != _spread && _controller.hasClients) {
      _controller.animateToPage(
        spread,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
      );
    }
  }

  int get _perSpread {
    final size = _lastSize;
    return size != null && size.width >= 1000 ? 2 : 1;
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.palette;
    final style = TextStyle(
      fontFamily: widget.preferences.fontFamily.toLowerCase().contains('sans')
          ? null
          : 'serif',
      fontSize: widget.preferences.fontSize,
      height: 1.6,
      color: palette.ink,
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        const padding = EdgeInsets.fromLTRB(28, 18, 28, 10);
        final size = Size(
          constraints.maxWidth - padding.horizontal,
          constraints.maxHeight - padding.vertical,
        );
        if (_lastSize != size) {
          _lastSize = size;
          final images = widget.book.images
              .where((image) => image.chapterIndex == widget.chapter.index)
              .toList(growable: false);
          _pages = const BookPaginator().paginate(
            chapter: widget.chapter,
            size: size,
            style: style,
            images: images,
            textScaler: MediaQuery.textScalerOf(context),
          );
          _spread = _spread.clamp(
            0,
            _spreadCount(_pages.length, _perSpread) - 1,
          );
        }
        if (_pages.isEmpty) {
          return Center(
            child: Text(
              'Este capítulo no tiene texto legible.',
              style: TextStyle(color: palette.inkSoft),
            ),
          );
        }
        final perSpread = _perSpread;
        final spreadCount = _spreadCount(_pages.length, perSpread);
        return Column(
          children: [
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: spreadCount,
                onPageChanged: (value) {
                  setState(() => _spread = value);
                  widget.onPageChanged?.call(value * perSpread);
                },
                itemBuilder: (context, spread) {
                  final first = spread * perSpread;
                  final items = <Widget>[];
                  for (var offset = 0; offset < perSpread; offset++) {
                    final index = first + offset;
                    if (index >= _pages.length) {
                      break;
                    }
                    if (offset > 0) {
                      items.add(
                        VerticalDivider(
                          width: 1,
                          thickness: 1,
                          color: palette.line.withValues(alpha: 0.5),
                        ),
                      );
                    }
                    items.add(
                      Expanded(
                        child: _PageView(
                          page: _pages[index],
                          palette: palette,
                          preferences: widget.preferences,
                          activeSegmentId: widget.activeSegmentId,
                          book: widget.book,
                        ),
                      ),
                    );
                  }
                  return Padding(
                    padding: padding,
                    child: Row(children: items),
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(28, 0, 28, 12),
              child: Row(
                children: [
                  IconButton(
                    tooltip: 'Página anterior',
                    onPressed: _spread == 0
                        ? null
                        : () => _controller.previousPage(
                            duration: const Duration(milliseconds: 220),
                            curve: Curves.easeOut,
                          ),
                    icon: const Icon(Icons.chevron_left),
                    color: palette.inkSoft,
                  ),
                  Expanded(
                    child: Text(
                      perSpread == 2
                          ? 'Páginas ${firstPage(_spread, perSpread)}–${lastPage(_spread, perSpread, _pages.length)} de ${_pages.length}'
                          : 'Página ${_spread + 1} de ${_pages.length}',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 11,
                        color: palette.inkFaint,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Página siguiente',
                    onPressed: _spread >= spreadCount - 1
                        ? null
                        : () => _controller.nextPage(
                            duration: const Duration(milliseconds: 220),
                            curve: Curves.easeOut,
                          ),
                    icon: const Icon(Icons.chevron_right),
                    color: palette.inkSoft,
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

int _spreadCount(int pageCount, int perSpread) {
  if (pageCount == 0) {
    return 0;
  }
  return (pageCount / perSpread).ceil();
}

int firstPage(int spread, int perSpread) => spread * perSpread + 1;

int lastPage(int spread, int perSpread, int pageCount) {
  final last = spread * perSpread + perSpread;
  return last > pageCount ? pageCount : last;
}

class _PageView extends StatelessWidget {
  const _PageView({
    required this.page,
    required this.palette,
    required this.preferences,
    required this.activeSegmentId,
    required this.book,
  });

  final BookPage page;
  final ReaderPalette palette;
  final ReaderPreferences preferences;
  final String? activeSegmentId;
  final Book book;

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      fontFamily: preferences.fontFamily.toLowerCase().contains('sans')
          ? null
          : 'serif',
      fontSize: preferences.fontSize,
      height: 1.6,
      color: palette.ink,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final block in page.blocks)
          if (block.isImage)
            _image(block.image!)
          else
            Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Container(
                decoration: block.segmentId == activeSegmentId
                    ? BoxDecoration(
                        color: palette.accentSoft.withValues(alpha: 0.45),
                        borderRadius: BorderRadius.circular(4),
                      )
                    : null,
                padding: block.segmentId == activeSegmentId
                    ? const EdgeInsets.symmetric(horizontal: 4, vertical: 2)
                    : null,
                child: Text(block.text, style: style),
              ),
            ),
      ],
    );
  }

  Widget _image(BookImage image) {
    final directory = book.directoryPath;
    final path = image.path;
    if (directory == null || path == null) {
      return _placeholder(image);
    }
    final file = File(p.join(directory, path));
    if (!file.existsSync()) {
      return _placeholder(image);
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Center(
        child: Image.file(
          file,
          height: 220,
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) => _placeholder(image),
        ),
      ),
    );
  }

  Widget _placeholder(BookImage image) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Container(
        height: 110,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: palette.paper.withValues(alpha: 0.6),
          border: Border.all(color: palette.line),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          image.alt.isEmpty ? 'Ilustración no disponible' : image.alt,
          style: TextStyle(color: palette.inkFaint, fontSize: 12),
        ),
      ),
    );
  }
}
