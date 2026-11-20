import '../../domain/timing.dart';

/// Builds the karaoke timing file from synthesized segment spans.
class TimingBuilder {
  const TimingBuilder();

  ChapterTiming build({
    required int chapterIndex,
    required Map<String, String> segmentTexts,
    required List<Map<String, dynamic>> spans,
    required int durationMs,
    List<Map<String, dynamic>>? wordTimings,
    String precision = 'estimated',
  }) {
    final realWords = <String, List<WordTiming>>{};
    if (wordTimings != null) {
      for (final entry in wordTimings) {
        final id = entry['id'] as String? ?? '';
        final words = entry['words'];
        if (words is List && words.isNotEmpty) {
          realWords[id] = [
            for (final word in words)
              if (word is Map<String, dynamic>)
                WordTiming(
                  text: word['text'] as String? ?? '',
                  startMs: (word['start_ms'] as num?)?.toInt() ?? 0,
                  endMs: (word['end_ms'] as num?)?.toInt() ?? 0,
                ),
          ];
        }
      }
    }
    final segments = <SegmentTiming>[];
    for (final span in spans) {
      final id = span['id'] as String? ?? '';
      final startMs = (span['start_ms'] as num?)?.toInt() ?? 0;
      final endMs = (span['end_ms'] as num?)?.toInt() ?? startMs;
      final text = segmentTexts[id] ?? '';
      segments.add(
        SegmentTiming(
          id: id,
          startMs: startMs,
          endMs: endMs,
          precision: precision,
          words: realWords[id] ?? _words(text, startMs, endMs),
        ),
      );
    }
    return ChapterTiming(
      chapterIndex: chapterIndex,
      durationMs: durationMs,
      precision: precision,
      segments: segments,
    );
  }

  List<WordTiming> _words(String text, int startMs, int endMs) {
    final matches = RegExp(r'\S+').allMatches(text).toList(growable: false);
    if (matches.isEmpty || endMs <= startMs) {
      return const [];
    }
    final weights = <double>[];
    for (final match in matches) {
      final word = match.group(0)!;
      var weight = word.length.clamp(2, 18).toDouble();
      if (RegExp(r'[,;:]$').hasMatch(word)) {
        weight += 2.5;
      }
      if (RegExp(r'''[.!?…]["'”’»)]*$''').hasMatch(word)) {
        weight += 4.5;
      }
      weights.add(weight);
    }
    final totalWeight = weights.fold<double>(0, (sum, weight) => sum + weight);
    final totalMs = endMs - startMs;
    final words = <WordTiming>[];
    var cursor = startMs;
    var consumed = 0.0;
    for (var index = 0; index < matches.length; index++) {
      consumed += weights[index];
      final isLast = index == matches.length - 1;
      final end = isLast
          ? endMs
          : startMs + (totalMs * consumed / totalWeight).round();
      final safeEnd = end.clamp(cursor, endMs).toInt();
      words.add(
        WordTiming(
          text: matches[index].group(0)!,
          startMs: cursor,
          endMs: safeEnd,
        ),
      );
      cursor = safeEnd;
    }
    return words;
  }
}
