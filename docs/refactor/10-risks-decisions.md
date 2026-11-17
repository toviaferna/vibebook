# 10 — Riesgos técnicos y decisiones pendientes

## 1. Cómo leer este documento

- **Hecho:** verificado en el repo o en documentación oficial.
- **Riesgo:** probabilidad/impacto estimados; se validan en el spike o en la
  fase indicada.
- **Recomendación:** propuesta del equipo de planificación, no una decisión
  tomada.
- **Pendiente:** requiere aprobación del usuario antes de implementar.

## 2. Riesgos principales

| # | Riesgo | Prob. | Impacto | Mitigación | Fase |
|---|---|---|---|---|---|
| R1 | La reescritura completa en Dart pierde features o introduce regresiones | Alta | Alto | F0 spike + matriz de paridad + beta + tests de migración | F0/F11/F13 |
| R2 | Kokoro español no es viable en Dart puro | Media | Alto | Spike con `flutter_onnxruntime` + G2P; fallback Piper/cloud o Python embebido | F0/F7 |
| R3 | El modo EPUB Original no alcanza fidelidad sin WebView | Alta | Medio | Decidir alcance: HTML simplificado vs WebView por plataforma; aprobar G2 | F0/F8 |
| R4 | La mezcla de ambience en vivo no es sample-accurate en Flutter | Media | Medio | Múltiples players; si no alcanza, motor nativo/FFI; Web Audio en Web | F0/F9 |
| R5 | FFmpeg no está disponible en Windows/Linux ARM64 | Alta | Medio | FFmpeg del sistema, binario propio o emulación; mensaje claro; probar | F0/F10 |
| R6 | Background jobs/audio en Android/iOS se pausan o matan | Alta | Alto | Foreground service, audio_service, BGTask, reanudación persistente | F10 |
| R7 | APK/IPA/instaladores exceden tamaño | Media | Medio | Modelos fuera del binario, split ABI, `_audio` FFmpeg, medir | F10/F12 |
| R8 | Plugins sin soporte ARM64 o Web | Media | Medio | Matriz de capacidades; fallback; excluir feature | F10 |
| R9 | App Store rechaza descarga de modelos o ejecución de binarios | Baja/Media | Alto | Descarga de datos, no binarios; revisar guidelines; TestFlight | F10/F12 |
| R10 | Firma/notarización no disponible (sin Apple/Windows cert) | Alta | Medio | Distribución unsigned documentada; updates solo donde se pueda firmar | G4/F12 |
| R11 | Migración de biblioteca/DB pierde estado | Media | Alto | Backup, migración idempotente, tests con biblioteca real, rollback | F5/F13 |
| R12 | Dependencias de baja adopción (edge_tts, epub_plus, FFmpegKit fork) | Media | Medio | Vendor/fork MIT, tests de contrato, plan de reemplazo | F2/F6/F7 |
| R13 | Cloud TTS cambia API/precios/cuotas | Media | Medio | Clientes aislados, errores claros, proveedores alternativos | F7 |
| R14 | El equipo no tiene experiencia Flutter/Dart | Media | Medio | F3/F4 tempranos, docs, pair/agents, vertical slices | F3 |
| R15 | CI/costos de runners macOS/ARM64 | Media | Bajo/Medio | Ejecutar lo crítico; releases manuales; cache | F12 |
| R16 | Deuda de accesibilidad en componentes nuevos | Media | Medio | Goldens + SemanticsTester + auditoría por fase | F4/F11 |
| R17 | El lector custom es más lento que epubjs | Media | Alto | Paginador con cache/isolate; perf budget; fallback WebView | F0/F8 |
| R18 | Ambigüedad de alcance (Web/iOS/ARM64) | Alta | Medio | G3; matriz de soporte explícita | G3 |
| R19 | Licencias (FFmpeg LGPL/GPL, modelos, fuentes) | Baja/Media | Medio | `_audio` LGPL, notices, revisión, no bundlear modelos sin licencia | F12 |
| R20 | Se pierde la biblioteca `.books/` por un bug | Baja | Muy alto | Read-only scan, backups, tests, nunca borrar fuera del libro | F5/F13 |

## 3. Decisiones pendientes (puertas)

### G1 — Motor: Dart puro vs Python embebido

**Contexto:** el motor actual son 13.860 líneas de Python con 531 tests. Dart
puro elimina el runtime y unifica el lenguaje, pero exige reescribir ingest,
TTS, ffmpeg, M4B y ambience. Python embebido conserva el motor y acelera la
paridad, pero mantiene dos lenguajes y un runtime pesado.

**Recomendación:** **Dart puro con spike F0**. Si F0 falla en Kokoro/FFmpeg/
lector/background, cambiar a Python embebido con `serious_python` sin tirar la
UI/arquitectura.

**Aprobación necesaria:** sí. Sin G1 no se escribe código de producto.

### G2 — Paridad obligatoria: Kokoro español y EPUB Original

**Contexto:** Kokoro español es el motor local más expresivo; el modo Original
preserva la maquetación del EPUB. Ambos son caros de replicar en Flutter.

