/// A neural voice of the Edge Read Aloud service.
class EdgeVoice {
  const EdgeVoice({
    required this.id,
    required this.name,
    required this.locale,
    required this.gender,
  });

  /// Short name the service expects, e.g. `es-MX-JorgeNeural`.
  final String id;
  final String name;
  final String locale;
  final String gender;
}

/// Curated Spanish voices of the Edge service (es-*, male and female across
/// locales). The list is static: it avoids a network call on every conversion
/// and keeps the picker usable offline.
const edgeVoices = [
  EdgeVoice(
    id: 'es-ES-AlvaroNeural',
    name: 'Álvaro',
    locale: 'es-ES',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-ES-ElviraNeural',
    name: 'Elvira',
    locale: 'es-ES',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-ES-XimenaNeural',
    name: 'Ximena',
    locale: 'es-ES',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-MX-JorgeNeural',
    name: 'Jorge',
    locale: 'es-MX',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-MX-DaliaNeural',
    name: 'Dalia',
    locale: 'es-MX',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-AR-TomasNeural',
    name: 'Tomás',
    locale: 'es-AR',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-AR-ElenaNeural',
    name: 'Elena',
    locale: 'es-AR',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-US-AlonsoNeural',
    name: 'Alonso',
    locale: 'es-US',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-US-PalomaNeural',
    name: 'Paloma',
    locale: 'es-US',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-CO-GonzaloNeural',
    name: 'Gonzalo',
    locale: 'es-CO',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-CO-SalomeNeural',
    name: 'Salomé',
    locale: 'es-CO',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-CL-LorenzoNeural',
    name: 'Lorenzo',
    locale: 'es-CL',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-CL-CatalinaNeural',
    name: 'Catalina',
    locale: 'es-CL',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-PY-MarioNeural',
    name: 'Mario',
    locale: 'es-PY',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-PY-TaniaNeural',
    name: 'Tania',
    locale: 'es-PY',
    gender: 'femenina',
  ),
  EdgeVoice(
    id: 'es-PE-AlexNeural',
    name: 'Alex',
    locale: 'es-PE',
    gender: 'masculina',
  ),
  EdgeVoice(
    id: 'es-PE-CamilaNeural',
    name: 'Camila',
    locale: 'es-PE',
    gender: 'femenina',
  ),
];

const defaultEdgeVoiceId = 'es-MX-JorgeNeural';

EdgeVoice? edgeVoiceById(String? id) {
  for (final voice in edgeVoices) {
    if (voice.id == id) {
      return voice;
    }
  }
  return null;
}
