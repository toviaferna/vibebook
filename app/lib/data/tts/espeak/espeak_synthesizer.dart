import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../../../domain/models.dart';
import '../chapter_synthesizer.dart';

const defaultEspeakVoice = 'es-419';
const defaultEspeakWpm = 175;

class EspeakNotConfigured implements Exception {
  const EspeakNotConfigured(this.message);

  final String message;

  @override
  String toString() => message;
}

class EspeakException implements Exception {
  const EspeakException(this.message);

  final String message;

  @override
  String toString() => message;
}

class EspeakRunResult {
  const EspeakRunResult({
    required this.exitCode,
    required this.stdout,
    required this.stderr,
  });

  final int exitCode;
  final String stdout;
  final String stderr;
}

/// Runs an executable. Tests inject a fake so no real binary is required.
abstract class EspeakRunner {
  Future<EspeakRunResult> run({
    required String binary,
    required List<String> args,
  });
}

class ProcessEspeakRunner implements EspeakRunner {
  const ProcessEspeakRunner({this.timeout = const Duration(seconds: 60)});

  final Duration timeout;

  @override
  Future<EspeakRunResult> run({
    required String binary,
    required List<String> args,
  }) async {
    try {
      final result = await Process.run(
        binary,
        args,
        stdoutEncoding: utf8,
        stderrEncoding: utf8,
        runInShell: false,
      ).timeout(timeout);
      return EspeakRunResult(
        exitCode: result.exitCode,
        stdout: '${result.stdout ?? ''}',
        stderr: '${result.stderr ?? ''}',
      );
    } on ProcessException catch (error) {
      throw EspeakNotConfigured(
        'No se pudo ejecutar eSpeak NG: ${error.message}',
      );
    } on TimeoutException {
      throw const EspeakException('eSpeak NG tardó demasiado en responder.');
    }
  }
}

/// Finds `VIBEBOOK_ESPEAK_BIN`, then `espeak-ng` and `espeak` in PATH.
class EspeakBinaryResolver {
  EspeakBinaryResolver({
    EspeakRunner? runner,
    Map<String, String>? environment,
    bool Function(String path)? fileExists,
  }) : _runner = runner ?? const ProcessEspeakRunner(),
       _environment = environment ?? Platform.environment,
       _fileExists = fileExists ?? ((path) => File(path).existsSync());

  final EspeakRunner _runner;
  final Map<String, String> _environment;
  final bool Function(String path) _fileExists;

  Future<String?> resolve() async {
    final configured = _environment['VIBEBOOK_ESPEAK_BIN']?.trim();
    if (configured != null &&
        configured.isNotEmpty &&
        _fileExists(configured)) {
      return configured;
    }
    for (final name in const ['espeak-ng', 'espeak']) {
      try {
        final locator = Platform.isWindows ? 'where' : 'which';
        final located = await _runner.run(binary: locator, args: [name]);
        if (located.exitCode == 0) {
          final path = located.stdout
              .split(RegExp(r'\r?\n'))
              .map((line) => line.trim())
              .firstWhere((line) => line.isNotEmpty, orElse: () => '');
          return path.isEmpty ? name : path;
        }
        final direct = await _runner.run(binary: name, args: ['--version']);
        if (direct.exitCode == 0) {
          return name;
        }
      } on EspeakNotConfigured {
        continue;
      } on EspeakException {
        continue;
      }
    }
    return null;
  }
}

/// One decoded mono PCM buffer.
class EspeakWav {
  const EspeakWav({required this.samples, required this.sampleRate});

  final Float32List samples;
  final int sampleRate;
}

/// Decodes a PCM 16-bit RIFF/WAVE file. eSpeak always writes this format.
EspeakWav decodeEspeakWav(Uint8List bytes) {
  if (bytes.length < 44) {
    throw const EspeakException('eSpeak NG devolvió un WAV vacío.');
  }
  String tag(int offset) =>
      String.fromCharCodes(bytes.sublist(offset, offset + 4));
  int uint16(int offset) => ByteData.sublistView(
    bytes,
    offset,
    offset + 2,
  ).getUint16(0, Endian.little);
  int uint32(int offset) => ByteData.sublistView(
    bytes,
    offset,
    offset + 4,
  ).getUint32(0, Endian.little);

  if (tag(0) != 'RIFF' || tag(8) != 'WAVE') {
    throw const EspeakException('eSpeak NG devolvió un archivo que no es WAV.');
  }
  var offset = 12;
  int? sampleRate;
  int? channels;
  int? bitsPerSample;
  Uint8List? data;
  while (offset + 8 <= bytes.length) {
    final id = tag(offset);
    final size = uint32(offset + 4);
    final content = offset + 8;
    if (content + size > bytes.length) {
      break;
    }
    if (id == 'fmt ' && size >= 16) {
      final format = uint16(content);
      if (format != 1) {
        throw const EspeakException(
          'eSpeak NG devolvió un WAV comprimido; se esperaba PCM.',
        );
      }
      channels = uint16(content + 2);
      sampleRate = uint32(content + 4);
      bitsPerSample = uint16(content + 14);
    } else if (id == 'data') {
      data = Uint8List.sublistView(bytes, content, content + size);
    }
    offset = content + size + (size.isOdd ? 1 : 0);
  }
  if (sampleRate == null ||
      channels == null ||
      bitsPerSample == null ||
      data == null) {
    throw const EspeakException('eSpeak NG devolvió un WAV incompleto.');
  }
  if (bitsPerSample != 16) {
    throw EspeakException(
      'eSpeak NG devolvió $bitsPerSample bits por muestra; se esperaban 16.',
    );
  }
  final frameBytes = channels * 2;
  final frames = data.length ~/ frameBytes;
  final samples = Float32List(frames);
  final view = ByteData.sublistView(data);
  for (var frame = 0; frame < frames; frame++) {
    var sum = 0;
    for (var channel = 0; channel < channels; channel++) {
      sum += view.getInt16(frame * frameBytes + channel * 2, Endian.little);
    }
    samples[frame] = (sum / channels) / 32768;
  }
  return EspeakWav(samples: samples, sampleRate: sampleRate);
}