**Opciones:**

- A) Ambos obligatorios desde la primera versión → más tiempo/riesgo.
- B) Kokoro obligatorio, Original simplificado → medio.
- C) Original obligatorio, Kokoro reemplazado por Piper/cloud → medio.
- D) Ninguno obligatorio en v1; se documenta y se agrega después → más rápido,
  pero es una pérdida funcional que requiere aprobación.

**Recomendación:** B o C según el spike; no prometer ambos sin evidencia.

**Aprobación necesaria:** sí, porque puede implicar eliminar una feature.

### G3 — Plataformas oficiales

**Contexto:** Flutter soporta las 6 familias, pero los plugins nativos no
siempre. Windows/Linux ARM64 y Web son los más débiles.

**Opciones:**

- A) Oficiales: Windows x64/ARM64, macOS x64/ARM64, Linux x64/ARM64, Android,
  iOS; Web best-effort.
- B) Oficiales: Windows x64, macOS, Linux x64, Android; ARM64/Web best-effort.
- C) Oficiales: Windows x64, macOS, Linux x64, Android; iOS/ARM64/Web fuera de
  v1.

**Recomendación:** A, con Web best-effort y ARM64 condicionado a FFmpeg.

**Aprobación necesaria:** sí.

### G4 — Firma y distribución

**Contexto:** la app actual no está firmada. La nueva app puede firmarse o no.

**Opciones:**

- A) Sin firma: SmartScreen/Gatekeeper documentados; updates manuales.
- B) Windows Authenticode + macOS Developer ID/notarización; updates firmados.
- C) B + Play Store/App Store.

**Recomendación:** B para desktop si hay certificados; Android/iOS según
tienda. Sin certificados, no prometer auto-update en macOS.

**Aprobación necesaria:** sí; depende de presupuesto/cuentas.

### G5 — Migración y formato de biblioteca

**Contexto:** la biblioteca actual en disco es portable; la DB y estados viven
en SQLite. Una migración mal hecha puede perder datos.

**Opciones:**

- A) Conservar manifiesto/layout y migrar DB/estado (recomendado).
- B) Nuevo formato y migración irreversible (no recomendado).
- C) Empezar de cero (no recomendado).

**Recomendación:** A, con backup y rollback.

**Aprobación necesaria:** sí.

## 4. Supuestos del plan

Si alguno es falso, el plan cambia:

1. El usuario quiere una app de escritorio + Android/iOS, no solo desktop.
2. La biblioteca existente debe conservarse.
3. La app sigue siendo local-first y AGPL-3.0-only.
4. No hay un equipo grande; el trabajo es de una persona asistida por agentes.
5. Se acepta una reescritura de varios meses si el spike la justifica.
6. No se exige paridad 1:1 de cada detalle visual en la primera beta.
7. Web no es un objetivo principal.
8. Los proveedores cloud siguen siendo opcionales.
9. Los modelos TTS se descargan aparte, no se bundlean.
10. No se publican releases sin aprobación.

## 5. Decisiones ya recomendadas (no bloqueantes)

- Riverpod 3.5 para estado/DI.
- go_router 18.1 para navegación.
- Drift 2.35 para persistencia.
- Freezed 4 + json_serializable.
- Dio 5.11.
- just_audio + audio_service + media_kit desktop.
- sherpa_onnx para Piper/VITS.
- ffmpeg_kit_flutter_new_audio + fallback ARM64.
- fork de epub_plus + lector propio.
- gen_l10n + ARB.
- Lucide icons.
- very_good_analysis + riverpod_lint.
- talker + Sentry opt-in.
- desktop_updater para desktop.

Estas se pueden revisar en F2, pero no se cambian sin un ADR.

## 6. Preguntas para el usuario

Antes de implementar, se necesita respuesta a:

1. **G1:** ¿Aceptás el spike Dart puro y, si falla, el fallback Python embebido?
2. **G2:** ¿Kokoro español y EPUB Original son obligatorios en la primera
   versión Flutter?
3. **G3:** ¿iOS y Web son objetivos oficiales o best-effort? ¿Windows/Linux
   ARM64 son obligatorios?
4. **G4:** ¿Tenés Apple Developer y/o certificado Windows Authenticode?
5. **G5:** ¿Confirmás que la biblioteca actual debe migrarse sin pérdida y que
   se conserva el layout en disco?
6. **Alcance:** ¿la primera beta debe incluir ambience y export M4B, o se puede
   lanzar con lectura + conversión y agregar ambience después?
7. **Tiempo:** ¿hay una fecha límite o se prioriza calidad/paridad?

## 7. Criterio de éxito de la planificación

La planificación se considera completa cuando:

- [ ] G1–G5 están respondidas y registradas.
- [ ] El stack y los ADRs están aprobados.
- [ ] El plan F0–F14 está aprobado.
- [ ] La matriz de paridad está acordada.
- [ ] Los riesgos P0 tienen mitigación y dueño.
- [ ] No se empezó a implementar código de producto antes de la aprobación.
