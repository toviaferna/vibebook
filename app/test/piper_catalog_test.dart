import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/piper_catalog.dart';

void main() {
  test('el catálogo tiene ids únicos y descargas bien formadas', () {
    final ids = piperCatalog.map((entry) => entry.id).toSet();
    expect(piperCatalog, hasLength(ids.length));
    for (final entry in piperCatalog) {
      expect(
        entry.url,
        startsWith(
          'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/',
        ),
      );
      expect(entry.url, endsWith('.tar.bz2'));
      expect(entry.sizeBytes, greaterThan(20 * 1024 * 1024));
      expect(entry.license.trim(), isNotEmpty);
      expect(entry.licenseUrl.trim(), isNotEmpty);
      expect(entry.description.trim(), isNotEmpty);
      expect(entry.name.trim(), isNotEmpty);
    }
  });

  test('incluye las voces nuevas en español', () {
    final ids = piperCatalog.map((entry) => entry.id).toSet();
    expect(
      ids,
      containsAll(const [
        'vits-piper-es_MX-claude-high',
        'vits-piper-es_AR-daniela-high',
        'vits-piper-es_ES-sharvard-medium',
        'vits-piper-es_ES-carlfm-x_low',
        'vits-piper-es_ES-glados-medium',
      ]),
    );
    expect(ids, contains('vits-piper-es_ES-davefx-medium'));
    expect(ids, contains('vits-piper-es_MX-ald-medium'));
  });

  test('las descripciones cubren variedad: femenina, liviana y acentos', () {
    final descriptions = piperCatalog
        .map((entry) => entry.description.toLowerCase())
        .toList();
    expect(descriptions.any((text) => text.contains('femenina')), isTrue);
    expect(descriptions.any((text) => text.contains('liviana')), isTrue);
    expect(descriptions.any((text) => text.contains('argentino')), isTrue);
    expect(descriptions.any((text) => text.contains('robótica')), isTrue);
  });
}
