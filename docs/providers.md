# Proveedores TTS

Cada motor cloud se configura desde **Ajustes → Proveedores en la nube**. La
clave se guarda en `<datos de la app>/provider-keys.json`, con permisos
restringidos en Linux/macOS, y la API solo devuelve `configurada` y los últimos
cuatro caracteres. Nunca se muestra completa ni se escribe en el repositorio.

También se aceptan variables de entorno, que tienen prioridad:

| Proveedor | Variables |
|---|---|
| Gemini | `GEMINI_API_KEY` o `GOOGLE_API_KEY` |
| ElevenLabs | `ELEVENLABS_API_KEY` |
| Azure | `AZURE_SPEECH_KEY` y `AZURE_SPEECH_REGION` |

## Gemini TTS

- Modelo: `gemini-3.8-flash-tts`.
- Salida: WAV 24 kHz mono 16 bits.
- Español: detección automática, más de 130 idiomas.
- Emociones: `speech_metadata.style` en inglés; no se leen en voz alta.
- Timings: no devuelve palabras; el lector usa timings estimados.
- Límite gratuito: 3 solicitudes por minuto. Para un libro completo hace falta
  facturación.
- La conversión usa concurrencia 1 y espera 65 s ante un `429`.

Clave: https://aistudio.google.com/apikey

## ElevenLabs

- Endpoint: `/v1/text-to-speech/{voice}/with-timestamps`.
- Salida: MP3.
- Timings exactos por carácter, agrupados en palabras.
- Emociones: `eleven_v3` con etiquetas `[sad]`, `[whispers]`, etc.; para el
  resto se usan `voice_settings.style` y `stability`.
- Voces disponibles en el plan gratuito: Adam, Antoni, Arnold y Bella.
  Domi, Elli, Josh y Sam requieren plan pago.
- Los 10.000 créditos del plan gratuito equivalen a ~10.000 caracteres, unos
  10–12 minutos de audio. La app avisa si el libro supera el saldo conocido.
- Si la clave no tiene `user_read`, no se puede mostrar el saldo. Si tampoco
  tiene `voices_read`, no se listan las voces; la app usa las voces curadas.

Clave: https://elevenlabs.io/app/settings/api-keys

## Azure Speech

- Estilos por voz (`chat`, `cheerful`, `excited`, `sad`, `whispering`).
- Word boundaries nativos.
- Requiere clave y región; la capa gratuita incluye 0,5 M de caracteres al mes.
- El SDK opcional (`uv sync --extra azure-sdk`) mejora los timings; sin SDK se
  usa REST.

Clave: https://portal.azure.com

## Costos y privacidad

- Gemini y ElevenLabs envían el texto a sus servidores. No envían el EPUB ni la
  biblioteca completa.
- Edge es un servicio no oficial y puede limitar solicitudes.
- Kokoro, Piper y eSpeak NG funcionan sin red.
- La app no incluye claves ni las comparte entre usuarios.

## Solución de problemas

- **“Sin configurar”**: revisá que la clave tenga al menos 8 caracteres y, en
  Azure, que la región esté completa.
- **ElevenLabs 402**: el plan no permite esa voz. Probá Adam, Antoni, Arnold o
  Bella.
- **Gemini 429**: esperá un minuto o activá facturación.
- **La clave no aparece**: si existe una variable de entorno, tiene prioridad
  sobre el archivo y el botón Quitar no la borra.
