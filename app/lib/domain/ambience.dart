enum AmbiencePreset { rain, wind, sea, fire, night, forest }

extension AmbiencePresetDetails on AmbiencePreset {
  String get id => switch (this) {
    AmbiencePreset.sea => 'ocean',
    _ => name,
  };

  String get label => switch (this) {
    AmbiencePreset.rain => 'Lluvia',
    AmbiencePreset.wind => 'Viento',
    AmbiencePreset.sea => 'Mar',
    AmbiencePreset.fire => 'Fuego',
    AmbiencePreset.night => 'Noche',
    AmbiencePreset.forest => 'Bosque',
  };

  String get description => switch (this) {
    AmbiencePreset.rain => 'Lluvia real grabada en exterior.',
    AmbiencePreset.wind => 'Viento entre árboles, grabación de campo.',
    AmbiencePreset.sea => 'Olas y resaca en la costa.',
    AmbiencePreset.fire => 'Chimenea con madera crepitando.',
    AmbiencePreset.night => 'Grillos y ambiente nocturno.',
    AmbiencePreset.forest => 'Bosque, pájaros y vegetación.',
  };

  static AmbiencePreset byId(String? id) {
    for (final preset in AmbiencePreset.values) {
      if (preset.id == id || preset.name == id) {
        return preset;
      }
    }
    return AmbiencePreset.rain;
  }
}
