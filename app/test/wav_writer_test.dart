import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/wav_writer.dart';

void main() {
  test('escribe un WAV PCM mono válido', () {
    final samples = Float32List(8000);
    final bytes = const WavWriter().encode(samples, 8000);
    expect(bytes.length, 44 + 8000 * 2);
    expect(String.fromCharCodes(bytes.sublist(0, 4)), 'RIFF');
    expect(String.fromCharCodes(bytes.sublist(8, 12)), 'WAVE');
    expect(String.fromCharCodes(bytes.sublist(36, 40)), 'data');
  });

  test('concatena fragmentos con silencio', () {
    final first = Float32List.fromList([0.1, 0.2]);
    final second = Float32List.fromList([0.3]);
    final merged = const WavWriter().concat(
      [first, second],
      sampleRate: 1000,
      silenceMs: 10,
    );
    expect(merged.length, 2 + 10 + 1);
    expect(merged[0], closeTo(0.1, 0.0001));
    expect(merged[2], 0);
    expect(merged.last, closeTo(0.3, 0.0001));
  });
}
