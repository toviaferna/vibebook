import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/ambience/ambience_generator.dart';
import 'package:vibebook_app/domain/ambience.dart';

void main() {
  test('genera una cama loopable y determinista para cada preset', () {
    for (final preset in AmbiencePreset.values) {
      final first = renderAmbienceSamples(preset);
      final second = renderAmbienceSamples(preset);
      expect(first.length, (32 - 2) * AmbienceGenerator.sampleRate, reason: preset.id);
      expect(first.length, second.length);
      expect(first[0], second[0]);
      expect(first[first.length ~/ 2], second[first.length ~/ 2]);
      var peak = 0.0;
      for (final value in first) {
        expect(value.isFinite, isTrue);
        final absolute = value.abs();
        if (absolute > peak) {
          peak = absolute;
        }
      }
      expect(peak, greaterThan(0.05), reason: preset.id);
      expect(peak, lessThanOrEqualTo(1.0), reason: preset.id);
    }
  });

  test('el catálogo de presets tiene etiquetas estables', () {
    expect(AmbiencePresetDetails.byId('sea'), AmbiencePreset.sea);
    expect(AmbiencePresetDetails.byId('desconocido'), AmbiencePreset.rain);
    expect(AmbiencePreset.values.map((preset) => preset.label).toSet(), hasLength(5));
  });
}
