import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../data/tts/edge/edge_client.dart';
import '../data/tts/edge/edge_synthesizer.dart'
    show EdgeSynthesizer, decodeEdgeMp3;
import '../data/tts/wav_writer.dart';

/// Headless check of the Edge pipeline: one sentence over the network, MP3 to
/// PCM via FFmpegKit, WAV on disk. Needs internet, so it stays out of CI.
///
/// Usage:
///   `vibebook_app.exe --edge-tts-smoke <voice> <out.wav> <out.json>`
Future<void> runEdgeTtsSmoke(List<String> args) async {
  final flag = args.indexOf('--edge-tts-smoke');
  final voice = flag + 1 < args.length ? args[flag + 1] : '';
  final outputWav = flag + 2 < args.length ? args[flag + 2] : '';
  final outputJson = flag + 3 < args.length ? args[flag + 3] : '';
  final result = <String, dynamic>{
    'ok': false,
    'voice': voice,
    'wav': outputWav,
  };
  try {
    if (voice.isEmpty || outputWav.isEmpty || outputJson.isEmpty) {
      throw ArgumentError('Uso: --edge-tts-smoke <voice> <out.wav> <out.json>');
    }
    const text =
        'La casa de los Ferrer se levantaba sobre una loma que olía a sal. '
        'Desde la ventana se veía el puerto.';
    final client = EdgeTtsClient();
    final bytes = BytesBuilder(copy: false);
    var boundaries = 0;
    await for (final event in client.synthesize(
      text: text,
      voice: voice,
      rate: '+0%',
    )) {
      if (event is EdgeAudioEvent) {
        bytes.add(event.data);
      } else if (event is EdgeWordBoundaryEvent) {
        boundaries += 1;
      }
    }
    final mp3 = bytes.takeBytes();
    if (mp3.isEmpty) {
      throw const EdgeNoAudioException();
    }
    final samples = await decodeEdgeMp3(mp3);
    if (samples.isEmpty) {
      throw StateError('La decodificación no produjo muestras.');
    }
    final wav = const WavWriter().encode(samples, EdgeSynthesizer.sampleRate);
    final file = File(outputWav);
    await file.parent.create(recursive: true);
    await file.writeAsBytes(wav, flush: true);
    result
      ..['ok'] = true
      ..['mp3_bytes'] = mp3.length
      ..['sample_rate'] = EdgeSynthesizer.sampleRate
      ..['samples'] = samples.length
      ..['duration_ms'] = (samples.length * 1000 / EdgeSynthesizer.sampleRate)
          .round()
      ..['word_boundaries'] = boundaries
      ..['wav_bytes'] = wav.length;
  } catch (error, stackTrace) {
    result
      ..['error'] = '$error'
      ..['stack'] = '$stackTrace';
  } finally {
    if (outputJson.isNotEmpty) {
      final file = File(outputJson);
      await file.parent.create(recursive: true);
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(result),
        flush: true,
      );
    }
  }
  exit(result['ok'] == true ? 0 : 1);
}
