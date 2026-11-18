enum AmbiencePreset { rain, wind, sea, fire, night }

extension AmbiencePresetDetails on AmbiencePreset {
  String get id => name;

  String get label => switch (this) {
        AmbiencePreset.rain => 'Lluvia',
        AmbiencePreset.wind => 'Viento',
        AmbiencePreset.sea => 'Mar',
        AmbiencePreset.fire => 'Fuego',
        AmbiencePreset.night => 'Noche',
      };

  String get description => switch (this) {
        AmbiencePreset.rain => 'Lluvia suave sobre la ventana.',
        AmbiencePreset.wind => 'Viento lejano entre los árboles.',
        AmbiencePreset.sea => 'Olas lentas y espuma.',
        AmbiencePreset.fire => 'Chispas y madera crepitando.',
        AmbiencePreset.night => 'Grillos y aire quieto.',
      };

  static AmbiencePreset byId(String? id) {
    for (final preset in AmbiencePreset.values) {
      if (preset.id == id) {
        return preset;
      }
    }
    return AmbiencePreset.rain;
  }
}
