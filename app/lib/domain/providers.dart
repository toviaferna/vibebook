/// Cloud TTS provider metadata and status.
class ProviderInfo {
  const ProviderInfo({
    required this.id,
    required this.label,
    required this.description,
    required this.docsUrl,
    required this.keyUrl,
    this.requiresRegion = false,
  });

  final String id;
  final String label;
  final String description;
  final String docsUrl;
  final String keyUrl;
  final bool requiresRegion;
}

const providerCatalog = <ProviderInfo>[
  ProviderInfo(
    id: 'gemini',
    label: 'Google Gemini TTS',
    description:
        'Emociones y estilo por instrucción; audio WAV. Requiere una clave '
        'de Google AI Studio.',
    docsUrl: 'https://ai.google.dev/gemini-api/docs/speech-generation',
    keyUrl: 'https://aistudio.google.com/apikey',
  ),
  ProviderInfo(
    id: 'elevenlabs',
    label: 'ElevenLabs',
    description:
        'Timings exactos por carácter y etiquetas emocionales. Las voces '
        'gratuitas son en inglés; las españolas son de biblioteca.',
    docsUrl: 'https://elevenlabs.io/docs/api-reference/text-to-speech',
    keyUrl: 'https://elevenlabs.io/app/settings/api-keys',
  ),
  ProviderInfo(
    id: 'azure',
    label: 'Azure Speech',
    description:
        'Estilos de emoción por voz y word boundaries. Requiere clave y '
        'región.',
    docsUrl: 'https://learn.microsoft.com/azure/ai-services/speech-service/',
    keyUrl: 'https://portal.azure.com',
    requiresRegion: true,
  ),
];

ProviderInfo providerInfo(String id) {
  for (final provider in providerCatalog) {
    if (provider.id == id) {
      return provider;
    }
  }
  throw ArgumentError.value(id, 'id', 'Proveedor desconocido');
}

class ProviderStatus {
  const ProviderStatus({
    required this.info,
    required this.configured,
    this.hint,
    this.source,
    this.region,
  });

  final ProviderInfo info;
  final bool configured;

  /// Masked key, for example `•••• 1234`.
  final String? hint;

  /// `env` when the key comes from the environment, `file` when stored.
  final String? source;
  final String? region;

  String get id => info.id;
  String get label => info.label;
}

class ProviderTestResult {
  const ProviderTestResult({
    required this.ok,
    required this.message,
    this.creditsUsed,
    this.creditsLimit,
    this.warning,
  });

  final bool ok;
  final String message;
  final int? creditsUsed;
  final int? creditsLimit;
  final String? warning;
}

class ProviderKeyException implements Exception {
  const ProviderKeyException(this.message);

  final String message;

  @override
  String toString() => message;
}
