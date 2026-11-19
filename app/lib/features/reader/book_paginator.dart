import 'package:material_ui/material_ui.dart';

import '../../domain/models.dart';

/// One block on a paginated page: text or an image.
class BookPageBlock {
  const BookPageBlock.text({required this.text, required this.segmentId})
    : image = null;

  const BookPageBlock.image(this.image) : text = '', segmentId = null;

  final String text;
  final String? segmentId;
  final BookImage? image;

  bool get isImage => image != null;

  BookPageBlock withText(String value) {
    return BookPageBlock.text(text: value, segmentId: segmentId);
  }
}

class BookPage {
  const BookPage({required this.chapterIndex, required this.blocks});

  final int chapterIndex;
  final List<BookPageBlock> blocks;

  Iterable<String> get segmentIds =>
      blocks.map((block) => block.segmentId).whereType<String>();
}

/// Measures text into pages that fit a given content box.
///
/// The algorithm first tries whole paragraphs, then splits by words with a
/// binary search so a long paragraph never overflows. Images take a fixed
/// height and can start a new page.
class BookPaginator {
  const BookPaginator({
    this.paragraphSpacing = 14,
    this.imageHeight = 220,
    this.imageSpacing = 16,
  });

  final double paragraphSpacing;
  final double imageHeight;
  final double imageSpacing;

  List<BookPage> paginate({
    required Chapter chapter,
    required Size size,
    required TextStyle style,
    List<BookImage> images = const [],
    TextScaler textScaler = TextScaler.noScaling,
  }) {
    if (size.width <= 0 || size.height <= 0) {
      return const [];
    }
    final blocks = <BookPageBlock>[];
    final imagesByParagraph = <int, List<BookImage>>{};
    for (final image in images) {
      imagesByParagraph
          .putIfAbsent(image.paragraphIndex, () => <BookImage>[])
          .add(image);
    }
    final usedImages = <BookImage>{};
    for (final segment in chapter.segments) {
      for (final image
          in imagesByParagraph[segment.paragraphIndex] ?? const []) {
        blocks.add(BookPageBlock.image(image));
        usedImages.add(image);
      }
      if (segment.text.trim().isNotEmpty) {
        blocks.add(
          BookPageBlock.text(text: segment.text, segmentId: segment.id),
        );
      }
    }
    for (final image in images) {
      if (!usedImages.contains(image)) {
        blocks.add(BookPageBlock.image(image));
      }
    }

    final pages = <BookPage>[];
    var current = <BookPageBlock>[];
    var used = 0.0;

    void flush() {
      if (current.isEmpty) {
        return;
      }
      pages.add(BookPage(chapterIndex: chapter.index, blocks: current));
      current = <BookPageBlock>[];
      used = 0;
    }

    double measure(String text) {
      final painter = TextPainter(
        text: TextSpan(text: text, style: style),
        textDirection: TextDirection.ltr,
        textScaler: textScaler,
      )..layout(maxWidth: size.width);
      return painter.height;
    }

    for (final block in blocks) {
      if (block.isImage) {
        if (used + imageHeight > size.height && current.isNotEmpty) {
          flush();
        }
        current.add(block);
        used += imageHeight + imageSpacing;
        if (used >= size.height) {
          flush();
        }
        continue;
      }
      var text = block.text;
      while (text.isNotEmpty) {
        final remaining = size.height - used;
        if (remaining < style.fontSize! * 1.4) {
          if (current.isEmpty) {
            current.add(block.withText(text));
            flush();
            break;
          }
          flush();
          continue;
        }
        final fullHeight = measure(text);
        if (fullHeight <= remaining) {
          current.add(block.withText(text));
          used += fullHeight + paragraphSpacing;
          break;
        }
        final words = _splitKeepingWhitespace(text);
        var low = 0;
        var high = words.length;
        var best = 0;
        while (low <= high) {
          final middle = (low + high) ~/ 2;
          final candidate = words.take(middle).join().trimRight();
          if (candidate.isEmpty || measure(candidate) <= remaining) {
            best = middle;
            low = middle + 1;
          } else {
            high = middle - 1;
          }
        }
        if (best == 0) {
          if (current.isEmpty) {
            current.add(block.withText(text));
            flush();
            break;
          }
          flush();
          continue;
        }
        final head = words.take(best).join();
        final tail = words.skip(best).join();
        if (head.isNotEmpty) {
          current.add(block.withText(head));
        }
        flush();
        text = tail;
      }
    }
    flush();
    return pages;
  }
}

List<String> _splitKeepingWhitespace(String text) {
  final result = <String>[];
  for (final match in RegExp(r'\S+|\s+').allMatches(text)) {
    final value = match.group(0);
    if (value != null && value.isNotEmpty) {
      result.add(value);
    }
  }
  return result;
}
