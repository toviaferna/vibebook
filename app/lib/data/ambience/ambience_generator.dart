import 'dart:io';
import 'dart:isolate';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../domain/ambience.dart';
import '../tts/wav_writer.dart';

/// Generates deterministic, seamless ambience beds locally.
///
/// The beds are synthesized from noise and simple acoustic events; no external
/// assets or licenses are involved.
class AmbienceGenerator {
  const AmbienceGenerator();

  static const sampleRate = 22050;

  Future<File> ensurePreset(AmbiencePreset preset) async {
    final support = await getApplicationSupportDirectory();
    final directory = Directory(p.join(support.path, 'ambience'));
    await directory.create(recursive: true);
    final file = File(p.join(directory.path, '${preset.id}.wav'));
    if (await file.exists() && await file.length() > 44) {
      return file;
    }
    final temporary = File('${file.path}.tmp');
    await Isolate.run(() => _generateToFile(preset.id, temporary.path));
    if (await file.exists()) {
      await file.delete();
    }
    await temporary.rename(file.path);
    return file;
  }
}

void _generateToFile(String presetId, String path) {
  final preset = AmbiencePresetDetails.byId(presetId);
  final samples = _render(preset);
  final bytes = const WavWriter().encode(samples, AmbienceGenerator.sampleRate);
  File(path).writeAsBytesSync(bytes, flush: true);
}

Float32List renderAmbienceSamples(AmbiencePreset preset) => _render(preset);

Float32List _render(AmbiencePreset preset) {
  const sampleRate = AmbienceGenerator.sampleRate;
  const seconds = 32.0;
  const loopFadeSeconds = 2.0;
  final total = (sampleRate * seconds).round();
  final values = Float32List(total);
  final random = math.Random(1000 + preset.index * 7919);
  const twoPi = math.pi * 2;
  var brown = 0.0;
  var low = 0.0;
  var drop = 0.0;
  var dropFrequency = 0.0;
  var crackle = 0.0;
  var chirp = 0.0;

  for (var index = 0; index < total; index++) {
    final time = index / sampleRate;
    final white = random.nextDouble() * 2 - 1;
    switch (preset) {
      case AmbiencePreset.rain:
        low += (white - low) * 0.35;
        var sample = low * 0.42;
        if (random.nextDouble() < 0.0012) {
          drop = 1;
          dropFrequency = 700 + random.nextDouble() * 2200;
        }
        if (drop > 0.001) {
          sample += math.sin(twoPi * dropFrequency * time) * drop * 0.22;
          drop *= 0.9997;
        } else {
          drop = 0;
        }
        values[index] = sample;
      case AmbiencePreset.wind:
        brown = ((brown + white * 0.02) * 0.999).clamp(-1.0, 1.0).toDouble();
        low += (brown - low) * 0.025;
        final gust = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(twoPi * time / 17));
        values[index] = (low * 1.7 + white * 0.02) * gust;
      case AmbiencePreset.sea:
        brown = ((brown + white * 0.015) * 0.9995).clamp(-1.0, 1.0).toDouble();
        low += (brown - low) * 0.05;
        final wave = 0.5 + 0.5 * math.sin(twoPi * time / 11 + 0.7);
        values[index] = low * 1.5 * (0.35 + 0.65 * wave) + white * 0.025 * wave;
      case AmbiencePreset.fire:
        brown = ((brown + white * 0.03) * 0.999).clamp(-1.0, 1.0).toDouble();
        low += (brown - low) * 0.12;
        if (random.nextDouble() < 0.00055) {
          crackle = 1;
        }
        var spark = 0.0;
        if (crackle > 0.001) {
          spark = white * crackle * 0.6;
          crackle *= 0.995;
        } else {
          crackle = 0;
        }
        values[index] = low * 0.55 + spark;
      case AmbiencePreset.night:
        brown = ((brown + white * 0.01) * 0.9997).clamp(-1.0, 1.0).toDouble();
        low += (brown - low) * 0.03;
        var cricket = 0.0;
        if (chirp <= 0 && random.nextDouble() < 0.00003) {
          chirp = 0.35;
        }
        if (chirp > 0) {
          final elapsed = 0.35 - chirp;
          final gate = (elapsed % 0.09) < 0.035 ? 1.0 : 0.0;
          cricket = math.sin(twoPi * 4300 * time) * gate * (chirp / 0.35) * 0.08;
          chirp -= 1 / sampleRate;
        }
        values[index] = low * 0.9 + cricket;
    }
  }

  var peak = 0.0;
  for (final value in values) {
    final absolute = value.abs();
    if (absolute > peak) {
      peak = absolute;
    }
  }
  if (peak > 0) {
    final gain = 0.72 / peak;
    for (var index = 0; index < values.length; index++) {
      values[index] *= gain;
    }
  }

  final fade = (sampleRate * loopFadeSeconds).round();
  final keep = total - fade;
  for (var index = 0; index < fade; index++) {
    final mix = index / fade;
    values[index] = values[index] * mix + values[keep + index] * (1 - mix);
  }
  return values.sublist(0, keep);
}
