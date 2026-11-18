class PiperCatalogEntry {
  const PiperCatalogEntry({
    required this.id,
    required this.name,
    required this.language,
    required this.description,
    required this.url,
    required this.sizeBytes,
    required this.license,
    required this.licenseUrl,
  });

  final String id;
  final String name;
  final String language;
  final String description;
  final String url;
  final int sizeBytes;
  final String license;
  final String licenseUrl;

  String get sizeLabel {
    final mb = sizeBytes / (1024 * 1024);
    return '${mb.toStringAsFixed(0)} MB';
  }
}

const piperCatalog = [
  PiperCatalogEntry(
    id: 'vits-piper-es_ES-davefx-medium',
    name: 'Davefx',
    language: 'Español (España)',
    description: 'Voz masculina, calidad media. Clara y neutra.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_ES-davefx-medium.tar.bz2',
    sizeBytes: 67184952,
    license: 'CC0',
    licenseUrl: 'https://huggingface.co/rhasspy/piper-voices/raw/main/es/es_ES/davefx/medium/MODEL_CARD',
  ),
  PiperCatalogEntry(
    id: 'vits-piper-es_MX-ald-medium',
    name: 'Ald',
    language: 'Español (México)',
    description: 'Voz masculina, calidad media. Acento mexicano.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_MX-ald-medium.tar.bz2',
    sizeBytes: 67196497,
    license: 'Unlicense',
    licenseUrl: 'https://huggingface.co/rhasspy/piper-voices/raw/main/es/es_MX/ald/medium/MODEL_CARD',
  ),
];
