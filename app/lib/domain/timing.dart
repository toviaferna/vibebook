import 'dart:convert';

class WordTiming {
  const WordTiming({required this.text, required this.startMs, required this.endMs});

  final String text;
  final int startMs;
  final int endMs;

  factory WordTiming.fromJson(Map<String, dynamic> json) {
    return WordTiming(
      text: json['text'] as String? ?? '',
      startMs: _int(json['start_ms']),
      endMs: _int(json['end_ms']),
    );
  }
}

class SegmentTiming {
  const SegmentTiming({
    required this.id,
    required this.startMs,
    required this.endMs,
    required this.precision,
    required this.words,
  });

  final String id;
  final int startMs;
  final int endMs;
  final String precision;
  final List<WordTiming> words;

  factory SegmentTiming.fromJson(Map<String, dynamic> json) {
    final rawWords = json['words'];
    final words = <WordTiming>[];
    if (rawWords is List) {
      for (final item in rawWords) {
        if (item is Map<String, dynamic>) {
          words.add(WordTiming.fromJson(item));
        }
      }
    }
    return SegmentTiming(
      id: json['id'] as String? ?? '',
      startMs: _int(json['start_ms']),
      endMs: _int(json['end_ms']),
      precision: json['precision'] as String? ?? 'estimated',
      words: words,
    );
  }
}

class ChapterTiming {
  const ChapterTiming({
    required this.chapterIndex,
    required this.durationMs,
    required this.precision,
    required this.segments,
  });

  final int chapterIndex;
  final int durationMs;
  final String precision;
  final List<SegmentTiming> segments;

  factory ChapterTiming.fromJson(Map<String, dynamic> json) {
    final rawSegments = json['segments'];
    final segments = <SegmentTiming>[];
    if (rawSegments is List) {
      for (final item in rawSegments) {
        if (item is Map<String, dynamic>) {
          segments.add(SegmentTiming.fromJson(item));
        }
      }
    }
    return ChapterTiming(
      chapterIndex: _int(json['chapter_index']),
      durationMs: _int(json['duration_ms']),
      precision: json['precision'] as String? ?? 'estimated',
      segments: segments,
    );
  }

  factory ChapterTiming.fromJsonString(String source) {
    final decoded = jsonDecode(source);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Timing inválido.');
    }
    return ChapterTiming.fromJson(decoded);
  }

  SegmentTiming? segmentAt(int positionMs) {
    for (final segment in segments) {
      if (positionMs >= segment.startMs && positionMs < segment.endMs) {
        return segment;
      }
    }
    return null;
  }
}

int _int(Object? value) {
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? 0;
  }
  return 0;
}