/// [ChapterSynthesizer] over the local eSpeak NG binary.
///
/// eSpeak does not report word timings, so the reader estimates them from the
/// segment spans. The binary is never bundled: the user installs it or points
/// `VIBEBOOK_ESPEAK_BIN` at it, exactly like the Tauri app.
class EspeakSynthesizer implements ChapterSynthesizer {
  EspeakSynthesizer({
    required this.binary,
    this.voice = defaultEspeakVoice,
    EspeakRunner? runner,
    this.paragraphPauseMs = 190,
    this.sentencePauseMs = 90,
  }) : _runner = runner ?? const ProcessEspeakRunner();

  final String binary;
  final String voice;
  final EspeakRunner _runner;
  final int paragraphPauseMs;
  final int sentencePauseMs;

  @override
  String get engineId => 'espeak';

  @override
  String get voiceId => voice;

  /// Maps the chapter speed multiplier to eSpeak words per minute.
  static int wordsPerMinute(double speed) {
    if (speed <= 0) {
      throw const EspeakException('La velocidad debe ser mayor que cero.');
    }
    return (defaultEspeakWpm * speed).round().clamp(80, 450);
  }

  @override
  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  }) async {
    final wpm = wordsPerMinute(speed);
    final directory = await Directory.systemTemp.createTemp('vibebook-espeak-');
    final chunks = <Float32List>[];
    final spans = <Map<String, dynamic>>[];
    int? sampleRate;
    var cursor = 0;
    try {
      for (var index = 0; index < chapter.segments.length; index++) {
        if (isCancelled()) {
          throw const SynthesisCancelled();
        }
        final segment = chapter.segments[index];
        if (segment.text.trim().isEmpty) {
          continue;
        }
        final textFile = File(
          '${directory.path}${Platform.pathSeparator}segment_$index.txt',
        );
        final wavFile = File(
          '${directory.path}${Platform.pathSeparator}segment_$index.wav',
        );
        await textFile.writeAsString('${segment.text}\n', encoding: utf8);
        final result = await _runner.run(
          binary: binary,
          args: [
            '-v',
            voice,
            '-s',
            '$wpm',
            '-b',
            '1',
            '-w',
            wavFile.path,
            '-f',
            textFile.path,
          ],
        );
        if (isCancelled()) {
          throw const SynthesisCancelled();
        }
        if (result.exitCode != 0) {
          final detail =
              (result.stderr.isNotEmpty ? result.stderr : result.stdout).trim();
          throw EspeakException(
            'eSpeak NG falló (código ${result.exitCode})'
            '${detail.isEmpty ? '' : ': ${detail.substring(detail.length > 300 ? detail.length - 300 : 0)}'}',
          );
        }
        if (!await wavFile.exists()) {
          throw const EspeakException('eSpeak NG no produjo audio.');
        }
        final decoded = decodeEspeakWav(await wavFile.readAsBytes());
        if (decoded.samples.isEmpty) {
          throw const EspeakException('eSpeak NG devolvió audio vacío.');
        }
        final rate = sampleRate ?? decoded.sampleRate;
        if (decoded.sampleRate != rate) {
          throw const EspeakException(
            'eSpeak NG cambió la frecuencia de muestreo entre segmentos.',
          );
        }
        sampleRate = rate;
        final startMs = (cursor * 1000 / rate).round();
        chunks.add(decoded.samples);
        cursor += decoded.samples.length;
        final endMs = (cursor * 1000 / rate).round();
        spans.add({'id': segment.id, 'start_ms': startMs, 'end_ms': endMs});
        if (index < chapter.segments.length - 1) {
          final pauseMs = segment.boundary == 'paragraph'
              ? paragraphPauseMs
              : sentencePauseMs;
          final pauseFrames = (rate * pauseMs / 1000).round();
          if (pauseFrames > 0) {
            chunks.add(Float32List(pauseFrames));
            cursor += pauseFrames;
          }
        }
      }
      final total = chunks.fold<int>(0, (sum, chunk) => sum + chunk.length);
      final samples = Float32List(total);
      var offset = 0;
      for (final chunk in chunks) {
        samples.setAll(offset, chunk);
        offset += chunk.length;
      }
      return ChapterSynthesis(
        samples: samples,
        sampleRate: sampleRate ?? 22050,
        spans: spans,
        wordTimings: const [],
      );
    } finally {
      try {
        await directory.delete(recursive: true);
      } on FileSystemException {
        // The OS can keep a handle briefly on Windows; the temp file is safe.
      }
    }
  }
}
