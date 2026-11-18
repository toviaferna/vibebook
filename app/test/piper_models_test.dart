import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/tts/piper_models.dart';

void main() {
  test('detecta una voz dentro de la carpeta de modelos', () async {
    final root = await Directory.systemTemp.createTemp('vibebook-piper-test-');
    addTearDown(() async {
      if (await root.exists()) {
        await root.delete(recursive: true);
      }
    });
    final voice = Directory(p.join(root.path, 'vits-piper-es-glados-medium'));
    await voice.create(recursive: true);
    await File(p.join(voice.path, 'es-glados-medium.onnx')).writeAsBytes([1, 2, 3]);
    await File(p.join(voice.path, 'tokens.txt')).writeAsString('a 1\nb 2\n');
    await File(p.join(voice.path, 'es-glados-medium.onnx.json')).writeAsString(
      jsonEncode({
        'audio': {'sample_rate': 22050},
        'espeak': {'voice': 'es'},
        'inference': {'noise_scale': 0.6, 'noise_w': 0.7, 'length_scale': 1.1},
        'num_speakers': 1,
      }),
    );

    final models = await PiperModelStore(rootPath: root.path).scan();
    expect(models, hasLength(1));
    final model = models.first;
    expect(model.id, 'vits-piper-es-glados-medium');
    expect(model.name, 'Es Glados Medium');
    expect(model.language, 'es');
    expect(model.espeakVoice, 'es');
    expect(model.sampleRate, 22050);
    expect(model.noiseScale, 0.6);
    expect(model.lengthScale, 1.1);
    expect(model.isValid, isTrue);
  });

  test('una carpeta sin onnx o tokens no se considera modelo', () async {
    final root = await Directory.systemTemp.createTemp('vibebook-piper-test-');
    addTearDown(() async {
      if (await root.exists()) {
        await root.delete(recursive: true);
      }
    });
    await File(p.join(root.path, 'tokens.txt')).writeAsString('a 1\n');
    final models = await PiperModelStore(rootPath: root.path).scan();
    expect(models, isEmpty);
  });
}
