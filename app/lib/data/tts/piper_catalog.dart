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
    id: 'vits-piper-es_ES-sharvard-medium',
    name: 'Sharvard',
    language: 'Español (España)',
    description:
        'Voz masculina, calidad media. El modelo trae 2 oradores; se usa el 0.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_ES-sharvard-medium.tar.bz2',
    sizeBytes: 80318184,
    license: 'CC-BY 3.0 (dataset)',
    licenseUrl: 'https://datashare.ed.ac.uk/handle/10283/574',
  ),
  PiperCatalogEntry(
    id: 'vits-piper-es_ES-carlfm-x_low',
    name: 'Carlfm',
    language: 'Español (España)',
    description: 'Voz masculina liviana (x_low, 16 kHz). La más rápida para equipos modestos.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_ES-carlfm-x_low.tar.bz2',
    sizeBytes: 26520563,
    license: 'Dominio público',
    licenseUrl: 'https://github.com/carlfm01/my-speech-datasets',
  ),
  PiperCatalogEntry(
    id: 'vits-piper-es_ES-glados-medium',
    name: 'GLaDOS',
    language: 'Español (España)',
    description: 'Voz robótica (GLaDOS, Portal). Para prueba y humor.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_ES-glados-medium.tar.bz2',
    sizeBytes: 67214285,
    license: 'Sin licencia declarada',
    licenseUrl: 'https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models',
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
  PiperCatalogEntry(
    id: 'vits-piper-es_MX-claude-high',
    name: 'Claude',
    language: 'Español (México)',
    description: 'Voz masculina, calidad alta. Acento mexicano.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_MX-claude-high.tar.bz2',
    sizeBytes: 67207890,
    license: 'Apache-2.0 (dataset)',
    licenseUrl: 'https://huggingface.co/spaces/HirCoir/Piper-TTS-Spanish',
  ),
  PiperCatalogEntry(
    id: 'vits-piper-es_AR-daniela-high',
    name: 'Daniela',
    language: 'Español (Argentina)',
    description: 'Voz femenina, calidad alta. Acento argentino.',
    url: 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_AR-daniela-high.tar.bz2',
    sizeBytes: 115562134,
    license: 'CC-BY-SA 4.0 (dataset)',
    licenseUrl: 'https://www.openslr.org/61/',
  ),
];
