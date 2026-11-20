import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/domain/timing.dart';

void main() {
  test('parsea timings y encuentra el segmento activo', () {
    final timing = ChapterTiming.fromJsonString('''
    {
      "chapter_index": 1,
      "duration_ms": 2400,
      "precision": "exact",
      "segments": [
        {
          "id": "c001p0001s00",
          "start_ms": 0,
          "end_ms": 1200,
          "precision": "exact",
          "words": [
            {"text": "La", "start_ms": 0, "end_ms": 200},
            {"text": "casa", "start_ms": 200, "end_ms": 600}
          ]
        },
        {
          "id": "c001p0002s00",
          "start_ms": 1200,
          "end_ms": 2400,
          "precision": "estimated",
          "words": []
        }
      ]
    }
    ''');
    expect(timing.chapterIndex, 1);
    expect(timing.precision, 'exact');
    expect(timing.segments, hasLength(2));
    expect(timing.segmentAt(300)?.id, 'c001p0001s00');
    expect(timing.segmentAt(1500)?.id, 'c001p0002s00');
    expect(timing.segmentAt(3000), isNull);
    expect(timing.segments.first.words.first.text, 'La');
  });
}
