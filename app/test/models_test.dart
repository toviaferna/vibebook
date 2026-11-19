import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/domain/models.dart';

void main() {
  test('parsea un manifiesto existente', () {
    final manifest = jsonEncode({
      'id': 'el-gato-negro-1234',
      'title': 'El gato negro',
      'author': 'Edgar Allan Poe',
      'language': 'es',
      'language_declared': 'en',
      'status': 'ready',
      'engine': 'kokoro',
      'voice': 'ef_dora',
      'duration_ms': 3600000,
      'chapters': [
        {
          'index': 1,
          'title': 'El gato negro',
          'audio': 'audio/chapters/chapter_001.mp3',
          'duration_ms': 120000,
          'segments': [
            {
              'id': 'c001p0001s00',
              'paragraph_index': 1,
              'text': 'La casa olía a sal.',
            },
            {
              'id': 'c001p0002s00',
              'paragraph_index': 2,
              'text': 'El gato miraba.',
            },
          ],
        },
      ],
      'toc': [
        {'title': 'El gato negro', 'level': 1, 'chapter_index': 1},
      ],
      'images': [],
      'cover': 'cover.jpg',
    });
    final book = Book.fromJsonString(manifest, id: 'el-gato-negro-1234');
    expect(book.title, 'El gato negro');
    expect(book.language, 'es');
    expect(book.declaredLanguage, 'en');
    expect(book.chapterCount, 1);
    expect(book.segmentCount, 2);
    expect(book.hasAudio, isTrue);
    expect(book.progressLabel, '1h 0m');
  });

  test('usa valores seguros con manifiesto incompleto', () {
    final book = Book.fromManifest({'chapters': []});
    expect(book.title, 'Sin título');
    expect(book.author, 'Desconocido');
    expect(book.language, 'es');
    expect(book.chapterCount, 0);
    expect(book.segmentCount, 0);
  });

  test('conserva las preferencias de ambiente y voz', () {
    final settings = AppSettings.fromJson({
      'themeMode': 'dark',
      'piperModelId': 'voice-a',
      'piperRate': -5,
      'ambienceEnabled': true,
      'ambiencePreset': 'sea',
      'ambienceVolume': 0.5,
      'ambienceDucking': 0.2,
      'reader': {'playbackRate': 1.25, 'volume': 0.8},
    });
    expect(settings.themeMode, 'dark');
    expect(settings.piperModelId, 'voice-a');
    expect(settings.piperRate, -5);
    expect(settings.ambienceEnabled, isTrue);
    expect(settings.ambiencePreset, 'sea');
    expect(settings.ambienceVolume, 0.5);
    expect(settings.ambienceDucking, 0.2);
    expect(settings.reader.playbackRate, 1.25);
    expect(settings.reader.volume, 0.8);
    final updated = settings.copyWith(
      ambiencePreset: 'fire',
      ambienceVolume: 0.7,
    );
    expect(updated.ambiencePreset, 'fire');
    expect(updated.ambienceVolume, 0.7);
    expect(updated.ambienceEnabled, isTrue);
  });

  test('los ajustes de motor TTS tienen defaults y viajan por JSON', () {
    // Un JSON viejo, sin los campos nuevos, carga con los defaults.
    final legacy = AppSettings.fromJson({'themeMode': 'dark'});
    expect(legacy.ttsEngine, 'piper');
    expect(legacy.edgeVoiceId, 'es-MX-JorgeNeural');
    expect(legacy.edgeRate, 0);
    expect(legacy.edgeFavorites, isEmpty);

    final edge = legacy.copyWith(
      ttsEngine: 'edge',
      edgeVoiceId: 'es-ES-ElviraNeural',
      edgeRate: -10,
      edgeFavorites: const ['es-ES-ElviraNeural', 'es-MX-DaliaNeural'],
    );
    expect(edge.ttsEngine, 'edge');
    expect(edge.edgeVoiceId, 'es-ES-ElviraNeural');
    expect(edge.edgeRate, -10);
    expect(edge.edgeFavorites, ['es-ES-ElviraNeural', 'es-MX-DaliaNeural']);

    final restored = AppSettings.fromJson(edge.toJson());
    expect(restored.ttsEngine, 'edge');
    expect(restored.edgeVoiceId, 'es-ES-ElviraNeural');
    expect(restored.edgeRate, -10);
    expect(restored.edgeFavorites, contains('es-MX-DaliaNeural'));
    expect(restored.piperModelId, legacy.piperModelId);
  });
}
