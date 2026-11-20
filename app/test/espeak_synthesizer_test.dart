import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/chapter_synthesizer.dart';
import 'package:vibebook_app/data/tts/espeak/espeak_synthesizer.dart';
import 'package:vibebook_app/data/tts/wav_writer.dart';
import 'package:vibebook_app/domain/models.dart';

class _FakeRunner implements EspeakRunner {
  _FakeRunner({this.exitCode = 0, this.writeWav = true, this.failAll = false});

  final int exitCode;
  final bool writeWav;
  final bool failAll;
  final calls = <List<String>>[];

  @override
  Future<EspeakRunResult> run({
    required String binary,
    required List<String> args,
  }) async {
    if (failAll) {
      throw const EspeakNotConfigured('not found');
    }
    calls.add([binary, ...args]);
    if (writeWav && args.contains('-w')) {
      final index = args.indexOf('-w');
      final path = args[index + 1];
      final samples = Float32List(22050)..fillRange(0, 22050, 0.25);
      await File(path)
          .writeAsBytes(const WavWriter().encode(samples, 22050), flush: true);
    }
    return EspeakRunResult(
      exitCode: exitCode,
      stdout: '',
      stderr: exitCode == 0 ? '' : 'boom',
    );
  }
}

Chapter _chapter() {
  return const Chapter(
    index: 1,
    title: 'Uno',
    segments: [
      Segment(
        id: 'c001p0001s00',
        chapterIndex: 1,
        paragraphIndex: 1,
        text: 'Primer párrafo.',
        boundary: 'paragraph',
      ),
      Segment(
        id: 'c001p0002s00',
        chapterIndex: 1,
        paragraphIndex: 2,
        text: 'Segundo párrafo.',
        boundary: 'paragraph',
      ),
    ],
  );
}

void main() {
  test('decodifica WAV PCM 16-bit mono', () {
    final samples = Float32List.fromList([0.5, -0.5, 0.0, 1.0]);
    final wav = decodeEspeakWav(const WavWriter().encode(samples, 22050));
    expect(wav.sampleRate, 22050);
    expect(wav.samples.length, 4);
    expect(wav.samples[0], closeTo(0.5, 0.001));
    expect(wav.samples[1], closeTo(-0.5, 0.001));
    expect(wav.samples[3], closeTo(1.0, 0.001));
  });

  test('decodifica WAV estéreo promediando canales', () {
    final header = ByteData(44);
    void ascii(int offset, String value) {
      for (var index = 0; index < value.length; index++) {
        header.setUint8(offset + index, value.codeUnitAt(index));
      }
    }

    ascii(0, 'RIFF');
    header.setUint32(4, 36 + 8, Endian.little);
    ascii(8, 'WAVE');
    ascii(12, 'fmt ');
    header.setUint32(16, 16, Endian.little);
    header.setUint16(20, 1, Endian.little);
    header.setUint16(22, 2, Endian.little);
    header.setUint32(24, 22050, Endian.little);
    header.setUint32(28, 22050 * 4, Endian.little);
    header.setUint16(32, 4, Endian.little);
    header.setUint16(34, 16, Endian.little);
    ascii(36, 'data');
    header.setUint32(40, 8, Endian.little);
    final pcm = ByteData(8);
    pcm.setInt16(0, 16384, Endian.little);
    pcm.setInt16(2, 0, Endian.little);
    pcm.setInt16(4, -16384, Endian.little);
    pcm.setInt16(6, 0, Endian.little);
    final bytes = Uint8List.fromList([
      ...header.buffer.asUint8List(),
      ...pcm.buffer.asUint8List(),
    ]);
    final wav = decodeEspeakWav(bytes);
    expect(wav.samples.length, 2);
    expect(wav.samples[0], closeTo(0.25, 0.001));
    expect(wav.samples[1], closeTo(-0.25, 0.001));
  });

  test('convierte la velocidad a palabras por minuto', () {
    expect(EspeakSynthesizer.wordsPerMinute(1.0), 175);
    expect(EspeakSynthesizer.wordsPerMinute(1.1), 193);
    expect(EspeakSynthesizer.wordsPerMinute(0.5), 88);
    expect(EspeakSynthesizer.wordsPerMinute(0.1), 80);
    expect(EspeakSynthesizer.wordsPerMinute(5), 450);
    expect(
      () => EspeakSynthesizer.wordsPerMinute(0),
      throwsA(isA<EspeakException>()),
    );
  });

  test('sintetiza segmentos, agrega pausas y calcula spans', () async {
    final runner = _FakeRunner();
    final synthesizer = EspeakSynthesizer(binary: 'espeak-ng', runner: runner);
    final result = await synthesizer.synthesize(
      _chapter(),
      speed: 1.1,
      isCancelled: () => false,
    );
    expect(result.sampleRate, 22050);
    expect(result.spans, hasLength(2));
    expect(result.spans.first['id'], 'c001p0001s00');
    expect(result.spans.first['start_ms'], 0);
    expect(result.spans.first['end_ms'], 1000);
    expect(result.spans[1]['start_ms'], 1190);
    expect(result.spans[1]['end_ms'], 2190);
    expect(result.samples.length, 22050 * 2 + 4190);
    expect(result.wordTimings, isEmpty);
    expect(runner.calls, hasLength(2));
    expect(runner.calls.first, containsAll(['-v', 'es-419', '-s', '193']));
    expect(runner.calls.first, contains('-f'));
    expect(runner.calls.first, contains('-w'));
  });

  test('cancela entre segmentos', () async {
    final synthesizer = EspeakSynthesizer(
      binary: 'espeak-ng',
      runner: _FakeRunner(),
    );
    var calls = 0;
    await expectLater(
      synthesizer.synthesize(
        _chapter(),
        speed: 1,
        isCancelled: () => ++calls > 1,
      ),
      throwsA(isA<SynthesisCancelled>()),
    );
  });

  test('un binario que falla produce un error accionable', () async {
    final synthesizer = EspeakSynthesizer(
      binary: 'espeak-ng',
      runner: _FakeRunner(exitCode: 2, writeWav: false),
    );
    await expectLater(
      synthesizer.synthesize(_chapter(), speed: 1, isCancelled: () => false),
      throwsA(
        isA<EspeakException>().having(
          (error) => error.message,
          'message',
          contains('código 2'),
        ),
      ),
    );
  });

  test('el resolver acepta la variable de entorno y el PATH', () async {
    final temp = Directory.systemTemp.createTempSync('vibebook-espeak-bin-');
    addTearDown(() => temp.deleteSync(recursive: true));
    final binary = File('${temp.path}${Platform.pathSeparator}espeak-ng.exe')
      ..writeAsStringSync('fake');

    final envResolver = EspeakBinaryResolver(
      runner: _FakeRunner(failAll: true),
      environment: {'VIBEBOOK_ESPEAK_BIN': binary.path},
      fileExists: (path) => path == binary.path,
    );
    expect(await envResolver.resolve(), binary.path);

    final pathResolver = EspeakBinaryResolver(
      runner: _FakeRunner(),
      environment: const {},
    );
    expect(await pathResolver.resolve(), 'espeak-ng');

    final missing = EspeakBinaryResolver(
      runner: _FakeRunner(failAll: true),
      environment: const {},
    );
    expect(await missing.resolve(), isNull);
  });
}
