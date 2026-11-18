import 'dart:typed_data';

import 'package:piper_phonemize/piper_phonemize.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa;

import '../../core/platform_paths.dart';
import 'piper_models.dart';

class GeneratedSpeech {
  const GeneratedSpeech({required this.samples, required this.sampleRate});

  final Float32List samples;
  final int sampleRate;

  bool get isEmpty => samples.isEmpty;

  Duration get duration =>
      Duration(milliseconds: (samples.length * 1000 / sampleRate).round());
}

class PiperTtsException implements Exception {
  const PiperTtsException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Local Piper synthesis through sherpa-onnx with piper-phonemize.
class PiperTtsService {
  PiperTtsService();

  bool _initialized = false;
  PiperModel? _loadedModel;
  sherpa.OfflineTts? _tts;
  String? _espeakDataDir;

  PiperModel? get loadedModel => _loadedModel;

  bool get isReady => _initialized && _tts != null;

  Future<void> initialize() async {
    if (_initialized) {
      return;
    }
    try {
      sherpa.initBindings();
      initBindings();
      _espeakDataDir = await extractEspeakNgData();
      final result = PiperPhonemize.initialize(nativePath(_espeakDataDir!));
      if (result < 0) {
        throw const PiperTtsException('espeak-ng no pudo inicializarse.');
      }
      _initialized = true;
    } catch (error) {
      throw PiperTtsException('No se pudo inicializar Piper: $error');
    }
  }

  Future<void> loadModel(PiperModel model) async {
    if (!model.isValid) {
      throw PiperTtsException('El modelo Piper no está completo en ${model.directory}.');
    }
    await initialize();
    if (_loadedModel?.id == model.id && _tts != null) {
      return;
    }
    _tts?.free();
    _tts = null;
    try {
      final config = sherpa.OfflineTtsConfig(
        model: sherpa.OfflineTtsModelConfig(
          vits: sherpa.OfflineTtsVitsModelConfig(
            model: nativePath(model.modelPath),
            tokens: nativePath(model.tokensPath),
            noiseScale: model.noiseScale,
            noiseScaleW: model.noiseScaleW,
            lengthScale: model.lengthScale,
          ),
          numThreads: 2,
          debug: false,
          provider: 'cpu',
        ),
        maxNumSentences: 1,
      );
      _tts = sherpa.OfflineTts(config);
      _loadedModel = model;
    } catch (error) {
      throw PiperTtsException('No se pudo cargar el modelo Piper: $error');
    }
  }

  Future<GeneratedSpeech> synthesize(
    String text, {
    double speed = 1.0,
    int speakerId = 0,
  }) async {
    final tts = _tts;
    final model = _loadedModel;
    if (tts == null || model == null) {
      throw const PiperTtsException('No hay un modelo Piper cargado.');
    }
    final normalized = text.trim();
    if (normalized.isEmpty) {
      return GeneratedSpeech(samples: Float32List(0), sampleRate: 22050);
    }
    final List<List<int>> phonemes;
    try {
      phonemes = PiperPhonemize.phonemize(normalized, voice: model.espeakVoice)
          .where((sentence) => sentence.isNotEmpty)
          .toList(growable: false);
    } catch (error) {
      throw PiperTtsException('No se pudo fonemizar el texto: $error');
    }
    if (phonemes.isEmpty) {
      return GeneratedSpeech(samples: Float32List(0), sampleRate: tts.sampleRate);
    }
    final results = <Float32List>[];
    var sampleRate = tts.sampleRate;
    for (final sentence in phonemes) {
      final audio = tts.generateWithConfig(
        text: '',
        config: sherpa.OfflineTtsGenerationConfig(
          phonemeCodepoints: [sentence],
          speed: speed,
          sid: speakerId,
        ),
      );
      if (audio.samples.isEmpty) {
        continue;
      }
      sampleRate = audio.sampleRate;
      results.add(audio.samples);
    }
    if (results.isEmpty) {
      return GeneratedSpeech(samples: Float32List(0), sampleRate: sampleRate);
    }
    final total = results.fold<int>(0, (sum, part) => sum + part.length);
    final merged = Float32List(total);
    var offset = 0;
    for (final part in results) {
      merged.setAll(offset, part);
      offset += part.length;
    }
    return GeneratedSpeech(samples: merged, sampleRate: sampleRate);
  }

  void dispose() {
    _tts?.free();
    _tts = null;
    _loadedModel = null;
  }
}
