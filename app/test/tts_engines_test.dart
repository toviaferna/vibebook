import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/tts_engines.dart';
import 'package:vibebook_app/domain/models.dart';

void main() {
  test('el catálogo incluye todos los motores de la app Tauri', () {
    final ids = ttsEngines.map((engine) => engine.id).toSet();
    expect(
      ids,
      containsAll([
        'piper',
        'edge',
        'azure',
        'gemini',
        'elevenlabs',
        'kokoro',
        'espeak',
      ]),
    );
  });

  test('cada motor tiene una voz por defecto y voces cloud', () {
    expect(defaultTtsVoice('piper'), 'es_MX-ald-medium');
    expect(defaultTtsVoice('gemini'), 'Kore');
    expect(ttsVoicesFor('azure'), hasLength(2));
    expect(ttsVoicesFor('gemini'), hasLength(6));
    expect(ttsVoicesFor('elevenlabs'), hasLength(10));
    expect(ttsVoicesFor('kokoro'), hasLength(3));
    expect(ttsVoicesFor('espeak'), hasLength(1));
    expect(ttsVoiceById('Kore')!.name, 'Kore');
  });

  test('detecta cuando la voz no coincide con el idioma del libro', () {
    expect(voiceLanguageMismatch(ttsVoiceById('Kore'), 'es'), isFalse);
    expect(
      voiceLanguageMismatch(ttsVoiceById('pNInz6obpgDQGcFmaJgB'), 'es'),
      isTrue,
    );
    expect(
      voiceLanguageMismatch(ttsVoiceById('pNInz6obpgDQGcFmaJgB'), 'en'),
      isFalse,
    );
    expect(voiceLanguageMismatch(null, 'es'), isFalse);
  });

  test('los ajustes viejos migran al motor y la voz genéricos', () {
    final edge = AppSettings.fromJson({
      'ttsEngine': 'edge',
      'edgeVoiceId': 'es-ES-ElviraNeural',
      'edgeRate': -15,
    });
    expect(edge.ttsVoiceId, 'es-ES-ElviraNeural');
    expect(edge.ttsRate, -15);
    expect(edge.voiceForEngine('edge'), 'es-ES-ElviraNeural');
    expect(edge.rateForEngine('edge'), -15);

    final gemini = AppSettings.fromJson({'ttsEngine': 'gemini'});
    expect(gemini.voiceForEngine('gemini'), 'Kore');
    expect(gemini.ttsStyle, 'neutral');

    final piper = AppSettings.fromJson({
      'ttsEngine': 'piper',
      'piperModelId': 'voice-a',
      'piperRate': -5,
    });
    expect(piper.voiceForEngine('piper'), 'voice-a');
    expect(piper.rateForEngine('piper'), -5);
    expect(piper.ttsVoiceId, 'voice-a');
    expect(piper.ttsRate, -5);
  });

  test('una voz de otro motor cae al default', () {
    final settings = AppSettings.fromJson({
      'ttsEngine': 'gemini',
      'ttsVoiceId': 'es-MX-JorgeNeural',
    });
    expect(settings.voiceForEngine('gemini'), 'Kore');
    expect(settings.voiceForEngine('azure'), 'es-MX-JorgeNeural');
  });

  test('las preferencias de lectura nuevas se conservan', () {
    const preferences = ReaderPreferences();
    final book = preferences.copyWith(viewMode: 'book', pageTurn: false);
    expect(book.viewMode, 'book');
    expect(book.pageTurn, isFalse);
    final restored = ReaderPreferences.fromJson(book.toJson());
    expect(restored.viewMode, 'book');
    expect(restored.pageTurn, isFalse);
    expect(const ReaderPreferences().viewMode, 'text');
  });
}
