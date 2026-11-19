/// One TTS engine and its capabilities, mirroring the Tauri `EngineSpec`.
class TtsEngineSpec {
  const TtsEngineSpec({
    required this.id,
    required this.label,
    required this.description,
    required this.requiresNetwork,
    required this.requiresKey,
    required this.supportsStyles,
    required this.timing,
    required this.audioSuffix,
    required this.license,
    required this.sourceUrl,
    this.maxChars = 400,
    this.implemented = true,
  });

  final String id;
  final String label;
  final String description;
  final bool requiresNetwork;
  final bool requiresKey;
  final bool supportsStyles;

  /// `native_word`, `estimated_word` or `segment`.
  final String timing;
  final String audioSuffix;
  final String license;
  final String sourceUrl;
  final int maxChars;
  final bool implemented;
}

class TtsVoice {
  const TtsVoice({
    required this.id,
    required this.name,
    required this.locale,
    required this.gender,
    required this.engine,
    required this.detail,
    this.styles = const [],
  });

  final String id;
  final String name;
  final String locale;
  final String gender;
  final String engine;
  final String detail;
  final List<String> styles;
}

const _expressiveStyles = ['chat', 'cheerful', 'excited', 'sad', 'whispering'];

const ttsEngines = <TtsEngineSpec>[
  TtsEngineSpec(
    id: 'piper',
    label: 'Piper (local)',
    description: 'Sin cuenta ni nube. La síntesis corre en este equipo.',
    requiresNetwork: false,
    requiresKey: false,
    supportsStyles: false,
    timing: 'segment',
    audioSuffix: '.wav',
    license: 'GPL-3.0',
    sourceUrl: 'https://github.com/OHF-Voice/piper1-gpl',
  ),
  TtsEngineSpec(
    id: 'edge',
    label: 'Edge (online, experimental)',
    description: 'Voces neuronales de Microsoft vía red. Servicio no oficial.',
    requiresNetwork: true,
    requiresKey: false,
    supportsStyles: false,
    timing: 'native_word',
    audioSuffix: '.mp3',
    license: 'Servicio externo no oficial',
    sourceUrl: 'https://github.com/rany2/edge-tts',
  ),
  TtsEngineSpec(
    id: 'azure',
    label: 'Azure Speech (nube)',
    description:
        'Estilos de emoción y voces neuronales. Requiere clave y región.',
    requiresNetwork: true,
    requiresKey: true,
    supportsStyles: true,
    timing: 'estimated_word',
    audioSuffix: '.mp3',
    license: 'Servicio comercial',
    sourceUrl:
        'https://azure.microsoft.com/products/ai-services/text-to-speech',
  ),
  TtsEngineSpec(
    id: 'gemini',
    label: 'Gemini TTS (nube)',
    description: 'Emociones reales por instrucción; audio WAV. Requiere clave.',
    requiresNetwork: true,
    requiresKey: true,
    supportsStyles: true,
    timing: 'estimated_word',
    audioSuffix: '.wav',
    license: 'Servicio comercial',
    sourceUrl: 'https://ai.google.dev/gemini-api/docs/speech-generation',
  ),
  TtsEngineSpec(
    id: 'elevenlabs',
    label: 'ElevenLabs (nube)',
    description:
        'Timings exactos y etiquetas emocionales. Requiere clave; los '
        'créditos gratuitos son limitados.',
    requiresNetwork: true,
    requiresKey: true,
    supportsStyles: true,
    timing: 'native_word',
    audioSuffix: '.mp3',
    license: 'Servicio comercial',
    sourceUrl: 'https://elevenlabs.io/docs/api-reference/text-to-speech',
  ),
  TtsEngineSpec(
    id: 'kokoro',
    label: 'Kokoro (local)',
    description:
        'Voz local expresiva. El modelo español todavía no está validado en '
        'esta versión de Flutter.',
    requiresNetwork: false,
    requiresKey: false,
    supportsStyles: false,
    timing: 'estimated_word',
    audioSuffix: '.wav',
    license: 'Apache-2.0',
    sourceUrl: 'https://github.com/thewh1teagle/kokoro-onnx',
    implemented: false,
  ),
  TtsEngineSpec(
    id: 'espeak',
    label: 'eSpeak NG (local)',
    description: 'Fallback local pequeño y robótico. Requiere el binario.',
    requiresNetwork: false,
    requiresKey: false,
    supportsStyles: false,
    timing: 'segment',
    audioSuffix: '.wav',
    license: 'GPL-3.0',
    sourceUrl: 'https://github.com/espeak-ng/espeak-ng',
    implemented: false,
  ),
];

