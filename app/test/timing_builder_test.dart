import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/timing_builder.dart';

void main() {
  test('estima palabras dentro de un segmento', () {
    const builder = TimingBuilder();
    final timing = builder.build(
      chapterIndex: 3,
      segmentTexts: const {'c003p0001s00': 'La casa olía a sal.'},
      spans: const [
        {'id': 'c003p0001s00', 'start_ms': 200, 'end_ms': 1400},
      ],
      durationMs: 2000,
    );
    expect(timing.chapterIndex, 3);
    expect(timing.durationMs, 2000);
    expect(timing.precision, 'estimated');
    expect(timing.segments, hasLength(1));
    final segment = timing.segments.first;
    expect(segment.startMs, 200);
    expect(segment.endMs, 1400);
    expect(segment.words, hasLength(5));
    expect(segment.words.first.text, 'La');
    expect(segment.words.first.startMs, 200);
    expect(segment.words.last.text, 'sal.');
    expect(segment.words.last.endMs, 1400);
    for (var index = 1; index < segment.words.length; index++) {
      expect(segment.words[index].startMs, segment.words[index - 1].endMs);
      expect(segment.words[index].endMs, greaterThanOrEqualTo(segment.words[index].startMs));
    }
  });

  test('omite segmentos sin texto o sin duración', () {
    const builder = TimingBuilder();
    final timing = builder.build(
      chapterIndex: 1,
      segmentTexts: const {'a': '', 'b': 'Hola.'},
      spans: const [
        {'id': 'a', 'start_ms': 0, 'end_ms': 0},
        {'id': 'b', 'start_ms': 100, 'end_ms': 100},
      ],
      durationMs: 100,
    );
    expect(timing.segments.first.words, isEmpty);
    expect(timing.segments.last.words, isEmpty);
  });
}
