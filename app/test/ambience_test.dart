import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/domain/ambience.dart';

void main() {
  test('cada preset tiene una grabación real y un manifiesto válido', () async {
    final manifest = jsonDecode(
      await File(p.join('assets', 'ambience', 'manifest.json')).readAsString(),
    ) as Map<String, dynamic>;
    final assets = (manifest['assets'] as List).cast<Map<String, dynamic>>();
    expect(assets, hasLength(AmbiencePreset.values.length));
    for (final preset in AmbiencePreset.values) {
      final entry = assets.firstWhere((item) => item['id'] == preset.id);
      final file = File(p.join('assets', 'ambience', entry['file'] as String));
      expect(await file.exists(), isTrue, reason: preset.id);
      expect(await file.length(), greaterThan(1024 * 1024), reason: preset.id);
      expect(entry['license'], 'CC0 1.0');
      expect(entry['source'], startsWith('https://freesound.org/s/'));
    }
  });

  test('el catálogo de presets acepta nombres viejos y nuevos', () {
    expect(AmbiencePresetDetails.byId('sea'), AmbiencePreset.sea);
    expect(AmbiencePresetDetails.byId('ocean'), AmbiencePreset.sea);
    expect(AmbiencePresetDetails.byId('forest'), AmbiencePreset.forest);
    expect(AmbiencePresetDetails.byId('desconocido'), AmbiencePreset.rain);
    expect(
      AmbiencePreset.values.map((preset) => preset.label).toSet(),
      hasLength(6),
    );
  });
}