const ttsCloudVoices = <TtsVoice>[
  TtsVoice(
    id: 'es-MX-JorgeNeural',
    name: 'Jorge',
    locale: 'es-MX',
    gender: 'Masculino',
    engine: 'azure',
    detail: 'Masculino · México · Azure',
    styles: ['chat', 'cheerful', 'excited', 'sad', 'whispering'],
  ),
  TtsVoice(
    id: 'es-MX-DaliaNeural',
    name: 'Dalia',
    locale: 'es-MX',
    gender: 'Femenino',
    engine: 'azure',
    detail: 'Femenino · México · Azure',
    styles: ['cheerful', 'sad', 'whispering'],
  ),
  TtsVoice(
    id: 'Kore',
    name: 'Kore',
    locale: 'es-419',
    gender: 'Femenino',
    engine: 'gemini',
    detail: 'Femenino · Latinoamérica · Gemini',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'Orus',
    name: 'Orus',
    locale: 'es-419',
    gender: 'Masculino',
    engine: 'gemini',
    detail: 'Masculino · Latinoamérica · Gemini',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'Puck',
    name: 'Puck',
    locale: 'es-419',
    gender: 'Masculino',
    engine: 'gemini',
    detail: 'Masculino · Latinoamérica · Gemini',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'Charon',
    name: 'Charon',
    locale: 'es-419',
    gender: 'Masculino',
    engine: 'gemini',
    detail: 'Masculino · Latinoamérica · Gemini',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'Aoede',
    name: 'Aoede',
    locale: 'es-419',
    gender: 'Femenino',
    engine: 'gemini',
    detail: 'Femenino · Latinoamérica · Gemini',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'Sulafat',
    name: 'Sulafat',
    locale: 'es-419',
    gender: 'Femenino',
    engine: 'gemini',
    detail: 'Femenino · Latinoamérica · Gemini',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'pNInz6obpgDQGcFmaJgB',
    name: 'Adam',
    locale: 'en-US',
    gender: 'Masculino',
    engine: 'elevenlabs',
    detail: 'Masculino · Inglés multilingüe · ElevenLabs',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'ErXwobaYiN019PkySvjV',
    name: 'Antoni',
    locale: 'en-US',
    gender: 'Masculino',
    engine: 'elevenlabs',
    detail: 'Masculino · Inglés multilingüe · ElevenLabs',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'VR6AewLTigWG4xSOukaG',
    name: 'Arnold',
    locale: 'en-US',
    gender: 'Masculino',
    engine: 'elevenlabs',
    detail: 'Masculino · Inglés multilingüe · ElevenLabs',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'EXAVITQu4vr4xnSDxMaL',
    name: 'Bella',
    locale: 'en-US',
    gender: 'Femenino',
    engine: 'elevenlabs',
    detail: 'Femenino · Inglés multilingüe · ElevenLabs',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'dlGxemPxFMTY7iXagmOj',
    name: 'Fernando',
    locale: 'es-419',
    gender: 'Masculino',
    engine: 'elevenlabs',
    detail: 'Masculino · Latinoamérica · ElevenLabs biblioteca',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'CaJslL1xziwefCeTNzHv',
    name: 'Cristina',
    locale: 'es-419',
    gender: 'Femenino',
    engine: 'elevenlabs',
    detail: 'Femenino · Latinoamérica · ElevenLabs biblioteca',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'l1zE9xgNpUTaQCZzpNJa',
    name: 'Alberto',
    locale: 'es-419',
    gender: 'Masculino',
    engine: 'elevenlabs',
    detail: 'Masculino · Latinoamérica · ElevenLabs biblioteca',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'UOIqAnmS11Reiei1Ytkc',
    name: 'Carolina',
    locale: 'es-ES',
    gender: 'Femenino',
    engine: 'elevenlabs',
    detail: 'Femenino · España · ElevenLabs biblioteca',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'dF1Qg3iMRirscWEMtEKb',
    name: 'Diego',
    locale: 'es-419',
    gender: 'Masculino',
    engine: 'elevenlabs',
    detail: 'Masculino · Latinoamérica · ElevenLabs biblioteca',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: '9oPKasc15pfAbMr7N6Gs',
    name: 'Valeria',
    locale: 'es-419',
    gender: 'Femenino',
    engine: 'elevenlabs',
    detail: 'Femenino · Latinoamérica · ElevenLabs biblioteca',
    styles: _expressiveStyles,
  ),
  TtsVoice(
    id: 'ef_dora',
    name: 'Dora',
    locale: 'es-ES',
    gender: 'Femenino',
    engine: 'kokoro',
    detail: 'Femenino · España · Kokoro local',
  ),
  TtsVoice(
    id: 'em_alex',
    name: 'Alex',
    locale: 'es-ES',
    gender: 'Masculino',
    engine: 'kokoro',
    detail: 'Masculino · España · Kokoro local',
  ),
  TtsVoice(
    id: 'em_santa',
    name: 'Santa',
    locale: 'es-ES',
    gender: 'Masculino',
    engine: 'kokoro',
    detail: 'Masculino · España · Kokoro local',
  ),
  TtsVoice(
    id: 'es-419',
    name: 'eSpeak Latinoamérica',
    locale: 'es-419',
    gender: 'Neutro',
    engine: 'espeak',
    detail: 'Neutro · Latinoamérica · eSpeak NG',
  ),
];

const _defaults = {
  'piper': 'es_MX-ald-medium',
  'edge': 'es-MX-JorgeNeural',
  'azure': 'es-MX-JorgeNeural',
  'gemini': 'Kore',
  'elevenlabs': 'pNInz6obpgDQGcFmaJgB',
  'kokoro': 'ef_dora',
  'espeak': 'es-419',
};

TtsEngineSpec ttsEngine(String id) {
  for (final engine in ttsEngines) {
    if (engine.id == id) {
      return engine;
    }
  }
  return ttsEngines.first;
}

String defaultTtsVoice(String engine) =>
    _defaults[engine] ?? 'es-MX-JorgeNeural';

List<TtsVoice> ttsVoicesFor(String engine) {
  return ttsCloudVoices
      .where((voice) => voice.engine == engine)
      .toList(growable: false);
}

TtsVoice? ttsVoiceById(String id) {
  for (final voice in ttsCloudVoices) {
    if (voice.id == id) {
      return voice;
    }
  }
  return null;
}

bool voiceLanguageMismatch(TtsVoice? voice, String? bookLanguage) {
  if (voice == null || bookLanguage == null || bookLanguage.isEmpty) {
    return false;
  }
  final book = bookLanguage.split('-').first.toLowerCase();
  final voiceLocale = voice.locale.split('-').first.toLowerCase();
  return book != voiceLocale && voiceLocale != 'multi';
}
