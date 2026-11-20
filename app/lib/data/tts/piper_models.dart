import 'dart:convert';
import 'dart:io';

import 'package:collection/collection.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// A Piper voice installed on disk.
class PiperModel {
  const PiperModel({
    required this.id,
    required this.name,
    required this.language,
    required this.directory,
    required this.modelFile,
    required this.tokensFile,
    required this.espeakVoice,
    this.sampleRate = 22050,
    this.numSpeakers = 1,
    this.noiseScale = 0.667,
    this.noiseScaleW = 0.8,
    this.lengthScale = 1.0,
  });

  final String id;
  final String name;
  final String language;
  final String directory;
  final String modelFile;
  final String tokensFile;
  final String espeakVoice;
  final int sampleRate;
  final int numSpeakers;
  final double noiseScale;
  final double noiseScaleW;
  final double lengthScale;

  String get modelPath => p.join(directory, modelFile);
  String get tokensPath => p.join(directory, tokensFile);
  String get espeakDataPath => p.join(directory, 'espeak-ng-data');

  bool get isValid {
    return File(modelPath).existsSync() && File(tokensPath).existsSync();
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'language': language,
    'directory': directory,
    'model': modelFile,
    'tokens': tokensFile,
    'espeak_voice': espeakVoice,
    'sample_rate': sampleRate,
  };
}

/// Discovers Piper voices stored as one directory per voice.
class PiperModelStore {
  PiperModelStore({String? rootPath}) {
    _rootPath = rootPath;
  }

  String? _rootPath;

  Future<String> resolveRoot() async {
    if (_rootPath != null && _rootPath!.trim().isNotEmpty) {
      return _rootPath!;
    }
    final support = await getApplicationSupportDirectory();
    return p.join(support.path, 'models', 'piper');
  }

  Future<void> setRoot(String? path) async {
    _rootPath = path;
  }

  Future<List<PiperModel>> scan() async {
    final root = Directory(await resolveRoot());
    if (!await root.exists()) {
      await root.create(recursive: true);
      return const [];
    }
    final direct = await _readModel(root);
    if (direct != null) {
      return [direct];
    }
    final models = <PiperModel>[];
    await for (final entity in root.list(followLinks: false)) {
      if (entity is! Directory) {
        continue;
      }
      final model = await _readModel(entity);
      if (model != null) {
        models.add(model);
      }
    }
    models.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    return models;
  }

  Future<PiperModel?> _readModel(Directory directory) async {
    final files = await directory
        .list(followLinks: false)
        .where((entity) => entity is File)
        .cast<File>()
        .toList();
    final onnx = files
        .where((file) => file.path.toLowerCase().endsWith('.onnx'))
        .firstOrNull;
    final tokens = files
        .where((file) => p.basename(file.path) == 'tokens.txt')
        .firstOrNull;
    if (onnx == null || tokens == null) {
      return null;
    }
    final jsonFile = files
        .where((file) => file.path.toLowerCase().endsWith('.onnx.json'))
        .firstOrNull;
    var sampleRate = 22050;
    var voice = 'en-us';
    var noiseScale = 0.667;
    var noiseScaleW = 0.8;
    var lengthScale = 1.0;
    var numSpeakers = 1;
    if (jsonFile != null) {
      try {
        final decoded = jsonDecode(await jsonFile.readAsString());
        if (decoded is Map<String, dynamic>) {
          final audio = decoded['audio'];
          if (audio is Map<String, dynamic> && audio['sample_rate'] is num) {
            sampleRate = (audio['sample_rate'] as num).toInt();
          }
          final espeak = decoded['espeak'];
          if (espeak is Map<String, dynamic> && espeak['voice'] is String) {
            voice = espeak['voice'] as String;
          }
          final inference = decoded['inference'];
          if (inference is Map<String, dynamic>) {
            if (inference['noise_scale'] is num) {
              noiseScale = (inference['noise_scale'] as num).toDouble();
            }
            if (inference['noise_w'] is num) {
              noiseScaleW = (inference['noise_w'] as num).toDouble();
            }
            if (inference['length_scale'] is num) {
              lengthScale = (inference['length_scale'] as num).toDouble();
            }
          }
          if (decoded['num_speakers'] is num) {
            numSpeakers = (decoded['num_speakers'] as num).toInt();
          }
        }
      } catch (_) {
        // A malformed sidecar keeps the defaults.
      }
    }
    final stem = p.basenameWithoutExtension(onnx.path);
    final id = p.basename(directory.path);
    final language = voice.split(RegExp(r'[-_]')).first.toLowerCase();
    return PiperModel(
      id: id,
      name: _displayName(stem),
      language: language,
      directory: directory.path,
      modelFile: p.basename(onnx.path),
      tokensFile: p.basename(tokens.path),
      espeakVoice: voice,
      sampleRate: sampleRate,
      numSpeakers: numSpeakers,
      noiseScale: noiseScale,
      noiseScaleW: noiseScaleW,
      lengthScale: lengthScale,
    );
  }

  String _displayName(String stem) {
    var cleaned = stem.replaceFirst(
      RegExp(r'^vits-piper-', caseSensitive: false),
      '',
    );
    cleaned = cleaned.replaceAll(RegExp(r'[-_]+'), ' ').trim();
    if (cleaned.isEmpty) {
      return 'Piper';
    }
    return cleaned
        .split(' ')
        .map(
          (word) => word.isEmpty
              ? word
              : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
  }
}
